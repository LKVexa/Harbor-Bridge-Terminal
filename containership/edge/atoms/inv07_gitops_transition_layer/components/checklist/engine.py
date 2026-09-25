"""INV-07 checklist engine: 54 components x 40 checks = 2,160 records.
Adapted from the shop's GAP-09 v5.1.0 engine (same status vocabulary and
falsifier rules), re-keyed to this checklist's check families.

Status vocabulary: NOT_STARTED / IN_PROGRESS / BLOCKED / VERIFYING / PASS / WAIVED.
The engine can emit **VERIFYING at most**.  PASS needs a named owner and an
independent human reviewer (G02); WAIVED needs an owner-accepted waiver.
Neither exists, and ``validate`` refuses any record that claims otherwise --
including records edited by hand after the run.

VERIFYING means: the component has bound code, every bound test class ran
and passed in *this* run (a skip is NOT_RUN, never a pass), the check's family
is backed by a flag a reviewer can falsify, nothing in the check names an
activity this pass did not perform, and the check shares at least 3 subject
stems with the bound modules/tests (a lower bound that can only refuse).
Every record carries the ``rule`` that produced it.
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
sys.path.insert(0, os.path.join(COMP, "tools"))
sys.dont_write_bytecode = True

from inv07_gitops_transition_layer.components.checklist.bindings import B_OWNER, C  # noqa: E402
import master  # noqa: E402

STATUSES = ("NOT_STARTED", "IN_PROGRESS", "BLOCKED", "VERIFYING", "PASS", "WAIVED")
FORBIDDEN_REVIEWERS = re.compile(r"(?i)claude|assistant|model|engine|tool|bot|\bci\b|automation|inv07|builder")
MIN_COVER = 3
NOT_DONE = re.compile(r"(?i)(game[- ]day|sign-?off|\bCI\b|publish|upgrade/downgrade|mixed-version|\bsoak\b|"
                      r"penetration|approv(?:ed|al) (?:by|from)|periodic review|mutation|exercised)")
# check family -> required flag (None = handled explicitly)
FAMILY_FLAG = {"A03": "r", "A05": "s", "I01": "i", "C01": "c", "C02": "c", "S01": "t", "S02": "l", "S04": "f",
               "R01": "b", "R02": "k", "R03": "q", "P01": "p", "P02": "m", "O01": "o", "O02": "o", "T03": "x",
               "T04": "a", "D01": "d", "DOD04": "f", "DOD06": "o"}
FAMILY_REASON = {"r": "no ADR-001 row for this component", "s": "no explicit lifecycle state machine",
                 "i": "no independently versioned wire/durable schema for this component",
                 "c": "component settings not in PK_GITOPS_CONFIG/1", "t": "no THREAT_MODEL.md row",
                 "l": "no least-privilege profile for this component", "f": "fail-closed path not tested",
                 "b": "bounded dependency-failure behaviour not implemented/tested",
                 "k": "crash-consistency not implemented/tested", "q": "no safe rollback/disable/quarantine path",
                 "p": "no explicit resource limits", "m": "not measured by tools/bench.py",
                 "o": "not wired to metrics/events/traces/audit", "x": "no concurrency/restart test",
                 "a": "no adversarial/resource-exhaustion test", "d": "no component-specific operator docs"}
ALWAYS_OPEN = {  # families no evidence in this archive can satisfy
    "A02": ("BLOCKED", "R-OWNER", "no accountable engineering owner / security reviewer / operations owner", [B_OWNER]),
    "G02": ("BLOCKED", "R-OWNER", "named engineering, security and operations review required", [B_OWNER]),
    "A04": ("IN_PROGRESS", "R-REQGEN", "SHALL statements are generated from the closure objective; no per-component "
                                       "latency/availability/capacity/durability/isolation requirements", []),
    "T05": ("IN_PROGRESS", "R-NOCOMPAT", "no N-1 release exists; upgrade/downgrade compatibility untested", []),
    "E01": ("IN_PROGRESS", "R-NOREV", "evidence bound to file digests (MANIFEST.sha256), not to a VCS source commit "
                                      "or a signed release artifact", []),
    "G01": ("IN_PROGRESS", "R-NOCI", "gates exist (tools/gates.py, engine) but no release pipeline enforces them", []),
    "DOD03": ("IN_PROGRESS", "R-NOCOMPAT", "versioned and validated, but compatibility across versions untested", []),
    "DOD05": ("IN_PROGRESS", "R-NOUPGRADE", "upgrade/rollback-of-release path not executed", []),
    "DOD08": ("IN_PROGRESS", "R-NOREV", "no immutable release artifact to bind evidence to", []),
}


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


def run_tests(exclude=()) -> dict:
    loader, suite = unittest.TestLoader(), unittest.TestSuite()
    tdir = os.path.join(COMP, "tests")
    for fn in sorted(os.listdir(tdir)):
        if fn.startswith("test_") and fn.endswith(".py") and fn[:-3] not in exclude:
            suite.addTests(loader.loadTestsFromName(fn[:-3]))
    stream = io.StringIO()
    t0 = time.time()
    res = unittest.TextTestRunner(stream=stream, resultclass=_Result, verbosity=0).run(suite)
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


STOP = set("""about above across after against along also among apply before being between both bound build
carry cases check checks clear component components covering create current define defined defines describe
detail document documented during each either every exact exist explicit field fields first following from have
include including instead into items least make needed never other otherwise over required requirement should
since specific specify state states such than that their them then there these they this those through under
until using where whether which while with within without would write where appropriate applicable""".split())


def _stems(text: str) -> set:
    return {w[:6] for w in re.findall(r"[a-z][a-z0-9]{4,}", text.lower()) if w not in STOP}


_SRC: dict = {}


def _source_stems(b: dict) -> set:
    if b["id"] not in _SRC:
        text = []
        for m in b["modules"]:
            p = os.path.join(COMP, m)
            if os.path.exists(p):
                with open(p, encoding="utf-8", errors="replace") as fh:
                    text.append(fh.read())
        for t in b["tests"]:
            p = os.path.join(COMP, "tests", t.split(".")[0] + ".py")
            if os.path.exists(p):
                with open(p, encoding="utf-8", errors="replace") as fh:
                    text.append(fh.read())
        _SRC[b["id"]] = _stems("\n".join(text))
    return _SRC[b["id"]]


def coverage(check_text: str, b: dict) -> tuple[int, list]:
    want = _stems(check_text) - _stems(b["title"])
    hit = sorted(want & _source_stems(b))
    return len(hit), hit


def family(check_id: str) -> str:
    return check_id.split(".", 1)[1]


def fam_key(f: str) -> str:
    return f if f.startswith("DOD") else re.sub(r"\d+$", lambda m: m.group(0), f)


def classify(cid: str, check: dict, b: dict, tstat: dict, evidence_ids: list) -> dict:
    fam = family(check["id"])
    text = check["text"]
    low = text.lower()
    base = {"id": check["id"], "family": fam, "owner": "UNASSIGNED", "reviewer": None, "evidence": evidence_ids}

    def out(status, rule, reason, deps=()):
        return {**base, "status": status, "rule": rule, "reason": reason, "dependencies": list(deps)}

    if fam in ALWAYS_OPEN:
        st, rule, why, deps = ALWAYS_OPEN[fam]
        return out(st, rule, why, deps)
    if not b["tests"]:
        return out("BLOCKED" if b["blockers"] else "NOT_STARTED", "R-NOIMPL", "no implementation bound", b["blockers"])
    bad = [k for k, s in tstat.items() if s[0] in ("fail", "error", "missing")]
    if bad:
        return out("IN_PROGRESS", "R-TESTFAIL", "bound tests failing or missing: " + ", ".join(bad))
    lanes = [k for k, s in tstat.items() if s[0] == "not_run"]
    if lanes:
        return out("IN_PROGRESS", "R-LANE", "bound test class NOT_RUN (a skip is not a pass): " +
                   "; ".join(str(tstat[k][2][0]) for k in lanes))
    if fam in ("X02", "T02", "DOD02"):
        if "L" not in b["flags"]:
            return out("BLOCKED", "R-PRODLIKE", "no production-like dependency for this component is reachable here",
                       b["blockers"] or [B_OWNER])
        if fam != "T02":
            return out("IN_PROGRESS", "R-NODEMO", "exercised locally by tests against real git/filesystem/TLS, but no "
                       "retained, immutable demonstration record of exact configuration, inputs, outputs and versions")
    for kw in b["block_kw"]:
        if kw in low and b["blockers"]:
            return out("BLOCKED", "R-BLOCK-KW", f"'{kw}' can only be satisfied through the blocker", b["blockers"])
    if fam == "DOD01" and "e" not in b["flags"]:
        return out("BLOCKED", "R-ADAPTER", "only an adapter/stub exists locally; production binding missing",
                   b["blockers"])
    if fam == "DOD07" and b["blockers"]:
        return out("BLOCKED", "R-DEPS", "required tests with the external dependency present cannot run", b["blockers"])
    for kw in b["lacks"]:
        if kw in low or fam in ("X01", "DOD02"):
            return out("IN_PROGRESS", "R-LACK", f"aspect '{kw}' is not implemented in this pass")
    need = FAMILY_FLAG.get(fam)
    if need and need not in b["flags"]:
        return out("IN_PROGRESS", "R-FAMILY", FAMILY_REASON[need])
    m = NOT_DONE.search(text)
    if m:
        return out("IN_PROGRESS", "R-NOTDONE", f"requires an activity not performed in this pass ('{m.group(0)}')")
    n_hit, hit = coverage(text, b)
    if n_hit < MIN_COVER:
        return out("IN_PROGRESS", "R-NOCOVER", f"bound artifacts share only {n_hit} subject stems with the check "
                   f"({', '.join(hit) or 'none'}); coverage not shown")
    if fam == "P02":
        return out("VERIFYING", "R-PERF", "measured in evidence/perf_baseline.json; targets PROPOSED (W-004)")
    if fam in ("A01", "A04", "D01"):
        return out("VERIFYING", "R-SPEC", "normative text in module docstrings + docs/ (REQUIREMENTS.md, ADR-001); "
                   "tests pass; not reviewed -- a reviewer may judge the prose insufficient")
    return out("VERIFYING", "R-IMPL", f"bound implementation + passing tests cover stems {', '.join(hit[:8])}; "
               "awaiting independent review")


def _sha(path: str) -> str | None:
    p = os.path.join(COMP, path)
    if not os.path.exists(p):
        return None
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def build(out_dir: str | None = None, *, tests: dict | None = None) -> dict:
    out_dir = out_dir or os.path.join(COMP, "evidence")
    parsed = master.parse()
    tests = tests or run_tests()
    records, evidence, problems = [], [], []
    if set(parsed["components"]) != set(C):
        problems.append("binding/checklist component sets differ")
    for cid, comp in sorted(parsed["components"].items()):
        b = C[cid]
        if b["title"].lower() != comp["title"].lower():
            problems.append(f"binding title mismatch for {cid}: {b['title']!r} vs {comp['title']!r}")
        if len(comp["checks"]) != 40:
            problems.append(f"component {cid} has {len(comp['checks'])} checks (expected 40)")
        tstat = {cls: class_status(tests["outcomes"], cls) for cls in b["tests"]}
        eids = []
        for i, m in enumerate(b["modules"], 1):
            eid = f"INV07-C{cid}-E{i:02d}"
            evidence.append({"id": eid, "component": cid, "kind": "artifact", "path": f"components/{m}", "sha256": _sha(m)})
            eids.append(eid)
        for j, (cls, st) in enumerate(sorted(tstat.items()), len(b["modules"]) + 1):
            eid = f"INV07-C{cid}-E{j:02d}"
            evidence.append({"id": eid, "component": cid, "kind": "test", "test": cls, "result": st[0], "tests": st[1],
                             "detail": st[2]})
            eids.append(eid)
        for ch in comp["checks"]:
            records.append({"component": cid, "title": comp["title"], "priority": comp["priority"],
                            **classify(cid, ch, b, tstat, eids)})
    summary = {s: sum(1 for r in records if r["status"] == s) for s in STATUSES}
    per_comp: dict = {}
    for r in records:
        per_comp.setdefault(r["component"], {}).setdefault(r["status"], 0)
        per_comp[r["component"]][r["status"]] += 1
    rules: dict = {}
    for r in records:
        rules[r["rule"]] = rules.get(r["rule"], 0) + 1
    doc = {"schema": "INV07-CHECKLIST-STATUS/1", "checklist_sha256": parsed["sha256"], "checks": len(records),
           "summary": summary, "rules": rules, "production_certification": "NOT CERTIFIED", "problems": problems,
           "test_run": {"ran": tests["ran"], "seconds": tests["seconds"],
                        "passed": sum(1 for o, _ in tests["outcomes"].values() if o == "pass"),
                        "not_run": sorted(k for k, (o, _) in tests["outcomes"].items() if o == "not_run"),
                        "failed": sorted(k for k, (o, _) in tests["outcomes"].items() if o in ("fail", "error"))},
           "per_component": per_comp, "records": records}
    errs = validate(doc, evidence)
    if errs:
        raise SystemExit("engine produced invalid records: " + "; ".join(errs[:5]))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "CHECKLIST_STATUS.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
    with open(os.path.join(out_dir, "EVIDENCE_INDEX.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"schema": "INV07-EVIDENCE/1", "items": evidence}, fh, indent=1, sort_keys=True)
    _gate_ledger(os.path.join(out_dir, "GATE_LEDGER.jsonl"), doc)
    _traceability(os.path.join(out_dir, "TRACEABILITY.md"), doc, parsed)
    if os.path.abspath(out_dir) == os.path.abspath(os.path.join(COMP, "evidence")):
        _status_md(os.path.join(COMP, "STATUS.md"), doc)
    return doc


def _status_md(path: str, doc: dict) -> None:
    s, tr = doc["summary"], doc["test_run"]
    lines = ["# INV-07 v5.0.0 production overlay -- status", "",
             "**Candidate:** `inv07_gitops_transition_layer` v4.2.0 (reference model, contract, adapter, tests and "
             "CHECKLIST.json left byte-identical -- `tests/test_overlay_integrity.py`).",
             "**Workflow applied:** *INV-07 GitOps Transition Layer -- 54-Component Professional Engineering Checklist "
             "v1.0.0* -- 54 components x 40 checks = **2,160** (the checklist header says 30+8 per component; every "
             "component actually has 32 engineering controls + 8 DoD).",
             "**Production certification: NOT CERTIFIED.** The engine never emits PASS: every PASS needs a named owner "
             "and an independent human reviewer, and none is assigned (`docs/OWNERS.md`).", "",
             "## How to verify", "", "```text", "python -B inv07_gitops_transition_layer/components/run_all.py", "```",
             "Exit 0 = all stages pass and every check verified; **3 = INCOMPLETE** (all stages pass, checklist items "
             "open -- the expected result); 1 = a stage failed.", "",
             "## Result", "", "| Measure | Value |", "|---|---|",
             f"| Overlay tests | {tr['passed']} pass / {tr['ran']} ran, {len(tr['not_run'])} not run, "
             f"{len(tr['failed'])} failed ({tr['seconds']} s) |",
             f"| Checks | **{s['VERIFYING']} VERIFYING · {s['IN_PROGRESS']} IN_PROGRESS · {s['BLOCKED']} BLOCKED · "
             f"{s['PASS']} PASS · {s['WAIVED']} WAIVED · {s['NOT_STARTED']} NOT_STARTED** |",
             "| Decision rules used | " + ", ".join(f"{k} {v}" for k, v in sorted(doc["rules"].items())) + " |", "",
             "VERIFYING = bound code + every bound test class passed in this run + the check family is backed by a "
             "falsifiable flag + nothing names an activity not performed + >= 3 shared subject stems (a lower bound "
             "that can only refuse). It is still a machine claim awaiting review.", "",
             "## Per component", "", "| # | Component | Pri | VERIFYING | IN_PROGRESS | BLOCKED | Blocking dependency |",
             "|---|---|---|---|---|---|---|"]
    pri = {r["component"]: r["priority"] for r in doc["records"]}
    for cid in sorted(C):
        pc = doc["per_component"].get(cid, {})
        lines.append(f"| {cid} | {C[cid]['title']} | {pri.get(cid, '')} | {pc.get('VERIFYING', 0)} | "
                     f"{pc.get('IN_PROGRESS', 0)} | {pc.get('BLOCKED', 0)} | "
                     f"{'; '.join(x.split(' -- ')[0] for x in C[cid]['blockers']) or '—'} |")
    lines += ["", "Every decision with its rule and reason: `evidence/CHECKLIST_STATUS.json`; hash chain "
              "`evidence/GATE_LEDGER.jsonl` (+ `.head`); matrix `evidence/TRACEABILITY.md`.", ""]
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))


def _gate_ledger(path: str, doc: dict) -> None:
    prev = "0" * 64
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for i, r in enumerate(doc["records"]):
            e = {"seq": i, "check": r["id"], "status": r["status"], "rule": r["rule"], "evidence": r["evidence"],
                 "prev": prev}
            prev = hashlib.sha256(json.dumps(e, sort_keys=True).encode()).hexdigest()
            e["hash"] = prev
            fh.write(json.dumps(e, sort_keys=True) + "\n")
    with open(path + ".head", "w", encoding="ascii", newline="\n") as fh:
        fh.write(f"{len(doc['records'])} {prev}\n")


def _traceability(path: str, doc: dict, parsed: dict) -> None:
    lines = ["# INV-07 requirement -> design -> implementation -> test -> evidence traceability", "",
             "_Generated by `checklist/engine.py`; statuses are machine decisions awaiting independent review._", "",
             "| Comp | Requirement | Modules | Tests | VERIFYING | IN_PROGRESS | BLOCKED | Blocking dependency |",
             "|---|---|---|---|---|---|---|---|"]
    for cid in sorted(C):
        b, pc = C[cid], doc["per_component"].get(cid, {})
        lines.append(f"| {cid} | INV07-C{cid}-R01 {b['title']} | {', '.join(b['modules'])} | "
                     f"{', '.join(b['tests'])} | {pc.get('VERIFYING', 0)} | {pc.get('IN_PROGRESS', 0)} | "
                     f"{pc.get('BLOCKED', 0)} | {'; '.join(x.split(' -- ')[0] for x in b['blockers']) or '—'} |")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


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
        if r["family"] in ("A02", "G02") and s != "BLOCKED":
            errs.append(f"{r['id']}: owner/review check not BLOCKED")
    return errs


if __name__ == "__main__":
    d = build()
    print(json.dumps({k: d[k] for k in ("checks", "summary", "production_certification", "problems")}, indent=1))
    print("tests:", {k: (v if not isinstance(v, list) else len(v)) for k, v in d["test_run"].items()})
    print("rules:", d["rules"])
