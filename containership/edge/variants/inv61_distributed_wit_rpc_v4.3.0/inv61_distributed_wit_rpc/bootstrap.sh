#!/usr/bin/env bash
# INV-61 deterministic bootstrap (M31 / C040): empty node -> verified, healthy install.
#   ./bootstrap.sh --wheel dist/<wheel> [--config cfg.json] [--prefix /opt/inv61] [--python python3]
#   ./bootstrap.sh --verify-only --wheel dist/<wheel> [--config cfg.json]
#   ./bootstrap.sh --rollback [--prefix /opt/inv61]
set -euo pipefail
PREFIX=/opt/inv61; PY=python3; WHEEL=""; CONFIG=""; MODE=install
while [[ $# -gt 0 ]]; do case "$1" in
  --wheel) WHEEL="$2"; shift 2;; --config) CONFIG="$2"; shift 2;; --prefix) PREFIX="$2"; shift 2;;
  --python) PY="$2"; shift 2;; --verify-only) MODE=verify; shift;; --rollback) MODE=rollback; shift;;
  *) echo "unknown arg $1" >&2; exit 2;; esac; done

die() { echo "bootstrap: $*" >&2; exit 1; }
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' || die "python >= 3.10 required"

if [[ $MODE == rollback ]]; then
  [[ -L "$PREFIX/current" && -d "$PREFIX/previous" ]] || die "no previous release to roll back to"
  prev=$(readlink -f "$PREFIX/previous"); ln -sfn "$prev" "$PREFIX/current"
  "$PREFIX/current/venv/bin/inv61-selfcheck" || die "selfcheck failed after rollback"
  echo "rolled back to $prev"; exit 0
fi

[[ -n "$WHEEL" && -f "$WHEEL" ]] || die "--wheel <file> required"
DIST=$(dirname "$WHEEL")
[[ -f "$DIST/SHA256SUMS" ]] || die "SHA256SUMS missing next to wheel"
( cd "$DIST" && grep " $(basename "$WHEEL")\$" SHA256SUMS | sha256sum -c - ) || die "wheel checksum mismatch"
[[ $MODE == verify ]] && { echo "verify-only: wheel checksum OK"; exit 0; }

REL="$PREFIX/releases/$(basename "$WHEEL" .whl)"
mkdir -p "$REL"
"$PY" -m venv "$REL/venv"
HASH=$(sha256sum "$WHEEL" | cut -d' ' -f1)
echo "inv61-distributed-wit-rpc @ file://$(readlink -f "$WHEEL") --hash=sha256:$HASH" > "$REL/requirements.txt"
"$REL/venv/bin/pip" install --no-index --no-deps --require-hashes -r "$REL/requirements.txt" >/dev/null
if [[ -n "$CONFIG" ]]; then
  "$REL/venv/bin/python" -c "import json,sys; from inv61_distributed_wit_rpc import config as c; cfg=dict(c.DEFAULTS); cfg.update(json.load(open(sys.argv[1]))); e=c.validate(cfg); print('\n'.join(e)); sys.exit(1 if e else 0)" "$CONFIG" || die "configuration invalid"
fi
"$REL/venv/bin/inv61-selfcheck" || die "selfcheck failed"
[[ -L "$PREFIX/current" ]] && ln -sfn "$(readlink -f "$PREFIX/current")" "$PREFIX/previous"
ln -sfn "$REL" "$PREFIX/current"
echo "installed $(basename "$WHEEL") -> $REL"
