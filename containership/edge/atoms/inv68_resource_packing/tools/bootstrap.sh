#!/usr/bin/env sh
# INV-68 clean-environment bootstrap (MC-12). Offline-aware: no network unless --online.
# Usage: tools/bootstrap.sh [--online] [--certification] [--state-dir DIR]
# Exit: 0 ready, 1 preflight failed, 2 unsupported interpreter, 3 install failed.
set -eu
HERE=$(cd "$(dirname "$0")/.." && pwd)
PARENT=$(dirname "$HERE")
PY=${PYTHON:-python3}
ONLINE=0; CERT=""; STATE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --online) ONLINE=1 ;;
    --certification) CERT="--certification" ;;
    --state-dir) shift; STATE="--state-dir $1" ;;
    *) echo "unknown option $1" >&2; exit 64 ;;
  esac; shift
done
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || { echo "Python >= 3.10 required" >&2; exit 2; }
# 1. verify shipped file digests when a release manifest is present
if [ -f "$HERE/SHA256SUMS" ]; then
  (cd "$HERE" && sha256sum -c --quiet SHA256SUMS) || { echo "digest verification failed" >&2; exit 3; }
fi
# 2. runtime needs no third-party packages; dev tooling optional
if [ "$ONLINE" = 1 ]; then
  if grep -q -- "--hash=" "$HERE/requirements-dev.lock"; then HASHES=--require-hashes; else HASHES=""; echo "WARNING: dev lock has no hashes (MC-09 open)" >&2; fi
  "$PY" -m pip install $HASHES -r "$HERE/requirements-dev.lock" || exit 3
fi
# 3. preflight + self-test
cd "$PARENT"
"$PY" -m inv68_resource_packing.tools.preflight $CERT $STATE || exit 1
"$PY" -m unittest discover -s inv68_resource_packing/tests -q || exit 1
echo "INV-68 bootstrap: ready"
