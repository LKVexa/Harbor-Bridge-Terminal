"""Standalone runtime model for INV-31 function execution lifecycle.

This module intentionally has no dependency on ``pk_core`` so the safety-critical
reuse, isolation, concurrency, eviction, and pool-capacity rules can be tested in
isolation.  The pk_core adapter lives in :mod:`component`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Any, ClassVar, Final

CONCURRENCY_LIMIT: Final[int] = 4
MAX_AGE: Final[int] = 300
MAX_POOL_INSTANCES: Final[int] = 1024
MAX_IDENTIFIER_LENGTH: Final[int] = 256


class ConcurrencyExceeded(RuntimeError):
    """Raised when an instance is already at its concurrency bound."""


class PoolCapacityExceeded(RuntimeError):
    """Raised when no additional instance may be created safely."""


class InstanceDestroyed(RuntimeError):
    """Raised when work is attempted on an instance that has been destroyed."""


class InstanceExpired(RuntimeError):
    """Raised when direct entry is attempted outside an instance's safe age window."""


def _validate_identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value or not value.strip():
        raise ValueError(f"{field_name} must be non-empty and non-blank")
    if len(value) > MAX_IDENTIFIER_LENGTH:
        raise ValueError(
            f"{field_name} exceeds the {MAX_IDENTIFIER_LENGTH}-character safety limit")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError(f"{field_name} contains control characters")
    return value


def _validate_tick(value: int, field_name: str = "now") -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be a non-negative integer tick")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


def _validate_positive_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be a positive integer")
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")
    return value


@dataclass
class Instance:
    """One function instance with immutable tenant/version identity.

    Scratch state is maintained per active invocation scope.  This matters when
    concurrency is greater than one: completing one invocation must never clear
    another invocation's state.
    """

    name: str
    tenant: str
    version: str
    created_at: int
    concurrency_limit: int = CONCURRENCY_LIMIT
    max_age: int = MAX_AGE
    in_flight: int = field(default=0, init=False)
    invocations: int = field(default=0, init=False)
    last_used_at: int = field(init=False)
    scratch: dict[str, dict[str, Any]] = field(default_factory=dict, init=False, repr=False)
    _scope_counter: int = field(default=0, init=False, repr=False)
    _destroyed: bool = field(default=False, init=False, repr=False)
    _identity_sealed: bool = field(default=False, init=False, repr=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False, compare=False)

    _IMMUTABLE_FIELDS: ClassVar[tuple[str, ...]] = ("name", "tenant", "version", "created_at")

    def __post_init__(self) -> None:
        _validate_identifier(self.name, "name")
        _validate_identifier(self.tenant, "tenant")
        _validate_identifier(self.version, "version")
        _validate_tick(self.created_at, "created_at")
        _validate_positive_int(self.concurrency_limit, "concurrency_limit")
        _validate_positive_int(self.max_age, "max_age")
        object.__setattr__(self, "last_used_at", self.created_at)
        object.__setattr__(self, "_identity_sealed", True)

    def __setattr__(self, name: str, value: Any) -> None:
        if (name in self._IMMUTABLE_FIELDS
                and getattr(self, "_identity_sealed", False)):
            raise AttributeError(f"{name} is immutable for the lifetime of an instance")
        object.__setattr__(self, name, value)

    @property
    def destroyed(self) -> bool:
        with self._lock:
            return self._destroyed

    def reusable_for(self, tenant: str, version: str, now: int) -> bool:
        tenant = _validate_identifier(tenant, "tenant")
        version = _validate_identifier(version, "version")
        now = _validate_tick(now)
        with self._lock:
            age = now - self.created_at
            return (
                not self._destroyed
                and self.tenant == tenant
                and self.version == version
                and 0 <= age <= self.max_age
                and self.in_flight < self.concurrency_limit
            )

    def enter(self, now: int | None = None) -> str:
        """Start one invocation and return its opaque scratch-scope token."""
        if now is not None:
            now = _validate_tick(now)
        with self._lock:
            if self._destroyed:
                raise InstanceDestroyed(f"{self.name}: instance has been destroyed")
            if now is not None:
                age = now - self.created_at
                if age < 0 or age > self.max_age:
                    raise InstanceExpired(
                        f"{self.name}: age {age} is outside the reusable window 0..{self.max_age}")
            if self.in_flight >= self.concurrency_limit:
                raise ConcurrencyExceeded(
                    f"{self.name}: already at {self.concurrency_limit} concurrent invocations")
            self._scope_counter += 1
            scope_id = f"scope-{self._scope_counter}"
            self.scratch[scope_id] = {}
            self.in_flight += 1
            self.invocations += 1
            if now is not None:
                self.last_used_at = now
            self._check_invariants_locked()
            return scope_id

    def set_scratch(self, scope_id: str, key: str, value: Any) -> None:
        _validate_identifier(scope_id, "scope_id")
        _validate_identifier(key, "scratch key")
        with self._lock:
            if scope_id not in self.scratch:
                raise KeyError(f"{self.name}: unknown or completed invocation scope {scope_id!r}")
            self.scratch[scope_id][key] = value

    def has_scope(self, scope_id: str) -> bool:
        _validate_identifier(scope_id, "scope_id")
        with self._lock:
            return scope_id in self.scratch

    def scope_snapshot(self, scope_id: str) -> dict[str, Any]:
        _validate_identifier(scope_id, "scope_id")
        with self._lock:
            if scope_id not in self.scratch:
                raise KeyError(f"{self.name}: unknown or completed invocation scope {scope_id!r}")
            return dict(self.scratch[scope_id])

    def leave(self, scope_id: str | None = None) -> None:
        """Complete one invocation and clear only that invocation's scratch state.

        Omitting ``scope_id`` remains compatible for the single-in-flight case.
        It is rejected when multiple scopes are active because guessing which
        invocation ended would risk cross-request state corruption.
        """
        with self._lock:
            if self.in_flight <= 0 or not self.scratch:
                raise RuntimeError(f"{self.name}: leave() without a matching enter()")
            if scope_id is None:
                if len(self.scratch) != 1:
                    raise RuntimeError(
                        f"{self.name}: scope_id is required when multiple invocations are active")
                scope_id = next(iter(self.scratch))
            if scope_id not in self.scratch:
                raise RuntimeError(f"{self.name}: leave() for unknown scope {scope_id!r}")
            del self.scratch[scope_id]
            self.in_flight -= 1
            self._check_invariants_locked()

    def destroy(self) -> None:
        """Destroy an idle instance; active work is never terminated implicitly."""
        with self._lock:
            if self.in_flight:
                raise RuntimeError(f"{self.name}: cannot destroy {self.in_flight} in-flight invocation(s)")
            self.scratch.clear()
            self._destroyed = True
            self._check_invariants_locked()

    def snapshot(self, now: int) -> dict[str, Any]:
        """Return diagnostics without exposing invocation scratch contents."""
        now = _validate_tick(now)
        with self._lock:
            self._check_invariants_locked()
            return {
                "name": self.name,
                "tenant": self.tenant,
                "version": self.version,
                "created_at": self.created_at,
                "last_used_at": self.last_used_at,
                "age": now - self.created_at,
                "in_flight": self.in_flight,
                "invocations": self.invocations,
                "destroyed": self._destroyed,
            }

    def _check_invariants_locked(self) -> None:
        if self.in_flight != len(self.scratch):
            raise RuntimeError(
                f"{self.name}: internal invariant violated: in_flight={self.in_flight}, "
                f"scratch_scopes={len(self.scratch)}")
        if self.in_flight < 0 or self.in_flight > self.concurrency_limit:
            raise RuntimeError(f"{self.name}: invalid in_flight count {self.in_flight}")
        if self._destroyed and self.in_flight:
            raise RuntimeError(f"{self.name}: destroyed instance still has in-flight work")


