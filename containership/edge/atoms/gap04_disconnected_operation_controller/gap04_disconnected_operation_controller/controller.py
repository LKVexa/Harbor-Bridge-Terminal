"""Core disconnected-operation state machine for GAP-04.

This module intentionally has no dependency on ``pk_core`` so the safety-critical
lease/tier/reconciliation behavior can be tested and embedded independently of
the conformance framework.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from threading import RLock
from typing import Final

TIERS: Final = ("full", "sustain", "freeze", "expired")
PERMITTED: Final = {
    "full": frozenset({"restart", "rebalance", "admit-known", "admit-new", "scale"}),
    "sustain": frozenset({"restart", "rebalance", "admit-known"}),
    "freeze": frozenset({"restart"}),
    "expired": frozenset(),
}
TIER_AT: Final = ((0, "full"), (30, "sustain"), (120, "freeze"))
MAX_SITE_CHARS: Final = 256
MAX_KIND_CHARS: Final = 64
MAX_SUBJECT_CHARS: Final = 512
MAX_REASON_CHARS: Final = 2048


class ControllerError(RuntimeError):
    """Base class for controller lifecycle and policy errors."""


class LeaseExpired(PermissionError, ControllerError):
    """Raised when an action requires a valid autonomy lease but none exists."""


class NotPermittedAtTier(PermissionError, ControllerError):
    """Raised when a decision is above the current degradation tier."""


class NotPartitioned(ControllerError):
    """Raised when an offline-only operation is attempted while connected."""


class PolicyStale(PermissionError, ControllerError):
    """Raised when cached policy exceeds the configured staleness bound."""


class ReconciliationRequired(ControllerError):
    """Raised when lease renewal would bypass a pending partition reconciliation."""


class DecisionJournalFull(ControllerError):
    """Raised when the bounded in-memory offline decision journal is full."""


def validate_tier_schedule(schedule) -> tuple:
    """Validate a tier schedule: starts at 0 with 'full', strictly increasing ages,
    tiers only narrow (never widen) as the partition ages (GAP04-C23)."""
    try:
        sched = tuple((int(a), str(n)) for a, n in schedule)
    except (TypeError, ValueError):
        raise ValueError("tier schedule must be a sequence of (age, tier) pairs") from None
    if not sched or sched[0] != (0, "full"):
        raise ValueError("tier schedule must start with (0, 'full')")
    order = [TIERS.index(n) if n in TIERS[:-1] else -1 for _, n in sched]
    if -1 in order:
        raise ValueError("tier schedule names must be full/sustain/freeze")
    for (a1, _), (a2, _) in zip(sched, sched[1:]):
        if a2 <= a1:
            raise ValueError("tier schedule ages must strictly increase")
    if order != sorted(order) or len(set(order)) != len(order):
        raise ValueError("tier schedule must strictly narrow authority")
    return sched


def _tick(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer tick")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def _positive_tick(name: str, value: int) -> int:
    value = _tick(name, value)
    if value == 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _strict_bool(name: str, value: bool) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{name} must be a bool")
    return value


def _bounded_text(name: str, value: str, max_chars: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    value = value.strip()
    if len(value) > max_chars:
        raise ValueError(f"{name} exceeds {max_chars} characters")
    return value


@dataclass
class AutonomyController:
    """Bounded local authority for one site during a control-plane partition.

    The controller is deliberately fail-closed. Mutable operations must move
    forward in logical time, local decisions are only legal while partitioned,
    stale policy is refused, and reconnect must reconcile before a lease can be
    renewed. The decision journal is bounded in memory; production durability is
    a separate component called out in ``MISSING_COMPONENTS.md``.
    """

    site: str
    granted_at: int = 0
    lease_ticks: int = 180
    partitioned_since: int | None = None
    policy_cached_at: int = 0
    max_policy_staleness_ticks: int = 180
    max_decisions: int = 10_000
    tier_schedule: tuple = TIER_AT
    lease_capabilities: frozenset | None = None
    tier_cap: str | None = None
    _decisions: list[dict] = field(default_factory=list, init=False, repr=False)
    _partition_epoch: int = field(default=0, init=False, repr=False)
    _last_event_at: int = field(default=0, init=False, repr=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.site = _bounded_text("site", self.site, MAX_SITE_CHARS)
        self.granted_at = _tick("granted_at", self.granted_at)
        self.lease_ticks = _positive_tick("lease_ticks", self.lease_ticks)
        self.policy_cached_at = _tick("policy_cached_at", self.policy_cached_at)
        self.max_policy_staleness_ticks = _positive_tick(
            "max_policy_staleness_ticks", self.max_policy_staleness_ticks
        )
        self.max_decisions = _positive_tick("max_decisions", self.max_decisions)
        self.tier_schedule = validate_tier_schedule(self.tier_schedule)
        if self.lease_capabilities is not None:
            self.lease_capabilities = frozenset(self.lease_capabilities)
            if not self.lease_capabilities <= PERMITTED["full"]:
                raise ValueError("lease_capabilities contains unknown actions")
        if self.tier_cap is not None and self.tier_cap not in TIERS:
            raise ValueError("tier_cap must be a known tier")
        if self.partitioned_since is not None:
            self.partitioned_since = _tick("partitioned_since", self.partitioned_since)
            if self.partitioned_since < self.granted_at:
                raise ValueError("partitioned_since cannot predate granted_at")
            if self.policy_cached_at > self.partitioned_since:
                raise ValueError("policy_cached_at cannot be after an already-active partition")
            self._partition_epoch = 1
        self._last_event_at = max(
            self.granted_at,
            self.policy_cached_at,
            self.partitioned_since if self.partitioned_since is not None else 0,
        )

    @property
    def decisions(self) -> list[dict]:
        """Return a defensive copy of pending offline decisions."""
        with self._lock:
            return deepcopy(self._decisions)

    @property
    def partition_epoch(self) -> int:
        return self._partition_epoch

    def _event_time(self, name: str, now: int) -> int:
        now = _tick(name, now)
        if now < self._last_event_at:
            raise ValueError(
                f"{self.site}: {name}={now} predates the last state-changing event "
                f"at {self._last_event_at}"
            )
        return now

    def expires_at(self) -> int:
        with self._lock:
            return self.granted_at + self.lease_ticks

    def lease_view(self, now: int) -> dict:
        """Return the versioned public lease representation."""
        with self._lock:
            now = _tick("now", now)
            expires_at = self.granted_at + self.lease_ticks
            return {
                "schema": "PK_AUTONOMY_LEASE/1",
                "site": self.site,
                "granted_at": self.granted_at,
                "expires_at": expires_at,
                "remaining_ticks": max(0, expires_at - now),
                "policy_cached_at": self.policy_cached_at,
                "max_policy_staleness_ticks": self.max_policy_staleness_ticks,
            }

    def cache_policy(self, now: int, *, control_plane_reachable: bool) -> int:
        """Refresh cached-policy age only while connected to the control plane."""
        with self._lock:
            _strict_bool("control_plane_reachable", control_plane_reachable)
            if not control_plane_reachable:
                raise PolicyStale(f"{self.site}: cannot refresh policy without control-plane contact")
            now = self._event_time("policy cache time", now)
            self._last_event_at = now
            if self.partitioned_since is not None:
                raise ReconciliationRequired(
                    f"{self.site}: reconcile the active partition before refreshing cached policy"
                )
            self.policy_cached_at = now
            self._last_event_at = now
            return self.policy_cached_at

    def renew(self, now: int, *, control_plane_reachable: bool) -> int:
        """Renew a lease only with control-plane contact and a clean lifecycle."""
        with self._lock:
            _strict_bool("control_plane_reachable", control_plane_reachable)
            if not control_plane_reachable:
                raise LeaseExpired(f"{self.site}: cannot renew a lease without control-plane contact")
            now = self._event_time("renewal time", now)
            self._last_event_at = now
            if now < self.granted_at:
                raise ValueError(
                    f"{self.site}: renewal at {now} predates the current grant at {self.granted_at}"
                )
            if self.partitioned_since is not None or self._decisions:
                raise ReconciliationRequired(
                    f"{self.site}: reconcile the active partition before renewing the lease"
                )
            self.granted_at = now
            return self.expires_at()

    def partition(self, now: int) -> None:
        """Enter partitioned mode without ever rewinding an existing partition."""
        with self._lock:
            now = self._event_time("partition time", now)
            if now < self.granted_at:
                raise ValueError(f"{self.site}: partition cannot predate the autonomy grant")
            if self.partitioned_since is None:
                if self.policy_cached_at > now:
                    raise ValueError(f"{self.site}: cached policy timestamp is in the future")
                self.partitioned_since = now
                self._partition_epoch += 1
            self._last_event_at = now

    def tier(self, now: int) -> str:
        with self._lock:
            now = _tick("now", now)
            expires_at = self.granted_at + self.lease_ticks
            if now < self.granted_at or now >= expires_at:
                return "expired"
            if self.partitioned_since is None or now < self.partitioned_since:
                return self.tier_cap if self.tier_cap in ("sustain", "freeze", "expired") else "full"
            age = now - self.partitioned_since
            current = "full"
            for at, name in self.tier_schedule:
                if age >= at:
                    current = name
            if self.tier_cap is not None and TIERS.index(self.tier_cap) > TIERS.index(current):
                current = self.tier_cap
            return current

    def permitted(self, now: int) -> frozenset:
        """Actions allowed right now: tier authority intersected with the lease's capability set."""
        allowed = PERMITTED[self.tier(now)]
        if self.lease_capabilities is not None:
            allowed = allowed & self.lease_capabilities
        return allowed

    def tier_view(self, now: int) -> dict:
        """Return the versioned public degradation-tier representation."""
        with self._lock:
            now = _tick("now", now)
            tier = self.tier(now)
            return {
                "schema": "PK_DEGRADATION_TIER/1",
                "site": self.site,
                "at": now,
                "tier": tier,
                "permitted": sorted(self.permitted(now)),
                "partition_epoch": self._partition_epoch,
            }

    def decide(self, kind: str, subject: str, now: int, *, reason: str | None = None) -> dict:
        """Take one bounded offline decision, or fail closed.

        Every accepted decision records the tier, policy age, lease boundary,
        partition epoch, and a reason suitable for later reconciliation.
        """
        with self._lock:
            kind = _bounded_text("decision kind", kind, MAX_KIND_CHARS)
            subject = _bounded_text("decision subject", subject, MAX_SUBJECT_CHARS)
            if self.partitioned_since is None:
                raise NotPartitioned(f"{self.site}: local autonomy decisions require an active partition")
            now = self._event_time("decision time", now)
            self._last_event_at = now
            if now < self.partitioned_since:
                raise ValueError(f"{self.site}: decision cannot predate the active partition")
            if self.policy_cached_at > now:
                raise ValueError(f"{self.site}: cached policy timestamp is in the future")
            tier = self.tier(now)
            if tier == "expired":
                raise LeaseExpired(f"{self.site}: autonomy lease expired at {self.expires_at()}")
            policy_age = now - self.policy_cached_at
            if policy_age > self.max_policy_staleness_ticks:
                raise PolicyStale(
                    f"{self.site}: cached policy age {policy_age} exceeds bound "
                    f"{self.max_policy_staleness_ticks}"
                )
            if kind not in self.permitted(now):
                raise NotPermittedAtTier(f"{self.site}: {kind!r} is not permitted at tier {tier!r}")
            if len(self._decisions) >= self.max_decisions:
                raise DecisionJournalFull(
                    f"{self.site}: offline decision journal limit {self.max_decisions} reached"
                )
            if reason is None:
                reason = f"permitted_by_tier={tier};policy_age={policy_age}"
            else:
                reason = _bounded_text("reason", reason, MAX_REASON_CHARS)
            record = {
                "sequence": len(self._decisions) + 1,
                "partition_epoch": self._partition_epoch,
                "kind": kind,
                "subject": subject,
                "at": now,
                "tier": tier,
                "policy_age": policy_age,
                "lease_granted_at": self.granted_at,
                "lease_expires_at": self.expires_at(),
                "reason": reason,
            }
            self._decisions.append(record)
            self._last_event_at = now
            return deepcopy(record)

    def reconcile(self, now: int) -> dict:
        """Close an active partition and return every local decision."""
        with self._lock:
            if self.partitioned_since is None:
                raise NotPartitioned(f"{self.site}: no active partition to reconcile")
            now = self._event_time("reconnect time", now)
            if now < self.partitioned_since:
                raise ValueError(f"{self.site}: reconnect cannot predate the partition")
            record = {
                "schema": "PK_RECONCILIATION_RECORD/1",
                "site": self.site,
                "partition_epoch": self._partition_epoch,
                "partitioned_since": self.partitioned_since,
                "reconnected_at": now,
                "lease_granted_at": self.granted_at,
                "lease_expires_at": self.expires_at(),
                "decisions": deepcopy(self._decisions),
                "decision_count": len(self._decisions),
                "max_policy_age": max((d["policy_age"] for d in self._decisions), default=0),
            }
            self._decisions.clear()
            self.partitioned_since = None
            self._last_event_at = now
            return record

    def reconnect(self, now: int, *, control_plane_reachable: bool) -> dict:
        """Safely reconcile an active partition and renew in one lifecycle operation."""
        with self._lock:
            _strict_bool("control_plane_reachable", control_plane_reachable)
            if not control_plane_reachable:
                raise LeaseExpired(f"{self.site}: reconnect requires control-plane contact")
            record = self.reconcile(now)
            record["renewed_until"] = self.renew(now, control_plane_reachable=True)
            return record

    def to_snapshot(self, include_decisions: bool = True) -> dict:
        """Serializable state for the durable store (GAP04-C17/C18)."""
        with self._lock:
            return {
                "site": self.site, "granted_at": self.granted_at, "lease_ticks": self.lease_ticks,
                "partitioned_since": self.partitioned_since, "policy_cached_at": self.policy_cached_at,
                "max_policy_staleness_ticks": self.max_policy_staleness_ticks, "max_decisions": self.max_decisions,
                "tier_schedule": [list(x) for x in self.tier_schedule],
                "lease_capabilities": sorted(self.lease_capabilities) if self.lease_capabilities is not None else None,
                "tier_cap": self.tier_cap, "decisions": deepcopy(self._decisions) if include_decisions else [],
                "partition_epoch": self._partition_epoch, "last_event_at": self._last_event_at,
            }

    @classmethod
    def from_snapshot(cls, snap: dict) -> "AutonomyController":
        c = cls(site=snap["site"], granted_at=snap["granted_at"], lease_ticks=snap["lease_ticks"],
                policy_cached_at=snap["policy_cached_at"], max_policy_staleness_ticks=snap["max_policy_staleness_ticks"],
                max_decisions=snap["max_decisions"], tier_schedule=tuple(tuple(x) for x in snap["tier_schedule"]),
                lease_capabilities=None if snap["lease_capabilities"] is None else frozenset(snap["lease_capabilities"]),
                tier_cap=snap["tier_cap"])
        c.partitioned_since = snap["partitioned_since"]
        c._decisions = deepcopy(snap["decisions"])
        c._partition_epoch = snap["partition_epoch"]
        c._last_event_at = snap["last_event_at"]
        return c

    def health(self, now: int) -> dict:
        """Return a dependency-free health snapshot for adapters/telemetry exporters."""
        with self._lock:
            now = _tick("now", now)
            policy_age = max(0, now - self.policy_cached_at)
            expires_at = self.granted_at + self.lease_ticks
            return {
                "site": self.site,
                "partitioned": self.partitioned_since is not None,
                "partition_epoch": self._partition_epoch,
                "tier": self.tier(now),
                "lease_remaining": max(0, expires_at - now),
                "pending_decisions": len(self._decisions),
                "policy_age": policy_age,
                "policy_stale": policy_age > self.max_policy_staleness_ticks,
            }
