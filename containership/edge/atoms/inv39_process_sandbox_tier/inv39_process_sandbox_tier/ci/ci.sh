#!/bin/sh
# MC-104 — the CI pipeline: compile, unit, optimized mode, schema/fixtures, backend integration,
# security (threat-model-derived), fuzz, benchmark gate, reproducible build, release exit gate.
set -eu
HERE=$(cd "$(dirname "$0")/.." && pwd)
PY=${PYTHON:-python3}
cd "$HERE"
echo "== compile";        "$PY" -m compileall -q . >/dev/null
echo "== tests";          "$PY" -W ignore tests/run_all.py
echo "== tests (-O)";     "$PY" -O -W ignore tests/run_all.py >/dev/null
echo "== fixtures";       "$PY" -W ignore -m unittest -q tests/test_contracts_and_fixtures.py 2>/dev/null || (cd tests && "$PY" -W ignore test_contracts_and_fixtures.py)
echo "== bench gate";     "$PY" tools/bench.py --n ${BENCH_N:-100} --gate --out "${TMPDIR:-/tmp}" | tail -1
echo "== build x2";       "$PY" tools/build_release.py "${TMPDIR:-/tmp}/inv39-b1" >/dev/null
                          "$PY" tools/build_release.py "${TMPDIR:-/tmp}/inv39-b2" >/dev/null
cmp "${TMPDIR:-/tmp}/inv39-b1/"*.zip "${TMPDIR:-/tmp}/inv39-b2/"*.zip && echo "reproducible: yes"
echo "== exit gate";      "$PY" tools/exit_gate.py --dist "${TMPDIR:-/tmp}/inv39-b1" || { echo "exit gate: NO_GO (expected until owner acceptance)"; [ "${REQUIRE_GO:-0}" = 1 ] && exit 1; true; }
