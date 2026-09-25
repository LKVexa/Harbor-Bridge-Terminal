"""Component 62 - incident severity taxonomy, escalation, safe mode, recovery and
post-incident records (PK_DYN_INCIDENT/1).  Procedure: docs/62_incident_response.md.

Paging is modelled, not performed: no pager integration or on-call humans exist,
so ``escalation`` returns the roles to page and flags them UNASSIGNED via
ownership.json (component 08).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from ..model import Pool
from . import ownership

# Ordered most severe first. Each rule: (severity, signal predicate description, predicate)
SEVERITIES = {
    "SEV1": {"ack_min": 5, "update_min": 30, "page": ["oncall_primary", "incident_commander", "service_owner"],
             "examples": ["busy node reclaimed (safe-reclaim SLO has no budget)",
                          "pool exceeded max_nodes (bounded SLO has no budget)",
                          "audit chain verification failed"]},
    "SEV2": {"ack_min": 15, "update_min": 60, "page": ["oncall_primary", "incident_commander"],
             "examples": ["scale decisions failing for > 1 tick", "lease store unavailable (safe mode engaged)"]},
    "SEV3": {"ack_min": 60, "update_min": 240, "page": ["oncall_primary"],
             "examples": ["leaked nodes accruing cost", "responsiveness SLO budget > 50% consumed"]},
    "SEV4": {"ack_min": 1440, "update_min": 0, "page": [], "examples": ["single transient provider retry"]},
}


def classify(signals: dict) -> str:
    if signals.get("busy_reclaimed", 0) > 0 or signals.get("size_over_max", 0) > 0 or \
            signals.get("audit_chain_broken"):
        return "SEV1"
    if signals.get("failed_ticks", 0) > 1 or signals.get("lease_store_down"):
        return "SEV2"
    if signals.get("leaked_nodes", 0) > 0 or signals.get("slo_budget_used", 0) > 0.5:
        return "SEV3"
    return "SEV4"


def escalation(sev: str, elapsed_min: float, owners: dict | None = None) -> dict:
    spec = SEVERITIES[sev]
    owners = ownership.load() if owners is None else owners
    chain = owners.get("escalation_chain", [])
    level = 0
    if spec["ack_min"]:
        level = min(len(chain) - 1, int(elapsed_min // spec["ack_min"])) if chain else 0
    roles = list(dict.fromkeys(spec["page"] + chain[:level + 1] if spec["page"] else []))
    unassigned = []
    for r in roles:
        try:
            if ownership.query(owners, r).get("primary", "UNASSIGNED").startswith("UNASSIGNED"):
                unassigned.append(r)
        except KeyError:
            unassigned.append(r)
    return {"severity": sev, "page": roles, "level": level, "unassigned": unassigned,
            "blocked": bool(unassigned)}


class SafeModePool:
    """Containment wrapper: when frozen, a tick that would reclaim any node is rolled
    back (scale-in freeze); scale-out still honours max_nodes."""

    def __init__(self, pool: Pool) -> None:
        self.pool = pool
        self.frozen = False
        self.suppressed: list = []

    def tick(self, now, demand, **kw):
        if not self.frozen:
            return self.pool.tick(now, demand, **kw)
        before = copy.deepcopy(self.pool)
        res = self.pool.tick(now, demand, **kw)
        if res["reclaimed"]:
            self.suppressed.append((now, list(res["reclaimed"])))
            # keep the time watermark and accounting, restore membership + renew all
            nodes = before.nodes
            for s in nodes.values():
                s["expires"] = max(s["expires"], now + self.pool.lease_ttl)
            kept = dict(nodes)
            for nid, st in self.pool.nodes.items():   # nodes added this tick
                if nid not in kept and len(kept) < self.pool.max_nodes:
                    kept[nid] = st
            self.pool.nodes = kept
            res = dict(res, reclaimed=[], size=len(kept), safe_mode="scale-in suppressed")
        return res


def recovery_validation(pool: Pool, *, expected_busy: set[str]) -> list[str]:
    p = []
    if len(pool.nodes) > pool.max_nodes:
        p.append("size above max")
    if len(pool.nodes) < pool.min_nodes:
        p.append("size below min")
    missing = expected_busy - set(pool.nodes)
    if missing:
        p.append(f"busy nodes missing: {sorted(missing)}")
    try:
        probe = copy.deepcopy(pool)
        probe.tick(probe._last_now if probe._last_now is not None else 0, 0, elapsed_hours=0)
    except ValueError as exc:
        p.append(f"state invalid: {exc}")
    return p


@dataclass
class PostIncident:
    incident_id: str
    severity: str
    timeline: list = field(default_factory=list)      # [(ts, actor, action)]
    actions: list = field(default_factory=list)       # corrective actions

    def add_event(self, ts: float, actor: str, action: str) -> None:
        if self.timeline and ts < self.timeline[-1][0]:
            raise ValueError("timeline must be non-decreasing")
        self.timeline.append((ts, actor, action))

    def add_action(self, title: str, due_ts: float, owner: str = "UNASSIGNED") -> None:
        self.actions.append({"title": title, "owner": owner, "due": due_ts, "status": "OPEN"})

    def record(self, audit=None) -> dict:
        rec = {"schema": "PK_DYN_INCIDENT/1", "id": self.incident_id, "severity": self.severity,
               "timeline": [list(e) for e in self.timeline], "actions": self.actions,
               "blockers": [a["title"] for a in self.actions if a["owner"] == "UNASSIGNED"],
               "complete": bool(self.timeline) and bool(self.actions)}
        if audit is not None:
            audit.append("incident-tooling", "postmortem.record", self.incident_id, "SUCCESS",
                         {"severity": self.severity, "actions": len(self.actions)})
        return rec
