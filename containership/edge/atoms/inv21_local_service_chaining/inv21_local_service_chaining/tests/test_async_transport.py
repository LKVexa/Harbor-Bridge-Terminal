"""GAP-007 async chaining, GAP-006 concrete HTTP transport."""
import asyncio, json, time, unittest
from dataclasses import replace
from _support import E, ChainEndpoint, Deadline, build, ctx, verifier
from inv21_local_service_chaining.transport import ChainHttpServer, HttpJsonTransport, LoopbackTransport


class AsyncTest(unittest.TestCase):
    def test_async_handlers_and_nested_acall(self):
        ch, res, prov, v = build(grants=[("acme", "a", "invoke"), ("acme", "b", "invoke")])
        async def b(hop, r):
            await asyncio.sleep(0); return r + 1
        async def a(hop, r):
            return await hop.acall("b", r * 10)
        res.place("a", "acme", a, abi="hop"); res.place("b", "acme", b, abi="hop")
        self.assertEqual(asyncio.run(ch.ainvoke("a", 4, ctx(v))), 41)
        with self.assertRaises(E.ValidationFailed):
            ch.invoke("a", 4, ctx(v))  # async handler via sync path is refused, not leaked

    def test_async_deadline_and_cancellation(self):
        ch, res, prov, v = build(grants=[("acme", "slow", "invoke")])
        async def slow(hop, r):
            await asyncio.sleep(1)
        res.place("slow", "acme", slow, abi="hop")
        with self.assertRaises(E.DeadlineExceeded):
            asyncio.run(ch.ainvoke("slow", 0, ctx(v, deadline=Deadline.after(0.03))))
        c = ctx(v)
        async def main():
            t = asyncio.ensure_future(ch.ainvoke("slow", 0, c))
            await asyncio.sleep(0.02); t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                return "cancelled"
        self.assertEqual(asyncio.run(main()), "cancelled")
        self.assertTrue(c.cancel.cancelled)  # propagated to the shared token
        with self.assertRaises(E.Cancelled):
            ch.invoke("slow", 0, c)
        self.assertEqual(ch.admission.snapshot()["in_flight"], 0)

    def test_async_remote_via_thread(self):
        b, rb, pb, v = build("host-b", grants=[("acme", "svc", "invoke")])
        rb.place("svc", "acme", lambda hop, r: {"echo": r}, abi="hop")
        a, ra, pa, _ = build("host-a", grants=[("acme", "svc", "invoke")],
                             transport=LoopbackTransport(ChainEndpoint(b, v)))
        self.assertEqual(asyncio.run(a.ainvoke("svc", [1], ctx(v))), {"echo": [1]})


class HttpTransportTest(unittest.TestCase):
    def test_real_http_round_trip_errors_and_auth(self):
        b, rb, pb, v = build("host-b", grants=[("acme", "svc", "invoke"), ("acme", "bad", "invoke")])
        rb.place("svc", "acme", lambda hop, r: {"got": r, "depth": hop.ctx.depth}, abi="hop")
        rb.place("bad", "acme", lambda hop, r: 1 / 0, abi="hop")
        with ChainHttpServer(ChainEndpoint(b, v)) as srv:
            a, ra, pa, _ = build("host-a", grants=[("acme", "svc", "invoke"), ("acme", "bad", "invoke")],
                                 transport=HttpJsonTransport(srv.url))
            self.assertEqual(a.invoke("svc", {"x": 1}, ctx(v)), {"got": {"x": 1}, "depth": 0})
            with self.assertRaises(E.HandlerFailed):
                a.invoke("bad", {}, ctx(v))
            c = ctx(v)
            forged = replace(c, credential=verifier().issue("svc-a", "evil"))
            with self.assertRaises(E.Unauthenticated):    # caller-side: principal/credential mismatch
                a.invoke("svc", {}, forged)
            ep_status, out = ChainEndpoint(b, v).handle(json.dumps({   # peer-side: wire context vs credential
                "schema": "PK_LOCAL_CHAIN/1", "callee": "svc", "payload": 0,
                "context": {"schema": "PK_CALL_CONTEXT/1", "trace_id": "t", "operation": "invoke",
                            "tenant": "acme", "subject": "svc-a", "path": []}}).encode(), forged.credential)
            self.assertEqual(json.loads(out)["error"]["code"], "PK_CHAIN_INVALID_REQUEST")
            with self.assertRaises(E.Unauthenticated):
                a.invoke("svc", {}, replace(c, credential="garbage"))
            import urllib.request
            r = urllib.request.urlopen(urllib.request.Request(srv.url + "/pk/local-chain/1", data=b"{", method="POST"))
            self.assertEqual(json.loads(r.read())["error"]["code"], "PK_CHAIN_INVALID_REQUEST")

    def test_network_unavailable_and_timeout(self):
        a, ra, pa, v = build("host-a", grants=[("acme", "svc", "invoke")],
                             transport=HttpJsonTransport("http://127.0.0.1:9"))
        with self.assertRaises(E.TransportUnavailable):
            a.invoke("svc", {}, ctx(v))
        b, rb, pb, _ = build("host-b", grants=[("acme", "svc", "invoke")])
        rb.place("svc", "acme", lambda hop, r: time.sleep(0.5), abi="hop")
        with ChainHttpServer(ChainEndpoint(b, v)) as srv:
            a2, _, _, _ = build("host-a", grants=[("acme", "svc", "invoke")], transport=HttpJsonTransport(srv.url))
            with self.assertRaises(E.DeadlineExceeded):
                a2.invoke("svc", {}, ctx(v, deadline=Deadline.after(0.1)))

    def test_tls_required_off_loopback_and_health_endpoints(self):
        with self.assertRaises(ValueError):
            HttpJsonTransport("http://10.0.0.5:8080")
        HttpJsonTransport("https://peer.example:8443"); HttpJsonTransport("http://127.0.0.1:1")
        import urllib.request, urllib.error
        b, rb, pb, v = build("host-b")
        with ChainHttpServer(ChainEndpoint(b, v)) as srv:
            self.assertEqual(json.loads(urllib.request.urlopen(srv.url + "/healthz").read()), {"live": True})
            self.assertTrue(json.loads(urllib.request.urlopen(srv.url + "/readyz").read())["ready"])
            self.assertIn(b"inv21_ready 1", urllib.request.urlopen(srv.url + "/metrics").read())
            b.quarantine(reason="t", actor="t")
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(srv.url + "/readyz")
            self.assertEqual(cm.exception.code, 503)

    def test_peer_does_not_forward_again(self):
        b, rb, pb, v = build("host-b", grants=[("acme", "ghost", "invoke")])
        a, ra, pa, _ = build("host-a", grants=[("acme", "ghost", "invoke")],
                             transport=LoopbackTransport(ChainEndpoint(b, v)))
        with self.assertRaises(E.TransportUnavailable):
            a.invoke("ghost", {}, ctx(v))  # no ping-pong between peers

    def test_dev_mode_without_transport_keeps_compat_sentinel(self):
        from inv21_local_service_chaining.chain import Chainer
        from inv21_local_service_chaining.residency import Residency
        self.assertEqual(Chainer(Residency("h")).call("x", "t", 1), ("remote", "x", 1))


if __name__ == "__main__":
    unittest.main()
