"""Fail-closed runtime model for INV-44.

This module intentionally has no ``pk_core`` dependency so the security-critical
state machine can be unit-tested even when the wider conformance framework is
not installed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Final

#: Every one of these must be active. A partial set is not a hardened runtime.
REQUIRED_HARDENING: Final[frozenset[str]] = frozenset({
    "guard_pages",
    "cfi",
    "bounds_checks",
    "stack_limits",
    "fuel_metering",
    "output_verification",
})

#: Default linear-memory ceiling in 64-KiB pages. Engines may select a stricter
#: environment-specific value at construction time.
MEMORY_PAGE_CEILING: Final[int] = 512
MAX_LABEL_LENGTH: Final[int] = 256

_INSTANCE_FACTORY_TOKEN: Final[object] = object()


class HardeningIncomplete(PermissionError):
    """Raised when the engine is missing a required hardening feature."""


class OutputUnverified(PermissionError):
    """Raised when compiled module output fails verification."""


class FuelExhausted(RuntimeError):
    """Raised when a module attempts to consume more than its fuel budget."""


class MemoryCeiling(RuntimeError):
    """Raised when linear memory would grow past its configured ceiling."""


class InstanceConstructionDenied(PermissionError):
    """Raised when code tries to bypass :meth:`Engine.instantiate`."""


def _validated_label(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value or len(value) > MAX_LABEL_LENGTH:
        raise ValueError(f"{field_name} must contain 1..{MAX_LABEL_LENGTH} characters")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError(f"{field_name} must not contain control characters")
    return value


def _validated_int(value: object, field_name: str, *, minimum: int) -> int:
    # bool is an int subclass; accepting it makes security/resource settings
    # surprisingly coercible (True == 1), so reject it explicitly.
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value < minimum:
        relation = "positive" if minimum == 1 else f">= {minimum}"
        raise ValueError(f"{field_name} must be {relation}")
    return value


@dataclass(frozen=True, slots=True)
class Engine:
    """A Wasm engine that either has the complete hardening set or fails closed."""

    name: str
    active: frozenset[str]
    memory_page_ceiling: int = MEMORY_PAGE_CEILING

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _validated_label(self.name, "engine name"))
        if isinstance(self.active, (str, bytes)):
            raise TypeError("active hardening features must be an iterable of feature names")
        try:
            active = frozenset(self.active)
        except TypeError as exc:
            raise TypeError("active hardening features must be iterable") from exc
        for feature in active:
            _validated_label(feature, "hardening feature")
        object.__setattr__(self, "active", active)
        object.__setattr__(
            self,
            "memory_page_ceiling",
            _validated_int(self.memory_page_ceiling, "memory_page_ceiling", minimum=0),
        )

    def check(self) -> None:
        missing = REQUIRED_HARDENING - self.active
        if missing:
            raise HardeningIncomplete(
                f"{self.name}: hardening features inactive: {sorted(missing)}"
            )

    def instantiate(
        self,
        module: str,
        *,
        output_valid: bool,
        fuel: int,
        pages: int = 1,
    ) -> "Instance":
        """Validate all security gates before creating an executable instance."""
        self.check()
        module = _validated_label(module, "module")
        if not isinstance(output_valid, bool):
            raise TypeError("output_valid must be a bool produced by the verifier")
        if not output_valid:
            raise OutputUnverified(
                f"{module}: compiled output failed verification and will not execute"
            )
        fuel = _validated_int(fuel, "fuel", minimum=1)
        pages = _validated_int(pages, "pages", minimum=0)
        if pages > self.memory_page_ceiling:
            raise MemoryCeiling(
                f"{module}: {pages} initial pages exceed the "
                f"{self.memory_page_ceiling}-page ceiling"
            )
        return Instance(
            module,
            self,
            fuel,
            pages,
            _factory_token=_INSTANCE_FACTORY_TOKEN,
        )


@dataclass(frozen=True, slots=True, init=False)
class Instance:
    """A metered, memory-capped module instance with immutable public state.

    Instances can only be created through :meth:`Engine.instantiate`. Mutable
    accounting updates are serialized under a private lock and use
    ``object.__setattr__`` internally; ordinary callers cannot rewrite fuel,
    page, consumed, or trap state after construction.
    """

    module: str
    engine: Engine
    fuel: int
    pages: int
    consumed: int
    trapped: str | None
    _lock: Lock = field(compare=False, repr=False)

    def __init__(
        self,
        module: str,
        engine: Engine,
        fuel: int,
        pages: int,
        *,
        _factory_token: object | None = None,
    ) -> None:
        if _factory_token is not _INSTANCE_FACTORY_TOKEN:
            raise InstanceConstructionDenied(
                "Instance objects must be created by Engine.instantiate()"
            )
        if not isinstance(engine, Engine):
            raise TypeError("engine must be an Engine")
        # Re-check the engine at the construction boundary so a future refactor
        # cannot accidentally bypass the factory's validation sequence.
        engine.check()
        object.__setattr__(self, "module", _validated_label(module, "module"))
        object.__setattr__(self, "engine", engine)
        object.__setattr__(self, "fuel", _validated_int(fuel, "fuel", minimum=1))
        pages = _validated_int(pages, "pages", minimum=0)
        if pages > engine.memory_page_ceiling:
            raise MemoryCeiling(
                f"{module}: {pages} initial pages exceed the "
                f"{engine.memory_page_ceiling}-page ceiling"
            )
        object.__setattr__(self, "pages", pages)
        object.__setattr__(self, "consumed", 0)
        object.__setattr__(self, "trapped", None)
        object.__setattr__(self, "_lock", Lock())

    @property
    def remaining_fuel(self) -> int:
        return self.fuel - self.consumed

    def step(self, cost: int = 1) -> int:
        """Consume strictly positive fuel or trap when the budget is exceeded."""
        cost = _validated_int(cost, "step cost", minimum=1)
        with self._lock:
            if self.trapped:
                raise RuntimeError(f"{self.module}: already trapped ({self.trapped})")
            if cost > self.remaining_fuel:
                object.__setattr__(self, "trapped", "fuel exhausted")
                raise FuelExhausted(
                    f"{self.module}: request for {cost} fuel exceeds "
                    f"{self.remaining_fuel} remaining"
                )
            object.__setattr__(self, "consumed", self.consumed + cost)
            return self.remaining_fuel

    def grow(self, pages: int) -> int:
        """Grow memory atomically without crossing the engine's ceiling."""
        pages = _validated_int(pages, "memory growth", minimum=0)
        with self._lock:
            if self.trapped:
                raise RuntimeError(f"{self.module}: already trapped ({self.trapped})")
            target = self.pages + pages
            if target > self.engine.memory_page_ceiling:
                raise MemoryCeiling(
                    f"{self.module}: growing to {target} pages exceeds the "
                    f"{self.engine.memory_page_ceiling}-page ceiling"
                )
            object.__setattr__(self, "pages", target)
            return self.pages
