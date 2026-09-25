"""Component 09 - hardware/site calibration inventory.

Each hardware class carries validated device limits. A node's effective
``PowerThermalPolicy`` is derived from its hardware profile and can only be
*tighter* than the profile's vendor limits. Unknown hardware falls back to the
conservative ``UNKNOWN_PROFILE`` - never to permissive defaults.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..model import PolicyError, PowerThermalPolicy

BATTERY_CHEMISTRIES = {"li-ion": 0.15, "lifepo4": 0.10, "lead-acid": 0.50, "none": 0.0}


@dataclass(frozen=True)
class HardwareProfile:
    hardware_class: str
    vendor_throttle_c: float          # temperature at which firmware throttles
    vendor_shutdown_c: float          # hard thermal shutdown
    sustained_power_w: float          # TDP / sustained budget
    peak_power_w: float
    battery_chemistry: str = "none"
    battery_capacity_wh: float = 0.0
    cooling: str = "passive"          # passive | fan | liquid | room
    thermal_time_constant_s: float = 120.0
    sensor_kinds: tuple[str, ...] = ("cpu",)
    calibration_revision: str = "r1"
    validated_by: str = ""

    def __post_init__(self):
        if not self.vendor_throttle_c < self.vendor_shutdown_c:
            raise PolicyError(f"{self.hardware_class}: throttle must be below shutdown")
        if not 0 < self.sustained_power_w <= self.peak_power_w:
            raise PolicyError(f"{self.hardware_class}: sustained power must be within (0, peak]")
        if self.battery_chemistry not in BATTERY_CHEMISTRIES:
            raise PolicyError(f"{self.hardware_class}: unknown battery chemistry")
        if self.thermal_time_constant_s <= 0:
            raise PolicyError("thermal_time_constant_s must be > 0")

    def derive_policy(self, base: PowerThermalPolicy = PowerThermalPolicy(), guard_c: float = 5.0) -> PowerThermalPolicy:
        """Emergency sits ``guard_c`` below vendor throttle so GAP-10 always acts first."""
        emergency = min(base.emergency_c, self.vendor_throttle_c - guard_c)
        critical = min(base.critical_c, emergency - 2 * base.recovery_margin_c)
        elevated = min(base.elevated_c, critical - 2 * base.recovery_margin_c)
        reserve = max(base.battery_reserve, BATTERY_CHEMISTRIES[self.battery_chemistry])
        return PowerThermalPolicy(
            min_valid_temperature_c=base.min_valid_temperature_c,
            elevated_c=elevated, critical_c=critical, emergency_c=emergency,
            max_valid_temperature_c=max(base.max_valid_temperature_c, self.vendor_shutdown_c + 1),
            recovery_margin_c=base.recovery_margin_c,
            battery_reserve=min(reserve, 0.95),
            battery_recovery_margin=min(base.battery_recovery_margin, 1 - min(reserve, 0.95)),
            power_elevated_ratio=base.power_elevated_ratio, power_critical_ratio=base.power_critical_ratio,
            power_emergency_ratio=base.power_emergency_ratio, power_recovery_margin=base.power_recovery_margin,
            max_sensor_age_seconds=base.max_sensor_age_seconds, max_future_skew_seconds=base.max_future_skew_seconds,
            nominal_ceiling=base.nominal_ceiling, elevated_ceiling=base.elevated_ceiling,
            critical_ceiling=base.critical_ceiling, emergency_ceiling=0.0,
        )


UNKNOWN_PROFILE = HardwareProfile("unknown", 70.0, 90.0, 50.0, 60.0, "li-ion", 0.0, "passive", 60.0,
                                  ("cpu",), "conservative-default", "gap10-builtin")


@dataclass
class CalibrationInventory:
    profiles: dict[str, HardwareProfile] = field(default_factory=dict)
    node_class: dict[str, str] = field(default_factory=dict)

    def register(self, profile: HardwareProfile) -> None:
        if not profile.validated_by:
            raise PolicyError(f"{profile.hardware_class}: calibration must name a validator")
        self.profiles[profile.hardware_class] = profile

    def assign(self, node: str, hardware_class: str) -> None:
        if hardware_class not in self.profiles:
            raise PolicyError(f"unknown hardware class {hardware_class}")
        self.node_class[node] = hardware_class

    def profile_for(self, node: str) -> tuple[HardwareProfile, bool]:
        """Return (profile, calibrated). Uncalibrated nodes get the conservative profile."""
        cls = self.node_class.get(node)
        if cls is None:
            return UNKNOWN_PROFILE, False
        return self.profiles[cls], True

    def budget_for(self, node: str) -> float:
        return self.profile_for(node)[0].sustained_power_w

    def to_dict(self) -> dict:
        return {"profiles": {k: vars(v) | {"sensor_kinds": list(v.sensor_kinds)} for k, v in self.profiles.items()},
                "node_class": dict(self.node_class)}
