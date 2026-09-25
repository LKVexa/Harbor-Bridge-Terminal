#!/usr/bin/env sh
# Deterministic bootstrap from an empty node (component 33).
# Usage: tools/bootstrap.sh [extra ...]   e.g. tools/bootstrap.sh encryption kafka
set -eu
HERE=$(cd "$(dirname "$0")/.." && pwd)
PY=${PYTHON:-python3}
"$PY" -c 'import sys; assert sys.version_info >= (3, 10), "Python >= 3.10 required"'
"$PY" -m venv "$HERE/.venv"
. "$HERE/.venv/bin/activate"
for extra in "$@"; do
  pin=$(grep -E "extra: $extra\b" "$HERE/requirements-lock.txt" | awk '{print $1}')
  [ -n "$pin" ] || { echo "unknown extra: $extra"; exit 2; }
  pip install --require-virtualenv "$pin"
done
cd "$(dirname "$HERE")"
python -B -m unittest discover -s "$HERE/tests" -p 'test_*.py'
python -B "$HERE/tools/gen_evidence.py"
echo "bootstrap complete: see $HERE/evidence/exit_gate.json"
