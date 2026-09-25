"""Deterministic elasticity controller used by PLN-05.

This module intentionally has no dependency on ``pk_core`` so the safety-critical
capacity algorithm can be unit-tested in isolation.  The framework adapter lives
in :mod:`pln05_elasticity_plane.component`.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real


def _require_int(name: str, value: object, *, minimum: int | None = None) -> int:
    """Validate an integer configuration value without accepting ``bool``."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an int")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _require_finite_real(name: str, value: object) -> float:
    """Validate a finite real number without accepting ``bool``."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite real number")
    return result


@dataclass(frozen=True, slots=True)
class Limits:
    """Declared capacity envelope and hysteresis parameters for one workload.

    ``floor`` and ``ceiling`` are non-negative integer capacity targets.
    ``grace_samples`` is the number of consecutive low-utilisation observations
    required before a scale-down is allowed.
    """

    floor: int = 0
    ceiling: int = 10
    scale_up_at: float = 0.75
    scale_down_at: float = 0.25
    grace_samples: int = 3

    def __post_init__(self) -> None:
        floor = _require_int("floor", self.floor, minimum=0)
        ceiling = _require_int("ceiling", self.ceiling, minimum=0)
        _require_int("grace_samples", self.grace_samples, minimum=1)
        scale_up_at = _require_finite_real("scale_up_at", self.scale_up_at)
        scale_down_at = _require_finite_real("scale_down_at", self.scale_down_at)

        if ceiling < floor:
            raise ValueError(f"inconsistent limits: floor={floor} ceiling={ceiling}")
        if not 0.0 < scale_down_at < scale_up_at < 1.0:
            raise ValueError("thresholds must satisfy 0 < scale_down_at < scale_up_at < 1")


#: Stable machine-readable outcome/reason codes for every ``observe`` result.
REASONS: dict[str, tuple[str, str]] = {
    "scale-up": ("scale-up", "R_SCALE_UP"),
    "scale-down": ("scale-down", "R_SCALE_DOWN"),
    "hold: at ceiling": ("constrained-hold", "R_AT_CEILING"),
    "hold: at floor": ("constrained-hold", "R_AT_FLOOR"),
    "hold: within scale-down grace period": ("hold", "R_GRACE_HOLD"),
    "hold: within band": ("hold", "R_IN_BAND"),
}


class ElasticityController:
    """Hysteretic capacity controller for one workload.

    Scale-up is immediate.  Scale-down requires ``grace_samples`` consecutive
    observations at or below the low-water mark.  Every emitted target remains
    inside the active ``[floor, ceiling]`` envelope.

    The ``lower_ceiling`` operation is deliberately monotonic: callers cannot
    use a method intended for emergency/site/power caps to increase capacity or
    silently push the effective ceiling below the declared floor.
    """

    def __init__(self, limits: Limits, current: int | None = None):
        if not isinstance(limits, Limits):
            raise TypeError("limits must be a Limits instance")
        self.limits = limits
        current = limits.floor if current is None else current
        _require_int("current", current)
        self.current = max(limits.floor, min(current, limits.ceiling))
        self._below = 0
        self.suppressed = 0

    def lower_ceiling(self, ceiling: int) -> None:
        """Apply a stricter externally imposed ceiling.

        The requested cap must remain at or above the declared floor and may not
        exceed the currently active ceiling.  Invalid caps fail closed rather
        than mutating the floor or expanding authority.
        """
        ceiling = _require_int("ceiling", ceiling, minimum=0)
        if ceiling < self.limits.floor:
            raise ValueError(
                f"external ceiling {ceiling} is below declared floor {self.limits.floor}"
            )
        if ceiling > self.limits.ceiling:
            raise ValueError(
                f"lower_ceiling cannot raise ceiling from {self.limits.ceiling} to {ceiling}"
            )
        if ceiling == self.limits.ceiling:
            return

        self.limits = Limits(
            self.limits.floor,
            ceiling,
            self.limits.scale_up_at,
            self.limits.scale_down_at,
            self.limits.grace_samples,
        )
        self.current = min(self.current, ceiling)
        # A limit change invalidates pending low-water evidence collected under
        # the previous envelope.
        self._below = 0

    def observe(self, utilisation: float) -> tuple[int, str]:
        """Feed one demand sample and return ``(target, reason)``.

        Utilisation must be finite.  Values above 1.0 are permitted because a
        demand signal can represent oversubscription; negative values are
        rejected as physically invalid for this contract.
        """
        utilisation = _require_finite_real("utilisation", utilisation)
        if utilisation < 0.0:
            raise ValueError("utilisation must be >= 0")

        lim = self.limits
        if utilisation >= lim.scale_up_at:
            self._below = 0
            if self.current >= lim.ceiling:
                target, reason = self.current, "hold: at ceiling"
            else:
                target = min(self.current + max(1, self.current), lim.ceiling)
                reason = "scale-up"
        elif utilisation <= lim.scale_down_at:
            if self.current <= lim.floor:
                self._below = 0
                target, reason = self.current, "hold: at floor"
            else:
                self._below += 1
                if self._below >= lim.grace_samples:
                    self._below = 0
                    target, reason = max(self.current // 2, lim.floor), "scale-down"
                else:
                    self.suppressed += 1
                    target, reason = self.current, "hold: within scale-down grace period"
        else:
            self._below = 0
            target, reason = self.current, "hold: within band"

        self.current = max(lim.floor, min(target, lim.ceiling))
        return self.current, reason

    # -- persistence (MC-18) -------------------------------------------------
    def snapshot(self) -> dict:
        """Must-persist state: restoring it reproduces identical future decisions."""
        lim = self.limits
        return {"current": self.current, "below": self._below, "suppressed": self.suppressed,
                "limits": {"floor": lim.floor, "ceiling": lim.ceiling, "scale_up_at": lim.scale_up_at,
                           "scale_down_at": lim.scale_down_at, "grace_samples": lim.grace_samples}}

    @classmethod
    def restore(cls, snap: dict) -> "ElasticityController":
        """Rebuild from :meth:`snapshot`; every field is re-validated (fail closed)."""
        ctl = cls(Limits(**snap["limits"]), current=snap["current"])
        if ctl.current != snap["current"]:
            raise ValueError("persisted current is outside the persisted envelope")
        below = _require_int("below", snap["below"], minimum=0)
        if below >= ctl.limits.grace_samples:
            raise ValueError("persisted grace counter exceeds grace_samples")
        ctl._below = below
        ctl.suppressed = _require_int("suppressed", snap["suppressed"], minimum=0)
        return ctl
