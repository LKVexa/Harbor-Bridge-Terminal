"""Components 08, 18, 25, 26 - controller ownership/leader fencing,
quarantine/freeze/emergency-disable controls, retry/backoff/circuit-breaker
policy, and partition/reconnect semantics."""
from __future__ import annotations

import random
import threading
from dataclasses import dataclass, field
from typing import Callable

from .errors import ErrorCode, Gap10Error
from .keys import KeyRing


# --------------------------------------------------------------- 08 leases
@dataclass
class LeaseManager:
    """Per-shard leadership leases with monotonically increasing fencing tokens.

    Backed in production by an external linearizable store (etcd/consul/DB
    row with compare-and-swap); this in-process implementation provides the
    same semantics for tests and single-host deployments."""
    keyring: KeyRing | None = None
    ttl_s: float = 10.0
    _leases: dict[str, tuple[str, int, float]] = field(default_factory=dict)  # shard -> (holder, token, expires)
    _token: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def acquire(self, shard: str, holder: str, now: float) -> int:
        with self._lock:
            cur = self._leases.get(shard)
            if cur and cur[0] != holder and cur[2] > now:
                raise Gap10Error(ErrorCode.OWNERSHIP_CONFLICT, f"{shard} held by {cur[0]} until {cur[2]}")
            if cur and cur[0] == holder and cur[2] > now:
                self._leases[shard] = (holder, cur[1], now + self.ttl_s)
                return cur[1]
            self._token += 1
            self._leases[shard] = (holder, self._token, now + self.ttl_s)
            return self._token

    def validate(self, shard: str, holder: str, token: int, now: float) -> None:
        cur = self._leases.get(shard)
        if not cur or cur[0] != holder or cur[1] != token or cur[2] <= now:
            raise Gap10Error(ErrorCode.FENCING_TOKEN_STALE, f"{holder} token {token} not current for {shard}")

    def release(self, shard: str, holder: str) -> None:
        with self._lock:
            if self._leases.get(shard, ("",))[0] == holder:
                del self._leases[shard]

    def holder(self, shard: str, now: float):
        cur = self._leases.get(shard)
        return cur if cur and cur[2] > now else None


# --------------------------------------------------------------- 18 controls
CONTROL_KINDS = {
    "quarantine": 0.0,          # node gets no new work (ceiling 0)
    "freeze": None,             # ceiling frozen at current value, cannot increase
    "emergency-disable": None,  # GAP-10 automation disabled -> static conservative ceiling
}


@dataclass(frozen=True)
class Control:
    control_id: str
    kind: str
    target: str            # node id or "*" for fleet
    actor: str
    reason: str
    applied_at: float
    expires_at: float | None
    frozen_fraction: float | None = None
    ticket: str = ""


@dataclass
class ControlPlane:
    """Authenticated operational controls. Every control can only restrict.
    Release requires ``control.release``; expiry of a control never widens
    capacity past what the live decision allows (it just stops restricting)."""
    keyring: KeyRing
    audit: object = None
    disable_fraction: float = 0.25   # static conservative ceiling while automation disabled
    controls: dict[str, Control] = field(default_factory=dict)

    def apply(self, *, key_id, signature, kind, target, reason, control_id, now, ttl_s=None, current_fraction=None,
              ticket=""):
        payload = {"kind": kind, "target": target, "reason": reason, "control_id": control_id, "ticket": ticket}
        try:
            actor = self.keyring.verify(key_id, "control.operate", target, payload, signature, now=now)
        except Gap10Error as e:
            if self.audit:
                self.audit.append("control.rejected", str(key_id), now, kind=str(kind), code=e.code.value)
            raise Gap10Error(ErrorCode.CONTROL_UNAUTHORIZED, e.message) from e
        if kind not in CONTROL_KINDS or not reason or not ticket:
            raise Gap10Error(ErrorCode.CONTROL_INVALID, f"bad control {kind!r}")
        frozen = None
        if kind == "freeze":
            if current_fraction is None:
                raise Gap10Error(ErrorCode.CONTROL_INVALID, "freeze needs current_fraction")
            frozen = current_fraction
        existing = self.controls.get(control_id)
        if existing is not None and (existing.kind, existing.target) == (kind, target):
            return existing  # idempotent re-delivery
        c = Control(control_id, kind, target, actor, reason, now, None if ttl_s is None else now + ttl_s, frozen, ticket)
        self.controls[control_id] = c
        if self.audit:
            self.audit.append("control.applied", actor, now, control_id=control_id, kind=kind, target=target, reason=reason, ticket=ticket)
        return c

    def release(self, *, key_id, signature, control_id, now):
        payload = {"release": control_id}
        c = self.controls.get(control_id)
        if c is None:
            raise Gap10Error(ErrorCode.CONTROL_INVALID, f"unknown control {control_id}")
        try:
            actor = self.keyring.verify(key_id, "control.release", c.target, payload, signature, now=now)
        except Gap10Error as e:
            raise Gap10Error(ErrorCode.CONTROL_UNAUTHORIZED, e.message) from e
        del self.controls[control_id]
        if self.audit:
            self.audit.append("control.released", actor, now, control_id=control_id)

    def active_for(self, node: str, now: float) -> list[Control]:
        return [c for c in self.controls.values()
                if c.target in (node, "*") and (c.expires_at is None or c.expires_at > now)]

    def bound(self, node: str, now: float) -> tuple[float, list[str], bool]:
        """Return (max_fraction, reasons, automation_disabled)."""
        bound, reasons, disabled = 1.0, [], False
        for c in self.active_for(node, now):
            if c.kind == "quarantine":
                bound = 0.0
            elif c.kind == "freeze":
                bound = min(bound, c.frozen_fraction)
            elif c.kind == "emergency-disable":
                bound = min(bound, self.disable_fraction)
                disabled = True
            reasons.append(f"control {c.kind} {c.control_id} by {c.actor}: {c.reason}")
        return bound, reasons, disabled


