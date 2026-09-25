"""Checklist 45: canary / staged rollout with automatic rollback.

A rollout moves a candidate configuration (or policy digest) through
cohorts - by default 1% -> 10% -> 50% -> 100% of nodes.  After each stage a
caller-supplied ``probe(stage_nodes)`` returns observed signals; the stage
passes only when every guard holds:

* ``software_defect`` count == 0 (any defect aborts),
* ``attack_suspected`` did not rise above the baseline,
* the policy-refusal rate did not rise by more than ``max_refusal_delta``
  (a new policy that suddenly refuses 30% of placements is a rollout bug,
  not a security win, until a human says otherwise),
* health is not ``stalled``.

A failing stage triggers :meth:`ConfigStore.rollback` for every stage
already applied, writes ``rollout_aborted`` to the audit chain and returns a
machine-readable report.  Nothing here claims the rollout was approved: the
``approved_by`` field must be supplied and is recorded, not checked against
an identity provider (that is the platform's job - see STATUS item 45).
"""
from __future__ import annotations

import math

from .auditlog import AuditLog
from .config import ConfigStore

DEFAULT_STAGES = (0.01, 0.10, 0.50, 1.00)


def cohorts(nodes: list[str], stages=DEFAULT_STAGES) -> list[list[str]]:
    ordered = sorted(nodes)
    out, done = [], 0
    for frac in stages:
        upto = max(1, math.ceil(len(ordered) * frac)) if ordered else 0
        out.append(ordered[done:upto])
        done = upto
    return out


def run(store: ConfigStore, audit: AuditLog, nodes: list[str], *, environment: dict, probe,
        baseline: dict, approved_by: str, max_refusal_delta: float = 0.05, stages=DEFAULT_STAGES) -> dict:
    if not approved_by:
        raise ValueError("a rollout needs a named approver")
    report = {"schema": "INV43_ROLLOUT/1", "approved_by": approved_by, "stages": [], "result": None}
    applied = 0
    audit.append("rollout_started", approved_by=approved_by, nodes=len(nodes))
    for i, cohort in enumerate(cohorts(nodes, stages)):
        prov = store.activate(environment=environment, source=f"rollout-stage-{i}", author=approved_by)
        applied += 1
        sig = probe(cohort)
        breaches = []
        if sig.get("software_defect", 0) > 0:
            breaches.append("software_defect")
        if sig.get("attack_suspected", 0) > baseline.get("attack_suspected", 0):
            breaches.append("attack_suspected_rise")
        if sig.get("refusal_rate", 0.0) - baseline.get("refusal_rate", 0.0) > max_refusal_delta:
            breaches.append("refusal_rate_jump")
        if sig.get("health") == "stalled":
            breaches.append("stalled")
        report["stages"].append({"stage": i, "cohort_size": len(cohort), "config_digest": prov["digest"],
                                 "signals": sig, "breaches": breaches})
        if breaches:
            for _ in range(applied):
                store.rollback(author=f"auto-rollback:{approved_by}")
            audit.append("rollout_aborted", stage=i, breaches=breaches)
            report["result"] = "rolled_back"
            report["restored_digest"] = store.provenance["digest"]
            return report
    audit.append("rollout_completed", stages=len(report["stages"]))
    report["result"] = "completed"
    return report
