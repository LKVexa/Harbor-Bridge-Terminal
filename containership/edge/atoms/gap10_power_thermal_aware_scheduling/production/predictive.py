"""Components 11, 12, 13, 14 - thermal rate-of-rise predictor, battery runtime
estimator, cooling-domain correlation, and GAP-11 accelerator integration.

All of them can only *raise* severity (lower the ceiling); none can relax the
reactive kernel's band.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from ..model import BAND_RANK, BANDS, PowerThermalPolicy


def worse(a: str, b: str) -> str:
    return a if BAND_RANK[a] >= BAND_RANK[b] else b


# ------------------------------------------------------------- 11 rate of rise
@dataclass
class RateOfRisePredictor:
    """Least-squares slope over a sliding window; predicts the temperature at
    ``horizon_s`` and derates pre-emptively if that crosses a threshold."""
    window: int = 8
    horizon_s: float = 60.0
    min_points: int = 3
    max_slope_c_per_s: float = 5.0   # physically implausible slopes are ignored as noise
    _hist: dict[str, deque] = field(default_factory=dict)

    def observe(self, node: str, t: float, temp: float) -> None:
        h = self._hist.setdefault(node, deque(maxlen=self.window))
        if h and t <= h[-1][0]:
            return
        h.append((t, temp))

    def slope(self, node: str) -> float | None:
        h = self._hist.get(node)
        if not h or len(h) < self.min_points:
            return None
        n = len(h)
        mt = sum(p[0] for p in h) / n
        my = sum(p[1] for p in h) / n
        den = sum((p[0] - mt) ** 2 for p in h)
        if den == 0:
            return None
        s = sum((p[0] - mt) * (p[1] - my) for p in h) / den
        return s if abs(s) <= self.max_slope_c_per_s else None

    def predict(self, node: str) -> float | None:
        s = self.slope(node)
        if s is None:
            return None
        return self._hist[node][-1][1] + max(s, 0.0) * self.horizon_s

    def band(self, node: str, policy: PowerThermalPolicy) -> tuple[str, str | None]:
        p = self.predict(node)
        if p is None:
            return "nominal", None
        # Predictive derating tops out at 'critical': exclusion stays reserved for observed emergency.
        if p >= policy.emergency_c:
            return "critical", f"predicted {p:.1f}C in {self.horizon_s:.0f}s >= emergency {policy.emergency_c:.1f}C"
        if p >= policy.critical_c:
            return "elevated", f"predicted {p:.1f}C in {self.horizon_s:.0f}s >= critical {policy.critical_c:.1f}C"
        return "nominal", None


# ------------------------------------------------------------- 12 battery runtime
@dataclass(frozen=True)
class BatteryModel:
    capacity_wh: float
    health: float = 1.0                  # state-of-health fraction
    reserve_fraction: float = 0.15
    required_runtime_s: float = 1800.0   # runtime above reserve required to stay nominal
    # piecewise discharge curve: usable-energy multiplier vs. state of charge
    curve: tuple[tuple[float, float], ...] = ((0.0, 0.0), (0.1, 0.07), (0.5, 0.48), (1.0, 1.0))

    def usable_fraction(self, soc: float) -> float:
        pts = self.curve
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if x0 <= soc <= x1:
                return y0 + (y1 - y0) * (soc - x0) / (x1 - x0)
        return 1.0 if soc > 1 else 0.0

    def runtime_s(self, soc: float, load_w: float) -> float | None:
        if load_w is None or load_w <= 0 or self.capacity_wh <= 0:
            return None
        energy = self.capacity_wh * self.health * (self.usable_fraction(soc) - self.usable_fraction(self.reserve_fraction))
        return max(energy, 0.0) * 3600.0 / load_w

    def band(self, soc: float | None, load_w: float | None, on_mains: bool) -> tuple[str, str | None]:
        if on_mains or soc is None:
            return "nominal", None
        rt = self.runtime_s(soc, load_w)
        if rt is None:
            return "critical", "battery runtime unknown (no load evidence)"
        if rt <= 0:
            return "critical", "battery at or below reserve energy"
        if rt < self.required_runtime_s / 2:
            return "critical", f"battery runtime {rt:.0f}s < {self.required_runtime_s / 2:.0f}s"
        if rt < self.required_runtime_s:
            return "elevated", f"battery runtime {rt:.0f}s < {self.required_runtime_s:.0f}s"
        return "nominal", None


# ------------------------------------------------------------- 13 cooling domains
@dataclass
class CoolingDomainModel:
    """Nodes sharing a rack/cabinet/room share fate. If a quorum fraction of a
    domain is hot (or the domain's own inlet is hot), every member is raised to
    at least the domain band - a locally cool reading cannot hide a failing
    shared domain."""
    membership: dict[str, str] = field(default_factory=dict)   # node -> domain
    parent: dict[str, str] = field(default_factory=dict)       # rack -> room, etc.
    quorum: float = 0.5
    inlet_limits_c: dict[str, float] = field(default_factory=dict)
    _bands: dict[str, str] = field(default_factory=dict)
    _inlet: dict[str, float] = field(default_factory=dict)

    def report(self, node: str, band: str) -> None:
        self._bands[node] = band

    def report_inlet(self, domain: str, temp_c: float) -> None:
        self._inlet[domain] = temp_c

    def _domains_of(self, node):
        d = self.membership.get(node)
        while d is not None:
            yield d
            d = self.parent.get(d)

    def members(self, domain: str) -> list[str]:
        return [n for n in self.membership if domain in self._domains_of(n)]

    def domain_band(self, domain: str) -> tuple[str, str | None]:
        members = self.members(domain)
        band, reason = "nominal", None
        limit = self.inlet_limits_c.get(domain)
        if limit is not None and self._inlet.get(domain, -1e9) >= limit:
            band, reason = "critical", f"cooling domain {domain} inlet {self._inlet[domain]:.1f}C >= {limit:.1f}C"
        if members:
            hot = [n for n in members if BAND_RANK[self._bands.get(n, "critical")] >= BAND_RANK["critical"]]
            if len(hot) / len(members) >= self.quorum and len(members) > 1:
                b = "elevated" if band == "nominal" else band
                band = worse(band, b)
                reason = reason or f"cooling domain {domain}: {len(hot)}/{len(members)} members critical+"
        return band, reason

    def band_for(self, node: str) -> tuple[str, str | None]:
        band, reason = "nominal", None
        for d in self._domains_of(node):
            b, r = self.domain_band(d)
            if BAND_RANK[b] > BAND_RANK[band]:
                band, reason = b, r
        return band, reason


# ------------------------------------------------------------- 14 accelerators (GAP-11)
@dataclass(frozen=True)
class AcceleratorReport:
    """``PK_ACCEL_THERMAL/1`` record published by GAP-11 per device."""
    device_id: str
    kind: str                # gpu | npu | fpga
    hotspot_c: float | None
    hotspot_limit_c: float
    power_w: float | None
    trusted: bool = True


def accelerator_band(reports, policy: PowerThermalPolicy) -> tuple[str, float, str | None]:
    """Return (band, accelerator_power_w, reason). Hotspot is judged against the
    device's own limit mapped onto the node band scale; missing/untrusted device
    telemetry fails closed to critical."""
    band, reason, power = "nominal", None, 0.0
    for r in reports:
        if not r.trusted or r.hotspot_c is None or r.power_w is None:
            b, why = "critical", f"accelerator {r.device_id} telemetry unusable"
        else:
            power += r.power_w
            headroom = r.hotspot_limit_c - r.hotspot_c
            if headroom <= 0:
                b, why = "emergency", f"accelerator {r.device_id} hotspot {r.hotspot_c:.1f}C >= limit {r.hotspot_limit_c:.1f}C"
            elif headroom <= policy.emergency_c - policy.critical_c:
                b, why = "critical", f"accelerator {r.device_id} hotspot within {headroom:.1f}C of limit"
            elif headroom <= policy.emergency_c - policy.elevated_c:
                b, why = "elevated", f"accelerator {r.device_id} hotspot within {headroom:.1f}C of limit"
            else:
                b, why = "nominal", None
        if BAND_RANK[b] > BAND_RANK[band]:
            band, reason = b, why
    return band, power, reason


__all__ = ["RateOfRisePredictor", "BatteryModel", "CoolingDomainModel", "AcceleratorReport",
           "accelerator_band", "worse", "BANDS"]
