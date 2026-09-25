"""RTM builder and the formal production exit gate (C020, C070, C090, C099, C100).

``certify()`` produces an explicit ``GO`` / ``CONDITIONAL_GO`` / ``NO_GO`` from
executed evidence only.  Rules:

* a failed or erroring mandatory test -> FAIL; a *skipped* mandatory test -> BLOCKED;
* a requirement with no linked test -> BLOCKED (RTM incomplete);
* any FAIL or BLOCKED -> ``NO_GO`` (exit code 20);
* otherwise open CONDITIONs -> ``CONDITIONAL_GO`` (exit 10) only if every condition
  is accepted, with approver and unexpired date, in governance/ACCEPTED_CONDITIONS.json;
  an unaccepted condition -> ``NO_GO``;
* otherwise ``GO`` (exit 0).

The evidence record lists the SHA-256 of every input and is sealed with a SHA-256
digest, plus HMAC-SHA256 when ``INV18_RELEASE_KEY`` holds a key.  ``verify()``
re-derives everything and fails on any difference.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import hmac
import importlib.util
import json
import os
import pathlib
import platform
import re
import subprocess
import sys
from typing import Any

PKG = pathlib.Path(__file__).resolve().parent
EXIT = {"GO": 0, "CONDITIONAL_GO": 10, "NO_GO": 20}
PASS, FAIL, BLOCKED, CONDITION = "PASS", "FAIL", "BLOCKED", "CONDITION"


def _read(rel: str) -> Any:
    return json.loads((PKG / rel).read_text(encoding="utf-8"))


def sha256_file(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _today() -> _dt.date:
    s = os.environ.get("INV18_TODAY")
    return _dt.date.fromisoformat(s) if s else _dt.date.today()


# ------------------------------------------------------------------ RTM
def build_rtm(results: dict) -> dict:
    req = _read("REQUIREMENTS.json")
    by_tag: dict[str, list[dict]] = {}
    untagged = []
    for t in results["tests"]:
        if not t["tags"]:
            untagged.append(t["id"])
        for tag in t["tags"]:
            by_tag.setdefault(tag, []).append(t)
    rows = []
    known = set()
    for kind, items in (("shall", req["shall"]), ("checklist", req["checklist"])):
        for it in items:
            rid = it["id"]
            known.add(rid)
            tests = by_tag.get(rid, [])
            arts = it.get("artifacts") or [a.strip().split("::")[0] for a in it.get("realised_by", "").split(";") if a.strip()]
            from .tools_verify import GENERATED
            missing_art = [a for a in arts if a not in GENERATED and not (PKG / a.split(" ")[0]).exists()]
            st = [t["status"] for t in tests]
            if not tests:
                status, why = "blocked", "no linked test"
            elif any(s in ("fail", "error") for s in st):
                status, why = "failed", "linked test failed"
            elif any(s == "skip" for t, s in zip(tests, st) if t["mandatory"]):
                status, why = "blocked", "mandatory linked test skipped"
            elif missing_art:
                status, why = "partial", "missing artifact(s): " + ", ".join(missing_art)
            elif it.get("blockers"):
                status, why = "partial", "open blockers: " + ", ".join(it["blockers"])
            else:
                status, why = "satisfied", ""
            rows.append({"id": rid, "kind": kind, "text": it.get("text") or it.get("requirement"),
                         "artifacts": arts, "tests": [t["id"] for t in tests],
                         "test_status": {t["id"]: t["status"] for t in tests},
                         "blockers": it.get("blockers", []), "status": status, "reason": why,
                         "artifact_digests": {a: sha256_file(PKG / a) for a in arts
                                              if (PKG / a).is_file()}})
    unknown_tags = sorted(t for t in by_tag if t not in known)
    # orphan implementation: package modules no requirement mentions
    mentioned = " ".join(" ".join(r["artifacts"]) for r in rows)
    orphans = sorted(p.name for p in PKG.glob("*.py")
                     if p.name not in mentioned and p.name not in ("__init__.py", "__main__.py"))
    summary: dict[str, int] = {}
    for r in rows:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    return {"schema": "INV18_RTM/1", "version": (PKG / "VERSION").read_text().strip(),
            "summary": summary, "requirements": len(rows),
            "checklist_coverage": sum(1 for r in rows if r["kind"] == "checklist" and r["tests"]),
            "tests_without_requirements": untagged, "unknown_tags": unknown_tags,
            "orphan_modules": orphans, "rows": rows}


def rtm_markdown(rtm: dict) -> str:
    out = [f"# INV-18 requirements traceability (generated, v{rtm['version']})", "",
           "Generated from conformance/RTM.json by `python -m inv18_completion_primitive rtm`; do not edit.", "",
           "Summary: " + ", ".join(f"{k}={v}" for k, v in sorted(rtm["summary"].items())), "",
           "| Requirement | Status | Tests | Reason |", "|---|---|---|---|"]
    for r in rtm["rows"]:
        out.append(f"| {r['id']} | {r['status']} | {len(r['tests'])} | {r['reason']} |")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ blocker resolution
def _waiver(wid: str) -> dict | None:
    return next((w for w in _read("governance/WAIVERS.json")["entries"] if w["id"] == wid), None)


def _pk_core_available() -> bool:
    return importlib.util.find_spec("pk_core") is not None


def resolve_blocker(name: str, ctx: dict) -> tuple[str, str] | None:
    """Return (severity, detail) while a blocker is still open, None when cleared."""
    if name == "PK_CORE_MISSING":
        lock = _read("requirements.lock.json")
        pinned = next((d for d in lock["dependencies"] if d["name"] == "pk_core"), {})
        if _pk_core_available() and pinned.get("sha256"):
            return None
        return BLOCKED, "pk_core not importable and/or not pinned by digest (W-C031)"
    if name == "OWNERS_VACANT":
        o = _read("governance/OWNERS.json")
        vac = [r for r in o["required_roles"] if o["roles"][r]["team"] in ("", "VACANT")]
        return (BLOCKED, "vacant owner roles: " + ", ".join(vac)) if vac else None
    if name == "ADR_NOT_APPROVED":
        txt = (PKG / "docs/adr/ADR-001-completion-primitive.md").read_text()
        return None if re.search(r"\| Status \| \*\*ACCEPTED\*\*", txt) else (BLOCKED, "ADR-001 status is not ACCEPTED")
    if name == "THREAT_MODEL_NOT_APPROVED":
        return None if _read("conformance/THREAT_MODEL.json").get("approved_by") else \
            (CONDITION, "threat model not approved by the security owner")
    if name == "UNSIGNED_EVIDENCE":
        return None if os.environ.get("INV18_RELEASE_KEY") else (CONDITION, "no release signing key; evidence sealed by digest only")
    if name == "THRESHOLDS_PROPOSED":
        th = _read("conformance/PERFORMANCE_THRESHOLDS.json")
        return None if th.get("status") == "APPROVED" else (CONDITION, "performance thresholds/SLO are PROPOSED (W-C062)")
    if name == "REAL_TIER_NOT_RUN":
        real = [t for t in ctx["results"]["tests"] if t["id"].startswith("tests/test_integration_real.py")]
        if real and all(t["status"] == "pass" for t in real):
            return None
        return BLOCKED, "real INV-12/15/16/17/20 integration tier not executed"
    if name == "PLATFORMS_NOT_RUN":
        cr = ctx.get("compat") or {}
        need = set(_read("conformance/COMPAT_MATRIX.json")["declared_platforms"])
        have = {r["platform"] for r in cr.get("runs", []) if r.get("passed")}
        missing = sorted(need - have)
        return (CONDITION, "declared platforms without executed evidence: " + ", ".join(missing)) if missing else None
    if name == "TABLETOP_PENDING":
        recs = _read("governance/REVIEWS.json")["records"]
        done = any(r.get("review") == "incident_tabletop" and r.get("completed_by") for r in recs)
        return None if done else (CONDITION, "incident tabletop exercise not conducted")
    if name == "REVIEW_NOT_COUNTERSIGNED":
        recs = _read("governance/REVIEWS.json")["records"]
        return None if any(r.get("completed_by") for r in recs) else (CONDITION, "no human-completed review record")
    w = _waiver(name)
    if w is not None:
        exp = _dt.date.fromisoformat(w["expires"])
        if exp < _today():
            return FAIL, f"waiver {name} expired {w['expires']}"
        if not w.get("approved_by"):
            return CONDITION, f"waiver {name} proposed but not approved"
        return None
    return BLOCKED, f"unknown blocker {name}"


# ------------------------------------------------------------------ evidence producers
def run_suite(python: str = sys.executable, env: dict | None = None) -> dict:
    code = ("import json,sys; sys.path.insert(0, %r); from %s import testrunner; "
            "print(json.dumps(testrunner.run()))") % (str(PKG.parent), PKG.name)
    out = subprocess.run([python, "-c", code], capture_output=True, text=True, cwd=str(PKG.parent),
                         env={**os.environ, **(env or {})}, timeout=1800)
    if out.returncode != 0 or not out.stdout.strip():
        return {"schema": "INV18_TEST_RESULTS/1", "tests": [], "counts": {"error": 1},
                "runner_error": out.stderr[-3000:], "environment": {"python": python}}
    return json.loads(out.stdout.strip().splitlines()[-1])


def perf_check(bench_result: dict) -> list[dict]:
    th = _read("conformance/PERFORMANCE_THRESHOLDS.json")
    out = []
    for path, rule in th["absolute"].items():
        cur: Any = bench_result
        try:
            for k in path.split("."):
                cur = cur[int(k)] if isinstance(cur, list) else cur[k]
            cur = float(cur)
        except (KeyError, TypeError, ValueError):
            out.append({"metric": path, "result": FAIL, "detail": "missing measurement"})
            continue
        ok = cur <= rule["max"] if "max" in rule else cur >= rule["min"]
        out.append({"metric": path, "value": cur, "rule": rule, "result": PASS if ok else FAIL})
    return out


# ------------------------------------------------------------------ gate
def _check(checks: list, cid: str, reqs: list[str], result: str, detail: str) -> None:
    checks.append({"check": cid, "requirements": reqs, "result": result, "detail": detail})


def certify(*, results: dict | None = None, bench_result: dict | None = None, fault_results: list | None = None,
            compat: dict | None = None, bootstrap_report: dict | None = None, out_dir: pathlib.Path | None = None,
            write: bool = True) -> dict:
    from . import bench, bootstrap, fault, fixtures_runner
    if write and out_dir is None:
        # a fresh certification must not be influenced by the previous one's outputs
        from .tools_verify import GENERATED
        for rel in GENERATED - {"SHA256SUMS", "conformance/COMPAT_RESULTS.json"}:
            (PKG / rel).unlink(missing_ok=True)
    results = results if results is not None else run_suite()
    bench_result = bench_result if bench_result is not None else bench.run(quick=True, reps=3)
    fault_results = fault_results if fault_results is not None else fault.run_all()
    if compat is None and (PKG / "conformance/COMPAT_RESULTS.json").exists():
        compat = _read("conformance/COMPAT_RESULTS.json")
    bootstrap_report = bootstrap_report if bootstrap_report is not None else bootstrap.run(write=False)
    ctx = {"results": results, "compat": compat}
    rtm = build_rtm(results)
    checks: list[dict] = []

    # tests: failures, errors, skips of mandatory tests
    bad = [t for t in results["tests"] if t["status"] in ("fail", "error")]
    skipped = [t for t in results["tests"] if t["status"] == "skip" and t["mandatory"]]
    _check(checks, "tests.executed", ["INV-18-C082", "INV-18-C090"], PASS if results["tests"] and not bad else FAIL,
           f"{results.get('counts')}; failing: {[t['id'] for t in bad][:10]}" + (f"; runner: {results.get('runner_error','')[-300:]}" if results.get("runner_error") else ""))
    _check(checks, "tests.no_mandatory_skips", ["INV18-CMP-003", "INV-18-C100"], PASS if not skipped else BLOCKED,
           "mandatory skipped: " + ", ".join(t["id"] + " (" + (t["detail"] or "") + ")" for t in skipped) if skipped else "none")
    # RTM
    rtm_blocked = [r["id"] for r in rtm["rows"] if r["status"] in ("blocked", "failed") and r["reason"] == "no linked test"]
    _check(checks, "rtm.complete", ["INV-18-C020"], PASS if not rtm_blocked and not rtm["unknown_tags"] and not rtm["orphan_modules"] else BLOCKED,
           f"untested: {rtm_blocked}; unknown tags: {rtm['unknown_tags']}; orphan modules: {rtm['orphan_modules']}; untagged tests: {len(rtm['tests_without_requirements'])}")
    failed_reqs = [r["id"] for r in rtm["rows"] if r["status"] == "failed"]
    _check(checks, "requirements.mandatory", ["INV-18-C011", "INV-18-C100"], PASS if not failed_reqs else FAIL,
           f"failed requirements: {failed_reqs}")
    # blockers (conditions / blocked) from the requirements map
    seen = {}
    for r in rtm["rows"]:
        for b in r["blockers"]:
            seen.setdefault(b, []).append(r["id"])
    for b, rids in sorted(seen.items()):
        res = resolve_blocker(b, ctx)
        _check(checks, f"blocker.{b}", rids, PASS if res is None else res[0], "cleared" if res is None else res[1])
    # schemas & fixtures
    from . import wire
    drift = [n for n, s in wire.SCHEMAS.items()
             if not (PKG / "schemas" / (n.replace("/", "_v") + ".json")).exists()
             or json.loads((PKG / "schemas" / (n.replace("/", "_v") + ".json")).read_text()) != s]
    _check(checks, "interfaces.schemas", ["INV-18-C022"], PASS if not drift else FAIL, f"drifted/missing: {drift}")
    fx = fixtures_runner.run_all()
    _check(checks, "interfaces.fixtures", ["INV-18-C029"], PASS if fx and all(f["passed"] for f in fx) else FAIL,
           f"{sum(f['passed'] for f in fx)}/{len(fx)} fixtures pass")
    # threat model coverage
    tm = _read("conformance/THREAT_MODEL.json")
    status = {t["id"]: t["status"] for t in results["tests"]}
    uncovered = [th["id"] for th in tm["threats"] if th["severity"] in ("high", "critical")
                 and not all(status.get(x) == "pass" for x in th["tests"])]
    _check(checks, "security.threat_coverage", ["INV-18-C041", "INV-18-C087"], PASS if not uncovered else FAIL,
           f"high/critical threats without passing tests: {uncovered}")
    # resilience
    fbad = [f["scenario"] for f in fault_results if not f["passed"]]
    _check(checks, "resilience.faults", ["INV-18-C060", "INV-18-C089"], PASS if not fbad else FAIL,
           f"{len(fault_results) - len(fbad)}/{len(fault_results)} scenarios recovered; failed: {fbad}")
    # performance
    pc = perf_check(bench_result)
    pbad = [p["metric"] for p in pc if p["result"] != PASS]
    _check(checks, "performance.thresholds", ["INV-18-C062", "INV18-NFR-003"], PASS if not pbad else FAIL,
           f"out of threshold: {pbad}")
    base = _read("conformance/BENCH_BASELINE.json")
    waived = {w["requirement"]: w for w in _read("governance/WAIVERS.json")["entries"] if w.get("approved_by")}
    regs = bench.compare(bench_result, base, waivers=waived)
    _check(checks, "performance.regression", ["INV-18-C070", "INV18-NFR-004"], PASS if not regs else FAIL,
           f"regressions vs approved baseline: {regs}")
    # bootstrap / config / dependencies
    _check(checks, "bootstrap.clean", ["INV-18-C040"], PASS if bootstrap_report.get("ok") else FAIL,
           "; ".join(f"{s['step']}={s['result']}" for s in bootstrap_report.get("steps", [])))
    # waivers expiry
    expired = [w["id"] for w in _read("governance/WAIVERS.json")["entries"] if _dt.date.fromisoformat(w["expires"]) < _today()]
    _check(checks, "governance.waivers_unexpired", ["INV-18-C099"], PASS if not expired else FAIL, f"expired: {expired}")
    # overdue critical reviews
    rv = _read("governance/REVIEWS.json")
    last = {}
    for r in rv["records"]:
        if r.get("completed_by"):
            for name in (rv["cadence_days"] if r["review"] == "all" else [r["review"]]):
                last[name] = max(last.get(name, r["date"]), r["date"])
    overdue = [c for c in rv["critical"] if c in last and
               (_today() - _dt.date.fromisoformat(last[c])).days > rv["cadence_days"][c]]
    _check(checks, "governance.reviews_current", ["INV-18-C098"], PASS if not overdue else FAIL, f"overdue: {overdue}")
    # artifact integrity
    from .tools_verify import verify_tree
    bad_files = verify_tree(PKG)
    _check(checks, "integrity.artifact_digests", ["INV-18-C045"], PASS if not bad_files else FAIL,
           f"digest mismatches: {bad_files[:10]}")

    # ---------------------------------------------------------------- verdict
    fails = [c for c in checks if c["result"] in (FAIL, BLOCKED)]
    conds = [c for c in checks if c["result"] == CONDITION]
    accepted = {a["condition"]: a for a in _read("governance/ACCEPTED_CONDITIONS.json")["accepted"]
                if a.get("approved_by") and _dt.date.fromisoformat(a["expires"]) >= _today()}
    unaccepted = [c["check"] for c in conds if c["check"] not in accepted]
    if fails:
        verdict = "NO_GO"
    elif conds and unaccepted:
        verdict = "NO_GO"
    elif conds:
        verdict = "CONDITIONAL_GO"
    else:
        verdict = "GO"

    version = (PKG / "VERSION").read_text().strip()
    sums = PKG / "SHA256SUMS"
    artifact_digest = sha256_file(sums) if sums.exists() else None
    inputs = {rel: sha256_file(PKG / rel) for rel in
              ("REQUIREMENTS.json", "CHECKLIST.json", "governance/OWNERS.json", "governance/WAIVERS.json",
               "governance/REVIEWS.json", "governance/ACCEPTED_CONDITIONS.json", "conformance/THREAT_MODEL.json",
               "conformance/PERFORMANCE_THRESHOLDS.json", "conformance/BENCH_BASELINE.json",
               "conformance/COMPAT_MATRIX.json", "conformance/COMPAT_RESULTS.json", "requirements.lock.json", "docs/adr/ADR-001-completion-primitive.md",
               "SHA256SUMS") if (PKG / rel).exists()}
    evidence = {
        "schema": "INV18_RELEASE_EVIDENCE/1", "component": "INV-18", "version": version,
        "source_commit": os.environ.get("INV18_SOURCE_COMMIT", "no-vcs"),
        "artifact_digest": artifact_digest,
        "build_environment": {"python": platform.python_version(), "system": platform.system(),
                              "machine": platform.machine(), "host_id": hashlib.sha256(platform.node().encode()).hexdigest()[:12]},
        "generated": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "verdict": verdict, "exit_code": EXIT[verdict],
        "unaccepted_conditions": unaccepted, "checks": checks,
        "test_summary": {"counts": results.get("counts"), "total": len(results["tests"]),
                         "environment": results.get("environment")},
        "rtm_summary": rtm["summary"], "fault_results": fault_results,
        "benchmark_metadata": bench_result.get("metadata"),
        "input_digests": inputs,
    }
    body = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    seal = {"sha256": hashlib.sha256(body).hexdigest(), "hmac_sha256": None}
    key = os.environ.get("INV18_RELEASE_KEY")
    if key:
        seal["hmac_sha256"] = hmac.new(key.encode(), body, hashlib.sha256).hexdigest()
    evidence["seal"] = seal
    if write:
        od = out_dir or (PKG / "conformance")
        od.mkdir(parents=True, exist_ok=True)
        (od / "RTM.json").write_text(json.dumps(rtm, indent=1))
        (od / "RTM.md").write_text(rtm_markdown(rtm))
        (od / "RELEASE_EVIDENCE.json").write_text(json.dumps(evidence, indent=1))
        (od / "TEST_RESULTS.json").write_text(json.dumps(results, indent=1))
        (od / "BENCH_RESULTS.json").write_text(json.dumps(bench_result, indent=1, default=str))
        (od / "LINEAGE.json").write_text(json.dumps({
            "release_id": f"INV-18-{version}-{seal['sha256'][:12]}", "version": version,
            "artifact_digest": artifact_digest, "source_commit": evidence["source_commit"],
            "evidence_seal": seal["sha256"], "config_revision_certified": "defaults+test",
            "infrastructure_graph": None}, indent=1))
    return evidence


def verify(path: pathlib.Path | str | None = None) -> tuple[bool, list[str]]:
    """Independently re-validate a sealed evidence record against the tree."""
    p = pathlib.Path(path) if path else PKG / "conformance" / "RELEASE_EVIDENCE.json"
    ev = json.loads(p.read_text())
    problems = []
    seal = ev.pop("seal", {})
    body = json.dumps(ev, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(body).hexdigest() != seal.get("sha256"):
        problems.append("seal digest mismatch (evidence altered)")
    key = os.environ.get("INV18_RELEASE_KEY")
    if seal.get("hmac_sha256"):
        if not key:
            problems.append("evidence is HMAC-sealed but INV18_RELEASE_KEY is not available to verify it")
        elif not hmac.compare_digest(hmac.new(key.encode(), body, hashlib.sha256).hexdigest(), seal["hmac_sha256"]):
            problems.append("HMAC mismatch")
    root = p.parent.parent if p.parent.name == "conformance" else PKG
    for rel, d in ev.get("input_digests", {}).items():
        f = root / rel
        if not f.exists() or sha256_file(f) != d:
            problems.append(f"input changed since certification: {rel}")
    if ev.get("exit_code") != EXIT.get(ev.get("verdict")):
        problems.append("verdict/exit code inconsistent")
    return (not problems), problems
