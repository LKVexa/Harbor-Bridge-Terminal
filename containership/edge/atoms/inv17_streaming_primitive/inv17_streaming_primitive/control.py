"""Multi-stream control plane for INV-17 (instance-local).

Controls: C016/C027/C093 (version negotiation), C017/C028 (tenant quotas + fairness),
C052 (health + stall thresholds), C054 (load shedding + circuit breaker), C059
(quarantine / freeze / emergency disable), C046 (isolation via authorised transfer),
C057 (explicit crash semantics: registry state is ephemeral).

The data-plane ``Stream`` stays dependency-free; this module composes it with
``security`` (capabilities + audit) and exposes the operator decisions that
``observability`` explains.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import RLock
from typing import Callable, Iterable, Mapping

from .security import AuditLedger, AuthError, AuthzDenied, CapabilityAuthority, TrustServiceUnavailable
from .stream import PROTOCOL_VERSIONS, Stream, StreamConfig, StreamError

SUPPORTED_VERSIONS: Mapping[str, tuple[int, ...]] = {name: (1,) for name in PROTOCOL_VERSIONS}


class QuotaExceeded(StreamError):
    code = "PK_STREAM_QUOTA"


class LoadShed(StreamError):
    code = "PK_STREAM_LOAD_SHED"


class CircuitOpen(StreamError):
    code = "PK_STREAM_CIRCUIT_OPEN"


class ComponentDisabled(StreamError):
    code = "PK_STREAM_DISABLED"


class StreamNotFound(StreamError, KeyError):
    code = "PK_STREAM_NOT_FOUND"


class VersionUnsupported(StreamError):
    code = "PK_STREAM_VERSION_UNSUPPORTED"


# --------------------------------------------------------------------------- versions
def negotiate(interface: str, offered: Iterable[int]) -> int:
    """Pick the highest mutually supported version; refuse (never guess) otherwise."""
    supported = SUPPORTED_VERSIONS.get(interface)
    if supported is None:
        raise VersionUnsupported("unknown interface", interface=interface)
    offered_set = {v for v in offered if isinstance(v, int) and not isinstance(v, bool)}
    common = sorted(offered_set & set(supported))
    if not common:
        raise VersionUnsupported("no mutually supported version", interface=interface,
                                 offered=sorted(offered_set), supported=list(supported))
    return common[-1]


# --------------------------------------------------------------------------- quotas
@dataclass(frozen=True)
class TenantQuota:
    max_streams: int = 64
    max_buffered: int = 65536
    weight: int = 1

    def __post_init__(self) -> None:
        for name in ("max_streams", "max_buffered", "weight"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
                raise ValueError(f"{name} must be a positive integer")


class FairCreditScheduler:
    """Weighted deficit round-robin over tenants for a shared credit pool (anti-starvation).

    Every tenant with demand receives at least one unit per round while its quota allows,
    so a heavy tenant cannot starve a light one; weights skew the share, not access.
    """

    def __init__(self, weights: Mapping[str, int]) -> None:
        self.weights = dict(weights)
        self._deficit: dict[str, int] = {}

    def allocate(self, pool: int, demand: Mapping[str, int]) -> dict[str, int]:
        if pool < 0:
            raise ValueError("pool must be non-negative")
        grants = {t: 0 for t in demand}
        active = [t for t in sorted(demand) if demand[t] > 0]
        while pool > 0 and active:
            for t in list(active):
                self._deficit[t] = self._deficit.get(t, 0) + max(1, self.weights.get(t, 1))
                take = min(self._deficit[t], demand[t] - grants[t], pool)
                grants[t] += take
                self._deficit[t] -= take
                pool -= take
                if grants[t] >= demand[t]:
                    active.remove(t)
                    self._deficit[t] = 0
                if pool == 0:
                    break
        return grants


# --------------------------------------------------------------------------- breaker
class CircuitBreaker:
    """closed -> open after ``threshold`` failures in a row; half-open after ``cooldown``."""

    def __init__(self, threshold: int = 5, cooldown: float = 5.0, clock: Callable[[], float] = time.monotonic):
        self.threshold, self.cooldown, self._clock = threshold, cooldown, clock
        self.failures = 0
        self.state = "closed"
        self._opened_at = 0.0

    def allow(self) -> bool:
        if self.state == "open" and self._clock() - self._opened_at >= self.cooldown:
            self.state = "half_open"
        return self.state != "open"

    def success(self) -> None:
        self.failures = 0
        self.state = "closed"

    def failure(self) -> None:
        self.failures += 1
        if self.state == "half_open" or self.failures >= self.threshold:
            self.state = "open"
            self._opened_at = self._clock()


# --------------------------------------------------------------------------- health
@dataclass(frozen=True)
class HealthPolicy:
    """C052 thresholds (mirrors ``operations/health-policy.json``)."""

    stall_ratio_degraded: float = 0.25
    stall_ratio_unhealthy: float = 0.75
    stall_seconds_unhealthy: float = 30.0
    min_attempts: int = 20
    buffer_fill_degraded: float = 0.9


@dataclass
class HealthReport:
    status: str  # healthy | degraded | unhealthy | disabled
    reasons: list[str] = field(default_factory=list)
    streams: int = 0


# --------------------------------------------------------------------------- registry
class StreamRegistry:
    """Owns open streams for one instance: authorisation, quotas, shedding, controls.

    Crash semantics (C057, ``spec/crash-semantics.md``): the registry is memory-only.
    A process restart loses every stream; holders of an old stream id receive
    ``StreamNotFound`` and must reopen -- there is no replay or resume.
    """

    def __init__(self, *, authority: CapabilityAuthority | None = None, audit: AuditLedger | None = None,
                 quotas: Mapping[str, TenantQuota] | None = None, default_quota: TenantQuota | None = None,
                 global_buffer_budget: int = 1 << 20, health: HealthPolicy | None = None,
                 clock: Callable[[], float] = time.monotonic, admins: Iterable[str] = ("sre-oncall",)) -> None:
        self.authority = authority or CapabilityAuthority()
        self.audit = audit or AuditLedger()
        self.quotas = dict(quotas or {})
        self.default_quota = default_quota or TenantQuota()
        self.global_buffer_budget = global_buffer_budget
        self.health_policy = health or HealthPolicy()
        self.breaker = CircuitBreaker(clock=clock)
        self._clock = clock
        self.admins = frozenset(admins)
        self.disabled = False
        self.frozen_scopes: set[tuple[str, str]] = set()  # ("tenant", t) / ("workload", w)
        self._streams: dict[str, Stream] = {}
        self._stall_since: dict[str, float] = {}
        self._lock = RLock()
        self.decisions: list[dict[str, object]] = []  # bounded explain log
        self.shed_count = 0
        self._scheduler = FairCreditScheduler({})

    # -- helpers
    def quota(self, tenant: str) -> TenantQuota:
        return self.quotas.get(tenant, self.default_quota)

    def _decide(self, op: str, outcome: str, reason: str, **ctx: object) -> None:
        self.decisions.append({"op": op, "outcome": outcome, "reason": reason, **ctx})
        del self.decisions[:-256]

    def _authorize(self, token: str, stream_id: str, tenant: str, workload: str, right: str) -> None:
        try:
            self.authority.verify(token, stream_id=stream_id, tenant=tenant, workload=workload, right=right)
        except TrustServiceUnavailable as exc:
            self.audit.record("trust.unavailable", tenant, stream_id, "denied",
                              dependency=exc.details.get("dependency"))
            self._decide(right, "denied", "trust service unavailable (fail closed)", stream=stream_id)
            raise
        except AuthzDenied as exc:
            self.audit.record("authz.denied", tenant, stream_id, "denied", right=right, error=exc.code)
            self._decide(right, "denied", str(exc), stream=stream_id)
            raise
        except AuthError as exc:
            kind = "auth.replay" if exc.code == "PK_STREAM_TOKEN_REPLAY" else "auth.denied"
            self.audit.record(kind, tenant, stream_id, "denied", right=right, error=exc.code)
            self._decide(right, "denied", str(exc), stream=stream_id)
            raise

    def buffered_total(self, tenant: str | None = None) -> int:
        with self._lock:
            return sum(len(s.buffer) for s in self._streams.values() if tenant is None or s.tenant == tenant)

    def _gate(self, tenant: str, workload: str) -> None:
        if self.disabled:
            raise ComponentDisabled("INV-17 is emergency-disabled")
        if ("tenant", tenant) in self.frozen_scopes or ("workload", workload) in self.frozen_scopes:
            raise ComponentDisabled("scope quarantined", tenant=tenant, workload=workload)

    # -- lifecycle
    def open(self, element_type: type, *, tenant: str, workload: str, token: str, stream_id: str,
             config: StreamConfig | None = None, versions: Mapping[str, Iterable[int]] | None = None) -> Stream:
        with self._lock:
            self._gate(tenant, workload)
            self._authorize(token, stream_id, tenant, workload, "open")
            for iface, offered in (versions or {k: (1,) for k in PROTOCOL_VERSIONS}).items():
                negotiate(iface, offered)
            if stream_id in self._streams:
                raise StreamError("stream id already open", stream_id=stream_id)
            if not self.breaker.allow():
                self._decide("open", "denied", "circuit open", tenant=tenant)
                raise CircuitOpen("admission circuit open")
            q = self.quota(tenant)
            open_for_tenant = sum(1 for s in self._streams.values() if s.tenant == tenant)
            if open_for_tenant >= q.max_streams:
                self.audit.record("quota.denied", tenant, stream_id, "denied", limit="max_streams")
                self._decide("open", "denied", "tenant stream quota reached", tenant=tenant, limit=q.max_streams)
                raise QuotaExceeded("tenant stream quota reached", tenant=tenant, max_streams=q.max_streams)
            s: Stream = Stream(element_type, config=config, tenant=tenant, workload=workload, stream_id=stream_id)
            self._streams[stream_id] = s
            self.audit.record("stream.open", tenant, stream_id, "allowed", workload=workload)
            self._decide("open", "allowed", "authorised, within quota", tenant=tenant, stream=stream_id)
            return s

    def get(self, stream_id: str, *, tenant: str, workload: str, token: str, right: str) -> Stream:
        with self._lock:
            self._gate(tenant, workload)
            s = self._streams.get(stream_id)
            if s is None:
                raise StreamNotFound("no such stream in this instance (streams do not survive restart)",
                                     stream_id=stream_id)
            if s.tenant != tenant or s.workload != workload:
                self.audit.record("authz.denied", tenant, stream_id, "denied", reason="cross-tenant access")
                raise AuthzDenied("stream belongs to another tenant/workload")
            self._authorize(token, stream_id, tenant, workload, right)
            return s

    def write(self, stream_id: str, element: object, *, tenant: str, workload: str, token: str,
              idempotency_key: str | None = None) -> bool:
        s = self.get(stream_id, tenant=tenant, workload=workload, token=token, right="write")
        with self._lock:
            q = self.quota(tenant)
            if self.buffered_total(tenant) >= q.max_buffered:
                self.shed_count += 1
                self._decide("write", "shed", "tenant buffered quota reached", tenant=tenant)
                raise QuotaExceeded("tenant buffered-element quota reached", tenant=tenant)
            if self.buffered_total() >= self.global_buffer_budget:
                self.shed_count += 1
                self.breaker.failure()
                self._decide("write", "shed", "instance buffer budget exhausted", tenant=tenant)
                raise LoadShed("instance buffer budget exhausted; retry with backoff")
        ok = s.write(element, idempotency_key=idempotency_key)
        self.breaker.success()
        return ok

    def transfer(self, stream_id: str, *, from_tenant: str, workload: str, token: str,
                 to_tenant: str, to_workload: str) -> Stream:
        """Explicit, authorised, single-use transfer across a tenant boundary (contract rule)."""
        with self._lock:
            s = self.get(stream_id, tenant=from_tenant, workload=workload, token=token, right="transfer")
            s.tenant, s.workload = to_tenant, to_workload
            self.audit.record("stream.transfer", from_tenant, stream_id, "allowed", to=to_tenant)
            return s

    def close(self, stream_id: str) -> None:
        with self._lock:
            self._streams.pop(stream_id, None)
            self._stall_since.pop(stream_id, None)

    def rebalance(self, pool: int) -> dict[str, int]:
        """Distribute ``pool`` credit fairly across tenants' open streams (C017/C028).

        Demand per stream is its unused credit headroom; the weighted deficit
        round-robin scheduler splits the pool across tenants, then each tenant's share is
        granted round-robin over its streams. Frozen/terminated streams get nothing.
        """
        with self._lock:
            eligible = [s for s in self._streams.values() if s.state in ("open", "credit_stalled")]
            demand: dict[str, int] = {}
            for s in eligible:
                demand[s.tenant] = demand.get(s.tenant, 0) + (s.config.max_credit - s.credit)
            sched = self._scheduler
            sched.weights = {t: self.quota(t).weight for t in demand}
            shares = sched.allocate(pool, demand)
            granted: dict[str, int] = {}
            for tenant, share in shares.items():
                mine = [s for s in eligible if s.tenant == tenant]
                while share > 0:
                    progressed = False
                    for s in mine:
                        if share and s.credit < s.config.max_credit:
                            s.grant(1)
                            granted[s.stream_id] = granted.get(s.stream_id, 0) + 1
                            share -= 1
                            progressed = True
                    if not progressed:
                        break
            self._decide("rebalance", "applied", "weighted fair share", pool=pool, tenants=len(shares))
            return granted

    def streams(self) -> list[Stream]:
        with self._lock:
            return list(self._streams.values())

    # -- emergency controls (C059)
    def _admin(self, principal: str, action: str) -> None:
        if principal not in self.admins:
            self.audit.record("authz.denied", principal, "inv17", "denied", action=action)
            raise AuthzDenied("principal may not operate emergency controls", principal=principal)

    def emergency_disable(self, principal: str, reason: str) -> None:
        self._admin(principal, "disable")
        with self._lock:
            self.disabled = True
            for s in self._streams.values():
                if not s.frozen:  # never overwrite the reason of an existing freeze
                    s.freeze(f"component disabled: {reason}")
            self.audit.record("control.disable", principal, "inv17", "applied", reason=reason)

    def enable(self, principal: str, reason: str) -> None:
        self._admin(principal, "enable")
        with self._lock:
            self.disabled = False
            for s in self._streams.values():
                # only lift freezes this control applied; scope quarantines and
                # individually frozen streams stay frozen until released explicitly
                if s.freeze_reason.startswith("component disabled:"):
                    s.unfreeze()
            self.audit.record("control.enable", principal, "inv17", "applied", reason=reason)

    def quarantine(self, principal: str, *, scope: str, value: str, reason: str) -> int:
        if scope not in ("tenant", "workload"):
            raise ValueError("scope must be 'tenant' or 'workload'")
        self._admin(principal, "freeze")
        with self._lock:
            self.frozen_scopes.add((scope, value))
            hit = [s for s in self._streams.values() if getattr(s, scope) == value]
            for s in hit:
                s.freeze(f"quarantine: {reason}")
            self.audit.record("control.freeze", principal, f"{scope}:{value}", "applied",
                              reason=reason, streams=len(hit))
            return len(hit)

    def release(self, principal: str, *, scope: str, value: str) -> None:
        self._admin(principal, "unfreeze")
        with self._lock:
            self.frozen_scopes.discard((scope, value))
            if not self.disabled:
                for s in self._streams.values():
                    if getattr(s, scope) == value and s.freeze_reason.startswith("quarantine:"):
                        s.unfreeze()
            self.audit.record("control.unfreeze", principal, f"{scope}:{value}", "applied")

    # -- health (C052)
    def health(self) -> HealthReport:
        p = self.health_policy
        now = self._clock()
        with self._lock:
            if self.disabled:
                return HealthReport("disabled", ["emergency disable active"], len(self._streams))
            reasons: list[str] = []
            status = "healthy"
            for sid, s in self._streams.items():
                st = s.stats()
                attempts = st.transferred + st.credit_stalls
                if st.state == "credit_stalled" and st.buffered == 0 and not (st.transferred or st.credit_stalls):
                    self._stall_since.pop(sid, None)
                    continue
                if st.state == "credit_stalled":
                    since = self._stall_since.setdefault(sid, now)
                    if now - since >= p.stall_seconds_unhealthy and st.credit_stalls:
                        status = "unhealthy"
                        reasons.append(f"{sid}: credit stalled for {now - since:.1f}s")
                else:
                    self._stall_since.pop(sid, None)
                if attempts >= p.min_attempts:
                    ratio = st.credit_stalls / attempts
                    if ratio >= p.stall_ratio_unhealthy:
                        status = "unhealthy"
                        reasons.append(f"{sid}: stall ratio {ratio:.2f}")
                    elif ratio >= p.stall_ratio_degraded and status == "healthy":
                        status = "degraded"
                        reasons.append(f"{sid}: stall ratio {ratio:.2f}")
                if st.buffered >= p.buffer_fill_degraded * s.config.max_buffer and status == "healthy":
                    status = "degraded"
                    reasons.append(f"{sid}: buffer {st.buffered}/{s.config.max_buffer}")
            if self.breaker.state != "closed" and status == "healthy":
                status = "degraded"
                reasons.append(f"admission breaker {self.breaker.state}")
            return HealthReport(status, reasons, len(self._streams))
