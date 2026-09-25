#!/usr/bin/env bash
# GAP-12 CI pipeline (G12-I105).  Every lane runs against ONE source revision,
# identified by SOURCE_DIGEST, and writes machine-readable results under
# evidence/out/.  The final gate treats a skipped or missing mandatory lane as
# NOT-EVIDENCED (never PASS).  Linux + CPython >= 3.11.  The privileged lab lane
# needs root (network namespaces, veth, iptables).
set -u
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
OUT=evidence/out
mkdir -p "$OUT"
export PYTHONDONTWRITEBYTECODE=1 SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-1790035200}
SOURCE_DIGEST=$($PY -B -c "import sys; sys.path.insert(0,'evidence'); import run_tests; print(run_tests.source_digest())")
echo "SOURCE_DIGEST=$SOURCE_DIGEST"
jobs=()
record() { jobs+=("{\"job\":\"$1\",\"mandatory\":$2,\"status\":\"$3\",\"source_digest\":\"$SOURCE_DIGEST\"}"); }

# LANE fast: unit / contract / fuzz / concurrency tests (unprivileged)
if $PY -B evidence/run_tests.py --out "$OUT/test_results.json"; then record unit true PASS; else record unit true FAIL; fi

# LANE privileged-lab: kernel NAT lab (netns + veth + iptables)
if [ "$(id -u)" = "0" ]; then
  $PY -B lab/scenarios.py --out "$OUT/lab"; rc=$?
  case $rc in 0) record lab true PASS;; 3) record lab true NOT-RUN;; *) record lab true FAIL;; esac
else
  record lab true NOT-RUN
fi

# LANE bench: performance measurements with declared budgets
if $PY -B evidence/bench.py --out "$OUT/bench.json"; then record bench true PASS; else record bench true FAIL; fi

# LANE release: reproducible build twice, SBOM + provenance bound to the artifact
if $PY -B ops/build.py --check && $PY -B ops/build.py --out dist >/dev/null; then
  ART=$(ls dist/*.zip | head -1)
  $PY -B ops/sbom.py --artifact "$ART" --out "$OUT" --tests-results "$OUT/test_results.json" && record release true PASS || record release true FAIL
else
  record release true FAIL
fi

# LANE gate: evaluate all 2,420 checklist items from the evidence above
printf '[%s]\n' "$(IFS=,; echo "${jobs[*]}")" > "$OUT/ci_jobs.json"
$PY -B evidence/evaluate.py --out "$OUT" && $PY -B ops/status.py
$PY -B -c "
import json,sys; sys.path.insert(0,'evidence'); import ci_gate
d=ci_gate.decide(json.load(open('$OUT/ci_jobs.json'))); json.dump(d,open('$OUT/ci_gate.json','w'),indent=1); print('CI LANES (not the production gate)',d)
sys.exit(0 if d['decision']=='PASS' else 1)"
