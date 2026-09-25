"""Standalone unit tests for INV-53 reliability primitives.

These tests intentionally load ``reliability.py`` without importing package
``__init__`` so they remain executable when the external ``pk_core`` framework is
not installed in the audit environment.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("inv53_reliability_standalone", PKG_DIR / "reliability.py")
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import machinery failure
    raise RuntimeError("unable to load reliability.py for standalone tests")
R = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = R
SPEC.loader.exec_module(R)


class ReliableQueueTest(unittest.TestCase):
    def test_stale_ack_cannot_settle_new_lease(self):
        q = R.ReliableQueue(visibility=5, max_attempts=3)
        q.put({"id": "m1", "payload": {"n": 1}})
        first = q.receive(now=0)
        self.assertIsNotNone(first)
        second = q.receive(now=6)
        self.assertIsNotNone(second)
        self.assertNotEqual(first.lease_id, second.lease_id)
        self.assertFalse(q.ack(first, now=6))
        self.assertTrue(q.ack(second, now=6))
        self.assertEqual(q.snapshot()["ack_rejections"], 1)


    def test_ack_after_visibility_deadline_is_rejected_without_receive(self):
        q = R.ReliableQueue(visibility=1, max_attempts=3)
        q.put({"id": "late"})
        d = q.receive(now=0)
        self.assertFalse(q.ack(d, now=2))
        self.assertEqual(q.ready_count, 1)
        redelivered = q.receive(now=2)
        self.assertEqual(redelivered.attempt, 2)

    def test_caller_mutation_does_not_change_redelivery(self):
        q = R.ReliableQueue(visibility=1)
        original = {"id": "m2", "payload": {"n": 1}}
        q.put(original)
        original["payload"]["n"] = 99
        first = q.receive(now=0)
        first.message["payload"]["n"] = 77
        again = q.receive(now=2)
        self.assertEqual(again.message["payload"]["n"], 1)

    def test_poison_message_dead_letters_at_cap(self):
        q = R.ReliableQueue(visibility=1, max_attempts=3)
        q.put({"id": "poison"})
        self.assertEqual(q.receive(now=0).attempt, 1)
        self.assertEqual(q.receive(now=1).attempt, 2)
        self.assertEqual(q.receive(now=2).attempt, 3)
        self.assertIsNone(q.receive(now=3))
        self.assertEqual(len(q.dlq), 1)
        self.assertEqual(q.dlq[0].attempts, 3)
        self.assertEqual(q.dlq[0].reason, "visibility_timeout")

    def test_duplicate_active_id_rejected_but_reusable_after_ack(self):
        q = R.ReliableQueue()
        q.put({"id": "same"})
        with self.assertRaises(R.DuplicateMessageError):
            q.put({"id": "same"})
        d = q.receive(now=0)
        self.assertTrue(q.ack(d, now=0))
        q.put({"id": "same"})
        self.assertEqual(q.ready_count, 1)

    def test_string_ack_requires_matching_lease_token(self):
        q = R.ReliableQueue()
        q.put({"id": "m3"})
        d = q.receive(now=0)
        self.assertFalse(q.ack("m3", now=0))
        self.assertFalse(q.ack("m3", "wrong", now=0))
        self.assertTrue(q.ack("m3", d.lease_id, now=0))

    def test_nack_requeue_and_terminal_nack(self):
        q = R.ReliableQueue(max_attempts=3)
        q.put({"id": "m4"})
        first = q.receive(now=0)
        self.assertTrue(q.nack(first, now=0.5))
        second = q.receive(now=0.5)
        self.assertEqual(second.attempt, 2)
        self.assertTrue(q.nack(second, now=0.6, requeue=False, reason="invalid_payload"))
        self.assertEqual(q.dead_letter_count, 1)
        self.assertEqual(q.dlq[0].reason, "invalid_payload")

    def test_visibility_extension_preserves_token(self):
        q = R.ReliableQueue(visibility=2)
        q.put({"id": "m5"})
        d = q.receive(now=0)
        extended = q.extend_visibility(d, now=1, extension=5)
        self.assertEqual(extended.lease_id, d.lease_id)
        self.assertEqual(extended.deadline, 6)
        self.assertIsNone(q.receive(now=3))
        redelivered = q.receive(now=7)
        self.assertNotEqual(redelivered.lease_id, d.lease_id)

    def test_capacity_failure_does_not_drop_in_flight_message(self):
        q = R.ReliableQueue(visibility=1, max_attempts=2, max_ready=1)
        q.put({"id": "m6"})
        d = q.receive(now=0)
        q.put({"id": "blocker"})
        with self.assertRaises(R.QueueCapacityError):
            q.expire(now=2)
        self.assertEqual(q.in_flight_count, 1)
        self.assertTrue(q.ack(d, now=0.5))

    def test_concurrent_put_is_safe(self):
        q = R.ReliableQueue(max_ready=200)
        errors = []

        def worker(i):
            try:
                q.put({"id": f"m-{i}"})
            except Exception as exc:  # pragma: no cover - diagnostic collection
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(q.ready_count, 100)

    def test_input_validation(self):
        with self.assertRaises(ValueError):
            R.ReliableQueue(visibility=0)
        with self.assertRaises(ValueError):
            R.ReliableQueue(max_attempts=0)
        q = R.ReliableQueue()
        with self.assertRaises(ValueError):
            q.put({"id": "   "})
        with self.assertRaises(TypeError):
            q.put([("id", "x")])
        with self.assertRaises(ValueError):
            q.receive(now=float("nan"))


class IdempotentConsumerTest(unittest.TestCase):
    def test_scope_aware_deduplication(self):
        c = R.IdempotentConsumer(max_entries=3)
        self.assertTrue(c.handle({"id": "m"}, scope="tenant-a"))
        self.assertFalse(c.handle({"id": "m"}, scope="tenant-a"))
        self.assertTrue(c.handle({"id": "m"}, scope="tenant-b"))
        self.assertEqual(c.effects, 2)
        self.assertEqual(c.skipped, 1)

    def test_capacity_fails_closed_before_untracked_effect(self):
        c = R.IdempotentConsumer(max_entries=1)
        self.assertTrue(c.handle({"id": "m1"}))
        with self.assertRaises(R.DeduplicationCapacityError):
            c.handle({"id": "m2"})
        self.assertEqual(c.effects, 1)


if __name__ == "__main__":
    unittest.main()
