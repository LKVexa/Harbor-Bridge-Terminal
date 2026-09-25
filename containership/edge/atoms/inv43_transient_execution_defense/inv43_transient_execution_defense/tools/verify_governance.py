"""Items 01, 07, 49, 50, 52 (+02, 35): mechanical governance checks.

    python tools/verify_governance.py [--root DIR] [--today YYYY-MM-DD] [--strict]

Reports every production blocker it can see.  ``--strict`` exits 1 when any
blocker exists (production gate mode); without it the report is written and
the exit code is 0 unless an artifact is *inconsistent* (digest mismatch,
expired exception, malformed file) - those always fail.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def sha256(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check(root: pathlib.Path, today: dt.date) -> dict:
    blockers, failures = [], []

    prov = json.loads((root / "provenance" / "PROVENANCE.json").read_text())
    for a in prov["artifacts"]:
        p = root / a["path"]
        if a["status"] == "present":
            if not p.exists():
                failures.append({"code": "provenance_artifact_absent", "path": a["path"]})
            elif sha256(p) != a["sha256"]:
                failures.append({"code": "provenance_digest_mismatch", "path": a["path"]})
        elif a["status"] == "missing":
            if p.exists():
                failures.append({"code": "provenance_declared_missing_but_present", "path": a["path"]})
            exc = a.get("exception")
            if not exc:
                failures.append({"code": "provenance_missing_without_exception", "path": a["path"]})
            else:
                blockers.append({"code": "provenance_artifact_missing", "path": a["path"], "exception": exc})
        else:
            failures.append({"code": "provenance_bad_status", "path": a["path"]})

    owners = json.loads((root / "governance" / "OWNERS.json").read_text())
    for k in ("accountable_owner", "owning_team", "security_contact", "on_call_rotation"):
        if not owners.get(k):
            blockers.append({"code": "owner_unassigned", "field": k})

    exc = json.loads((root / "governance" / "EXCEPTIONS.json").read_text())
    ids = set()
    for e in exc["entries"]:
        if e["id"] in ids:
            failures.append({"code": "exception_duplicate_id", "id": e["id"]})
        ids.add(e["id"])
        for f in ("id", "type", "item", "statement", "status", "opened", "expires"):
            if f not in e:
                failures.append({"code": "exception_malformed", "id": e.get("id"), "field": f})
        if dt.date.fromisoformat(e["expires"]) < today:
            failures.append({"code": "exception_expired", "id": e["id"], "expires": e["expires"]})
        if e["status"] != "APPROVED" or not e.get("approved_by") or not e.get("owner"):
            blockers.append({"code": "exception_unapproved", "id": e["id"]})

    rev = json.loads((root / "governance" / "REVIEW_SCHEDULE.json").read_text())
    done = {r["review"]: dt.date.fromisoformat(r["date"]) for r in rev.get("records", [])}
    for c in rev["cadence"]:
        last = done.get(c["review"])
        if last is None:
            blockers.append({"code": "review_never_performed", "review": c["review"]})
        elif (today - last).days > c["every_days"]:
            blockers.append({"code": "review_overdue", "review": c["review"]})

    lock = json.loads((root / "deps" / "pk_core.lock.json").read_text())
    if lock["status"] != "PINNED" or not lock.get("approved_digest"):
        blockers.append({"code": "pk_core_unpinned"})

    notice = (root / "NOTICE").read_text()
    if "LICENSE STATUS: UNDECIDED" in notice or not (root / "LICENSE").exists():
        blockers.append({"code": "license_undecided"})

    thr = json.loads((root / "perf" / "thresholds.json").read_text())
    if thr.get("status") != "APPROVED" or not thr.get("approved_by"):
        blockers.append({"code": "perf_thresholds_unapproved"})

    pol = json.loads((root / "policy" / "default_policy.json").read_text())
    if not str(pol.get("status", "")).startswith("APPROVED"):
        blockers.append({"code": "policy_unapproved", "version": pol.get("version")})

    for adr in sorted((root / "docs" / "adr").glob("ADR-*.md")):
        head = adr.read_text().split("\n", 4)[:4]
        if not any("**Status:** APPROVED" in line for line in head):
            blockers.append({"code": "adr_unapproved", "adr": adr.name})

    return {"schema": "INV43_GOVERNANCE_REPORT/1", "checked_on": today.isoformat(),
            "consistent": not failures, "failures": failures, "blockers": blockers,
            "production_ready": not failures and not blockers}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--today", default=dt.date.today().isoformat())
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    rep = check(pathlib.Path(a.root), dt.date.fromisoformat(a.today))
    text = json.dumps(rep, indent=2, sort_keys=True)
    if a.out:
        pathlib.Path(a.out).write_text(text)
    print(text)
    if rep["failures"]:
        return 2
    return 1 if (a.strict and rep["blockers"]) else 0


if __name__ == "__main__":
    sys.exit(main())
