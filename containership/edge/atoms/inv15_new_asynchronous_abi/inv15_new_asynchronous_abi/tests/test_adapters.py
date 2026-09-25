"""Components 31-37: scheduler, INV-16/17/18 adapters, migration shim."""
from concurrent.futures import Future
import unittest

from _util import mk
from inv15_new_asynchronous_abi.adapters import (AsyncFunctionAdapter, Completion, PollableShim,
                                                 SchedulerAdapter, StreamAdapter, require_contract)
from inv15_new_asynchronous_abi.errors import AbiError, ErrorCode, CancelAck


def code(fn):
    try:
        fn()
    except AbiError as e:
        return e.code


class TestScheduler(unittest.TestCase):
    def test_event_driven_coalesced(self):
        h, _ = mk()
        v = h.register("i", tenant="t", workload="w")
        resumed = []
        s = SchedulerAdapter(h, resumed.append)
        xs = [v.call()[1] for _ in range(5)]
        self.assertEqual(s.runnable(), [])
        for x in xs:
            h.complete(x, 0)
        self.assertEqual(s.runnable(), ["i"])
        self.assertEqual(s.coalesced, 4)
        self.assertEqual(s.run_once(), 1)
        self.assertEqual(resumed, [v])
        self.assertEqual(s.run_once(), 0)
        self.assertEqual(h.metrics.hist["ready_to_resume_ns"].n, 1)

    def test_contract_version(self):
        require_contract(1)
        self.assertEqual(code(lambda: require_contract(2)), ErrorCode.UNSUPPORTED_VERSION)


class TestAsyncFunction(unittest.TestCase):
    def test_sync_async_error_paths(self):
        h, _ = mk()
        v = h.register("i", tenant="t", workload="w")
        a = AsyncFunctionAdapter(h, v)
        self.assertEqual(a.invoke(lambda: 5), ("value", 5))
        f = Future()
        _, x = a.invoke(lambda: f)
        f.set_result("ok")
        self.assertEqual(v.take(x), "ok")
        g = Future()
        _, y = a.invoke(lambda: g)
        g.set_exception(ValueError("bad"))
        self.assertEqual(code(lambda: v.take(y)), ErrorCode.TRAPPED)
        k = Future()
        _, z = a.invoke(lambda: k)
        self.assertEqual(v.cancel(z), CancelAck.PROPAGATED)
        k.set_result("late")  # discarded, no crash


class TestStream(unittest.TestCase):
    def test_backpressure_close_error(self):
        h, _ = mk()
        v = h.register("i", tenant="t", workload="w")
        s = StreamAdapter(h, v, capacity=2)
        _, r1 = s.read()
        self.assertEqual(s.write("a"), "delivered")
        self.assertEqual(v.take(r1), "a")
        s.write("b"); s.write("c")
        self.assertEqual(code(lambda: s.write("d")), ErrorCode.BUDGET_EXHAUSTED)
        self.assertEqual(s.read(), ("value", "b"))
        _, r2 = s.read(); _ = r2
        s.read()
        _, r3 = s.read()
        s.close()
        self.assertEqual(v.take(r3), StreamAdapter.EOS)
        self.assertEqual(s.read(), ("value", StreamAdapter.EOS))
        s2 = StreamAdapter(h, v)
        _, r4 = s2.read()
        s2.error("disk")
        self.assertEqual(code(lambda: v.take(r4)), ErrorCode.TRAPPED)

    def test_cancelled_read_is_skipped(self):
        h, _ = mk()
        v = h.register("i", tenant="t", workload="w")
        s = StreamAdapter(h, v)
        _, r1 = s.read()
        _, r2 = s.read()
        v.cancel(r1)
        s.write("x")
        self.assertEqual(v.take(r2), "x")


class TestCompletion(unittest.TestCase):
    def test_typed_lift(self):
        h, _ = mk()
        v = h.register("i", tenant="t", workload="w")
        c = Completion(h, v, int)
        c.resolve_ok(3)
        self.assertEqual(c.lift(), ("ok", 3))
        d = Completion(h, v, int)
        d.resolve_ok("str")
        self.assertEqual(code(d.lift), ErrorCode.TRAPPED)
        e = Completion(h, v)
        e.resolve_err(42, "nope")
        self.assertEqual(e.lift(), ("err", 42, "nope"))


class TestShim(unittest.TestCase):
    def test_legacy_and_cutover(self):
        h, _ = mk()
        v = h.register("i", tenant="t", workload="w")
        s = PollableShim(h, v)
        p = s.start()
        self.assertFalse(s.poll(p))
        h.complete(p, 9)
        self.assertTrue(s.poll(p))
        self.assertEqual(s.block(p), 9)
        self.assertEqual(h.metrics.get("pk_async_legacy_pollable_calls_total"), 4)
        s.cutover = True
        self.assertEqual(code(s.start), ErrorCode.UNSUPPORTED_VERSION)


if __name__ == "__main__":
    unittest.main()
