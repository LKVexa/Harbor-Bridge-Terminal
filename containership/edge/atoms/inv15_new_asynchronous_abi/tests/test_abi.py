"""Dependency-free runtime tests for the INV-15 asynchronous ABI model."""
from __future__ import annotations

import pathlib
import sys
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inv15_new_asynchronous_abi import (  # noqa: E402
    AsyncAbi,
    BudgetExhausted,
    ForeignHandle,
    HandleConsumed,
    SubtaskHandle,
    SubtaskNotReady,
    WaitSetTooLarge,
    __version__,
)


class AsyncAbiRuntimeTest(unittest.TestCase):
    def test_version(self):
        self.assertEqual(__version__, "4.3.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text().strip(), "4.3.0")

    def test_immediate_none_is_a_value(self):
        self.assertEqual(AsyncAbi("x").call(immediate=None), ("value", None))

    def test_take_requires_ready_and_is_single_use(self):
        abi = AsyncAbi("x")
        _, handle = abi.call()
        with self.assertRaises(SubtaskNotReady):
            abi.take(handle)
        abi.complete(handle, None)
        self.assertIsNone(abi.take(handle))
        with self.assertRaises(HandleConsumed):
            abi.take(handle)

    def test_generator_wait_and_set_semantics(self):
        abi = AsyncAbi("x", budget=2)
        _, h1 = abi.call()
        _, h2 = abi.call()
        abi.complete(h2, "ok")
        self.assertEqual(abi.wait(iter([h1, h2])), [h2])
        self.assertEqual(abi.wait([h2, h2]), [h2])

    def test_wait_set_is_bounded(self):
        abi = AsyncAbi("x", budget=2)
        _, h1 = abi.call()
        _, h2 = abi.call()
        with self.assertRaises(WaitSetTooLarge):
            abi.wait([h1, h2, h1])

    def test_cross_instance_numeric_collision_is_rejected(self):
        a, b = AsyncAbi("a"), AsyncAbi("b")
        _, ha = a.call()
        _, hb = b.call()
        self.assertEqual(ha.sequence, hb.sequence)
        self.assertNotEqual(ha, hb)
        with self.assertRaises(ForeignHandle):
            b.wait([ha])

    def test_one_handle_cannot_forge_another_in_same_instance(self):
        abi = AsyncAbi("x")
        _, first = abi.call()
        _, second = abi.call()
        forged = SubtaskHandle(first.token, second.sequence)
        self.assertNotEqual(forged, second)
        with self.assertRaises(ForeignHandle):
            abi.wait([forged])

    def test_live_table_snapshot_is_read_only(self):
        abi = AsyncAbi("x")
        _, handle = abi.call()
        with self.assertRaises(TypeError):
            abi.table[handle] = abi.table[handle]

    def test_cancel_one_and_cancel_all_release_rows(self):
        abi = AsyncAbi("x")
        _, pending = abi.call()
        _, ready = abi.call()
        abi.complete(ready, "done")
        self.assertTrue(abi.cancel(pending, "test"))
        self.assertFalse(abi.cancel(ready, "test"))
        self.assertEqual(abi.open_subtasks, 0)
        self.assertEqual(abi.cancellations, 1)
        self.assertEqual(abi.abandoned_ready, 1)

        handles = [abi.call()[1] for _ in range(3)]
        abi.complete(handles[-1], "done")
        self.assertEqual(abi.cancel_all("caller gone"), 2)
        self.assertEqual(abi.open_subtasks, 0)
        self.assertEqual(abi.abandoned_ready, 2)

    def test_budget_counts_only_live_rows(self):
        abi = AsyncAbi("x", budget=1)
        _, h = abi.call()
        with self.assertRaises(BudgetExhausted):
            abi.call()
        abi.complete(h, 1)
        self.assertEqual(abi.take(h), 1)
        abi.call()  # row was retired, so capacity is reusable

    def test_tombstones_are_bounded(self):
        abi = AsyncAbi("x", budget=1, tombstone_limit=3)
        for i in range(10):
            _, h = abi.call()
            abi.complete(h, i)
            self.assertEqual(abi.take(h), i)
        self.assertLessEqual(abi.snapshot()["retired_tombstones"], 3)

    def test_concurrent_allocations_are_unique_and_bounded(self):
        abi = AsyncAbi("x", budget=64)
        handles = []
        failures = []
        lock = threading.Lock()

        def worker():
            try:
                _, handle = abi.call()
                with lock:
                    handles.append(handle)
            except Exception as exc:  # pragma: no cover - captured for assertion
                with lock:
                    failures.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(64)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(failures, [])
        self.assertEqual(len(handles), 64)
        self.assertEqual(len(set(handles)), 64)
        self.assertEqual(abi.open_subtasks, 64)
        with self.assertRaises(BudgetExhausted):
            abi.call()


if __name__ == "__main__":
    unittest.main()
