"""Tamper-evident durable audit pipeline (checklist #47, #76).

Each record is canonical JSON carrying ``prev`` (hash of the previous record) and
``hash`` = SHA-256 over the canonical record without ``hash``; an optional HMAC key
makes the chain unforgeable by anyone lacking the key.  ``FileAuditSink`` appends
and fsyncs before the operation is acknowledged; if the sink fails the service
fails closed (ErrorCode.AUDIT_UNAVAILABLE).  Records never contain secret values;
secret names are pseudonymised per ``docs/security/secret-name-privacy.md``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import json
import os
import threading
from typing import Iterable, Protocol

GENESIS = "sha256:" + "0" * 64


def canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


class AuditSink(Protocol):
    def append(self, line: bytes) -> None: ...


@dataclass
class MemoryAuditSink:
    lines: list[bytes] = field(default_factory=list)
    fail: bool = False

    def append(self, line: bytes) -> None:
        if self.fail:
            raise OSError("audit sink failure (injected)")
        self.lines.append(line)


@dataclass
class FileAuditSink:
    path: str
    fsync: bool = True
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def append(self, line: bytes) -> None:
        with self._lock:
            fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            try:
                os.write(fd, line + b"\n")
                if self.fsync:
                    os.fsync(fd)
            finally:
                os.close(fd)


@dataclass
class AuditChain:
    sink: AuditSink
    hmac_key: bytes | None = None
    head: str = GENESIS
    seq: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def _digest(self, body: bytes) -> str:
        if self.hmac_key:
            return "hmac-sha256:" + hmac.new(self.hmac_key, body, hashlib.sha256).hexdigest()
        return "sha256:" + hashlib.sha256(body).hexdigest()

    def record(self, event: dict) -> dict:
        """Append durably; raises OSError if the sink fails (caller fails closed)."""
        with self._lock:
            rec = dict(event)
            rec["seq"] = self.seq + 1
            rec["prev"] = self.head
            rec["hash"] = self._digest(canonical(rec))
            self.sink.append(canonical(rec))
            self.seq, self.head = rec["seq"], rec["hash"]
            return rec


def resume_from_file(path: str, sink: AuditSink, hmac_key: bytes | None = None) -> AuditChain:
    """Verify an existing audit file and continue its chain.  Raises ValueError on divergence
    (the service must then quarantine rather than start a fresh chain)."""
    try:
        with open(path, "rb") as fh:
            lines = fh.read().splitlines()
    except FileNotFoundError:
        lines = []
    ok, n, reason = verify_chain(lines, hmac_key)
    if not ok:
        raise ValueError(f"audit chain verification failed: {reason}")
    head = GENESIS
    if n:
        head = json.loads([l for l in lines if l.strip()][-1])["hash"]
    return AuditChain(sink, hmac_key, head=head, seq=n)


def verify_chain(lines: Iterable[bytes | str], hmac_key: bytes | None = None) -> tuple[bool, int, str]:
    """Return (ok, records_verified, reason)."""
    prev, n = GENESIS, 0
    for raw in lines:
        if isinstance(raw, str):
            raw = raw.encode()
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except ValueError:
            return False, n, f"malformed record after seq {n}"
        claimed = rec.pop("hash", None)
        if rec.get("prev") != prev or rec.get("seq") != n + 1:
            return False, n, f"chain break at seq {n + 1}"
        body = canonical(rec)
        if hmac_key:
            expect = "hmac-sha256:" + hmac.new(hmac_key, body, hashlib.sha256).hexdigest()
        else:
            expect = "sha256:" + hashlib.sha256(body).hexdigest()
        if not hmac.compare_digest(expect, claimed or ""):
            return False, n, f"hash mismatch at seq {n + 1}"
        prev, n = claimed, n + 1
    return True, n, "ok"


def pseudonymise(name: str, key: bytes) -> str:
    """Keyed pseudonym for secret names in exported telemetry (not in the local audit)."""
    return "sn:" + hmac.new(key, name.encode(), hashlib.sha256).hexdigest()[:16]
