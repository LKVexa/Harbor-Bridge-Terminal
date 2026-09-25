"""Operational controls: time authority (09), admission/backpressure (12),
per-tenant quotas (13), quarantine/freeze (41), circuit breakers (42),
health/readiness (36) and decision/explain records (37).
"""
from __future__ import annotations

import threading
import time as _time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable

from .errors import DependencyUnavailable, Quarantined, QuotaExceeded, Throttled, TimeUntrusted

# ----------------------------------------------------------------- decisions (37)


class DecisionLog:
    """Bounded machine/operator-readable explain records for every automated
    drop, throttle, quarantine, sampling or policy decision."""

    def __init__(self, capacity: int = 10_000) -> None:
        self._d: deque = deque(maxlen=capacity)
        self._lock = threading.Lock()
        self.total = 0

    def record(self, *, decision: str, reason: str, subject: dict, rule: str, at: int, **extra: Any) -> dict:
        rec = {"decision": decision, "reason": reason, "rule": rule, "subject": dict(subject), "at": at, **extra}
        with self._lock:
            self._d.append(rec)
            self.total += 1
        return rec

    def recent(self, n: int = 100) -> list[dict]:
        with self._lock:
            return list(self._d)[-n:]


# ----------------------------------------------------------------- time (09)


class TimeAuthority:
    """Trusted-time policy.

    ``trusted_now`` comes from an injected trusted source (NTS/PTP/roughtime
    adapter in production).  Reporter timestamps are judged against it with a
    maximum skew; if the source has not synchronised within ``max_sync_age``
    the authority loses confidence and every time-dependent decision fails
    closed with ``time_untrusted`` rather than trusting the local clock.
    """

    def __init__(self, source: Callable[[], tuple[int, int]], *, max_skew: int, max_sync_age: int) -> None:
        # source() -> (now, last_sync_at) in integer seconds
        if max_skew < 0 or max_sync_age <= 0:
            raise ValueError("invalid time policy")
        self.source = source
        self.max_skew = max_skew
        self.max_sync_age = max_sync_age

    def now(self) -> int:
        try:
            now, last_sync = self.source()
        except Exception as exc:
            raise TimeUntrusted("trusted time source unavailable") from exc
        if now - last_sync > self.max_sync_age or last_sync > now:
            raise TimeUntrusted("time confidence lost: source not synchronised within policy")
        return now

    def check_reported(self, reported: int) -> int:
        now = self.now()
        if reported > now + self.max_skew:
            raise TimeUntrusted("reported time ahead of trusted time beyond max skew", skew=reported - now)
        return now


# ----------------------------------------------------------------- admission (12)


class TokenBucket:
    def __init__(self, rate: float, burst: float) -> None:
        if rate <= 0 or burst <= 0:
            raise ValueError("rate and burst must be positive")
        self.rate, self.burst = rate, burst
        self.tokens, self.t = burst, None

    def take(self, n: float, now: float) -> float:
        """Return 0.0 if admitted, else the seconds until it would be."""
        if self.t is None:
            self.t = now
        self.tokens = min(self.burst, self.tokens + (now - self.t) * self.rate)
        self.t = max(self.t, now)
        if n > self.burst:
            return float("inf")
        if self.tokens >= n:
            self.tokens -= n
            return 0.0
        return (n - self.tokens) / self.rate


class AdmissionController:
    """Per-tenant and per-reporter token buckets plus a global in-flight cap.

    Order: global queue limit -> tenant bucket -> reporter bucket.  A refusal
    carries ``retry_after`` (seconds, rounded up) and is recorded as a decision.
    Fairness: one tenant exhausting its bucket cannot consume another's.
    """

    def __init__(self, *, tenant_rate: float, tenant_burst: float, reporter_rate: float, reporter_burst: float,
                 max_inflight: int, decisions: DecisionLog | None = None) -> None:
        self._t = defaultdict(lambda: TokenBucket(tenant_rate, tenant_burst))
        self._r = defaultdict(lambda: TokenBucket(reporter_rate, reporter_burst))
        self.max_inflight = max_inflight
        self.inflight = 0
        self._lock = threading.Lock()
        self.decisions = decisions or DecisionLog()
        self.shed = 0

    def admit(self, *, tenant: str, reporter: str, cost: int, now: float) -> None:
        with self._lock:
            if self.inflight >= self.max_inflight:
                self.shed += 1
                self.decisions.record(decision="shed", reason="global in-flight limit", rule="ADM-GLOBAL",
                                      subject={"tenant": tenant, "reporter": reporter}, at=int(now))
                raise Throttled("server saturated", retry_after=1.0)
            wait = self._t[tenant].take(cost, now)
            if wait:
                self.decisions.record(decision="throttle", reason="tenant rate", rule="ADM-TENANT",
                                      subject={"tenant": tenant}, at=int(now), retry_after=wait)
                raise Throttled("tenant rate exceeded", retry_after=wait)
            wait = self._r[reporter].take(cost, now)
            if wait:
                self._t[tenant].tokens += cost  # refund: tenant was not the limiting party
                self.decisions.record(decision="throttle", reason="reporter rate", rule="ADM-REPORTER",
                                      subject={"reporter": reporter}, at=int(now), retry_after=wait)
                raise Throttled("reporter rate exceeded", retry_after=wait)
            self.inflight += 1

    def release(self) -> None:
        with self._lock:
            self.inflight = max(0, self.inflight - 1)


