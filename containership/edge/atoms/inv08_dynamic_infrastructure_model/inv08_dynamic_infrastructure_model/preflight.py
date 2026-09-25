"""Deterministic local preflight for INV-08.

Exit 0 means package-local structural checks passed.  By default, absence of
``pk_core`` is a failure because full conformance cannot run.  Use
``--allow-missing-pk-core`` only for standalone model development.
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
REQUIRED = {
    "VERSION",
    "README.md",
    "CHANGELOG.md",
    "CHECKLIST.json",
    "__init__.py",
    "metadata.py",
    "model.py",
    "component.py",
    "contract.py",
    "tests/test_component.py",
    "AUDIT_REPORT.md",
    "MISSING_COMPONENTS.md",
}


def check(allow_missing_pk_core: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    missing = sorted(name for name in REQUIRED if not (ROOT / name).exists())
    if missing:
        errors.append("missing required files: " + ", ".join(missing))

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    init_text = (ROOT / "__init__.py").read_text(encoding="utf-8")
    if f'__version__ = "{version}"' not in init_text:
        errors.append("VERSION and __version__ do not agree")

    checklist = json.loads((ROOT / "CHECKLIST.json").read_text(encoding="utf-8"))
    items = checklist.get("items", [])
    if checklist.get("item_count") != 100 or len(items) != 100:
        errors.append("CHECKLIST.json must declare and contain exactly 100 items")
    ids = [item.get("check_id") for item in items]
    if len(set(ids)) != len(ids):
        errors.append("CHECKLIST.json contains duplicate check_id values")

    for path in sorted(ROOT.rglob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors.append(f"syntax error in {path.relative_to(ROOT)}: {exc}")

    if importlib.util.find_spec("pk_core") is None:
        message = "pk_core is not importable; full 100-item conformance was not executed"
        if allow_missing_pk_core:
            warnings.append(message)
        else:
            errors.append(message)

    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-missing-pk-core", action="store_true")
    args = parser.parse_args(argv)
    errors, warnings = check(args.allow_missing_pk_core)
    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"FAIL: {error}")
    if errors:
        return 2
    print("PASS: INV-08 package-local preflight")
    return 0


if __name__ == "__main__":
    sys.exit(main())
