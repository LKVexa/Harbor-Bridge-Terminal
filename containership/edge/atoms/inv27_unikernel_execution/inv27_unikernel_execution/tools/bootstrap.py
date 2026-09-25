"""Deterministic bootstrap / install verification (MC-034; C040, C096 day-0).

    python -B inv27_unikernel_execution/tools/bootstrap.py

Checks the interpreter, the vendored pk_core against its recorded digests, the fixture digests, and the
release manifest; then runs the mandatory test profile.  Exit 0 only if every step passes.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    fails = []
    if sys.version_info < (3, 10):
        fails.append(f"python {sys.version.split()[0]} < 3.10")
    prov = json.loads((ROOT / "_vendor" / "PK_CORE_PROVENANCE.json").read_text())
    for f, h in prov["files_sha256"].items():
        if hashlib.sha256((ROOT / "_vendor" / "pk_core" / f).read_bytes()).hexdigest() != h:
            fails.append(f"pk_core/{f} digest mismatch")
    fx = json.loads((ROOT / "tests" / "fixtures" / "FIXTURES.json").read_text())
    for f, h in fx["sha256"].items():
        if hashlib.sha256((ROOT / "tests" / "fixtures" / f).read_bytes()).hexdigest() != h:
            fails.append(f"fixture {f} digest mismatch")
    for args in (["-B", "-m", f"{ROOT.name}.tools.manifest", "--verify"], ["-B", str(ROOT / "tests" / "run_all.py")]):
        p = subprocess.run([sys.executable, *args], cwd=str(ROOT.parent), capture_output=True, text=True)
        if p.returncode:
            fails.append(f"{' '.join(args)} failed: {(p.stdout + p.stderr)[-300:]}")
    for f in fails:
        print("BOOTSTRAP FAIL", f)
    print("BOOTSTRAP", "PASS" if not fails else "FAIL")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
