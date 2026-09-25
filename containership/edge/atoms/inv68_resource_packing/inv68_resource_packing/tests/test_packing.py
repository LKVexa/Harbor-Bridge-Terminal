"""Standalone unit and hardening tests for the pure INV-68 packing engine."""
from __future__ import annotations

import json
import math
import pathlib
import subprocess
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import inv68_resource_packing as rp


class PackingEngineTest(unittest.TestCase):
    def test_package_and_engine_import_without_pk_core(self):
        self.assertEqual(rp.__version__, (PKG_DIR / "VERSION").read_text().strip())
        self.assertTrue(callable(rp.pack))
        self.assertTrue(callable(rp.pack_detailed))

    def test_basic_pack_and_fragmentation(self):
        work = [
            {"name": "a", "cpu": 2, "mem": 8},
            {"name": "b", "cpu": 4, "mem": 16},
            {"name": "c", "cpu": 6, "mem": 12},
        ]
        hosts, unplaced = rp.pack(work, 16, 64)
        self.assertEqual(unplaced, [])
        self.assertEqual(len(hosts), 1)
        self.assertEqual(hosts[0].used, {"cpu": 12.0, "mem": 36.0})
        self.assertEqual(rp.fragmentation(hosts), {"cpu": 9.6, "mem": 21.6})

    def test_does_not_mutate_caller_workloads(self):
        work = [{"name": "a", "cpu": 1, "mem": 1, "metadata": {"tier": "edge"}}]
        before = json.loads(json.dumps(work))
        result = rp.pack_detailed(work, 4, 8)
        self.assertEqual(work, before)
        self.assertEqual(result.assignments, {"a": "h0"})
        self.assertNotIn("host", work[0])

    def test_headroom_and_no_memory_overcommit(self):
        result = rp.pack_detailed(
            [{"name": "fits", "cpu": 1, "mem": 57.6}, {"name": "too-big", "cpu": 1, "mem": 57.6001}],
            16,
            64,
            headroom=0.1,
        )
        self.assertIn("too-big", result.unplaced)
        self.assertNotIn("fits", result.unplaced)
        self.assertLessEqual(max(h.used["mem"] for h in result.hosts), 57.6 + 1e-9)

    def test_capacity_report_matches_capacity_interface_shape(self):
        report = rp.capacity_report(16, 64, 0.1)
        self.assertEqual(report["cpu"], 16.0)
        self.assertEqual(report["mem"], 64.0)
        self.assertEqual(report["headroom"], 0.1)
        self.assertAlmostEqual(report["effective_cpu"], 21.6)
        self.assertAlmostEqual(report["effective_mem"], 57.6)

    def test_detailed_result_serializes_to_response_shape(self):
        result = rp.pack_detailed([{"name": "a", "cpu": 1, "mem": 2}], 4, 8)
        payload = result.to_dict()
        self.assertEqual(payload["assignments"], {"a": "h0"})
        self.assertEqual(payload["unplaced"], [])
        self.assertEqual(payload["hosts"][0]["used"], {"cpu": 1.0, "mem": 2.0})
        self.assertEqual(payload["decisions"][0]["workload"], "a")
        json.dumps(payload)

    def test_cpu_overcommit_policy_is_applied(self):
        caps = rp.effective_capacity(10, 10, 0.0)
        self.assertEqual(caps, {"cpu": 15.0, "mem": 10.0})
        result = rp.pack_detailed([{"name": "cpu-heavy", "cpu": 14.5, "mem": 1}], 10, 10, 0.0)
        self.assertEqual(result.unplaced, ())

    def test_oversize_workload_has_explainable_unplaced_decision(self):
        result = rp.pack_detailed([{"name": "whale", "cpu": 1, "mem": 60}], 16, 64, 0.1)
        self.assertEqual(result.unplaced, ("whale",))
        decision = result.decisions[0]
        self.assertEqual(decision.status, "unplaced")
        self.assertIsNone(decision.host)
        self.assertEqual(decision.reason, "request_exceeds_effective_host_capacity")

    def test_deterministic_order_for_equal_dominant_share(self):
        work = [
            {"name": "z", "cpu": 1, "mem": 1},
            {"name": "a", "cpu": 1, "mem": 1},
        ]
        result = rp.pack_detailed(work, 4, 8)
        self.assertEqual([d.workload for d in result.decisions], ["a", "z"])

    def test_empty_lower_bound(self):
        self.assertEqual(rp.lower_bound([], 16, 64), 0)

    def test_lower_bound_uses_effective_capacity(self):
        work = [{"name": f"w{i}", "cpu": 6, "mem": 20} for i in range(4)]
        expected = max(math.ceil(24 / 21.6), math.ceil(80 / 57.6))
        self.assertEqual(rp.lower_bound(work, 16, 64, 0.1), expected)

    def test_invalid_host_capacity_rejected(self):
        for value in (0, -1, math.inf, math.nan, True, "16"):
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    rp.pack([], value, 64)

    def test_effective_capacity_overflow_or_underflow_rejected(self):
        with self.assertRaises(ValueError):
            rp.pack([], 1.5e308, 64)
        with self.assertRaises(ValueError):
            rp.pack([], 1e-323, 64, headroom=0.9)
        with self.assertRaises(ValueError):
            rp.pack([], 10**10000, 64)

    def test_aggregate_lower_bound_overflow_rejected(self):
        with self.assertRaises(ValueError):
            rp.lower_bound(
                [{"name": "a", "cpu": 1e308, "mem": 1}, {"name": "b", "cpu": 1e308, "mem": 1}],
                1e308 / 2,
                64,
                headroom=0.0,
            )

    def test_invalid_headroom_rejected(self):
        for value in (-0.1, 1, 1.1, math.inf, math.nan, True, "0.1"):
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    rp.pack([], 16, 64, value)

    def test_malformed_workloads_rejected(self):
        bad = [
            None,
            {"name": "x", "cpu": 1},
            {"name": "", "cpu": 1, "mem": 1},
            {"name": "x", "cpu": -1, "mem": 1},
            {"name": "x", "cpu": math.nan, "mem": 1},
            {"name": "x", "cpu": 1, "mem": math.inf},
            {"name": "x", "cpu": True, "mem": 1},
        ]
        for workload in bad:
            with self.subTest(workload=workload):
                with self.assertRaises((TypeError, ValueError)):
                    rp.pack([workload], 16, 64)

    def test_duplicate_workload_names_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate workload name"):
            rp.pack(
                [{"name": "dup", "cpu": 1, "mem": 1}, {"name": "dup", "cpu": 2, "mem": 2}],
                16,
                64,
            )

    def test_fragmentation_rejects_invalid_host_accounting(self):
        host = rp.Host("h0", 10, 10, used={"cpu": 20, "mem": 1})
        with self.assertRaisesRegex(ValueError, "exceeds effective cpu capacity"):
            rp.fragmentation([host], headroom=0.1)

    def test_fragmentation_validates_input_types(self):
        with self.assertRaises(TypeError):
            rp.fragmentation([object()])

    def test_pure_engine_survives_optimised_mode(self):
        code = (
            "import inv68_resource_packing as rp; "
            "r=rp.pack_detailed([{'name':'a','cpu':1,'mem':2}],4,8); "
            "print(r.assignments['a'])"
        )
        out = subprocess.run(
            [sys.executable, "-O", "-c", code],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "h0")

    def test_schema_files_are_valid_json_and_versioned(self):
        schema_dir = PKG_DIR / "schemas"
        expected = {
            "PK_PACK_REQUEST_1.schema.json",
            "PK_PACK_RESPONSE_1.schema.json",
            "PK_PACK_CAPACITY_1.schema.json",
            "PK_PACK_FRAG_1.schema.json",
            # 4.3.0 additions (MC-07/10/15/25/27)
            "PK_PACK_CONFIG_1.schema.json",
            "PK_PACK_ERROR_1.schema.json",
            "PK_PACK_STATUS_1.schema.json",
            "PK_PACK_EXPLAIN_1.schema.json",
            "PK_PACK_AUDIT_1.schema.json",
            "PK_PACK_SERVICE_RESPONSE_1.schema.json",
        }
        self.assertEqual({p.name for p in schema_dir.glob("*.schema.json")}, expected)
        for path in schema_dir.glob("*.schema.json"):
            payload = json.loads(path.read_text())
            self.assertEqual(payload["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertIn(":1", payload["$id"])


if __name__ == "__main__":
    unittest.main()
