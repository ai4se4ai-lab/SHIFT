#!/usr/bin/env python3
"""Stdlib-only Ollama client for SHIFT LLM-judge jobs (runs on GPU compute nodes).

Reads prompts JSONL, sends every (prompt, seed) pair to a node-local Ollama
server with structured-output schema, and appends one JSON line per response,
including raw text, timing and token counts. Resumable: keys already present in
the output are skipped. Prompts can be sharded with --shard i/n.
"""
import argparse
import concurrent.futures as cf
import json
import os
import sys
import time
import urllib.request


def call(host, model, rec, seed, opts, timeout):
    body = {"model": model, "stream": False, "format": rec["schema"],
            "messages": [{"role": "system", "content": rec["system"]},
                         {"role": "user", "content": rec["user"]}],
            "options": dict(opts, seed=seed)}
    if "gpt-oss" in model:
        body["think"] = "low"
    req = urllib.request.Request(f"{host}/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read())
        err = None
    except Exception as e:  # recorded as a failed generation, never silently dropped
        resp, err = {}, f"{type(e).__name__}: {e}"
    msg = resp.get("message", {}) if isinstance(resp, dict) else {}
    return {"key": rec["key"], "model": model, "seed": seed, "prompt_sha256": rec["sha256"],
            "content": msg.get("content", ""), "thinking": msg.get("thinking", ""),
            "error": err, "wall_s": round(time.time() - t0, 2),
            "eval_count": resp.get("eval_count"), "prompt_eval_count": resp.get("prompt_eval_count"),
            "eval_duration_ns": resp.get("eval_duration"), "total_duration_ns": resp.get("total_duration"),
            "host": os.uname().nodename, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--seeds", default="11,22,33")
    ap.add_argument("--host", default="http://127.0.0.1:11434")
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--num-ctx", type=int, default=16384)
    ap.add_argument("--num-predict", type=int, default=2048)
    ap.add_argument("--temperature", type=float, default=0.2)
    a = ap.parse_args()
    i, n = map(int, a.shard.split("/"))
    prompts = [json.loads(l) for l in open(a.prompts) if l.strip()]
    prompts = [p for k, p in enumerate(prompts) if k % n == i]
    if a.limit:
        prompts = prompts[: a.limit]
    seeds = [int(s) for s in a.seeds.replace(":", ",").split(",") if s]
    done = set()
    if os.path.exists(a.out):
        for l in open(a.out):
            try:
                r = json.loads(l)
                if not r.get("error"):
                    done.add((r["key"], r["seed"]))
            except json.JSONDecodeError:
                pass
    todo = [(p, s) for s in seeds for p in prompts if (p["key"], s) not in done]
    opts = {"temperature": a.temperature, "top_p": 0.9, "num_ctx": a.num_ctx, "num_predict": a.num_predict}
    print(f"model={a.model} shard={a.shard} prompts={len(prompts)} todo={len(todo)}", flush=True)
    t0, k = time.time(), 0
    with open(a.out, "a") as fh, cf.ThreadPoolExecutor(a.parallel) as ex:
        futs = [ex.submit(call, a.host, a.model, p, s, opts, a.timeout) for p, s in todo]
        for f in cf.as_completed(futs):
            r = f.result()
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            k += 1
            if k % 20 == 0 or k == len(todo):
                el = time.time() - t0
                print(f"{k}/{len(todo)} done, {el:.0f}s, {k / max(el, 1e-9):.3f} gen/s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
