"""Formal production-exit gate + machine-readable release evidence (checklist #89, #98, #99).

    python -m inv55_secrets_integration.tools.gate [--out evidence]

Collects evidence by EXECUTING things (compile, the full unittest suite with
per-test results, secret scan, SBOM/import audit, schema-file drift, config
validation, benchmark, status registry drift, digests), then ``evaluate()``
decides.  Rules that make the verdict honest:

* a mandatory gate is PASS only if it executed and passed; NOT_RUN, BLOCKED,
  SKIPPED and FAIL are all non-PASS;
* any skipped test in the mandatory suite fails the ``tests`` gate - a skip is
  not a pass (the three pk_core conformance tests therefore fail it here);
* a waiver covers nothing unless APPROVED, unexpired (<= 90 days), with an
  approver and compensating controls;
* approvals count only for a human principal named in OWNERSHIP.md, never for
  the evidence author, and never for a name that reads as a tool or model;
* GO requires every gate PASS, every component complete, and engineering,
  security and operations release approvals.
Exit code: 0 GO, 3 NO_GO.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import pathlib
import platform
import re
import subprocess
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG.parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

EVIDENCE_AUTHOR = "chop-shop build (Claude)"
TOOLISH = re.compile(r"(?i)\b(claude|gpt|copilot|bot|ci|automation|service|tool|pipeline|agent|unassigned)\b")
MANDATORY = ["compile", "tests", "security_suite", "fuzz", "concurrency", "integration_real_vault", "secret_scan",
             "sbom", "schemas", "config_validation", "status_registry", "performance", "provenance_signature",
             "waivers", "components", "approvals"]


# ---------------------------------------------------------------- evaluation
def valid_approver(entry: dict, owners: set[str]) -> tuple[bool, str]:
    who = str(entry.get("approver") or "")
    if not who:
        return False, "no approver"
    if entry.get("principal_kind") != "human":
        return False, "principal is not human"
    if TOOLISH.search(who):
        return False, "approver reads as a tool/model/placeholder"
    if who == EVIDENCE_AUTHOR or who == entry.get("evidence_author"):
        return False, "author cannot approve own evidence"
    if who not in owners:
        return False, "approver not named in OWNERSHIP.md"
    return True, "ok"


def check_waivers(reg: dict, today: dt.date) -> tuple[list[dict], list[str]]:
    effective, problems = [], []
    for w in reg.get("waivers", []):
        if w.get("status") != "APPROVED":
            continue
        exp = w.get("expires")
        try:
            e = dt.date.fromisoformat(exp) if exp else None
            c = dt.date.fromisoformat(w.get("created"))
        except (TypeError, ValueError):
            problems.append(f"{w.get('id')}: bad dates"); continue
        if e is None or e < today:
            problems.append(f"{w.get('id')}: expired or no expiry"); continue
        if (e - c).days > 90:
            problems.append(f"{w.get('id')}: expiry beyond 90 days"); continue
        if not w.get("approver") or not w.get("compensating_controls"):
            problems.append(f"{w.get('id')}: missing approver/compensating controls"); continue
        effective.append(w)
    return effective, problems


def evaluate(ev: dict, today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    g = {}
    def put(k, result, detail):
        g[k] = {"result": result, "detail": detail}
    put("compile", "PASS" if ev["compile_ok"] else "FAIL", "compileall")
    t = ev["tests"]
    skipped = [x for x in t["results"] if x["status"] == "skipped"]
    failed = [x for x in t["results"] if x["status"] in ("FAIL", "ERROR")]
    parsed_all = t.get("ran", len(t["results"])) == len(t["results"])
    put("tests", "PASS" if t["executed"] and parsed_all and not failed and not skipped else "FAIL",
        {"total": len(t["results"]), "ran": t.get("ran"), "every_result_accounted_for": parsed_all, "failed": len(failed), "skipped": len(skipped),
         "skipped_ids": [s["id"] for s in skipped][:20], "rule": "a skipped mandatory test is not a pass"})
    def suite(key, prefix):
        rs = [x for x in t["results"] if x["id"].startswith(prefix)]
        ok = bool(rs) and all(x["status"] == "ok" for x in rs)
        put(key, "PASS" if ok else ("NOT_RUN" if not rs else "FAIL"), {"tests": len(rs)})
    suite("security_suite", "test_runtime_service.Adversarial")
    suite("fuzz", "test_runtime_service.Fuzz")
    suite("concurrency", "test_runtime_service.Concurrency")
    put("integration_real_vault", "BLOCKED" if not ev.get("real_vault") else "PASS",
        "only the KV v2 wire double is available (W-001)" if not ev.get("real_vault") else ev["real_vault"])
    put("secret_scan", "PASS" if ev["secret_findings"] == 0 else "FAIL", {"findings": ev["secret_findings"]})
    put("sbom", "PASS" if not ev["third_party_imports"] else "FAIL", {"third_party_imports": ev["third_party_imports"]})
    put("schemas", "PASS" if not ev["schema_drift"] else "FAIL", {"drift": ev["schema_drift"]})
    put("config_validation", "PASS" if not ev["config_errors"] else "FAIL", ev["config_errors"] or "all deploy/config documents valid")
    put("status_registry", "PASS" if not ev["status_problems"] and not ev["status_drift"] else "FAIL",
        {"problems": ev["status_problems"], "drift": ev["status_drift"]})
    b = ev.get("bench")
    if b is None:
        put("performance", "NOT_RUN", "benchmark not executed")
    else:
        put("performance", "FAIL" if not all(b["verdict"].values()) else "BLOCKED",
            "reference host met PROPOSED thresholds, but thresholds are unapproved and the environment is not certified (W-006)"
            if all(b["verdict"].values()) else b["verdict"])
    put("provenance_signature", "BLOCKED" if not ev.get("signature") else "PASS",
        "digests recorded in SHA256SUMS; no signing identity (W-009)")
    eff, wprob = check_waivers(ev["waivers"], today)
    put("waivers", "PASS" if not wprob else "FAIL", {"effective": [w["id"] for w in eff], "problems": wprob,
                                                     "open_proposed": sum(1 for w in ev["waivers"].get("waivers", []) if w.get("status") != "APPROVED")})
    owners = set(ev["owners"])
    comp_ok, comp_rows = 0, []
    appr = [a for a in ev["approvals"].get("approvals", [])]
    for c in ev["components"]:
        a = next((x for x in appr if x.get("component") == c["id"]), None)
        ok_a, why = valid_approver(a, owners) if a else (False, "no approval")
        complete = c["status"] == "IMPLEMENTED" and ok_a and all(
            any(r["id"].startswith(_tid(tn)) and r["status"] == "ok" for r in t["results"]) for tn in c["tests"]) and bool(c["tests"])
        comp_ok += complete
        if not complete:
            comp_rows.append({"id": c["id"], "status": c["status"], "why": why if c["status"] == "IMPLEMENTED" else c.get("blocker")})
    put("components", "PASS" if comp_ok == len(ev["components"]) == 100 else "FAIL",
        {"complete": comp_ok, "total": len(ev["components"]), "first_incomplete": comp_rows[:10]})
    roles_needed = {"engineering", "security", "operations"}
    got = set()
    refused = []
    for a in appr:
        if a.get("component") == "release":
            ok_a, why = valid_approver(a, owners)
            if ok_a:
                got.add(a.get("role"))
            else:
                refused.append({"approver": a.get("approver"), "why": why})
    put("approvals", "PASS" if roles_needed <= got else "FAIL",
        {"have": sorted(got), "need": sorted(roles_needed), "refused": refused})
    verdict = "GO" if all(g[k]["result"] == "PASS" for k in MANDATORY) else "NO_GO"
    counts = {}
    for k in MANDATORY:
        counts[g[k]["result"]] = counts.get(g[k]["result"], 0) + 1
    return {"schema": "PK_GATE_RESULTS/inv55-1", "element": "INV-55", "verdict": verdict, "gate_counts": counts, "gates": g}


def _tid(test_ref: str) -> str:
    """'tests/test_x.py::Cls.meth' -> 'test_x.Cls.meth' (prefix match)."""
    f, _, rest = test_ref.partition("::")
    mod = pathlib.Path(f).stem
    return f"{mod}.{rest}" if rest else mod


# ---------------------------------------------------------------- collection
_LINE = re.compile(r"^(test\w*) \((\S+)\)(?:\n.*?)? \.\.\. (ok|skipped.*|FAIL|ERROR|expected failure|unexpected success)$", re.M)


def run_tests():
    p = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", str(PKG / "tests"), "-v"],
                       capture_output=True, text=True, cwd=str(ROOT), timeout=900)
    res = []
    for m in _LINE.finditer(p.stderr):
        name, where, st = m.groups()
        st = "skipped" if st.startswith("skipped") else st
        # where = module.Class.test (py3.11+) or module.Class
        full = where if where.endswith(name) else f"{where}.{name}"
        res.append({"id": full, "status": st})
    m = re.search(r"^Ran (\d+) tests?", p.stderr, re.M)
    return {"executed": p.returncode in (0, 1), "returncode": p.returncode, "results": res, "ran": int(m.group(1)) if m else None,
            "summary": p.stderr.strip().splitlines()[-1] if p.stderr.strip() else ""}


def digests(files):
    out = []
    for f in files:
        out.append(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.relative_to(PKG).as_posix()}")
    return "\n".join(out) + "\n"


def collect(bench_n=2000):
    from inv55_secrets_integration.runtime import config as C
    from inv55_secrets_integration.runtime.wire import SCHEMAS
    import secret_scan, sbom, build_status, bench  # noqa: E401
    ev = {}
    ev["compile_ok"] = _compile_check()
    ev["tests"] = run_tests()
    ev["secret_findings"] = len(secret_scan.scan(PKG))
    bom, third = sbom.build((PKG / "VERSION").read_text().strip())
    ev["sbom"], ev["third_party_imports"] = bom, third
    drift = []
    for k, s in SCHEMAS.items():
        f = PKG / "schemas" / f"{k.replace('/', '_')}.schema.json"
        disk = json.loads(f.read_text()) if f.exists() else None
        if disk is None or {kk: vv for kk, vv in disk.items() if kk != "$schema"} != json.loads(json.dumps(s)):
            drift.append(k)
    ev["schema_drift"] = drift
    errs = {}
    base = json.loads((PKG / "deploy/config/base.json").read_text())
    for f in sorted((PKG / "deploy/config").glob("*.json")):
        d = json.loads(f.read_text())
        doc = d if "schema" in d else C.deep_merge(base, d)
        e = C.check(doc)
        if e:
            errs[f.name] = e
    ev["config_errors"] = errs
    st, tr, probs = build_status.build()
    ev["status_problems"] = probs
    cur = json.loads((PKG / "COMPONENT_STATUS.json").read_text())
    ev["status_drift"] = cur != json.loads(json.dumps(st))
    ev["components"] = st["components"]
    ev["bench"] = bench.run(bench_n)
    ev["waivers"] = json.loads((PKG / "docs/governance/WAIVERS.json").read_text())
    ev["approvals"] = json.loads((PKG / "docs/governance/APPROVALS.json").read_text())
    own = (PKG / "docs/governance/OWNERSHIP.md").read_text()
    ev["owners"] = [m.strip() for m in re.findall(r"^\| [^|]+ \| ([^|]+) \|", own, re.M) if m.strip() not in ("Name", "UNASSIGNED", "") and not set(m.strip()) <= set("-")]
    return ev


def _compile_check():
    buf = io.StringIO()
    ok = True
    for p in sorted(PKG.rglob("*.py")):
        try:
            compile(p.read_text(encoding="utf-8"), str(p), "exec")
        except SyntaxError as e:
            ok = False
            buf.write(f"{p}: {e}\n")
    return ok


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PKG / "evidence"))
    ap.add_argument("--bench-n", type=int, default=2000)
    a = ap.parse_args(argv)
    sys.path.insert(0, str(PKG / "tools"))
    ev = collect(a.bench_n)
    res = evaluate(ev)
    out = pathlib.Path(a.out)
    rel = out / "release"
    rel.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in PKG.rglob("*") if p.is_file() and "__pycache__" not in p.parts and out not in p.parents)
    (rel / "SHA256SUMS").write_text(digests(files))
    tree = hashlib.sha256((rel / "SHA256SUMS").read_bytes()).hexdigest()
    (rel / "sbom.json").write_text(json.dumps(ev["sbom"], indent=1, sort_keys=True) + "\n")
    (rel / "test_results.json").write_text(json.dumps(ev["tests"], indent=1) + "\n")
    (out / "bench.json").write_text(json.dumps(ev["bench"], indent=1) + "\n")
    res["evidence"] = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "package_version": (PKG / "VERSION").read_text().strip(),
        "source_tree_sha256": tree,
        "config_digests": {f.name: _cfg_digest(f) for f in sorted((PKG / "deploy/config").glob("*.json"))},
        "runtime": {"python": platform.python_version(), "implementation": platform.python_implementation(), "system": platform.system()},
        "tools": {"unittest": "stdlib", "sbom": "tools/sbom.py", "scanner": "tools/secret_scan.py"},
        "evidence_author": EVIDENCE_AUTHOR,
        "refs": ["release/SHA256SUMS", "release/sbom.json", "release/test_results.json", "bench.json"],
    }
    (out / "PK_GATE_RESULTS.json").write_text(json.dumps(res, indent=1) + "\n")
    print(f"gate: {res['verdict']} {res['gate_counts']}")
    for k in MANDATORY:
        print(f"  {k:24s} {res['gates'][k]['result']}")
    return 0 if res["verdict"] == "GO" else 3


def _cfg_digest(f):
    from inv55_secrets_integration.runtime.config import digest
    return digest(json.loads(f.read_text()))


if __name__ == "__main__":
    sys.exit(main())
