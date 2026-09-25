"""Constraint precedence resolver (C019).

Precedence is data (``PRECEDENCE_POLICY``, versioned), not control flow.  The
resolver evaluates every constraint, returns a structured decision trace that
names the winning constraint and every rejected alternative, and embeds the
policy version.  Hard constraints can never be waived; waivable ones need a
``Waiver`` whose scope matches and whose expiry is in the future.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping
import time

from .errors import AgentError

PRECEDENCE_POLICY: Mapping[str, Any] = {
    "schema": "PK_AGENT_PRECEDENCE/1",
    "version": "PK_AGENT_PRECEDENCE/1.0.0",
    # Highest precedence first.
    "order": ["security", "legal_residency", "safety", "data_integrity", "availability_slo", "performance", "cost"],
    "hard": ["security", "legal_residency", "safety", "data_integrity"],
    "waivable": ["availability_slo", "performance", "cost"],
    "max_waiver_s": 30 * 86400,
    "collisions": {
        "slo_vs_approval_latency": "approval wins (safety > availability_slo); run waits or fails with AGT-APR-001",
        "cost_vs_secure_sandbox": "heavy tier wins (security > cost); cost budget exhaustion refuses rather than downgrades",
        "failover_vs_residency": "residency wins (legal_residency > availability_slo); no failover outside allowed zones",
        "retry_vs_budget": "budget wins (safety); retries never exceed step/cost budget or deadline",
        "degraded_mode_vs_audit": "audit wins (data_integrity); no audit => no execution",
    },
}


@dataclass(frozen=True)
class Waiver:
    waiver_id: str
    constraint_class: str
    scope: str            # e.g. "tenant:acme" or "*"
    owner: str
    justification: str
    expires_at: float
    audit_ref: str


@dataclass(frozen=True)
class Constraint:
    name: str
    klass: str                         # one of PRECEDENCE_POLICY["order"]
    admits: Callable[[Mapping[str, Any]], bool]   # does this candidate action satisfy it?
    description: str = ""


@dataclass
class Decision:
    chosen: Mapping[str, Any] | None
    winning_constraint: str | None
    trace: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)
    policy_version: str = PRECEDENCE_POLICY["version"]
    waivers_used: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": "PK_AGENT_DECISION/1", "policy_version": self.policy_version, "chosen": self.chosen,
                "winning_constraint": self.winning_constraint, "trace": self.trace, "rejected": self.rejected,
                "waivers_used": self.waivers_used}


def _waiver_ok(w: Waiver, klass: str, scope: str, now: float) -> bool:
    return (w.constraint_class == klass and klass in PRECEDENCE_POLICY["waivable"]
            and (w.scope == "*" or w.scope == scope) and now < w.expires_at
            and w.expires_at - now <= PRECEDENCE_POLICY["max_waiver_s"] and bool(w.owner) and bool(w.justification))


def resolve(candidates: list[Mapping[str, Any]], constraints: list[Constraint], *, scope: str = "*",
            waivers: list[Waiver] = (), clock=time.time) -> Decision:
    """Pick the first candidate (caller's preference order) satisfying every hard constraint and
    every unwaived waivable constraint.  Deterministic: same inputs -> same trace."""
    order = PRECEDENCE_POLICY["order"]
    for c in constraints:
        if c.klass not in order:
            raise AgentError("AGT-POL-001", "unknown constraint class", details={"class": c.klass})
    ranked = sorted(constraints, key=lambda c: (order.index(c.klass), c.name))
    now = clock()
    d = Decision(None, None)
    for cand in candidates:
        failed = None
        used: list[str] = []
        for c in ranked:
            ok = bool(c.admits(cand))
            waived = None
            if not ok:
                w = next((w for w in waivers if _waiver_ok(w, c.klass, scope, now)), None)
                if w is not None:
                    waived, ok = w.waiver_id, True
                    used.append(w.waiver_id)
            d.trace.append({"candidate": dict(cand), "constraint": c.name, "class": c.klass,
                            "hard": c.klass in PRECEDENCE_POLICY["hard"], "satisfied": ok, "waiver": waived})
            if not ok:
                failed = c
                break
        if failed is None:
            d.chosen, d.waivers_used = dict(cand), used
            return d
        d.rejected.append({"candidate": dict(cand), "blocked_by": failed.name, "class": failed.klass})
        if d.winning_constraint is None:
            d.winning_constraint = failed.name
    raise AgentError("AGT-POL-001", "no candidate satisfies the constraint set",
                     details={"decision": d.to_dict()})
