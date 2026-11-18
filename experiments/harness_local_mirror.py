"""Run the official SWE-bench 4.0.4 evaluation, cloning repositories from local mirrors.

Identical to `python -m swebench.harness.run_evaluation` (same CLI) except that
instance image builds clone from a read-only `git daemon` on the Docker bridge
(git://172.17.0.1/<owner>__<name>.git) instead of github.com. The mirrors are
bare clones of the same upstream repositories and every build still resets to
the instance's pinned base commit, so the resulting environments are unchanged.
"""
import os
import runpy
import sys
from pathlib import Path

import swebench.harness.test_spec.test_spec as ts

ROOT = Path(__file__).resolve().parents[1]
MIRROR = os.environ.get("SHIFT_GIT_MIRROR", "git://172.17.0.1")
READY = set(os.environ.get("SHIFT_MIRRORED", "django/django,sympy/sympy").split(","))
_orig = ts.make_repo_script_list


def make_repo_script_list(specs, repo, repo_directory, base_commit, env_name):
    lines = _orig(specs, repo, repo_directory, base_commit, env_name)
    if repo in READY:
        url = f"{MIRROR}/{repo.replace('/', '__')}.git"
        lines = [l.replace(f"https://github.com/{repo}", url) for l in lines]
    return lines


ts.make_repo_script_list = make_repo_script_list

if __name__ == "__main__":
    import swebench.harness.run_evaluation as re_mod
    sys.argv[0] = re_mod.__file__
    # Execute the official module as __main__ in this interpreter (patch already applied).
    sys.modules.pop("swebench.harness.run_evaluation", None)
    runpy.run_module("swebench.harness.run_evaluation", run_name="__main__", alter_sys=True)
