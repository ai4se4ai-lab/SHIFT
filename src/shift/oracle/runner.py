"""Execution oracle on official SWE-bench environments (Docker, native arch).

One container per analysed patch. The container is prepared once (test patch
applied and committed), then each *configuration* (a set of file contents) is
written, the instance's test command is run, and the log is parsed with the
official SWE-bench parser for that repository. Between configurations the
working tree is hard-reset to the prepared commit.
"""
from __future__ import annotations

import io
import json
import shlex
import subprocess
import tarfile
import time
import uuid
from dataclasses import dataclass, field

from swebench.harness.constants import (END_TEST_OUTPUT, MAP_REPO_VERSION_TO_SPECS,
                                        START_TEST_OUTPUT)
from swebench.harness.log_parsers import MAP_REPO_TO_PARSER
from swebench.harness.test_spec.python import get_test_directives
from swebench.harness.test_spec.test_spec import make_test_spec

PASS_STATES = {"PASSED", "XFAIL"}


@dataclass
class RunResult:
    status: dict[str, str]          # test id -> PASSED/FAILED/ERROR/SKIPPED/...
    seconds: float
    timed_out: bool
    exit_code: int
    log_tail: str = ""


@dataclass
class Verdict:
    goal_ok: bool
    pres_ok: bool
    failing_goal: list[str] = field(default_factory=list)
    failing_pres: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.goal_ok and self.pres_ok


def image_name(instance_id: str, arch: str = "arm64") -> str:
    return f"sweb.eval.{arch}.{instance_id.lower()}:latest"


def django_label(path: str) -> str:
    d = path[:-3] if path.endswith(".py") else path
    d = d[len("tests/"):] if d.startswith("tests/") else d
    return d.replace("/", ".")


class InstanceOracle:
    """Context manager owning one container for one SWE-bench instance."""

    def __init__(self, instance: dict, timeout: int = 900, cpus: float = 2.0):
        self.inst = instance
        self.repo = instance["repo"]
        self.spec = MAP_REPO_VERSION_TO_SPECS[self.repo][instance["version"]]
        self.timeout = timeout
        self.cpus = cpus
        self.name = f"shift-{instance['instance_id'][:40]}-{uuid.uuid4().hex[:8]}".replace("__", "-")
        self.test_spec = make_test_spec(instance)
        self.default_directives = get_test_directives(instance)
        self.calls = 0
        self.oracle_seconds = 0.0

    # ------------------------------------------------------------ container plumbing
    def _exec(self, script: str, timeout: int | None = None) -> tuple[int, str, bool]:
        cmd = ["docker", "exec", self.name, "bash", "-lc", script]
        try:
            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                               errors="replace", timeout=timeout or self.timeout)
            return r.returncode, r.stdout, False
        except subprocess.TimeoutExpired as e:
            out = (e.stdout or b"")
            out = out.decode(errors="replace") if isinstance(out, bytes) else out
            # The container runs only the oracle's tests: kill every test process, including
            # interpreter children that do not match the launcher's name (e.g. SymPy's _test).
            subprocess.run(["docker", "exec", self.name, "bash", "-lc",
                            "pkill -9 -f runtests; pkill -9 -f bin/test; pkill -9 -f pytest; pkill -9 python"],
                           capture_output=True)
            return 124, out, True

    def __enter__(self) -> "InstanceOracle":
        subprocess.run(["docker", "run", "-d", "--name", self.name, "--network", "none",
                        f"--cpus={self.cpus}", "--memory=8g", image_name(self.inst["instance_id"]),
                        "sleep", "infinity"], check=True, capture_output=True)
        env = self._env_prefix(setup=True)
        tp = self.inst["test_patch"]
        script = (f"{env} && git config --global user.email shift@local && "
                  f"git config --global user.name shift && git config --global --add safe.directory /testbed && "
                  f"git status --porcelain | head -5; "
                  f"git apply -v - <<'EOF_SHIFT_TP'\n{tp}\nEOF_SHIFT_TP\n"
                  f"git add -A && git commit -qm shift-test-patch --no-verify")
        code, out, _ = self._exec(script, timeout=300)
        if code != 0:
            self.__exit__(None, None, None)
            raise RuntimeError(f"test patch failed for {self.inst['instance_id']}: {out[-800:]}")
        return self

    def __exit__(self, *exc) -> None:
        subprocess.run(["docker", "rm", "-f", self.name], capture_output=True)

    def _env_prefix(self, setup: bool = False) -> str:
        """Shell prefix for test runs. One-time setup commands of the instance spec (e.g.
        locale generation) run once when the container is prepared; environment exports
        are repeated for every run."""
        parts = ["source /opt/miniconda3/bin/activate", "conda activate testbed", "cd /testbed"]
        for c in self.spec.get("eval_commands", []):
            if setup or c.strip().startswith("export "):
                parts.append(c)
        return " && ".join(parts)

    # ------------------------------------------------------------ configurations
    def write_config(self, files: dict[str, str | None], protected: set[str] = frozenset()) -> None:
        """Reset to prepared state, then materialise file contents (None = delete)."""
        self._exec("cd /testbed && git reset -q --hard && git clean -fdq -e __pycache__ -e '*.pyc'", timeout=120)
        buf = io.BytesIO()
        deletions = []
        with tarfile.open(fileobj=buf, mode="w") as tar:
            for path, content in files.items():
                if path in protected:           # test-patch files are owned by the oracle
                    continue
                if content is None:
                    deletions.append(path)
                    continue
                data = content.encode("utf-8", errors="surrogateescape")
                ti = tarfile.TarInfo(path)
                ti.size = len(data)
                ti.mtime = int(time.time())
                ti.mode = 0o644
                tar.addfile(ti, io.BytesIO(data))
        buf.seek(0)
        subprocess.run(["docker", "cp", "-", f"{self.name}:/testbed"], input=buf.read(),
                       check=True, capture_output=True)
        if deletions:
            self._exec("cd /testbed && rm -f " + " ".join(shlex.quote(d) for d in deletions), timeout=60)

    def run_tests(self, directives: list[str] | None = None) -> RunResult:
        directives = directives if directives is not None else self.default_directives
        cmd = " ".join([self.spec["test_cmd"], *directives])
        script = f"{self._env_prefix()} && echo '{START_TEST_OUTPUT}' && {cmd}; echo '{END_TEST_OUTPUT}'"
        t0 = time.time()
        code, out, to = self._exec(script)
        dt = time.time() - t0
        self.calls += 1
        self.oracle_seconds += dt
        body = out
        if START_TEST_OUTPUT in out:
            body = out.split(START_TEST_OUTPUT, 1)[1].split(END_TEST_OUTPUT, 1)[0]
        status = MAP_REPO_TO_PARSER[self.repo](body, self.test_spec)
        return RunResult(status, dt, to, code, out[-1500:])

    def verdict(self, rr: RunResult, f2p: list[str], p2p: list[str]) -> Verdict:
        fg = [t for t in f2p if rr.status.get(t) not in PASS_STATES]
        fp = [t for t in p2p if rr.status.get(t) not in PASS_STATES]
        return Verdict(not fg and not rr.timed_out, not fp and not rr.timed_out, fg, fp)

    def protected_paths(self) -> set[str]:
        import re
        return set(re.findall(r"diff --git a/.* b/(.*)", self.inst["test_patch"]))


def result_to_json(rr: RunResult) -> str:
    return json.dumps({"status": rr.status, "seconds": round(rr.seconds, 2),
                       "timed_out": rr.timed_out, "exit": rr.exit_code})
