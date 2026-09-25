#!/usr/bin/env sh
# RG-03 local CI: every stage the release gate relies on, in order. Exit non-zero on first failure,
# except the final acceptance gate, whose NO_GO is reported but expected until blockers close.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
PY=${PYTHON:-python3}
cd "$HERE"
echo "== compile";           $PY -m compileall -q .
echo "== schema drift";      $PY tools/gen_schemas.py --check
echo "== unit+integration";  $PY tools/run_tests.py --out test-report.json
echo "== optimized mode";    $PY -O tools/run_tests.py --out /tmp/inv57-test-report-O.json
echo "== benchmark";         $PY tools/benchmark.py --out evidence/benchmark-ci --samples 50 \
                               --baseline evidence/benchmark/summary.json --max-regression 1.0
echo "== package"
TMP=$(mktemp -d)
cp -r "$HERE" "$TMP/src"; rm -rf "$TMP/src/test-report.json" "$TMP/src/evidence/benchmark-ci" "$TMP/src/acceptance-manifest.json"
find "$TMP/src" -name __pycache__ -prune -exec rm -rf {} +
$PY -m venv "$TMP/venv"
# Build with the venv's own setuptools (>=68 required by pyproject), never the distro-patched
# system copy (Debian's breaks with AttributeError: install_layout).
"$TMP/venv/bin/python" -c 'import setuptools,sys;v=int(setuptools.__version__.split(".")[0]);sys.exit(v<68)'
# Reproducibility: fixed SOURCE_DATE_EPOCH, build twice from clean trees, require identical bytes.
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-1790000000}
"$TMP/venv/bin/pip" wheel -q --no-deps --no-build-isolation -w "$TMP/dist" "$TMP/src"
rm -rf "$TMP/src/build" "$TMP"/src/*.egg-info
"$TMP/venv/bin/pip" wheel -q --no-deps --no-build-isolation -w "$TMP/dist2" "$TMP/src"
cmp "$TMP"/dist/*.whl "$TMP"/dist2/*.whl && echo "reproducible wheel: identical across two builds"
"$TMP/venv/bin/pip" install -q "$TMP"/dist/*.whl
SITE=$("$TMP/venv/bin/python" -c 'import sysconfig;print(sysconfig.get_paths()["purelib"])')
(cd "$TMP" && PYTHONDONTWRITEBYTECODE=1 "$TMP/venv/bin/python" -B -m unittest discover -s "$SITE/inv57_durable_execution/tests" -t "$SITE" -q)
PYTHONDONTWRITEBYTECODE=1 "$TMP/venv/bin/inv57" errors >/dev/null
sha256sum "$TMP"/dist/*.whl | tee "$HERE/evidence/wheel.sha256"
"$TMP/venv/bin/pip" uninstall -q -y inv57-durable-execution
"$TMP/venv/bin/python" -c 'import importlib.util,sys;sys.exit(importlib.util.find_spec("inv57_durable_execution") is not None)'
echo "uninstall clean"
echo "== acceptance gate";   PYTHONPATH="$HERE/.." $PY -m inv57_durable_execution gate --out acceptance-manifest.json || echo "gate: NO_GO (expected; see blockers)"