@dataclass
class FunctionPool:
    """Thread-safe function-instance pool with bounded resource growth."""

    concurrency_limit: int = CONCURRENCY_LIMIT
    max_age: int = MAX_AGE
    max_instances: int = MAX_POOL_INSTANCES
    instances: list[Instance] = field(default_factory=list)
    next_id: int = 0
    clears: int = 0
    invocations: int = 0
    cold_starts: int = 0
    warm_starts: int = 0
    capacity_rejections: int = 0
    rollback_evictions: int = 0
    _lock: RLock = field(default_factory=RLock, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        _validate_positive_int(self.concurrency_limit, "concurrency_limit")
        _validate_positive_int(self.max_age, "max_age")
        _validate_positive_int(self.max_instances, "max_instances")
        if len(self.instances) > self.max_instances:
            raise ValueError("initial instances exceed max_instances")
        seen: set[str] = set()
        for instance in self.instances:
            if not isinstance(instance, Instance):
                raise TypeError("instances must contain Instance objects")
            if instance.name in seen:
                raise ValueError(f"duplicate instance name {instance.name!r}")
            if instance.destroyed:
                raise ValueError(f"preloaded instance {instance.name!r} is already destroyed")
            if (instance.concurrency_limit != self.concurrency_limit
                    or instance.max_age != self.max_age):
                raise ValueError("preloaded instance limits must match pool limits")
            seen.add(instance.name)
            if instance.name.startswith("fn-") and instance.name[3:].isdigit():
                self.next_id = max(self.next_id, int(instance.name[3:]))

    def _evict_aged_locked(self, now: int) -> list[str]:
        evicted: list[str] = []
        # 4.3.0 (C065): read age/in_flight directly instead of building a full
        # diagnostic snapshot dict per instance on every invocation.
        for instance in list(self.instances):
            with instance._lock:
                age = now - instance.created_at
                idle = instance.in_flight == 0
            if idle and (age < 0 or age > self.max_age):
                instance.destroy()
                self.instances.remove(instance)
                evicted.append(instance.name)
                if age < 0:
                    self.rollback_evictions += 1
        return evicted

    def evict_aged(self, now: int) -> list[str]:
        now = _validate_tick(now)
        with self._lock:
            return self._evict_aged_locked(now)

    def _evict_one_idle_for_capacity_locked(self, now: int) -> str | None:
        idle: list[tuple[int, int, str, Instance]] = []
        for instance in self.instances:
            state = instance.snapshot(now)
            if state["in_flight"] == 0:
                idle.append((state["last_used_at"], state["created_at"], state["name"], instance))
        if not idle:
            return None
        _, _, _, victim = min(idle, key=lambda item: item[:3])
        victim.destroy()
        self.instances.remove(victim)
        return victim.name

    def _new_instance_locked(
        self, tenant: str, version: str, now: int
    ) -> tuple[Instance, str | None]:
        capacity_evicted: str | None = None
        if len(self.instances) >= self.max_instances:
            capacity_evicted = self._evict_one_idle_for_capacity_locked(now)
            if capacity_evicted is None:
                self.capacity_rejections += 1
                raise PoolCapacityExceeded(
                    f"pool is at max_instances={self.max_instances} and every instance is busy")
        names = {instance.name for instance in self.instances}
        while True:
            self.next_id += 1
            name = f"fn-{self.next_id}"
            if name not in names:
                break
        instance = Instance(
            name,
            tenant,
            version,
            now,
            concurrency_limit=self.concurrency_limit,
            max_age=self.max_age,
        )
        self.instances.append(instance)
        return instance, capacity_evicted

    def invoke(self, *, tenant: str, version: str, now: int) -> dict[str, Any]:
        tenant = _validate_identifier(tenant, "tenant")
        version = _validate_identifier(version, "version")
        now = _validate_tick(now)

        with self._lock:
            evicted = self._evict_aged_locked(now)
            selected: Instance | None = None
            scope_id: str | None = None
            for candidate in self.instances:
                # 4.3.0 (C065): cheap exact-identity prefilter; reusable_for still
                # re-checks the full rule, so the decision is unchanged.
                if candidate.tenant != tenant or candidate.version != version:
                    continue
                if not candidate.reusable_for(tenant, version, now):
                    continue
                try:
                    scope_id = candidate.enter(now)
                except ConcurrencyExceeded:
                    continue
                selected = candidate
                break

            cold = selected is None
            if cold:
                selected, capacity_evicted = self._new_instance_locked(tenant, version, now)
                if capacity_evicted is not None:
                    evicted.append(capacity_evicted)
                scope_id = selected.enter(now)
                self.cold_starts += 1
                decision_reason = "no_reusable_same_tenant_same_version_instance"
            else:
                self.warm_starts += 1
                decision_reason = "reused_same_tenant_same_version_instance"
            self.invocations += 1
            invocation_count = selected.snapshot(now)["invocations"]

        if scope_id is None:  # defensive: impossible if the selection code above is correct
            raise RuntimeError("invocation scope was not allocated")

        try:
            selected.set_scratch(scope_id, "request", {"tenant": tenant, "tick": now})
        finally:
            selected.leave(scope_id)
            with self._lock:
                self.clears += 1

        return {
            "schema": "PK_INVOCATION/1",
            "instance": selected.name,
            "tenant": tenant,
            "version": version,
            "cold": cold,
            "decision_reason": decision_reason,
            "invocations_on_instance": invocation_count,
            "scratch_cleared": not selected.has_scope(scope_id),
            "evicted": evicted,
        }

    def destroy_idle(self, *, tenant: str | None = None, version: str | None = None) -> list[str]:
        """Operator control for safely draining/quarantining idle instances."""
        if tenant is not None:
            tenant = _validate_identifier(tenant, "tenant")
        if version is not None:
            version = _validate_identifier(version, "version")
        destroyed: list[str] = []
        with self._lock:
            for instance in list(self.instances):
                state = instance.snapshot(instance.last_used_at)
                if state["in_flight"]:
                    continue
                if tenant is not None and instance.tenant != tenant:
                    continue
                if version is not None and instance.version != version:
                    continue
                instance.destroy()
                self.instances.remove(instance)
                destroyed.append(instance.name)
        return destroyed

    def pool_snapshot(self, now: int) -> dict[str, Any]:
        """Return the PK_FUNCTION_POOL/1 diagnostics view.

        Aged or clock-invalid idle instances are removed first.  Invocation
        scratch data is deliberately excluded from the returned structure.
        """
        now = _validate_tick(now)
        with self._lock:
            evicted = self._evict_aged_locked(now)
            total = self.invocations
            return {
                "schema": "PK_FUNCTION_POOL/1",
                "ready": True,
                "configuration": {
                    "concurrency_limit": self.concurrency_limit,
                    "max_age": self.max_age,
                    "max_instances": self.max_instances,
                },
                "stats": {
                    "invocations": total,
                    "cold_starts": self.cold_starts,
                    "warm_starts": self.warm_starts,
                    "warm_rate": (self.warm_starts / total) if total else None,
                    "state_clears": self.clears,
                    "capacity_rejections": self.capacity_rejections,
                    "clock_rollback_evictions": self.rollback_evictions,
                },
                "evicted": evicted,
                "instances": [instance.snapshot(now) for instance in self.instances],
            }
