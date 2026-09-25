"""Traceability, release inventory and production exit gate (MC-29, MC-50, MC-53, MC-64).

``build_bundle`` writes a self-describing evidence directory:
  traceability.json  – all 100 INV-22 controls → work packages → code/tests/status
  inventory.json     – every shipped file with sha256 + declared dependencies
  preflight.json     – dependency/baseline/crypto status
  tests.json         – unittest results (counts, skips, failures)
  gate.json          – GO / NO_GO with every blocking reason
  MANIFEST.json      – digest of each evidence file (bundle integrity)
The gate consumes these artifacts; it never relies on manual assertions.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import time

from . import __version__, canonical, preflight

PKG = pathlib.Path(__file__).resolve().parent
_EXCLUDE_DIRS = {"__pycache__", "evidence", ".pytest_cache", "build", "dist", ".git"}


def _json(rel: str):
    return json.loads((PKG / rel).read_text(encoding="utf-8"))


def _expand(spec: str) -> list[str]:
    out = []
    for part in re.split(r",\s*", spec.strip()):
        m = re.fullmatch(r"C(\d{3})\s*[–-]\s*C(\d{3})", part)
        if m:
            out += [f"C{i:03d}" for i in range(int(m.group(1)), int(m.group(2)) + 1)]
        elif re.fullmatch(r"C\d{3}", part):
            out.append(part)
    return out


def mc_to_controls() -> dict[str, list[str]]:
    text = (PKG / "docs/REMEDIATION_CHECKLIST.md").read_text(encoding="utf-8")
    mapping, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"^## (MC-\d{2})", line)
        if m:
            cur = m.group(1)
        m = re.match(r"^\*\*Related INV-22 controls:\*\*\s*(.+?)\s*$", line)
        if m and cur:
            mapping[cur] = _expand(m.group(1))
    return mapping


_RANK = {"implemented": 3, "partial": 2, "owner_decision": 1, "blocked_external": 0}


def traceability() -> dict:
    checklist = _json("CHECKLIST.json")
    rem = _json("data/remediation.json")["items"]
    mapping = mc_to_controls()
    rows = []
    for item in checklist["items"]:
        cid = item["check_id"].split("-")[-1]
        mcs = sorted(mc for mc, cs in mapping.items() if cid in cs)
        statuses = [rem[mc]["status"] for mc in mcs if mc in rem]
        rows.append({"control": item["check_id"], "dimension": item["dimension"], "requirement": item["requirement"],
                     "work_packages": mcs,
                     "implementation": sorted({p for mc in mcs for p in rem.get(mc, {}).get("implementation", [])})
                     or ["contract.py (v4.2.0 contract; not re-audited by this checklist)"],
                     "tests": sorted({p for mc in mcs for p in rem.get(mc, {}).get("tests", [])}),
                     "status": (min(statuses, key=lambda st: _RANK[st]) if statuses else "legacy_v4.2.0"),
                     "best_status": (max(statuses, key=lambda st: _RANK[st]) if statuses else "legacy_v4.2.0"),
                     "owner": "unassigned"})
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"schema": "PK_BRANCH_TRACE/1", "release": __version__, "controls": len(rows), "by_status": counts, "rows": rows}


def inventory() -> dict:
    files = []
    for p in sorted(PKG.rglob("*")):
        if p.is_file() and not (set(p.relative_to(PKG).parts) & _EXCLUDE_DIRS) and p.suffix not in (".pyc", ".sqlite3", ".db"):
            files.append({"path": p.relative_to(PKG).as_posix(), "sha256": canonical.file_digest(p), "bytes": p.stat().st_size})
    deps = []
    lock = PKG / "requirements.lock"
    if lock.exists():
        for line in lock.read_text().splitlines():
            m = re.match(r"^([A-Za-z0-9_.\-]+)==([^\s\\]+)", line)
            if m:
                deps.append({"name": m.group(1), "version": m.group(2)})
    return {"schema": "PK_BRANCH_INVENTORY/1", "component": "inv22_alternative_wasi_branch", "version": __version__,
            "files": files, "dependencies": deps + [{"name": "pk_core", "version": "UNPINNED (absent)"}],
            "tree_digest": canonical.digest([[f["path"], f["sha256"]] for f in files])}


def run_tests() -> dict:
    code = ("import sys, unittest, json; sys.path.insert(0, %r); sys.path.insert(0, %r);"
            "s=unittest.defaultTestLoader.discover(%r, pattern='test_*.py', top_level_dir=%r);"
            "r=unittest.TestResult(); s.run(r);"
            "print(json.dumps({'run': r.testsRun, 'failures': [str(t) for t,_ in r.failures],"
            "'errors': [str(t) for t,_ in r.errors], 'skipped': [[str(t), why] for t, why in r.skipped]}))"
            ) % (str(PKG.parent), str(PKG / "tests"), str(PKG / "tests"), str(PKG / "tests"))
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(PKG.parent), timeout=900)
    try:
        res = json.loads(out.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        res = {"run": 0, "failures": [], "errors": ["test runner crashed: " + out.stderr[-500:]], "skipped": []}
    res["ok"] = not res["failures"] and not res["errors"]
    return res


def gate(trace: dict, pre: dict, tests: dict) -> dict:
    reasons = []
    if not tests["ok"]:
        reasons.append(f"test failures/errors: {len(tests['failures']) + len(tests['errors'])}")
    if tests["skipped"]:
        reasons.append(f"{len(tests['skipped'])} skipped tests (full conformance requires zero skips)")
    for c in pre["checks"]:
        if not c["ok"]:
            reasons.append(f"preflight {c['check']} not ok")
    rem = _json("data/remediation.json")["items"]
    open_mcs = sorted(mc for mc, v in rem.items() if v["status"] != "implemented")
    if open_mcs:
        reasons.append(f"{len(open_mcs)} of {len(rem)} work packages not complete")
    not_done = [r["control"] for r in trace["rows"] if r["status"] != "implemented"]
    if not_done:
        reasons.append(f"{len(not_done)} of {trace['controls']} controls lack complete evidence")
    return {"schema": "PK_BRANCH_GATE/1", "release": __version__, "verdict": "GO" if not reasons else "NO_GO",
            "reasons": reasons, "open_work_packages": open_mcs}


def build_bundle(out_dir: str = "evidence", *, with_tests: bool = True) -> dict:
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    trace, inv, pre = traceability(), inventory(), preflight.run(strict=False)
    tests: dict = run_tests() if with_tests else {"run": 0, "failures": [], "errors": [], "skipped": [["not run", "with_tests=False"]],
                                                  "ok": True}
    g = gate(trace, pre, tests)
    docs = {"traceability.json": trace, "inventory.json": inv, "preflight.json": pre, "tests.json": tests, "gate.json": g}
    manifest = {"schema": "PK_BRANCH_EVIDENCE/1", "release": __version__, "generated_at": int(time.time()),
                "tree_digest": inv["tree_digest"], "files": {}}
    for name, doc in docs.items():
        data = json.dumps(doc, indent=2, sort_keys=True).encode("utf-8")
        (out / name).write_bytes(data)
        manifest["files"][name] = canonical.file_digest(out / name)
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return {"ok": g["verdict"] == "GO", "verdict": g["verdict"], "reasons": g["reasons"], "out_dir": str(out),
            "tests": {"run": tests["run"], "skipped": len(tests["skipped"]), "failed": len(tests["failures"]) + len(tests["errors"])},
            "controls": trace["by_status"]}


if __name__ == "__main__":
    print(json.dumps(build_bundle(sys.argv[1] if len(sys.argv) > 1 else "evidence"), indent=2))
