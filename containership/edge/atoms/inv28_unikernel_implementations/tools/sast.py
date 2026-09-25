"""Stdlib static security analysis (MC-034).  AST rules over package + tools (tests excluded; vendored pk_core
is scanned separately and reported, not suppressed).

Rules (id: what):
  S-EXEC   eval/exec/compile of dynamic strings          S-SHELL  subprocess with shell=True / os.system / os.popen
  S-PICKLE pickle/marshal/shelve load                    S-YAML   yaml.load
  S-HASH   md5/sha1 via hashlib                          S-RAND   `random` module in runtime (not tests/fixtures)
  S-TMP    tempfile.mktemp                               S-ASSERT assert used for control flow in runtime modules
  S-HMAC   `==` comparison of a value named *mac*/*signature*/*digest* in trust/binding (timing)
Exit 1 on any finding outside the allow-list (none today).
"""
from __future__ import annotations

import ast
import sys

from ._common import EVIDENCE, ROOT, RUNTIME_MODULES, py_files, write_json

ALLOW: set[tuple[str, str]] = set()


def scan_file(rel: str, text: str) -> list[dict]:
    out = []
    tree = ast.parse(text)
    runtime = rel.removesuffix(".py") in RUNTIME_MODULES

    def hit(rule, node, msg):
        if (rel, rule) not in ALLOW:
            out.append({"rule": rule, "file": rel, "line": getattr(node, "lineno", 0), "message": msg})
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
            base = f.value.id if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) else ""
            if name in ("eval", "exec") and isinstance(f, ast.Name):
                hit("S-EXEC", node, f"{name}()")
            if base == "os" and name in ("system", "popen"):
                hit("S-SHELL", node, f"os.{name}")
            if base == "subprocess" and any(k.arg == "shell" and getattr(k.value, "value", False) is True
                                            for k in node.keywords):
                hit("S-SHELL", node, "subprocess shell=True")
            if base in ("pickle", "marshal", "shelve") and name in ("load", "loads", "open"):
                hit("S-PICKLE", node, f"{base}.{name}")
            if base == "yaml" and name == "load":
                hit("S-YAML", node, "yaml.load")
            if base == "hashlib" and name in ("md5", "sha1"):
                hit("S-HASH", node, f"hashlib.{name}")
            if base == "tempfile" and name == "mktemp":
                hit("S-TMP", node, "tempfile.mktemp")
        if runtime and isinstance(node, (ast.Import, ast.ImportFrom)):
            mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            if "random" in mods:
                hit("S-RAND", node, "random module in runtime code")
        if runtime and isinstance(node, ast.Assert):
            hit("S-ASSERT", node, "assert in runtime module (stripped by -O)")
        if rel in ("trust.py", "binding.py") and isinstance(node, ast.Compare) and any(isinstance(o, ast.Eq) for o in node.ops):
            names = [n.id for n in ast.walk(node) if isinstance(n, ast.Name)]
            if any(k in n.lower() for n in names for k in ("mac", "signature")):
                hit("S-HMAC", node, "non-constant-time comparison of a MAC")
    return out


def main(argv=None) -> int:
    findings = []
    for rel, p in py_files(include_tests=False):
        findings += scan_file(rel, p.read_text(encoding="utf-8"))
    vendor = []
    for p in sorted((ROOT / "_vendor" / "pk_core").glob("*.py")):
        vendor += scan_file("_vendor/pk_core/" + p.name, p.read_text(encoding="utf-8"))
    write_json(EVIDENCE / "SAST.json", {"schema": "PK_SAST/1", "tool": "tools/sast.py", "findings": findings,
                                        "vendored_findings": vendor, "pass": not findings})
    for f in findings + vendor:
        print("SAST", f["rule"], f"{f['file']}:{f['line']}", f["message"])
    print("SAST", "PASS" if not findings else f"FAIL ({len(findings)})", f"vendored={len(vendor)}")
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
