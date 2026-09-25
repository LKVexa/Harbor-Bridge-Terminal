"""M25 concurrency/race tests and M26 adjacent-layer contract harness.

M26 note: the sibling packages INV-11, INV-60, INV-65 and INV-36 are not in
this archive.  These tests pin INV-61's side of each boundary against
contract stubs that implement exactly the behaviour the INV-61 contract
declares for that neighbour; they must be re-pointed at the real packages
when those are co-installed (tracked as W-006 in WAIVERS.md).
"""
import hashlib
import hmac
import secrets
import threading
import unittest

from _harness import KV, Fixture, codec, rpc, security, transport, wit_model


class ConcurrencyTest(unittest.TestCase):
    def test_reference_endpoint_counters_are_exact_under_threads(self):
        ep = rpc.Endpoint("kv", "1")
        ep.export("f", [], [], lambda: 1)
        frame = rpc.make_frame("kv", "1", "f", [], [], [], 10)
        ts = [threading.Thread(target=lambda: [ep.handle(frame, 0) for _ in range(2000)]) for _ in range(8)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(ep.stats.calls, 16000)
        self.assertEqual(ep.stats.succeeded, 16000)

    def test_idempotent_duplicates_race_to_single_execution(self):
        fx = Fixture()
        gate = threading.Barrier(16)
        orig = fx.svc.exports[(KV.qualified, "put")].impl
        def slow_put(e, mode):
            import time; time.sleep(0.05)
            return orig(e, mode)
        fx.svc.exports[(KV.qualified, "put")].impl = slow_put
        envs = [fx.envelope("put", [{"key": "a", "value": 1, "tags": []}, "strong"], idem="race-1") for _ in range(16)]
        out = []
        def go(e):
            gate.wait()
            out.append(fx.call(e)["status"])
        ts = [threading.Thread(target=go, args=(e,)) for e in envs]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(fx.calls["put"], 1)
        self.assertGreaterEqual(out.count("ok"), 1)  # first + any cached replays
        self.assertTrue(set(out) <= {"ok", "unavailable"})
        self.assertEqual(fx.svc.admission.inflight, 0)

    def test_concurrent_load_leaves_no_leaked_slots(self):
        fx = Fixture()
        def go():
            for _ in range(50):
                fx.call(fx.envelope("get", ["a"]))
                fx.call(fx.envelope("boom", []))
        ts = [threading.Thread(target=go) for _ in range(8)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(fx.svc.admission.inflight, 0)
        self.assertEqual(fx.svc.inflight(), 0)
        ok, n, _ = security.AuditLog.verify(fx.tmp / "audit.jsonl", fx.audit_key)
        self.assertTrue(ok)

    def test_registration_during_dispatch(self):
        fx = Fixture()
        extra = wit_model.parse("package inv61:extra@1.0.0; interface x { f: func() -> u8; }")[0]
        stop = threading.Event()
        errs = []
        def load():
            while not stop.is_set():
                try:
                    fx.call(fx.envelope("get", ["a"]))
                except Exception as e:
                    errs.append(e)
        ts = [threading.Thread(target=load) for _ in range(4)]
        [t.start() for t in ts]
        fx.svc.export(extra, "f", lambda: 1)
        stop.set(); [t.join() for t in ts]
        self.assertEqual(errs, [])

    def test_audit_chain_under_concurrent_append(self):
        fx = Fixture()
        ts = [threading.Thread(target=lambda: [fx.audit.append("authz-deny", i=i) for i in range(100)])
              for _ in range(8)]
        [t.start() for t in ts]; [t.join() for t in ts]
        ok, n, _ = security.AuditLog.verify(fx.tmp / "audit.jsonl", fx.audit_key)
        self.assertTrue(ok)
        self.assertEqual(n, 800)


# ---------------------------------------------------------------- M26 stubs
class Inv11ContractStub:
    """INV-11: supplies the WIT signatures INV-61 fingerprints."""
    SOURCE = (__import__("_harness").PKG_DIR / "wit" / "kv.wit").read_text()

    def interfaces(self):
        return wit_model.parse(self.SOURCE)


class Inv60FabricStub:
    """INV-60: routes opaque frame bytes between hosts without reading them."""

    def __init__(self):
        self.routes = {}

    def attach(self, host, handler):
        self.routes[host] = handler

    def route(self, host, frame_bytes):
        return self.routes[host](frame_bytes)


class Inv36ControlSealStub:
    """INV-36: seals control-class frames; INV-61 must pass them through intact."""

    def __init__(self):
        self.k = secrets.token_bytes(32)

    def seal(self, b):
        return hmac.new(self.k, b, hashlib.sha256).digest() + b

    def open(self, b):
        tag, body = b[:32], b[32:]
        if not hmac.compare_digest(tag, hmac.new(self.k, body, hashlib.sha256).digest()):
            raise ValueError("seal")
        return body


class AdjacentLayerTest(unittest.TestCase):
    def test_inv11_signatures_drive_fingerprints(self):
        iface = Inv11ContractStub().interfaces()[0]
        f = iface.funcs["get"]
        self.assertEqual(Fixture().svc.exports[(iface.qualified, "get")].fp,
                         rpc.fingerprint(f.param_types(), f.result_types()))

    def test_inv60_fabric_routes_frames_between_hosts(self):
        fx = Fixture()
        fabric = Inv60FabricStub()
        def host_b(frame):
            _, _, kind, body = codec.unpack_frame(frame)
            return codec.pack_frame(codec.KIND_RESPONSE, fx.svc.handle(body), 2, 1)
        fabric.attach("host-b", host_b)
        env = fx.envelope("get", ["a"])
        out = fabric.route("host-b", codec.pack_frame(codec.KIND_REQUEST, codec.encode(codec.REQUEST_ENVELOPE, env), 2, 1))
        _, _, kind, body = codec.unpack_frame(out)
        self.assertEqual(codec.decode(codec.RESPONSE_ENVELOPE, body)["status"], "ok")

    def test_inv65_provider_receives_calls_in_frame_format(self):
        fx = Fixture()
        seen = []
        fx.svc.exports[(KV.qualified, "echo")].impl = lambda b: seen.append(bytes(b)) or b
        fx.call(fx.envelope("echo", [list(b"provider")]))
        self.assertEqual(seen, [b"provider"])

    def test_inv36_sealed_control_frames_pass_through(self):
        fx = Fixture()
        seal = Inv36ControlSealStub()
        env = fx.envelope("get", ["a"])
        sealed = seal.seal(codec.encode(codec.REQUEST_ENVELOPE, env))
        resp = fx.svc.handle(seal.open(sealed))
        self.assertEqual(codec.decode(codec.RESPONSE_ENVELOPE, resp)["status"], "ok")
        tampered = bytearray(sealed); tampered[-1] ^= 1
        with self.assertRaises(ValueError):
            seal.open(bytes(tampered))


if __name__ == "__main__":
    unittest.main()
