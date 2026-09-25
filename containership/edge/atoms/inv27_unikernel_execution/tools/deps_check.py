"""Dependency check (MC-022, MC-089): every runtime import is stdlib, package-internal, or a declared
optional import guarded by ImportError (cryptography in trust/signing.py and sealed_store.py)."""
from __future__ import annotations

import ast
import sys

from ._refs import ROOT

OPTIONAL = {"cryptography"}
ALLOWED_PKCORE = {"component.py", "contract.py"}   # pk_core integration, loaded lazily


def runtime_modules() -> list[str]:
    import tomllib
    return tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["inv27"]["lint"]["runtime_modules"]


def check() -> list[str]:
    errs = []
    std = set(sys.stdlib_module_names)
    for rel in runtime_modules() + sorted(ALLOWED_PKCORE):
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            for n in names:
                top = n.split(".")[0]
                if top in std or top == "__future__":
                    continue
                if top == "pk_core" and rel in ALLOWED_PKCORE:
                    continue
                if top in OPTIONAL:
                    continue
                errs.append(f"{rel}: non-stdlib import {n}")
    return errs


def main(argv=None) -> int:
    errs = check()
    for e in errs:
        print("FAIL", e)
    print("DEPS", "PASS" if not errs else "FAIL")
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
