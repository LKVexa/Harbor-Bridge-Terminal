"""Governance evidence (INV-68 MC-03, MC-04, MC-36, MC-39; C009, C010, C094, C098, C099).

    python -m inv68_resource_packing.tools.governance_check [--today YYYY-MM-DD] [--out evidence/]

Machine-checks what only people can close: named owners and on-call route,
ADR approval with named reviewers, performed reviews within cadence, and a
register whose entries are owned, approved and unexpired.  Produces
``GOVERNANCE.json``; any unmet item is a FAIL with its reason.  Nothing here
can be satisfied by code -- that is the point.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

from .common import PKG, write


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PKG / "evidence"))
    ap.add_argument("--today")
    a = ap.parse_args(argv)
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    problems: list[str] = []
    owners = json.loads((PKG / "ops" / "owners.json").read_text())
    for r in owners["roles"]:
        if not r.get("assignee"):
            problems.append(f"owners: role {r['role']} unassigned")
    if not owners["on_call"].get("route"):
        problems.append("owners: no on-call route")
    adr = (PKG / "ops" / "ADR-0001-resource-packing.md").read_text()
    status = re.search(r"^\*\*Status:\*\*\s*(\S+)", adr, re.M)
    if not status or status.group(1).upper() != "ACCEPTED":
        problems.append(f"ADR-0001: status {status.group(1) if status else 'missing'} (needs ACCEPTED with named approvers)")
    if re.search(r"^\*\*Approvers:\*\*\s*(none|TBD|-)", adr, re.M | re.I):
        problems.append("ADR-0001: no named approvers")
    reviews = json.loads((PKG / "ops" / "REVIEWS.json").read_text())
    for rv in reviews["cadence"]:
        if not rv.get("last"):
            problems.append(f"review never performed: {rv['review']}")
        elif (today - dt.date.fromisoformat(rv["last"])).days > rv["every_days"]:
            problems.append(f"review overdue: {rv['review']}")
    reg = json.loads((PKG / "ops" / "REGISTER.json").read_text())
    for e in reg["entries"]:
        if not e.get("owner") or not e.get("approvers") or e.get("status") != "active":
            problems.append(f"register {e['id']}: not owned/approved/active ({e.get('status')})")
        if dt.date.fromisoformat(e["expires"]) < today:
            problems.append(f"register {e['id']}: expired {e['expires']}")
    lic = (PKG / "LICENSING.md").read_text()
    if "UNDECIDED" in lic:
        problems.append("license: distribution license not chosen by the owner (LICENSING.md)")
    sec = (PKG / "SECURITY_RESPONSE.md").read_text()
    if "UNASSIGNED" in sec:
        problems.append("vulnerability response: intake contact unassigned")
    doc = {"schema": "PK_PACK_GOVERNANCE/1", "today": today.isoformat(), "problems": problems,
           "result": "PASS" if not problems else "FAIL",
           "note": "Governance items require named humans; code cannot close them."}
    write(Path(a.out) / "GOVERNANCE.json", doc)
    print(f"GOVERNANCE {doc['result']}: {len(problems)} open items")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
