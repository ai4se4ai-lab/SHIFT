"""RQ3 controlled injection jobs: per validated instance, one semantic and one neutral
injection into a nonlocal module (operators rotated deterministically by seed)."""
from __future__ import annotations

import json
import random
from pathlib import Path

import yaml

from shift.data.repos import load_dataset
from shift.envelope.inject import NEUTRAL, SEMANTIC, make_injection

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    import sys
    sys.path.insert(0, str(ROOT / "experiments"))
    from build_jobs import validated_instances
    cfg = yaml.safe_load(open(ROOT / "configs/study.yaml"))
    seed = cfg["injection"]["seed"]
    df = load_dataset()
    valid = sorted(i for i, w in validated_instances().items() if w == "ok")
    rnd = random.Random(seed)
    jobs, missing = [], 0
    for iid in valid:
        inst = df.loc[iid].to_dict()
        for pool in (SEMANTIC, NEUTRAL):
            ops = list(pool)
            rnd.shuffle(ops)
            inj = None
            for op in ops:                      # first operator with an eligible site
                inj = make_injection(inst, op, seed)
                if inj:
                    break
            if not inj:
                missing += 1
                continue
            jobs.append({"instance_id": iid, "label": f"inj-{inj['kind']}", "patch": inj["patch"],
                         "repo": inst["repo"], "inj_target": inj["target"], "inj_op": inj["op"],
                         "inj_line": inj["site_line"], "inj_distance": inj["distance"]})
    out = ROOT / "results/processed/jobs/injection_jobs.jsonl"
    out.write_text("".join(json.dumps(j) + "\n" for j in jobs))
    print(f"instances={len(valid)} jobs={len(jobs)} no_site={missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
