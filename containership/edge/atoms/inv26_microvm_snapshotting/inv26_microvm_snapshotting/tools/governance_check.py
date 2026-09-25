"""Governance gate (C009, C098, C099): required roles assigned, on-call route present, waivers approved."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]


def check() -> dict:
    own = json.loads((PKG / "ops" / "ownership.json").read_text())
    reg = json.loads((PKG / "ops" / "REGISTER.json").read_text())
    rev = json.loads((PKG / "ops" / "REVIEWS.json").read_text())
    roles = {r["role"]: r for r in own["roles"]}
    problems = []
    for need in own["required_roles"]:
        if need not in roles:
            problems.append(f"role {need} missing from ownership.json")
        elif not roles[need].get("assignee"):
            problems.append(f"role {need} unassigned")
    if not (own.get("on_call") or {}).get("route"):
        problems.append("no on-call paging route")
    for e in reg["entries"]:
        if e["type"] == "waiver" and (not e.get("approver") or not e.get("expiry")):
            problems.append(f"{e['id']} waiver lacks approver/expiry")
    for r in rev["cadence"]:
        if r.get("last") is None:
            problems.append(f"review '{r['review']}' never performed")
    codeowners = (PKG / "CODEOWNERS").read_text()
    if "@inv26-security" not in codeowners:
        problems.append("CODEOWNERS lacks security owner for crypto/auth")
    return {"schema": "PK_SNAPSHOT_GOVERNANCE/1", "problems": problems,
            "result": "PASS" if not problems else "GOVERNANCE_PENDING"}


def main() -> int:
    res = check()
    print(json.dumps(res, indent=1))
    return 0 if res["result"] == "PASS" else 3


if __name__ == "__main__":
    sys.exit(main())
