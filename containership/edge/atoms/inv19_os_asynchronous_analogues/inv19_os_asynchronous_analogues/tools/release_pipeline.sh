#!/usr/bin/env bash
# Full INV-19 evidence pipeline, in dependency order.  Exit code = gate verdict (0 GO, 2 BLOCKED, 1 NO_GO).
set -u
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1
SOAK_S="${SOAK_S:-900}"
python3 tools/certify.py record                 # this host's cell
python3 tools/bench.py                          # perf + regression decision
python3 tools/soak.py --duration "$SOAK_S"      # soak/burst/fleet/disaster
python3 tools/certify.py matrix
python3 tools/supply_chain.py all               # SBOM, vuln scan, signed manifest, verify
python3 tools/run_gate.py >/dev/null            # first pass (self-test needs a bundle)
python3 tools/run_gate.py --self-test
python3 tools/run_gate.py; rc=$?
python3 tools/run_gate.py --verify
exit $rc
