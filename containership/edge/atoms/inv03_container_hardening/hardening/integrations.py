"""Typed hooks for adjacent systems, plus the staged rollout controller.

Checklist items served: 30 (node attestation hook), 31 (artifact provenance
binding), 36 (image-scan verdict hook), 37 (runtime intrusion-detection hook ->
quarantine), 63 (canary/staged rollout controller). INV-03 does not own the
scanners, attestors or IDS (contract ``not_owns``); it consumes their verdicts
and fails closed when a verdict is absent, stale or unsigned.
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from typing import Mapping

from .core import canonical


@dataclass(frozen=True)
class Verdict:
    source: str
    subject: str
    ok: bool
    at: int
    mac: str


class VerdictGate:
    """Accepts HMAC-sealed verdicts from named upstream sources only."""

    def __init__(self, source_keys: Mapping[str, bytes], max_age: int = 3600):
        self._keys, self._max_age = dict(source_keys), max_age

    @staticmethod
    def seal(key: bytes, source: str, subject: str, ok: bool, at: int) -> Verdict:
        mac = hmac.new(key, canonical([source, subject, ok, at]), hashlib.sha256).hexdigest()
        return Verdict(source, subject, ok, at, mac)

    def accept(self, v: object, subject: str, now: int) -> tuple[bool, str]:
        if not isinstance(v, Verdict):
            return False, "no verdict"
        key = self._keys.get(v.source)
        if key is None:
            return False, f"unknown verdict source {v.source!r}"
        exp = hmac.new(key, canonical([v.source, v.subject, v.ok, v.at]), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(exp, v.mac):
            return False, "verdict seal invalid"
        if v.subject != subject:
            return False, "verdict is for a different subject"
        if not (0 <= now - v.at <= self._max_age):
            return False, "verdict stale or from the future"
        return (True, "ok") if v.ok is True else (False, f"{v.source} verdict negative")


def check_image_provenance(pod: Mapping, verdicts: Mapping[str, Verdict], gate: VerdictGate, now: int) -> list[str]:
    """Items 31/36: every image must be digest-pinned and carry an accepted verdict."""
    issues = []
    for field_ in ("initContainers", "containers", "ephemeralContainers"):
        for c in pod.get(field_) or []:
            img = c.get("image") if isinstance(c, Mapping) else None
            if not isinstance(img, str) or "@sha256:" not in img or len(img.split("@sha256:")[1]) != 64:
                issues.append(f"image {img!r} is not pinned by sha256 digest")
                continue
            ok, why = gate.accept(verdicts.get(img), img, now)
            if not ok:
                issues.append(f"image {img}: {why}")
    return issues


def check_node_attestation(node: str, verdicts: Mapping[str, Verdict], gate: VerdictGate, now: int) -> tuple[bool, str]:
    """Item 30: a node without an accepted attestation verdict gets no workloads."""
    return gate.accept(verdicts.get(node), node, now)


def ids_finding_to_action(engine, finding: Mapping, gate: VerdictGate, now: int) -> dict:
    """Item 37: an accepted IDS finding produces a quarantine plan and an audit event."""
    v = finding.get("verdict")
    wl = finding.get("workload")
    if not isinstance(wl, str):
        return {"accepted": False, "why": "finding names no workload"}
    ok, why = gate.accept(v, wl, now)
    # An IDS verdict of ok=False means "intrusion detected"; a valid seal is required either way.
    if isinstance(v, Verdict) and (why == "ok" or why.endswith("verdict negative")):
        plan = engine.quarantine_plan(wl, f"IDS finding from {v.source}") if not ok else None
        engine.ledger.append("ids.finding", wl, v.source, now, {"intrusion": not ok, "plan": bool(plan)})
        return {"accepted": True, "intrusion": not ok, "plan": plan}
    return {"accepted": False, "why": why}


@dataclass
class Rollout:
    """Item 63: staged rollout of a new baseline across node cohorts.

    Stages advance only when the health gate passes for the current stage; any
    failed gate or a freeze rolls every cohort back to the prior baseline.
    """
    stages: tuple = (1, 5, 25, 50, 100)
    max_denial_rate_increase: float = 0.02
    stage: int = 0
    frozen: bool = False
    rolled_back: bool = False
    history: list = field(default_factory=list)

    def percent(self) -> int:
        return 0 if self.rolled_back else self.stages[self.stage]

    def cohort_enabled(self, node_id: str) -> bool:
        bucket = int(hashlib.sha256(node_id.encode()).hexdigest()[:8], 16) % 100
        return bucket < self.percent()

    def gate(self, baseline_denial_rate: float, canary_denial_rate: float, errors: int) -> str:
        if self.frozen or self.rolled_back:
            return "HELD"
        healthy = errors == 0 and canary_denial_rate - baseline_denial_rate <= self.max_denial_rate_increase
        self.history.append({"stage": self.percent(), "healthy": healthy,
                             "delta": round(canary_denial_rate - baseline_denial_rate, 6), "errors": errors})
        if not healthy:
            self.rolled_back = True
            return "ROLLED_BACK"
        if self.stage < len(self.stages) - 1:
            self.stage += 1
            return "ADVANCED"
        return "COMPLETE"

    def freeze(self) -> None:
        self.frozen = True
