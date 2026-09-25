"""Restart / crash-consistency / recovery (MC-10).

Design decision (see docs/RECOVERY.md): cryptographic session state is
**never** persisted or resumed.  Every restart, reconnect, VM snapshot restore
or migration performs a fresh PK_CTRL_HS/1 handshake with new CSPRNG ephemerals,
so sequence numbers can never be reset under the same key (MC-10.003/.006/.007)
and two restored clones of one VM snapshot cannot share traffic keys
(MC-10.012).

What *is* persisted is small, integrity-checked, versioned metadata:

=====================  ==================  =========================================
State                  Class               Restart behaviour
=====================  ==================  =========================================
session_id/keys/seq    ephemeral           discarded; re-handshake
peer identity          reconstructable     re-proven by handshake
partial inbound bytes  ephemeral           discarded (Connection.close clears)
pending outbound work  ephemeral           discarded unless caller re-submits
dedup (op_id) window   persistence-req.    persisted; replays across restart refused
config version         persistence-req.    ConfigStore.recover()
quarantine directives  persistence-req.    QuarantineRegistry.load() (re-verified)
audit cursor/head      persistence-req.    AuditLog.open() (torn tail truncated)
shutdown marker        persistence-req.    clean/unclean detection
=====================  ==================  =========================================
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
import pathlib
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable

from .errors import ErrorCode, Inv36Error

STATE_SCHEMA = "inv36.state/1"
STATE_CLASSIFICATION = {
    "session_id": "ephemeral", "traffic_keys": "ephemeral", "sequence_counters": "ephemeral",
    "peer_identity": "reconstructable", "partial_inbound": "ephemeral", "pending_outbound": "ephemeral",
    "dedup_window": "persistence_required", "config_version": "persistence_required",
    "quarantine": "persistence_required", "audit_cursor": "persistence_required",
    "shutdown_marker": "persistence_required",
}
FORBIDDEN_PERSISTED = ("key", "secret", "shared", "seq", "session_id", "nonce")
RESTART_SEMANTICS = {
    "process_restart": "new instance id; all sessions re-handshake; dedup window reloaded",
    "guest_reboot": "same as process restart on the guest; host side sees StreamReset and reconnects with backoff",
    "host_reboot": "guests observe reset; reconnect with jittered backoff once host listener is back",
    "live_migration": "vsock connections reset by hypervisor; sessions re-established on destination",
    "snapshot_restore": "restored process has a stale instance id; it re-handshakes with fresh ephemerals; "
                        "persisted state carries no key material so clones cannot share traffic keys",
}
RTO_TARGET_S = 5.0


class StateCorrupt(Inv36Error, ValueError):
    code = ErrorCode.CONFIG_INVALID


@dataclass
class DedupWindow:
    """Bounded idempotency window for operations eligible for replay (MC-10.005)."""

    ttl_s: float = 600.0
    capacity: int = 65536
    clock: Callable[[], float] = time.time
    _seen: collections.OrderedDict = field(default_factory=collections.OrderedDict, init=False)

    def check_and_record(self, op_id: bytes) -> bool:
        """Return True if new; False if a duplicate within the window."""
        now = self.clock()
        while self._seen:
            k, t = next(iter(self._seen.items()))
            if now - t <= self.ttl_s and len(self._seen) <= self.capacity:
                break
            self._seen.popitem(last=False)
        key = op_id.hex()
        if key in self._seen:
            return False
        self._seen[key] = now
        return True

    def export(self) -> dict:
        return dict(self._seen)

    def load(self, data: dict) -> None:
        now = self.clock()
        for k, t in sorted(data.items(), key=lambda kv: kv[1]):
            if isinstance(k, str) and len(k) == 32 and now - float(t) <= self.ttl_s:
                self._seen[k] = float(t)


def _digest(body: dict) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass
class StateStore:
    path: pathlib.Path
    clock: Callable[[], float] = time.time

    def write(self, body: dict) -> None:
        for k in body:
            if any(f in k.lower() for f in FORBIDDEN_PERSISTED) and k != "dedup":
                raise StateCorrupt("refusing to persist session/key material", detail={"field": k})
        doc = {"schema": STATE_SCHEMA, "body": body, "sha256": _digest(body)}
        tmp = self.path.with_suffix(".tmp")
        with open(tmp, "w") as fh:
            fh.write(json.dumps(doc, sort_keys=True))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)
        try:
            dfd = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
        except OSError:  # pragma: no cover - directory fsync unsupported on some filesystems
            pass

    def read(self) -> dict | None:
        tmp = self.path.with_suffix(".tmp")
        if tmp.exists():
            tmp.unlink()
        if not self.path.exists():
            return None
        try:
            doc = json.loads(self.path.read_text())
        except ValueError as exc:
            raise StateCorrupt("state file unparseable") from exc
        if doc.get("schema") != STATE_SCHEMA:
            raise StateCorrupt("incompatible state schema", detail={"schema": str(doc.get("schema"))[:32]})
        if _digest(doc.get("body", {})) != doc.get("sha256"):
            raise StateCorrupt("state checksum mismatch")
        return doc["body"]


@dataclass
class RecoveryManager:
    """Boot-time recovery: detects unclean shutdown, reloads bounded state."""

    store: StateStore
    dedup: DedupWindow = field(default_factory=DedupWindow)
    instance_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: dict = field(default_factory=dict, init=False)

    def start(self) -> dict:
        t0 = time.monotonic()
        try:
            prev = self.store.read()
            corrupt = False
        except StateCorrupt as exc:
            prev, corrupt = None, True
            self.status["corruption"] = exc.code.name
        clean = bool(prev and prev.get("clean_shutdown"))
        if prev:
            self.dedup.load(prev.get("dedup", {}))
        self.status.update({
            "schema": "inv36.recovery/1", "instance_id": self.instance_id,
            "previous_instance_id": prev.get("instance_id") if prev else None,
            "last_shutdown": "clean" if clean else ("none" if prev is None and not corrupt else "unclean"),
            "state_corrupt": corrupt,
            "operator_action": "quarantine node and inspect state file; delete it to start with empty dedup window"
            if corrupt else "",
            "sessions_resumed": 0,  # by design: never
            "recovery_s": round(time.monotonic() - t0, 6),
        })
        self.checkpoint(clean=False)
        return dict(self.status)

    def checkpoint(self, *, clean: bool) -> None:
        self.store.write({"instance_id": self.instance_id, "clean_shutdown": clean,
                          "written_at": self.store.clock(), "dedup": self.dedup.export()})

    def shutdown(self) -> None:
        self.checkpoint(clean=True)
