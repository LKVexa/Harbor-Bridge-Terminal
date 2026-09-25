"""GAP-09 checklist engine: 60 components x 24 checks = 1,440 records.

Status vocabulary is the checklist's own: NOT_STARTED / IN_PROGRESS / BLOCKED
/ VERIFYING / PASS / WAIVED.  This engine can emit **VERIFYING at most**:
PASS needs a named owner and an independent reviewer (xx.23), and WAIVED
needs an owner-accepted waiver.  Neither exists, and ``validate`` refuses any
record that claims otherwise -- including records edited by hand after the run.

Every decision carries the ``rule`` that produced it, so the classification of
all 1,440 checks is auditable rather than asserted.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
COMP = os.path.dirname(HERE)
PKG = os.path.dirname(COMP)
sys.path.insert(0, os.path.dirname(PKG))
sys.path.insert(0, os.path.join(COMP, "tests"))

from gap09_unified_observability.components.checklist.bindings import C, B_OWNER, B_KMS  # noqa: E402

STATUSES = ("NOT_STARTED", "IN_PROGRESS", "BLOCKED", "VERIFYING", "PASS", "WAIVED")
FORBIDDEN_REVIEWERS = re.compile(r"(?i)claude|assistant|model|engine|tool|bot|ci|automation|gap09")
PERF_COVERED = {"02", "03", "10", "11", "12", "13", "14", "21"}   # hot paths measured by tools/bench.py
EXTERNAL = re.compile(r"(?i)\b(real adjacent|against the real|integration tests? against|production (?:trust|environment)|"
                      r"hardware|fleet|representative platform|named implementation owner|independent reviewer|"
                      r"sibling|pk_core)\b")
PERF = re.compile(r"(?i)\b(benchmark|p50|p95|p99|latency|throughput|cpu/memory|resource budget)\b")
RUNBOOK = re.compile(r"(?i)\brunbook\b")
DIAGRAM = re.compile(r"(?i)\bdiagram\b")
DIAGRAM_COVERED = {f"{i:02d}" for i in range(1, 16)} | {"19", "40"}          # docs/TRUST_BOUNDARY.md
SPEC = re.compile(r"(?i)^(write|document|define|specify|describe)\b")
LACK_BLOCKER = {"encrypt": B_KMS, "kms": B_KMS, "key separation": B_KMS}


def parse_checklist(path: str) -> dict:
    text = open(path, encoding="utf-8").read()
    comps = {}
    for m in re.finditer(r"^### (\d\d)\. (.+?)\n\n\*\*Requirement:\*\* (.+?)\n", text, re.M):
        comps[m.group(1)] = {"title": m.group(2).strip(), "requirement": m.group(3).strip(), "checks": []}
    for m in re.finditer(r"^- \[ \] \*\*(\d\d)\.(\d\d)\*\* (.+)$", text, re.M):
        comps[m.group(1)]["checks"].append({"id": f"{m.group(1)}.{m.group(2)}", "text": m.group(3).strip()})
    return {"sha256": hashlib.sha256(text.encode()).hexdigest(), "components": comps}


def _sha(path: str) -> str | None:
    p = os.path.join(COMP, path)
    if not os.path.exists(p):
        return None
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class _Result(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.outcomes = {}

    def _set(self, test, outcome, detail=""):
        self.outcomes[test.id()] = (outcome, detail)

    def addSuccess(self, test):
        super().addSuccess(test); self._set(test, "pass")

    def addFailure(self, test, err):
        super().addFailure(test, err); self._set(test, "fail", self._exc_info_to_string(err, test)[-400:])

    def addError(self, test, err):
        super().addError(test, err); self._set(test, "error", self._exc_info_to_string(err, test)[-400:])

    def addSkip(self, test, reason):
        super().addSkip(test, reason); self._set(test, "not_run", reason)


def run_tests(exclude=("test_checklist_engine",)) -> dict:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    tdir = os.path.join(COMP, "tests")
    for fn in sorted(os.listdir(tdir)):
        if fn.startswith("test_") and fn.endswith(".py") and fn[:-3] not in exclude:
            suite.addTests(loader.loadTestsFromName(fn[:-3]))
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, resultclass=_Result, verbosity=0)
    t0 = time.time()
    res = runner.run(suite)
    return {"outcomes": res.outcomes, "seconds": round(time.time() - t0, 2), "ran": res.testsRun}


def class_status(outcomes: dict, cls: str) -> tuple[str, int, list]:
    hits = {k: v for k, v in outcomes.items() if k.startswith(cls + ".")}
    if not hits:
        return "missing", 0, []
    bad = [k for k, (o, _) in hits.items() if o in ("fail", "error")]
    if bad:
        return "fail", len(hits), bad
    skipped = [v[1] for v in hits.values() if v[0] == "not_run"]
    if skipped:
        return "not_run", len(hits), skipped[:1]
    return "pass", len(hits), []


STOP = set("""about above across after against align along also among another appropriate apply before being between
both bound build carry cases check checks clear component components covering create current define defined defines
describe detail document documented during each either every exact exist explicit field fields first following
from have include including instead into items least make needed never other otherwise over required requirement
should since specific specify state states such than that their them then there these they this those through under
until using where whether which while with within without would write""".split())


def _stems(text: str) -> set:
    words = re.findall(r"[a-z][a-z0-9]{4,}", text.lower())
    return {w[:6] for w in words if w not in STOP}


_SRC_CACHE: dict = {}


def _source_stems(b: dict) -> set:
    key = b["id"]
    if key not in _SRC_CACHE:
        text = []
        for m in b["modules"]:
            p = os.path.join(COMP, m)
            if os.path.exists(p):
                text.append(open(p, encoding="utf-8", errors="replace").read())
        for t in b["tests"]:
            p = os.path.join(COMP, "tests", t.split(".")[0] + ".py")
            if os.path.exists(p):
                text.append(open(p, encoding="utf-8", errors="replace").read())
        _SRC_CACHE[key] = _stems("\n".join(text))
    return _SRC_CACHE[key]


def coverage(check_text: str, b: dict) -> tuple[int, list]:
    """Relevance lower bound: how many of the check's content-word stems
    (minus the component title's own words) appear in the bound modules and
    tests.  It under-reports on purpose -- it can refuse a VERIFYING, it can
    never manufacture one."""
    want = _stems(re.sub(r"\*\*[^*]+\*\*", " ", check_text)) - _stems(b["title"])
    hit = sorted(want & _source_stems(b))
    return len(hit), hit


MIN_COVER = 3
# Activities no code in this archive performed, whatever words it shares with the check.
NOT_DONE = re.compile(r"(?i)(game[- ]day|sign-?off|signed (?:release|manifest|provenance)|optimi[sz]ed|mutation|"
                      r"\bCI\b|publish|previous supported release|mixed-version|upgrade|downgrade|\bsoak\b|"
                      r"\bSLO\b|\bSLA\b|\balert|pager|on-call|penetration|approv|periodic review|cadence|"
                      r"post-incident|flake policy|line coverage)")


def classify(cid: str, check: dict, b: dict, tstat: dict, evidence_ids: list, perf_ok: bool) -> dict:
    n = int(check["id"][3:])
    text = check["text"]
    base = {"id": check["id"], "owner": "UNASSIGNED", "reviewer": None, "evidence": evidence_ids}

    def out(status, rule, reason, deps=()):
        return {**base, "status": status, "rule": rule, "reason": reason, "dependencies": list(deps)}

    if n == 23:
        return out("BLOCKED", "R-OWNER", "no named owner or independent reviewer exists", [B_OWNER])
    if n == 24:
        return out("BLOCKED", "R-CLOSE", "closure needs checks 01-23 PASS; engine cannot emit PASS", [B_OWNER])
    if not b["tests"]:
        if b["blockers"]:
            return out("BLOCKED", "R-NOIMPL-DEP", "nothing implementable without the dependency", b["blockers"])
        return out("NOT_STARTED", "R-NOIMPL", "no implementation bound")
    if EXTERNAL.search(text) and b["blockers"]:
        return out("BLOCKED", "R-EXTERNAL", "check requires a dependency absent from the archive", b["blockers"])
    low = text.lower()
    for kw in b.get("block_kw", ()):
        if kw in low and b["blockers"]:
            return out("BLOCKED", "R-BLOCK-KW", f"'{kw}' can only be satisfied through the blocker", b["blockers"])
    for kw in b["lacks"]:
        if kw.lower() in low:
            dep = LACK_BLOCKER.get(kw.lower())
            if dep:
                return out("BLOCKED", "R-LACK-DEP", f"aspect '{kw}' needs a missing dependency", [dep])
            return out("IN_PROGRESS", "R-LACK", f"aspect '{kw}' is not implemented in the overlay")
    bad = [c for c, s in tstat.items() if s[0] in ("fail", "error", "missing")]
    if bad:
        return out("IN_PROGRESS", "R-TESTFAIL", "bound tests failing or missing: " + ", ".join(bad))
    lanes = [c for c, s in tstat.items() if s[0] == "not_run"]
    if lanes:
        return out("IN_PROGRESS", "R-LANE", "declared lane NOT_RUN: " + "; ".join(str(tstat[c][2][0]) for c in lanes))
    if PERF.search(text):
        if cid in PERF_COVERED and perf_ok:
            return out("VERIFYING", "R-PERF", "hot path measured in evidence/perf_baseline.json; thresholds unapproved (W-004)")
        return out("IN_PROGRESS", "R-NOPERF", "no benchmark covers this component")
    if RUNBOOK.search(text):
        if b.get("runbook"):
            return out("VERIFYING", "R-RUNBOOK", "runbook entry in docs/RUNBOOKS.md; not exercised by an operator")
        return out("IN_PROGRESS", "R-NORUNBOOK", "no component-specific runbook entry")
    if DIAGRAM.search(text) and cid not in DIAGRAM_COVERED:
        return out("IN_PROGRESS", "R-NODIAGRAM", "no diagram for this component (docs/TRUST_BOUNDARY.md covers 01-15, 19, 40)")
    m = NOT_DONE.search(text)
    if m:
        return out("IN_PROGRESS", "R-NOTDONE", f"requires an activity not performed in this pass ('{m.group(0)}')")
    n_hit, hit = coverage(text, b)
    if n_hit < MIN_COVER:
        return out("IN_PROGRESS", "R-NOCOVER", f"bound artifacts share only {n_hit} subject stems with the check "
                   f"({', '.join(hit) or 'none'}); coverage not shown")
    if SPEC.search(text):
        return out("VERIFYING", "R-SPEC", "normative text is the bound module docstring(s) plus docs/; tests pass; "
                   "not reviewed -- a reviewer may judge the prose insufficient")
    if EXTERNAL.search(text):
        return out("IN_PROGRESS", "R-EXTERNAL-NODEP", "external evidence named by the check does not exist here")
    return out("VERIFYING", "R-IMPL", f"bound implementation + passing tests cover subject stems {', '.join(hit[:8])}; "
               "awaiting independent review")


def build(checklist_path: str, out_dir: str, *, tests: dict | None = None) -> dict:
    parsed = parse_checklist(checklist_path)
    tests = tests or run_tests()
    perf_ok = os.path.exists(os.path.join(COMP, "evidence", "perf_baseline.json"))
    records, evidence, problems = [], [], []
    for cid, comp in sorted(parsed["components"].items()):
        b = C[cid]
        if b["title"].lower() not in comp["title"].lower() and comp["title"].lower() not in b["title"].lower():
            problems.append(f"binding title mismatch for {cid}: {b['title']!r} vs {comp['title']!r}")
        tstat = {cls: class_status(tests["outcomes"], cls) for cls in b["tests"]}
        eids = []
        for i, m in enumerate(b["modules"], 1):
            eid = f"GAP09-C{cid}-E{i:02d}"
            evidence.append({"id": eid, "component": cid, "kind": "artifact", "path": f"components/{m}", "sha256": _sha(m)})
            eids.append(eid)
        for j, (cls, st) in enumerate(sorted(tstat.items()), len(b["modules"]) + 1):
            eid = f"GAP09-C{cid}-E{j:02d}"
            evidence.append({"id": eid, "component": cid, "kind": "test", "test": cls, "result": st[0], "tests": st[1],
                             "detail": st[2]})
            eids.append(eid)
        if len(comp["checks"]) != 24:
            problems.append(f"component {cid} has {len(comp['checks'])} checks")
        for ch in comp["checks"]:
            records.append({"component": cid, "title": comp["title"], **classify(cid, ch, b, tstat, eids, perf_ok)})
    summary = {s: sum(1 for r in records if r["status"] == s) for s in STATUSES}
    per_comp = {}
    for r in records:
        per_comp.setdefault(r["component"], {}).setdefault(r["status"], 0)
        per_comp[r["component"]][r["status"]] += 1
    doc = {"schema": "GAP09-CHECKLIST-STATUS/1", "checklist_sha256": parsed["sha256"], "checks": len(records),
           "summary": summary, "production_certification": "NOT CERTIFIED", "problems": problems,
           "test_run": {"ran": tests["ran"], "seconds": tests["seconds"],
                        "passed": sum(1 for o, _ in tests["outcomes"].values() if o == "pass"),
                        "not_run": sorted(k for k, (o, _) in tests["outcomes"].items() if o == "not_run"),
                        "failed": sorted(k for k, (o, _) in tests["outcomes"].items() if o in ("fail", "error"))},
           "per_component": per_comp, "records": records}
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "CHECKLIST_STATUS.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
    with open(os.path.join(out_dir, "EVIDENCE_INDEX.json"), "w", encoding="utf-8") as fh:
        json.dump({"schema": "GAP09-EVIDENCE/1", "items": evidence}, fh, indent=1, sort_keys=True)
    _gate_ledger(os.path.join(out_dir, "GATE_LEDGER.jsonl"), doc, evidence)
    errs = validate(doc, evidence)
    if errs:
        raise SystemExit("engine produced invalid records: " + "; ".join(errs[:5]))
    return doc


def _gate_ledger(path: str, doc: dict, evidence: list) -> None:
    prev = "0" * 64
    with open(path, "w", encoding="utf-8") as fh:
        for i, r in enumerate(doc["records"]):
            e = {"seq": i, "check": r["id"], "status": r["status"], "rule": r["rule"], "evidence": r["evidence"], "prev": prev}
            prev = hashlib.sha256(json.dumps(e, sort_keys=True).encode()).hexdigest()
            e["hash"] = prev
            fh.write(json.dumps(e, sort_keys=True) + "\n")
    with open(path + ".head", "w", encoding="ascii") as fh:
        fh.write(f"{len(doc['records'])} {prev}\n")


def validate(doc: dict, evidence: list) -> list[str]:
    """Refuse any record the evidence does not support (the falsifier target)."""
    errs = []
    ev = {e["id"]: e for e in evidence}
    for r in doc["records"]:
        s = r["status"]
        if s not in STATUSES:
            errs.append(f"{r['id']}: unknown status {s}")
        if s == "PASS":
            if r.get("owner") in (None, "", "UNASSIGNED"):
                errs.append(f"{r['id']}: PASS without a named owner")
            rv = r.get("reviewer")
            if not rv or rv == r.get("owner") or FORBIDDEN_REVIEWERS.search(str(rv)):
                errs.append(f"{r['id']}: PASS without an independent human reviewer")
        if s == "WAIVED":
            errs.append(f"{r['id']}: WAIVED without an owner-accepted waiver (all waivers are PROPOSED)")
        if s == "VERIFYING":
            tests = [ev[e] for e in r["evidence"] if e in ev and ev[e]["kind"] == "test"]
            if not tests or any(t["result"] != "pass" for t in tests):
                errs.append(f"{r['id']}: VERIFYING without passing test evidence")
            if any(ev[e]["kind"] == "artifact" and not ev[e]["sha256"] for e in r["evidence"] if e in ev):
                errs.append(f"{r['id']}: evidence artifact missing on disk")
        for e in r["evidence"]:
            if e not in ev:
                errs.append(f"{r['id']}: dangling evidence id {e}")
        if int(r["id"][3:]) in (23, 24) and s != "BLOCKED":
            errs.append(f"{r['id']}: owner/closure check not BLOCKED")
    return errs


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("checklist")
    ap.add_argument("--out", default=os.path.join(COMP, "evidence"))
    a = ap.parse_args()
    d = build(a.checklist, a.out)
    print(json.dumps({k: d[k] for k in ("checks", "summary", "production_certification", "problems")}, indent=1))
    print("tests:", {k: (v if not isinstance(v, list) else len(v)) for k, v in d["test_run"].items()})
