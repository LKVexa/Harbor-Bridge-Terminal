"""Self-check for GAP-09 v5.0.0 using only the Python standard library."""
from __future__ import annotations

import compileall
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
EXPECTED = "5.0.0"


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode:
        raise SystemExit(proc.returncode)


def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if version != EXPECTED:
        raise SystemExit(f"VERSION mismatch: expected {EXPECTED}, got {version}")
    init_text = (ROOT / "__init__.py").read_text(encoding="utf-8")
    if f'__version__ = "{EXPECTED}"' not in init_text:
        raise SystemExit("__version__ mismatch")

    expected_schema_ids = {
        "PK_SIGNAL_SUBMISSION_2.schema.json": "PK_SIGNAL_SUBMISSION/2",
        "PK_SIGNAL_QUERY_1.schema.json": "PK_SIGNAL_QUERY/1",
        "PK_SIGNAL_QUERY_2.schema.json": "PK_SIGNAL_QUERY/2",
        "PK_SIGNAL_CATALOGUE_1.schema.json": "PK_SIGNAL_CATALOGUE/1",
    }
    seen = set()
    for schema in sorted((ROOT / "schemas").glob("*.json")):
        data = json.loads(schema.read_text(encoding="utf-8"))
        expected_id = expected_schema_ids.get(schema.name)
        if expected_id is None or data.get("$id") != expected_id:
            raise SystemExit(f"unexpected schema identity: {schema.name} -> {data.get('$id')!r}")
        seen.add(schema.name)
        print("schema JSON/identity OK:", schema.name)
    if seen != set(expected_schema_ids):
        raise SystemExit(f"schema set mismatch: expected {sorted(expected_schema_ids)}, got {sorted(seen)}")

    if not compileall.compile_dir(ROOT, quiet=1):
        raise SystemExit("compileall failed")

    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    run([sys.executable, "-O", "-m", "unittest", "discover", "-s", "tests", "-p", "test_runtime.py", "-v"])

    candidates = [os.environ.get("PK_CORE_PATH"), str(ROOT.parent), str(ROOT.parent.parent)]
    original_path = list(sys.path)
    try:
        for candidate in filter(None, candidates):
            if candidate not in sys.path:
                sys.path.insert(0, candidate)
        pk_core_found = importlib.util.find_spec("pk_core") is not None
    finally:
        sys.path[:] = original_path
    if not pk_core_found:
        print("STANDALONE PASS; pk_core is not installed, so the 100-item orchestration gate remains unverified.")
    else:
        print("STANDALONE PASS; pk_core detected. Run the documented pk_core gate commands for release certification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
