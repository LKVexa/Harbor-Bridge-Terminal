"""Stdlib lint/format gate (MC-086).  Always runs; ruff (pyproject.toml) is the optional stricter lane.

Rules: file compiles; no tabs; no trailing whitespace; LF endings; final newline; lines <= 140 chars
(contract.py exempt: generated contract prose carried over from the PK series); no bare ``except:``;
no ``print(`` in runtime modules (cli.py and tools excepted); no wildcard imports.
"""
from __future__ import annotations

import ast
import sys

from ._common import EVIDENCE, RUNTIME_MODULES, py_files, write_json

MAX_LINE = 140


def lint() -> list[str]:
    errs = []
    for rel, p in py_files():
        raw = p.read_bytes()
        text = raw.decode("utf-8")
        if b"\r\n" in raw:
            errs.append(f"{rel}: CRLF line endings")
        if text and not text.endswith("\n"):
            errs.append(f"{rel}: no final newline")
        for n, line in enumerate(text.splitlines(), 1):
            if "\t" in line:
                errs.append(f"{rel}:{n}: tab")
            if line != line.rstrip():
                errs.append(f"{rel}:{n}: trailing whitespace")
            if len(line) > MAX_LINE and rel != "contract.py":
                errs.append(f"{rel}:{n}: line > {MAX_LINE} chars ({len(line)})")
        try:
            tree = ast.parse(text, filename=rel)
        except SyntaxError as exc:
            errs.append(f"{rel}: syntax error {exc}")
            continue
        runtime = rel.removesuffix(".py") in RUNTIME_MODULES
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                errs.append(f"{rel}:{node.lineno}: bare except")
            if isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names):
                errs.append(f"{rel}:{node.lineno}: wildcard import")
            if runtime and isinstance(node, ast.Call) and getattr(node.func, "id", "") == "print":
                errs.append(f"{rel}:{node.lineno}: print() in runtime module")
    return errs


def main(argv=None) -> int:
    errs = lint()
    write_json(EVIDENCE / "LINT.json", {"schema": "PK_LINT/1", "tool": "tools/lint.py", "findings": errs,
                                        "pass": not errs})
    for e in errs[:50]:
        print("LINT", e)
    print("LINT", "PASS" if not errs else f"FAIL ({len(errs)})")
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
