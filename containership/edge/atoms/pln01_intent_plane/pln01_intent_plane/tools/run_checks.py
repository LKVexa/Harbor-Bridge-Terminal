"""Run every PLN-01 suite, normal and ``-O``; emit conformance/test_results.json. Exit non-zero on any failure."""
from __future__ import annotations

import json
import pathlib
import platform
import re
import subprocess
import sys
import time

PKG = pathlib.Path(__file__).resolve().parents[1]
SUITES = ["tests/test_component.py", "tests/test_production.py"]


def run(pkg: pathlib.Path = PKG, write: bool = True) -> dict:
    results = []
    subprocess.run([sys.executable, "-m", "compileall", "-q", str(pkg)], check=True, capture_output=True)
    for opt in ([], ["-O"]):
        for suite in SUITES:
            t = time.time()
            p = subprocess.run([sys.executable, *opt, str(pkg / suite)], capture_output=True, text=True, cwd=str(pkg.parent))
            tail = p.stderr.strip().splitlines()[-3:]
            ran = re.search(r"Ran (\d+) tests", p.stderr)
            skipped = re.search(r"skipped=(\d+)", p.stderr)
            results.append({"suite": suite, "optimized": bool(opt), "returncode": p.returncode,
                            "tests": int(ran.group(1)) if ran else 0, "skipped": int(skipped.group(1)) if skipped else 0,
                            "seconds": round(time.time() - t, 3), "tail": tail})
    doc = {"schema": "PLN01_TEST_RESULTS/1", "python": platform.python_version(), "platform": platform.platform(),
           "status": "PASS" if all(r["returncode"] == 0 for r in results) else "FAIL", "runs": results}
    if write:
        (pkg / "conformance" / "test_results.json").write_text(json.dumps(doc, indent=2))
    return doc


if __name__ == "__main__":
    d = run()
    for r in d["runs"]:
        print(f"{r['suite']:28} {'-O' if r['optimized'] else '  '} rc={r['returncode']} tests={r['tests']} skipped={r['skipped']}")
    print("overall:", d["status"])
    sys.exit(0 if d["status"] == "PASS" else 1)
