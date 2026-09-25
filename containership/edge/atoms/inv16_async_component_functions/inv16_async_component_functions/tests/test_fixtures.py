"""Closures #2, #4, #5, #6 - INV-16's side of each integration against SURROGATE fixtures.

Every assertion here must keep passing when the real sibling replaces the
surrogate; until then these items are PARTIAL (see docs/CLOSURE_LEDGER.md).
"""
import threading
import unittest

from _util import rt, scale, sub

inv15 = sub("fixtures.inv15")
comp = sub("fixtures.composition")
streams = sub("fixtures.streams")
http = sub("fixtures.http")
AF = rt.AsyncFunctions


class Inv15(unittest.TestCase):
    def test_n_calls_multi_subtasks_cancel_trap_no_leaks(self):
        t = inv15.SubtaskTable(capacity=10_000)
        b = inv15.AbiBinding(AF("i", declared={"a": True}), t)
        calls = [b.invoke("a", subtasks=3) for _ in range(scale(200))]
        self.assertEqual(t.outstanding(), 3 * len(calls))
        for i, (c, hs) in enumerate(calls):
            if i % 3 == 0:
                b.cancel(c.call_id, rt.CancelCode.DISCONNECT)
            elif i % 3 == 1:
                b.subtask_done(hs[0]); b.subtask_done(hs[1]); b.subtask_done(hs[2], "v", last=True)
        b.trap()
        self.assertEqual(t.outstanding(), 0)
        self.assertEqual(b.fns.calls_in_flight, 0)
        self.assertEqual(sum(1 for v in t.cancelled.values() if v == "disconnect"), 3 * len(calls[0::3]))
        self.assertIn("trapped", t.cancelled.values())

    def test_late_completion_after_cancel_rejected(self):
        t = inv15.SubtaskTable()
        b = inv15.AbiBinding(AF("i", declared={"a": True}), t)
        c, hs = b.invoke("a", subtasks=1)
        b.cancel(c.call_id)
        with self.assertRaises(rt.CallCancelled):
            b.fns.complete(c.call_id, "late")
        self.assertEqual(b.fns.double_delivery_attempts, 0)

    def test_capacity_refusal_rolls_back(self):
        t = inv15.SubtaskTable(capacity=2)
        b = inv15.AbiBinding(AF("i", declared={"a": True}), t)
        with self.assertRaises(inv15.SubtaskCapacity):
            b.invoke("a", subtasks=3)
        self.assertEqual((t.outstanding(), b.fns.calls_in_flight), (0, 0))

    def test_trap_races_completion(self):
        for _ in range(scale(100)):
            t = inv15.SubtaskTable()
            b = inv15.AbiBinding(AF("i", declared={"a": True}), t)
            c, hs = b.invoke("a", subtasks=1)
            bar = threading.Barrier(2)
            res = []

            def complete():
                bar.wait()
                try:
                    b.subtask_done(hs[0], 1, last=True); res.append("c")
                except (rt.CallTrapped, KeyError):
                    res.append("x")

            def trap():
                bar.wait()
                res.append("t" if b.trap() else "-")

            ts = [threading.Thread(target=complete), threading.Thread(target=trap)]
            [x.start() for x in ts]; [x.join() for x in ts]
            self.assertEqual(b.fns.completed_calls + b.fns.trapped_calls, 1)
            self.assertEqual(t.outstanding(), 0)


