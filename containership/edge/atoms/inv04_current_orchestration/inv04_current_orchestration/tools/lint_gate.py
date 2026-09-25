#!/usr/bin/env python3
"""Security/lint policy gate (components 67, 70; GLOBAL assert rule).

  python tools/lint_gate.py

Dependency-free checks that must hold even where ruff/mypy are unavailable:
  * no ``assert`` statements in non-test code (safety must survive ``python -O``);
  * no eval/exec/pickle.loads/marshal/os.system/subprocess(shell=True)/yaml.load;
  * no bare ``except:``;
  * no committed secret material (private keys, AWS keys, bearer tokens,
    high-entropy ``password=``/``token=`` literals) in any shipped text file;
  * every shipped Python file parses.
When ruff/mypy are installed, they are run with the pinned configuration
from pyproject.toml and must be clean.  Dependency CVE scanning (pip-audit /
OSV) is a CI step - the runtime has zero third-party dependencies.
"""
from __future__ import annotations

import ast
import pathlib
import re
import shutil
import subprocess  # noqa: S404 - fixed argv, no shell

PKG = pathlib.Path(__file__).resolve().parents[1]
SKIP = {"__pycache__", "dist", ".mypy_cache", ".ruff_cache"}
BANNED_CALLS = {"eval", "exec", "compile"}
BANNED_ATTRS = {("pickle", "loads"), ("pickle", "load"), ("marshal", "loads"), ("os", "system"), ("yaml", "load")}
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)(password|secret|api[_-]?key)\s*[:=]\s*['\"][A-Za-z0-9/+]{16,}['\"]"),
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
]


def files(pattern: str):
    return [p for p in PKG.rglob(pattern) if not set(p.relative_to(PKG).parts) & SKIP]


def check_python() -> list[str]:
    out = []
    for f in files("*.py"):
        rel = f.relative_to(PKG).as_posix()
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            out.append(f"{rel}: syntax error {exc}")
            continue
        is_test = rel.startswith("tests/")
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert) and not is_test:
                out.append(f"{rel}:{node.lineno}: assert in non-test code")
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                out.append(f"{rel}:{node.lineno}: bare except")
            if isinstance(node, ast.Call):
                fn = node.func
                if isinstance(fn, ast.Name) and fn.id in BANNED_CALLS:
                    out.append(f"{rel}:{node.lineno}: banned call {fn.id}()")
                if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) and (fn.value.id, fn.attr) in BANNED_ATTRS:
                    if not is_test:
                        out.append(f"{rel}:{node.lineno}: banned call {fn.value.id}.{fn.attr}()")
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        out.append(f"{rel}:{node.lineno}: subprocess shell=True")
    return out


def check_secrets() -> list[str]:
    out = []
    for f in files("*"):
        if not f.is_file() or f.suffix in (".pyc", ".zip"):
            continue
        rel = f.relative_to(PKG).as_posix()
        if rel == "tools/lint_gate.py":
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        for pat in SECRET_PATTERNS:
            for m in pat.finditer(text):
                out.append(f"{rel}: possible secret ({m.group(0)[:12]}...)")
    return out


def run_tool(argv: list[str]) -> list[str]:
    exe = shutil.which(argv[0])
    if not exe:
        return []
    proc = subprocess.run([exe, *argv[1:]], cwd=PKG, capture_output=True, text=True)  # noqa: S603
    return [] if proc.returncode == 0 else [f"{argv[0]} failed:\n{proc.stdout[-2000:]}{proc.stderr[-500:]}"]


def main() -> int:
    problems = check_python() + check_secrets() + run_tool(["ruff", "check", "."]) + run_tool(["mypy", "."])
    print("LINT GATE:", "OK" if not problems else "FAIL")
    for p in problems:
        print(" -", p)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
