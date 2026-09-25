"""INV-38-C098/C099 — Governance checks: reviews overdue + waiver register."""
from __future__ import annotations

class GovernanceError(RuntimeError):
    code = "PK_BYPASS_GOVERNANCE_BLOCK"

def overdue_reviews(schedule: list[dict], now: float) -> list[str]:
    return [r["type"] for r in schedule if r.get("next_review_epoch", 0) < now]

def validate_waivers(waivers: list[dict], now: float) -> list[str]:
    problems, seen = [], set()
    required = {"id", "requirement", "scope", "rationale", "risk",
                "compensating_controls", "owner", "approver", "created", "expiry", "review"}
    for w in waivers:
        missing = required - set(w)
        if missing:
            problems.append(f"{w.get('id','?')} missing fields {sorted(missing)}")
            continue
        if w["id"] in seen:
            problems.append(f"duplicate waiver id {w['id']}")
        seen.add(w["id"])
        if w["expiry"] < now:
            problems.append(f"{w['id']} expired")
        if not w["owner"] or not w["approver"]:
            problems.append(f"{w['id']} ownerless/unapproved")
        if w.get("waives_safety_invariant"):
            problems.append(f"{w['id']} attempts to waive a non-waivable safety invariant")
    return problems

def release_blocked(schedule: list[dict], waivers: list[dict], now: float) -> list[str]:
    problems: list[str] = []
    overdue = overdue_reviews(schedule, now)
    if overdue:
        problems.append(f"reviews overdue: {overdue}")
    problems.extend(validate_waivers(waivers, now))
    return problems
