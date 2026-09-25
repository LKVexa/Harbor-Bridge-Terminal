#!/usr/bin/env sh
# INV-65 CI entry point (M29). Run from the directory that CONTAINS inv65_capability_providers/.
set -eu
PY=${PYTHON:-python3}
export PYTHONDONTWRITEBYTECODE=1
$PY -m compileall -q inv65_capability_providers
$PY -B -W ignore -m unittest discover -s inv65_capability_providers/tests -t .
$PY -O -B -W ignore -m unittest discover -s inv65_capability_providers/tests -t .
$PY -B inv65_capability_providers/tools/check_rtm.py
$PY -B -m inv65_capability_providers.fuzz.harness --iterations 6000 --seed "${FUZZ_SEED:-65}"
$PY -B -m inv65_capability_providers.benchmarks.harness --soak-s 3
# release gate writes evidence; NO_GO is reported, not hidden
$PY -B -m inv65_capability_providers.tools.release_gate --quick
