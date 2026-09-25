"""Tamper-evident security audit log (MC-18).

Records are canonical JSON lines, each carrying ``prev`` (hash of the previous
record) and ``hash`` (SHA-256 over the canonical record without ``hash``).  Every
``checkpoint_every`` records an Ed25519-signed checkpoint binding the chain head,
record count, segment ID, component version and node identity is appended.
Deletion, insertion, reordering, bit flips, duplicates, forged checkpoints and
wrong signing keys are all detected by :func:`verify_log`, which reports the
first corruption point.

Appends are ``write + flush + fsync`` of a single line; a crash can at worst
leave a torn final line, which the verifier reports as ``torn_tail`` and
:meth:`AuditLog.open` truncates (recovering to the last complete record).
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
import pathlib
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Iterable, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .errors import ErrorCode, Inv36Error

GENESIS = "0" * 64
MANDATORY_EVENTS = frozenset({
    "handshake.success", "handshake.failure", "authz.decision", "key.rotate", "key.revoke", "key.rollback",
    "key.rollback_denied", "config.activate", "config.rollback", "config.validation_failed",
    "config.rollback_denied", "quarantine.request", "quarantine.activate", "quarantine.expire",
    "quarantine.remove", "quarantine.rejected", "admin.break_glass", "policy.activate", "policy.rollback_denied",
    "integrity.failure", "replay.threshold", "release.sign", "release.certify", "killswitch.engaged",
})
SECURITY_CRITICAL = frozenset({"key.revoke", "quarantine.activate", "admin.break_glass", "config.activate",
                               "policy.activate", "release.sign", "killswitch.engaged"})
_REDACT_KEYS = ("secret", "key_bytes", "private", "plaintext", "payload", "shared", "password", "token")
MAX_FIELD = 256
MAX_FIELDS = 32


class AuditUnavailable(Inv36Error, RuntimeError):
    code = ErrorCode.GATE_UNAVAILABLE


def _canon(obj: Mapping[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _sanitize(v: Any, depth: int = 0) -> Any:
    if depth > 3:
        return "<depth>"
    if v is None or isinstance(v, (bool, int, float)):
        return v
    if isinstance(v, (bytes, bytearray)):
        return f"<bytes:{len(v)}>"
    if isinstance(v, Mapping):
        out = {}
        for k, val in list(v.items())[:MAX_FIELDS]:
            ks = str(k)[:64]
            out[ks] = "<redacted>" if any(r in ks.lower() for r in _REDACT_KEYS) else _sanitize(val, depth + 1)
        return out
    if isinstance(v, (list, tuple, set, frozenset)):
        return [_sanitize(x, depth + 1) for x in list(v)[:MAX_FIELDS]]
    # ensure_ascii + escaping keeps attacker text on one line (log-injection safe, MC-18.016)
    return str(v)[:MAX_FIELD]


@dataclass
class AuditLog:
    path: pathlib.Path
    signer: Any = None                    # SigningKey-like with .sign(bytes); None = unsigned chain only
    signer_key_id: str = ""
    node: str = "unknown-node"
    component_version: str = ""
    checkpoint_every: int = 64
    max_buffer: int = 1024
    fail_closed_security: bool = True
    clock: Callable[[], float] = time.time
    mono: Callable[[], float] = time.monotonic
    segment: str = field(default_factory=lambda: uuid.uuid4().hex)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _head: str = field(default=GENESIS, init=False)
    _seq: int = field(default=0, init=False)
    _since_cp: int = field(default=0, init=False)
    _buffer: Deque[dict] = field(default_factory=collections.deque, init=False, repr=False)
    sink_available: bool = field(default=True, init=False)
    dropped: int = field(default=0, init=False)

    @classmethod
    def open(cls, path: str | os.PathLike, **kw) -> "AuditLog":
        log = cls(pathlib.Path(path), **kw)
        log.path.parent.mkdir(parents=True, exist_ok=True)
        if log.path.exists():
            data = log.path.read_bytes()
            if data and not data.endswith(b"\n"):
                # torn tail from a crash mid-append: drop the partial record
                keep = data[: data.rfind(b"\n") + 1]
                with open(log.path, "r+b") as fh:
                    fh.truncate(len(keep))
                    fh.flush()
                    os.fsync(fh.fileno())
                data = keep
            lines = data.splitlines()
            if lines:
                last = json.loads(lines[-1])
                log._head, log._seq = last["hash"], int(last["seq"])
        return log

    @property
    def head(self) -> str:
        return self._head

    def _write(self, rec: dict) -> None:
        if not self.sink_available:
            raise OSError("audit sink unavailable")
        line = _canon(rec) + b"\n"
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            os.write(fd, line)
            os.fsync(fd)
        finally:
            os.close(fd)

    def _seal(self, body: dict) -> dict:
        self._seq += 1
        rec = {**body, "seq": self._seq, "prev": self._head}
        rec["hash"] = hashlib.sha256(_canon(rec)).hexdigest()
        return rec

    def emit(self, event: str, data: Mapping[str, Any] | None = None, *, actor: str = "", target: str = "",
             tenant: str = "", decision: str = "", reason: str = "", correlation_id: str = "") -> dict | None:
        body = {
            "kind": "event", "event": str(event)[:64], "event_id": uuid.uuid4().hex,
            "ts": round(self.clock(), 6), "mono": round(self.mono(), 6), "clock_source": "system_realtime",
            "node": self.node, "component_version": self.component_version, "segment": self.segment,
            "actor": str(actor)[:128], "target": str(target)[:128], "tenant": str(tenant)[:64],
            "decision": str(decision)[:32], "reason": str(reason)[:128], "correlation_id": str(correlation_id)[:64],
            "data": _sanitize(dict(data or {})),
        }
        with self._lock:
            self._flush_buffer_locked()
            rec = self._seal(body)
            try:
                self._write(rec)
            except OSError as exc:
                if event in SECURITY_CRITICAL and self.fail_closed_security:
                    self._seq -= 1
                    raise AuditUnavailable("audit sink unavailable for security-critical event") from exc
                if len(self._buffer) >= self.max_buffer:
                    self._buffer.popleft()
                    self.dropped += 1
                self._buffer.append(rec)
            self._head = rec["hash"]
            self._since_cp += 1
            if (self.signer is not None and self._since_cp >= self.checkpoint_every
                    and not self._buffer and self.sink_available):
                self._checkpoint_locked()
            return rec

    def _flush_buffer_locked(self) -> None:
        while self._buffer and self.sink_available:
            rec = self._buffer[0]
            try:
                self._write(rec)
            except OSError:
                return
            self._buffer.popleft()

    def _checkpoint_locked(self) -> dict:
        body = {"kind": "checkpoint", "ts": round(self.clock(), 6), "node": self.node,
                "component_version": self.component_version, "segment": self.segment,
                "head": self._head, "count": self._seq, "key_id": self.signer_key_id}
        sig = self.signer.sign(_canon(body))
        rec = self._seal({**body, "sig": sig.hex()})
        self._write(rec)
        self._head = rec["hash"]
        self._since_cp = 0
        return rec

    def checkpoint(self) -> dict:
        with self._lock:
            if self.signer is None:
                raise AuditUnavailable("no audit signer configured")
            return self._checkpoint_locked()

    def listener(self) -> Callable[[str, dict], None]:
        """Adapter for component event hooks (key/policy/config/quarantine)."""
        def _listen(ev: str, data: dict) -> None:
            self.emit(ev, data)
        return _listen


@dataclass
class VerifyResult:
    ok: bool
    records: int
    checkpoints: int
    first_error_line: int | None = None
    error: str = ""
    head: str = GENESIS

    def to_dict(self) -> dict:
        return {"schema": "inv36.audit-verify/1", "ok": self.ok, "records": self.records,
                "checkpoints": self.checkpoints, "first_error_line": self.first_error_line,
                "error": self.error, "head": self.head}


def verify_log(path: str | os.PathLike, trusted_keys: Mapping[str, bytes] | None = None,
               require_checkpoint: bool = False, expected_head: str | None = None) -> VerifyResult:
    """Offline verifier (MC-18.017). ``trusted_keys`` maps key_id -> Ed25519 public bytes."""
    p = pathlib.Path(path)
    data = p.read_bytes() if p.exists() else b""
    lines: Iterable[bytes] = data.split(b"\n")
    lines = list(lines)
    torn = bool(lines and lines[-1])
    if not torn and lines:
        lines = lines[:-1]
    prev, seq, cps = GENESIS, 0, 0
    seen_ids: set[str] = set()
    for i, raw in enumerate(lines, 1):
        if torn and i == len(lines):
            return VerifyResult(False, seq, cps, i, "torn_tail", prev)
        try:
            rec = json.loads(raw)
        except ValueError:
            return VerifyResult(False, seq, cps, i, "unparseable", prev)
        h = rec.pop("hash", None)
        if hashlib.sha256(_canon(rec)).hexdigest() != h:
            return VerifyResult(False, seq, cps, i, "hash_mismatch", prev)
        if rec.get("prev") != prev:
            return VerifyResult(False, seq, cps, i, "chain_break", prev)
        if rec.get("seq") != seq + 1:
            return VerifyResult(False, seq, cps, i, "sequence_gap", prev)
        eid = rec.get("event_id")
        if eid:
            if eid in seen_ids:
                return VerifyResult(False, seq, cps, i, "duplicate_event", prev)
            seen_ids.add(eid)
        if rec.get("kind") == "checkpoint":
            body = {k: rec[k] for k in ("kind", "ts", "node", "component_version", "segment", "head", "count",
                                        "key_id")}
            if body["head"] != prev or body["count"] != seq:
                return VerifyResult(False, seq, cps, i, "checkpoint_mismatch", prev)
            if trusted_keys is not None:
                pub = trusted_keys.get(body["key_id"])
                if pub is None:
                    return VerifyResult(False, seq, cps, i, "untrusted_checkpoint_key", prev)
                try:
                    Ed25519PublicKey.from_public_bytes(pub).verify(bytes.fromhex(rec["sig"]), _canon(body))
                except (InvalidSignature, ValueError):
                    return VerifyResult(False, seq, cps, i, "bad_checkpoint_signature", prev)
            cps += 1
        prev, seq = h, rec["seq"]
    if require_checkpoint and cps == 0:
        return VerifyResult(False, seq, cps, None, "no_checkpoint", prev)
    if expected_head is not None and prev != expected_head:
        return VerifyResult(False, seq, cps, None, "head_mismatch_truncation", prev)
    return VerifyResult(True, seq, cps, None, "", prev)


RETENTION_POLICY = {
    "security_audit": {"prod": "400 days + legal hold", "stage": "90 days", "dev/test": "14 days"},
    "access": "tenant operators see only records whose tenant field matches their tenant; "
              "security owners see all; nobody may mutate or delete segments",
    "checkpoint_frequency": "every 64 records and on segment rotation",
    "segment_rotation": "new segment per process start; external rotation copies whole segments only",
    "verification_metadata": "export chain head + last signed checkpoint to an external store "
                             "(ship via telemetry exporter) so local tampering is detectable",
}
