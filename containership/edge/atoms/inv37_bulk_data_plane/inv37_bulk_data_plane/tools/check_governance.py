"""Governance gate (C009, C098, C099).  Validates structure strictly; reports
BLOCKED when roles are unassigned, reviews are overdue, or waivers are invalid.
Exit 0 PASS, 1 INVALID (malformed metadata), 2 BLOCKED."""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REQUIRED_ROLES = {"service_owner", "backup_owner", "security_owner", "sre_owner", "architecture_approver"}
REQUIRED_RACI = {"architecture_decision", "schema_change", "transport_change", "security_exception", "incident_command",
                 "release_approval", "rollback", "policy_precedence"}
MAX_WAIVER_DAYS = 90


def check(root: Path = HERE, today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    invalid, blocked = [], []
    try:
        owners = json.loads((root / "governance" / "OWNERS.json").read_text())
        waivers = json.loads((root / "governance" / "WAIVERS.json").read_text())
        codeowners = (root / "governance" / "CODEOWNERS").read_text()
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "INVALID", "invalid": [f"unreadable:{exc}"], "blocked": []}
    roles = owners.get("roles", {})
    if set(roles) != REQUIRED_ROLES:
        invalid.append(f"roles mismatch: {sorted(set(roles) ^ REQUIRED_ROLES)}")
    for name, r in roles.items():
        if not r.get("codeowners_handle") or r["codeowners_handle"] not in codeowners:
            invalid.append(f"{name}: codeowners handle missing or unbound")
        if not r.get("assignee"):
            blocked.append(f"{name}: unassigned")
    raci = owners.get("raci", {})
    if set(raci) != REQUIRED_RACI:
        invalid.append(f"raci mismatch: {sorted(set(raci) ^ REQUIRED_RACI)}")
    for k, v in raci.items():
        for key in ("R", "A"):
            if v.get(key) not in roles:
                invalid.append(f"raci.{k}.{key} references unknown role")
    if not owners.get("escalation"):
        invalid.append("escalation path missing")
    try:
        if dt.date.fromisoformat(owners["review_by"]) < today:
            blocked.append("owner review overdue")
    except (KeyError, ValueError):
        invalid.append("review_by missing/invalid")
    if not owners.get("tabletop", {}).get("last_exercised"):
        blocked.append("escalation tabletop not exercised")
    active_waivers = []
    for w in waivers.get("waivers", []):
        need = {"requirement", "justification", "compensating_controls", "approver_role", "approver", "created", "expires"}
        if need - set(w):
            invalid.append(f"waiver {w.get('requirement')} missing {sorted(need - set(w))}")
            continue
        c, e = dt.date.fromisoformat(w["created"]), dt.date.fromisoformat(w["expires"])
        if (e - c).days > MAX_WAIVER_DAYS:
            invalid.append(f"waiver {w['requirement']} exceeds {MAX_WAIVER_DAYS} days")
        elif e < today:
            blocked.append(f"waiver {w['requirement']} expired")
        else:
            active_waivers.append(w["requirement"])
    status = "INVALID" if invalid else ("BLOCKED" if blocked else "PASS")
    return {"schema": "INV37_GOVERNANCE_CHECK/1", "status": status, "invalid": invalid, "blocked": blocked,
            "active_waivers": active_waivers}


def main() -> int:
    r = check()
    print(json.dumps(r, indent=1))
    return {"PASS": 0, "INVALID": 1, "BLOCKED": 2}[r["status"]]


if __name__ == "__main__":
    sys.exit(main())
