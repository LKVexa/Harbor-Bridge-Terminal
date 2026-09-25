"""Stdlib-only reproducible audit for the INV-71 repository."""
from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import py_compile
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent


def result(name: str, status: str, detail: str) -> dict[str, str]:
    return {"check": name, "status": status, "detail": detail}


def main() -> int:
    checks: list[dict[str, str]] = []

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    tree = ast.parse((ROOT / "__init__.py").read_text(encoding="utf-8"))
    init_version = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets):
            if isinstance(node.value, ast.Constant):
                init_version = node.value.value
    checks.append(result("version_coherence", "PASS" if version == init_version else "FAIL", f"VERSION={version}; __version__={init_version}"))

    compile_errors = []
    for path in ROOT.rglob("*.py"):
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:  # pragma: no cover - audit path
            compile_errors.append(f"{path.relative_to(ROOT)}: {exc}")
    checks.append(result("python_compile", "PASS" if not compile_errors else "FAIL", "; ".join(compile_errors) or "all Python files compile"))

    json_errors = []
    for path in [ROOT / "CHECKLIST.json", *sorted((ROOT / "schemas").glob("*.json"))]:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            json_errors.append(f"{path.relative_to(ROOT)}: {exc}")
    checks.append(result("json_parse", "PASS" if not json_errors else "FAIL", "; ".join(json_errors) or "checklist and schemas parse"))

    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-p", "test_*.py"],
        cwd=str(PARENT), capture_output=True, text=True,
    )
    checks.append(result("unit_tests", "PASS" if proc.returncode == 0 else "FAIL", (proc.stdout + proc.stderr).strip()[-4000:]))

    pk_core = importlib.util.find_spec("pk_core")
    checks.append(result(
        "pk_core_available",
        "PASS" if pk_core is not None else "WARN",
        "pk_core import is available" if pk_core is not None else "external pk_core package is not present; integration/gate tests cannot be executed here",
    ))

    required = [
        "README.md", "CHANGELOG.md", "VERSION", "CHECKLIST.json", "sandbox.py",
        "docs/ADR-0001-heavy-agent-sandbox.md", "docs/THREAT_MODEL.md",
        "AUDIT_REPORT.md", "AUDIT_AFTER.json", "MISSING_COMPONENTS.md",
    ]
    absent = [p for p in required if not (ROOT / p).exists()]
    checks.append(result("audit_artifacts", "PASS" if not absent else "FAIL", "missing: " + ", ".join(absent) if absent else "required audit artifacts present"))

    report = {"element": "INV-71", "version": version, "checks": checks}
    out = ROOT / "REPO_AUDIT_RESULTS.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if any(c["status"] == "FAIL" for c in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
