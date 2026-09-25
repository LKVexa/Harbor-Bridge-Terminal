#!/usr/bin/env sh
# MC-59 CI: compile, unit/contract/security/resilience suites, schema drift, SBOM, RTM,
# bench gate, checklist status, exit gate.  Writes evidence/ci_result.json.
# The exit gate is expected to be NO_GO; CI records it and does not fail on it.
set -u
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"
export PYTHONDONTWRITEBYTECODE=1
fail=0; steps=""
step() { name="$1"; shift; if "$@" >/tmp/sch01_ci_$name.log 2>&1; then r=PASS; else r=FAIL; fail=1; fi
         steps="$steps{\"step\":\"$name\",\"result\":\"$r\"},"; echo "$name: $r"; }
step compile "$PY" -m compileall -q -x 'tests|tools' .
step unit "$PY" -B -m unittest discover -s tests
step schemas "$PY" -B tools/gen_schemas.py --check
step sbom "$PY" -B tools/sbom.py
step rtm "$PY" -B tools/rtm.py
step bench "$PY" -B tools/bench.py --out evidence/bench.json
"$PY" -B tools/bench.py --gate evidence/bench.json > evidence/bench_gate.json; echo "bench_gate: $(cat evidence/bench_gate.json | cut -c1-60)"
step checklist "$PY" -B tools/checklist_status.py
"$PY" -B tools/verify_master_provenance.py >/dev/null; echo "provenance rc=$? (3 = EVIDENCE_GAP, expected)"
v=PASS; [ $fail -ne 0 ] && v=FAIL
printf '{"schema":"PK_CI_RESULT/1","verdict":"%s","steps":[%s],"python":"%s"}\n' "$v" "${steps%,}" "$($PY -c 'import platform;print(platform.python_version())')" > evidence/ci_result.json
"$PY" -B tools/exit_gate.py; echo "exit_gate rc=$? (2 = NO_GO)"
"$PY" -B tools/evidence_bundle.py
"$PY" -B tools/sbom.py >/dev/null   # refresh checksums last
exit $fail
