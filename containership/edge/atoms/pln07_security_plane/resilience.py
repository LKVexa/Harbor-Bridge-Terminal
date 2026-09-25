"""Resilience controls (MC-25 .. MC-28, MC-31).

* ``Health`` - starting/ready/degraded/failed state machine with a watchdog
  that flags stalls when a heartbeat is not seen within ``stall_after``.
* ``retry`` - bounded exponential backoff with full jitter for idempotent
  operations only; ``IdempotencyCache`` de-duplicates keyed requests.
* ``TokenBucket`` - admission control / load shedding.
* ``CircuitBreaker`` - closed/open/half-open around a dependency.
* ``Quarantine`` - freeze tenants, subjects, sites or the whole plane.

Degraded mode rule (MC-28): when a dependency needed to *issue* is down the
plane refuses issuance; *verification* continues from local state only while
the revocation horizon has not been breached.  It never fails open.
"""
from __future__ import annotations

import random
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Callable, TypeVar

from .grants import SecurityPlaneError

T = TypeVar("T")


class Overloaded(SecurityPlaneError):
    code = "admission.overloaded"


class CircuitOpen(SecurityPlaneError):
    code = "dependency.circuit_open"


class Frozen(SecurityPlaneError):
    code = "control.frozen"


STATES = ("starting", "ready", "degraded", "failed")


@dataclass
class Health:
    stall_after: float = 30.0
    clock: Callable[[], float] = time.monotonic
    state: str = "starting"
    reasons: dict[str, str] = field(default_factory=dict)
    _beats: dict[str, float] = field(default_factory=dict)

    def heartbeat(self, loop: str) -> None:
        self._beats[loop] = self.clock()

    def set(self, state: str, reason: str = "", source: str = "core") -> None:
        if state not in STATES:
            raise ValueError(state)
        self.state = state
        if reason:
            self.reasons[source] = reason
        else:
            self.reasons.pop(source, None)

    def check(self) -> dict:
        now = self.clock()
        stalled = sorted(k for k, t in self._beats.items() if now - t > self.stall_after)
        state = self.state
        if stalled and state == "ready":
            state = "degraded"
        return {"state": state, "stalled": stalled, "reasons": dict(self.reasons),
                "ready": state == "ready", "live": state != "failed"}


def retry(fn: Callable[[], T], *, attempts: int = 4, base: float = 0.05, cap: float = 1.0,
          retry_on: tuple[type[BaseException], ...] = (OSError, TimeoutError),
          sleep: Callable[[float], None] = time.sleep) -> T:
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    for i in range(attempts):
        try:
            return fn()
        except retry_on:
            if i == attempts - 1:
                raise
            sleep(random.uniform(0, min(cap, base * (2 ** i))))
    raise AssertionError("unreachable")


@dataclass
class IdempotencyCache:
    capacity: int = 10000
    _data: OrderedDict = field(default_factory=OrderedDict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def run(self, key: str, fn: Callable[[], T]) -> T:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                return self._data[key]
            result = fn()
            self._data[key] = result
            if len(self._data) > self.capacity:
                self._data.popitem(last=False)
            return result


@dataclass
class TokenBucket:
    rate: float
    burst: float
    clock: Callable[[], float] = time.monotonic
    _tokens: float = -1.0
    _t: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def admit(self, cost: float = 1.0) -> None:
        with self._lock:
            now = self.clock()
            if self._tokens < 0:
                self._tokens, self._t = self.burst, now
            self._tokens = min(self.burst, self._tokens + (now - self._t) * self.rate)
            self._t = now
            if self._tokens < cost:
                raise Overloaded("request shed by admission control")
            self._tokens -= cost


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    reset_seconds: float = 30.0
    clock: Callable[[], float] = time.monotonic
    state: str = "closed"
    _failures: int = 0
    _opened: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def call(self, fn: Callable[[], T]) -> T:
        with self._lock:
            if self.state == "open":
                if self.clock() - self._opened >= self.reset_seconds:
                    self.state = "half-open"
                else:
                    raise CircuitOpen(f"{self.name} circuit open")
        try:
            result = fn()
        except Exception:
            with self._lock:
                self._failures += 1
                if self.state == "half-open" or self._failures >= self.failure_threshold:
                    self.state, self._opened = "open", self.clock()
            raise
        with self._lock:
            self.state, self._failures = "closed", 0
        return result


@dataclass
class Quarantine:
    """Freeze controls; checked before issue/attenuate/verify."""

    plane_frozen: bool = False
    tenants: set[str] = field(default_factory=set)
    subjects: set[str] = field(default_factory=set)
    sites: set[str] = field(default_factory=set)
    log: list[dict] = field(default_factory=list)

    def freeze(self, kind: str, value: str | None = None, *, actor: str, reason: str) -> None:
        if kind == "plane":
            self.plane_frozen = True
        else:
            getattr(self, kind).add(value)
        self.log.append({"op": "freeze", "kind": kind, "value": value, "actor": actor, "reason": reason})

    def thaw(self, kind: str, value: str | None = None, *, actor: str, reason: str) -> None:
        if kind == "plane":
            self.plane_frozen = False
        else:
            getattr(self, kind).discard(value)
        self.log.append({"op": "thaw", "kind": kind, "value": value, "actor": actor, "reason": reason})

    def check(self, *, tenant: str, subject: str | None = None, site: str | None = None) -> None:
        if self.plane_frozen:
            raise Frozen("security plane is frozen")
        if tenant in self.tenants:
            raise Frozen("tenant is quarantined", details={"tenant": tenant})
        if subject and subject in self.subjects:
            raise Frozen("subject is quarantined")
        if site and site in self.sites:
            raise Frozen("site is quarantined", details={"site": site})
