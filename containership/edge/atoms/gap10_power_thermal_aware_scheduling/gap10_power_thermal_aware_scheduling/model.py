"""Deterministic power/thermal constraint kernel for GAP-10.

This module intentionally depends only on the Python standard library so the
scheduling logic can be unit-tested without the wider ``pk_core`` estate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Final

BANDS: Final[tuple[str, ...]] = ("nominal", "elevated", "critical", "emergency")
BAND_RANK: Final[dict[str, int]] = {band: index for index, band in enumerate(BANDS)}


class PolicyError(ValueError):
    """Raised when a thermal/power policy is internally unsafe or inconsistent."""


def _finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value))


@dataclass(frozen=True, slots=True)
class PowerThermalPolicy:
    """Validated policy used to translate telemetry into a capacity ceiling.

    Temperature thresholds are degrees Celsius. Power thresholds are fractions
    of the configured node power budget. Recovery margins prevent flapping.
    """

    min_valid_temperature_c: float = -100.0
    elevated_c: float = 75.0
    critical_c: float = 85.0
    emergency_c: float = 95.0
    max_valid_temperature_c: float = 250.0
    recovery_margin_c: float = 5.0

    battery_reserve: float = 0.15
    battery_recovery_margin: float = 0.02

    power_elevated_ratio: float = 0.80
    power_critical_ratio: float = 0.90
    power_emergency_ratio: float = 1.00
    power_recovery_margin: float = 0.05

    max_sensor_age_seconds: float = 30.0
    max_future_skew_seconds: float = 5.0

    nominal_ceiling: float = 1.00
    elevated_ceiling: float = 0.60
    critical_ceiling: float = 0.25
    emergency_ceiling: float = 0.00

    def __post_init__(self) -> None:
        numeric_fields = (
            "min_valid_temperature_c", "elevated_c", "critical_c", "emergency_c",
            "max_valid_temperature_c", "recovery_margin_c",
            "battery_reserve", "battery_recovery_margin",
            "power_elevated_ratio", "power_critical_ratio", "power_emergency_ratio",
            "power_recovery_margin", "max_sensor_age_seconds", "max_future_skew_seconds",
            "nominal_ceiling", "elevated_ceiling", "critical_ceiling", "emergency_ceiling",
        )
        for name in numeric_fields:
            if not _finite_number(getattr(self, name)):
                raise PolicyError(f"{name} must be a finite number")

        if not (
            self.min_valid_temperature_c < self.elevated_c < self.critical_c
            < self.emergency_c < self.max_valid_temperature_c
        ):
            raise PolicyError(
                "temperature limits must satisfy min_valid < elevated < critical < emergency < max_valid"
            )
        min_temp_gap = min(self.critical_c - self.elevated_c, self.emergency_c - self.critical_c)
        if not 0.0 < self.recovery_margin_c < min_temp_gap:
            raise PolicyError("recovery_margin_c must be > 0 and smaller than each temperature band gap")

        if not 0.0 <= self.battery_reserve < 1.0:
            raise PolicyError("battery_reserve must be within [0, 1)")
        if not 0.0 <= self.battery_recovery_margin <= 1.0 - self.battery_reserve:
            raise PolicyError("battery_recovery_margin exceeds available battery range")

        if not 0.0 < self.power_elevated_ratio < self.power_critical_ratio < self.power_emergency_ratio:
            raise PolicyError("power ratios must satisfy 0 < elevated < critical < emergency")
        min_power_gap = min(
            self.power_critical_ratio - self.power_elevated_ratio,
            self.power_emergency_ratio - self.power_critical_ratio,
        )
        if not 0.0 < self.power_recovery_margin < min_power_gap:
            raise PolicyError("power_recovery_margin must be > 0 and smaller than each power band gap")

        if self.max_sensor_age_seconds <= 0.0:
            raise PolicyError("max_sensor_age_seconds must be > 0")
        if self.max_future_skew_seconds < 0.0:
            raise PolicyError("max_future_skew_seconds must be >= 0")

        ceilings = (
            self.nominal_ceiling,
            self.elevated_ceiling,
            self.critical_ceiling,
            self.emergency_ceiling,
        )
        if any(not 0.0 <= value <= 1.0 for value in ceilings):
            raise PolicyError("capacity ceiling fractions must be within [0, 1]")
        if not self.nominal_ceiling >= self.elevated_ceiling >= self.critical_ceiling >= self.emergency_ceiling:
            raise PolicyError("capacity ceiling fractions must decrease with severity")
        if self.emergency_ceiling != 0.0:
            raise PolicyError("emergency_ceiling must be 0 to guarantee exclusion")

    @property
    def band_ceiling(self) -> dict[str, float]:
        return {
            "nominal": self.nominal_ceiling,
            "elevated": self.elevated_ceiling,
            "critical": self.critical_ceiling,
            "emergency": self.emergency_ceiling,
        }


DEFAULT_POLICY: Final[PowerThermalPolicy] = PowerThermalPolicy()

# Compatibility aliases retained for sibling code that imported v4.1 constants.
ELEVATED: Final[float] = DEFAULT_POLICY.elevated_c
CRITICAL: Final[float] = DEFAULT_POLICY.critical_c
EMERGENCY: Final[float] = DEFAULT_POLICY.emergency_c
RECOVERY_MARGIN: Final[float] = DEFAULT_POLICY.recovery_margin_c
BATTERY_RESERVE: Final[float] = DEFAULT_POLICY.battery_reserve
BAND_CEILING: Final[dict[str, float]] = DEFAULT_POLICY.band_ceiling


@dataclass(slots=True)
class ThermalState:
    """One node's current constrained state and the ceiling it implies.

    ``update`` escalates immediately and recovers only after hysteresis margins
    have been cleared. Missing, non-finite, stale, or implausibly future thermal
    evidence is fail-closed to at least ``critical``.
    """

    node: str
    temperature: float | None = None
    battery: float | None = None
    band: str = "critical"
    power_draw_watts: float | None = None
    power_budget_watts: float | None = None
    policy: PowerThermalPolicy = field(default_factory=PowerThermalPolicy)
    telemetry_status: str = "unobserved"
    last_observed_at: float | None = None
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.node, str) or not self.node.strip():
            raise ValueError("node must be a non-empty string")
        if len(self.node) > 256 or any(ord(ch) < 32 or ord(ch) == 127 for ch in self.node):
            raise ValueError("node must be <= 256 characters and contain no control characters")
        if self.band not in BAND_RANK:
            raise ValueError(f"unknown initial band: {self.band!r}")

    @staticmethod
    def _normalize_temperature(value: object) -> float | None:
        if value is None or not _finite_number(value):
            return None
        return float(value)

    @staticmethod
    def _normalize_power_draw(value: object) -> float | None:
        if value is None or not _finite_number(value) or float(value) < 0.0:
            return None
        return float(value)

    @staticmethod
    def _validate_battery(value: object, node: str) -> float | None:
        if value is None:
            return None
        if not _finite_number(value) or not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"{node}: battery fraction must be within [0, 1], got {value!r}")
        return float(value)

    @staticmethod
    def _validate_power_budget(value: object, node: str) -> float | None:
        if value is None:
            return None
        if not _finite_number(value) or float(value) <= 0.0:
            raise ValueError(f"{node}: power budget must be a positive finite number, got {value!r}")
        return float(value)

    def _temperature_band(self, *, stale: bool) -> tuple[str, str]:
        if stale:
            return "critical", f"telemetry {self.telemetry_status}; thermal evidence is not usable"
        if self.temperature is None:
            return "critical", "no usable temperature evidence"
        if self.temperature >= self.policy.emergency_c:
            return "emergency", f"temperature {self.temperature:.1f}C >= emergency {self.policy.emergency_c:.1f}C"
        if self.temperature >= self.policy.critical_c:
            return "critical", f"temperature {self.temperature:.1f}C >= critical {self.policy.critical_c:.1f}C"
        if self.temperature >= self.policy.elevated_c:
            return "elevated", f"temperature {self.temperature:.1f}C >= elevated {self.policy.elevated_c:.1f}C"
        return "nominal", f"temperature {self.temperature:.1f}C nominal"

    def _battery_band(self) -> tuple[str, str] | None:
        if self.battery is None:
            return None
        if self.battery < self.policy.battery_reserve:
            return "critical", (
                f"battery {self.battery:.1%} below reserve {self.policy.battery_reserve:.1%}"
            )
        return "nominal", f"battery {self.battery:.1%} above reserve"

    def _power_band(self, *, stale: bool) -> tuple[str, str] | None:
        if self.power_draw_watts is None and self.power_budget_watts is None:
            return None
        if stale or self.power_draw_watts is None or self.power_budget_watts is None:
            return "critical", "power evidence incomplete or stale"
        ratio = self.power_draw_watts / self.power_budget_watts
        if ratio >= self.policy.power_emergency_ratio:
            return "emergency", (
                f"power ratio {ratio:.1%} >= emergency {self.policy.power_emergency_ratio:.1%}"
            )
        if ratio >= self.policy.power_critical_ratio:
            return "critical", f"power ratio {ratio:.1%} >= critical {self.policy.power_critical_ratio:.1%}"
        if ratio >= self.policy.power_elevated_ratio:
            return "elevated", f"power ratio {ratio:.1%} >= elevated {self.policy.power_elevated_ratio:.1%}"
        return "nominal", f"power ratio {ratio:.1%} nominal"

    def _can_recover(self, current_band: str, *, stale: bool) -> bool:
        if stale or self.temperature is None:
            return False

        temperature_floor = {
            "elevated": self.policy.elevated_c,
            "critical": self.policy.critical_c,
            "emergency": self.policy.emergency_c,
        }[current_band]
        if self.temperature > temperature_floor - self.policy.recovery_margin_c:
            return False

        if self.battery is not None and self.battery < (
            self.policy.battery_reserve + self.policy.battery_recovery_margin
        ):
            return False

        if self.power_draw_watts is not None or self.power_budget_watts is not None:
            if self.power_draw_watts is None or self.power_budget_watts is None:
                return False
            ratio = self.power_draw_watts / self.power_budget_watts
            power_floor = {
                "elevated": self.policy.power_elevated_ratio,
                "critical": self.policy.power_critical_ratio,
                "emergency": self.policy.power_emergency_ratio,
            }[current_band]
            if ratio > power_floor - self.policy.power_recovery_margin:
                return False

        return True

    def update(
        self,
        *,
        temperature: float | None,
        battery: float | None = None,
        power_draw_watts: float | None = None,
        power_budget_watts: float | None = None,
        observed_at: float | None = None,
        now: float | None = None,
    ) -> str:
        """Apply one telemetry sample and return the resulting severity band.

        ``observed_at`` and ``now`` must be supplied together when freshness is
        checked. Readings older than ``max_sensor_age_seconds`` or too far in the
        future are treated as unusable evidence and fail closed.
        """

        if (observed_at is None) != (now is None):
            raise ValueError("observed_at and now must be supplied together")
        if observed_at is not None:
            if not _finite_number(observed_at) or not _finite_number(now):
                raise ValueError("observed_at and now must be finite numbers")
            observed = float(observed_at)
            current_time = float(now)
            age = current_time - observed
            if self.last_observed_at is not None and observed < self.last_observed_at:
                stale = True
                self.telemetry_status = "replayed"
            elif age > self.policy.max_sensor_age_seconds:
                stale = True
                self.telemetry_status = "stale"
            elif age < -self.policy.max_future_skew_seconds:
                stale = True
                self.telemetry_status = "future"
            else:
                stale = False
                self.telemetry_status = "fresh"
                self.last_observed_at = observed
        else:
            stale = False
            self.telemetry_status = "freshness-unchecked"

        self.temperature = self._normalize_temperature(temperature)
        if self.temperature is not None and not (
            self.policy.min_valid_temperature_c <= self.temperature <= self.policy.max_valid_temperature_c
        ):
            self.temperature = None
        self.battery = self._validate_battery(battery, self.node)
        self.power_draw_watts = self._normalize_power_draw(power_draw_watts)
        self.power_budget_watts = self._validate_power_budget(power_budget_watts, self.node)

        constraints: list[tuple[str, str]] = [self._temperature_band(stale=stale)]
        battery_constraint = self._battery_band()
        if battery_constraint is not None:
            constraints.append(battery_constraint)
        power_constraint = self._power_band(stale=stale)
        if power_constraint is not None:
            constraints.append(power_constraint)

        proposed = max((band for band, _ in constraints), key=BAND_RANK.__getitem__)
        proposed_rank = BAND_RANK[proposed]
        current_rank = BAND_RANK[self.band]
        held_by_hysteresis = False
        if proposed_rank > current_rank:
            self.band = proposed
        elif proposed_rank < current_rank:
            if self._can_recover(self.band, stale=stale):
                self.band = proposed
            else:
                held_by_hysteresis = True

        limiting_rank = max(BAND_RANK[band] for band, _ in constraints)
        decision_reasons = [reason for band, reason in constraints if BAND_RANK[band] == limiting_rank]
        if held_by_hysteresis:
            decision_reasons.append(f"recovery hysteresis holds {self.band} band")
        self.reasons = tuple(decision_reasons)
        return self.band

    def ceiling(self, full_capacity: int) -> dict[str, object]:
        """Return a stable ``PK_POWER_CEILING/1`` decision record."""
        if isinstance(full_capacity, bool) or not isinstance(full_capacity, int) or full_capacity < 0:
            raise ValueError(f"{self.node}: full capacity must be a non-negative integer")
        fraction = self.policy.band_ceiling[self.band]
        slots = int(full_capacity * fraction)
        reasons = self.reasons or (
            "no decision sample has been applied; conservative state may not reflect live telemetry",
        )
        return {
            "schema": "PK_POWER_CEILING/1",
            "node": self.node,
            "band": self.band,
            "ceiling": slots,
            "ceiling_fraction": fraction,
            "excluded": self.band == "emergency",
            "reason": "; ".join(reasons),
            "reasons": list(reasons),
            "telemetry_status": self.telemetry_status,
        }
