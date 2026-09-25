"""Governance checks (C009, C098, C099, C094 EOL, C016 packaging consistency).

    python -m inv69_agentic_workload_layer.tools.governance_check [--today YYYY-MM-DD] [--json]

Exit 0 only when every check passes.  Failures are named; placeholders are failures, never passes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = re.compile(r"(?i)\b(bot|ci|service|automation|pipeline|claude)\b")
PLACEHOLDERS = {"", "UNASSIGNED", "TBD", "TODO", "N/A", None}


def _j(p):
    return json.loads((ROOT / p).read_text(encoding="utf-8"))


def check_owners() -> list[str]:
    out = []
    o = _j("ops/OWNERS.json")
    holders = {}
    for r in o["roles"]:
        if r["required"] and r["holder"] in PLACEHOLDERS:
            out.append(f"C009 owner role {r['alias']} has placeholder holder {r['holder']!r}")
        elif r["holder"] and SERVICE.search(str(r["holder"])):
            out.append(f"C009 owner role {r['alias']} held by a service identity")
        holders[r["alias"]] = r["holder"]
    so, ra = holders.get("inv69-security-owner"), holders.get("inv69-release-approver")
    if so not in PLACEHOLDERS and so == ra:
        out.append("C009 separation of duties: security owner == release approver")
    for doc in ("README.md", "docs/SECURITY.md", "ops/RUNBOOK.md"):
        if "OWNERS.md" not in (ROOT / doc).read_text(encoding="utf-8"):
            out.append(f"C009 {doc} does not link ops/OWNERS.md")
    co = (ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    for path in ("/runtime.py", "/governed.py", "/artifacts.py", "/config.py", "/ops/WAIVERS.json"):
        if path not in co:
            out.append(f"C009 CODEOWNERS lacks protected path {path}")
    return out


def check_waivers(today: dt.date) -> list[str]:
    out = []
    w = _j("ops/WAIVERS.json")
    req = ("id", "category", "controls", "scope", "rationale", "risk", "owner", "opened", "expires", "remediation", "status")
    for e in w["entries"]:
        miss = [k for k in req if e.get(k) in (None, "", [])]
        if miss:
            out.append(f"C099 {e.get('id')} missing fields {miss}")
        exp = dt.date.fromisoformat(e["expires"])
        opened = dt.date.fromisoformat(e["opened"])
        maxd = w["max_duration_days"].get(e["risk"], 30)
        if (exp - opened).days > maxd:
            out.append(f"C099 {e['id']} duration {(exp - opened).days}d exceeds max {maxd}d for risk {e['risk']}")
        if exp < today:
            out.append(f"C099 {e['id']} EXPIRED on {exp}")
        if e["status"] != "approved" or not e.get("approver"):
            out.append(f"C099 {e['id']} not approved (status={e['status']}, approver={e.get('approver')})")
        if e["risk"] in ("high", "security") and e["category"] == "technical_debt" and not (e.get("test_coverage") or e.get("compensating")):
            out.append(f"C099 {e['id']} safety debt lacks test coverage/compensating control")
    for d in w["deprecated_behaviors"]:
        if not d.get("removal_target"):
            out.append(f"C099 deprecation {d['id']} lacks removal target")
    return out


def check_reviews(today: dt.date) -> list[str]:
    out = []
    r = _j("ops/REVIEWS.json")
    for rv in r["reviews"]:
        if dt.date.fromisoformat(rv["next_due"]) < today:
            out.append(f"C098 review {rv['id']} overdue since {rv['next_due']}")
    for f in r["findings_register"]:
        if f["status"] != "closed" and dt.date.fromisoformat(f["due"]) < today:
            out.append(f"C098 finding {f['id']} overdue")
    return out


def check_versions() -> list[str]:
    out = []
    v = (ROOT / "VERSION").read_text().strip()
    init = (ROOT / "__init__.py").read_text()
    if f'__version__ = "{v}"' not in init:
        out.append("C016 __init__ version != VERSION")
    if f"## {v}" not in (ROOT / "CHANGELOG.md").read_text():
        out.append("C016 CHANGELOG lacks an entry for VERSION")
    m = _j("ops/COMPATIBILITY_MATRIX.json")
    if m["version"] != v:
        out.append("C093 compatibility matrix version != VERSION")
    if _j("RELEASE_MANIFEST.json").get("version") != v:
        out.append("C016 RELEASE_MANIFEST version != VERSION")
    sys.path.insert(0, str(ROOT.parent))
    from importlib import import_module
    compat = import_module(ROOT.name + ".compat")
    if compat.COMPONENT_VERSION != v:
        out.append("C016 compat.COMPONENT_VERSION != VERSION")
    eol = _j("ops/EOL.json")
    line = ".".join(v.split(".")[:2])
    if not any(l["line"] == line and l["state"] == "fully_supported" for l in eol["lines"]):
        out.append("C094 EOL table lacks a supported entry for this release line")
    return out


def run(today: dt.date) -> dict:
    results = {"owners": check_owners(), "waivers": check_waivers(today), "reviews": check_reviews(today),
               "versions": check_versions()}
    results["pass"] = not any(results[k] for k in ("owners", "waivers", "reviews", "versions"))
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=dt.date.today().isoformat())
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    res = run(dt.date.fromisoformat(a.today))
    if a.json:
        print(json.dumps(res, indent=2))
    else:
        for k in ("owners", "waivers", "reviews", "versions"):
            for m in res[k]:
                print("FAIL", m)
        print("GOVERNANCE", "PASS" if res["pass"] else "FAIL")
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
