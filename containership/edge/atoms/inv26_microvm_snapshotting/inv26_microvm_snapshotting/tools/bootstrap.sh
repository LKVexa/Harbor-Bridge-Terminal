#!/usr/bin/env bash
# Deterministic, idempotent bootstrap (C040). Every completed step leaves a marker; re-running skips it.
# Usage: INV26_STATE=/var/lib/inv26 INV26_DIST=./dist PROFILE=reference tools/bootstrap.sh
set -euo pipefail
STATE="${INV26_STATE:?set INV26_STATE}"; DIST="${INV26_DIST:?set INV26_DIST}"; PROFILE="${PROFILE:-reference}"
PY="${PYTHON:-python3}"; M="$STATE/bootstrap"; umask 077
mkdir -p "$M" "$STATE/meta" "$STATE/blobs" "$STATE/work"
step() { local n="$1"; shift; if [ -f "$M/$n.done" ]; then echo "skip $n"; return; fi
         echo "run  $n"; "$@"; date -u +%FT%TZ > "$M/$n.done"; }
step 01-verify-dist   bash -c "cd '$DIST' && sha256sum -c SHA256SUMS && $PY -m inv26_microvm_snapshotting.tools.release verify --dist ."
step 02-install       bash -c "$PY -m pip install --no-deps --no-index --find-links '$DIST' inv26-microvm-snapshotting"
step 03-preflight     $PY -m inv26_microvm_snapshotting.tools.preflight --profile "$PROFILE" --workdir "$STATE/work" \
                          --dir "$STATE/meta" --dir "$STATE/blobs" --out "$M/preflight.json"
step 04-smoke         $PY -m inv26_microvm_snapshotting.tools.smoke --root "$STATE" --out "$M/smoke.json"
echo "bootstrap complete: $(ls "$M" | wc -l) markers in $M"
