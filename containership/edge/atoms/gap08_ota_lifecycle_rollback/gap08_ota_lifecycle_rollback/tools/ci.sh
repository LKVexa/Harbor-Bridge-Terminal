#!/usr/bin/env sh
# GAP-08 CI gate: compile, full suite (incl. python -O parity), evidence bundle, evidence verification.
set -eu
cd "$(dirname "$0")/.."
python3 -m compileall -q .
( cd tests && python3 -m unittest discover -p 'test_*.py' -q )
( cd tests && python3 -O -m unittest discover -p 'test_*.py' -q )
python3 tools/checklist_status.py --check
python3 tools/release_evidence.py build ${GAP08_RELEASE_KEY:+--sign-key-env GAP08_RELEASE_KEY}
python3 tools/release_evidence.py verify
echo "CI gate passed (note: release remains non-releasable while CHECKLIST_STATUS has open P0 items)"
