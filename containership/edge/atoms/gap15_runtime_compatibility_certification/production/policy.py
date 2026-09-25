"""Policy-precedence engine (component 23) and waiver registry (component 49).

Domains are ranked (MC-23-02): ``revocation`` > ``integrity`` > ``lifecycle`` >
``security`` > ``residency`` > ``compatibility`` > ``slo`` > ``cost`` >
``convenience``. A higher-ranked deny can never be overridden by a lower
domain's allow. Waivers can only override *waivable* controls; revocation and
integrity are non-waivable (MC-23-03, MC-49-03). Evaluation is deterministic
and returns a full trace (MC-23-04). Bundles are validated for contradictory
equal-priority rules, unknown attributes and over-broad wildcards
(MC-23-05) and can be simulated against a decision set before activation
(MC-23-07).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .canonical import digest

DOMAIN_RANK = {"revocation": 100, "integrity": 90, "lifecycle": 80, "security": 70, "residency": 60,
               "compatibility": 50, "slo": 40, "cost": 30, "convenience": 20}
NON_WAIVABLE = {"revocation", "integrity"}
KNOWN_ATTRS = {"verdict", "runtime", "partition", "artifact_digest", "profile_id", "lifecycle", "trust_class",
               "emergency", "site", "environment", "feature_scope"}


class PolicyError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


@dataclass(frozen=True)
class PolicyRule:
    rule_id: str
    domain: str
    effect: str  # allow | deny | require
    match: tuple  # ((attr, value), ...) ; value "*" matches anything
    priority: int = 0
    effective_from: int = 0
    effective_until: Optional[int] = None
    control_id: Optional[str] = None  # the control a waiver would reference

    def matches(self, ctx: dict, now: int) -> bool:
        if now < self.effective_from or (self.effective_until is not None and now >= self.effective_until):
            return False
        return all(v == "*" or ctx.get(a) == v for a, v in self.match)


@dataclass
class PolicySet:
    revision: str
    rules: list = field(default_factory=list)
    signature: Optional[dict] = None

    def validate(self) -> list:
        problems = []
        seen = {}
        for r in self.rules:
            if r.domain not in DOMAIN_RANK:
                problems.append(f"{r.rule_id}: unknown domain {r.domain}")
            if r.effect not in ("allow", "deny", "require"):
                problems.append(f"{r.rule_id}: bad effect")
            for a, v in r.match:
                if a not in KNOWN_ATTRS:
                    problems.append(f"{r.rule_id}: unknown attribute {a}")
            if r.effect == "allow" and all(v == "*" for _, v in r.match) and DOMAIN_RANK.get(r.domain, 0) >= DOMAIN_RANK["lifecycle"]:
                problems.append(f"{r.rule_id}: unconditional allow in a high-precedence domain")
            key = (r.domain, r.priority, tuple(sorted(r.match)))
            if key in seen and seen[key].effect != r.effect:
                problems.append(f"{r.rule_id}: contradicts {seen[key].rule_id} at equal domain/priority/scope")
            seen[key] = r
        return problems

    def digest(self) -> str:
        return digest({"revision": self.revision, "rules": [
            [r.rule_id, r.domain, r.effect, [list(m) for m in r.match], r.priority, r.effective_from,
             r.effective_until, r.control_id] for r in self.rules]})


@dataclass(frozen=True)
class Waiver:
    waiver_id: str
    revision: int
    wtype: str  # lifecycle-reactivation | unsupported-combination | security-control | policy-bypass | operational
    control_id: str
    scope: tuple  # ((attr, value), ...) — exact, no wildcards
    justification: str
    risk: str  # low | medium | high
    compensating_controls: tuple
    owner: str
    approvers: tuple
    created_at: int
    effective_at: int
    expires_at: int
    status: str = "approved"  # approved | revoked | rejected | superseded

    def applies(self, ctx: dict, now: int) -> bool:
        return (self.status == "approved" and self.effective_at <= now < self.expires_at
                and all(ctx.get(a) == v for a, v in self.scope))


class WaiverRegistry:
    """Append-only waiver history; the effective record is the latest revision per id."""

    MAX_DURATION = {"low": 90 * 86400, "medium": 30 * 86400, "high": 7 * 86400}

    def __init__(self) -> None:
        self.history: list = []

    def submit(self, w: Waiver, *, non_waivable_controls: set) -> Waiver:
        if w.control_id in non_waivable_controls:
            raise PolicyError("E_WAIVER_NON_WAIVABLE", w.control_id)
        if not w.scope or any(v in ("*", "", None) for _, v in w.scope):
            raise PolicyError("E_WAIVER_SCOPE", "waivers need an exact, non-wildcard scope")
        if w.expires_at <= w.effective_at or w.expires_at - w.effective_at > self.MAX_DURATION[w.risk]:
            raise PolicyError("E_WAIVER_DURATION", f"{w.risk} waivers last at most {self.MAX_DURATION[w.risk]}s")
        needed = 2 if w.risk == "high" or ("partition", "*") in w.scope else 1
        approvers = set(w.approvers) - {w.owner}
        if len(approvers) < needed:
            raise PolicyError("E_WAIVER_SOD", f"needs {needed} approver(s) distinct from the owner")
        prev = self.current(w.waiver_id)
        if prev is not None:
            if w.revision != prev.revision + 1:
                raise PolicyError("E_WAIVER_REVISION", "revisions are sequential")
            if w.expires_at > prev.expires_at and set(w.approvers) == set(prev.approvers):
                raise PolicyError("E_WAIVER_RENEWAL", "extending a waiver needs fresh approval")
        elif w.revision != 1:
            raise PolicyError("E_WAIVER_REVISION", "first revision is 1")
        self.history.append(w)
        return w

    def revoke(self, waiver_id: str, at: int) -> Waiver:
        cur = self.current(waiver_id)
        if cur is None:
            raise PolicyError("E_WAIVER_UNKNOWN", waiver_id)
        w = Waiver(**{**cur.__dict__, "revision": cur.revision + 1, "status": "revoked", "expires_at": min(cur.expires_at, at)})
        self.history.append(w)
        return w

    def current(self, waiver_id: str) -> Optional[Waiver]:
        cands = [w for w in self.history if w.waiver_id == waiver_id]
        return cands[-1] if cands else None

    def active(self, now: int) -> list:
        ids = sorted({w.waiver_id for w in self.history})
        return [w for w in (self.current(i) for i in ids) if w and w.status == "approved" and w.effective_at <= now < w.expires_at]

    def expiring(self, now: int, horizon_s: int) -> list:
        return [w for w in self.active(now) if w.expires_at - now <= horizon_s]

    def report(self, now: int) -> dict:
        act = self.active(now)
        return {"active": len(act), "by_risk": {r: sum(1 for w in act if w.risk == r) for r in ("low", "medium", "high")},
                "near_expiry_7d": len(self.expiring(now, 7 * 86400)),
                "by_control": sorted({w.control_id for w in act})}


def evaluate(policy: PolicySet, ctx: dict, now: int, waivers: Optional[WaiverRegistry] = None) -> dict:
    """Deterministic evaluation: highest-ranked matching deny wins unless waived (and waivable)."""
    trace = []
    matched = sorted((r for r in policy.rules if r.matches(ctx, now)),
                     key=lambda r: (-DOMAIN_RANK[r.domain], -r.priority, r.rule_id))
    applied_waivers = []
    effect = "allow"
    decided_by = None
    for r in matched:
        step = {"rule": r.rule_id, "domain": r.domain, "rank": DOMAIN_RANK[r.domain], "effect": r.effect}
        if r.effect in ("deny", "require") and effect == "allow":
            w = None
            if waivers is not None and r.domain not in NON_WAIVABLE and r.control_id:
                w = next((w for w in waivers.active(now) if w.control_id == r.control_id and w.applies(ctx, now)), None)
            if w is not None:
                step["waived_by"] = f"{w.waiver_id}@{w.revision}"
                applied_waivers.append(step["waived_by"])
            else:
                effect, decided_by = "deny", r.rule_id
        trace.append(step)
    return {"effect": effect, "decided_by": decided_by, "policy_revision": policy.revision,
            "policy_digest": policy.digest(), "waivers": applied_waivers, "trace": trace}


def simulate(old: PolicySet, new: PolicySet, contexts: list, now: int) -> dict:
    """Impact preview for canarying a policy change (MC-23-07, MC-23-09)."""
    changed = []
    for ctx in contexts:
        a, b = evaluate(old, ctx, now)["effect"], evaluate(new, ctx, now)["effect"]
        if a != b:
            changed.append({"context": ctx, "from": a, "to": b})
    return {"evaluated": len(contexts), "changed": changed, "old": old.revision, "new": new.revision}
