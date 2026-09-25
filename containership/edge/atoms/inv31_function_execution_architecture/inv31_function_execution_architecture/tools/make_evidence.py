"""Build machine-readable evidence for INV-31 4.3.0 (A05, C090, C100).

Runs each check as a real subprocess, records argv/exit/output digest, hashes
every shipped file, writes a hash-chained evidence ledger and evaluates the
production gate mechanically.  The gate can only read GO when pk_core is
available and pinned, and an owner and independent approver are recorded;
none of those exist, so it reads NO_GO and names why.
"""
from __future__ import annotations

import hashlib, json, pathlib, platform, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "tools"))
from status_table import ITEMS  # noqa: E402

EV = HERE / "evidence"
EXCLUDE_DIRS = {"__pycache__", ".git", "evidence"}


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(argv, cwd=ROOT):
    r = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    out = (r.stdout + r.stderr)
    tail = out.strip().splitlines()[-3:]
    return {"argv": [a.replace(str(ROOT), "<root>") for a in argv], "exit": r.returncode,
            "output_sha256": hashlib.sha256(out.encode()).hexdigest(), "tail": tail}


def main(preflight: bool = False) -> int:
    EV.mkdir(exist_ok=True)
    py = sys.executable
    pkg = HERE.name
    checks = {} if preflight else {
        "unit_runtime": run([py, "-B", f"{pkg}/tests/test_component.py"]),
        "unit_runtime_optimised": run([py, "-B", "-O", f"{pkg}/tests/test_component.py"]),
        "unit_remediation": run([py, "-B", f"{pkg}/tests/test_remediation.py"]),
        "unit_remediation_optimised": run([py, "-B", "-O", f"{pkg}/tests/test_remediation.py"]),
        "compileall": run([py, "-c", f"import compileall,sys; sys.exit(0 if compileall.compile_dir('{pkg}', quiet=1, legacy=False, optimize=0, workers=1, force=True, ddir=None, rx=None) else 1)"]),
        "json_parse": run([py, "-c", f"import json,pathlib; [json.loads(p.read_text()) for p in pathlib.Path('{pkg}').rglob('*.json') if 'evidence' not in p.parts]"]),
    }
    # compileall writes __pycache__; remove it so shipped hashes stay clean
    for d in HERE.rglob("__pycache__"):
        for f in d.iterdir():
            f.unlink()
        d.rmdir()
    # jsonschema lane: validate fixtures against schemas only when jsonschema is present
    try:
        if preflight:
            raise ModuleNotFoundError
        import jsonschema  # noqa: F401
        lane = run([py, "-B", "-c", (
            "import json,pathlib,jsonschema;"
            f"P=pathlib.Path('{pkg}');fx=json.loads((P/'fixtures/conformance_fixtures.json').read_text());"
            "req=json.loads((P/'schemas/PK_INVOKE_REQUEST_1.schema.json').read_text());"
            "cfg=json.loads((P/'schemas/PK_INV31_CONFIG_1.schema.json').read_text());"
            "[jsonschema.validate(r,req) for r in fx['request_valid']];"
            "bad=[r for r in fx['request_invalid'] if jsonschema.Draft202012Validator(req).is_valid(r)];"
            "assert not bad, bad;"
            "[jsonschema.validate(json.loads(p.read_text()),cfg) for p in (P/'config').glob('*.json')];"
            "assert not [d for d in fx['config_invalid'] if jsonschema.Draft202012Validator(cfg).is_valid(d)]")])
    except ModuleNotFoundError:
        lane = {"argv": [], "exit": None, "status": "NOT_RUN", "reason": "jsonschema not installed"}
    checks["schema_fixture_validation"] = lane
    bench_out = EV / "bench.json"
    if not preflight:
      checks["bench_quick"] = run([py, "-B", f"{pkg}/tools/bench.py", "--quick", "--check",
                                 "--out", str(bench_out)])

    sys.path.insert(0, str(ROOT))
    from importlib import import_module
    pk = import_module(pkg)
    status = pk.PK_CORE_STATUS

    files = sorted(p for p in HERE.rglob("*") if p.is_file()
                   and not EXCLUDE_DIRS & set(p.relative_to(HERE).parts))
    manifest = {str(p.relative_to(HERE)).replace("\\", "/"): sha(p) for p in files}
    (EV / "MANIFEST.sha256.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    subject = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()

    upload_dir = pathlib.Path(__import__("os").environ.get("INV31_CHECKLIST_DIR", "/nonexistent"))
    cl = next(upload_dir.glob("*COMPREHENSIVE_MISSING_COMPONENT_CHECKLIST.md"), None) if upload_dir.exists() else None
    (EV / "source_hashes.json").write_text(json.dumps({
        "MASTER.md": {"status": "ABSENT", "sha256": None,
                      "note": "not supplied; not reconstructed (A02)"},
        "CHECKLIST.json": {"status": "PRESENT", "sha256": manifest["CHECKLIST.json"]},
        "POST_AUDIT.json": {"status": "PRESENT_UNMODIFIED_FROM_4.2.0", "sha256": manifest["POST_AUDIT.json"]},
        "remediation_checklist": {"status": "PRESENT" if cl else "RECORDED_BY_BUILDER",
                                  "sha256": sha(cl) if cl else
                                  None
                                  },
    }, indent=2))
    (EV / "sbom.json").write_text(json.dumps({
        "schema": "PK_INV31_SBOM/1", "component": "inv31-function-execution-architecture",
        "version": pk.__version__, "runtime_dependencies": [],
        "optional": [{"name": "pk_core", "version": status["version"], "pinned": status["pinned_version"],
                      "status": "UNPINNED"}],
        "stdlib_only": True}, indent=2))

    items = []
    for iid, title, st, evidence, blockers, note in ITEMS:
        missing_ev = [e for e in evidence if not e.startswith("tests/") and "::" not in e and "#" not in e
                      and "*" not in e and " " not in e and not (HERE / e).exists()]
        items.append({"_missing": missing_ev, "id": iid, "title": title, "status": st, "evidence": evidence,
                      "blockers": blockers, "note": note})
    counts = {}
    for i in items:
        counts[i["status"]] = counts.get(i["status"], 0) + 1
    tests_ok = bool(checks) and all(c.get("exit") == 0 for k, c in checks.items() if k.startswith("unit_") or k in ("compileall", "json_parse"))
    gate_reasons = []
    if not tests_ok:
        gate_reasons.append("local checks failing")
    if not (status["available"] and status["compatible"] and status["pin_satisfied"]):
        gate_reasons.append("pk_core 100-item gate not run (A01)")
    gate_reasons.append("no accountable owner or independent approver recorded (C009, C100)")
    blocked = [i["id"] for i in items if i["status"] == "BLOCKED"]
    gate_reasons.append(f"{len(blocked)} items BLOCKED: {', '.join(blocked)}")
    report = {
        "schema": "PK_INV31_REMEDIATION/1", "element": "INV-31", "version": pk.__version__,
        "subject_sha256": subject, "counts": counts, "total": len(items),
        "local_checks_pass": tests_ok, "pk_core": status,
        "production_gate": "NO_GO", "gate_reasons": gate_reasons,
        "independent_review": "UNASSIGNED", "items": items,
    }
    (HERE / "REMEDIATION_STATUS.json").write_text(json.dumps(report, indent=1))

    run_rec = {"schema": "PK_INV31_CI_RUN/1", "interpreter": f"{platform.python_implementation()} "
               f"{platform.python_version()}", "machine": platform.machine(), "subject_sha256": subject,
               "checks": checks}
    (EV / "ci_run.json").write_text(json.dumps(run_rec, indent=1))
    # hash-chained ledger over the evidence records
    prev, chain = "0" * 64, []
    for name in ("ci_run.json", "bench.json", "sbom.json", "source_hashes.json", "MANIFEST.sha256.json"):
        h = hashlib.sha256((prev + sha(EV / name)).encode()).hexdigest()
        chain.append({"record": name, "sha256": sha(EV / name), "prev": prev, "chain": h})
        prev = h
    bad = {i["id"]: i["_missing"] for i in items if [m for m in i["_missing"] if not (HERE / m).exists()]}
    if bad:
        raise SystemExit(f"cited evidence does not exist: {bad}")
    for i in items:
        i.pop("_missing")
    report["items"] = items
    (HERE / "REMEDIATION_STATUS.json").write_text(json.dumps(report, indent=1))
    (EV / "evidence_chain.json").write_text(json.dumps({"head": prev, "entries": chain}, indent=1))
    print(json.dumps({"counts": counts, "local_checks_pass": tests_ok, "gate": "NO_GO",
                      "checks": {k: v.get("exit") for k, v in checks.items()}}, indent=1))
    return 0 if tests_ok else 1


if __name__ == "__main__":
    # Preflight writes the status/provenance files the source-tree tests read,
    # then the real pass runs every check and rewrites them with results.
    if not (EV / "bench.json").exists():
        (EV).mkdir(exist_ok=True)
        (EV / "bench.json").write_text("{}")
    main(preflight=True)
    sys.exit(main())
