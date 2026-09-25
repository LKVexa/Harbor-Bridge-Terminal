"""Runtime controls: quarantine service, replay/nonce cache, admission rate limiting.

* ``QuarantineService`` - digest-keyed, append-only persisted (hash-chained
  JSONL) record of failed/unknown artifacts; repeated execution attempts are
  counted; release needs two distinct approvers and a reason, and is itself
  recorded.  Quarantine survives restart.
* ``ReplayCache`` - bounded nonce cache for *online* one-time authorisations
  (break-glass tokens, signing requests); entries expire on trusted time; when
  full, the oldest unexpired entry is never silently evicted - new nonces are
  refused (fail closed) instead.
* ``AdmissionLimiter`` - bounded concurrency + bounded queue + token bucket per
  tenant.  Shedding returns ``OVERLOADED`` which admission maps to DENY, so
  overload can never skip verification.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections import OrderedDict
from contextlib import contextmanager
from typing import Any, Iterator

from .canonical import canonical_bytes
from .errors import fail


class QuarantineService:
    def __init__(self, path: str | None = None, *, audit: Any = None):
        self._path = path
        self._audit = audit
        self._lock = threading.Lock()
        self._entries: dict[str, dict[str, Any]] = {}
        self._head = "0" * 64
        if path and os.path.exists(path):
            self._replay()

    def _append(self, rec: dict[str, Any]) -> None:
        rec = {**rec, "previous": self._head}
        rec["hash"] = hashlib.sha256(canonical_bytes(rec)).hexdigest()
        self._head = rec["hash"]
        if self._path:
            with open(self._path, "ab") as fh:
                fh.write(canonical_bytes(rec) + b"\n")
                fh.flush()
                os.fsync(fh.fileno())
        self._apply(rec)

    def _apply(self, rec: dict[str, Any]) -> None:
        d = rec["digest"]
        if rec["op"] == "quarantine":
            e = self._entries.setdefault(d, {"digest": d, "reasons": [], "first_seen": rec["time"], "attempts": 0, "active": True})
            e["active"] = True
            e["reasons"].append(rec["reason"])
            e["last_seen"] = rec["time"]
            e["evidence"] = rec.get("evidence", {})
        elif rec["op"] == "attempt":
            if d in self._entries:
                self._entries[d]["attempts"] += 1
                self._entries[d]["last_seen"] = rec["time"]
        elif rec["op"] == "release":
            if d in self._entries:
                self._entries[d]["active"] = False

    def _replay(self) -> None:
        prev = "0" * 64
        with open(self._path, "rb") as fh:  # type: ignore[arg-type]
            for line in fh:
                rec = json.loads(line)
                h = rec.pop("hash")
                if rec["previous"] != prev or hashlib.sha256(canonical_bytes(rec)).hexdigest() != h:
                    raise fail("AUDIT_CHAIN_BROKEN", "quarantine journal tampered")
                rec["hash"] = prev = h
                self._apply(rec)
        self._head = prev

    def quarantine(self, digest: str, reason: str, *, now: int, evidence: dict[str, Any] | None = None) -> None:
        with self._lock:
            self._append({"op": "quarantine", "digest": digest, "reason": reason, "time": now, "evidence": evidence or {}})
        if self._audit is not None:
            self._audit.append("quarantine.add", {"digest": digest, "reason": reason})

    def check(self, digest: str, *, now: int) -> None:
        with self._lock:
            e = self._entries.get(digest)
            if e is not None and e["active"]:
                self._append({"op": "attempt", "digest": digest, "reason": "blocked", "time": now})
                raise fail("QUARANTINED", "artifact digest is quarantined", digest=digest, attempts=e["attempts"])

    def release(self, digest: str, *, approvers: list[str], reason: str, now: int) -> None:
        if len(set(approvers)) < 2 or not reason:
            raise fail("BREAK_GLASS_INVALID", "quarantine release requires two distinct approvers and a reason")
        with self._lock:
            if digest not in self._entries:
                raise fail("POLICY_INVALID", "digest is not quarantined")
            self._append({"op": "release", "digest": digest, "reason": reason, "time": now, "evidence": {"approvers": sorted(set(approvers))}})
        if self._audit is not None:
            self._audit.append("quarantine.release", {"digest": digest, "approvers": sorted(set(approvers))})

    def entries(self) -> list[dict[str, Any]]:
        return [dict(e) for e in self._entries.values()]


class ReplayCache:
    """Nonce cache; with ``path`` it is durable across restarts and shared by controllers on one host."""

    def __init__(self, capacity: int = 100_000, path: str | None = None):
        self._cap = capacity
        self._lock = threading.Lock()
        self._seen: OrderedDict[str, int] = OrderedDict()
        self._path = path
        if path and os.path.exists(path):
            with open(path, "rb") as fh:
                for line in fh:
                    try:
                        rec = json.loads(line)
                        self._seen[str(rec["n"])] = int(rec["e"])
                    except (ValueError, KeyError, TypeError) as exc:
                        raise fail("AUDIT_CHAIN_BROKEN", "replay cache journal corrupt; refusing one-time authorisations") from exc

    def use(self, nonce: str, *, expires: int, now: int) -> None:
        if not isinstance(nonce, str) or not 16 <= len(nonce) <= 128:
            raise fail("ENVELOPE_MALFORMED", "nonce invalid")
        if expires < now:
            raise fail("REPLAY", "one-time authorisation expired")
        with self._lock:
            for k in [k for k, exp in self._seen.items() if exp < now]:
                del self._seen[k]
            if nonce in self._seen:
                raise fail("REPLAY", "nonce already used")
            if len(self._seen) >= self._cap:
                raise fail("OVERLOADED", "replay cache full; refusing new one-time authorisations")
            if self._path:
                with open(self._path, "ab") as fh:  # persist BEFORE honouring the nonce
                    fh.write(canonical_bytes({"n": nonce, "e": expires}) + b"\n")
                    fh.flush()
                    os.fsync(fh.fileno())
            self._seen[nonce] = expires


class AdmissionLimiter:
    def __init__(self, max_concurrent: int = 32, max_queue: int = 256, rate_per_s: float = 500.0, burst: int = 1000,
                 queue_timeout_s: float = 2.0, clock=time.monotonic):
        self._sem = threading.BoundedSemaphore(max_concurrent)
        self._max_queue = max_queue
        self._queued = 0
        self._qlock = threading.Lock()
        self._rate, self._burst = rate_per_s, burst
        self._buckets: dict[str, tuple[float, float]] = {}
        self._timeout = queue_timeout_s
        self._clock = clock
        self.shed = 0

    def _take_token(self, tenant: str) -> bool:
        now = self._clock()
        with self._qlock:
            tokens, last = self._buckets.get(tenant, (float(self._burst), now))
            tokens = min(self._burst, tokens + (now - last) * self._rate)
            if tokens < 1:
                self._buckets[tenant] = (tokens, now)
                return False
            self._buckets[tenant] = (tokens - 1, now)
            return True

    @contextmanager
    def slot(self, tenant: str) -> Iterator[None]:
        if not self._take_token(tenant):
            self.shed += 1
            raise fail("OVERLOADED", "tenant admission rate exceeded", tenant=tenant)
        with self._qlock:
            if self._queued >= self._max_queue:
                self.shed += 1
                raise fail("OVERLOADED", "admission queue full")
            self._queued += 1
        try:
            if not self._sem.acquire(timeout=self._timeout):
                self.shed += 1
                raise fail("OVERLOADED", "timed out waiting for verification capacity")
        finally:
            with self._qlock:
                self._queued -= 1
        try:
            yield
        finally:
            self._sem.release()
