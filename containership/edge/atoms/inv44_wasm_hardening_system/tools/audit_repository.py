"""Repeatable local repository audit for INV-44 v4.3.0 (stdlib only)."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VERSION = "4.3.0"
EXCLUDED_DIRS = {"__pycache__", ".pytest_cache", "evidence", "build", "dist"}
REQUIRED_FILES = (
    "pyproject.toml", "LICENSING.md", "NOTICE", "DEPENDENCIES.md", ".github/workflows/ci.yml",
    "schemas/pk_wasm_hardening.v1.schema.json", "schemas/pk_wasm_instance.v1.schema.json",
    "COMPONENTS_STATUS.json", "MASTER_SOURCE_STATUS.json", "ops/OWNERS.md", "ops/RUNBOOK.md",
    "ops/ADR-0001-wasm-hardening.md", "ops/REQUIREMENTS.md", "ops/COMPATIBILITY.md", "ops/WAIVERS.json",
    "ops/alerts.yaml", "bench/perf_suite.py", "release_gate.py",
)


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if version != EXPECTED_VERSION:
        fail(f"VERSION is {version!r}, expected {EXPECTED_VERSION!r}")

    init_text = (ROOT / "__init__.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f'__version__ = "{EXPECTED_VERSION}"' not in init_text:
        fail("__init__.py version mismatch")
    if f"**Version:** {EXPECTED_VERSION}" not in readme:
        fail("README version mismatch")
    if f"## {EXPECTED_VERSION} - " not in changelog:
        fail("CHANGELOG version entry missing")

    checklist = json.loads((ROOT / "CHECKLIST.json").read_text(encoding="utf-8"))
    items = checklist.get("items", [])
    if checklist.get("item_count") != 100 or len(items) != 100:
        fail("CHECKLIST.json must contain exactly 100 items")
    if [item.get("ordinal") for item in items] != list(range(1, 101)):
        fail("checklist ordinals are not 1..100")
    if len({item.get("check_id") for item in items}) != 100:
        fail("checklist IDs are not unique")

    matrix = json.loads((ROOT / "POST_AUDIT_MATRIX.json").read_text(encoding="utf-8"))
    rows = matrix.get("requirements", [])
    if len(rows) != 100:
        fail("post-audit matrix does not cover all 100 checklist items")
    if matrix.get("version") != EXPECTED_VERSION:
        fail("post-audit matrix version mismatch")

    manifest_path = ROOT / "CHECKSUMS.sha256"
    if not manifest_path.is_file():
        fail("CHECKSUMS.sha256 is missing")
    listed: dict[str, str] = {}
    for raw in manifest_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        digest, rel = raw.split("  ", 1)
        listed[rel] = digest
    actual = {
        p.relative_to(ROOT).as_posix()
        for p in ROOT.rglob("*")
        if p.is_file()
        and p.name != "CHECKSUMS.sha256"
        and not EXCLUDED_DIRS & set(p.relative_to(ROOT).parts)
        and not any(part.endswith(".egg-info") for part in p.relative_to(ROOT).parts)
        and p.suffix != ".pyc"
    }
    if set(listed) != actual:
        missing = sorted(actual - set(listed))
        stale = sorted(set(listed) - actual)
        fail(f"checksum manifest file set mismatch; unlisted={missing}, stale={stale}")
    for rel, expected in listed.items():
        got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        if got != expected:
            fail(f"checksum mismatch for {rel}")

    for rel in REQUIRED_FILES:
        if not (ROOT / rel).is_file():
            fail(f"required v{EXPECTED_VERSION} artifact missing: {rel}")
    status = json.loads((ROOT / "COMPONENTS_STATUS.json").read_text(encoding="utf-8"))
    comps = status.get("components", [])
    if [c.get("id") for c in comps] != list(range(1, 20)):
        fail("COMPONENTS_STATUS.json must list components 1..19 in order")
    if any(c.get("status") not in status["status_vocabulary"] for c in comps):
        fail("component status outside the declared vocabulary")
    for c in comps:
        if c["status"] == "COMPLETE":
            fail(f"component {c['id']} claims COMPLETE; this script cannot verify external evidence")
    counts = {k: sum(r["status"] == k for r in rows) for k in ("verified", "partial", "missing")}
    if counts != matrix.get("summary"):
        fail(f"matrix summary {matrix.get('summary')} disagrees with rows {counts}")

    py_files = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.glob("*.py"))
    for rel in py_files:
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"), filename=rel)
        bare_asserts = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
        if bare_asserts:
            fail(f"{rel} contains optimizer-strippable assert statements at {bare_asserts}")

    tests = subprocess.run(
        [sys.executable, "-B", str(ROOT / "tests" / "run_all.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if tests.returncode:
        sys.stderr.write(tests.stdout)
        sys.stderr.write(tests.stderr)
        fail("local test suite failed")

    summary = matrix["summary"]
    print(
        "PASS: local structural/security audit; "
        f"post-audit evidence = {summary['verified']} verified, "
        f"{summary['partial']} partial, {summary['missing']} missing"
    )
    print("COMPONENTS: " + ", ".join(f"{k}={sum(c['status'] == k for c in comps)}"
                                     for k in status["status_vocabulary"]))
    print("NOTE: this is the repository-local audit; the production exit gate is release_gate.py (NO_GO until pk_core + human approval).")
    print("NOTE: pk_core is external to the supplied archive; its estate-level gate is not run by this script.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
