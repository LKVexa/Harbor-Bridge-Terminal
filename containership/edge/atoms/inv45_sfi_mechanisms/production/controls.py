"""Operational controls: quarantine/freeze/disable, anti-rollback floors, lifecycle,
admission control, deadlines, bounded retry and circuit breaking.

C015 (lifecycle), C017/C028/C054/C067 (quotas, admission, bounds), C025/C053
(deadlines, cancellation, retry), C057/C058 (crash-consistent durable state and
single-owner writes), C059 (quarantine).
"""
from __future__ import annotations

import json
import random
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator, Optional, TypeVar

from .config import _atomic_write, load_json_strict
from .errors import SfiError

T = TypeVar("T")

# ------------------------------------------------------------------------------ lifecycle

STATES = ("DISCOVERED", "VALIDATED", "VERIFIED", "SEALED", "LOADED", "RUNNING", "STOPPED",
          "QUARANTINED", "REJECTED")
TRANSITIONS: dict[str, frozenset[str]] = {
    "DISCOVERED": frozenset({"VALIDATED", "REJECTED"}),
    "VALIDATED": frozenset({"VERIFIED", "REJECTED"}),
    "VERIFIED": frozenset({"SEALED", "REJECTED"}),
    "SEALED": frozenset({"LOADED", "REJECTED", "QUARANTINED"}),
    "LOADED": frozenset({"RUNNING", "STOPPED", "QUARANTINED"}),
    "RUNNING": frozenset({"LOADED", "STOPPED", "QUARANTINED"}),
    "STOPPED": frozenset(),
    "QUARANTINED": frozenset({"STOPPED"}),
    "REJECTED": frozenset(),
}


@dataclass
class Lifecycle:
    state: str = "DISCOVERED"
    history: list[tuple[str, str, str]] = field(default_factory=list)

    def to(self, new: str, reason: str) -> None:
        if new not in TRANSITIONS.get(self.state, frozenset()):
            raise SfiError("SFI_ILLEGAL_TRANSITION", "illegal lifecycle transition", from_state=self.state,
                           to_state=new)
        self.history.append((self.state, new, reason))
        self.state = new


# ------------------------------------------------------------------------------ durable state

class DurableState:
    """Quarantine entries + anti-rollback floors, persisted atomically.

    Single-writer discipline: an exclusive owner lock file (``O_EXCL``) with the
    owner id and a fencing counter prevents two controllers from both writing
    (split-brain, C058).  A stale owner can be taken over only with ``force=True``
    by an operator, which bumps the fencing epoch so the old owner's writes fail.
    """

    SCHEMA = "PK_SFI_STATE/1"

    def __init__(self, root: Path, owner: str, *, force: bool = False):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.owner = owner
        self._lock = threading.Lock()
        self._epoch = self._acquire(force)

    def _acquire(self, force: bool) -> int:
        lock = self.root / "OWNER"
        epoch = 1
        if lock.exists():
            info = json.loads(lock.read_text())
            if info["owner"] != self.owner and not force:
                raise SfiError("SFI_CONFIG_CONFLICT", "state store is owned by another controller",
                               target=info["owner"])
            epoch = int(info["epoch"]) + 1
        _atomic_write(lock, json.dumps({"owner": self.owner, "epoch": epoch}).encode())
        return epoch

    def _check_fence(self) -> None:
        info = json.loads((self.root / "OWNER").read_text())
        if info["owner"] != self.owner or int(info["epoch"]) != self._epoch:
            raise SfiError("SFI_CONFIG_CONFLICT", "fenced: another controller took ownership",
                           target=info["owner"])

    def _path(self) -> Path:
        return self.root / "state.json"

    def read(self) -> dict[str, Any]:
        p = self._path()
        if not p.exists():
            return {"schema": self.SCHEMA, "quarantine": {}, "floors": {}}
        st = load_json_strict(p.read_text(encoding="utf-8"))
        if st.get("schema") != self.SCHEMA:
            raise SfiError("SFI_UNSUPPORTED_VERSION", "state schema", expected_version=self.SCHEMA)
        return st

    def _write(self, st: dict[str, Any]) -> None:
        self._check_fence()
        _atomic_write(self._path(), json.dumps(st, sort_keys=True, indent=1).encode())

    # quarantine ----------------------------------------------------------------------
    def set_quarantine(self, scope: str, target: str, action: str, reason: str, approvers: list[str]) -> None:
        if scope not in ("global", "tenant", "artifact") or action not in ("freeze", "disable"):
            raise SfiError("SFI_SCHEMA_INVALID", "bad quarantine scope/action", scope=scope)
        with self._lock:
            st = self.read()
            st["quarantine"][f"{scope}:{target}"] = {"action": action, "reason": reason[:256],
                                                     "approvers": sorted(approvers), "at": time.time()}
            self._write(st)

    def release(self, scope: str, target: str) -> bool:
        with self._lock:
            st = self.read()
            gone = st["quarantine"].pop(f"{scope}:{target}", None) is not None
            self._write(st)
            return gone

    def blocked(self, tenant: str, artifact_sha256: str) -> Optional[dict[str, Any]]:
        q = self.read()["quarantine"]
        for key in ("global:*", f"tenant:{tenant}", f"artifact:{artifact_sha256}"):
            if key in q:
                return {"scope": key.split(":", 1)[0], **q[key]}
        return None

    # anti-rollback ---------------------------------------------------------------------
    def enforce_floor(self, workload: str, version: int) -> None:
        with self._lock:
            st = self.read()
            floor = int(st["floors"].get(workload, 0))
            if version < floor:
                raise SfiError("SFI_ROLLBACK_REJECTED", "artifact version below anti-rollback floor",
                               workload=workload, floor=floor, observed_version=version)
            if version > floor:
                st["floors"][workload] = version
                self._write(st)