# --------------------------------------------------------------- 25 retry / circuit
@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 4
    base_delay_s: float = 0.05
    max_delay_s: float = 2.0
    jitter: float = 0.5
    deadline_s: float = 5.0

    def delays(self, rng: random.Random | None = None):
        rng = rng or random.Random()
        d = self.base_delay_s
        total = 0.0
        for _ in range(self.max_attempts - 1):
            j = d * (1 - self.jitter * rng.random())
            if total + j > self.deadline_s:
                return
            total += j
            yield j
            d = min(d * 2, self.max_delay_s)


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    reset_after_s: float = 30.0
    state: str = "closed"
    failures: int = 0
    opened_at: float = 0.0

    def allow(self, now: float) -> bool:
        if self.state == "open" and now - self.opened_at >= self.reset_after_s:
            self.state = "half-open"
        return self.state != "open"

    def success(self) -> None:
        self.state, self.failures = "closed", 0

    def failure(self, now: float) -> None:
        self.failures += 1
        if self.state == "half-open" or self.failures >= self.failure_threshold:
            self.state, self.opened_at = "open", now


def call_with_policy(fn: Callable, *, breaker: CircuitBreaker, policy: RetryPolicy, now: Callable[[], float],
                     sleep: Callable[[float], None] = lambda s: None, retry_on=(Gap10Error, OSError, TimeoutError),
                     rng: random.Random | None = None):
    """Invoke ``fn`` under retry + circuit breaker. On exhaustion raises
    CIRCUIT_OPEN / DEPENDENCY_TIMEOUT; callers must then fail closed."""
    if not breaker.allow(now()):
        raise Gap10Error(ErrorCode.CIRCUIT_OPEN, breaker.name)
    last = None
    delays = list(policy.delays(rng)) + [None]
    for delay in delays:
        try:
            result = fn()
            breaker.success()
            return result
        except retry_on as e:  # noqa: PERF203
            last = e
            breaker.failure(now())
            if breaker.state == "open" or delay is None:
                break
            sleep(delay)
    raise Gap10Error(ErrorCode.DEPENDENCY_TIMEOUT, f"{breaker.name}: {last}")


# --------------------------------------------------------------- 26 partition
@dataclass
class PartitionManager:
    """Edge autonomy when the control plane is unreachable.

    * Local authority: the node-local GAP-10 agent keeps evaluating local
      trusted telemetry with the *last activated* policy; it may lower the
      ceiling freely but may not raise it above ``min(last_confirmed,
      partition_cap)``.
    * After ``max_autonomy_s`` without reconnect the node drops to the
      critical fraction.
    * On reconnect, reconciliation takes the minimum of local and central
      decisions until central confirms a fresh decision (no bump-up on
      reconnect).
    """
    partition_cap: float = 0.60
    max_autonomy_s: float = 900.0
    critical_fraction: float = 0.25
    connected: bool = True
    partitioned_at: float | None = None
    last_confirmed_fraction: dict[str, float] = field(default_factory=dict)
    reconciling: set[str] = field(default_factory=set)

    def on_disconnect(self, now: float) -> None:
        if self.connected:
            self.connected, self.partitioned_at = False, now

    def on_reconnect(self, nodes) -> None:
        self.connected = True
        self.partitioned_at = None
        self.reconciling = set(nodes)

    def confirm(self, node: str, central_fraction: float) -> None:
        self.last_confirmed_fraction[node] = central_fraction
        self.reconciling.discard(node)

    def bound(self, node: str, local_fraction: float, now: float) -> tuple[float, str | None]:
        last = self.last_confirmed_fraction.get(node, self.critical_fraction)
        if not self.connected:
            if self.partitioned_at is not None and now - self.partitioned_at > self.max_autonomy_s:
                return min(local_fraction, self.critical_fraction), "partition autonomy window exceeded"
            return min(local_fraction, last, self.partition_cap), "partitioned: local authority, capped"
        if node in self.reconciling:
            return min(local_fraction, last), "reconciling after partition"
        return local_fraction, None
