"""Adjacent-layer integration through contract doubles, local execution tier (C030, C074, C083).

Real-component tier: tests/test_integration_real.py.  These doubles cannot satisfy it.
"""
import gc
import threading
import time
import unittest

from _util import m, rt as make_rt

adj = m("adjacent")
future = m("future")
errors = m("errors")
telemetry = m("telemetry")


class INV15WaitableSetTest(unittest.TestCase):
    def test_readiness_paths(self):
        """REQ: C030 C083 C003"""
        rt = make_rt()
        ws = adj.WaitableSet(rt)
        caps = [rt.create(int) for _ in range(3)]
        for _, r in caps:
            ws.join(r)
        self.assertEqual(ws.poll(), [])
        rt.resolve(caps[1][0], 5)
        ready = ws.poll()
        self.assertEqual([c.future_id for c in ready], [caps[1][1].future_id])
        self.assertEqual(rt.take(ready[0]), ("ok", 5))
        rt.abandon(caps[0][0])                                   # abandonment propagates as readiness
        r0 = ws.poll()[0]
        with self.assertRaises(future.Abandoned):
            rt.take(r0)
        threading.Timer(0.02, lambda: rt.resolve_error(caps[2][0], "late")).start()
        self.assertEqual(len(ws.poll(timeout=2)), 1)             # timeout path
        self.assertEqual(adj.check_layer_version("INV-15", 1), 1)
        with self.assertRaises(errors.Rejected) as cm:
            adj.check_layer_version("INV-15", 2)
        self.assertEqual(cm.exception.code, "INCOMPATIBLE_VERSION")


class INV12CodecTest(unittest.TestCase):
    def test_lower_lift_paths(self):
        """REQ: C030 C083"""
        rt = make_rt()
        w, r = rt.create(float)
        rt.resolve(w, adj.Codec.lift(adj.Codec.lower(3), float))
        self.assertEqual(rt.take(r), ("ok", 3.0))
        with self.assertRaises(errors.Rejected) as cm:
            adj.Codec.lift(adj.Codec.lower("x"), int)
        self.assertEqual(cm.exception.code, "TYPE_MISMATCH")
        with self.assertRaises(errors.Rejected) as cm:
            adj.Codec.lift(b"\x00garbage", int)
        self.assertEqual(cm.exception.code, "INVALID_ARGUMENT")
        with self.assertRaises(errors.Rejected):
            adj.Codec.lift(adj.Codec.lower(True), int)


class INV16AsyncTest(unittest.TestCase):
    def test_return_error_crash_timeout_trace(self):
        """REQ: C030 C083 C074 C051"""
        rt = make_rt()
        parent = telemetry.TraceContext.new()
        r, t = adj.async_call(rt, lambda: 7, int, trace=parent)
        self.assertEqual(rt.take_wait(r, 5), ("ok", 7))
        r, t = adj.async_call(rt, lambda: 1 / 0, int)
        tag, msg = rt.take_wait(r, 5)
        self.assertEqual(tag, "error")
        self.assertTrue(msg.startswith("INTERNAL_INVARIANT") or msg.startswith("INVALID_ARGUMENT"))
        def crash():
            raise SystemExit
        r, t = adj.async_call(rt, crash, int)
        t.join(); gc.collect()
        with self.assertRaises(future.Abandoned):
            rt.take_wait(r, 5)
        r, t = adj.async_call(rt, lambda: time.sleep(0.3) or 1, int)
        with self.assertRaises(errors.Rejected) as cm:
            rt.take_wait(r, 0.01)                                 # dependency slow: caller deadline
        self.assertEqual(cm.exception.code, "TIMEOUT")
        self.assertEqual(rt.take_wait(r, 5), ("ok", 1))

    def test_trace_continuity(self):
        """REQ: C074 C083"""
        rt = make_rt()
        parent = telemetry.TraceContext.parse("00-" + "a" * 32 + "-" + "b" * 16 + "-01")
        self.assertEqual(parent.trace_id, "a" * 32)
        r, t = adj.async_call(rt, lambda: 1, int, trace=parent)
        info = rt.inspect(r)
        self.assertEqual(info["trace_id"], "a" * 32)
        rt.take_wait(r, 5)


class INV17StreamTest(unittest.TestCase):
    def test_stream_to_completion(self):
        """REQ: C030 C083 C001"""
        rt = make_rt()
        self.assertEqual(rt.take(adj.completion_from_stream(rt, adj.Stream([4]), int)), ("ok", 4))
        with self.assertRaises(future.Abandoned):
            rt.take(adj.completion_from_stream(rt, adj.Stream([]), int))
        tag, msg = rt.take(adj.completion_from_stream(rt, adj.Stream([1, 2]), int))
        self.assertEqual(tag, "error")
        self.assertIn("more than one value", msg)


class INV20HttpTest(unittest.TestCase):
    def test_trailer_paths(self):
        """REQ: C030 C083 C074"""
        rt = make_rt()
        tr = telemetry.TraceContext.new()
        r = adj.http_trailers(rt, [b"body", {"status": 200}], trace=tr)
        self.assertEqual(rt.inspect(r)["trace_id"], tr.trace_id)
        self.assertEqual(rt.take(r), ("ok", 200))
        self.assertEqual(rt.take(adj.http_trailers(rt, [b"x", {"status": 503}]))[0], "error")
        with self.assertRaises(future.Abandoned):
            rt.take(adj.http_trailers(rt, [b"partial"]))          # connection dropped
        self.assertEqual(rt.take(adj.http_trailers(rt, [{"status": "x"}]))[0], "error")
        # duplicate trailers: last block wins, still exactly one resolution
        self.assertEqual(rt.take(adj.http_trailers(rt, [{"status": 201}, {"status": 202}])), ("ok", 202))
        self.assertEqual(rt.metrics.counter("inv18_double_resolutions_total"), 0)


class TierMatrixTest(unittest.TestCase):
    def test_local_and_wire_tier_identical_semantics(self):
        """REQ: C083 C030 — local tier vs remote-adapter tier give the same outcomes"""
        rt = make_rt()
        auth, adapters = m("auth"), m("adapters")
        kr = auth.KeyRing(); kr.add("k", b"k" * 32)
        au = auth.Authenticator(kr)
        cli = adapters.RemoteClient(adapters.Link(adapters.RemoteEndpoint(rt, au)), au, "t",
                                    ["create", "resolve", "receive", "abandon"])
        for scenario in ("value", "error", "abandon"):
            w, r = rt.create(int)
            fid = cli.create("int")["result"]["future_id"]
            if scenario == "value":
                rt.resolve(w, 1); cli.resolve(fid, 1)
                self.assertEqual(rt.take(r)[0], cli.take(fid, "int")["result"]["outcome"])
            elif scenario == "error":
                rt.resolve_error(w, "e"); cli.resolve_error(fid, errors.ErrorRecord("TIMEOUT", "e"))
                self.assertEqual(rt.take(r)[0], cli.take(fid, "int")["result"]["outcome"])
            else:
                rt.abandon(w); cli.abandon(fid)
                with self.assertRaises(future.Abandoned) as cm:
                    rt.take(r)
                self.assertEqual(cm.exception.code, cli.take(fid, "int")["error"]["code"])


if __name__ == "__main__":
    unittest.main()