# ------------------------------------------------------------------------------ admission

class Admission:
    """Global + per-tenant concurrency caps with a bounded wait queue (fair rejection)."""

    def __init__(self, max_concurrent: int, max_per_tenant: int, max_queue: int, *,
                 queue_timeout: float = 1.0):
        self.max_concurrent = max_concurrent
        self.max_per_tenant = max_per_tenant
        self.max_queue = max_queue
        self.queue_timeout = queue_timeout
        self._cv = threading.Condition()
        self._active = 0
        self._per: dict[str, int] = {}
        self._waiting = 0
        self.shed = 0
        self.peak_active = 0

    @contextmanager
    def slot(self, tenant: str) -> Iterator[None]:
        with self._cv:
            if self._per.get(tenant, 0) >= self.max_per_tenant:
                self.shed += 1
                raise SfiError("SFI_OVERLOADED", "tenant concurrency quota reached", tenant=tenant,
                               limit=self.max_per_tenant, retry_after_ms=100)
            if self._active >= self.max_concurrent:
                if self._waiting >= self.max_queue:
                    self.shed += 1
                    raise SfiError("SFI_OVERLOADED", "admission queue full", limit=self.max_queue,
                                   retry_after_ms=200)
                self._waiting += 1
                try:
                    ok = self._cv.wait_for(lambda: self._active < self.max_concurrent, self.queue_timeout)
                finally:
                    self._waiting -= 1
                if not ok:
                    self.shed += 1
                    raise SfiError("SFI_OVERLOADED", "admission wait timed out", retry_after_ms=200)
                if self._per.get(tenant, 0) >= self.max_per_tenant:
                    self.shed += 1
                    raise SfiError("SFI_OVERLOADED", "tenant concurrency quota reached", tenant=tenant)
            self._active += 1
            self._per[tenant] = self._per.get(tenant, 0) + 1
            self.peak_active = max(self.peak_active, self._active)
        try:
            yield
        finally:
            with self._cv:
                self._active -= 1
                self._per[tenant] -= 1
                if not self._per[tenant]:
                    del self._per[tenant]
                self._cv.notify()

    def snapshot(self) -> dict[str, int]:
        with self._cv:
            return {"active": self._active, "waiting": self._waiting, "shed": self.shed,
                    "peak_active": self.peak_active, "tenants": len(self._per)}


def retry(fn: Callable[[], T], *, attempts: int = 4, base: float = 0.05, cap: float = 1.0,
          sleep: Callable[[float], None] = time.sleep, rng: random.Random = random.Random()) -> T:
    """Retry only errors whose registry entry says ``retryable``; full jitter; bounded."""
    for i in range(attempts):
        try:
            return fn()
        except SfiError as e:
            if not e.retryable or i == attempts - 1:
                raise
            sleep(rng.uniform(0, min(cap, base * (2 ** i))))
    raise SfiError("SFI_INTERNAL_INVARIANT", "retry loop exhausted without result")  # pragma: no cover


class CircuitBreaker:
    """Opens after ``threshold`` consecutive dependency failures; half-opens after ``cooldown``."""

    def __init__(self, name: str, threshold: int = 5, cooldown: float = 30.0,
                 clock: Callable[[], float] = time.monotonic):
        self.name, self.threshold, self.cooldown, self.clock = name, threshold, cooldown, clock
        self.failures = 0
        self.opened_at: Optional[float] = None
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        if self.opened_at is None:
            return "closed"
        return "half-open" if self.clock() - self.opened_at >= self.cooldown else "open"

    def call(self, fn: Callable[[], T]) -> T:
        with self._lock:
            if self.state == "open":
                raise SfiError("SFI_DEPENDENCY_UNAVAILABLE", "circuit open", dependency=self.name,
                               retry_after_ms=int(self.cooldown * 1000))
        try:
            out = fn()
        except SfiError as e:
            if e.spec.category == "dependency" or e.code == "SFI_DEADLINE_EXCEEDED":
                with self._lock:
                    self.failures += 1
                    if self.failures >= self.threshold:
                        self.opened_at = self.clock()
            raise
        with self._lock:
            self.failures = 0
            self.opened_at = None
        return out


class Deadline:
    def __init__(self, seconds: float, clock: Callable[[], float] = time.monotonic):
        self.clock = clock
        self.at = clock() + seconds
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True

    def expired(self) -> bool:
        return self.cancelled or self.clock() > self.at

    def check(self, op: str) -> None:
        if self.cancelled:
            raise SfiError("SFI_CANCELLED", "operation cancelled", operation=op)
        if self.clock() > self.at:
            raise SfiError("SFI_DEADLINE_EXCEEDED", "operation deadline exceeded", operation=op)

    def remaining(self) -> float:
        return max(0.0, self.at - self.clock())
