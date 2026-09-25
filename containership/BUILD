#!/bin/sh
# Unikernel_Containership/BUILD -- extract + build the four engines from hold/, install the hull, register berth faces
# Offline. Nothing here opens a socket (NETWORK=deny, BACKEND=none).
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"
exec "$PY" -B uc.py build "$@"
