#!/usr/bin/env sh
# M01..M52-049 clean-environment CI gate.  Run from the directory containing the package.
set -eu
PKG=inv09_portable_compute_isa
python3 -m venv .ci-venv && . .ci-venv/bin/activate
pip install --require-hashes -r $PKG/requirements.lock   # lock must carry hashes in CI
python -m unittest discover -s $PKG/tests -p "test_*.py" -v
python -O -m unittest discover -s $PKG/tests -p "test_*.py"
python $PKG/tools/evidence.py static
python $PKG/tools/evidence.py tests
python $PKG/tools/evidence.py fuzz 1,2,3,4,5 40000
python $PKG/tools/evidence.py bench
python $PKG/tools/evidence.py soak 300
python $PKG/tools/linecov.py
python $PKG/tools/evidence.py sbom
python $PKG/tools/evidence.py buildmeta
python $PKG/tools/checklist_status.py
python - <<'PY'
import json,sys
v=json.load(open("inv09_portable_compute_isa/evidence/production_gate.json"))["verdict"]
print("M52:", v); sys.exit(0 if v in ("GO","CONDITIONAL_GO") else 1)
PY