class TenantCardinalityQuota:
    """Per-tenant cap on distinct series keys, checked before allocation."""

    def __init__(self, default_limit: int, overrides: dict[str, int] | None = None,
                 decisions: DecisionLog | None = None) -> None:
        self.default = default_limit
        self.overrides = dict(overrides or {})
        self._series: dict[str, set] = defaultdict(set)
        self._lock = threading.Lock()
        self.decisions = decisions or DecisionLog()

    def limit(self, tenant: str) -> int:
        return self.overrides.get(tenant, self.default)

    def reserve(self, tenant: str, keys: list, now: int = 0) -> None:
        with self._lock:
            have = self._series[tenant]
            new = {k for k in keys if k not in have}
            if len(have) + len(new) > self.limit(tenant):
                self.decisions.record(decision="refuse", reason="tenant series quota", rule="QUOTA-SERIES",
                                      subject={"tenant": tenant}, at=now, used=len(have), requested=len(new),
                                      limit=self.limit(tenant))
                raise QuotaExceeded("tenant series quota exceeded", tenant=tenant, limit=self.limit(tenant))
            have.update(new)

    def usage(self) -> dict[str, int]:
        with self._lock:
            return {t: len(s) for t, s in self._series.items()}


# ----------------------------------------------------------------- quarantine (41)


class QuarantineRegistry:
    SCOPES = ("reporter", "site", "tenant")

    def __init__(self, audit=None, decisions: DecisionLog | None = None) -> None:
        self._q: dict[tuple[str, str], dict] = {}
        self._lock = threading.Lock()
        self._audit = audit
        self.decisions = decisions or DecisionLog()

    def freeze(self, scope: str, name: str, *, reason: str, actor: str, until: int | None = None) -> None:
        if scope not in self.SCOPES:
            raise ValueError("unknown quarantine scope")
        with self._lock:
            self._q[(scope, name)] = {"reason": reason, "actor": actor, "until": until}
        if self._audit:
            self._audit.append("quarantine", {"action": "freeze", "scope": scope, "name": name, "reason": reason}, actor=actor)

    def release(self, scope: str, name: str, *, actor: str) -> None:
        with self._lock:
            self._q.pop((scope, name), None)
        if self._audit:
            self._audit.append("quarantine", {"action": "release", "scope": scope, "name": name}, actor=actor)

    def check(self, *, reporter: str, site: str, tenant: str, now: int) -> None:
        with self._lock:
            for scope, name in (("reporter", reporter), ("site", site), ("tenant", tenant)):
                q = self._q.get((scope, name))
                if q and (q["until"] is None or now < q["until"]):
                    self.decisions.record(decision="refuse", reason=f"{scope} quarantined", rule="QUAR",
                                          subject={scope: name}, at=now)
                    raise Quarantined(f"{scope} is quarantined", scope=scope)

    def active(self) -> list[dict]:
        with self._lock:
            return [{"scope": s, "name": n, **v} for (s, n), v in sorted(self._q.items())]


# ----------------------------------------------------------------- breakers (42)


class CircuitBreaker:
    """closed -> open after ``threshold`` consecutive failures; open refuses
    for ``cooldown`` s; half-open admits one probe.  An open breaker on a
    *trust* dependency means refuse -- never bypass the dependency."""

    def __init__(self, name: str, *, threshold: int, cooldown: float) -> None:
        self.name, self.threshold, self.cooldown = name, threshold, cooldown
        self.state, self.failures, self.opened_at = "closed", 0, 0.0
        self._lock = threading.Lock()

    def call(self, fn: Callable[[], Any], now: float) -> Any:
        with self._lock:
            if self.state == "open":
                if now - self.opened_at < self.cooldown:
                    raise DependencyUnavailable(f"circuit {self.name} open", breaker=self.name)
                self.state = "half_open"
        try:
            out = fn()
        except Exception:
            with self._lock:
                self.failures += 1
                if self.state == "half_open" or self.failures >= self.threshold:
                    self.state, self.opened_at = "open", now
            raise
        with self._lock:
            self.state, self.failures = "closed", 0
        return out


# ----------------------------------------------------------------- health (36)


@dataclass
class HealthModel:
    version: str
    config_digest: Callable[[], str]
    dependencies: dict[str, Callable[[], bool]] = field(default_factory=dict)
    saturation: Callable[[], float] = lambda: 0.0
    capabilities: tuple = ()

    def report(self) -> dict:
        deps = {}
        for name, probe in sorted(self.dependencies.items()):
            try:
                deps[name] = "up" if probe() else "down"
            except Exception:
                deps[name] = "down"
        sat = float(self.saturation())
        degraded = any(v != "up" for v in deps.values()) or sat >= 0.9
        return {"schema": "GAP09-HEALTH/1", "version": self.version, "config_digest": self.config_digest(),
                "dependencies": deps, "saturation": round(sat, 4), "capabilities": list(self.capabilities),
                "live": True, "ready": not degraded, "mode": "degraded" if degraded else "normal"}
