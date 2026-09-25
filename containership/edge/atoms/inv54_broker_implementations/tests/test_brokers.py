"""Dependency-free behavioural and hardening tests for the reference brokers."""
from __future__ import annotations

import importlib
import pathlib
from dataclasses import FrozenInstanceError
import sys
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pkg = importlib.import_module(PKG_DIR.name)
FanoutBroker = pkg.FanoutBroker
PartitionedLog = pkg.PartitionedLog


class FanoutBrokerTest(unittest.TestCase):
    def test_fanout_is_complete_and_isolated(self):
        broker = FanoutBroker()
        a = broker.subscribe("a")
        b = broker.subscribe("b")
        message = {"items": [1]}
        self.assertEqual(broker.publish(message), 2)
        self.assertEqual(a, [message])
        self.assertEqual(b, [message])
        self.assertIsNot(a[0], b[0])
        self.assertIsNot(a[0]["items"], b[0]["items"])
        a[0]["items"].append(2)
        self.assertEqual(b[0], {"items": [1]})
        self.assertEqual(message, {"items": [1]})

    def test_copy_failure_is_atomic(self):
        class NotCopyable:
            def __deepcopy__(self, memo):
                raise RuntimeError("no")

        broker = FanoutBroker()
        a = broker.subscribe("a")
        b = broker.subscribe("b")
        with self.assertRaises(TypeError):
            broker.publish(NotCopyable())
        self.assertEqual(a, [])
        self.assertEqual(b, [])

    def test_subscriber_validation_and_unsubscribe(self):
        broker = FanoutBroker()
        with self.assertRaises(TypeError):
            broker.subscribe(1)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            broker.subscribe("")
        broker.subscribe("a")
        self.assertTrue(broker.unsubscribe("a"))
        self.assertFalse(broker.unsubscribe("a"))

    def test_internal_state_cannot_be_injected_at_construction(self):
        with self.assertRaises(TypeError):
            FanoutBroker(subscribers={"spoofed": []})  # type: ignore[call-arg]


class PartitionedLogTest(unittest.TestCase):
    def test_order_replay_and_independent_offsets(self):
        log = PartitionedLog(partitions=1)
        for i in range(6):
            log.append("k", i)
        self.assertEqual([m for _, m in log.poll("c1", 0, 2)], [0, 1])
        self.assertEqual([m for _, m in log.poll("c2", 0, 1)], [0])
        log.seek("c1", 0, 1)
        self.assertEqual([m for _, m in log.poll("c1", 0)], [1, 2, 3, 4, 5])
        self.assertEqual(log.committed_offset("c2", 0), 1)
        self.assertEqual(log.end_offset(0), 6)

    def test_partition_count_validation(self):
        for value, exc in [(0, ValueError), (-1, ValueError), (True, TypeError), (1.5, TypeError)]:
            with self.subTest(value=value), self.assertRaises(exc):
                PartitionedLog(partitions=value)  # type: ignore[arg-type]

    def test_index_limit_offset_and_identity_validation(self):
        log = PartitionedLog(partitions=2)
        log.append("k", 1)
        for partition in (-1, 2):
            with self.subTest(partition=partition), self.assertRaises((ValueError, IndexError)):
                log.poll("c", partition)
        with self.assertRaises(TypeError):
            log.poll("c", True)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            log.poll("c", 0, -1)
        with self.assertRaises(TypeError):
            log.poll("c", 0, True)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            log.poll("c", 0, 1.5)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            log.seek("c", 0, -1)
        with self.assertRaises(IndexError):
            log.seek("c", 0, log.end_offset(0) + 1)
        with self.assertRaises(TypeError):
            log.seek("c", 0, True)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            log.poll("", 0)
        with self.assertRaises(TypeError):
            log.append(1, "bad")  # type: ignore[arg-type]

    def test_internal_state_cannot_be_injected_at_construction(self):
        with self.assertRaises(TypeError):
            PartitionedLog(logs=[[('k', 1)]])  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            PartitionedLog(offsets={("c", 0): 99})  # type: ignore[call-arg]

    def test_partition_count_cannot_be_rebound(self):
        log = PartitionedLog(partitions=2)
        with self.assertRaises(FrozenInstanceError):
            log.partitions = 8  # type: ignore[misc]

    def test_concurrent_appends_do_not_lose_records(self):
        log = PartitionedLog(partitions=1)
        start = threading.Barrier(5)

        def writer(worker: int) -> None:
            start.wait()
            for i in range(250):
                log.append("shared", (worker, i))

        threads = [threading.Thread(target=writer, args=(n,)) for n in range(4)]
        for thread in threads:
            thread.start()
        start.wait()
        for thread in threads:
            thread.join()
        self.assertEqual(log.end_offset(0), 1000)
        self.assertEqual(len(log.poll("reader", 0, 2000)), 1000)


if __name__ == "__main__":
    unittest.main()
