#!/usr/bin/env bash
# SHIFT LLM-judge job: one model, one shard, node-local Ollama on one GPU.
# Required env (passed with sbatch --export): SHIFT_ROOT MODEL SHARD PROMPTS OUT SEEDS PARALLEL OLLAMA_BIN OLLAMA_MODELS
#SBATCH --job-name=shift-llm
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --output=%x-%j.out
set -euo pipefail
module load StdEnv/2023 python/3.12.4 2>/dev/null || true
echo "host=$(hostname) job=$SLURM_JOB_ID model=$MODEL shard=$SHARD gpu=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1)"
mkdir -p "$(dirname "$OUT")" "$SHIFT_ROOT/logs"
LOG="$SHIFT_ROOT/logs/ollama_${SLURM_JOB_ID}.log"

# Stage runtime on node-local disk (shared scratch can trip Ollama's GPU-discovery watchdog).
runtime_source=$(cd "$(dirname "$OLLAMA_BIN")/.." && pwd)
runtime_local="${SLURM_TMPDIR:-/tmp}/shift-ollama"
mkdir -p "$runtime_local"
rsync -a --exclude=vulkan "$runtime_source/" "$runtime_local/"
export OLLAMA_VULKAN=0 OLLAMA_LOAD_TIMEOUT=10m OLLAMA_NOPRUNE=1 OLLAMA_NO_CLOUD=1
export OLLAMA_HOST="127.0.0.1:$((20000 + SLURM_JOB_ID % 30000))"
export OLLAMA_NUM_PARALLEL="${PARALLEL:-4}" OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=30m
export OLLAMA_MODELS OLLAMA_CONTEXT_LENGTH="${NUM_CTX:-16384}" OLLAMA_FLASH_ATTENTION=1
"$runtime_local/bin/ollama" serve > "$LOG" 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null || true' EXIT
curl --fail --silent --retry 20 --retry-connrefused --retry-delay 2 --retry-max-time 60 \
     "http://$OLLAMA_HOST/api/version"; echo

# Preload and require full GPU residency before any task prompt.
curl -s "http://$OLLAMA_HOST/api/generate" -d "{\"model\":\"$MODEL\",\"prompt\":\"\",\"keep_alive\":\"30m\",\"options\":{\"num_ctx\":${NUM_CTX:-16384}}}" > /dev/null
python3 - "$OLLAMA_HOST" "$MODEL" <<'EOF'
import json, sys, urllib.request
ps = json.load(urllib.request.urlopen(f"http://{sys.argv[1]}/api/ps"))
m = [x for x in ps.get("models", []) if x["name"].startswith(sys.argv[2])]
assert m, f"model not loaded: {ps}"
size, vram = m[0]["size"], m[0].get("size_vram", 0)
print(f"residency size={size} vram={vram} ratio={vram/size:.3f} digest={m[0].get('digest','')[:16]}")
assert vram >= 0.98 * size, "model not fully GPU resident"
EOF

python3 "$SHIFT_ROOT/hpc/payload/llm_client.py" --prompts "$PROMPTS" --out "$OUT" --model "$MODEL" \
  --seeds "$SEEDS" --host "http://$OLLAMA_HOST" --parallel "${PARALLEL:-4}" --shard "$SHARD" \
  --num-ctx "${NUM_CTX:-16384}" ${LIMIT:+--limit $LIMIT}
nvidia-smi --query-gpu=name,utilization.gpu,memory.used --format=csv,noheader
echo "done $(date -u +%FT%TZ)"
