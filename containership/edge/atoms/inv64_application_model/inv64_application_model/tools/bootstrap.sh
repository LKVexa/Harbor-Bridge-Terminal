#!/usr/bin/env sh
# Day-0 bootstrap for POSIX hosts (MC-02 / MC-33). Creates an isolated venv, installs this
# package (+ optional crypto extra when an index or wheelhouse is available), then runs the
# preflight. Certification mode additionally requires PK_CORE_PATH to point at the pinned
# pk_core and fails closed otherwise.
#   usage: sh tools/bootstrap.sh [--certification] [--wheelhouse DIR]
set -eu
HERE=$(cd "$(dirname "$0")/.." && pwd)
PARENT=$(dirname "$HERE")
VENV="${INV64_VENV:-$PARENT/.inv64-venv}"
CERT=""; WHEELHOUSE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --certification) CERT="--certification" ;;
    --wheelhouse) shift; WHEELHOUSE="$1" ;;
  esac; shift
done
python3 -c 'import sys; assert (3,10) <= sys.version_info[:2] <= (3,13), sys.version' \
  || { echo "unsupported Python (need 3.10-3.13; see compatibility.json)"; exit 2; }
python3 -m venv "$VENV"
if [ -n "$WHEELHOUSE" ]; then
  "$VENV/bin/python" -m pip install --no-index --find-links "$WHEELHOUSE" "inv64-application-model[crypto]"
else
  "$VENV/bin/python" -m pip install -c "$HERE/constraints-certification.txt" "$HERE[crypto]" \
    || "$VENV/bin/python" -m pip install --no-deps "$HERE"
fi
"$VENV/bin/python" -m pip check
cd "$PARENT"
"$VENV/bin/python" -m inv64_application_model.tools.preflight $CERT --out "$HERE/evidence/PREFLIGHT.json"
