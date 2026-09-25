"""Standalone behavioral tests for the INV-05 state model (stdlib only)."""
from __future__ import annotations

import pathlib
import sys
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inv05_current_control_state_system.state import (  # noqa: E402
    Compacted,
    ControlState,
    InvalidStateRequest,
)


class StateModelTest(unittest.TestCase):
    def test_compare_and_swap_and_no_partial_write(self):
        state = ControlState()
        self.assertTrue(state.txn({"lease/a": 0}, {"lease/a": "node-1"}))
        first_rev = state.get("lease/a")[1]
        self.assertFalse(state.txn({"lease/a": first_rev + 1}, {"lease/a": "bad"}))
        self.assertEqual(state.get("lease/a"), ("node-1", first_rev))

    def test_compare_and_write_are_atomic_between_threads(self):
        state = ControlState()
        self.assertTrue(state.txn({"lease/a": 0}, {"lease/a": "seed"}))
        expected = state.get("lease/a")[1]
        barrier = threading.Barrier(17)
        results: list[bool] = []
        result_lock = threading.Lock()

        def contender(n: int) -> None:
            barrier.wait()
            won = state.txn({"lease/a": expected}, {"lease/a": f"node-{n}"})
            with result_lock:
                results.append(won)

        threads = [threading.Thread(target=contender, args=(n,)) for n in range(16)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(timeout=5)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count(False), 15)

    def test_watch_compaction_never_silently_gaps(self):
        state = ControlState()
        for i in range(10):
            self.assertTrue(state.txn({}, {f"k{i}": i}))
        self.assertEqual([e[0] for e in state.watch(5)], [5, 6, 7, 8, 9, 10])
        self.assertEqual(state.compact(6), 6)
        with self.assertRaises(Compacted):
            state.watch(5)
        self.assertEqual([e[0] for e in state.watch(7)], [7, 8, 9, 10])

    def test_invalid_revisions_and_keys_fail_closed(self):
        state = ControlState()
        for bad in (-1, True, 1.5, "1"):
            with self.subTest(bad=bad):
                with self.assertRaises(InvalidStateRequest):
                    state.watch(bad)
        with self.assertRaises(InvalidStateRequest):
            state.txn({"a": -1}, {"a": 1})
        with self.assertRaises(InvalidStateRequest):
            state.txn({}, {"": 1})
        with self.assertRaises(InvalidStateRequest):
            state.txn({}, {"bad\x00key": 1})

    def test_compaction_cannot_advance_beyond_current_revision(self):
        state = ControlState()
        state.txn({}, {"a": 1})
        with self.assertRaises(InvalidStateRequest):
            state.compact(2)
        self.assertEqual(state.compacted_at, 0)
        self.assertEqual([e[0] for e in state.watch(1)], [1])

    def test_exposed_containers_are_snapshots(self):
        state = ControlState()
        state.txn({}, {"a": 1})
        data = state.data
        history = state.history
        data.clear()
        history.clear()
        self.assertEqual(state.get("a"), (1, 1))
        self.assertEqual(len(state.history), 1)


if __name__ == "__main__":
    unittest.main()
