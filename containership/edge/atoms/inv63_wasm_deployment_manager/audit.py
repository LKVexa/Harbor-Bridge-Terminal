"""Executable INV-63 audit (INV-63-C020, C090; closeout items).

    python audit.py [--out-dir evidence] [--no-write-docs]

1. Runs the full unittest suite, recording per-test status and C-ID tags.
2. Joins results with tools/requirements_src.py (SHALL, implementation refs,
   docs, external-evidence keys) and governance/APPROVALS.json.
3. Computes each C001-C100 status from evidence only:
     MISSING   an implementation/doc ref is absent, or a tagged test failed
     PARTIAL   repository work complete, but external evidence is pending
     SATISFIED repo evidence complete AND every external key approved
4. Regenerates AUDIT_RESULTS.json, MISSING_COMPONENTS.md,
   docs/requirements/{REQUIREMENTS.json,REQUIREMENTS.md,TRACEABILITY.md}
   and evidence/{test_results.json,audit_bundle.json}, all bound to the
   package source digest.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(PKG_DIR.parent))
sys.path.insert(0, str(PKG_DIR / "tests"))
sys.path.insert(0, str(PKG_DIR / "tools"))
evidence = importlib.import_module(f"{PKG_DIR.name}.evidence")

MANDATORY_TESTS_REQUIRING_PK_CORE = "test_component"


class _Collector(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.records: dict[str, dict] = {}

    def _rec(self, test, status, detail=""):
        fn = getattr(test, test._testMethodName, None) if hasattr(test, "_testMethodName") else None
        tags = list(getattr(fn, "__inv63__", ()))
        self.records[test.id()] = {"status": status, "cids": tags, "detail": detail[:500]}

    def addSuccess(self, test):
        super().addSuccess(test); self._rec(test, "PASS")

    def addFailure(self, test, err):
        super().addFailure(test, err); self._rec(test, "FAIL", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err); self._rec(test, "FAIL", self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason); self._rec(test, "SKIPPED", reason)


def run_tests() -> dict:
    suite = unittest.defaultTestLoader.discover(str(PKG_DIR / "tests"), top_level_dir=str(PKG_DIR / "tests"))
    with open(__import__("os").devnull, "w") as devnull:
        runner = unittest.TextTestRunner(stream=devnull, resultclass=_Collector, verbosity=0)
        res = runner.run(suite)
    recs = res.records
    return {"total": len(recs),
            "passed": sum(r["status"] == "PASS" for r in recs.values()),
            "failed": sum(r["status"] == "FAIL" for r in recs.values()),
            "skipped": sum(r["status"] == "SKIPPED" for r in recs.values()),
            "tests": recs}


def _ref_ok(ref: str) -> bool:
    path, _, sym = ref.partition("::")
    p = PKG_DIR / path
    if path.endswith("/"):
        return p.is_dir() and any(p.iterdir())
    if not p.exists():
        return False
    if not sym:
        return p.stat().st_size > 0 if p.is_file() else True
    text = p.read_text(encoding="utf-8", errors="replace")
    return sym.split(".")[-1] in text


def approvals(today: dt.date) -> dict[str, dict]:
    data = json.loads((PKG_DIR / "governance/APPROVALS.json").read_text())
    keys = json.loads((PKG_DIR / "governance/EXTERNAL_EVIDENCE.json").read_text())["keys"]
    ok = {}
    for a in data.get("approvals", []):
        k = a.get("key")
        try:
            exp = dt.date.fromisoformat(a.get("expires", ""))
        except ValueError:
            continue
        if k in keys and a.get("role") == keys[k]["role"] and a.get("approver") and exp >= today \
                and a.get("signature"):
            ok[k] = a
    return ok


def audit(today: dt.date | None = None, tests: dict | None = None) -> dict:
    today = today or dt.date.today()
    R = importlib.import_module("requirements_src").R
    checklist = json.loads((PKG_DIR / "CHECKLIST.json").read_text())
    ext_keys = json.loads((PKG_DIR / "governance/EXTERNAL_EVIDENCE.json").read_text())["keys"]
    tests = tests if tests is not None else run_tests()
    approved = approvals(today)
    by_cid: dict[str, list[tuple[str, str]]] = {}
    for tid, r in tests["tests"].items():
        for c in r["cids"]:
            by_cid.setdefault(c, []).append((tid, r["status"]))
    reqs = []
    for item in checklist["items"]:
        cid = item["check_id"]
        short = cid.split("-")[-1]
        shall, impl, docs, ext = R[short]
        t = by_cid.get(cid, [])
        if short == "C081":
            t = [(tid, r["status"]) for tid, r in tests["tests"].items() if tid.startswith("test_manager.")]
        missing_refs = [x for x in impl + docs if not _ref_ok(x)]
        failed = [tid for tid, s in t if s == "FAIL"]
        skipped = [tid for tid, s in t if s == "SKIPPED"]
        pending = [k for k in ext if k not in approved]
        if missing_refs or failed or skipped:
            status = "MISSING"
        elif pending:
            status = "PARTIAL"
        else:
            status = "SATISFIED"
        reqs.append({
            "check_id": cid, "ordinal": item["ordinal"], "dimension": item["dimension"],
            "requirement": item["requirement"], "shall": shall, "status": status,
            "implementation": impl, "design": docs, "tests": sorted(tid for tid, _ in t),
            "tests_passed": sum(s == "PASS" for _, s in t), "missing_refs": missing_refs,
            "failed_tests": failed, "skipped_tests": skipped,
            "external_evidence_pending": [{"key": k, "role": ext_keys[k]["role"], "what": ext_keys[k]["what"]}
                                          for k in pending],
            "owner": "UNASSIGNED",
        })
    summary = {s: sum(r["status"] == s for r in reqs) for s in ("SATISFIED", "PARTIAL", "MISSING")}
    return {
        "schema": "INV63_AUDIT/2", "element": "INV-63", "name": "Wasm deployment manager",
        "version": (PKG_DIR / "VERSION").read_text().strip(), "audit_date": today.isoformat(),
        "source_digest": evidence.source_digest(),
        "method": "executable: audit.py (tests + refs + approvals); no status is asserted by hand",
        "test_summary": {k: tests[k] for k in ("total", "passed", "failed", "skipped")},
        "summary": summary, "requirements": reqs,
    }


def write_docs(result: dict) -> None:
    reqs = result["requirements"]
    (PKG_DIR / "docs/requirements/REQUIREMENTS.json").write_text(json.dumps(
        {"schema": "INV63_REQUIREMENTS/1", "requirements": [
            {k: r[k] for k in ("check_id", "dimension", "requirement", "shall", "implementation", "design")}
            for r in reqs]}, indent=2) + "\n")
    md = ["# INV-63 normative requirements (INV-63-C011)", "",
          "Generated by `audit.py` from `tools/requirements_src.py`. Each SHALL is verified by the tests listed in",
          "`TRACEABILITY.md`.", ""]
    dim = None
    for r in reqs:
        if r["dimension"] != dim:
            dim = r["dimension"]; md += ["", f"## {dim}", ""]
        md.append(f"- **{r['check_id']}** — {r['shall']}")
    (PKG_DIR / "docs/requirements/REQUIREMENTS.md").write_text("\n".join(md) + "\n")
    tr = ["# INV-63 traceability matrix (INV-63-C020)", "",
          f"Generated by `audit.py` on {result['audit_date']} for source digest `{result['source_digest']}`.",
          f"Tests: {result['test_summary']}.", "",
          "| C-ID | Status | Design | Implementation | Tests (passed/total) | External evidence pending | Owner |",
          "|---|---|---|---|---|---|---|"]
    for r in reqs:
        tr.append(f"| {r['check_id']} | {r['status']} | {'<br>'.join(r['design'])} | {'<br>'.join(r['implementation'])} | "
                  f"{r['tests_passed']}/{len(r['tests'])} | {', '.join(e['key'] for e in r['external_evidence_pending']) or '-'} | {r['owner']} |")
    (PKG_DIR / "docs/requirements/TRACEABILITY.md").write_text("\n".join(tr) + "\n")
    s = result["summary"]
    mc = ["# INV-63 — Remaining production-readiness items", "",
          f"**Version audited:** {result['version']} — generated by `audit.py` on {result['audit_date']}  ",
          f"**Result:** {s['SATISFIED']} satisfied, {s['PARTIAL']} partial (repository work complete, external evidence pending), "
          f"{s['MISSING']} missing.  ",
          f"**Source digest:** `{result['source_digest']}`", "",
          "No item below can be closed from inside the repository: each needs the named role to supply evidence and",
          "record a signed approval in `governance/APPROVALS.json` (format in that file), after which `audit.py` re-rates it.", ""]
    pend: dict[str, list[str]] = {}
    for r in reqs:
        for e in r["external_evidence_pending"]:
            pend.setdefault(e["key"], []).append(r["check_id"])
    keys = json.loads((PKG_DIR / "governance/EXTERNAL_EVIDENCE.json").read_text())["keys"]
    for k, cids in sorted(pend.items()):
        mc += [f"## {k} — owner role: `{keys[k]['role']}`", "", keys[k]["what"], "", f"**Blocks:** {', '.join(cids)}", ""]
    missing = [r for r in reqs if r["status"] == "MISSING"]
    if missing:
        mc += ["## MISSING (repository defects)", ""]
        for r in missing:
            mc.append(f"- {r['check_id']}: refs={r['missing_refs']} failed={r['failed_tests']} skipped={r['skipped_tests']}")
    (PKG_DIR / "MISSING_COMPONENTS.md").write_text("\n".join(mc) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(PKG_DIR / "evidence"))
    ap.add_argument("--no-write-docs", action="store_true")
    a = ap.parse_args(argv)
    tests = run_tests()
    result = audit(tests=tests)
    out = pathlib.Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "test_results.json").write_text(json.dumps({"source_digest": result["source_digest"], **tests}, indent=2))
    (PKG_DIR / "AUDIT_RESULTS.json").write_text(json.dumps(result, indent=2) + "\n")
    bundle = {"schema": "INV63_EVIDENCE_BUNDLE/1", "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
              "source_digest": result["source_digest"], "audit_summary": result["summary"],
              "test_summary": result["test_summary"],
              "audit_results_sha256": __import__("hashlib").sha256((PKG_DIR / "AUDIT_RESULTS.json").read_bytes()).hexdigest()}
    (out / "audit_bundle.json").write_text(json.dumps(bundle, indent=2) + "\n")
    if not a.no_write_docs:
        write_docs(result)
    print(json.dumps({"summary": result["summary"], "tests": result["test_summary"]}))
    return 0 if result["summary"]["MISSING"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
