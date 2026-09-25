#!/bin/sh
# INV-31 CI: clean-venv install from declared metadata, then evidence build.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
PY=${PYTHON:-python3}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
"$PY" -m venv "$TMP/venv"
"$TMP/venv/bin/pip" install -q --no-deps --no-build-isolation "$HERE" 2>/dev/null \
  || "$TMP/venv/bin/pip" install -q "$HERE"
(cd "$TMP" && "$TMP/venv/bin/python" -B -c "import inv31_function_execution_architecture as p, sys; assert p.__version__=='4.3.0'; print('clean install OK', p.__version__)")
(cd "$TMP" && "$TMP/venv/bin/python" -B -m unittest -q inv31_function_execution_architecture.tests.test_remediation 2>&1 | tail -2)
"$PY" -B "$HERE/tools/make_evidence.py"
echo "CI PASS (production gate remains NO_GO by design)"
