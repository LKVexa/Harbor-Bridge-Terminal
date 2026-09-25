"""Shared helpers for INV-28 tools: paths, runtime-module list, JSON I/O."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
PKG = ROOT.name
EVIDENCE = ROOT / "evidence"
CACHE_DIRS = {"__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache"}
RUNTIME_MODULES = ("advisories", "binding", "certification", "errors", "explain", "model", "observability", "policy",
                   "registry", "rollout", "schema_check", "selection", "service", "trust")


def ensure_path() -> None:
    for p in (str(PARENT), str(ROOT / "_vendor")):
        if p not in sys.path:
            sys.path.insert(0, p)
    sys.dont_write_bytecode = True


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def py_files(include_tests=True, include_tools=True):
    for p in sorted(ROOT.rglob("*.py")):
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith("_vendor/") or "__pycache__" in rel:
            continue
        if not include_tests and rel.startswith("tests/"):
            continue
        if not include_tools and rel.startswith("tools/"):
            continue
        yield rel, p
