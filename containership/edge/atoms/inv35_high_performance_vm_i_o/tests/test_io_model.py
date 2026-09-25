"""Standalone tests for the untrusted virtqueue boundary (no pk_core required)."""
from __future__ import annotations

import importlib
import pathlib
import sys
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pkg = importlib.import_module(PKG_DIR.name)
Descriptor = pkg.Descriptor
DescriptorInvalid = pkg.DescriptorInvalid
MemoryRegion = pkg.MemoryRegion
QueueFull = pkg.QueueFull
VirtQueue = pkg.VirtQueue
MAX_CHAIN = pkg.MAX_CHAIN
QUEUE_DEPTH = pkg.QUEUE_DEPTH


class MemoryRegionTest(unittest.TestCase):
    def test_rejects_invalid_region_definition(self):
        for args in [(-1, 1), (0, 0), (0, -1)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                MemoryRegion(*args)
        with self.assertRaises(TypeError):
            MemoryRegion(True, 1)

    def test_adjacent_regions_cover_one_descriptor_without_gap(self):
        q = VirtQueue("vq", (MemoryRegion(0x1000, 0x100), MemoryRegion(0x1100, 0x100)))
        result = q.submit({0: Descriptor(0, 0x10F0, 0x20)}, 0)
        self.assertTrue(result["validated"])

    def test_gap_between_regions_fails_closed(self):
        q = VirtQueue("vq", (MemoryRegion(0x1000, 0x100), MemoryRegion(0x1200, 0x100)))
        with self.assertRaises(DescriptorInvalid):
            q.submit({0: Descriptor(0, 0x10F0, 0x120)}, 0)


class VirtQueueValidationTest(unittest.TestCase):
    def setUp(self):
        self.q = VirtQueue("vq0", (MemoryRegion(0x10000, 0x10000),))

    def assert_invalid(self, descriptor, head=0):
        with self.assertRaises(DescriptorInvalid):
            self.q.submit({0: descriptor}, head)
        self.assertEqual(self.q.in_flight, 0)
        self.assertEqual(self.q.pending, 0)
        self.assertEqual(self.q.in_flight_descriptors, 0)

    def test_valid_chain(self):
        chain = {0: Descriptor(0, 0x10000, 32, 1), 1: Descriptor(1, 0x10020, 16)}
        result = self.q.submit(chain, 0)
        self.assertEqual(result["descriptors"], [0, 1])
        self.assertEqual(result["descriptor_count"], 2)
        self.assertEqual(result["bytes"], 48)
        self.assertEqual(self.q.in_flight_descriptors, 2)

    def test_host_pointer_rejected(self):
        self.assert_invalid(Descriptor(0, 0, 64))

    def test_negative_address_rejected(self):
        self.assert_invalid(Descriptor(0, -1, 1))

    def test_negative_length_rejected(self):
        self.assert_invalid(Descriptor(0, 0x10000, -1))

    def test_bool_address_rejected(self):
        self.assert_invalid(Descriptor(0, True, 1))

    def test_bool_length_rejected(self):
        self.assert_invalid(Descriptor(0, 0x10000, False))

    def test_slot_index_mismatch_rejected(self):
        self.assert_invalid(Descriptor(9, 0x10000, 1))

    def test_invalid_head_types_rejected(self):
        for head in (-1, True, "0", None):
            with self.subTest(head=head), self.assertRaises(DescriptorInvalid):
                self.q.submit({0: Descriptor(0, 0x10000, 1)}, head)

    def test_invalid_slot_key_types_rejected(self):
        for slot in (-1, True, "0", 0.0):
            with self.subTest(slot=slot), self.assertRaises(DescriptorInvalid):
                self.q.submit({slot: Descriptor(0, 0x10000, 1)}, 0)

    def test_invalid_next_index_types_rejected(self):
        for nxt in (-1, True, "1", 1.0):
            with self.subTest(nxt=nxt), self.assertRaises(DescriptorInvalid):
                self.q.submit({0: Descriptor(0, 0x10000, 1, nxt)}, 0)

    def test_loop_rejected(self):
        with self.assertRaises(DescriptorInvalid):
            self.q.submit({0: Descriptor(0, 0x10000, 1, 1), 1: Descriptor(1, 0x10001, 1, 0)}, 0)

    def test_dangling_index_rejected(self):
        with self.assertRaises(DescriptorInvalid):
            self.q.submit({0: Descriptor(0, 0x10000, 1, 1)}, 0)

    def test_non_descriptor_slot_rejected(self):
        with self.assertRaises(DescriptorInvalid):
            self.q.submit({0: object()}, 0)

    def test_chain_length_is_bounded(self):
        chain = {
            i: Descriptor(i, 0x10000 + i, 1, i + 1 if i < MAX_CHAIN else None)
            for i in range(MAX_CHAIN + 1)
        }
        with self.assertRaises(DescriptorInvalid):
            self.q.submit(chain, 0)

    def test_chain_mapping_is_snapshotted(self):
        chain = {0: Descriptor(0, 0x10000, 1)}
        result = self.q.submit(chain, 0)
        chain[0] = Descriptor(0, 0, 1)
        self.assertTrue(result["validated"])


class VirtQueueAccountingTest(unittest.TestCase):
    def setUp(self):
        self.q = VirtQueue("vq0", (MemoryRegion(0x10000, 0x10000),))

    def test_runtime_counters_cannot_be_injected_at_construction(self):
        with self.assertRaises(TypeError):
            VirtQueue("vq", (MemoryRegion(0x10000, 0x1000),), in_flight=1)

    @staticmethod
    def chain(size):
        return {
            i: Descriptor(i, 0x10000 + i, 1, i + 1 if i + 1 < size else None)
            for i in range(size)
        }

    def test_queue_depth_counts_descriptor_entries(self):
        for _ in range(QUEUE_DEPTH // MAX_CHAIN):
            self.q.submit(self.chain(MAX_CHAIN), 0)
        self.assertEqual(self.q.in_flight_descriptors, QUEUE_DEPTH)
        with self.assertRaises(QueueFull):
            self.q.submit(self.chain(1), 0)

    def test_failed_capacity_check_does_not_mutate_counters(self):
        for _ in range(QUEUE_DEPTH):
            self.q.submit(self.chain(1), 0)
        before = (self.q.in_flight, self.q.pending, self.q.in_flight_descriptors)
        with self.assertRaises(QueueFull):
            self.q.submit(self.chain(1), 0)
        self.assertEqual((self.q.in_flight, self.q.pending, self.q.in_flight_descriptors), before)

    def test_completion_releases_correct_descriptor_count(self):
        self.q.submit(self.chain(3), 0)
        result = self.q.complete(guest_wants_notification=True)
        self.assertEqual(result["descriptors_released"], 3)
        self.assertEqual(result["in_flight_descriptors"], 0)

    def test_notification_suppression_cannot_strand_pending_work(self):
        self.q.submit(self.chain(1), 0)
        self.q.submit(self.chain(1), 0)
        first = self.q.complete(guest_wants_notification=False)
        second = self.q.complete(guest_wants_notification=False)
        self.assertTrue(first["notified"])
        self.assertFalse(second["notified"])

    def test_completion_history_is_bounded(self):
        for _ in range(QUEUE_DEPTH + 5):
            self.q.submit(self.chain(1), 0)
            self.q.complete(guest_wants_notification=True)
        self.assertEqual(len(self.q.completed), QUEUE_DEPTH)

    def test_complete_empty_queue_fails(self):
        with self.assertRaises(RuntimeError):
            self.q.complete(guest_wants_notification=True)

    def test_notification_flag_requires_bool(self):
        self.q.submit(self.chain(1), 0)
        with self.assertRaises(TypeError):
            self.q.complete(guest_wants_notification=1)
        self.assertEqual(self.q.pending, 1)

    def test_parallel_submissions_do_not_overcommit_queue(self):
        accepted = []
        lock = threading.Lock()

        def submit_one():
            try:
                self.q.submit(self.chain(1), 0)
            except QueueFull:
                return
            with lock:
                accepted.append(1)

        threads = [threading.Thread(target=submit_one) for _ in range(QUEUE_DEPTH * 2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(accepted), QUEUE_DEPTH)
        self.assertEqual(self.q.in_flight_descriptors, QUEUE_DEPTH)


if __name__ == "__main__":
    unittest.main()
