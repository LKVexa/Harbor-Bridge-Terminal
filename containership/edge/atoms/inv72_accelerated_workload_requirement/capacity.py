"""Capacity model and saturation signals (C017, C069).

Two different capacities matter and are reported separately:

* **decision capacity** - how many match decisions per second this instance can make.  Modelled as
  ``throughput = 1 / (base_us + per_device_us * inventory)`` from the measured perf baseline
  (evidence/PERF_RESULTS.json); saturation = offered rate / modelled capacity.
* **fleet capacity** - how much of the accelerator fleet is reserved, per class and per tenant quota.
  Saturation per class = reserved devices / devices of that class.

Thresholds: ``warn`` at 0.7, ``critical`` at 0.9 of either.  Alert rules in ops/alerts.json use them.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable

from .matcher import Device

WARN, CRITICAL = 0.7, 0.9


def decision_capacity(base_us: float, per_device_us: float, inventory: int) -> float:
    cost = base_us + per_device_us * max(0, inventory)
    return 1e6 / cost if cost > 0 else float("inf")


def fleet_saturation(devices: Iterable[Device], reserved_ids: set) -> dict:
    total, used = Counter(), Counter()
    for d in devices:
        total[d.cls] += 1
        if d.dev_id in reserved_ids:
            used[d.cls] += 1
    return {cls: {"devices": n, "reserved": used[cls], "ratio": used[cls] / n if n else 0.0,
                  "level": level(used[cls] / n if n else 0.0)} for cls, n in sorted(total.items())}


def level(ratio: float) -> str:
    return "critical" if ratio >= CRITICAL else "warn" if ratio >= WARN else "ok"


def model(offered_per_s: float, base_us: float, per_device_us: float, inventory: int,
          devices: Iterable[Device] = (), reserved_ids: set = frozenset()) -> dict:
    cap = decision_capacity(base_us, per_device_us, inventory)
    ratio = offered_per_s / cap if cap else float("inf")
    return {"schema": "PK_ACCEL_CAPACITY/1", "decision_capacity_per_s": round(cap, 1),
            "offered_per_s": offered_per_s, "decision_saturation": round(ratio, 4), "decision_level": level(ratio),
            "fleet": fleet_saturation(devices, set(reserved_ids)), "thresholds": {"warn": WARN, "critical": CRITICAL}}
