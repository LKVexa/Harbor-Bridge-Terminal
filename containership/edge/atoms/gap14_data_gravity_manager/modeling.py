"""Calibration/drift (P2-37), canary/shadow (P2-38) helpers.

* ``CalibrationTracker`` stores predicted vs observed cost per dimension, reports
  MAPE and signed bias, and runs a Page-Hinkley test on relative error; an alarm
  raises G14_DRIFT_DETECTED telemetry and marks the model revision *uncalibrated*.
* ``CanaryRouter`` deterministically buckets decisions by a keyed hash of the
  decision key so a canary cohort is stable and reproducible.
* Shadow evaluation is performed in ``service.DecisionService`` (the shadow model
  sees the *same* verified inputs, its result is recorded but never returned as
  the decision and never executable).
"""
from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PageHinkley:
    delta: float = 0.05       # tolerated mean shift
    threshold: float = 2.0    # alarm level
    n: int = 0
    mean: float = 0.0
    cum: float = 0.0
    min_cum: float = 0.0

    def update(self, x: float) -> bool:
        self.n += 1
        self.mean += (x - self.mean) / self.n
        self.cum += x - self.mean - self.delta
        self.min_cum = min(self.min_cum, self.cum)
        return self.cum - self.min_cum > self.threshold


@dataclass
class _Series:
    n: int = 0
    abs_pct: float = 0.0
    bias: float = 0.0
    ph: PageHinkley = field(default_factory=PageHinkley)
    alarmed: bool = False


class CalibrationTracker:
    def __init__(self, model_revision: str, *, min_observed: float = 1e-9, on_alarm=None):
        self.model_revision = model_revision
        self.min_observed = min_observed
        self._s: dict[str, _Series] = {}
        self._lock = threading.Lock()
        self.on_alarm = on_alarm

    def record(self, dimension: str, predicted: float, observed: float) -> bool:
        if observed < 0 or predicted < 0:
            raise ValueError("costs must be non-negative")
        rel = (predicted - observed) / max(observed, self.min_observed)
        with self._lock:
            s = self._s.setdefault(dimension, _Series())
            s.n += 1
            s.abs_pct += (abs(rel) - s.abs_pct) / s.n
            s.bias += (rel - s.bias) / s.n
            fired = s.ph.update(abs(rel))
            if fired and not s.alarmed:
                s.alarmed = True
                if self.on_alarm:
                    self.on_alarm(dimension)
            return fired

    def report(self) -> dict[str, Any]:
        with self._lock:
            return {"model_revision": self.model_revision,
                    "calibrated": not any(s.alarmed for s in self._s.values()),
                    "dimensions": {d: {"n": s.n, "mape": round(s.abs_pct, 6), "bias": round(s.bias, 6),
                                       "drift_alarm": s.alarmed} for d, s in self._s.items()}}


class CanaryRouter:
    def __init__(self, percent: float, salt: bytes):
        if not 0 <= percent <= 100:
            raise ValueError("percent in [0,100]")
        self.percent, self.salt = percent, salt

    def in_canary(self, key: str) -> bool:
        h = hashlib.sha256(self.salt + key.encode()).digest()
        return int.from_bytes(h[:8], "big") / 2**64 * 100 < self.percent
