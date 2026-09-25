"""Closures #16 (re-entrancy race stress) and #17 (concurrency-limit stress/fairness)."""
import random
import sys
import threading
import time
import unittest

from _util import rt, scale

AF = rt.AsyncFunctions


class Overlap:
    """Invariant sampler: records max concurrent *admitted* executions per function."""

    def __init__(self):
        self.lock = threading.Lock()
        self.active = {}
        self.max = {}

    def enter(self, fn):
        with self.lock:
            self.active[fn] = self.active.get(fn, 0) + 1
            self.max[fn] = max(self.max.get(fn, 0), self.active[fn])

    def leave(self, fn):
        with self.lock:
            self.active[fn] -= 1


class ReentrancyStress(unittest.TestCase):
    def _contend(self, f, fn, threads, per_thread, seed):
        ov = Overlap()
        counts = {"admitted": 0, "refused": 0}
        cl = threading.Lock()
        bar = threading.Barrier(threads)

        def worker(k):
            rng = random.Random(seed * 1000 + k)
            bar.wait()
            for _ in range(per_thread):
                try:
                    st = f.invoke(fn)
                except rt.ReentrancyRefused:
                    with cl:
                        counts["refused"] += 1
                    continue
                ov.enter(fn)
                with cl:
                    counts["admitted"] += 1
                if rng.random() < 0.3:
                    time.sleep(0)
                ov.leave(fn)          # leave *before* the terminal transition frees the slot
                if rng.random() < 0.8:
                    f.complete(st.call_id, k)
                else:
                    f.cancel(st.call_id, "caller")

        ts = [threading.Thread(target=worker, args=(k,)) for k in range(threads)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        return ov, counts

    def test_stateful_never_double_admitted(self):
        seeds = range(scale(6))
        total = 0
        for seed in seeds:
            for threads in (2, 8, 16):
                f = AF(f"i{seed}", declared={"s": True, "o": True}, stateful=frozenset({"s"}))
                ov, counts = self._contend(f, "s", threads, scale(400), seed)
                total += counts["admitted"] + counts["refused"]
                self.assertEqual(ov.max.get("s", 0), 1, f"overlap seed={seed} threads={threads}")
                self.assertEqual(f.reentrancy_refusals, counts["refused"])   # counter reconciliation
                self.assertEqual(f.completed_calls + f.cancelled_calls, counts["admitted"])
                self.assertEqual(f.calls_in_flight, 0)
        self.assertGreaterEqual(total, scale(6) * 26 * scale(400))

    def test_rapid_complete_reinvoke(self):
        f = AF("i", declared={"s": True}, stateful=frozenset({"s"}))
        for _ in range(scale(20_000)):
            st = f.invoke("s")
            f.complete(st.call_id, None)
        self.assertEqual(f.reentrancy_refusals, 0)

    def test_reentry_from_completion_listener(self):
        f = AF("i", declared={"s": True}, stateful=frozenset({"s"}))
        seen = []

        def listener(cid, outcome, value, reason):
            # re-entry from inside a terminal callback: the slot is already free
            st = f.invoke("s")
            seen.append(st.call_id)
            f.complete(st.call_id, None)

        st = f.invoke("s")
        f.add_terminal_listener(st.call_id, listener)
        f.complete(st.call_id, None)
        self.assertEqual(len(seen), 1)
        self.assertEqual(f.listener_failures, 0)

    def test_distinct_stateful_functions_overlap_and_instances_isolated(self):
        f = AF("i", declared={"a": True, "b": True}, stateful=frozenset({"a", "b"}))
        f.invoke("a")
        f.invoke("b")                     # documented: different stateful functions may overlap
        g = AF("j", declared={"a": True}, stateful=frozenset({"a"}))
        g.invoke("a")                     # another instance is unaffected
        self.assertEqual((f.calls_in_flight, g.calls_in_flight), (2, 1))

    def test_queue_policy_under_contention(self):
        pol = {"s": rt.ReentrancyPolicy(rt.ReentrancyMode.QUEUE, 4)}
        f = AF("i", declared={"s": True}, reentrancy=pol)
        admitted_max = [0]
        lock = threading.Lock()
        states = []

        def worker():
            for _ in range(scale(200)):
                try:
                    st = f.invoke("s")
                except rt.ReentrancyQueueFull:
                    continue
                with lock:
                    states.append(st)
                    admitted_max[0] = max(admitted_max[0], f.calls_in_flight)

        def completer(stop):
            while not stop.is_set() or f.calls_in_flight or f.calls_queued:
                with f:
                    live = list(f.in_flight)
                for cid in live:
                    try:
                        f.complete(cid, None)
                    except (rt.TerminalConflict, ValueError):
                        pass

        stop = threading.Event()
        c = threading.Thread(target=completer, args=(stop,))
        c.start()
        ws = [threading.Thread(target=worker) for _ in range(8)]
        for w in ws:
            w.start()
        for w in ws:
            w.join()
        stop.set()
        c.join()
        self.assertEqual(admitted_max[0], 1)
        self.assertEqual(f.completed_calls, len(states))
        self.assertEqual(f.calls_queued, 0)


class ConcurrencyLimitStress(unittest.TestCase):
    def test_hard_limit_under_offered_load(self):
        for limit in (1, 4, 32):
            for factor in (1, 2, 10):
                f = AF("i", declared={"x": True}, concurrency_limit=limit)
                peak = [0]
                pl = threading.Lock()
                refused = [0]
                threads = min(64, limit * factor)
                bar = threading.Barrier(threads)

                def worker():
                    bar.wait()
                    for _ in range(scale(150)):
                        try:
                            st = f.invoke("x")
                        except rt.ConcurrencyLimitReached:
                            with pl:
                                refused[0] += 1
                            continue
                        with pl:
                            peak[0] = max(peak[0], f.calls_in_flight)
                        f.complete(st.call_id, None)

                ts = [threading.Thread(target=worker) for _ in range(threads)]
                for t in ts:
                    t.start()
                for t in ts:
                    t.join()
                self.assertLessEqual(peak[0], limit)
                self.assertEqual(f.concurrency_refusals, refused[0])
                self.assertEqual(f.calls_in_flight, 0)           # capacity recovers after drain
                st = f.invoke("x")
                f.complete(st.call_id, None)

    def test_refusal_cost_is_bounded(self):
        f = AF("i", declared={"x": True}, concurrency_limit=1000)
        for _ in range(1000):
            f.invoke("x")
        t0 = time.perf_counter()
        n = scale(20_000)
        for _ in range(n):
            try:
                f.invoke("x")
            except rt.ConcurrencyLimitReached:
                pass
        per = (time.perf_counter() - t0) / n
        if sys.gettrace() is None:
            self.assertLess(per, 50e-6, f"refusal took {per*1e6:.1f}us - not O(1)?")

    def test_queue_is_fifo_fair(self):
        f = AF("i", declared={"s": True}, reentrancy={"s": rt.ReentrancyPolicy(rt.ReentrancyMode.QUEUE, 50)})
        first = f.invoke("s")
        queued = [f.invoke("s") for _ in range(50)]
        order = []
        cur = first
        while True:
            f.complete(cur.call_id, None)
            nxt = [q for q in queued if q.status == "live" and q.call_id not in order]
            if not nxt:
                break
            cur = nxt[0]
            order.append(cur.call_id)
        self.assertEqual(order, [q.call_id for q in queued])


if __name__ == "__main__":
    unittest.main()
