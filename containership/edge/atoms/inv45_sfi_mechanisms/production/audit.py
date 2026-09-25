"""Tamper-evident security audit trail (C049, C076).

Append-only JSON Lines where each event carries ``seq``, ``prev`` (hash of the
previous event) and ``hash`` (SHA-256 over the canonical event without ``hash``).
``verify_chain`` detects edits, reordering, deletion inside the chain and - given
an externally held checkpoint ``(seq, hash)`` - tail truncation, which a hash chain
alone cannot detect.

Events are redacted through an allowlist; artifact bytes, secrets and tokens are
never recorded.  If the sink fails, events are held in a bounded in-memory spool
and flushed on the next successful write; when the spool is full the audited
operation itself fails closed (security events are never silently dropped).
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

from .errors import SfiError
from .sfi import canonical_json, sha256_hex

AUDIT_SCHEMA = "PK_SFI_AUDIT/1"
GENESIS = "0" * 64
_ALLOWED = frozenset({
    "event", "outcome", "code", "tenant", "workload", "artifact_sha256", "profile_sha256", "proof_sha256",
    "config_sha256", "subject", "capability", "allowed", "reason", "scope", "target", "action",
    "generation", "trace_id", "span_id", "key_id", "state", "from_state", "to_state", "export",
    "approvers", "duration_ms", "artifact_version", "rewritten_accesses",
})


def redact(event: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in event.items():
        if k not in _ALLOWED:
            continue
        if isinstance(v, (bytes, bytearray)):
            v = f"<{len(v)} bytes redacted>"
        elif isinstance(v, str) and len(v) > 256:
            v = v[:253] + "..."
        out[k] = v
    return out


class AuditLog:
    def __init__(self, path: Path, *, clock: Callable[[], float] = time.time, spool_limit: int = 10_000,
                 fsync: bool = True, writer: Optional[Callable[[Path, str], None]] = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.clock = clock
        self.spool: list[dict[str, Any]] = []
        self.spool_limit = spool_limit
        self.fsync = fsync
        self._writer = writer or self._append
        self._lock = threading.Lock()
        self._seq, self._head = self._recover()

    def _recover(self) -> tuple[int, str]:
        if not self.path.exists():
            return 0, GENESIS
        last = None
        with self.path.open("rb") as fh:
            for line in fh:
                if line.strip():
                    last = line
        if last is None:
            return 0, GENESIS
        try:
            ev = json.loads(last)
            return int(ev["seq"]), str(ev["hash"])
        except (ValueError, KeyError):
            raise SfiError("SFI_AUDIT_TAMPERED", "audit tail unreadable at startup") from None

    def _append(self, path: Path, line: str) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            if self.fsync:
                os.fsync(fh.fileno())

    def emit(self, event: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            rec = redact(event)
            rec["schema"] = AUDIT_SCHEMA
            rec["ts"] = round(self.clock(), 6)
            rec["seq"] = self._seq + 1
            rec["prev"] = self._head
            rec["hash"] = sha256_hex(canonical_json(rec))
            self.spool.append(rec)
            self._seq, self._head = rec["seq"], rec["hash"]
            self._flush_locked()
            return rec

    def _flush_locked(self) -> None:
        while self.spool:
            rec = self.spool[0]
            try:
                self._writer(self.path, json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")
            except OSError:
                if len(self.spool) > self.spool_limit:
                    raise SfiError("SFI_DEPENDENCY_UNAVAILABLE", "audit sink down and spool full",
                                   dependency="audit-sink", limit=self.spool_limit) from None
                return
            self.spool.pop(0)

    def flush(self) -> int:
        with self._lock:
            self._flush_locked()
            return len(self.spool)

    def checkpoint(self) -> tuple[int, str]:
        """(seq, hash) to be stored OUTSIDE the log (e.g. in release evidence / SIEM)."""
        return self._seq, self._head


def verify_chain(path: Path, checkpoint: Optional[tuple[int, str]] = None) -> dict[str, Any]:
    prev, seq = GENESIS, 0
    count = 0
    with Path(path).open("rb") as fh:
        for n, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                raise SfiError("SFI_AUDIT_TAMPERED", "unparseable audit line", observed=n) from None
            h = ev.pop("hash", None)
            if ev.get("seq") != seq + 1 or ev.get("prev") != prev or h != sha256_hex(canonical_json(ev)):
                raise SfiError("SFI_AUDIT_TAMPERED", "audit chain broken", observed=n)
            prev, seq = h, ev["seq"]
            count += 1
    if checkpoint is not None:
        cseq, chash = checkpoint
        if seq < cseq:
            raise SfiError("SFI_AUDIT_TAMPERED", "audit log truncated below checkpoint", observed=seq,
                           limit=cseq)
        # the checkpointed event must still be the one in the chain
        with Path(path).open("rb") as fh:
            for line in fh:
                if line.strip():
                    ev = json.loads(line)
                    if ev["seq"] == cseq and ev["hash"] != chash:
                        raise SfiError("SFI_AUDIT_TAMPERED", "checkpointed event rewritten", observed=cseq)
    return {"events": count, "head_seq": seq, "head_hash": prev, "result": "INTACT"}
