"""Components 3, 11, 13, 14: async lifecycle, backpressure, retry, admission, fault injection."""
import asyncio
import gc
import unittest

try:
    from . import _path  # noqa: F401
except ImportError:
    import _path  # type: ignore # noqa: F401

from inv20_http_component_worlds.aio import (
    AdmissionController, AsyncBodyStream, AsyncCompletion, AsyncHttpWorld, BreakerState, Cancelled, CircuitBreaker,
    CircuitOpen, Deadline, DeadlineExceeded, HandlerTrap, IllegalState, Lifecycle, NoOutgoing, NotReady, Overloaded,
    RetryPolicy, RState, UpstreamConnect, UpstreamReset, within,
)
from inv20_http_component_worlds.egress import Answer, DestinationPolicy, EgressPolicyDenied
from inv20_http_component_worlds.errors import Inv20Error
from inv20_http_component_worlds.identity import CapabilityStore, KeyProvider, Principal, PrincipalKind, Quarantined
from inv20_http_component_worlds.protocol import Fields, Request, Response
from inv20_http_component_worlds.runtime import BodyTooLarge, CompletionAlreadyResolved

W = Principal(PrincipalKind.WORKLOAD, "acme", "billing")


def run(coro):
    return asyncio.run(coro)


class R:
    def resolve(self, h):
        return Answer(("93.184.216.34",))


def egress_world(transport, **kw):
    keys = KeyProvider(); keys.rotate()
    store = CapabilityStore(keys, "prod")
    pol = DestinationPolicy.from_hosts(["api.example.com"], resolver=R())
    w = AsyncHttpWorld("api", outgoing=True, policy=pol, capabilities=store, transport=transport, **kw)
    cap = store.mint(W, [("api.example.com", 443)], "p")
    return w, cap, store


class StateMachineTest(unittest.TestCase):
    def test_legal_and_illegal(self):
        lc = Lifecycle()
        with self.assertRaises(IllegalState):
            lc.to(RState.HEAD_SENT)
        lc.to(RState.DISPATCHED); lc.to(RState.HEAD_SENT); lc.to(RState.BODY_STREAMING); lc.to(RState.TRAILERS_DONE)
        lc.release(); lc.release()                      # idempotent
        self.assertEqual(lc.released_count, 1)
        with self.assertRaises(IllegalState):
            lc.to(RState.DISPATCHED)

    def test_first_terminal_cause_wins(self):
        lc = Lifecycle(); lc.to(RState.DISPATCHED)
        lc.fail(DeadlineExceeded("t"), cancelled=True)
        lc.fail(UpstreamReset("r"))
        self.assertEqual((lc.state, lc.error.code), (RState.CANCELLED, "E_DEADLINE"))


class StreamTest(unittest.TestCase):
    def test_backpressure_bounded(self):
        async def main():
            s = AsyncBodyStream(limit=1 << 20, max_chunks=2)
            produced = []

            async def prod():
                for i in range(10):
                    await s.write(b"x" * 100)
                    produced.append(i)
                await s.close()
            t = asyncio.ensure_future(prod())
            await asyncio.sleep(0.01)
            self.assertLessEqual(len(produced), 3)       # producer is awaiting capacity
            got = 0
            while (c := await s.read()) is not None:
                got += len(c)
            await t
            self.assertEqual(got, 1000)
            self.assertLessEqual(s.peak, 2)
            self.assertIsNone(await s.read())           # EOF is sticky
        run(main())

    def test_limit_abort_and_write_after_close(self):
        async def main():
            s = AsyncBodyStream(limit=10)
            await s.write(b"12345")
            with self.assertRaises(BodyTooLarge):
                await s.write(b"123456")
            with self.assertRaises(BodyTooLarge):
                await s.read()
            s2 = AsyncBodyStream(); await s2.close()
            with self.assertRaises(IllegalState):
                await s2.write(b"x")
        run(main())

    def test_slow_consumer_times_out(self):
        async def main():
            s = AsyncBodyStream(max_chunks=1)
            await s.write(b"a")
            with self.assertRaises(DeadlineExceeded):
                await s.write(b"b", Deadline.after(20))
            with self.assertRaises(DeadlineExceeded):
                await AsyncBodyStream().read(Deadline.after(20))   # slowloris producer
        run(main())

    def test_completion_exactly_once(self):
        async def main():
            c = AsyncCompletion()
            c.resolve(1)
            with self.assertRaises(CompletionAlreadyResolved):
                c.resolve(2)
            self.assertEqual(await c.wait(), 1)
        run(main())

    def test_validation(self):
        async def main():
            for bad in ((-1, 1), (1, 0), (True, 1)):
                with self.assertRaises(ValueError):
                    AsyncBodyStream(*bad)
        run(main())


