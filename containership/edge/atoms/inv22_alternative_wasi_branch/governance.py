"""Waivers, drift policy, precedence engine and workload admission (MC-23, MC-28, MC-44, MC-63).

Precedence is fixed and fail-closed:
    integrity > security > semantic compatibility > residency > SLO > cost > operational
A lower tier can never override a deny from a higher tier.  Waivers may only
relax gates that declare themselves waivable, never integrity/security/
semantic denies, and only while signed-off, scoped and unexpired.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from . import canonical
from .errors import Inv22Error

TIERS = ("integrity", "security", "semantic", "residency", "slo", "cost", "operational")
UNWAIVABLE = frozenset({"integrity", "security", "semantic"})
POLICY_VERSION = 1


@dataclass(frozen=True)
class Waiver:
    waiver_id: str
    gate: str            # e.g. "drift.review_required"
    tier: str
    scope: str           # concrete component/branch/site scope
    owner: str
    approver: str
    requested_by: str
    risk: str
    compensating_controls: tuple
    issued_at: int
    expires_at: int

    def check(self, *, gate: str, scope: str, now: int) -> None:
        bad = None
        if self.tier not in TIERS or self.tier in UNWAIVABLE:
            bad = "tier cannot be waived"
        elif self.gate != gate or self.scope != scope:
            bad = "waiver does not cover this gate/scope"
        elif not self.approver or self.approver == self.requested_by:
            bad = "waiver needs an independent approver"
        elif not self.compensating_controls or not self.risk or not self.owner:
            bad = "waiver lacks risk/owner/compensating controls"
        elif not self.issued_at <= now < self.expires_at:
            bad = "waiver is not within its validity window"
        elif self.expires_at - self.issued_at > 90 * 86400:
            bad = "waiver exceeds maximum 90-day duration"
        if bad:
            raise Inv22Error("INV22.WAIVER.INVALID", bad, {"waiver_id": self.waiver_id})

    def digest(self) -> str:
        return canonical.digest({k: (list(v) if isinstance(v, tuple) else v) for k, v in self.__dict__.items()})


@dataclass(frozen=True)
class Finding:
    tier: str
    gate: str
    allow: bool
    reason: str


def decide(findings: Iterable[Finding], *, scope: str, now: int, waivers: Iterable[Waiver] = ()) -> dict:
    """Deterministic, explainable decision.  Unknown tiers are denies."""
    waivers = list(waivers)
    ordered = sorted(findings, key=lambda f: (TIERS.index(f.tier) if f.tier in TIERS else -1, f.gate))
    trail: list[dict] = []
    applied: list[str] = []
    for f in ordered:
        if f.tier not in TIERS:
            trail.append({"gate": f.gate, "tier": f.tier, "verdict": "deny", "reason": "unknown policy tier"})
            return {"allow": False, "decided_by": f.gate, "trail": trail, "waivers": applied, "policy_version": POLICY_VERSION}
        if f.allow:
            trail.append({"gate": f.gate, "tier": f.tier, "verdict": "allow", "reason": f.reason})
            continue
        covering = None
        if f.tier not in UNWAIVABLE:
            for w in waivers:
                try:
                    w.check(gate=f.gate, scope=scope, now=now)
                    covering = w
                    break
                except Inv22Error:
                    continue
        if covering is not None:
            trail.append({"gate": f.gate, "tier": f.tier, "verdict": "waived", "reason": f.reason, "waiver": covering.waiver_id})
            applied.append(covering.waiver_id)
            continue
        trail.append({"gate": f.gate, "tier": f.tier, "verdict": "deny", "reason": f.reason})
        return {"allow": False, "decided_by": f.gate, "trail": trail, "waivers": applied, "policy_version": POLICY_VERSION}
    return {"allow": True, "decided_by": None, "trail": trail, "waivers": applied, "policy_version": POLICY_VERSION}


# --- drift thresholds (MC-44) -------------------------------------------------

@dataclass(frozen=True)
class DriftPolicy:
    review_delta: int = 1        # any new divergent interface needs review
    block_delta: int = 3         # three or more new divergent interfaces in one release block it
    block_total: int = 16        # absolute ceiling


DEFAULT_DRIFT_POLICY = DriftPolicy()


def drift_findings(history: list[dict], policy: DriftPolicy = DEFAULT_DRIFT_POLICY) -> list[Finding]:
    if not history:
        return [Finding("operational", "drift.recorded", False, "no drift record for this release")]
    cur = history[-1]["divergent"]
    delta = cur - history[-2]["divergent"] if len(history) > 1 else 0
    out = [Finding("operational", "drift.recorded", True, f"{len(history)} releases recorded")]
    out.append(Finding("slo", "drift.block", delta < policy.block_delta and cur < policy.block_total,
                       f"divergent={cur} delta={delta} (block at delta>={policy.block_delta} or total>={policy.block_total})"))
    out.append(Finding("operational", "drift.review_required", delta < policy.review_delta,
                       f"delta={delta}; review required at delta>={policy.review_delta}"))
    return out


# --- admission (MC-23) --------------------------------------------------------

def admit(*, store, trust, site: str, cert_id: str, artifact_digest: str, now: int | None,
          max_revocation_age: int = 3600, audit_actor: str = "system:admission") -> dict:
    """Admit a workload only when its certificate verifies for the site's active branch."""
    from .cert import verify
    state = store.site_state(site)
    try:
        if state is None:
            raise Inv22Error("INV22.STATE.ILLEGAL_TRANSITION", "site has no active branch", {"site": site})
        if state["frozen"]:
            raise Inv22Error("INV22.SITE.FROZEN", "site admissions are frozen", {"site": site})
        rec = store.get_cert(cert_id)
        verify(rec["envelope"], trust, now=now, branch=state["branch"], artifact_digest=artifact_digest,
               revocation=store.revocation_snapshot(), max_revocation_age=max_revocation_age)
        if rec["status"] != "valid":
            raise Inv22Error("INV22.CERT.REVOKED", "certificate not in an admitting state", {"status": rec["status"]})
    except Inv22Error as err:
        store.record_event(actor=audit_actor, action="admission.refused", obj=f"{site}:{cert_id}",
                           after=err.code, reason=err.message)
        raise
    store.record_event(actor=audit_actor, action="admission.allowed", obj=f"{site}:{cert_id}",
                       after=state["branch"], reason=f"epoch {state['epoch']}")
    return {"admitted": True, "branch": state["branch"], "epoch": state["epoch"]}


def plan_branch_change(store, *, site: str, target_branch: str, workloads: dict[str, str], trust, now: int) -> dict:
    """Pre-activation impact check: every workload needs a verifying cert for the target branch.

    ``workloads`` maps artifact digest -> cert_id intended for the target branch.
    """
    from .cert import verify
    blocked = []
    for digest, cid in sorted(workloads.items()):
        try:
            verify(store.get_cert(cid)["envelope"], trust, now=now, branch=target_branch, artifact_digest=digest,
                   revocation=store.revocation_snapshot())
        except Inv22Error as e:
            blocked.append({"artifact": digest, "cert_id": cid, "code": e.code})
    return {"site": site, "target_branch": target_branch, "ok": not blocked, "blocked": blocked}
