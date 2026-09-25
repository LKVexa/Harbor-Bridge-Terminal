#!/bin/sh
# Local equivalent of .github/workflows/ci.yml (run from the directory containing the package).
set -e
PY=${PY:-python3}
PKG=$(basename "$(cd "$(dirname "$0")" && pwd)")
$PY "$PKG/tools/run_tests.py"
$PY -O "$PKG/tests/test_future.py"
$PY "$PKG/tools/api_snapshot.py"
$PY "$PKG/tools/verify.py" "$PKG"
$PY -m "$PKG" gate
