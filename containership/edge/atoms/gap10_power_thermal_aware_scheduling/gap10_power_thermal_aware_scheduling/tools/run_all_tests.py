"""Run every suite and write machine-readable evidence (``evidence/TEST_REPORT.json``).

Separates suites (unit / contract / integration / concurrency / fault / perf /
certification), records source digest, Python version, platform and seeds,
and FAILS if any mandatory test is skipped without an approved waiver.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import platform
import sys
import time
import unittest

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tests"))
sys.path.insert(0, str(PKG.parent))

SUITES = {
    "unit": ["test_kernel", "test_prod_p1", "test_prod_p2"],
    "contract+integration+enforcement": ["test_prod_p0"],
    "certification(e2e/contract-fuzz/concurrency/fault/perf/release)": ["test_prod_p3"],
    "package": ["test_package", "test_prod_docs"],
    "estate": ["test_component"],
}
# Skips allowed only with an explicit waiver id from docs/EXCEPTION_REGISTER.md
WAIVED_SKIPS = {"test_component": "EX-008"}
SEEDS = {"telemetry_fuzz": 1234, "policy_fuzz": 99, "retry_jitter": 1}


def source_digest() -> str:
    h = hashlib.sha256()
    for p in sorted(PKG.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and "evidence" not in p.parts and p.name != "MANIFEST.sha256":
            h.update(p.relative_to(PKG).as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


class Recorder(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.rows = []

    def _row(self, test, outcome, detail=""):
        tid = test.id()
        tag = next((part[6:8] for part in tid.split(".") if part.startswith("test_c") and part[6:8].isdigit()), None)
        self.rows.append({"id": tid, "outcome": outcome, "component": tag, "detail": detail[:500]})

    def addSuccess(self, t):
        super().addSuccess(t); self._row(t, "passed")

    def addFailure(self, t, e):
        super().addFailure(t, e); self._row(t, "failed", self._exc_info_to_string(e, t))

    def addError(self, t, e):
        super().addError(t, e); self._row(t, "error", self._exc_info_to_string(e, t))

    def addSkip(self, t, r):
        super().addSkip(t, r); self._row(t, "skipped", r)


def main() -> int:
    report = {"schema": "PK_GAP10_TEST_REPORT/1", "version": (PKG / "VERSION").read_text().strip(),
              "source_sha256": source_digest(), "python": platform.python_version(),
              "platform": f"{platform.system()} {platform.machine()}", "seeds": SEEDS,
              "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "suites": {}}
    ok = True
    loader = unittest.TestLoader()
    for suite, mods in SUITES.items():
        rows = []
        for m in mods:
            runner = unittest.TextTestRunner(resultclass=Recorder, verbosity=0, stream=open("/dev/null", "w") if sys.platform != "win32" else sys.stderr)
            res = runner.run(loader.loadTestsFromName(m))
            rows += res.rows
            for r in res.rows:
                if r["outcome"] in ("failed", "error"):
                    ok = False
                if r["outcome"] == "skipped":
                    r["waiver"] = WAIVED_SKIPS.get(m)
                    if r["waiver"] is None:
                        ok = False
        report["suites"][suite] = rows
    allrows = [r for rows in report["suites"].values() for r in rows]
    report["totals"] = {k: sum(1 for r in allrows if r["outcome"] == k) for k in ("passed", "failed", "error", "skipped")}
    report["passed"] = ok
    out = PKG / "evidence"
    out.mkdir(exist_ok=True)
    (out / "TEST_REPORT.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report["totals"]), "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
