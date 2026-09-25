"""Standalone behavioural tests for INV-14's legacy polling primitive.

These tests deliberately do not import ``pk_core``.  They must run even when the
larger post-Kubernetes framework is not installed, preventing a missing optional
framework from turning every behavioural test into a skip.
"""
from __future__ import annotations

import pathlib
import sys
import threading
import time
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

from polling import (  # noqa: E402
    ForeignPollable,
    MIGRATION_TARGET,
    PollSet,
    PollValidationError,
    Pollable,
)


class PollingPrimitiveTest(unittest.TestCase):
    def test_presignalled_readiness_is_latched(self):
        p = Pollable("net", "inst-1")
        p.signal()
        result = PollSet("inst-1").poll([p], timeout_ticks=20)
        self.assertEqual(result["ready"], ["net"])
        self.assertEqual(result["ready_indexes"], [0])
        self.assertFalse(result["timed_out"])
        self.assertTrue(result["deprecated"])
        self.assertEqual(result["migrate_to"], MIGRATION_TARGET)

    def test_poll_actually_blocks_until_signal(self):
        p = Pollable("timer", "inst-1")
        ps = PollSet("inst-1")

        def signal_later():
            time.sleep(0.015)
            p.signal()

        t = threading.Thread(target=signal_later, daemon=True)
        t.start()
        started = time.monotonic()
        result = ps.poll([p], timeout_ticks=250)
        elapsed = time.monotonic() - started
        t.join(timeout=1)
        self.assertFalse(result["timed_out"])
        self.assertEqual(result["ready"], ["timer"])
        self.assertGreaterEqual(elapsed, 0.005)
        self.assertLess(elapsed, 0.25)

    def test_timeout_is_bounded_and_observable(self):
        p = Pollable("idle", "inst-1")
        ps = PollSet("inst-1")
        started = time.monotonic()
        result = ps.poll([p], timeout_ticks=8)
        elapsed = time.monotonic() - started
        self.assertTrue(result["timed_out"])
        self.assertEqual(result["ready"], [])
        self.assertGreaterEqual(elapsed, 0.004)
        self.assertLess(elapsed, 0.20)

    def test_signal_race_is_not_lost(self):
        for i in range(40):
            p = Pollable(f"p-{i}", "inst-1")
            ps = PollSet("inst-1")
            t = threading.Thread(target=p.signal, daemon=True)
            t.start()
            result = ps.poll([p], timeout_ticks=100)
            t.join(timeout=1)
            self.assertFalse(result["timed_out"], i)
            self.assertEqual(result["ready"], [f"p-{i}"])
            self.assertEqual(len(p._waiters), 0, "waiter leaked after poll completion")

    def test_multiple_waiters_receive_same_level_trigger(self):
        p = Pollable("shared", "inst-1")
        outcomes = []
        lock = threading.Lock()

        def waiter():
            result = PollSet("inst-1").poll([p], timeout_ticks=250)
            with lock:
                outcomes.append(result["ready"])

        threads = [threading.Thread(target=waiter, daemon=True) for _ in range(2)]
        for t in threads:
            t.start()
        time.sleep(0.01)
        p.signal()
        for t in threads:
            t.join(timeout=1)
        self.assertEqual(sorted(outcomes), [["shared"], ["shared"]])

    def test_clear_allows_a_later_readiness_cycle(self):
        p = Pollable("cycle", "inst-1")
        ps = PollSet("inst-1")
        p.signal()
        self.assertEqual(ps.poll([p], timeout_ticks=10)["ready"], ["cycle"])
        p.clear()
        self.assertTrue(ps.poll([p], timeout_ticks=4)["timed_out"])
        p.signal()
        self.assertEqual(ps.poll([p], timeout_ticks=10)["ready"], ["cycle"])

    def test_foreign_pollable_is_refused_with_structured_error(self):
        ps = PollSet("inst-1")
        with self.assertRaises(ForeignPollable) as cm:
            ps.poll([Pollable("other", "inst-2")], timeout_ticks=10)
        payload = cm.exception.as_dict()
        self.assertEqual(payload["schema"], "PK_POLL_ERROR/1")
        self.assertEqual(payload["code"], "PK_POLL_FOREIGN_OWNER")
        self.assertEqual(payload["migrate_to"], MIGRATION_TARGET)
        self.assertEqual(ps.metrics_snapshot()["cross_instance_refusals"], 1)

    def test_invalid_requests_fail_closed(self):
        ps = PollSet("inst-1", max_timeout_ticks=10, max_pollables=2)
        bad_calls = [
            lambda: ps.poll([], timeout_ticks=1),
            lambda: ps.poll([Pollable("a", "inst-1")], timeout_ticks=0),
            lambda: ps.poll([Pollable("a", "inst-1")], timeout_ticks=True),
            lambda: ps.poll([Pollable("a", "inst-1")], timeout_ticks=1.0),
            lambda: ps.poll([Pollable("a", "inst-1")], timeout_ticks=11),
            lambda: ps.poll([object()], timeout_ticks=1),
            lambda: ps.poll((p for p in [Pollable("a", "inst-1")]), timeout_ticks=1),
            lambda: ps.poll([Pollable("a", "inst-1"), Pollable("b", "inst-1"), Pollable("c", "inst-1")], timeout_ticks=1),
        ]
        for call in bad_calls:
            with self.assertRaises(PollValidationError):
                call()
        self.assertEqual(ps.metrics_snapshot()["invalid_requests"], len(bad_calls))

    def test_duplicate_handle_and_duplicate_name_are_refused(self):
        ps = PollSet("inst-1")
        p = Pollable("same", "inst-1")
        with self.assertRaises(PollValidationError) as cm:
            ps.poll([p, p], timeout_ticks=10)
        self.assertEqual(cm.exception.code, "PK_POLL_DUPLICATE_HANDLE")
        with self.assertRaises(PollValidationError) as cm:
            ps.poll([Pollable("same", "inst-1"), Pollable("same", "inst-1")], timeout_ticks=10)
        self.assertEqual(cm.exception.code, "PK_POLL_DUPLICATE_NAME")

    def test_identity_and_limit_validation(self):
        for args in [("", "owner"), ("name", ""), (None, "owner")]:
            with self.assertRaises(PollValidationError):
                Pollable(*args)
        with self.assertRaises(PollValidationError):
            PollSet("")
        with self.assertRaises(PollValidationError):
            PollSet("owner", tick_seconds=float("inf"))
        with self.assertRaises(PollValidationError):
            PollSet("owner", max_pollables=True)

    def test_hard_wall_clock_duration_ceiling(self):
        ps = PollSet("inst-1", tick_seconds=10.0, max_timeout_ticks=100)
        with self.assertRaises(PollValidationError) as cm:
            ps.poll([Pollable("a", "inst-1")], timeout_ticks=7)
        self.assertEqual(cm.exception.code, "PK_POLL_DURATION_LIMIT")

    def test_metrics_are_bounded_aggregates(self):
        ps = PollSet("inst-1")
        p = Pollable("a", "inst-1")
        ps.poll([p], timeout_ticks=2)
        p.signal()
        ps.poll([p], timeout_ticks=10)
        m = ps.metrics_snapshot()
        self.assertEqual(m["deprecated_uses"], 2)
        self.assertEqual(m["polls_timeout"], 1)
        self.assertEqual(m["polls_ready"], 1)
        self.assertEqual(m["total_pollables"], 2)
        self.assertEqual(m["max_set_size_seen"], 1)


if __name__ == "__main__":
    unittest.main()
