#!/bin/sh
# MC-029 — deterministic bootstrap from an empty supported Linux node.
# Idempotent; refuses (exit 2) when a mandatory kernel feature is missing.
set -eu
HERE=$(cd "$(dirname "$0")/.." && pwd)
PY=${PYTHON:-python3}
"$PY" - <<'PYEOF'
import sys
if sys.version_info < (3, 10):
    sys.exit("python >= 3.10 required")
PYEOF
cd "$(dirname "$HERE")"
"$PY" -c "import $(basename "$HERE") as m, $(basename "$HERE").backends as b, json; print(json.dumps(b.require(), indent=1))" || exit 2
command -v cc >/dev/null 2>&1 || command -v gcc >/dev/null 2>&1 || echo "WARN: no C compiler: adversarial probes cannot be built (certification will fail)"
INV39_FUZZ_ITERS=${INV39_FUZZ_ITERS:-1000} "$PY" -W ignore "$HERE/tests/run_all.py"
echo "bootstrap: OK"
