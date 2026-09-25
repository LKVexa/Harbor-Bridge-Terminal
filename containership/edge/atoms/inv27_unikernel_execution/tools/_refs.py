"""Shared helpers: resolve ``path`` / ``path::Symbol`` / ``path::Class.method`` references against the tree."""
from __future__ import annotations

import ast
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=None)
def symbols(path: str) -> frozenset:
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    out = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(node.name)
            if isinstance(node, ast.ClassDef):
                out.update(f"{node.name}.{s.name}" for s in node.body if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            for t in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                if isinstance(t, ast.Name):
                    out.add(t.id)
    return frozenset(out)


def resolve(ref: str) -> str | None:
    """None when ``ref`` resolves, else the reason."""
    file, _, sym = ref.partition("::")
    if not (ROOT / file).exists():
        return f"missing path {file}"
    if sym:
        if not file.endswith(".py"):
            return f"symbol on non-python file {file}"
        if sym not in symbols(file):
            return f"missing symbol {sym} in {file}"
    return None


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))
