"""Closure #15: terminal race contract - deterministic interleavings plus randomized stress."""
import itertools
import random
import threading
import unittest

from _util import rt, scale

AF = rt.AsyncFunctions
OPS = ("complete", "cancel", "trap_all", "cancel_all")


def run(f, op, cid):
    try:
        if op == "complete":
            f.complete(cid, "v")
            return "completed"
        if op == "cancel":
            f.cancel(cid, "caller")
            return "cancelled"
        if op == "trap_all":
            return "trapped" if f.trap_all() else "noop"
        return "cancelled" if f.cancel_all("parent") else "noop"
    except rt.TerminalConflict as e:
        return type(e).__name__


def check_invariants(tc, f, cids, dd=0):
    s = f.snapshot()
    tc.assertEqual(s["calls_in_flight"], 0)
    outcomes = [f.terminal_info(c).outcome for c in cids]
    tc.assertTrue(all(o is not None for o in outcomes))
    tc.assertEqual(s["completed_calls"] + s["cancelled_calls"] + s["trapped_calls"], len(cids))
    tc.assertEqual(s["completed_calls"], outcomes.count(rt.Outcome.COMPLETED))
    tc.assertEqual(s["double_delivery_attempts"], dd)  # counter == rejected duplicate completions


class DeterministicInterleavings(unittest.TestCase):
    def test_every_ordered_pair(self):
        """For each pair (A first, then B): exactly one winner, loser gets the table's result."""
        for a, b in itertools.product(OPS, repeat=2):
            with self.subTest(first=a, second=b):
                f = AF("i", declared={"x": True})
                cid = f.invoke("x").call_id
                r1, r2 = run(f, a, cid), run(f, b, cid)
                self.assertIn(r1, ("completed", "cancelled", "trapped"))
                tomb = f.terminal_info(cid)
                self.assertEqual(tomb.outcome.value, r1)
                if b == "complete":
                    self.assertEqual(r2, {"completed": "DoubleDelivery", "cancelled": "CallCancelled",
                                          "trapped": "CallTrapped"}[r1])
                elif b == "cancel":
                    self.assertEqual(r2, "AlreadyTerminal")
                else:
                    self.assertEqual(r2, "noop")
                self.assertEqual(f.completed_calls + f.cancelled_calls + f.trapped_calls, 1)

    def test_barrier_forced_simultaneous_pairs(self):
        for a, b in itertools.product(OPS, repeat=2):
            for _ in range(scale(40)):
                f = AF("i", declared={"x": True})
                cid = f.invoke("x").call_id
                bar = threading.Barrier(2)
                res = {}

                def go(op, key):
                    bar.wait()
                    res[key] = run(f, op, cid)

                ts = [threading.Thread(target=go, args=(a, 0)), threading.Thread(target=go, args=(b, 1))]
                for t in ts:
                    t.start()
                for t in ts:
                    t.join()
                winners = [r for r in res.values() if r in ("completed", "cancelled", "trapped")]
                self.assertEqual(len(winners), 1, (a, b, res))
                self.assertEqual(f.terminal_info(cid).outcome.value, winners[0])
                check_invariants(self, f, [cid], list(res.values()).count("DoubleDelivery"))


class RandomizedStress(unittest.TestCase):
    def test_many_calls_many_threads(self):
        rng = random.Random(0x1616)
        for batch in range(scale(20)):
            f = AF("i", declared={"x": True})
            cids = [f.invoke("x").call_id for _ in range(64)]
            plan = [(rng.choice(OPS[:2]), rng.choice(cids)) for _ in range(400)]
            plan += [("cancel_all", None)]
            chunks = [plan[i::8] for i in range(8)]
            bar = threading.Barrier(8)

            def worker(ch):
                bar.wait()
                for op, cid in ch:
                    run(f, op, cid)

            ts = [threading.Thread(target=worker, args=(c,)) for c in chunks]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
            f.cancel_all("drain")
            s = f.snapshot()
            self.assertEqual(s["calls_in_flight"], 0)
            self.assertEqual(s["completed_calls"] + s["cancelled_calls"] + s["trapped_calls"], len(cids))
            outcomes = [f.terminal_info(c).outcome for c in cids]
            self.assertEqual(s["completed_calls"], outcomes.count(rt.Outcome.COMPLETED))

    def test_duplicate_complete_race_counts_exactly(self):
        for _ in range(scale(200)):
            f = AF("i", declared={"x": True})
            cid = f.invoke("x").call_id
            bar = threading.Barrier(4)
            wins = []

            def go():
                bar.wait()
                try:
                    f.complete(cid, 1)
                    wins.append(1)
                except rt.DoubleDelivery:
                    pass

            ts = [threading.Thread(target=go) for _ in range(4)]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
            self.assertEqual(len(wins), 1)
            self.assertEqual(f.double_delivery_attempts, 3)


if __name__ == "__main__":
    unittest.main()