class Inv10(unittest.TestCase):
    def _link(self):
        def leaf_async(L, x): return x * 2
        def leaf_sync(L, x): return x + 1
        def mid(L, x): return L.call(True, "C", "double", x)
        def top(L, x): return L.call(False, "B", "mid", x)      # sync A -> async B -> async C
        C = comp.Component("C", {"double": (True, leaf_async), "inc": (False, leaf_sync)})
        B = comp.Component("B", {"mid": (True, mid)}, stateful=frozenset({"mid"}))
        A = comp.Component("A", {"top": (False, top)})
        return comp.Linked([A, B, C])

    def test_2x2_matrix_equivalence(self):
        L = self._link()
        for caller_async in (True, False):
            self.assertEqual(L.call(caller_async, "C", "double", 5), 10)
            self.assertEqual(L.call(caller_async, "C", "inc", 5), 6)
        self.assertEqual(L.by_name["C"].fns.bridge_calls, 1)       # only sync->async bridges

    def test_nested_chain_and_no_orphans(self):
        L = self._link()
        self.assertEqual(L.call(False, "A", "top", 4), 8)
        for c in L.by_name.values():
            self.assertEqual(c.fns.calls_in_flight, 0)

    def test_trap_at_each_hop_leaves_no_orphans(self):
        for hop in ("A", "B", "C"):
            L = self._link()
            impl = L.by_name[hop].exports
            fn = next(iter(impl))
            is_async, _ = impl[fn]
            impl[fn] = (is_async, lambda L_, x: (_ for _ in ()).throw(RuntimeError("trap")))
            with self.assertRaises(RuntimeError):
                L.call(False, "A", "top", 1)
            for c in L.by_name.values():
                self.assertEqual(c.fns.calls_in_flight, 0, hop)

    def test_incompatible_abi_rejected_before_execution(self):
        bad = comp.Component("X", {"f": (True, lambda L, x: x)}, abi_version=2)
        with self.assertRaises(comp.LinkError):
            comp.Linked([bad])


class Inv17(unittest.TestCase):
    def test_lifecycle_backpressure_isolation(self):
        fns = AF("i", declared={"s": True})
        reg = streams.StreamRegistry()
        a, b = fns.invoke("s"), fns.invoke("s")
        sa, sb = reg.open(fns, a.call_id, 4), reg.open(fns, b.call_id, 4)
        for i in range(4):
            sa.write(("a", i)); sb.write(("b", i))
        with self.assertRaises(streams.Backpressure):
            sa.write("overflow")                            # bounded per-call memory
        self.assertEqual(sa.read(), ("a", 0))               # no cross-call bytes
        fns.complete(a.call_id, None)                        # completion precedes exhaustion
        self.assertEqual(sa.read(), ("a", 1))
        fns.cancel(b.call_id, "disconnect")
        with self.assertRaises(streams.StreamClosed):
            sb.read()
        fns.trap_all()
        self.assertEqual(len(sb.buf), 0)

    def test_cancel_all_releases_buffers(self):
        fns = AF("i", declared={"s": True})
        reg = streams.StreamRegistry()
        for _ in range(20):
            c = fns.invoke("s")
            reg.open(fns, c.call_id, 8).write(b"x")
        fns.cancel_all("shutdown")
        self.assertEqual(reg.open_buffers(), 0)


class Inv20(unittest.TestCase):
    TP = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"

    def test_request_lifecycle_mapping(self):
        fns = AF("h", declared={"handle": True, "stateful": True}, stateful=frozenset({"stateful"}),
                 concurrency_limit=3, tracing=True)
        w = http.HttpWorld(fns)
        c, r = w.accept("handle", self.TP)
        w.handler_done(c, "body")
        self.assertEqual((r.status, r.body, r.writes), (200, "body", 1))
        self.assertEqual(c.trace.trace_id, "4bf92f3577b34da6a3ce929d0e0e4736")
        c, r = w.accept("handle"); w.disconnect(c); w.handler_done(c, "late")
        self.assertEqual((r.status, r.writes), (499, 1))
        c, r = w.accept("handle"); w.deadline(c); w.disconnect(c)
        self.assertEqual((r.status, r.writes), (504, 1))     # first cause wins, no second write
        c, r = w.accept("handle"); fns.trap_all()
        self.assertEqual(r.status, 500)
        s1, _ = w.accept("stateful")
        _, r2 = w.accept("stateful")
        self.assertEqual(r2.status, 429)
        w.accept("handle"); w.accept("handle")
        _, r3 = w.accept("handle")
        self.assertEqual(r3.status, 503)

    def test_high_concurrency_no_double_response(self):
        fns = AF("h", declared={"handle": True}, concurrency_limit=50)
        w = http.HttpWorld(fns)
        resps = []
        lock = threading.Lock()

        def client(k):
            for _ in range(scale(50)):
                c, r = w.accept("handle")
                with lock:
                    resps.append(r)
                if c is None:
                    continue
                if k % 2:
                    w.disconnect(c)
                w.handler_done(c, k)

        ts = [threading.Thread(target=client, args=(k,)) for k in range(16)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertTrue(all(r.writes == 1 for r in resps))
        self.assertEqual(fns.calls_in_flight, 0)


if __name__ == "__main__":
    unittest.main()
