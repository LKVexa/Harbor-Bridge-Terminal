#!/usr/bin/env python3
"""Run the suite and print one JSON document with per-test outcomes (used by gen_evidence.py)."""
import json
import pathlib
import sys
import unittest

TESTS = pathlib.Path(__file__).resolve().parents[1] / "inv66_enterprise_wasm_control_plane" / "tests"


class Result(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.cases = []

    def addSuccess(self, t):
        super().addSuccess(t); self.cases.append({"test": t.id(), "outcome": "ok"})

    def addFailure(self, t, err):
        super().addFailure(t, err); self.cases.append({"test": t.id(), "outcome": "FAIL"})

    def addError(self, t, err):
        super().addError(t, err); self.cases.append({"test": t.id(), "outcome": "ERROR"})

    def addSkip(self, t, reason):
        super().addSkip(t, reason); self.cases.append({"test": t.id(), "outcome": f"skipped: {reason}"})


suite = unittest.defaultTestLoader.discover(str(TESTS))
runner = unittest.TextTestRunner(stream=open("/dev/null", "w"), resultclass=Result)
res = runner.run(suite)
print(json.dumps({"ok": res.wasSuccessful(), "optimize": sys.flags.optimize, "cases": res.cases}))
