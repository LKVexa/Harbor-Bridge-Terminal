"""Build the requirement→implementation→verification matrix and the v4.3.0 audit update.

  python tools/build_rtm.py          write requirements/traceability.json, AUDIT_MATRIX.json, CLOSURE_LEDGER.json
  python tools/build_rtm.py --check  exit 1 on drift or on any evidence path that does not exist

AUDIT_MATRIX status policy (from the closure checklist): a row may become
`present` only when its evidence exists AND owner/reviewer approval is recorded.
Approvals are read from governance/APPROVALS.json; none are recorded in 4.3.0,
so implemented rows move to `partial` with the remaining gap stated exactly.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))
import closure_map as cm  # noqa: E402

BASELINE = PKG / "audit" / "AUDIT_MATRIX_v4.2.0.json"


def _path_of(evidence: str) -> str:
    return re.split(r"::|#| \(", evidence, maxsplit=1)[0].strip()


#: Outputs the release gate itself writes (verify.py step 5/7); checked after generation there.
GENERATED = ("release/", "conformance/", "evidence/", "requirements/traceability.json")


def _exists(evidence: str) -> bool:
    p = _path_of(evidence)
    if p.startswith(GENERATED):
        return True
    return (PKG / p).exists() or (p.endswith("/") and (PKG / p.rstrip("/")).is_dir())


def _digest(evidence: str) -> str | None:
    if _path_of(evidence).startswith(GENERATED) or _path_of(evidence) in ("AUDIT_MATRIX.json", "CLOSURE_LEDGER.json"):
        return None
    p = PKG / _path_of(evidence)
    if p.is_file():
        return hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    return None


def _approved(check_id: str, approvals: list[dict]) -> bool:
    from fnmatch import fnmatch
    return any(a.get("requirement") and fnmatch(check_id, a["requirement"]) and a["status"] == "approved"
               for a in approvals)


def build() -> dict[str, str]:
    checklist = json.loads((PKG / "CHECKLIST.json").read_text())
    baseline = json.loads(BASELINE.read_text())
    approvals = json.loads((PKG / "governance" / "APPROVALS.json").read_text())["approvals"]
    base_rows = {r["check_id"]: r for r in baseline["requirements"]}
    rtm_rows, audit_rows, ledger = [], [], []
    missing_paths = []
    for item in checklist["items"]:
        cid = item["check_id"]
        short = cid.split("-")[-1]
        base = base_rows[cid]
        if short in cm.ROWS:
            impl, tests, docs, extra, still_missing = cm.ROWS[short]
            evidence = sorted(set(impl + tests + docs))
            for e in evidence:
                if not _exists(e):
                    missing_paths.append(f"{cid}: {e}")
            blockers = ([] if _approved(cid, approvals) else [cm.OWNER]) + extra
            if still_missing:
                status = "missing"
            elif blockers:
                status = "partial"
            else:
                status = "present"
            closure = "open" if still_missing else ("implemented_pending" if blockers else "closed")
        else:
            evidence, tests, blockers, status, closure = base["evidence"], [], [], base["status"], "baseline_present"
        rtm_rows.append({
            "check_id": cid, "dimension": item["dimension"], "requirement": item["requirement"],
            "baseline_status_4_2_0": base["status"], "status": status, "closure": closure,
            "implementation": evidence,
            "verification": sorted(set(tests)),
            "evidence_digests": {e: _digest(e) for e in evidence if _digest(e)},
            "blockers": blockers,
        })
        audit_rows.append({**base, "status": status, "evidence": evidence,
                           "remaining_gap": "; ".join(blockers) if status != "present" else ""})
        if short in cm.ROWS:
            ledger.append({"id": cid, "title": base.get("remaining_gap") or item["requirement"],
                           "baseline": base["status"], "now": status, "closure": closure, "blockers": blockers})
    for rid, (title, paths, blockers) in cm.REPO.items():
        blockers = ([] if _approved(rid, approvals) else [cm.OWNER]) + blockers
        for p in paths:
            if not _exists(p):
                missing_paths.append(f"{rid}: {p}")
        ledger.append({"id": rid, "title": title, "baseline": "missing",
                       "now": "partial" if blockers else "present", "closure": "implemented_pending" if blockers else "closed",
                       "evidence": paths, "blockers": blockers})
    counts = {s: sum(r["status"] == s for r in audit_rows) for s in ("present", "partial", "missing")}
    version = (PKG / "VERSION").read_text().strip()
    audit = {"schema": "INV35_AUDIT_MATRIX/1", "repository_version": version, "audit_date": "2026-09-22",
             "method": ("v4.3.0 closure pass: static audit + executable suites (unit, contracts, fixtures, fuzz, "
                        "concurrency, security, faults, integration doubles, performance gate). Status `present` "
                        "requires recorded owner approval; none recorded yet. pk_core unavailable."),
             "baseline": "audit/AUDIT_MATRIX_v4.2.0.json", "counts": counts, "requirements": audit_rows}
    rtm = {"schema": "INV35_RTM/1", "version": version, "row_count": len(rtm_rows),
           "requirements_doc": "docs/requirements/INV-35_REQUIREMENTS.md", "rows": rtm_rows}
    closure_counts = {}
    for e in ledger:
        closure_counts[e["closure"]] = closure_counts.get(e["closure"], 0) + 1
    led = {"schema": "INV35_CLOSURE_LEDGER/1", "version": version, "work_packages": len(ledger),
           "closure_counts": closure_counts, "packages": ledger}
    if missing_paths:
        raise SystemExit("RTM=FAIL missing evidence paths:\n  " + "\n  ".join(missing_paths))
    dump = lambda o: json.dumps(o, indent=2) + "\n"  # noqa: E731
    return {"requirements/traceability.json": dump(rtm), "AUDIT_MATRIX.json": dump(audit),
            "CLOSURE_LEDGER.json": dump(led)}


def main() -> int:
    outputs = build()
    if "--check" in sys.argv:
        drift = [rel for rel, text in outputs.items() if not (PKG / rel).is_file() or (PKG / rel).read_text() != text]
        if drift:
            print("RTM=DRIFT " + " ".join(drift))
            return 1
        print("RTM=OK")
        return 0
    for rel, text in outputs.items():
        (PKG / rel).parent.mkdir(parents=True, exist_ok=True)
        (PKG / rel).write_text(text)
    print("RTM=WRITTEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
