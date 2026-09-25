"""Crash consistency, replay, fencing, disconnected operation and failover
(MC-009, MC-039, MC-040, MC-041).

* ``DurableAdapter`` - write-ahead JSON-lines journal with per-record checksums;
  a torn tail record is discarded on replay (crash consistency).  Every mutation
  carries the writer's fencing epoch; a lower epoch is refused (split-brain).
* ``Lease`` - ownership epoch + expiry.  Acquire bumps the epoch; a stale holder
  is fenced by the storage layer, not by trust.
* ``OfflineBuffer`` - bounded local buffer used in degraded (partitioned) mode;
  replay on reconnect re-publishes with the *original* idempotency keys so
  reconciliation is duplicate-free under at-least-once delivery.
* ``select_failover`` - residency- and consistency-safe target selection.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Sequence

from .runtime import Adapter, RuntimePlaneError, TransactionOperation


class Fenced(RuntimePlaneError):
    code = "PK_FENCED"


class ResidencyViolation(RuntimePlaneError):
    code = "PK_RESIDENCY_VIOLATION"


class ReadOnly(RuntimePlaneError):
    code = "PK_READ_ONLY"


def _rec(op: str, epoch: int, **data) -> str:
    body = {"op": op, "epoch": epoch, **data}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return json.dumps({"b": body, "c": hashlib.sha256(raw.encode()).hexdigest()[:16]}, sort_keys=True)


def _enc(v: bytes | None) -> str | None:
    return None if v is None else base64.b64encode(v).decode()


def _dec(v: str | None) -> bytes | None:
    return None if v is None else base64.b64decode(v)


class DurableAdapter(Adapter):
    def __init__(self, name: str, journal_path: str, available: bool = True, fsync: bool = True):
        super().__init__(name, available)
        self.journal_path, self.fsync = journal_path, fsync
        self.epoch = 0
        self.replayed = 0
        self.discarded_tail = 0
        if os.path.exists(journal_path):
            self._replay()

    # -- journal ---------------------------------------------------------------------------------
    def _append(self, line: str) -> None:
        with open(self.journal_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            if self.fsync:
                os.fsync(fh.fileno())

    def _replay(self) -> None:
        with open(self.journal_path, encoding="utf-8") as fh:
            lines = fh.read().split("\n")
        good: list[str] = []
        for i, line in enumerate(lines):
            if not line:
                continue
            try:
                rec = json.loads(line)
                body = rec["b"]
                raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
                if hashlib.sha256(raw.encode()).hexdigest()[:16] != rec["c"]:
                    raise ValueError("checksum")
            except Exception:
                # only a torn *final* record is tolerated; interior corruption is fatal
                if any(l for l in lines[i + 1:]):
                    raise RuntimePlaneError("journal corruption before tail", line=i + 1)
                self.discarded_tail += 1
                break
            self._apply(body)
            good.append(line)
            self.replayed += 1
        if self.discarded_tail:  # rewrite journal without the torn tail
            tmp = self.journal_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write("\n".join(good) + ("\n" if good else ""))
            os.replace(tmp, self.journal_path)

    def _apply(self, body: dict) -> None:
        self.epoch = max(self.epoch, int(body["epoch"]))
        op = body["op"]
        if op == "set":
            self._store[body["k"]] = _dec(body["v"])
        elif op == "del":
            self._store.pop(body["k"], None)
        elif op == "txn":
            for verb, k, v in body["ops"]:
                if verb == "set":
                    self._store[k] = _dec(v)
                else:
                    self._store.pop(k, None)
        elif op == "pub":
            self._store[body["k"]] = _dec(body["v"])
            self._seen.add(body["d"])
            self._messages.append((body["ch"], body["d"], _dec(body["v"])))
        elif op == "epoch":
            pass

    def _fence(self, epoch: int | None) -> int:
        e = self.epoch if epoch is None else epoch
        if e < self.epoch:
            raise Fenced("stale fencing epoch", presented=e, current=self.epoch)
        return e

    def advance_epoch(self, epoch: int) -> None:
        with self._lock:
            if epoch <= self.epoch:
                raise Fenced("epoch must increase", presented=epoch, current=self.epoch)
            self._append(_rec("epoch", epoch))
            self.epoch = epoch

    # -- mutations (journal first, then apply) -------------------------------------------------
    def set(self, key: str, value: bytes, epoch: int | None = None) -> None:  # type: ignore[override]
        from .runtime import _require_payload
        value = _require_payload(value)
        with self._lock:
            self._require_available()
            e = self._fence(epoch)
            self._append(_rec("set", e, k=key, v=_enc(value)))
            self._store[key] = value

    def delete(self, key: str, epoch: int | None = None) -> bool:  # type: ignore[override]
        with self._lock:
            self._require_available()
            e = self._fence(epoch)
            existed = key in self._store
            self._append(_rec("del", e, k=key))
            self._store.pop(key, None)
            return existed

    def transact(self, operations: Sequence[TransactionOperation], epoch: int | None = None) -> None:  # type: ignore[override]
        probe = Adapter(self.name)          # reuse base validation without touching our store
        probe.transact(list(operations))
        with self._lock:
            self._require_available()
            e = self._fence(epoch)
            self._append(_rec("txn", e, ops=[[v, k, _enc(x)] for v, k, x in operations]))
            for verb, k, x in operations:
                if verb == "set":
                    self._store[k] = x  # type: ignore[assignment]
                else:
                    self._store.pop(k, None)

    def publish(self, storage_key: str, channel: str, idempotency_key: str, payload: bytes,
                epoch: int | None = None) -> bool:  # type: ignore[override]
        from .runtime import _require_payload
        payload = _require_payload(payload)
        with self._lock:
            self._require_available()
            e = self._fence(epoch)
            if idempotency_key in self._seen:
                return False
            self._append(_rec("pub", e, k=storage_key, ch=channel, d=idempotency_key, v=_enc(payload)))
            self._store[storage_key] = payload
            self._seen.add(idempotency_key)
            self._messages.append((channel, idempotency_key, payload))
            return True


@dataclass
class Lease:
    holder: str
    epoch: int
    expires: float


class LeaseManager:
    def __init__(self, ttl: float = 10.0, clock: Callable[[], float] = time.monotonic):
        self.ttl, self.clock = ttl, clock
        self._lease: Lease | None = None
        self._epoch = 0
        self._lock = threading.Lock()

    def acquire(self, holder: str) -> Lease:
        with self._lock:
            now = self.clock()
            if self._lease and self._lease.expires > now and self._lease.holder != holder:
                raise Fenced("lease held by another owner", holder=self._lease.holder)
            if not (self._lease and self._lease.holder == holder and self._lease.expires > now):
                self._epoch += 1
            self._lease = Lease(holder, self._epoch, now + self.ttl)
            return self._lease


class OfflineBuffer:
    """Bounded store-and-forward buffer for publishes during a partition (MC-009/MC-040)."""

    def __init__(self, max_msgs: int, max_bytes: int):
        self.max_msgs, self.max_bytes = max_msgs, max_bytes
        self._q: deque[tuple[str, str, str, bytes, str]] = deque()
        self._bytes = 0
        self._lock = threading.Lock()

    def put(self, workload: str, tenant: str, topic: str, payload: bytes, idem: str) -> None:
        with self._lock:
            if len(self._q) >= self.max_msgs or self._bytes + len(payload) > self.max_bytes:
                raise ReadOnly("offline buffer full; refusing new writes until reconnect",
                               buffered=len(self._q))
            self._q.append((workload, tenant, topic, payload, idem))
            self._bytes += len(payload)

    def __len__(self) -> int:
        return len(self._q)

    def drain(self, publish: Callable[[str, str, str, bytes, str], bool]) -> dict:
        """Replay in FIFO order; stops at the first failure and keeps the remainder (no loss)."""
        sent = dup = 0
        while True:
            with self._lock:
                if not self._q:
                    break
                item = self._q[0]
            accepted = publish(*item)
            with self._lock:
                self._q.popleft()
                self._bytes -= len(item[3])
            sent += accepted
            dup += (not accepted)
        return {"replayed": sent, "deduplicated": dup, "remaining": len(self._q)}


@dataclass(frozen=True)
class Site:
    name: str
    zone: str
    healthy: bool
    consistency: str  # strong | read-your-writes | eventual
    lag_s: float = 0.0


_RANK = {"strong": 3, "read-your-writes": 2, "eventual": 1}


def select_failover(candidates: Sequence[Site], *, allowed_zones: set[str], required_consistency: str,
                    max_lag_s: float) -> Site:
    """Residency first, then consistency, then freshness (MC-010 precedence applied to MC-039)."""
    in_zone = [s for s in candidates if s.zone in allowed_zones]
    if not in_zone:
        raise ResidencyViolation("no failover target inside permitted residency zones")
    ok = [s for s in in_zone if s.healthy and _RANK[s.consistency] >= _RANK[required_consistency]
          and s.lag_s <= max_lag_s]
    if not ok:
        raise ReadOnly("no residency- and consistency-safe failover target; entering read-only degraded mode")
    return sorted(ok, key=lambda s: (s.lag_s, s.name))[0]
