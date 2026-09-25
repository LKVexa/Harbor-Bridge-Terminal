#!/bin/sh
# CI pipeline (component 66). Run from the folder that CONTAINS inv15_new_asynchronous_abi.
# Exit 0 only if every stage passes. No stage is skippable by flag.
set -eu
P=inv15_new_asynchronous_abi
export PYTHONDONTWRITEBYTECODE=1
echo "== compile";      python3 -m compileall -q "$P" >/dev/null && find "$P" -name __pycache__ -prune -exec rm -rf {} +
echo "== bindings";     python3 -B "$P/tools/bindgen.py" --check
echo "== vectors";      python3 -B "$P/tools/vectors.py" --check
echo "== interop";      python3 -B "$P/tools/interop.py" >/dev/null
for t in "$P"/tests/test_*.py; do
  echo "== $t";         python3 -B "$t" 2>&1 | tail -1
  echo "== $t (-O)";    python3 -B -O "$t" 2>&1 | tail -1
done
echo "== manifest";     (cd "$P" && sha256sum -c --quiet MANIFEST.sha256)
echo "CI PASS"
