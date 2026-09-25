"""Dependency and vulnerability-scan lane (MC-033, MC-082).

1. Runtime and tools import only the standard library (plus vendored pk_core in component/contract/pk_gate).
2. Vendored pk_core files match _vendor/PK_CORE_PROVENANCE.json digests exactly.
3. pyproject declares no runtime dependencies; requirements.lock pins match the CI optional-linter pins.
4. Vulnerability scan: with zero third-party runtime packages there is nothing for pip-audit/OSV to match;
   the lane records that fact (``third_party_runtime_packages: 0``) instead of claiming a clean scan of
   something it did not scan.  The CPython interpreter itself is out of this lane's scope.
"""
from __future__ import annotations

import ast
import hashlib
import re
import sys

from ._common import EVIDENCE, ROOT, py_files, read_json, write_json  # noqa: F401  (py_files re-exported for tests)

PK_ALLOWED = {"__init__.py", "component.py", "contract.py", "tools/pk_gate.py", "tests/test_component.py"}


def check() -> dict:
    std = set(sys.stdlib_module_names)
    third, errs = set(), []
    for rel, p in py_files():
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                mods = [node.module or ""]
            else:
                continue
            for m in mods:
                top = m.split(".")[0]
                if top in std or top in ("inv28_unikernel_implementations", "harness", "run_all") or top.startswith("test_"):
                    continue
                if top == "pk_core":
                    if rel not in PK_ALLOWED:
                        errs.append(f"{rel}: pk_core import outside allowed modules")
                    continue
                third.add(top)
                errs.append(f"{rel}: third-party import {m}")
    prov = read_json(ROOT / "_vendor" / "PK_CORE_PROVENANCE.json")
    for f, h in prov["files_sha256"].items():
        actual = hashlib.sha256((ROOT / "_vendor" / "pk_core" / f).read_bytes()).hexdigest()
        if actual != h:
            errs.append(f"vendored pk_core/{f} digest mismatch")
    extra = {p.name for p in (ROOT / "_vendor" / "pk_core").glob("*.py")} - set(prov["files_sha256"])
    if extra:
        errs.append(f"unpinned vendored files {sorted(extra)}")
    pp = (ROOT / "pyproject.toml").read_text()
    if not re.search(r"^dependencies = \[\]", pp, flags=re.M):
        errs.append("pyproject declares runtime dependencies")
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    lock = (ROOT / "requirements.lock").read_text()
    for pin in re.findall(r"(ruff==[\d.]+|mypy==[\d.]+)", ci):
        if pin not in lock:
            errs.append(f"CI pin {pin} missing from requirements.lock")
    return {"schema": "PK_DEPS/1", "tool": "tools/deps_check.py", "third_party_runtime_packages": len(third),
            "vendored": {"pk_core": {"files": len(prov["files_sha256"]), "digests_verified": not any("digest" in e for e in errs)}},
            "vulnerability_scan": {"scanner": "n/a", "reason": "no third-party runtime packages to scan",
                                   "packages_scanned": 0},
            "errors": errs, "pass": not errs}


def main(argv=None) -> int:
    r = check()
    write_json(EVIDENCE / "DEPS.json", r)
    for e in r["errors"]:
        print("DEPS", e)
    print("DEPS", "PASS" if r["pass"] else "FAIL")
    return 0 if r["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
