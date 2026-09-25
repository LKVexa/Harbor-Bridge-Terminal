"""Governance checks (MC-012, MC-039, MC-040, MC-036; C009, C098, C099, C094).

    python -B -m inv27_unikernel_execution.tools.governance_check [--today YYYY-MM-DD]

Fails (exit 1) on: unassigned or service-identity owners; security owner == release approver; a waiver
that is not approved, has no human approver, or is expired; a review cadence with no review held within
its window; an EOL entry for the current version missing.  Placeholders are failures, never passes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys

from ._refs import ROOT, load

SERVICE = re.compile(r"(?i)\b(bot|ci|service|automation|pipeline|claude)\b")
PLACEHOLDER = {"", "UNASSIGNED", "TBD", "TODO", None}


def check(today: dt.date) -> dict:
    out = {"owners": [], "waivers": [], "reviews": [], "versions": []}
    owners = load("ops/OWNERS.json")
    h = {}
    for r in owners["roles"]:
        if r["required"] and r["holder"] in PLACEHOLDER:
            out["owners"].append(f"{r['alias']} unassigned")
        elif r["holder"] and SERVICE.search(str(r["holder"])):
            out["owners"].append(f"{r['alias']} held by a service identity")
        h[r["alias"]] = r["holder"]
    if h.get("inv27-security-owner") not in PLACEHOLDER and h.get("inv27-security-owner") == h.get("inv27-release-approver"):
        out["owners"].append("security owner == release approver")
    for w in load("ops/WAIVERS.json")["entries"]:
        if w["status"] != "approved":
            out["waivers"].append(f"{w['id']} is {w['status']}")
        elif not w.get("approver") or SERVICE.search(str(w["approver"])):
            out["waivers"].append(f"{w['id']} has no human approver")
        elif dt.date.fromisoformat(w["expires"]) < today:
            out["waivers"].append(f"{w['id']} expired {w['expires']}")
    rev = load("ops/REVIEWS.json")
    held = {x["review"]: dt.date.fromisoformat(x["date"]) for x in rev["held"]}
    for c in rev["cadence"]:
        if "every_days" in c and (c["review"] not in held or (today - held[c["review"]]).days > c["every_days"]):
            out["reviews"].append(f"review '{c['review']}' not held within {c['every_days']} days")
    ver = (ROOT / "VERSION").read_text().strip()
    if not any(ver.startswith(s["version"].rstrip("x")) for s in load("ops/EOL.json")["supported"]):
        out["versions"].append(f"VERSION {ver} not covered by ops/EOL.json")
    for doc in ("README.md", "SECURITY.md", "ops/RUNBOOK.md"):
        if "OWNERS.md" not in (ROOT / doc).read_text(encoding="utf-8"):
            out["owners"].append(f"{doc} does not link ops/OWNERS.md")
    out["pass"] = not any(out[k] for k in ("owners", "waivers", "reviews", "versions"))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=dt.date.today().isoformat())
    a = ap.parse_args(argv)
    r = check(dt.date.fromisoformat(a.today))
    (ROOT / "evidence" / "GOVERNANCE_CHECK.json").write_text(json.dumps(r, indent=1))
    for k in ("owners", "waivers", "reviews", "versions"):
        for f in r[k]:
            print("FAIL", k, f)
    print("GOVERNANCE", "PASS" if r["pass"] else "FAIL")
    return 0 if r["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
