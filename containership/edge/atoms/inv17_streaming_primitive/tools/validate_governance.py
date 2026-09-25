"""C009/C097/C098/C099 governance validation: OWNERS completeness and freshness, waiver and
debt register shape and expiry. Exit 0 only when production-ready; the report lists every
problem. ``--today YYYY-MM-DD`` pins the clock for reproducible runs."""
import datetime as dt, json, sys
from _tools_pkg import ROOT

UNSET = {None, "", "UNASSIGNED"}


def check(today):
    problems, warnings = [], []
    o = json.loads((ROOT / "governance" / "OWNERS.json").read_text())
    for path in ("primary_owner.name", "primary_owner.contact", "deputy.name", "deputy.contact", "paging_target",
                 "service_team", "review.last_reviewed", "review.next_review_due"):
        cur = o
        for k in path.split("."):
            cur = cur.get(k) if isinstance(cur, dict) else None
        if cur in UNSET:
            problems.append(f"OWNERS: {path} unset")
    if o.get("primary_owner", {}).get("name") not in UNSET and o["primary_owner"]["name"] == o.get("deputy", {}).get("name"):
        problems.append("OWNERS: primary owner and deputy must differ")
    due = o.get("review", {}).get("next_review_due")
    if due not in UNSET and dt.date.fromisoformat(due) < today:
        problems.append("OWNERS: review overdue")
    for w in json.loads((ROOT / "governance" / "waivers.json").read_text())["waivers"]:
        for f in ("id", "control", "rationale", "owner", "approver", "scope", "expires", "status"):
            if w.get(f) in (None, ""):
                problems.append(f"waiver {w.get('id')}: missing {f}")
        if w.get("status") != "APPROVED":
            problems.append(f"waiver {w['id']}: status {w.get('status')} (not approved)")
        if w.get("approver") in UNSET:
            problems.append(f"waiver {w['id']}: no approver")
        if w.get("expires") and dt.date.fromisoformat(w["expires"]) < today:
            problems.append(f"waiver {w['id']}: EXPIRED {w['expires']}")
    for d in json.loads((ROOT / "governance" / "technical-debt.json").read_text())["items"]:
        if d.get("owner") in UNSET:
            warnings.append(f"debt {d['id']}: no owner")
    return {"today": today.isoformat(), "production_ready": not problems, "problems": problems, "warnings": warnings}


if __name__ == "__main__":
    today = dt.date.fromisoformat(sys.argv[sys.argv.index("--today") + 1]) if "--today" in sys.argv else dt.date.today()
    rep = check(today)
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence" / "governance.json").write_text(json.dumps(rep, indent=2) + "\n")
    print(json.dumps({"production_ready": rep["production_ready"], "problems": len(rep["problems"]), "warnings": len(rep["warnings"])}))
    sys.exit(0 if rep["production_ready"] else 1)
