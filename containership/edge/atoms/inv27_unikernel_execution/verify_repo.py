"""Offline repository verification for INV-27."""
from __future__ import annotations

import json
import pathlib
import py_compile
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
EXPECTED = "4.3.0"


def fail(message: str) -> None:
    raise SystemExit(f"VERIFY_FAIL: {message}")


version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
if version != EXPECTED:
    fail(f"VERSION is {version!r}, expected {EXPECTED!r}")

init_text = (ROOT / "__init__.py").read_text(encoding="utf-8")
if f'__version__ = "{EXPECTED}"' not in init_text:
    fail("__version__ is not synchronized with VERSION")

checklist = json.loads((ROOT / "CHECKLIST.json").read_text(encoding="utf-8"))
items = checklist.get("items", [])
if checklist.get("item_count") != 100 or len(items) != 100:
    fail("CHECKLIST.json must contain exactly 100 items")
ids = [item.get("check_id") for item in items]
if len(set(ids)) != 100:
    fail("CHECKLIST.json contains duplicate check_id values")

for path in [ROOT / "__init__.py", ROOT / "component.py", ROOT / "contract.py", ROOT / "runtime.py"]:
    py_compile.compile(str(path), doraise=True)

run = subprocess.run(
    [sys.executable, str(ROOT / "tests" / "test_runtime.py")],
    cwd=str(ROOT), capture_output=True, text=True
)
if run.returncode:
    sys.stderr.write(run.stdout + run.stderr)
    fail("dependency-free runtime tests failed")

print("VERIFY_PASS: version, checklist, compilation, and runtime security tests passed")
