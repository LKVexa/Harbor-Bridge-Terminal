"""Standalone unit tests for INV-72 matching logic (no pk_core required)."""
import math
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pkg = __import__(PKG_DIR.name, fromlist=["Device", "match"])
Device = pkg.Device
match = pkg.match
RequirementValidationError = pkg.RequirementValidationError
InventoryValidationError = pkg.InventoryValidationError


class MatcherTest(unittest.TestCase):
    def fleet(self):
        return [
            Device("a0", "gpu-large", 80, "n1", "nvl-1"),
            Device("a1", "gpu-large", 80, "n1", "nvl-1"),
            Device("b0", "gpu-large", 80, "n2", "pcie"),
            Device("c0", "gpu-large", 40, "n3", "pcie"),
            Device("p0", "gpu-large", 80, "n4", "pcie", partition_of="gpu-n4"),
        ]

    def test_exact_class_and_minimum_memory(self):
        selected, reasons = match(
            {"class": "gpu-large", "mem_gb": 80, "tenant": "t1"}, self.fleet(), reserve=False
        )
        self.assertEqual(selected, ["a0"])
        self.assertTrue(all("partition not allowed" in reason for reason in reasons))

    def test_insufficient_memory_explains_gap(self):
        selected, reasons = match(
            {"class": "gpu-large", "mem_gb": 120, "tenant": "t1"}, self.fleet(), reserve=False
        )
        self.assertIsNone(selected)
        self.assertEqual(reasons, ["largest gpu-large has 80 GB < 120 GB"])

    def test_shared_interconnect_requires_one_group(self):
        selected, _ = match(
            {
                "class": "gpu-large",
                "mem_gb": 80,
                "count": 2,
                "interconnect": True,
                "tenant": "t1",
            },
            list(reversed(self.fleet())),
            reserve=False,
        )
        self.assertEqual(selected, ["a0", "a1"])

    def test_selection_is_deterministic_across_inventory_order(self):
        requirement = {"class": "gpu-large", "mem_gb": 40, "tenant": "t1"}
        forward, _ = match(requirement, self.fleet(), reserve=False)
        reverse, _ = match(requirement, list(reversed(self.fleet())), reserve=False)
        self.assertEqual(forward, reverse)

    def test_dedicated_is_secure_default_and_rejects_partition(self):
        partition = [Device("p0", "gpu-large", 80, "n4", "pcie", partition_of="gpu-n4")]
        selected, reasons = match(
            {"class": "gpu-large", "mem_gb": 20, "tenant": "t1"}, partition, reserve=False
        )
        self.assertIsNone(selected)
        self.assertIn("partition not allowed for dedicated isolation", reasons[0])

    def test_unknown_isolation_is_rejected_fail_closed(self):
        for isolation in ("anything", [], 1):
            with self.subTest(isolation=isolation), self.assertRaises(RequirementValidationError):
                match(
                    {"class": "gpu-large", "mem_gb": 20, "tenant": "t1", "isolation": isolation},
                    self.fleet(),
                )

    def test_partition_cannot_cross_tenants(self):
        partition = [
            Device("p0", "gpu-large", 80, "n4", "pcie", partition_of="gpu-n4", tenants={"t1"})
        ]
        selected, reasons = match(
            {"class": "gpu-large", "mem_gb": 20, "tenant": "t2", "isolation": "shared"},
            partition,
            reserve=False,
        )
        self.assertIsNone(selected)
        self.assertIn("another tenant", reasons[0])

    def test_whole_device_cannot_cross_tenants(self):
        device = [Device("a0", "gpu-large", 80, "n1", "nvl-1", tenants={"t1"})]
        selected, reasons = match(
            {"class": "gpu-large", "mem_gb": 20, "tenant": "t2"}, device, reserve=False
        )
        self.assertIsNone(selected)
        self.assertIn("another tenant", reasons[0])

    def test_failed_match_has_no_reservation_side_effects(self):
        fleet = self.fleet()
        selected, _ = match(
            {
                "class": "gpu-large",
                "mem_gb": 80,
                "count": 3,
                "interconnect": True,
                "tenant": "t1",
            },
            fleet,
        )
        self.assertIsNone(selected)
        self.assertTrue(all(not d.tenants for d in fleet))

    def test_successful_match_reserves_only_after_selection(self):
        fleet = self.fleet()
        selected, _ = match(
            {
                "class": "gpu-large",
                "mem_gb": 80,
                "count": 2,
                "interconnect": True,
                "tenant": "t1",
            },
            fleet,
        )
        self.assertEqual(selected, ["a0", "a1"])
        owned = {d.dev_id for d in fleet if d.tenants == {"t1"}}
        self.assertEqual(owned, {"a0", "a1"})

    def test_reserve_false_is_side_effect_free(self):
        fleet = self.fleet()
        selected, _ = match(
            {"class": "gpu-large", "mem_gb": 40, "tenant": "t1"}, fleet, reserve=False
        )
        self.assertEqual(selected, ["a0"])
        self.assertTrue(all(not d.tenants for d in fleet))

    def test_boolean_and_nonfinite_numbers_are_rejected(self):
        bad_requirements = [
            {"class": "gpu-large", "mem_gb": True, "tenant": "t1"},
            {"class": "gpu-large", "mem_gb": math.nan, "tenant": "t1"},
            {"class": "gpu-large", "mem_gb": math.inf, "tenant": "t1"},
            {"class": "gpu-large", "mem_gb": 1, "count": True, "tenant": "t1"},
            {"class": "gpu-large", "mem_gb": 10**10000, "tenant": "t1"},
        ]
        for requirement in bad_requirements:
            with self.subTest(requirement=requirement), self.assertRaises(RequirementValidationError):
                match(requirement, self.fleet())

    def test_required_strings_and_boolean_interconnect_are_validated(self):
        for requirement in [
            {"class": "", "mem_gb": 1, "tenant": "t1"},
            {"class": "gpu-large", "mem_gb": 1, "tenant": ""},
            {"class": "gpu-large", "mem_gb": 1, "tenant": "t1", "interconnect": 1},
        ]:
            with self.subTest(requirement=requirement), self.assertRaises(RequirementValidationError):
                match(requirement, self.fleet())

    def test_duplicate_device_ids_are_rejected(self):
        with self.assertRaises(InventoryValidationError):
            match(
                {"class": "gpu-large", "mem_gb": 1, "tenant": "t1"},
                [
                    Device("dup", "gpu-large", 80, "n1", "x"),
                    Device("dup", "gpu-large", 80, "n2", "y"),
                ],
            )

    def test_mutated_invalid_inventory_is_revalidated(self):
        device = Device("a0", "gpu-large", 80, "n1", "x")
        device.mem_gb = math.nan
        with self.assertRaises(InventoryValidationError):
            match({"class": "gpu-large", "mem_gb": 1, "tenant": "t1"}, [device])


if __name__ == "__main__":
    unittest.main()
