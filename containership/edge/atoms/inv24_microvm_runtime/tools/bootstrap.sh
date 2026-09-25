#!/usr/bin/env bash
# MC-017 reproducible offline bootstrap: venv + local install + standalone suite.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"
"$PY" -c 'import sys; assert sys.version_info >= (3,10), sys.version'
"$PY" -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/python" -m pip install --no-index --no-build-isolation --no-deps "$ROOT" >/dev/null 2>&1 || \
  echo "note: pip install unavailable offline; running from source tree"
cd "$ROOT"
"$ROOT/.venv/bin/python" -m unittest discover -s inv24_microvm_runtime/tests -t . -q
"$ROOT/.venv/bin/python" -O -m unittest inv24_microvm_runtime.tests.test_runtime -q
echo "standalone suite OK"
