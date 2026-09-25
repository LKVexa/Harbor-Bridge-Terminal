"""Standalone structural audit for the PLN-03 component archive."""
from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
REQUIRED_RUNTIME_METHODS = {
    "state_get", "state_set", "state_delete", "state_transact",
    "publish", "subscribe", "secret_fetch", "invoke",
}


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    init_text = (ROOT / "__init__.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    component_test = (ROOT / "tests" / "test_component.py").read_text(encoding="utf-8")
    check(f'__version__ = "{version}"' in init_text, "__init__.py version drift", failures)
    check(f'**Version:** {version}' in readme, "README version drift", failures)
    check(version in component_test, "conformance test version drift", failures)

    checklist = json.loads((ROOT / "CHECKLIST.json").read_text(encoding="utf-8"))
    items = checklist.get("items", [])
    ids = [item.get("check_id") for item in items]
    ordinals = [item.get("ordinal") for item in items]
    check(len(items) == 100, f"expected 100 checklist items, found {len(items)}", failures)
    check(len(set(ids)) == 100, "checklist IDs are not unique", failures)
    check(ordinals == list(range(1, 101)), "checklist ordinals are not contiguous 1..100", failures)

    runtime_tree = ast.parse((ROOT / "runtime.py").read_text(encoding="utf-8"), filename="runtime.py")
    runtime_class = next((n for n in runtime_tree.body if isinstance(n, ast.ClassDef) and n.name == "DistributedRuntime"), None)
    methods = {n.name for n in runtime_class.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))} if runtime_class else set()
    missing_methods = sorted(REQUIRED_RUNTIME_METHODS - methods)
    check(not missing_methods, f"runtime API methods missing: {missing_methods}", failures)

    for name in sorted(p.name for p in ROOT.glob("*.py")):
        tree = ast.parse((ROOT / name).read_text(encoding="utf-8"), filename=name)
        bare_asserts = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
        check(not bare_asserts, f"{name} contains optimiser-strippable assert statements at {bare_asserts}", failures)

    check((ROOT / "MISSING_COMPONENTS.md").is_file(), "MISSING_COMPONENTS.md missing", failures)
    check((ROOT / "AUDIT_REPORT.md").is_file(), "AUDIT_REPORT.md missing", failures)
    if re.search(r"`MASTER\.md`.*(?:included|carried verbatim|present)", readme, re.I):
        failures.append("README still claims missing MASTER.md is included")

    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-t", "tests"],
        cwd=ROOT, capture_output=True, text=True, env={**__import__("os").environ, "PK_SOAK_OPS": "1000"},
    )
    test_tail = (proc.stderr.strip() or proc.stdout.strip()).splitlines()[-3:]
    check(proc.returncode == 0, "standalone test suites failed: " + " | ".join(test_tail), failures)

    # --- 4.3.0 remediation audit (MC-001..MC-056) ------------------------------------------------
    release_blockers: list[str] = []
    status_path = ROOT / "REMEDIATION_STATUS.json"
    remediation: dict[str, int] = {}
    if not status_path.is_file():
        failures.append("REMEDIATION_STATUS.json missing")
    else:
        status = json.loads(status_path.read_text(encoding="utf-8"))
        mc_ids = {m["id"] for m in json.loads((ROOT / "MISSING_COMPONENTS.json").read_text())["components"]}
        seen = {i["id"] for i in status["items"]}
        check(seen == mc_ids, f"remediation status does not cover findings: {sorted(mc_ids ^ seen)}", failures)
        for item in status["items"]:
            remediation[item["status"]] = remediation.get(item["status"], 0) + 1
            for art in item["artifacts"]:
                check((ROOT / art).exists(), f"{item['id']} artifact missing: {art}", failures)
            if item["status"] == "IMPLEMENTED":
                check(bool(item["tests"]), f"{item['id']} marked IMPLEMENTED without a linked test", failures)
            if item["status"] != "IMPLEMENTED":
                release_blockers.append(f"{item['id']} {item['status']}: {item['open']}")
    owners = (ROOT / "OWNERS.yaml").read_text(encoding="utf-8") if (ROOT / "OWNERS.yaml").is_file() else ""
    check(bool(owners), "OWNERS.yaml missing", failures)
    unresolved = owners.count("resolved: false")
    if unresolved:
        release_blockers.insert(0, f"OWNERS.yaml has {unresolved} unresolved role/boundary principals")
    for adr in sorted((ROOT / "docs" / "adr").glob("ADR-*.md")):
        if "**Status:** Proposed" in adr.read_text(encoding="utf-8"):
            release_blockers.append(f"{adr.name} not yet approved")
    for tool in ("tools/traceability.py", "tools/sbom.py", "tools/bench.py", "tools/release_evidence.py"):
        check((ROOT / tool).is_file(), f"{tool} missing", failures)
    trace = json.loads((ROOT / "TRACEABILITY.json").read_text()) if (ROOT / "TRACEABILITY.json").is_file() else {}
    check(len(trace.get("checklist", [])) == 100, "TRACEABILITY.json must map all 100 checklist items", failures)
    if not (ROOT / "LICENSE").is_file():
        release_blockers.append("LICENSE not selected (MC-056)")

    if importlib.util.find_spec("pk_core") is None:
        warnings.append("pk_core is not installed/vendored; 100-item conformance execution cannot be verified in this archive alone")
    if not (ROOT / "MASTER.md").exists():
        warnings.append("MASTER.md is absent; README now records this instead of claiming it is packaged")

    print(json.dumps({
        "version": version,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "warnings": warnings,
        "runtime_methods": sorted(methods & REQUIRED_RUNTIME_METHODS),
        "checklist_items": len(items),
        "remediation": remediation,
        "release_ready": not failures and not release_blockers,
        "release_blockers": release_blockers,
    }, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
