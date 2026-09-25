#!/bin/sh
# vm_small/DF_Xtra_Large/BUILD -- delegates to the ship (uc.py build). Offline; NETWORK=deny.
set -eu
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PY="${PYTHON:-python3}"
exec "$PY" -B "$HERE/../../../uc.py" build "$@"