class DeadlineTest(unittest.TestCase):
    def test_child_never_exceeds_parent(self):
        t = [100.0]
        clk = lambda: t[0]
        d = Deadline.after(1000, clk)
        self.assertAlmostEqual(d.child(5000, clk).at, d.at)
        self.assertAlmostEqual(d.child(10, clk).at, 100.01)
        t[0] = 102
        self.assertEqual(d.remaining(clk), 0.0)
        for bad in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                Deadline.after(bad)
        self.assertLess(Deadline.after(10**15, clk).at, 10**6)   # clamp, no overflow

    def test_exhausted(self):
        async def main():
            with self.assertRaises(DeadlineExceeded):
                await within(Deadline(0), asyncio.sleep(1))
        run(main())


class HandlerTest(unittest.TestCase):
    def _world(self, handler, **kw):
        w = AsyncHttpWorld("svc", **kw)
        w.export_handler(handler)
        return w

    def test_streaming_response_with_trailers(self):
        async def h(req, out):
            out.set(Response(200))
            for _ in range(5):
                await out.write(b"chunk")
            await out.finish(Fields([("x-digest", "ok")], trailers=True))

        async def main():
            w = self._world(h)
            out = await w.handle(Request.build("GET", "https", "h.com"), W, Deadline.after(1000))
            body = b""
            while (c := await out.body.read()) is not None:
                body += c
            tr = await out.trailers.wait()
            await asyncio.sleep(0)
            self.assertEqual((out.head.status, body, tr.get("x-digest")), (200, b"chunk" * 5, "ok"))
            self.assertFalse(w.live)
        run(main())

    def test_double_head_and_post_terminal(self):
        async def h(req, out):
            out.set(Response(200))
            with self.assertRaises(IllegalState):
                out.set(Response(500))
            await out.finish()
            with self.assertRaises(IllegalState):
                await out.write(b"late")

        async def main():
            await self._world(h).handle(Request.build("GET", "https", "h.com"), W, Deadline.after(500))
        run(main())

    def test_trap_before_head(self):
        async def h(req, out):
            raise ZeroDivisionError

        async def main():
            w = self._world(h)
            with self.assertRaises(HandlerTrap):
                await w.handle(Request.build("GET", "https", "h.com"), W, Deadline.after(500))
            self.assertFalse(w.live)
        run(main())

    def test_trap_mid_body(self):
        async def h(req, out):
            out.set(Response(200))
            await out.write(b"partial")
            await asyncio.sleep(0.01)
            raise RuntimeError("trap")

        async def main():
            w = self._world(h)
            out = await w.handle(Request.build("GET", "https", "h.com"), W, Deadline.after(500))
            with self.assertRaises(HandlerTrap):
                while await out.body.read() is not None:
                    pass
            with self.assertRaises(HandlerTrap):
                await out.trailers.wait()
            await asyncio.sleep(0)
            self.assertFalse(w.live)
        run(main())

    def test_timeout_before_head_cancels_handler(self):
        cancelled = []

        async def h(req, out):
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                cancelled.append(True)
                raise

        async def main():
            w = self._world(h)
            with self.assertRaises(DeadlineExceeded):
                await w.handle(Request.build("GET", "https", "h.com"), W, Deadline.after(30))
            await asyncio.sleep(0.01)
            self.assertEqual(cancelled, [True])
            self.assertFalse(w.live)
        run(main())

    def test_no_handler_not_ready_quarantine(self):
        async def main():
            with self.assertRaises(IllegalState):
                await AsyncHttpWorld("x").handle(Request.build("GET", "https", "h.com"), W, Deadline.after(10))
            w = self._world(lambda r, o: None, ready=lambda: False)
            with self.assertRaises(NotReady):
                await w.handle(Request.build("GET", "https", "h.com"), W, Deadline.after(10))
            keys = KeyProvider(); keys.rotate(); st = CapabilityStore(keys, "prod"); st.quarantine("acme")
            w2 = self._world(lambda r, o: None, capabilities=st)
            with self.assertRaises(Quarantined):
                await w2.handle(Request.build("GET", "https", "h.com"), W, Deadline.after(10))
        run(main())

    def test_concurrent_and_high_volume_cancellation_no_leaks(self):
        async def slow(req, out):
            out.set(Response(200))
            await out.write(b"x")
            await asyncio.sleep(10)

        async def main():
            w = self._world(slow, admission=AdmissionController(1000, 1000, 1000, 10))
            outs = await asyncio.gather(*(w.handle(Request.build("GET", "https", "h.com"), W, Deadline.after(1000))
                                          for _ in range(200)))
            self.assertEqual(len(w.live), 200)
            for lc in list(w.live):
                lc.release()                          # peer disconnect for every request
            await asyncio.sleep(0.05)
            self.assertEqual(len(w.live), 0)
            self.assertEqual(w.admission.active, 0)
            pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            self.assertEqual(pending, [])
            self.assertEqual(len(outs), 200)
        run(main())


