"""Run every standalone suite (normal and -O) and write conformance/test_results.json.

pk_core conformance (tests/test_component.py) is reported separately: when
pk_core is absent its skips are *certification-critical* and are counted as
such, so the gate cannot pass on a partial environment.
"""
from __future__ import annotations

import json
import pathlib
import platform
import subprocess
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
SUITES = sorted(p.name for p in (PKG / "tests").glob("test_*.py") if p.name != "test_component.py")


def run(args):
    p = subprocess.run([sys.executable, *args], cwd=PKG, capture_output=True, text=True)
    tail = (p.stderr or "").strip().splitlines()
    summary = next((l for l in reversed(tail) if l.startswith(("OK", "FAILED"))), "?")
    ran = next((l for l in reversed(tail) if l.startswith("Ran ")), "Ran 0 tests")
    return p.returncode, summary, int(ran.split()[1])


def main() -> int:
    results, passed, failed, skipped_cc = [], 0, 0, 0
    for flags in ([], ["-O"]):
        for s in SUITES:
            rc, summary, n = run([*flags, f"tests/{s}"])
            results.append({"suite": s, "optimize": bool(flags), "rc": rc, "tests": n, "summary": summary})
            passed += n if rc == 0 else 0
            failed += 0 if rc == 0 else 1
            print(f"{'-O ' if flags else '   '}{s:28s} {summary} ({n})")
    rc, summary, n = run(["tests/test_component.py"])
    if "skipped" in summary:
        skipped_cc = int(summary.split("skipped=")[1].rstrip(")").split(",")[0])
    results.append({"suite": "test_component.py", "optimize": False, "rc": rc, "tests": n, "summary": summary,
                    "certification_critical": True})
    print(f"   test_component.py (pk_core)   {summary} ({n})")
    out = {"python": platform.python_version(), "platform": platform.platform(),
           "passed": passed, "failed": failed, "errors": 0 if rc == 0 else 1,
           "certification_critical_skips": skipped_cc, "suites": results}
    (PKG / "conformance").mkdir(exist_ok=True)
    (PKG / "conformance" / "test_results.json").write_text(json.dumps(out, indent=2) + "\n")
    return 1 if failed or rc else 0


if __name__ == "__main__":
    sys.exit(main())
