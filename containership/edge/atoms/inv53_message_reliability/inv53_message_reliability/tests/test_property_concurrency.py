"""Model-based property tests, crash-anywhere recovery, concurrency (components 47, 73, 74, 77)."""
from __future__ import annotations

import random
import threading
import unittest

from _support import TmpDirCase
from inv53_message_reliability.durable import DurableQueue, StorageError
from inv53_message_reliability.reliability import DuplicateMessageError, QueueCapacityError, ReliableQueue


def run_ops(q, rng, n, ids, t0=0.0):
    """Drive a queue with a random op sequence; return ledger of accepted ids and acked ids."""
    accepted, acked, live = set(), set(), []
    now = t0
    for _ in range(n):
        now += rng.choice([0, 0.5, 1, 3, 7])
        op = rng.random()
        try:
            if op < 0.35:
                mid = rng.choice(ids)
                q.put({"id": mid})
                accepted.add(mid)
            elif op < 0.6:
                d = q.receive(now=now)
                if d:
                    live.append(d)
            elif op < 0.8 and live:
                d = live.pop(rng.randrange(len(live)))
                if q.ack(d, now=now):
                    acked.add(d.message_id)
            elif op < 0.9 and live:
                d = live.pop(rng.randrange(len(live)))
                q.nack(d, now=now, requeue=rng.random() < 0.7)
            elif live:
                q.extend_visibility(live[-1], now=now, extension=rng.choice([1, 4]))
        except (DuplicateMessageError, QueueCapacityError):
            pass
    return accepted, acked, now


def census(q):
    s = q.snapshot()
    return s["ready"] + s["in_flight"] + s["dead_lettered"]


class PropertyTest(TmpDirCase):
    def test_durable_equals_reference_model(self):
        """Same seed, same op sequence: the durable queue and the reference agree on every counter."""
        for seed in range(25):
            ref = ReliableQueue(visibility=5, max_attempts=3, max_ready=40)
            d = DurableQueue(self.tmp / f"d{seed}", visibility=5, max_attempts=3, max_ready=40, fsync=False)
            ids = [f"m{i}" for i in range(15)]
            # uuid lease tokens differ, so drive both with identical decisions via the same seed
            run_ops(ref, random.Random(seed), 300, ids)
            run_ops(d, random.Random(seed), 300, ids)
            a, b = ref.snapshot(), d.snapshot()
            for k in ("ready", "in_flight", "dead_lettered", "acks", "nacks", "redeliveries", "tracked_attempts"):
                self.assertEqual(a[k], b[k], f"seed {seed} {k}")
            d.close()

    def test_no_message_is_ever_lost(self):
        """Every accepted id is acked, in flight, ready or dead-lettered -- never nowhere."""
        for seed in range(40):
            q = ReliableQueue(visibility=3, max_attempts=3)
            rng = random.Random(seed)
            ids = [f"m{i}" for i in range(8)]
            accepted, acked, now = run_ops(q, rng, 400, ids)
            q.expire(now=now + 1_000)
            held = {m["id"] for m in [dl.message for dl in q.dlq]} | set(q._active_ids)
            for mid in accepted:
                self.assertTrue(mid in held or mid in acked, f"seed {seed}: {mid} vanished")
            self.assertEqual(q.in_flight_count, 0)
            self.assertLessEqual(q.snapshot()["tracked_attempts"], q.ready_count, "attempt state only for held work")

    def test_crash_at_any_write_then_recover_preserves_invariants(self):
        """Inject a crash at a random journal write; recovery must open cleanly and nothing is lost."""
        for seed in range(30):
            rng = random.Random(seed)
            crash_at = rng.randrange(5, 200)
            counter = {"n": 0}
            point = rng.choice(["before_write", "after_write"])

            def fault(p, op):
                if p == point:
                    counter["n"] += 1
                    if counter["n"] == crash_at:
                        raise OSError("injected crash")
            path = self.tmp / f"c{seed}"
            q = DurableQueue(path, visibility=4, max_attempts=50, fsync=False, fault=fault)
            owned, pending = set(), None           # ids the broker must still hold, per the caller's view
            try:
                ids = [f"m{i}" for i in range(12)]
                now = 0.0
                for _ in range(300):
                    now += 1
                    try:
                        if rng.random() < 0.5:
                            mid = rng.choice(ids)
                            pending = mid
                            if q.put({"id": mid}):
                                owned.add(mid)
                        else:
                            pending = None
                            d = q.receive(now=now)
                            if d and rng.random() < 0.6:
                                pending = d.message_id
                                if q.ack(d, now=now):
                                    owned.discard(d.message_id)
                        pending = None
                    except DuplicateMessageError:
                        pending = None
            except StorageError:
                pass
            self.assertGreaterEqual(counter["n"], crash_at, "the injected crash must actually fire")
            q.close()
            r = DurableQueue(path, visibility=4, max_attempts=50, fsync=False)
            held = set(r._state.msgs)
            fuzzy = {pending} if pending else set()
            self.assertEqual(held - fuzzy, owned - fuzzy, f"seed {seed} point {point}: durable state != caller view")
            r.close()


class ConcurrencyTest(TmpDirCase):
    def _hammer(self, q, n_msgs=400, workers=8):
        for i in range(n_msgs):
            q.put({"id": f"m{i}"})
        acked, leases, lock = [], set(), threading.Lock()
        barrier = threading.Barrier(workers)

        def worker():
            barrier.wait()
            while True:
                d = q.receive(now=0)
                if d is None:
                    return
                with lock:
                    self_dup = d.lease_id in leases
                    leases.add(d.lease_id)
                if q.ack(d, now=0):
                    with lock:
                        acked.append(d.message_id)
                assert not self_dup
        ts = [threading.Thread(target=worker) for _ in range(workers)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        return acked

    def test_reference_queue_each_message_acked_exactly_once(self):
        acked = self._hammer(ReliableQueue(visibility=1000, max_attempts=3))
        self.assertEqual(sorted(acked), sorted(f"m{i}" for i in range(400)))

    def test_durable_queue_each_message_acked_exactly_once(self):
        q = DurableQueue(self.tmp / "c", visibility=1000, max_attempts=3, fsync=False)
        acked = self._hammer(q, n_msgs=200)
        self.assertEqual(len(acked), len(set(acked)))
        self.assertEqual(len(acked), 200)
        q.close()
        r = DurableQueue(self.tmp / "c", visibility=1000, max_attempts=3, fsync=False)
        self.assertEqual(r.snapshot()["acks"], 200)
        r.close()

    def test_racing_stale_and_fresh_acks(self):
        """A stale ack racing a fresh ack of the same message: exactly one wins, and it is the fresh one."""
        for _ in range(50):
            q = ReliableQueue(visibility=1, max_attempts=5)
            q.put({"id": "x"})
            stale = q.receive(now=0)
            fresh = q.receive(now=2)
            results = {}
            b = threading.Barrier(2)

            def go(name, d):
                b.wait()
                results[name] = q.ack(d, now=2)
            ts = [threading.Thread(target=go, args=("stale", stale)), threading.Thread(target=go, args=("fresh", fresh))]
            [t.start() for t in ts]
            [t.join() for t in ts]
            self.assertEqual(results, {"stale": False, "fresh": True})


if __name__ == "__main__":
    unittest.main()
