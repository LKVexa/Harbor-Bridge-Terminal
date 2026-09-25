"""Governance lane (MC-038, MC-074, MC-076): owners named, release waivers approved and unexpired, recurring
reviews done and not overdue, decisions (ADRs, licence, signing) closed.  Placeholders are failures.

    python -B -m inv28_unikernel_implementations.tools.governance_check [--today YYYY-MM-DD] [--json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys

from ._common import ROOT, read_json

SERVICE = re.compile(r"(?i)\b(bot|ci|service|automation|pipeline|claude)\b")


def check(today: dt.date) -> dict:
    owners, waivers, reviews, decisions = [], [], [], []
    holders = {}
    for r in read_json(ROOT / "ops" / "OWNERS.json")["roles"]:
        h = r.get("holder")
        holders[r["alias"]] = h
        if not h:
            owners.append(f"role {r['alias']} has no named holder")
        elif SERVICE.search(str(h)):
            owners.append(f"role {r['alias']} held by a service identity")
    if holders.get("inv28-security-owner") and holders.get("inv28-security-owner") == holders.get("inv28-component-owner"):
        owners.append("separation of duties: security owner == component owner (release approver)")
    for w in read_json(ROOT / "ops" / "WAIVERS.json")["entries"]:
        if w["status"] != "approved" or not w.get("approver"):
            waivers.append(f"{w['id']} not approved (status={w['status']})")
        elif SERVICE.search(str(w["approver"])) or w["approver"] == w.get("owner"):
            waivers.append(f"{w['id']} approver invalid")
        if dt.date.fromisoformat(w["expires"]) < today:
            waivers.append(f"{w['id']} expired {w['expires']}")
    for rv in read_json(ROOT / "ops" / "REVIEWS.json")["reviews"]:
        if not rv.get("last_done"):
            reviews.append(f"{rv['id']} never done")
        elif dt.date.fromisoformat(rv["last_done"]) + dt.timedelta(days=rv["interval_days"]) < today:
            reviews.append(f"{rv['id']} overdue")
    for d in read_json(ROOT / "ops" / "DECISIONS.json")["decisions"]:
        if d["status"] != "accepted":
            decisions.append(f"{d['id']} ({d['mc']}) {d['status']}: {d['title']}")
    ok = not (owners or waivers or reviews or decisions)
    return {"schema": "PK_GOVERNANCE/1", "today": today.isoformat(), "pass": ok, "owners": owners,
            "waivers": waivers, "reviews": reviews, "decisions": decisions}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=dt.date.today().isoformat())
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    r = check(dt.date.fromisoformat(a.today))
    if a.json:
        print(json.dumps(r, indent=1))
    else:
        for k in ("owners", "waivers", "reviews", "decisions"):
            for x in r[k]:
                print("GOVERNANCE", k, x)
        print("GOVERNANCE", "PASS" if r["pass"] else "FAIL")
    return 0 if r["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
