#!/bin/sh
# vm_xtra_large/DF_Fabric/BUILD -- delegates to the ship (uc.py build). Offline; NETWORK=deny.
set -eu
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PY="${PYTHON:-python3}"
exec "$PY" -B "$HERE/../../../uc.py" build "$@"
