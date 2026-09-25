"""Certification test run (C056 of program rules, C082-C090).  Runs the full
unittest suite and writes machine-readable results bound to the artifact
digest.  Skips are classified: a skip whose reason starts with
``REQUIRED-CAPABILITY`` is a certification FAILURE; the only tolerated skips
are the optional pk_core adapter tests, and those are reported as
NOT_EXECUTED (never as passing evidence).

    python tools/run_certification.py [--out artifacts/certification/tests.json]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE / "tests"))


class Collect(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.records = []

    def _r(self, test, status, detail=""):
        self.records.append({"id": test.id(), "status": status, "detail": str(detail)[:500]})

    def addSuccess(self, t):
        super().addSuccess(t); self._r(t, "PASS")

    def addFailure(self, t, e):
        super().addFailure(t, e); self._r(t, "FAIL", self._exc_info_to_string(e, t))

    def addError(self, t, e):
        super().addError(t, e); self._r(t, "ERROR", self._exc_info_to_string(e, t))

    def addSkip(self, t, reason):
        super().addSkip(t, reason)
        if t.id().startswith("test_component."):
            status = "NOT_EXECUTED"  # optional pk_core adapter only
        elif reason.startswith("REQUIRED-CAPABILITY"):
            status = "FAIL_REQUIRED_SKIPPED"
        else:
            status = "FAIL_UNEXPECTED_SKIP"
        self._r(t, status, reason)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "artifacts" / "certification" / "tests.json"))
    a = ap.parse_args(argv)
    pkg = __import__(HERE.name)
    lineage = pkg.telemetry.release_lineage()
    suite = unittest.defaultTestLoader.discover(str(HERE / "tests"))
    t0 = time.time()
    res = unittest.TextTestRunner(resultclass=Collect, verbosity=0, stream=open("/dev/null", "w") if sys.platform != "win32" else None).run(suite)
    counts = {}
    for r in res.records:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    ok = res.wasSuccessful() and not any(k.startswith("FAIL") for k in counts)
    report = {"schema": "INV37_CERT_TESTS/1", "artifact": lineage, "started_at": t0, "duration_s": round(time.time() - t0, 3),
              "status": "PASS" if ok else "FAIL", "counts": counts,
              "not_executed_note": "NOT_EXECUTED tests are optional pk_core adapter checks; they are not counted as evidence.",
              "results": res.records}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(report, indent=1))
    print(json.dumps({"status": report["status"], "counts": counts, "source_digest": lineage["source_digest"]}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
