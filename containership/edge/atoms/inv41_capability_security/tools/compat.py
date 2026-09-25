"""Compatibility certification runner (Section 19, REQ-TST-006).

Runs compile + self-check + preflight + the unit/contract/security suites on
every interpreter found locally that the support matrix names, in normal and
-O mode, and records an environment fingerprint per run.  Matrix cells with
no local interpreter are recorded NOT_RUN (never PASS).  The CI workflow
(.github/workflows/ci.yml) runs the same tool on the full matrix.
Output: evidence/compat.json.
"""
from __future__ import annotations

import json
import pathlib
import platform
import shutil
import subprocess
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
SUITES = ["test_primitives.py", "test_contracts.py", "test_properties.py", "test_subsystems.py", "test_isolation.py",
          "test_governance.py"]


def run_on(exe: str) -> dict:
    fp = json.loads(subprocess.run([exe, "-c", "import json,platform,sys;print(json.dumps({'python':platform.python_version(),"
                                    "'impl':platform.python_implementation(),'os':platform.system(),'arch':platform.machine()}))"],
                                   capture_output=True, text=True).stdout)
    steps = {}
    steps["compileall"] = subprocess.run([exe, "-m", "compileall", "-q", str(PKG)], capture_output=True).returncode == 0
    for opt in ("", "-O"):
        args = [exe] + ([opt] if opt else []) + ["-B", "-m", "inv41_capability_security.selfcheck"]
        steps[f"selfcheck{opt}"] = subprocess.run(args, cwd=PKG.parent, capture_output=True).returncode == 0
    steps["preflight"] = subprocess.run([exe, "-B", "-m", "inv41_capability_security.preflight"], cwd=PKG.parent,
                                        capture_output=True).returncode == 0
    for s in SUITES:
        steps[s] = subprocess.run([exe, "-B", s], cwd=PKG / "tests", capture_output=True, text=True,
                                  env={"INV41_ITER": "150", "INV41_RACE_ROUNDS": "10", "PATH": "/usr/bin:/bin"}).returncode == 0
    return {"fingerprint": fp, "steps": steps, "result": "PASS" if all(steps.values()) else "FAIL"}


def main() -> int:
    matrix = json.loads((PKG / "contracts" / "SUPPORT_MATRIX.json").read_text())
    cells = []
    for py in matrix["python"]["supported"]:
        exe = shutil.which(f"python{py}")
        for os_name in matrix["os"]["supported"]:
            for arch in matrix["arch"]["supported"]:
                here = exe and platform.system() == os_name and platform.machine() == arch
                if here:
                    r = run_on(exe)
                    r.update(cell={"python": py, "os": os_name, "arch": arch})
                    cells.append(r)
                else:
                    cells.append({"cell": {"python": py, "os": os_name, "arch": arch}, "result": "NOT_RUN",
                                  "reason": "interpreter/platform not available in this environment"})
    # negative: an unsupported version must be refused by preflight
    neg = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, %r); from inv41_capability_security import preflight;"
                          "r=preflight.run(version_info=(3,8,0)); sys.exit(0 if not r['ok'] else 1)" % str(PKG.parent)])
    out = {"schema": "INV41_COMPAT/1", "cells": cells, "unsupported_refused": neg.returncode == 0,
           "summary": {k: sum(c["result"] == k for c in cells) for k in ("PASS", "FAIL", "NOT_RUN")}}
    (PKG / "evidence").mkdir(exist_ok=True)
    (PKG / "evidence" / "compat.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["summary"]), "unsupported_refused=", out["unsupported_refused"])
    return 0 if out["summary"]["FAIL"] == 0 and out["unsupported_refused"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
