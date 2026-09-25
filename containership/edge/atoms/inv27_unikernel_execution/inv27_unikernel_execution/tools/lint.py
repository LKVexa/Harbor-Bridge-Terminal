"""AST security lint for runtime modules (MC-091).

Rules: no eval/exec/compile; no os.system/os.popen; no subprocess with shell=True or a str command;
no pickle/marshal/shelve; no bare ``assert`` for control (stripped by -O); no ``except:`` bare;
no yaml.load; tempfile.mktemp forbidden.  Exit 1 with file:line on any finding.
"""
from __future__ import annotations

import ast
import sys

from ._refs import ROOT
from .deps_check import runtime_modules

BANNED_CALLS = {"eval", "exec", "compile"}
BANNED_ATTR = {("os", "system"), ("os", "popen"), ("tempfile", "mktemp"), ("yaml", "load")}
BANNED_MODS = {"pickle", "marshal", "shelve"}


def lint_file(rel: str) -> list[str]:
    out = []
    tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
    for n in ast.walk(tree):
        loc = f"{rel}:{getattr(n, 'lineno', 0)}"
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name) and f.id in BANNED_CALLS:
                out.append(f"{loc} call to {f.id}")
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and (f.value.id, f.attr) in BANNED_ATTR:
                out.append(f"{loc} call to {f.value.id}.{f.attr}")
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "subprocess":
                for kw in n.keywords:
                    if kw.arg == "shell" and not (isinstance(kw.value, ast.Constant) and kw.value.value is False):
                        out.append(f"{loc} subprocess shell=")
                if n.args and isinstance(n.args[0], (ast.Constant, ast.JoinedStr)):
                    out.append(f"{loc} subprocess with a string command")
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            mods = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module or ""]
            for m in mods:
                if m.split(".")[0] in BANNED_MODS:
                    out.append(f"{loc} import {m}")
        if isinstance(n, ast.Assert):
            out.append(f"{loc} assert statement (stripped under -O)")
        if isinstance(n, ast.ExceptHandler) and n.type is None:
            out.append(f"{loc} bare except")
    return out


def main(argv=None) -> int:
    findings = [f for rel in runtime_modules() for f in lint_file(rel)]
    for f in findings:
        print("LINT", f)
    print("LINT", "PASS" if not findings else "FAIL", len(findings))
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
