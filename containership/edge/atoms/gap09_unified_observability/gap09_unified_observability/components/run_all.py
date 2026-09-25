"""One deterministic entry point: tests -> checklist engine -> engine tests ->
doc check -> SBOM.  Exit 0 only if every stage passes; the doc check's
MASTER.md finding is expected and reported (exit 3 = INCOMPLETE, never PASS).
Run from anywhere:  python -B gap09_unified_observability/components/run_all.py
"""
from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = [sys.executable, "-B"]


def stage(name, argv, cwd=HERE):
    r = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
    print(f"[{'PASS' if r.returncode == 0 else 'rc=' + str(r.returncode)}] {name}: {' | '.join(tail)}")
    return r.returncode


def main() -> int:
    rc = []
    rc.append(stage("unit/integration tests", PY + ["-m", "unittest", "discover", "-s", "tests", "-t", "tests"]))
    rc.append(stage("checklist engine (1,440 checks)", PY + ["checklist/engine.py", "checklist/GAP09_MISSING_COMPONENTS_CHECKLIST.md"]))
    rc.append(stage("engine falsifiers", PY + ["-m", "unittest", "test_checklist_engine"], cwd=os.path.join(HERE, "tests")))
    doc = stage("doc check (60: MASTER.md)", PY + ["tools/doc_check.py"])
    rc.append(stage("SBOM", PY + ["tools/sbom.py"]))
    if any(rc):
        return 1
    return 3 if doc else 0


if __name__ == "__main__":
    sys.exit(main())
