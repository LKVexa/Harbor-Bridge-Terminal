"""Local CI entry point: base package tests, overlay suites (normal and -O),
base SHA256SUMS integrity, check-status ledger, exit gate.  Exit 0 = all local
steps passed AND the gate said GO; exit 3 = local steps passed, gate NO_GO
(the expected result while owners/reviewers/production signing are absent)."""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[2]
ROOT = PKG.parent


def run(args: list[str]) -> int:
    print("$", " ".join(args), flush=True)
    return subprocess.run(args, cwd=ROOT).returncode


def sums_ok() -> bool:
    bad = []
    for line in (PKG / "SHA256SUMS").read_text().splitlines():
        h, name = line.split(None, 1)
        if hashlib.sha256((PKG / name.strip()).read_bytes()).hexdigest() != h:
            bad.append(name)
    print("base SHA256SUMS:", "OK" if not bad else f"MISMATCH {bad}")
    return not bad


def main() -> int:
    py = sys.executable
    steps = [
        run([py, "-B", str(PKG / "tests" / "test_component.py")]),
        run([py, "-B", "-m", "unittest", "discover", "-s", str(PKG / "production" / "tests"), "-t", "."]),
        run([py, "-B", "-O", "-m", "unittest", "discover", "-s", str(PKG / "production" / "tests"), "-t", "."]),
        0 if sums_ok() else 1,
        run([py, "-B", "-m", f"{PKG.name}.production.status"]),
    ]
    if any(steps):
        print("LOCAL CI: FAIL", steps)
        return 1
    gate = run([py, "-B", "-m", f"{PKG.name}.production.exitgate"])
    print("LOCAL CI: PASS; exit gate", "GO" if gate == 0 else "NO_GO")
    return 0 if gate == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
