"""Verify the package tree against SHA256SUMS and, if present, the sealed release evidence.

Usage: python tools/verify.py [PACKAGE_DIR]      (exit 0 = intact)
"""
import pathlib
import sys

pkg = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[1]).resolve()
sys.path.insert(0, str(pkg.parent))
mod = __import__(pkg.name)
from importlib import import_module

tv = import_module(pkg.name + ".tools_verify")
problems = tv.verify_tree(pkg)
ev = pkg / "conformance" / "RELEASE_EVIDENCE.json"
if ev.exists():
    ok, p2 = import_module(pkg.name + ".certify").verify(ev)
    problems += p2
for p in problems:
    print("PROBLEM:", p)
print("INTACT" if not problems else f"{len(problems)} problem(s)")
sys.exit(0 if not problems else 1)
