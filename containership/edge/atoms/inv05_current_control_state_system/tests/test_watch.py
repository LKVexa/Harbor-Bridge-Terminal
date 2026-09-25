"""Watch ordering, progress, resume, slow consumers, quotas, drain (MC-014, MC-015, MC-017)."""
from __future__ import annotations

import threading
import time
import unittest

import _util  # noqa: F401
from inv05_current_control_state_system.errors import CompactedError, Draining, LimitExceeded, QuotaExceeded
from inv05_current_control_state_system.store import ControlStore, Delete, Put
from inv05_current_control_state_system.watch import WatchHub


class WatchTest(unittest.TestCase):
    def setUp(self):
        self.s = ControlStore()
        self.hub = WatchHub(self.s, max_queue=100, max_per_owner=2, max_total=5)

    def test_ordering_and_txn_grouping(self):
        w = self.hub.create(prefix="a/")
        self.s.txn((), [Put("a/1", 1), Put("a/2", 2), Put("b/1", 0)])
        self.s.delete("a/1")
        f1, f2 = w.poll(0.1), w.poll(0.1)
        self.assertEqual([e["key"] for e in f1.events], ["a/1", "a/2"])
        self.assertEqual({e["revision"] for e in f1.events}, {1})
        self.assertEqual(f2.events[0]["kind"], "DELETE")
        self.assertLess(f1.revision, f2.revision)

    def test_catch_up_from_revision_and_resume(self):
        for i in range(5):
            self.s.put("k", i)
        w = self.hub.create(start_revision=3)
        revs = [w.poll(0.1).revision for _ in range(3)]
        self.assertEqual(revs, [3, 4, 5])
        w.cancel()
        self.s.put("k", 99)
        w2 = self.hub.create(start_revision=w.last_revision + 1)  # resume token
        self.assertEqual(w2.poll(0.1).events[0]["value"], 99)

    def test_progress_frames_do_not_fabricate_events(self):
        w = self.hub.create(prefix="none/")
        self.s.put("other", 1)
        f = w.poll(0.05)
        self.assertEqual((f.type, f.events, f.revision), ("progress", [], 1))

    def test_compacted_start_refused(self):
        for i in range(5):
            self.s.put("k", i)
        self.s.compact(3)
        with self.assertRaises(CompactedError):
            self.hub.create(start_revision=3)
        self.hub.create(start_revision=4)

    def _drain(self, w):
        out = []
        while True:
            f = w.poll(0.01)
            if f.type != "events":
                return out, f
            out.extend(e["revision"] for e in f.events)

    def test_slow_consumer_falls_back_losslessly(self):
        w = self.hub.create()
        for i in range(150):
            self.s.put("k", i)
        revs, last = self._drain(w)
        self.assertEqual(revs, list(range(1, 151)))
        self.assertEqual(last.type, "progress")
        self.assertGreaterEqual(self.hub.counters["slow_consumer_fallbacks"], 1)

    def test_large_catch_up_is_paged(self):
        for i in range(450):
            self.s.put("k", i)
        w = self.hub.create(start_revision=1)
        revs, _ = self._drain(w)
        self.assertEqual(revs, list(range(1, 451)))

    def test_lagging_watch_cancelled_as_slow_consumer(self):
        hub = WatchHub(self.s, max_queue=10, max_lag=50)
        w = hub.create()
        for i in range(80):
            self.s.put("k", i)
        _, last = self._drain(w)
        self.assertEqual(last.error["code"], "CSTATE_SLOW_CONSUMER")
        self.assertEqual(last.error["details"]["resume_revision"], 11)

    def test_compaction_overtaking_catch_up_tells_client_to_relist(self):
        w = self.hub.create()
        for i in range(150):
            self.s.put("k", i)
        f = w.poll(0.01)  # first live page
        self.s.compact(140)
        _, last = self._drain(w)
        self.assertEqual(last.error["code"], "CSTATE_COMPACTED")

    def test_quotas(self):
        self.hub.create(owner="x")
        self.hub.create(owner="x")
        with self.assertRaises(QuotaExceeded):
            self.hub.create(owner="x")
        for _ in range(3):
            self.hub.create(owner="y" + str(_))
        with self.assertRaises(LimitExceeded):
            self.hub.create(owner="z")

    def test_drain_sends_terminal_frames(self):
        w = self.hub.create()
        n = self.hub.drain(0.2)
        self.assertEqual(n, 1)
        f = w.poll(0.1)
        self.assertEqual(f.error["code"], "CSTATE_DRAINING")
        with self.assertRaises(Draining):
            self.hub.create()

    def test_continuous_writers_during_watch(self):
        w = self.hub.create(prefix="c/")
        got = []
        stop = threading.Event()

        def reader():
            while not stop.is_set() or w.backlog:
                f = w.poll(0.02)
                if f.type == "events":
                    got.extend(e["revision"] for e in f.events)
        t = threading.Thread(target=reader)
        t.start()
        for i in range(80):
            self.s.put(f"c/{i % 7}", i)
            if i % 10 == 0:
                time.sleep(0.001)
        stop.set()
        t.join()
        self.assertEqual(got, list(range(1, 81)))

    def test_kind_filter_and_prev_value(self):
        w = self.hub.create(kinds={"DELETE"}, with_prev=True)
        self.s.put("k", 1)
        self.s.txn((), [Delete("k")])
        f = w.poll(0.1)
        self.assertEqual((f.events[0]["kind"], f.events[0]["prev_value"]), ("DELETE", 1))


if __name__ == "__main__":
    unittest.main()
