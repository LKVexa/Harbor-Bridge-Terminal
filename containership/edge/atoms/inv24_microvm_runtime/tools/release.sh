#!/usr/bin/env bash
# Full evidence -> gate -> closure-report sequence (MC-054/MC-064). Exit code is the gate's.
set -uo pipefail
cd "$(dirname "$0")/.."
python3 tools/run_evidence.py >/dev/null || { echo "evidence run failed"; exit 3; }
python3 tools/production_gate.py >/dev/null      # first pass creates evidence/production-gate.json
python3 tools/run_evidence.py >/dev/null          # re-resolve traceability now that the gate file exists
python3 tools/production_gate.py; rc=$?
python3 tools/render_closure.py
python3 tools/production_gate.py --verify evidence/production-gate.json
exit $rc
