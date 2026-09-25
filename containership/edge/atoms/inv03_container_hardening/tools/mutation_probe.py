"""Falsifier: plant known defects in a scratch copy and REQUIRE the suite to fail.

A suite that stays green with a defect planted is not evidence. Exit 0 only if
every mutant is killed. Usage: python3 -B tools/mutation_probe.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUTANTS = [
    ("hardening/controls.py", 'if _m(c.get("securityContext")).get("privileged") is not False]',
     'if _m(c.get("securityContext")).get("privileged") is True]', "omitted privileged admitted"),
    ("hardening/controls.py", 'elif norm.endswith(RUNTIME_SOCKET_SUFFIXES):', 'elif False:', "runtime socket admitted"),
    ("hardening/engine.py", 'if exc_rec and name != "sandbox-runtime":', 'if exc_rec:', "sandbox waivable"),
    ("hardening/authority.py", 'if p.subject == r["requester"]:\n                raise AuthError("SEPARATION_OF_DUTIES", "requester cannot approve own exception")',
     'pass', "self-approval allowed"),
    ("hardening/baseline.py", 'if artifact["digest"] != "sha256:" + hashlib.sha256(payload).hexdigest():',
     'if False:', "digest not checked"),
    ("hardening/core.py", 'if rec.get("prev") != prev:', 'if False:', "chain link unchecked"),
    ("hardening/core.py", 'if self._last is not None and t < self._last - self._max_backstep:', 'if False:',
     "clock rollback accepted"),
    ("hardening/engine.py", 'if out["admit"]:\n                out = self._deny(Reason.DEPENDENCY_FAILURE',
     'if False:\n                out = self._deny(Reason.DEPENDENCY_FAILURE', "admit without audit"),
    ("hardening/runtime.py", 'if rep["downgraded"]:', 'if False:', "runtime downgrade accepted"),
    ("hardening/baseline.py", 'if cur is not None and not set(v) <= set(cur):', 'if False:', "overlay may loosen sets"),
]


def run_suite(root: str) -> int:
    env = dict(os.environ, INV03_FUZZ_ITER="300", PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, "-B", "-m", "unittest", "-q", "test_h_controls", "test_h_integrity",
                           "test_h_engine", "test_h_certification"], cwd=os.path.join(root, "inv03_container_hardening",
                                                                                      "tests"),
                          env=env, capture_output=True).returncode


def main() -> int:
    survivors = []
    for rel, old, new, label in MUTANTS:
        with tempfile.TemporaryDirectory() as d:
            dst = os.path.join(d, "inv03_container_hardening")
            shutil.copytree(PKG, dst, ignore=shutil.ignore_patterns("__pycache__", "*.zip"))
            path = os.path.join(dst, rel)
            with open(path) as fh:
                src = fh.read()
            if old not in src:
                print(f"STALE   {label}: anchor not found in {rel}")
                survivors.append(label)
                continue
            with open(path, "w") as fh:
                fh.write(src.replace(old, new, 1))
            rc = run_suite(d)
            print(("KILLED " if rc != 0 else "SURVIVED") + f"  {label}")
            if rc == 0:
                survivors.append(label)
    print(f"{len(MUTANTS) - len(survivors)}/{len(MUTANTS)} mutants killed")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
