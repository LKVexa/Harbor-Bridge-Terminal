"""Tests for operational tooling: rollout evaluator, review scheduler, traceability, exit gate."""
from __future__ import annotations

import pathlib
import subprocess
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG_DIR))
sys.path.insert(0, str(PKG_DIR / "tools"))

import descriptors as d  # noqa: E402
import rollout  # noqa: E402
import telemetry  # noqa: E402


def export(n_ok, n_bad=0, disable=False):
    m = telemetry.Metrics()
    t = d.DescriptorTable("w", observer=m)
    fd = t.open("s", 1)
    for _ in range(n_ok):
        t.resolve(fd)
    other = d.DescriptorTable("x").open("s", 1)
    for _ in range(n_bad):
        try:
            t.resolve(other)
        except d.ForeignDescriptor:
            pass
    text = m.prometheus([t])
    return text.replace("inv42_emergency_disabled 0", "inv42_emergency_disabled 1") if disable else text


class RolloutTest(unittest.TestCase):
    def test_decisions(self):
        base = export(2000, 5)
        big = 10.0  # isolate non-latency rules from host timing noise
        self.assertEqual(rollout.evaluate(base, export(2000, 5), p99_threshold_s=big)[0], "promote")
        self.assertEqual(rollout.evaluate(base, export(2000, 400), p99_threshold_s=big)[0], "rollback")
        self.assertEqual(rollout.evaluate(base, export(2000, disable=True), p99_threshold_s=big)[0], "rollback")
        self.assertEqual(rollout.evaluate(base, export(50), p99_threshold_s=big)[0], "hold")
        decision, reasons, _ = rollout.evaluate(base, export(2000), p99_threshold_s=1e-12)
        self.assertEqual(decision, "rollback")
        self.assertIn("p99", reasons[0])


class GovernanceToolsTest(unittest.TestCase):
    def test_traceability_is_complete(self):
        r = subprocess.run([sys.executable, str(PKG_DIR / "tools" / "traceability.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_review_schedule_parses(self):
        r = subprocess.run([sys.executable, str(PKG_DIR / "tools" / "review_due.py"), "--as-of", "2026-09-23"], capture_output=True, text=True)
        self.assertIn(r.returncode, (0, 9), r.stderr)


if __name__ == "__main__":
    unittest.main()
