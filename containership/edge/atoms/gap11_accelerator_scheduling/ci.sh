#!/usr/bin/env sh
# GAP-11 v4.3.0 CI gate (GAP11-P2-42). Any failing stage exits non-zero.
set -eu
cd "$(dirname "$0")"
export PYTHONDONTWRITEBYTECODE=1
echo "[1/6] compile";           python3 -B -c "import sys; [compile(open(f).read(), f, 'exec') for f in sys.argv[1:]]" allocator.py gap11_control/*.py gap11_control/tests/*.py tools/*.py   # not py_compile: it writes .pyc even under -B
echo "[2/6] v4.2.0 core suite"; python3 -B tests/test_allocator.py -q 2>&1 | tail -1
echo "[3/6] python -O core";    python3 -B -O tests/test_allocator.py -q 2>&1 | tail -1
echo "[4/6] build artifacts";   python3 -B tools/build_artifacts.py
echo "[5/6] tests + checklist"; python3 -B tools/run_checklist.py > evidence/ci_summary.json
echo "[5b] overlay under -O";  (cd gap11_control/tests && python3 -B -O -m unittest -q test_state test_hardware test_security test_wire test_scheduler test_observability test_verification 2>&1 | tail -1)
echo "[6/6] manifest";          sha256sum -c MANIFEST.sha256 --quiet
python3 -B - <<'P'
import json,sys
b=json.load(open("evidence/EXIT_BUNDLE.json"))
print("verdict:", b["verdict"], "| totals:", b["checklist_totals"])
# CI passes on a clean run; the production verdict is reported, not gated here (it is NO_GO by construction until humans act).
P
