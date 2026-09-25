#!/usr/bin/env python3
"""MC-041 - machine-readable production exit gate.

Aggregates evidence/ (certify, bench, coverage, release_verify), TRACEABILITY.json
and WAIVERS.json into evidence/PRODUCTION_EXIT.json with verdict
``PRODUCTION_APPROVED`` | ``NOT_ELIGIBLE``.  Blocks on: missing evidence file,
certification profile not passed, any BLOCKER waiver open, any expired waiver,
bench/coverage failures, dev-only or unverified release, traceability gaps.
Exit 0 only when approved.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
EV = PKG / "evidence"
REQUIRED = {"certify_certification.json": "passed", "bench.json": "passed", "release_verify.json": "production_eligible"}


def load(p):
    try:
        return json.loads(p.read_text())
    except (FileNotFoundError, ValueError):
        return None


def main():
    today = dt.date.today().isoformat()
    blockers, checks = [], {}
    for name, key in REQUIRED.items():
        doc = load(EV / name)
        ok = bool(doc and doc.get(key))
        checks[name] = {"present": doc is not None, "ok": ok, "sha256": hashlib.sha256((EV / name).read_bytes()).hexdigest() if doc else None}
        if not ok:
            blockers.append(f"{name}: {'missing' if doc is None else 'not passed'}" + (f" ({'; '.join(doc.get('problems', [])[:3])})" if doc else ""))
    cov = load(EV / "coverage.json")
    cov_ok = bool(cov) and cov.get("_tests_ok") and all(v["covered_pct"] >= v["threshold"] for k, v in cov.items() if not k.startswith("_"))
    checks["coverage.json"] = {"present": cov is not None, "ok": cov_ok}
    if not cov_ok:
        blockers.append("coverage gate not met or missing")
    tr = load(PKG / "TRACEABILITY.json")
    checks["TRACEABILITY.json"] = {"present": tr is not None, "summary": tr and tr["summary"]}
    if not tr or len(tr["rows"]) != 100:
        blockers.append("traceability incomplete")
    for w in load(PKG / "WAIVERS.json")["waivers"]:
        if w["expires"] < today:
            blockers.append(f"waiver {w['id']} expired {w['expires']}")
        elif w["severity"] == "blocker":
            blockers.append(f"blocker waiver {w['id']} open ({w['component']}): {w['exit_condition']}")
    rel = load(EV / "release_verify.json") or {}
    result = {
        "schema": "INV42_PRODUCTION_EXIT/1", "element": "INV-42", "version": (PKG / "VERSION").read_text().strip(),
        "evaluated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "artifact_sha256": rel.get("archive_sha256"),
        "verdict": "PRODUCTION_APPROVED" if not blockers else "NOT_ELIGIBLE",
        "blockers": blockers, "checks": checks,
    }
    EV.mkdir(exist_ok=True)
    (EV / "PRODUCTION_EXIT.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"verdict": result["verdict"], "blockers": blockers}, indent=1))
    return 0 if not blockers else 10


if __name__ == "__main__":
    sys.exit(main())
