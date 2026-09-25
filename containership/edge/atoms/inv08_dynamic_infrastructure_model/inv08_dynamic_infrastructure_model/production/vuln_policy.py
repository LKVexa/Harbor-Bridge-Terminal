"""Component 63 - vulnerability SLA matrix, support/EOL windows, patch intake,
emergency release routing and upgrade enforcement (PK_DYN_VULN/1).
Policy text: docs/63_vuln_policy.md; data: vuln_policy.json.  Dates are
``datetime.date``; no wall clock is read (callers inject ``today``).
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from .pkcore_pin import parse_version

PATH = Path(__file__).resolve().parent / "vuln_policy.json"


def load(path: Path = PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def severity(cvss: float, policy: dict) -> str:
    if not isinstance(cvss, (int, float)) or isinstance(cvss, bool) or not 0 <= cvss <= 10:
        raise ValueError(f"CVSS score must be within 0..10, got {cvss!r}")
    for floor, sev in policy["severity_from_cvss"]:
        if cvss >= floor:
            return sev
    return "none"


def due(sev: str, disclosed: dt.date, policy: dict) -> dict:
    sla = policy["sla_days"][sev]
    return {"triage_by": disclosed + dt.timedelta(days=sla["triage"]),
            "fix_by": None if sla["fix"] is None else disclosed + dt.timedelta(days=sla["fix"])}


def intake(advisory: dict, policy: dict, today: dt.date) -> dict:
    """Triage a dependency/package advisory: {id, cvss, disclosed(date), affects:[versions], fixed_in}."""
    for k in ("id", "cvss", "disclosed"):
        if k not in advisory:
            raise ValueError(f"advisory missing {k}")
    sev = severity(advisory["cvss"], policy)
    d = due(sev, advisory["disclosed"], policy)
    overdue = d["fix_by"] is not None and today > d["fix_by"] and not advisory.get("fixed_in")
    return {"id": advisory["id"], "severity": sev, **d, "overdue": overdue,
            "emergency_release": sev in policy["emergency_release_for"],
            "route": "emergency-release" if sev in policy["emergency_release_for"] else "scheduled-patch"}


def supported(version: str, policy: dict, today: dt.date) -> dict:
    v = parse_version(version)
    rels = sorted(policy["releases"], key=lambda r: parse_version(r["version"]).key(), reverse=True)
    minors = []
    for r in rels:
        mm = parse_version(r["version"]).release[:2]
        if mm not in minors:
            minors.append(mm)
    mm = v.release[:2]
    if mm not in minors:
        return {"supported": False, "reason": "unknown release line"}
    idx = minors.index(mm)
    if idx >= policy["support"]["supported_minor_releases"]:
        return {"supported": False, "reason": "outside supported minor window"}
    for r in rels:
        if parse_version(r["version"]).release[:2] == mm and r.get("superseded"):
            eol = dt.date.fromisoformat(r["superseded"]) + dt.timedelta(
                days=30 * policy["support"]["security_fix_months_after_supersede"])
            if today > eol:
                return {"supported": False, "reason": f"EOL since {eol.isoformat()}"}
            return {"supported": True, "eol": eol.isoformat()}
    return {"supported": True, "eol": None}


def enforce_upgrade(running: str, advisories: list[dict], policy: dict, today: dt.date) -> dict:
    """Refuse to operate an unsupported version or one with an overdue critical/high fix available."""
    s = supported(running, policy, today)
    reasons = [] if s["supported"] else [s["reason"]]
    rv = parse_version(running).key()
    for a in advisories:
        t = intake(a, policy, today)
        fixed = a.get("fixed_in")
        if fixed and rv < parse_version(fixed).key() and t["severity"] in {"critical", "high"} \
                and t["fix_by"] is not None and today > t["fix_by"]:
            reasons.append(f"{a['id']} ({t['severity']}) fixed in {fixed}; upgrade overdue")
    notify = policy["notification"]["channels"]
    return {"allowed": not reasons, "reasons": reasons,
            "notification_blocked": all(c.startswith("UNASSIGNED") for c in notify)}
