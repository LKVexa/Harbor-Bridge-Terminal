"""Shared primitives: canonical JSON, digests, reason codes, trusted clock, audit chain.

Checklist items served: 26 (trusted time), 38 (tamper-evident audit ledger),
and the "stable machine-readable reason codes" sub-item every component carries.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable


def canonical(obj: Any) -> bytes:
    """RFC 8785-style canonical bytes (sorted keys, no whitespace, UTF-8)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(obj: Any) -> str:
    return "sha256:" + sha256_hex(canonical(obj))


class Reason:
    """Stable reason codes. Values are wire contract: never renumber, only add."""
    ADMIT = "ADMIT"
    POLICY_REJECTED = "POLICY_REJECTED"
    MALFORMED_INPUT = "MALFORMED_INPUT"
    DEPENDENCY_FAILURE = "DEPENDENCY_FAILURE"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    UNAUTHORIZED = "UNAUTHORIZED"
    UNSUPPORTED = "UNSUPPORTED_CONFIGURATION"
    INTERNAL = "INTERNAL_DEFECT"
    EMERGENCY_DENY = "EMERGENCY_DENY_ALL"
    BASELINE_UNAVAILABLE = "BASELINE_UNAVAILABLE"
    CLOCK_UNTRUSTED = "CLOCK_UNTRUSTED"
    RUNTIME_UNAVAILABLE = "SANDBOX_RUNTIME_UNAVAILABLE"


class ClockUntrusted(Exception):
    pass


class TrustedClock:
    """Item 26: time is never taken from the caller.

    Wraps a time source; refuses (raises ``ClockUntrusted``) when the source
    fails, goes backwards beyond ``max_backstep`` seconds, or disagrees with an
    optional reference source by more than ``max_skew`` seconds. A refusal makes
    every exception inactive (fail closed), it never makes one active.
    """

    def __init__(self, source: Callable[[], float] = time.time,
                 reference: Callable[[], float] | None = None,
                 max_skew: float = 5.0, max_backstep: float = 1.0):
        self._source, self._ref = source, reference
        self._max_skew, self._max_backstep = max_skew, max_backstep
        self._last: float | None = None
        self._lock = threading.Lock()

    def now(self) -> int:
        with self._lock:
            try:
                t = float(self._source())
            except Exception as exc:
                raise ClockUntrusted(f"time source failed: {exc}") from None
            if t != t or t <= 0:
                raise ClockUntrusted("time source returned a non-positive or NaN value")
            if self._last is not None and t < self._last - self._max_backstep:
                raise ClockUntrusted(f"clock moved backwards {self._last - t:.3f}s")
            if self._ref is not None:
                try:
                    r = float(self._ref())
                except Exception as exc:
                    raise ClockUntrusted(f"reference source failed: {exc}") from None
                if abs(r - t) > self._max_skew:
                    raise ClockUntrusted(f"skew {abs(r - t):.3f}s exceeds {self._max_skew}s")
            self._last = max(t, self._last or t)
            return int(t)


@dataclass(frozen=True)
class AuditEvent:
    seq: int
    kind: str
    subject: str
    actor: str
    at: int
    data: dict
    prev: str
    hash: str


class AuditLedger:
    """Item 38: append-only, hash-chained, HMAC-sealed audit ledger (JSON lines).

    ``verify`` detects any edit, deletion, reorder or insertion. Tail truncation
    is detected only against an externally recorded head (``expected_head``) -
    the standing blind spot of every self-contained chain, stated not hidden.
    """
    GENESIS = "sha256:" + "0" * 64

    def __init__(self, path: str | None, seal_key: bytes):
        if not isinstance(seal_key, bytes) or len(seal_key) < 16:
            raise ValueError("audit seal key must be >= 16 bytes")
        self.path, self._key = path, seal_key
        self._lock = threading.Lock()
        self._mem: list[dict] = []
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                self._mem = [json.loads(line) for line in fh if line.strip()]

    @property
    def head(self) -> str:
        return self._mem[-1]["hash"] if self._mem else self.GENESIS

    def _seal(self, body: dict) -> str:
        return "hmac-sha256:" + hmac.new(self._key, canonical(body), hashlib.sha256).hexdigest()

    def append(self, kind: str, subject: str, actor: str, at: int, data: dict) -> dict:
        with self._lock:
            body = {"seq": len(self._mem), "kind": kind, "subject": subject, "actor": actor,
                    "at": at, "data": data, "prev": self.head}
            rec = dict(body, hash=digest(body))
            rec["seal"] = self._seal(rec)
            line = json.dumps(rec, sort_keys=True, separators=(",", ":"))
            if self.path:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
            self._mem.append(rec)
            return rec

    def events(self) -> list[dict]:
        return list(self._mem)

    def verify(self, expected_head: str | None = None) -> tuple[bool, str]:
        prev = self.GENESIS
        for i, rec in enumerate(self._mem):
            body = {k: rec.get(k) for k in ("seq", "kind", "subject", "actor", "at", "data", "prev")}
            if rec.get("seq") != i:
                return False, f"sequence break at {i}"
            if rec.get("prev") != prev:
                return False, f"chain break at {i}"
            if rec.get("hash") != digest(body):
                return False, f"hash mismatch at {i}"
            seal = {k: v for k, v in rec.items() if k != "seal"}
            if not hmac.compare_digest(rec.get("seal", ""), self._seal(seal)):
                return False, f"seal mismatch at {i}"
            prev = rec["hash"]
        if expected_head is not None and prev != expected_head:
            return False, "head differs from externally recorded head (truncation or fork)"
        return True, f"{len(self._mem)} events verified"


def atomic_write(path: str, data: bytes) -> None:
    """Write-then-rename; readers see the old file or the new file, never a mix."""
    tmp = f"{path}.tmp.{os.getpid()}.{threading.get_ident()}"
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
