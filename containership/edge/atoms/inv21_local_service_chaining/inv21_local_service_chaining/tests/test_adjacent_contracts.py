"""GAP-028 adjacent-layer CONTRACT tests.

These exercise INV-21 against executable stand-ins that implement the adjacent
interfaces exactly as INV-21 consumes them. They are NOT interoperability tests
against the real INV-20 / INV-10 / INV-16 / INV-13 / SCH-01 packages, which are
not present in this repository: GAP-028 stays OPEN until tests/integration is
run in the assembled estate (tools/release_gate.py enforces that).
"""
import asyncio, unittest
from _support import E, build, ctx
from inv21_local_service_chaining.policy import CapabilityDecision, CAPABILITY_SCHEMA


class Inv20HttpWorld:
    """INV-20 stand-in: an HTTP component world exposing a request handler."""
    def handler(self, hop, req):
        return {"status": 200, "body": req.get("body", ""), "trace": hop.ctx.trace_id}


class Inv10Composition:
    """INV-10 stand-in: authoritative placement feed for reconcile()."""
    def __init__(self, links): self.links = links
    def feed(self):
        return [{"callee": c, "tenant": t, "epoch": e} for c, t, e in self.links]


class Inv13SystemInterface:
    """INV-13 stand-in: capability authority."""
    authoritative = True
    def decide(self, r):
        ok = "http.invoke" in r.capabilities
        return CapabilityDecision(ok, 1, "inv13", r.correlation_id)


class Sch01Scheduler:
    """SCH-01 stand-in: consumes the work-shape signal (local vs remote hops)."""
    def observe(self, prom_text):
        return {l.split(" ")[0]: float(l.split(" ")[1]) for l in prom_text.splitlines() if l.startswith("inv21_hops")}


class AdjacentContractTest(unittest.TestCase):
    def test_inv20_handler_through_inv13_authority(self):
        ch, res, _, v = build(provider=Inv13SystemInterface())
        res.place("web", "acme", Inv20HttpWorld().handler, abi="hop")
        with self.assertRaises(E.CapabilityRefused):
            ch.invoke("web", {"body": "x"}, ctx(v))
        out = ch.invoke("web", {"body": "x"}, ctx(v, caps=["http.invoke"], trace="tr-20"))
        self.assertEqual(out, {"status": 200, "body": "x", "trace": "tr-20"})

    def test_inv10_feed_reconciles_residency(self):
        ch, res, _, v = build(provider=Inv13SystemInterface())
        res.place("a", "acme", lambda hop, r: 1, abi="hop", epoch=1)
        res.place("gone", "acme", lambda hop, r: 1, abi="hop", epoch=1)
        out = res.reconcile(Inv10Composition([("a", "acme", 1)]).feed())
        self.assertEqual(out["evicted"], ["gone"])

    def test_inv16_async_function_call(self):
        ch, res, _, v = build(provider=Inv13SystemInterface())
        async def fn(hop, r):
            await asyncio.sleep(0); return r * 2
        res.place("async", "acme", fn, abi="hop")
        self.assertEqual(asyncio.run(ch.ainvoke("async", 21, ctx(v, caps=["http.invoke"]))), 42)

    def test_sch01_receives_work_shape_signal(self):
        ch, res, _, v = build(provider=Inv13SystemInterface())
        res.place("a", "acme", lambda hop, r: 1, abi="hop")
        ch.invoke("a", 0, ctx(v, caps=["http.invoke"]))
        sig = Sch01Scheduler().observe(ch.export_metrics())
        self.assertEqual(sig.get('inv21_hops_local_total{callee="a"}'), 1.0)


if __name__ == "__main__":
    unittest.main()
