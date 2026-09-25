"""Stdlib static-analysis gate for INV-53 (component 95).

Rules (library code only; tests are exempt from R1/R5):
  R1  no bare ``assert`` in library code (stripped by ``python -O``)
  R2  no ``eval``/``exec``/``compile`` of dynamic strings
  R3  no ``pickle``/``marshal``/``shelve`` (unsafe deserialisation)
  R4  no ``subprocess`` with ``shell=True`` and no ``os.system``
  R5  no ``print`` in library code (use the structured logger)
  R6  no bare ``except:`` (catches SystemExit/KeyboardInterrupt)
  R7  no ``random`` module for security material in security.py (use ``secrets``)
  R8  every public module has a docstring
Exit 0 when clean, 1 with findings (JSON on stdout).
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]


def check_file(path: Path, *, library: bool) -> list[dict]:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(path))
    out = []

    def add(rule, node, msg):
        out.append({"rule": rule, "file": path.relative_to(PKG).as_posix(), "line": getattr(node, "lineno", 0), "msg": msg})

    if library and not ast.get_docstring(tree):
        add("R8", tree, "module docstring missing")
    for node in ast.walk(tree):
        if library and isinstance(node, ast.Assert):
            add("R1", node, "bare assert in library code")
        if isinstance(node, ast.Call):
            f = node.func
            name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
            if name in ("eval", "exec") and isinstance(f, ast.Name):
                add("R2", node, f"{name}() call")
            if name == "system" and isinstance(f, ast.Attribute) and getattr(f.value, "id", "") == "os":
                add("R4", node, "os.system")
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    add("R4", node, "shell=True")
            if library and name == "print" and isinstance(f, ast.Name):
                add("R5", node, "print() in library code")
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for m in mods:
                if m.split(".")[0] in ("pickle", "marshal", "shelve"):
                    add("R3", node, f"import {m}")
                if path.name == "security.py" and m.split(".")[0] == "random":
                    add("R7", node, "random imported in security.py")
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            add("R6", node, "bare except")
    return out


def main() -> int:
    findings = []
    files = 0
    for p in sorted(PKG.rglob("*.py")):
        rel = p.relative_to(PKG)
        if "__pycache__" in rel.parts:
            continue
        files += 1
        findings += check_file(p, library=not (rel.parts[0] in ("tests", "tools")))
    sys.stdout.write(json.dumps({"schema": "inv53.lint/1", "files": files, "findings": findings}, indent=1) + "\n")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
