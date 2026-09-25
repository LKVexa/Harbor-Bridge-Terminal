"""Standalone unit tests for the GAP-11 allocation state machine.

No pk_core dependency is required; the security-critical allocator is loaded
from its source file so these tests remain runnable in a minimal checkout.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import importlib.util
from pathlib import Path
import sys
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "allocator.py"
SPEC = importlib.util.spec_from_file_location("gap11_allocator_under_test", MODULE_PATH)
allocator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = allocator
if SPEC.loader is None:  # pragma: no cover - importlib invariant
    raise RuntimeError(f"unable to load allocator module from {MODULE_PATH}")
SPEC.loader.exec_module(allocator)

Accelerator = allocator.Accelerator
AcceleratorPool = allocator.AcceleratorPool
AmbiguousRelease = allocator.AmbiguousRelease
InvalidAcceleratorConfiguration = allocator.InvalidAcceleratorConfiguration
NoMatchingAccelerator = allocator.NoMatchingAccelerator
PartitionSpec = allocator.PartitionSpec
ScrubRequired = allocator.ScrubRequired
UndeclaredPartition = allocator.UndeclaredPartition


class AllocatorTest(unittest.TestCase):

    def test_accelerator_kind_matching(self):
        pool = AcceleratorPool([
            Accelerator("gpu0", "g9", 24, kind="gpu"),
            Accelerator("npu0", "n1", 32, kind="npu"),
        ])
        self.assertEqual(pool.allocate(tenant="t", workload="n", kind="npu")["device"], "npu0")
        with self.assertRaises(NoMatchingAccelerator):
            pool.allocate(tenant="t", workload="f", kind="fpga")

    def test_best_fit_whole_device(self):
        pool = AcceleratorPool([
            Accelerator("gpu80", "g9", 80, frozenset({"fp8", "nvlink"})),
            Accelerator("gpu24", "g9", 24, frozenset({"fp8"})),
        ])
        result = pool.allocate(tenant="t1", workload="w1", memory_gb=16, features={"fp8"})
        self.assertEqual(result["device"], "gpu24")
        self.assertTrue(result["lease_id"])

    def test_cross_tenant_handoff_requires_scrub(self):
        pool = AcceleratorPool([Accelerator("gpu0", "g9", 24)])
        lease = pool.allocate(tenant="t1", workload="w1")
        pool.release("gpu0", lease_id=lease["lease_id"])
        with self.assertRaises(ScrubRequired):
            pool.allocate(tenant="t2", workload="w2")
        pool.scrub("gpu0")
        self.assertEqual(pool.allocate(tenant="t2", workload="w2")["device"], "gpu0")

    def test_same_tenant_dirty_reuse_is_allowed(self):
        pool = AcceleratorPool([Accelerator("gpu0", "g9", 24)])
        first = pool.allocate(tenant="t1", workload="w1")
        pool.release_lease(first["lease_id"])
        second = pool.allocate(tenant="t1", workload="w2")
        self.assertEqual(second["device"], "gpu0")

    def test_same_tenant_can_hold_distinct_partitions(self):
        pool = AcceleratorPool([
            Accelerator(
                "gpu0", "g9", 24, frozenset({"fp8"}),
                partitions=(PartitionSpec("half", 12), PartitionSpec("quarter", 6)),
            )
        ])
        a = pool.allocate(tenant="t1", workload="a", partition="half", memory_gb=8)
        b = pool.allocate(tenant="t1", workload="b", partition="quarter", memory_gb=4)
        self.assertEqual(len(pool.allocations()), 2)
        with self.assertRaises(NoMatchingAccelerator):
            pool.allocate(tenant="t1", workload="whole")
        with self.assertRaises(ScrubRequired):
            # The physical device cannot cross tenant boundaries even when another
            # partition name would otherwise be free.
            pool.release_lease(b["lease_id"])
            pool.allocate(tenant="t2", workload="cross", partition="quarter")
        pool.release_lease(a["lease_id"])

    def test_partition_capacity_is_attested_not_inherited_from_whole_device(self):
        pool = AcceleratorPool([
            Accelerator("gpu0", "g9", 80, partitions=(PartitionSpec("slice", 10),))
        ])
        with self.assertRaises(NoMatchingAccelerator):
            pool.allocate(tenant="t1", workload="too-big", partition="slice", memory_gb=11)

    def test_legacy_partition_name_cannot_claim_positive_memory(self):
        pool = AcceleratorPool([Accelerator("gpu0", "g9", 80, partitions=("slice",))])
        with self.assertRaises(NoMatchingAccelerator):
            pool.allocate(tenant="t1", workload="needs-memory", partition="slice", memory_gb=1)
        self.assertEqual(
            pool.allocate(tenant="t1", workload="capacity-unspecified", partition="slice")["partition"],
            "slice",
        )

    def test_partition_must_be_declared(self):
        pool = AcceleratorPool([Accelerator("gpu0", "g9", 24, partitions=(PartitionSpec("half", 12),))])
        with self.assertRaises(UndeclaredPartition):
            pool.allocate(tenant="t1", workload="w", partition="third")

    def test_failed_scrub_quarantines_even_previous_tenant(self):
        pool = AcceleratorPool([Accelerator("gpu0", "g9", 24)])
        lease = pool.allocate(tenant="t1", workload="w1")
        pool.release_lease(lease["lease_id"])
        result = pool.scrub("gpu0", succeeds=False)
        self.assertTrue(result["quarantined"])
        with self.assertRaises(ScrubRequired):
            pool.allocate(tenant="t1", workload="w2")
        pool.scrub("gpu0", succeeds=True)
        self.assertEqual(pool.allocate(tenant="t1", workload="w3")["device"], "gpu0")

    def test_scrub_while_held_fails_closed(self):
        pool = AcceleratorPool([Accelerator("gpu0", "g9", 24)])
        pool.allocate(tenant="t1", workload="w1")
        with self.assertRaises(ScrubRequired):
            pool.scrub("gpu0")

    def test_ambiguous_device_only_release_fails_closed(self):
        pool = AcceleratorPool([
            Accelerator("gpu0", "g9", 24, partitions=(PartitionSpec("a", 12), PartitionSpec("b", 12)))
        ])
        pool.allocate(tenant="t1", workload="a", partition="a")
        pool.allocate(tenant="t1", workload="b", partition="b")
        with self.assertRaises(AmbiguousRelease):
            pool.release("gpu0")

    def test_input_validation_and_duplicate_inventory(self):
        with self.assertRaises(InvalidAcceleratorConfiguration):
            AcceleratorPool([Accelerator("gpu0", "g9", 24), Accelerator("gpu0", "g9", 24)])
        pool = AcceleratorPool([Accelerator("gpu0", "g9", 24)])
        for kwargs in (
            {"tenant": "", "workload": "w"},
            {"tenant": "t", "workload": ""},
            {"tenant": "t", "workload": "w", "memory_gb": -1},
            {"tenant": "t", "workload": "w", "memory_gb": True},
            {"tenant": "t", "workload": "w", "features": {""}},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                pool.allocate(**kwargs)

    def test_release_unknown_or_unallocated_fails(self):
        pool = AcceleratorPool([Accelerator("gpu0", "g9", 24)])
        with self.assertRaises(KeyError):
            pool.release("missing")
        with self.assertRaises(KeyError):
            pool.release("gpu0")

    def test_inventory_snapshot_is_typed(self):
        pool = AcceleratorPool([
            Accelerator("gpu0", "g9", 24, frozenset({"fp8"}), partitions=(PartitionSpec("half", 12),))
        ])
        inventory = pool.inventory()
        self.assertEqual(inventory["schema"], "PK_ACCELERATOR_INVENTORY/1")
        self.assertEqual(inventory["devices"][0]["partitions"][0]["memory_gb"], 12)

    def test_structured_errors(self):
        pool = AcceleratorPool([Accelerator("gpu0", "g9", 24)])
        with self.assertRaises(NoMatchingAccelerator) as caught:
            pool.allocate(tenant="t", workload="w", memory_gb=25)
        payload = caught.exception.as_dict()
        self.assertEqual(payload["code"], "NO_MATCHING_ACCELERATOR")
        self.assertIn("details", payload)

    def test_partition_allocation_is_race_safe(self):
        pool = AcceleratorPool([
            Accelerator("gpu0", "g9", 24, partitions=(PartitionSpec("half", 12),))
        ])

        def attempt(index: int) -> str:
            try:
                pool.allocate(tenant="t1", workload=f"w{index}", partition="half")
                return "allocated"
            except NoMatchingAccelerator:
                return "refused"

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(attempt, range(16)))
        self.assertEqual(results.count("allocated"), 1)
        self.assertEqual(results.count("refused"), 15)


if __name__ == "__main__":
    unittest.main(verbosity=2)
