#!/usr/bin/env python3
"""SHIFT multi-cluster controller (Alliance: fir, rorqual, narval).

Uses the ControlMaster sockets opened by hpc/scripts/ssh-session.sh; never
handles credentials. Every submission is appended to hpc/fetched/jobs.jsonl.

  python hpc/scripts/fleet.py probe
  python hpc/scripts/fleet.py deploy  [--sites fir,rorqual]
  python hpc/scripts/fleet.py submit --site fir --model qwen2.5-coder:7b --shard 0/1 --tag smoke --limit 20 --time 0:45:00
  python hpc/scripts/fleet.py status
  python hpc/scripts/fleet.py fetch --tag smoke
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CFG = json.loads((ROOT / "hpc/config/clusters.json").read_text())
FETCHED = ROOT / "hpc/fetched"
JOBS = FETCHED / "jobs.jsonl"


def ssh_opts(site: str) -> list[str]:
    return ["-o", f"ControlPath={ROOT}/hpc/.ssh/{site}", "-o", "ControlMaster=no",
            "-o", "BatchMode=yes", "-o", "ConnectTimeout=20"]


def target(site: str) -> str:
    return f"{CFG['username']}@{CFG['clusters'][site]['host']}"


def rsh(site: str, cmd: str, timeout: int = 120) -> tuple[int, str]:
    r = subprocess.run(["ssh", *ssh_opts(site), target(site), cmd], capture_output=True,
                       text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr).strip()


def rsync(site: str, src: str, dst: str, timeout: int = 900) -> int:
    e = "ssh " + " ".join(shlex.quote(x) for x in ssh_opts(site))
    return subprocess.run(["rsync", "-az", "-e", e, src, dst], timeout=timeout).returncode


def sites(arg: str | None) -> list[str]:
    return arg.split(",") if arg else list(CFG["clusters"])


def probe(a) -> None:
    out = {}
    for s in sites(a.sites):
        code, txt = rsh(s, "hostname; echo; "
                        "for b in " + " ".join(CFG["ollama_bin_candidates"]) + "; do [ -x $b ] && echo BIN:$b; done; "
                        "for d in " + " ".join(CFG["model_dir_candidates"]) + "; do [ -d $d/manifests ] && "
                        "echo MODELS:$d && find $d/manifests -mindepth 3 -maxdepth 4 -type f | sed 's|.*/library/||' | tr '\\n' ' ' && echo; done; "
                        "sinfo -h -o '%P %G %a %D' | grep -i gpu | head -8; "
                        "squeue -u $USER -h | wc -l; diskusage_report 2>/dev/null | grep -E 'scratch|project' | head -3", timeout=90)
        out[s] = {"ok": code == 0, "report": txt}
        print(f"===== {s} (rc={code})\n{txt}\n")
    FETCHED.mkdir(parents=True, exist_ok=True)
    (FETCHED / "probe.json").write_text(json.dumps(out, indent=2))


def deploy(a) -> None:
    for s in sites(a.sites):
        w = CFG["clusters"][s]["work"]
        rsh(s, f"mkdir -p {w}/hpc/payload {w}/hpc/slurm {w}/inputs {w}/outputs {w}/logs")
        rc1 = rsync(s, f"{ROOT}/hpc/payload/", f"{target(s)}:{w}/hpc/payload/")
        rc2 = rsync(s, f"{ROOT}/hpc/slurm/", f"{target(s)}:{w}/hpc/slurm/")
        rc3 = rsync(s, f"{ROOT}/results/processed/llm_inputs/", f"{target(s)}:{w}/inputs/")
        print(f"{s}: deploy rc={rc1},{rc2},{rc3}")


def submit(a) -> None:
    s = a.site
    c = CFG["clusters"][s]
    w = c["work"]
    probe_info = json.loads((FETCHED / "probe.json").read_text()).get(s, {}).get("report", "")
    binp = a.ollama_bin or next((l[4:] for l in probe_info.splitlines() if l.startswith("BIN:")), "")
    mdir = a.models_dir or next((l[7:] for l in probe_info.splitlines() if l.startswith("MODELS:")), "")
    if not binp or not mdir:
        sys.exit(f"{s}: no ollama binary/model dir known; run probe or pass --ollama-bin/--models-dir")
    safe_model = a.model.replace(":", "_").replace("/", "_")
    shard_tag = a.shard.replace("/", "of") + "_s" + a.seeds.replace(",", "-").replace(":", "-")
    if "," in a.seeds:
        sys.exit("use : to separate seeds (sbatch --export splits on commas)")
    out = f"{w}/outputs/{a.tag}/{safe_model}__{shard_tag}.jsonl"
    env = {"SHIFT_ROOT": w, "MODEL": a.model, "SHARD": a.shard, "PROMPTS": f"{w}/inputs/{a.prompts}",
           "OUT": out, "SEEDS": a.seeds, "PARALLEL": str(a.parallel), "OLLAMA_BIN": binp,
           "OLLAMA_MODELS": mdir, "NUM_CTX": str(a.num_ctx)}
    if a.limit:
        env["LIMIT"] = str(a.limit)
    exports = "ALL," + ",".join(f"{k}={v}" for k, v in env.items())
    cmd = (f"cd {w}/logs && sbatch --parsable --account={c['gpu_account']} --gres={c['gres']} "
           f"--time={a.time} {('--dependency=' + a.dependency) if a.dependency else ''} --job-name=shift-{a.tag}-{safe_model[:18]} --export={shlex.quote(exports)} "
           f"{w}/hpc/slurm/llm_judge.sbatch")
    code, txt = rsh(s, cmd, timeout=180)
    rec = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "site": s, "tag": a.tag,
           "model": a.model, "shard": a.shard, "limit": a.limit, "seeds": a.seeds, "time": a.time,
           "parallel": a.parallel, "rc": code, "job": next((l for l in reversed(txt.strip().splitlines()) if l.strip().split(";")[0].isdigit()), txt.strip()[-200:]) if txt else "", "out": out}
    FETCHED.mkdir(parents=True, exist_ok=True)
    with JOBS.open("a") as fh:
        fh.write(json.dumps(rec) + "\n")
    print(json.dumps(rec))


def status(a) -> None:
    for s in sites(a.sites):
        code, txt = rsh(s, "squeue -u $USER -h -o '%i %j %T %M %l %R' | grep shift || true; "
                        "sacct -u $USER -S now-1days -n -X -o JobID,JobName%30,State,Elapsed | grep shift | tail -40")
        print(f"===== {s}\n{txt}\n")


def fetch(a) -> None:
    for s in sites(a.sites):
        w = CFG["clusters"][s]["work"]
        dst = FETCHED / s
        (dst / "outputs").mkdir(parents=True, exist_ok=True)
        rc = rsync(s, f"{target(s)}:{w}/outputs/", f"{dst}/outputs/")
        rc2 = rsync(s, f"{target(s)}:{w}/logs/", f"{dst}/logs/")
        print(f"{s}: fetch rc={rc},{rc2}")


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("probe", "deploy", "status", "fetch"):
        p = sub.add_parser(name)
        p.add_argument("--sites")
        p.add_argument("--tag")
    p = sub.add_parser("submit")
    p.add_argument("--site", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--shard", default="0/1")
    p.add_argument("--tag", required=True)
    p.add_argument("--prompts", default="prompts.jsonl")
    p.add_argument("--seeds", default="11,22,33")
    p.add_argument("--parallel", type=int, default=4)
    p.add_argument("--num-ctx", type=int, default=16384)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--time", default="2:00:00")
    p.add_argument("--dependency", default="")
    p.add_argument("--ollama-bin")
    p.add_argument("--models-dir")
    a = ap.parse_args()
    {"probe": probe, "deploy": deploy, "submit": submit, "status": status, "fetch": fetch}[a.cmd](a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
