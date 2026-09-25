"""Capacity/saturation model (items 6, 40).

A closed-form planning model the release gate compares benchmark results
against: controller throughput ~ workers / (api_rtt*writes + downstream_rtt +
cpu_per_reconcile). Saturation is declared when offered load exceeds 80 % of
modelled throughput or queue depth grows over an observation window."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Model:
    workers: int = 1
    api_rtt_s: float = 0.010
    api_writes_per_reconcile: float = 2.0
    downstream_rtt_s: float = 0.020
    cpu_s_per_reconcile: float = 0.0005

    def throughput(self) -> float:
        per = self.api_rtt_s * self.api_writes_per_reconcile + self.downstream_rtt_s + self.cpu_s_per_reconcile
        return self.workers / per

    def saturated(self, offered_per_s: float) -> bool:
        return offered_per_s > 0.8 * self.throughput()


def regression(baseline: dict, current: dict, tolerance: float = 0.20) -> list[str]:
    """Fail when any p99 grows, or throughput drops, by more than ``tolerance``."""
    bad = []
    for k, v in baseline.items():
        c = current.get(k)
        if c is None:
            bad.append(f"{k}: missing in current run")
        elif k.endswith("_p99_ms") and c > v * (1 + tolerance):
            bad.append(f"{k}: {c:.3f} > {v:.3f} * {1 + tolerance}")
        elif k.endswith("_per_s") and c < v * (1 - tolerance):
            bad.append(f"{k}: {c:.1f} < {v:.1f} * {1 - tolerance}")
    return bad
