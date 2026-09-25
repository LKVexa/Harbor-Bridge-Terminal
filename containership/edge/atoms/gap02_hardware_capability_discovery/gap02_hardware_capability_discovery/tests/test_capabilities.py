from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))

import gap02_hardware_capability_discovery as gap02


class CapabilityReportTests(unittest.TestCase):
    def test_three_valued_probe_and_no_sticky_present(self):
        report = gap02.CapabilityReport("node-1")
        self.assertEqual(gap02.probe(report, "gpu", lambda: True, 0), gap02.PRESENT)

        def crash():
            raise RuntimeError("driver vanished")

        self.assertEqual(gap02.probe(report, "gpu", crash, 1), gap02.UNPROBED)
        self.assertNotIn("gpu", report.present())
        self.assertIn("RuntimeError", report.diagnostics["gpu"])

    def test_invalid_and_ambiguous_probe_results_fail_closed(self):
        report = gap02.CapabilityReport("node-1")
        self.assertEqual(gap02.probe(report, "npu", lambda: 1, 0), gap02.UNPROBED)
        self.assertEqual(report.state("npu"), gap02.UNPROBED)

    def test_oldest_probe_controls_freshness(self):
        report = gap02.CapabilityReport("node-1")
        report.record("cpu", gap02.PRESENT, 0)
        report.record("memory", gap02.PRESENT, 59)
        with self.assertRaises(gap02.ReportStale):
            report.for_consumer(61)

    def test_empty_report_is_refused(self):
        with self.assertRaises(gap02.ReportInvalid):
            gap02.CapabilityReport("node-1").for_consumer(0)

    def test_future_timestamp_is_refused(self):
        report = gap02.CapabilityReport("node-1")
        report.record("cpu", gap02.PRESENT, 10)
        with self.assertRaises(gap02.ReportInvalid):
            report.for_consumer(9)

    def test_direct_mutation_is_detected(self):
        report = gap02.CapabilityReport("node-1")
        report.record("cpu", gap02.PRESENT, 1)
        report.results["cpu"] = ("invented", 1)
        with self.assertRaises(gap02.ReportInvalid):
            report.for_consumer(1)

    def test_canonical_bytes_are_stable_across_consumer_age(self):
        report = gap02.CapabilityReport("node-1")
        report.record("cpu", gap02.PRESENT, 0)
        first = report.canonical_bytes(1)
        second = report.canonical_bytes(2)
        self.assertEqual(first, second)
        body = json.loads(first)
        self.assertNotIn("age", body)
        self.assertEqual(body["present"], ["cpu"])

    def test_names_and_ticks_are_validated(self):
        with self.assertRaises(ValueError):
            gap02.CapabilityReport("node with spaces")
        report = gap02.CapabilityReport("node-1")
        with self.assertRaises(ValueError):
            report.record("bad capability", gap02.PRESENT, 0)
        with self.assertRaises(ValueError):
            report.record("cpu", gap02.PRESENT, True)


class ProbeScheduleTests(unittest.TestCase):
    def test_due_and_hot_add(self):
        report = gap02.CapabilityReport("node-1")
        report.record("cpu", gap02.PRESENT, 5)
        schedule = gap02.ProbeSchedule(("cpu", "gpu"), interval=10)
        self.assertEqual(schedule.due(report, 5), ["gpu"])
        self.assertEqual(schedule.due(report, 15), ["cpu", "gpu"])
        self.assertEqual(schedule.due(report, 6, hot_added=("cpu",)), ["cpu", "gpu"])

    def test_unknown_hot_add_is_rejected(self):
        report = gap02.CapabilityReport("node-1")
        schedule = gap02.ProbeSchedule(("cpu",), interval=10)
        with self.assertRaises(ValueError):
            schedule.due(report, 0, hot_added=("gpu",))


class DiscoveryTests(unittest.TestCase):
    def test_local_discovery_is_privacy_minimized_and_consumable(self):
        inventory, report = gap02.discover("selftest-node", 1)
        payload = inventory.to_dict()
        self.assertEqual(payload["schema"], "PK_HARDWARE_INVENTORY/1")
        self.assertFalse(payload["network"]["addresses_collected"])
        # The discovery layer always records the declared baseline capabilities,
        # even if some are UNPROBED on the current OS/container.
        self.assertEqual(
            set(report.results),
            {"cpu", "memory", "storage", "network", "gpu", "npu", "virtualization.cpu-extension", "tpm"},
        )
        view = report.for_consumer(1)
        self.assertEqual(view["schema"], "PK_NODE_CAPABILITIES/1")
        self.assertEqual(view["node"], "selftest-node")

    def test_version_file_matches_module(self):
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(version, gap02.__version__)


if __name__ == "__main__":
    unittest.main()
