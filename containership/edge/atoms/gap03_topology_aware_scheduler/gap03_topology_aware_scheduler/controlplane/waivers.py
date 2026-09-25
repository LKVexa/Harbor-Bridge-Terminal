"""MC-045 - Exception / waiver / debt registry (GAP03-WAIVER/1)."""
from __future__ import annotations

import datetime as dt
import json

REQUIRED = ("id", "control_ids", "severity", "scope", "owner", "created", "expires", "compensating_controls",
            "approval", "status", "rationale", "residual_risk", "links", "applies_to_version")
NON_WAIVABLE_PREFIXES = ("PG-005", "PG-006")  # distributed safety and auditability are never waivable
SEVERITIES = ("P0", "P1", "P2", "P3")
MAX_DAYS = {"P0": 30, "P1": 90, "P2": 180, "P3": 365}


def validate(entry: dict, *, today: dt.date, current_version: str | None = None) -> list[str]:
    p = [f"missing {k}" for k in REQUIRED if k not in entry]
    if p:
        return p
    if any(c.startswith(NON_WAIVABLE_PREFIXES) for c in entry["control_ids"]):
        p.append("non-waivable control")
    links = entry["links"] if isinstance(entry["links"], dict) else {}
    for k in ("work_items", "rtm"):
        if not links.get(k):
            p.append(f"missing link: {k}")
    if not entry["residual_risk"]:
        p.append("no residual-risk assessment")
    if current_version and entry["applies_to_version"] != current_version:
        p.append("reassessment required: version changed")
    if entry["severity"] not in SEVERITIES:
        p.append("bad severity")
    if not entry["owner"] or entry["owner"].startswith("UNASSIGNED"):
        p.append("no accountable owner")
    created, expires = dt.date.fromisoformat(entry["created"]), dt.date.fromisoformat(entry["expires"])
    if (expires - created).days > MAX_DAYS.get(entry["severity"], 0):
        p.append("expiry exceeds severity maximum")
    if expires < today:
        p.append("expired")
    ap = entry["approval"]
    if not isinstance(ap, dict) or not ap.get("approver") or not ap.get("record"):
        p.append("no approval record")
    if not entry["compensating_controls"]:
        p.append("no compensating controls")
    return p


def active(registry: list[dict], *, today: dt.date, current_version: str | None = None) -> list[dict]:
    return [w for w in registry if w.get("status") == "approved" and not validate(w, today=today, current_version=current_version)]


def covers(registry: list[dict], control_id: str, *, today: dt.date, current_version: str | None = None) -> dict | None:
    for w in active(registry, today=today, current_version=current_version):
        if control_id in w["control_ids"]:
            return w
    return None


def expiring(registry: list[dict], *, today: dt.date, within_days: int = 14) -> list[str]:
    return [w["id"] for w in registry if w.get("expires") and
            0 <= (dt.date.fromisoformat(w["expires"]) - today).days <= within_days]


def load(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["waivers"]


def summary(registry: list[dict], *, today: dt.date) -> dict:
    """Release summary: waived controls are reported as WAIVED, never as passed."""
    act = active(registry, today=today)
    by_sev: dict = {}
    for w in act:
        by_sev[w["severity"]] = by_sev.get(w["severity"], 0) + len(w["control_ids"])
    return {"active": len(act), "waived_controls": sorted(c for w in act for c in w["control_ids"]), "by_severity": by_sev,
            "oldest_days": max(((today - dt.date.fromisoformat(w["created"])).days for w in act), default=0),
            "invalid": {w.get("id", "?"): validate(w, today=today) for w in registry if validate(w, today=today)}}


def apply_change(registry: list[dict], change: dict, *, principal: dict, audit, today: dt.date) -> list[dict]:
    """create/edit/approve/close a waiver; every change is authorised and audited; closed records are kept."""
    if "waiver.approve" not in principal.get("perms", set()) and change["op"] in ("approve", "close"):
        audit.append(actor=principal.get("sub", "?"), action=f"waiver.{change['op']}", target=change.get("id", "?"), result="denied")
        from .errors import SchedulerError
        raise SchedulerError("PERMISSION_DENIED", "waiver.approve required")
    reg = [dict(w) for w in registry]
    before = next((w for w in reg if w["id"] == change["id"]), None)
    if change["op"] == "create":
        reg.append(dict(change["waiver"], status="draft"))
    elif change["op"] == "edit":
        before.update(change["fields"])
        before["status"] = "draft"  # any edit forces re-approval
    elif change["op"] == "approve":
        before.update(status="approved", approval={"approver": principal["sub"], "record": change["record"]})
    elif change["op"] == "close":
        before.update(status="closed", closed=today.isoformat())
    after = next(w for w in reg if w["id"] == change["id"])
    audit.append(actor=principal["sub"], action=f"waiver.{change['op']}", target=change["id"], result="ok", before=before, after=after)
    return reg
