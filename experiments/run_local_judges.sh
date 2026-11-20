#!/usr/bin/env bash
# Larger LLM judges (the three models pre-registered in configs/study.yaml but absent
# from the HPC model caches, amendment A1), run on the local GB10 through Ollama.
# Same prompts, schema and decoding as the HPC panel (temperature 0.2, top_p 0.9,
# num_ctx 8192); one seed (11). Resumable: re-running skips finished (key, seed) pairs.
# Output: results/raw/llm_local/full/<model>.jsonl  -> analysis/llm_judges.py --tag local --glob "results/raw/llm_local/full/*.jsonl"
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=results/raw/llm_local/full
mkdir -p "$OUT"
for M in qwen3-coder:30b gpt-oss:20b devstral:24b; do
  F="$OUT/${M//:/_}.jsonl"
  echo "=== $M $(date -u +%FT%TZ)"
  .venv/bin/python hpc/payload/llm_client.py --prompts results/processed/llm_inputs/prompts.jsonl \
    --out "$F" --model "$M" --seeds 11 --num-ctx 8192 --parallel 4 --timeout 900
  ollama stop "$M" 2>/dev/null || true
done
echo "=== all done $(date -u +%FT%TZ)"
