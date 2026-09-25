"""Backup, restore and restore verification (MC-039); compaction controller (MC-019).

Backup scope (MC-039-01): the full MVCC state (keys, retained history, leases,
fencing counter, idempotency table), the effective-config hash, build info and
a manifest.  Identity material is *referenced* (key ids), never copied.

A backup is a directory ``backup-<rev>-<ts>/`` containing ``state.bin`` (AES-GCM
sealed with the *backup* keyring, independent of the data keyring, MC-039-03)
and ``manifest.json`` with SHA-256 of ``state.bin`` and an HMAC signature over
the manifest.  A backup is marked successful only after it has been re-read,
signature- and checksum-verified, decoded, and its invariants checked
(MC-039-04).

Restore (MC-039-05/06) verifies everything again into a *new* data directory,
checks invariants, and sets ``compact_revision = backup revision`` so any
client resuming a watch from an older revision is told to relist rather than
silently missing the post-backup history that no longer exists.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
from typing import Any, Callable

from .errors import CorruptionError, InvalidArgument
from .store import ControlStore
from .wal import DurableStore, Sealer, write_snapshot

BACKUP_SCHEMA = "cstate.backup/1"


def _sign(manifest: dict[str, Any], key: bytes) -> str:
    body = json.dumps({k: v for k, v in manifest.items() if k != "signature"}, sort_keys=True).encode()
    return hmac.new(key, body, hashlib.sha256).hexdigest()


def create_backup(store: ControlStore, out_dir: str, *, sealer: Sealer, sign_key: bytes,
                  config_sha256: str = "", build: dict[str, Any] | None = None) -> dict[str, Any]:
    state = store.export_state()  # consistent: taken under the store lock
    rev = state["revision"]
    name = f"backup-{rev:016d}-{int(time.time())}"
    path = os.path.join(out_dir, name)
    os.makedirs(path, mode=0o700, exist_ok=False)
    body = json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
    sealed = sealer.seal(body, f"backup:{rev}".encode())
    with open(os.path.join(path, "state.bin"), "wb") as fh:
        fh.write(sealed)
        fh.flush()
        os.fsync(fh.fileno())
    manifest = {"schema": BACKUP_SCHEMA, "revision": rev, "compact_revision": state["compact_revision"],
                "created_unix": int(time.time()), "state_sha256": hashlib.sha256(sealed).hexdigest(),
                "plain_sha256": hashlib.sha256(body).hexdigest(), "key_id": sealer.keyring.active,
                "keys": len(state["keys"]), "config_sha256": config_sha256, "build": build or {},
                "status": "verifying"}
    manifest["signature"] = _sign(manifest, sign_key)
    _write_json(os.path.join(path, "manifest.json"), manifest)
    verify_backup(path, sealer=sealer, sign_key=sign_key, _allow_verifying=True)
    manifest["status"] = "verified"
    manifest["signature"] = _sign(manifest, sign_key)
    _write_json(os.path.join(path, "manifest.json"), manifest)
    return {"path": path, **manifest}


def _write_json(path: str, obj: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, sort_keys=True, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def verify_backup(path: str, *, sealer: Sealer, sign_key: bytes, _allow_verifying: bool = False) -> dict[str, Any]:
    try:
        with open(os.path.join(path, "manifest.json"), encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, ValueError) as exc:
        raise CorruptionError("backup manifest unreadable") from exc
    if manifest.get("schema") != BACKUP_SCHEMA:
        raise CorruptionError("unsupported backup schema")
    if not hmac.compare_digest(_sign(manifest, sign_key), str(manifest.get("signature"))):
        raise CorruptionError("backup manifest signature invalid")
    if manifest.get("status") != "verified" and not _allow_verifying:
        raise CorruptionError("backup was never verified; refusing to use it")
    with open(os.path.join(path, "state.bin"), "rb") as fh:
        sealed = fh.read()
    if hashlib.sha256(sealed).hexdigest() != manifest["state_sha256"]:
        raise CorruptionError("backup payload checksum mismatch")
    body = sealer.open(sealed, f"backup:{manifest['revision']}".encode())
    if hashlib.sha256(body).hexdigest() != manifest["plain_sha256"]:
        raise CorruptionError("backup plaintext checksum mismatch")
    state = json.loads(body)
    probe = ControlStore()
    probe.load_state(state)
    problems = probe.check_invariants()
    if problems or probe.revision != manifest["revision"]:
        raise CorruptionError("backup state inconsistent: " + "; ".join(problems or ["revision mismatch"]))
    return {"manifest": manifest, "state": state}


def restore_backup(path: str, data_dir: str, *, backup_sealer: Sealer, sign_key: bytes,
                   data_sealer: Sealer | None, **open_kw: Any) -> DurableStore:
    """Restore into an *empty* data dir and return the opened durable store."""
    if os.path.isdir(data_dir) and os.listdir(data_dir):
        raise InvalidArgument("restore target must be empty (never overwrite live state)", field="data_dir")
    os.makedirs(data_dir, mode=0o700, exist_ok=True)
    v = verify_backup(path, sealer=backup_sealer, sign_key=sign_key)
    state = v["state"]
    # Fence history: anything before the backup revision is no longer resumable.
    state = dict(state)
    state["events"] = []
    state["compact_revision"] = state["revision"]
    write_snapshot(data_dir, 1, state, data_sealer)
    ds = DurableStore.open(data_dir, sealer=data_sealer, **open_kw)
    if ds.store.check_invariants() or ds.store.revision != v["manifest"]["revision"]:
        raise CorruptionError("restored store failed verification")
    return ds


class CompactionController:
    """Policy-driven compaction (MC-019).

    target = revision - retain_revisions - safety_margin, never past the lowest
    protected revision, never past the oldest active watcher's resume point
    minus the margin, at most once per ``min_interval_s``, and only inside the
    optional maintenance window predicate.
    """

    def __init__(self, store: ControlStore, *, retain_revisions: int, safety_margin: int, min_interval_s: float,
                 watch_floor: Callable[[], int | None] | None = None,
                 window: Callable[[], bool] | None = None, clock: Callable[[], float] = time.monotonic,
                 on_compact: Callable[[int, int], None] | None = None) -> None:
        self.store, self.retain, self.margin, self.min_interval = store, retain_revisions, safety_margin, min_interval_s
        self.watch_floor, self.window, self.clock, self.on_compact = watch_floor, window, clock, on_compact
        self._last = -1e18
        self._lock = threading.Lock()
        self.last_target = 0

    def target(self) -> int:
        t = self.store.revision - self.retain - self.margin
        floors = list(self.store.protected.values())
        if self.watch_floor:
            wf = self.watch_floor()
            if wf is not None:
                floors.append(max(0, wf - 1 - self.margin))
        if floors:
            t = min(t, min(floors))
        return max(0, t)

    def run_once(self) -> int:
        with self._lock:
            if self.clock() - self._last < self.min_interval:
                return 0
            if self.window and not self.window():
                return 0
            t = self.target()
            if t <= self.store.compact_revision:
                return 0
            dropped = self.store.compact(t)
            self._last = self.clock()
            self.last_target = t
            if self.on_compact:
                self.on_compact(t, dropped)
            return dropped