class OutgoingTest(unittest.TestCase):
    def test_requires_import_and_capability(self):
        class T:
            async def send(self, d, r, dl):
                return Response(200)

        async def main():
            with self.assertRaises(NoOutgoing):
                await AsyncHttpWorld("sealed").fetch(W, "x", Request.build("GET", "https", "api.example.com"), Deadline.after(100))
            w, cap, store = egress_world(T())
            r = await w.fetch(W, cap.token, Request.build("GET", "https", "api.example.com"), Deadline.after(100))
            self.assertEqual(r.status, 200)
            with self.assertRaises(Inv20Error):
                await w.fetch(W, "forged.token", Request.build("GET", "https", "api.example.com"), Deadline.after(100))
            narrow = store.mint(W, [("other.example.com", 443)], "p")
            with self.assertRaises(EgressPolicyDenied):
                await w.fetch(W, narrow.token, Request.build("GET", "https", "api.example.com"), Deadline.after(100))
        run(main())
        with self.assertRaises(ValueError):
            AsyncHttpWorld("x", outgoing=True)

    def test_retry_only_safe(self):
        class Flaky:
            def __init__(self, err, n):
                self.err, self.n, self.calls = err, n, 0

            async def send(self, d, r, dl):
                self.calls += 1
                if self.calls <= self.n:
                    raise self.err("x")
                return Response(200)

        async def main():
            t = Flaky(UpstreamConnect, 2)
            w, cap, _ = egress_world(t, retry=RetryPolicy(base_ms=1, max_backoff_ms=2))
            self.assertEqual((await w.fetch(W, cap.token, Request.build("POST", "https", "api.example.com"), Deadline.after(1000))).status, 200)
            self.assertEqual(t.calls, 3)
            t2 = Flaky(UpstreamReset, 1)
            w2, cap2, _ = egress_world(t2, retry=RetryPolicy(base_ms=1, max_backoff_ms=2))
            with self.assertRaises(UpstreamReset):
                await w2.fetch(W, cap2.token, Request.build("GET", "https", "api.example.com"), Deadline.after(1000))
            self.assertEqual(t2.calls, 1)
            from inv20_http_component_worlds.egress import DnsFailure
            t3 = Flaky(DnsFailure, 5)
            w3, cap3, _ = egress_world(t3, retry=RetryPolicy(base_ms=1, max_backoff_ms=2))
            with self.assertRaises(DnsFailure):
                await w3.fetch(W, cap3.token, Request.build("POST", "https", "api.example.com"), Deadline.after(1000))
            self.assertEqual(t3.calls, 1)                # non-idempotent, no key -> no retry
            t4 = Flaky(DnsFailure, 5)
            w4, cap4, _ = egress_world(t4, retry=RetryPolicy(base_ms=1, max_backoff_ms=2, max_attempts=3))
            with self.assertRaises(DnsFailure):
                await w4.fetch(W, cap4.token, Request.build("POST", "https", "api.example.com"), Deadline.after(1000), idempotency_key="k")
            self.assertEqual(t4.calls, 3)                # bounded attempts
        run(main())

    def test_deadline_during_backoff(self):
        class Fail:
            async def send(self, d, r, dl):
                raise UpstreamConnect("x")

        async def main():
            w, cap, _ = egress_world(Fail(), retry=RetryPolicy(base_ms=500, max_backoff_ms=1000))
            with self.assertRaises(DeadlineExceeded):
                await w.fetch(W, cap.token, Request.build("GET", "https", "api.example.com"), Deadline.after(100))
        run(main())

    def test_breaker_opens(self):
        class Fail:
            calls = 0

            async def send(self, d, r, dl):
                Fail.calls += 1
                raise UpstreamConnect("x")

        async def main():
            w, cap, _ = egress_world(Fail(), retry=RetryPolicy(max_attempts=1))
            for _ in range(5):
                with self.assertRaises(UpstreamConnect):
                    await w.fetch(W, cap.token, Request.build("GET", "https", "api.example.com"), Deadline.after(100))
            with self.assertRaises(CircuitOpen):
                await w.fetch(W, cap.token, Request.build("GET", "https", "api.example.com"), Deadline.after(100))
            self.assertEqual(Fail.calls, 5)
        run(main())

    def test_fanout_limit(self):
        async def main():
            w = AsyncHttpWorld("f", max_fanout=2)
            async def one():
                return 1
            self.assertEqual(await w.fan_out([one, one]), [1, 1])
            with self.assertRaises(Overloaded):
                await w.fan_out([one, one, one])
        run(main())


