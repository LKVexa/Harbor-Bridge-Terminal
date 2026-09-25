"""GAP-030 fault injection: handler crash/stall, provider outage, stale residency,
transport failure, partition + reconnect, degraded control plane."""
import time, unittest
from _support import E, ChainEndpoint, LoopbackTransport, build, ctx, prod_config
from inv21_local_service_chaining.admission import CircuitBreaker


class Flaky:
    authoritative = True
    def __init__(self, inner): self.inner, self.down = inner, False
    def decide(self, r):
        if self.down:
            raise ConnectionError("policy plane down")
        return self.inner.decide(r)


class FaultInjectionTest(unittest.TestCase):
    def test_handler_crash_leaves_state_consistent(self):
        ch, res, prov, v = build(grants=[("acme", "c", "invoke")])
        res.place("c", "acme", lambda hop, r: (_ for _ in ()).throw(MemoryError("x")) if r else "ok", abi="hop")
        with self.assertRaises(E.HandlerFailed):
            ch.invoke("c", 1, ctx(v))
        self.assertEqual(ch.admission.snapshot()["in_flight"], 0)
        self.assertEqual(ch.invoke("c", 0, ctx(v)), "ok")

    def test_policy_outage_and_recovery(self):
        from inv21_local_service_chaining.policy import StaticPolicyProvider
        f = Flaky(StaticPolicyProvider([("acme", "s", "invoke")]))
        ch, res, _, v = build(provider=f)
        res.place("s", "acme", lambda hop, r: "ok", abi="hop")
        f.down = True
        for _ in range(3):
            with self.assertRaises(E.ProviderUnavailable):
                ch.invoke("s", 0, ctx(v))
        self.assertEqual(ch.health()["dependencies"]["policy"], "degraded")
        f.down = False
        self.assertEqual(ch.invoke("s", 0, ctx(v)), "ok")

    def test_partition_opens_breaker_then_reconnects(self):
        b, rb, pb, v = build("host-b", grants=[("acme", "far", "invoke")])
        rb.place("far", "acme", lambda hop, r: "far-ok", abi="hop")
        lt = LoopbackTransport(ChainEndpoint(b, v))
        a, ra, pa, _ = build("host-a", grants=[("acme", "far", "invoke")], transport=lt)
        a.breaker = CircuitBreaker(failure_threshold=2, reset_after_s=0.05)
        for _ in range(2):
            lt.fail_next = ConnectionResetError("partition")
            with self.assertRaises(E.TransportUnavailable):
                a.invoke("far", 0, ctx(v))
        sent = lt.sent
        with self.assertRaises(E.CircuitOpen):
            a.invoke("far", 0, ctx(v))
        self.assertEqual(lt.sent, sent)  # shed without touching the network
        self.assertIn("far", a.health()["dependencies"]["open_circuits"])
        time.sleep(0.06)
        self.assertEqual(a.invoke("far", 0, ctx(v)), "far-ok")  # half-open probe succeeds
        self.assertEqual(a.breaker.state("far"), "closed")

    def test_stale_residency_after_control_plane_loss(self):
        ch, res, prov, v = build(grants=[("acme", "s", "invoke")])
        res.place("s", "acme", lambda hop, r: "local", abi="hop", lease_s=0.02)
        time.sleep(0.03)  # control plane stopped renewing
        with self.assertRaises(E.TransportUnavailable):
            ch.invoke("s", 0, ctx(v))
        self.assertEqual(res.expire(), ["s"])

    def test_remote_stall_bounded_by_deadline(self):
        class Stall:
            def send(self, *a):
                time.sleep(0.2); return "late"
        import asyncio
        from _support import Deadline
        a, ra, pa, v = build(grants=[("acme", "far", "invoke")], transport=Stall())
        async def main():
            t0 = time.monotonic()
            try:
                await a.ainvoke("far", 0, ctx(v, deadline=Deadline.after(0.05)))
            except E.DeadlineExceeded:
                return time.monotonic() - t0
        elapsed = asyncio.run(main())
        self.assertIsNotNone(elapsed)
        self.assertLess(elapsed, 0.15)  # caller released at the deadline, not when the peer returns

    def test_degraded_lifecycle_still_serves(self):
        ch, res, prov, v = build(grants=[("acme", "s", "invoke")])
        res.place("s", "acme", lambda hop, r: "ok", abi="hop")
        ch.lifecycle.transition("degraded", reason="policy latency high")
        self.assertEqual(ch.invoke("s", 0, ctx(v)), "ok")
        self.assertEqual(ch.health()["state"], "degraded")


if __name__ == "__main__":
    unittest.main()
