"""2,376-check status ledger for the 66 missing-component checklists.

Derivation is mechanical and reproducible (``python -m ...production.status``):

* checks 05-19 come from each component's five engineering sub-parts
  (``components/NN.json``): spec (05/08/11/14/17) = LOCALLY_VERIFIED when the named
  spec file exists; implement (06/09/...) mirrors the sub-part state; verify
  (07/10/...) = LOCALLY_VERIFIED only when the sub-part is IMPLEMENTED *and* every
  listed test id passed in THIS run (tests are executed, not assumed).
* the 21 generic checks (01-04, 20-36) are decided by fixed rules below; any
  check that needs a named human, an independent reviewer, a representative
  environment or production signing is BLOCKED with that input named.

States: LOCALLY_VERIFIED | PARTIAL | BLOCKED.  There is deliberately no
COMPLETE state: rule 1 of the checklist ("implementation and objective evidence")
plus check 36 ("independent reviewer ... clean environment") cannot be satisfied
by the builder of the work.
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

from .core import digest

PROD = Path(__file__).resolve().parent
PKG = PROD.parent
ROOT = PKG.parent
SCHEMA = "PK_DYN_CHECKSTATUS/1"
LV, PA, BL = "LOCALLY_VERIFIED", "PARTIAL", "BLOCKED"

# Generic checks: (state, evidence, blocker)
OWNER = "named accountable owner + implementation/security/operations reviewers (ownership.json: all UNASSIGNED)"
GENERIC = {
    1: (BL, "production/ownership.json", OWNER),
    2: (PA, "components/NN.json spec fields + production/docs", "normative spec drafted by the builder; owner review/approval absent"),
    3: (PA, "production/threat_model.py, docs/09_topology.md, docs/10_persistence.md", "dependency/trust-boundary analysis not reviewed by an owner"),
    4: (PA, "production/bench.py PROPOSED budgets, docs/55_runbooks.md", "SLO/freshness targets PROPOSED; approver UNASSIGNED"),
    20: (PA, "production/threat_model.py, production/vuln_policy.py", "security-control coverage exists as a model; no vulnerability scan feed or security reviewer"),
    21: (PA, "production/controls.py, production/authz.py (audited decisions)", "operator identities need an authenticated IdP; roles UNASSIGNED"),
    22: (PA, "production/evidence.py, production/backup.py, production/audit.py (HMAC)", "integrity is HMAC under a NONPRODUCTION trust root; no asymmetric/KMS signer"),
    23: (LV, "production/waivers.py::validate (P0 checks 05-19 unwaivable), exitgate", None),
    24: (PA, "production/rollout.py, backup.py, leader.py, faults.py (simulated)", "exercised against doubles only; no representative environment"),
    25: (PA, "production/rollout.py, soak.py", "pass/fail thresholds PROPOSED, approver UNASSIGNED"),
    26: (PA, "production/controller.py drift detection, backup.py restore validation", "latent-drift detection runs against doubles only"),
    27: (LV, "production/status.py run record (run id, interpreter, platform, per-test outcome)", None),
    28: (BL, "production/dashboards.py (definitions only)", "no metrics backend/dashboard host to publish to"),
    29: (PA, "production/audit.py hash-chained summaries", "no WORM/immutable retention target"),
    30: (PA, "production/ci/run_all.py", "runs locally; no CI service or scheduler bound"),
    31: (PA, "overlay test suites (positive/negative/failure paths)", "mixed-version and degraded cases only where the component has them; no live env"),
    32: (BL, "status ledger", "reproducible evidence exists locally but has not been reproduced by an independent party"),
    33: (None, "production/rtm.py", None),        # decided per component from the RTM
    34: (BL, "production/docs/RUNBOOK.md", "procedure not verified in a representative non-production environment"),
    35: (PA, "completion artifact in CHECK_STATUS.json", "approver identity UNASSIGNED"),
    36: (BL, "-", "independent reviewer reproduction from a clean environment"),
}


def load_components() -> dict[int, dict]:
    out = {}
    for f in sorted((PROD / "components").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out[int(d["component"])] = d
    return out


def checklist_titles(path: Path) -> dict[int, dict]:
    t = path.read_text(encoding="utf-8")
    out = {}
    for blk in re.split(r"\n## (?=\d\d\. )", t)[1:]:
        m = re.match(r"(\d\d)\. (P\d) — (.+)", blk.split("\n")[0])
        checks = dict((int(n), txt) for n, txt in re.findall(r"- \[ \] \*\*(\d\d)\.\*\* (.+)", blk))
        lc = re.search(r"\*\*Linked controls:\*\* (.+)", blk).group(1).strip()
        out[int(m.group(1))] = {"priority": m.group(2), "title": m.group(3).strip(), "checks": checks, "linked": lc}
    return out


def run_tests(test_ids: set[str]) -> dict[str, bool]:
    """Execute every listed test id once; return id -> passed."""
    results: dict[str, bool] = {}
    loader = unittest.TestLoader()
    for tid in sorted(test_ids):
        try:
            suite = loader.loadTestsFromName(tid)
        except Exception:
            results[tid] = False
            continue
        r = unittest.TestResult()
        suite.run(r)
        results[tid] = r.wasSuccessful() and r.testsRun > 0 and not r.skipped
    return results


def _spec_exists(spec: str | None) -> bool:
    if not spec:
        return False
    path = spec.split("::")[0].split(" ")[0]
    for base in (ROOT / PKG.name, PKG.parent, PROD.parent):
        if (base / path).exists():
            return True
    return (ROOT / path).exists()


def derive(components: dict[int, dict], titles: dict[int, dict], passed: dict[str, bool],
           rtm_bad: set[int]) -> list[dict]:
    rows = []
    for c in range(1, 67):
        meta = titles[c]
        comp = components.get(c)
        subs = comp["subparts"] if comp else []
        for n in range(1, 37):
            row = {"component": c, "priority": meta["priority"], "check": n,
                   "text": meta["checks"].get(n, ""), "state": BL, "evidence": [], "blocker": None}
            if 5 <= n <= 19:
                k, kind = divmod(n - 5, 3)
                if k >= len(subs):
                    row["blocker"] = "no component manifest"
                else:
                    s = subs[k]
                    tests = s.get("tests") or []
                    tests_ok = bool(tests) and all(passed.get(t) for t in tests)
                    if kind == 0:
                        ok = _spec_exists(s.get("spec"))
                        row.update(state=LV if ok else BL, evidence=[s.get("spec")],
                                   blocker=None if ok else "spec not found")
                    elif kind == 1:
                        st = {"IMPLEMENTED": LV, "PARTIAL": PA}.get(s["state"], BL)
                        row.update(state=st, evidence=s.get("modules", []), blocker=s.get("blocker"))
                    else:
                        if s["state"] == "IMPLEMENTED" and tests_ok:
                            st = LV
                        elif tests_ok:
                            st = PA
                        else:
                            st = BL
                        row.update(state=st, evidence=tests,
                                   blocker=None if st == LV else (s.get("blocker") or "tests missing or failing"))
            else:
                st, ev, bl = GENERIC[n]
                if n == 33:
                    st = BL if c in rtm_bad else LV
                    bl = "component has RTM errors" if c in rtm_bad else None
                row.update(state=st, evidence=[ev], blocker=bl)
            rows.append(row)
    return rows


def completion_artifact(c: int, rows: list[dict], titles: dict[int, dict], run: dict) -> dict:
    mine = [r for r in rows if r["component"] == c]
    counts = {s: sum(1 for r in mine if r["state"] == s) for s in (LV, PA, BL)}
    return {"component_id": f"{c:02d}", "priority": titles[c]["priority"], "linked_controls": titles[c]["linked"],
            "counts": counts, "evidence_digest": digest(mine), "test_result": run["suite_ok"],
            "approver": "UNASSIGNED", "timestamp": run["timestamp"],
            "acceptance": "BLOCKED" if counts[PA] or counts[BL] else "READY_FOR_INDEPENDENT_REVIEW"}


def build(checklist_md: Path, *, timestamp: str) -> dict:
    import platform
    from . import rtm
    comps = load_components()
    titles = checklist_titles(checklist_md)
    ids = {t for d in comps.values() for s in d["subparts"] for t in (s.get("tests") or [])}
    passed = run_tests(ids)
    rep = rtm.build(rtm.load_json(PROD / "requirements.json"), PROD / "components",
                    rtm.load_json(PKG / "CHECKLIST.json"))
    rtm_bad = set()
    for e in list(rep.get("component_errors", [])) + list(rep.get("implemented_but_unverified", [])):
        m = re.search(r"(\d+)", str(e))
        if m:
            rtm_bad.add(int(m.group(1)))
    present = {r["component"] for r in rep.get("component_rows", [])}
    rtm_bad |= set(range(1, 67)) - present
    rows = derive(comps, titles, passed, rtm_bad)
    run = {"timestamp": timestamp, "python": platform.python_version(), "platform": sys.platform,
           "tests_listed": len(ids), "tests_passed": sum(passed.values()),
           "suite_ok": all(passed.values())}
    totals = {s: sum(1 for r in rows if r["state"] == s) for s in (LV, PA, BL)}
    return {"schema": SCHEMA, "run": run, "totals": totals, "checks": rows,
            "completion": [completion_artifact(c, rows, titles, run) for c in range(1, 67)],
            "failed_tests": sorted(t for t, ok in passed.items() if not ok)}


def main(argv: list[str] | None = None) -> int:
    import argparse, datetime
    ap = argparse.ArgumentParser()
    ap.add_argument("--checklist", default=str(PROD / "docs" / "COMPONENT_CHECKLISTS.md"))
    ap.add_argument("--out", default=str(PROD / "CHECK_STATUS.json"))
    ap.add_argument("--timestamp", default=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    a = ap.parse_args(argv)
    doc = build(Path(a.checklist), timestamp=a.timestamp)
    Path(a.out).write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"totals": doc["totals"], "run": doc["run"], "failed_tests": doc["failed_tests"]}))
    return 0 if not doc["failed_tests"] and len(doc["checks"]) == 2376 else 1


if __name__ == "__main__":
    raise SystemExit(main())