class RetryBreakerUnitTest(unittest.TestCase):
    def test_backoff_bounds(self):
        p = RetryPolicy(base_ms=100, max_backoff_ms=1000, retry_after_cap_ms=3000)
        for a in range(1, 10):
            b = p.backoff_ms(a)
            self.assertTrue(0 < b <= 1000)
        self.assertEqual(p.backoff_ms(1, retry_after_ms=10**9), 3000)
        self.assertFalse(p.classify("GET", UpstreamConnect("x"), head_committed=True))

    def test_breaker_half_open(self):
        t = [0.0]
        b = CircuitBreaker(failure_threshold=2, reset_after_s=5, clock=lambda: t[0])
        b.failure(); b.failure()
        self.assertFalse(b.allow())
        t[0] = 6
        self.assertTrue(b.allow()); self.assertEqual(b.state, BreakerState.HALF_OPEN)
        b.failure(); self.assertEqual(b.state, BreakerState.OPEN)
        t[0] = 12; b.allow(); b.success(); self.assertEqual(b.state, BreakerState.CLOSED)


class AdmissionTest(unittest.TestCase):
    def test_noisy_neighbour_and_queue(self):
        async def main():
            a = AdmissionController(max_concurrency=4, per_tenant=2, per_workload=2, queue_depth=1)
            await a.acquire("noisy", "w"); await a.acquire("noisy", "w")
            with self.assertRaises(Overloaded):
                await a.acquire("noisy", "w")               # shed without taking a queue slot
            await a.acquire("quiet", "w")                   # other tenant unaffected
            await a.acquire("third", "w")
            waiter = asyncio.ensure_future(a.acquire("fourth", "w", Deadline.after(500)))
            await asyncio.sleep(0.01)
            with self.assertRaises(Overloaded):
                await a.acquire("fifth", "w")               # queue full -> documented overload
            await a.release("quiet", "w")
            await waiter
            with self.assertRaises(Overloaded):
                await a.acquire("sixth", "w", Deadline.after(20))   # queue timeout
            self.assertEqual(a.rejections, {"tenant_limit": 1, "queue_full": 1, "queue_timeout": 1})
            for t in ("noisy", "noisy", "third", "fourth"):
                await a.release(t, "w")
            self.assertEqual(a.active, 0)
            await a.acquire("noisy", "w")                   # recovery after overload
        run(main())


if __name__ == "__main__":
    unittest.main()
