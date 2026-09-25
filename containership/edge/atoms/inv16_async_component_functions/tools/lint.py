"""Stdlib static checks: lint + security rules + annotation coverage (closures #32/#33 proxy).

Runs everywhere with zero third-party tools, so the gate is reproducible
offline.  ruff/mypy/bandit configurations are also shipped (pyproject.toml)
and run in CI where those tools are installable.

Exit 1 on any finding.  ``--json`` prints machine-readable results.
"""
from __future__ import annotations

import ast
import json
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
PROD = ["runtime.py", "bridge.py", "abi.py", "declare.py", "lowering.py", "observability.py", "preflight.py",
        "__init__.py"]
MAX_LINE = 120
BANNED_CALLS = {"eval", "exec", "compile", "__import__"}
BANNED_ATTRS = {("os", "system"), ("pickle", "loads"), ("pickle", "load"), ("marshal", "loads"),
                ("subprocess", "getoutput"), ("yaml", "load")}


def check_file(path: pathlib.Path, prod: bool) -> list[dict]:
    src = path.read_text()
    tree = ast.parse(src, str(path))
    out = []

    def f(node, rule, msg):
        out.append({"file": str(path.relative_to(PKG)), "line": getattr(node, "lineno", 0), "rule": rule, "msg": msg})

    for i, line in enumerate(src.splitlines(), 1):
        if len(line) > MAX_LINE:
            out.append({"file": str(path.relative_to(PKG)), "line": i, "rule": "E501", "msg": f"line > {MAX_LINE}"})
        if line.rstrip() != line:
            out.append({"file": str(path.relative_to(PKG)), "line": i, "rule": "W291", "msg": "trailing whitespace"})
    imported: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            f(node, "E722", "bare except")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for d in node.args.defaults + node.args.kw_defaults:
                if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                    f(node, "B006", f"mutable default in {node.name}")
            if prod and not node.name.startswith("_") and node.returns is None and node.name != "__init__":
                f(node, "ANN201", f"public function {node.name} lacks a return annotation")
        if prod and isinstance(node, ast.Assert):
            f(node, "S101", "assert in production code (stripped under -O)")
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id in BANNED_CALLS and (prod or fn.id != "compile"):
                f(node, "S307", f"banned call {fn.id}()")
            if (isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name)
                    and (fn.value.id, fn.attr) in BANNED_ATTRS):
                f(node, "S301", f"banned call {fn.value.id}.{fn.attr}()")
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    f(node, "S602", "subprocess with shell=True")
            if prod and isinstance(fn, ast.Name) and fn.id == "print" and path.name != "preflight.py":
                f(node, "T201", "print in library code")
        if isinstance(node, ast.Import):
            for a in node.names:
                imported[(a.asname or a.name).split(".")[0]] = node
        if isinstance(node, ast.ImportFrom) and node.module != "__future__":
            for a in node.names:
                imported[a.asname or a.name] = node
    if path.name != "__init__.py":
        used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | \
               {n.value.id for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}
        for name, node in imported.items():
            if name not in used and src.count(name) <= 1:
                f(node, "F401", f"unused import {name}")
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    files = [(PKG / p, True) for p in PROD]
    files += [(p, False) for p in sorted((PKG / "tests").glob("*.py"))]
    files += [(p, False) for p in sorted((PKG / "tools").glob("*.py")) + sorted((PKG / "bench").glob("*.py"))
              + sorted((PKG / "fixtures").glob("*.py"))]
    findings = []
    for p, prod in files:
        findings += check_file(p, prod)
    res = {"schema": "inv16.lint/1", "files": len(files), "findings": findings, "pass": not findings}
    if "--json" in argv:
        print(json.dumps(res, indent=2))
    else:
        for x in findings:
            print(f"{x['file']}:{x['line']}: {x['rule']} {x['msg']}")
        print(f"lint: {len(files)} files, {len(findings)} findings")
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
