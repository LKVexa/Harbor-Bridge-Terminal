"""M03, M23, M26, M29 - end-to-end over real loopback TCP: happy path, adversarial
peers, adjacent-layer contract stubs, and fault injection."""
import json
import os
import pathlib
import socket
import struct
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from wrpc import controls as C, node as N, ops as O, security as S, wit  # noqa: E402
from wrpc.codec import encode_frame  # noqa: E402
from rpc import fingerprint  # noqa: E402

SERVER_WIT = """package pk:kv@0.2.0;
interface store {
  variant err { missing, denied(string) }
  get: func(k: string) -> result<u64, err>;
  put: func(k: string, v: u64);
  slow: func(ms: u32) -> u32;
  boom: func();
  bad-result: func() -> u8;
}"""


class Harness:
    def __init__(self, grants=None, cfg=None, journal=None, audit_path=None, creds_from=None):
        self.pkg = wit.parse(SERVER_WIT)
        if creds_from is not None:        # a restarted node keeps the same enrolled credentials
            self.kr, self.psk, self.kid, self.psk_b, self.kid_b = (
                creds_from.kr, creds_from.psk, creds_from.kid, creds_from.psk_b, creds_from.kid_b)
        else:
            self.kr = S.Keyring()
            self.psk = os.urandom(32)
            self.kid = self.kr.add("svc-a", self.psk, 3600)
            self.psk_b = os.urandom(32)
            self.kid_b = self.kr.add("svc-b", self.psk_b, 3600)
        self.store = {}
        self.exec_count = {"put": 0}

        def put(k, v):
            self.exec_count["put"] += 1
            self.store[k] = v

        impls = {("pk:kv/store", "get"): lambda k: {"ok": self.store[k]} if k in self.store else {"err": {"missing": None}},
                 ("pk:kv/store", "put"): put,
                 ("pk:kv/store", "slow"): lambda ms: (time.sleep(ms / 1000), ms)[1],
                 ("pk:kv/store", "boom"): lambda: 1 / 0,
                 ("pk:kv/store", "bad-result"): lambda: 999}
        c, _ = O.ConfigStore.build(("test", cfg or {}))
        self.cfg = c
        g = grants if grants is not None else [C.Grant("t1", "svc-a", "pk:kv/store", "*"),
                                               C.Grant("t2", "svc-b", "pk:kv/store", "get")]
        self.logs, self.spans = [], []
        self.node = N.Node(c, self.kr, self.pkg, impls, {"svc-a": "t1", "svc-b": "t2"}, C.Authorizer(g),
                           audit=O.AuditLog(audit_path), journal=journal, log_sink=self.logs.append,
                           span_exporter=self.spans.append)
        self.host, self.port = self.node.start()

    def client(self, peer="svc-a", pkg_src=SERVER_WIT, **kw):
        kid, psk = (self.kid, self.psk) if peer == "svc-a" else (self.kid_b, self.psk_b)
        return N.Client(self.host, self.port, peer, kid, psk, self.cfg["node_id"], wit.parse(pkg_src), **kw)

    def raw(self):
        return socket.create_connection((self.host, self.port), timeout=2)

    def close(self):
        self.node.stop()


class EndToEndTest(unittest.TestCase):
    def setUp(self):
        self.h = Harness()

    def tearDown(self):
        self.h.close()

    def test_typed_round_trip(self):
        c = self.h.client()
        self.assertEqual(c.call("store", "put", ["a", 5]), {"ok": None})
        self.assertEqual(c.call("store", "get", ["a"]), {"ok": {"ok": 5}})
        self.assertEqual(c.call("store", "get", ["zz"]), {"ok": {"err": {"missing": None}}})
        self.assertEqual(c.version, "wrpc/2")

    def test_typed_errors_not_transport_failures(self):
        c = self.h.client()
        self.assertEqual(c.call("store", "boom", []), {"error": "callee-trap"})
        self.assertEqual(c.call("store", "bad-result", [])["error"], "result-type")
        self.assertEqual(c.call("store", "slow", [300], timeout_s=0.1, idempotent=False)["error"], "deadline-exceeded")

    def test_signature_drift_rejected_before_args_decoded(self):
        drifted = SERVER_WIT.replace("put: func(k: string, v: u64);", "put: func(k: string, v: s64);")
        c = self.h.client(pkg_src=drifted)
        self.assertEqual(c.call("store", "put", ["a", -1]), {"error": "signature-mismatch"})
        self.assertEqual(self.h.exec_count["put"], 0)

    def test_version_drift_rejected(self):
        c = self.h.client(pkg_src=SERVER_WIT.replace("@0.2.0", "@0.3.0"))
        self.assertEqual(c.call("store", "get", ["a"]), {"error": "version-mismatch", "expected": "0.2.0"})

    def test_authorization_default_deny_and_tenant_isolation(self):
        b = self.h.client("svc-b")
        self.assertEqual(b.call("store", "put", ["x", 1]), {"error": "permission-denied"})
        self.assertIn("ok", b.call("store", "get", ["x"]))
        denies = [r for r in self.h.node.audit.records if r["event"] == "authz" and r["decision"] == "deny"]
        self.assertEqual(denies[-1]["peer"], "svc-b")

    def test_retry_with_same_request_id_executes_once(self):
        c = self.h.client()
        rid = os.urandom(16).hex()
        c.call("store", "put", ["k", 1], request_id=rid)
        c.close()                                   # simulate reconnect
        c.call("store", "put", ["k", 1], request_id=rid)
        self.assertEqual(self.h.exec_count["put"], 1)

    def test_observability_emitted(self):
        c = self.h.client()
        tp = "00-" + "ab" * 16 + "-" + "cd" * 8 + "-01"
        c.call("store", "get", ["a"], traceparent=tp)
        self.assertIn("inv61_calls_total", self.h.node.metrics.render())
        self.assertTrue(any(json.loads(l)["event"] == "call" for l in self.h.logs))
        self.assertEqual(self.h.spans[-1]["trace_id"], "ab" * 16)
        self.assertTrue(O.AuditLog.verify(self.h.node.audit.records)[0])
        self.assertEqual(self.h.node.health.ready()["status"], "pass")
        self.h.node.drain()
        self.assertEqual(self.h.node.health.ready()["status"], "fail")


class DefectRegressionTest(unittest.TestCase):
    """Regressions for defects found by the independent assessment pass."""

    def setUp(self):
        self.h = Harness()

    def tearDown(self):
        self.h.close()

    def test_retry_after_overload_eventually_executes(self):
        h = self.h
        h.node.admission.max_inflight = 0          # force admission refusal
        c = h.client(retry=C.RetryPolicy(max_attempts=1))
        rid = os.urandom(16).hex()
        self.assertEqual(c.call("store", "put", ["k", 1], request_id=rid)["error"], "overloaded")
        h.node.admission.max_inflight = 8
        self.assertEqual(c.call("store", "put", ["k", 1], request_id=rid), {"ok": None})
        self.assertEqual(h.exec_count["put"], 1)

    def test_request_id_reuse_across_functions_conflicts(self):
        c = self.h.client()
        rid = os.urandom(16).hex()
        c.call("store", "put", ["k", 1], request_id=rid)
        self.assertEqual(c.call("store", "get", ["k"], request_id=rid), {"error": "idempotency-conflict"})

    def test_revoked_key_ends_live_session(self):
        c = self.h.client()
        self.assertIn("ok", c.call("store", "get", ["a"]))
        self.h.kr.revoke(self.h.kid)
        self.assertEqual(c.call("store", "get", ["a"], timeout_s=0.5)["error"], "transport")
        self.assertTrue(any(r["event"] == "record-reject" and r["reason"] == "credential-revoked"
                            for r in self.h.node.audit.records))

    def test_drain_refuses_new_work_and_readiness_fails(self):
        c = self.h.client()
        self.assertIn("ok", c.call("store", "get", ["a"]))
        self.assertTrue(self.h.node.drain(timeout_s=1))
        self.assertEqual(c.call("store", "get", ["a"], idempotent=False)["error"], "unavailable")
        self.assertEqual(self.h.node.health.ready()["status"], "fail")

    def test_audit_failure_fails_closed_and_flips_readiness(self):
        def broken(*a, **k):
            raise OSError("disk full")
        self.h.node.audit.append = broken
        c = self.h.client()
        self.assertEqual(c.call("store", "put", ["k", 1], idempotent=False)["error"], "unavailable")
        self.assertEqual(self.h.exec_count["put"], 0)
        self.assertEqual(self.h.node.health.ready()["checks"]["audit-writable"]["status"], "fail")

    def test_drain_waits_for_in_flight_call_and_refuses_connections(self):
        c = self.h.client()
        out = []
        t = threading.Thread(target=lambda: out.append(c.call("store", "slow", [300], idempotent=False)))
        t.start()
        time.sleep(0.1)
        t0 = time.time()
        self.assertTrue(self.h.node.drain(timeout_s=2))
        self.assertGreater(time.time() - t0, 0.1)            # it actually waited
        t.join()
        self.assertEqual(out, [{"ok": 300}])
        s = self.h.raw()
        s.settimeout(2)
        self.assertEqual(s.recv(1), b"")                       # new connection refused

    def test_broken_log_sink_and_journal_do_not_drop_responses(self):
        self.h.node.log.sink = lambda line: 1 / 0
        class BadJournal:
            def append(self, *a):
                raise OSError("disk full")
        self.h.node.idem.journal = BadJournal()
        self.assertEqual(self.h.client().call("store", "put", ["k", 1]), {"ok": None})
        self.assertEqual((self.h.node.log.sink_failures > 0, self.h.node.idem.journal_failures), (True, 1))

    def test_readiness_recovers_after_transient_audit_failure(self):
        orig = self.h.node.audit.append
        self.h.node.audit.append = lambda *a, **k: (_ for _ in ()).throw(OSError("blip"))
        self.h.client().call("store", "get", ["a"], idempotent=False)
        self.assertEqual(self.h.node.health.ready()["checks"]["audit-writable"]["status"], "fail")
        self.h.node.audit.append = orig
        self.h.client().call("store", "get", ["a"])
        self.h.node.health._cache.clear()
        self.assertEqual(self.h.node.health.ready()["checks"]["audit-writable"]["status"], "pass")

    def test_tampered_audit_file_refused_on_reload(self):
        import tempfile as _tf
        with _tf.TemporaryDirectory() as d:
            p = os.path.join(d, "a.jsonl")
            a = O.AuditLog(p)
            for i in range(3):
                a.append("e", subject=str(i))
            lines = open(p).read().splitlines()
            lines[1] = lines[1].replace('"subject": "1"', '"subject": "X"')
            open(p, "w").write("\n".join(lines) + "\n")
            with self.assertRaises(ValueError):
                O.AuditLog(p)

    def test_span_status_reflects_typed_error_and_logs_correlate(self):
        tp = "00-" + "ab" * 16 + "-" + "cd" * 8 + "-01"
        self.h.client("svc-b").call("store", "put", ["x", 1], traceparent=tp)
        self.assertEqual((self.h.spans[-1]["status"], self.h.spans[-1]["error"]), ("error", "permission-denied"))
        rec = json.loads(self.h.logs[-1])
        self.assertEqual(rec["trace_id"], "ab" * 16)
        self.assertEqual(len(rec["request_id"]), 32)

    def test_client_maps_malformed_response_to_typed_error(self):
        orig = self.h.node.handle
        self.h.node.handle = lambda body, tenant, peer: b"\x00\xff\xff"      # garbage result bytes
        try:
            self.assertEqual(self.h.client().call("store", "get", ["a"])["error"], "malformed-response")
        finally:
            self.h.node.handle = orig


class AdversarialTest(unittest.TestCase):
    """M23 abuse cases driven over the socket."""

    def setUp(self):
        self.h = Harness(cfg={"handshake_timeout_s": 0.5})

    def tearDown(self):
        self.h.close()

    def _closed(self, s):
        s.settimeout(2)
        try:
            return s.recv(1) == b""
        except (ConnectionResetError, socket.timeout):
            return True

    def test_oversize_length_prefix_refused_without_allocation(self):
        s = self.h.raw()
        s.sendall(struct.pack(">I", 0xFFFFFFFF))
        self.assertTrue(self._closed(s))

    def test_garbage_handshake(self):
        s = self.h.raw()
        body = b"not json"
        s.sendall(struct.pack(">I", len(body)) + body)
        self.assertTrue(self._closed(s))

    def test_slowloris_handshake_times_out(self):
        s = self.h.raw()
        s.sendall(b"\x00\x00")            # half a length prefix, then silence
        t0 = time.time()
        self.assertTrue(self._closed(s))
        self.assertLess(time.time() - t0, 2.0)

    def test_unknown_peer_and_unenrolled_peer(self):
        kr_outsider = os.urandom(32)
        c = N.Client(self.h.host, self.h.port, "svc-x", "bogus", kr_outsider, self.h.cfg["node_id"], self.h.pkg)
        self.assertEqual(c.call("store", "get", ["a"], timeout_s=0.5)["error"], "transport")
        self.h.kr.add("svc-enrolled-nowhere", b"k" * 32, 3600, key_id="kz")
        c2 = N.Client(self.h.host, self.h.port, "svc-enrolled-nowhere", "kz", b"k" * 32, self.h.cfg["node_id"], self.h.pkg)
        self.assertEqual(c2.call("store", "get", ["a"], timeout_s=0.5)["error"], "transport")
        codes = {r["reason"] for r in self.h.node.audit.records if r["event"] == "authn" and r["decision"] == "deny"}
        self.assertTrue({"authentication-failed", "peer-not-enrolled"} <= codes)

    def test_record_replay_on_live_session_kills_session(self):
        s = self.h.raw()
        hs = S.ClientHandshake("svc-a", self.h.kid, self.h.psk)
        N._send(s, json.dumps(hs.hello).encode())
        fin, chan, _ = hs.finish(json.loads(N._recv(s, 4096)), self.h.cfg["node_id"])
        N._send(s, json.dumps(fin).encode())
        sig = self.h.pkg.interfaces["store"].functions["put"]
        from wrpc.codec import encode_args
        frame = encode_frame({"interface": "pk:kv/store", "version": "0.2.0", "function": "put",
                              "fp": fingerprint(sig.param_texts(), sig.result_texts()), "deadline": time.time() + 5,
                              "request_id": os.urandom(16).hex(), "traceparent": ""},
                             encode_args([t for _, t in sig.params], ["r", 1]))
        rec = chan.seal(frame)
        N._send(s, rec)
        chan.open(N._recv(s, 1 << 21))
        N._send(s, rec)                       # replay the exact record
        self.assertTrue(self._closed(s))
        self.assertEqual(self.h.exec_count["put"], 1)
        self.assertTrue(any(r["event"] == "record-reject" and r["reason"] == "replay" for r in self.h.node.audit.records))

    def test_malformed_frame_inside_valid_session(self):
        out = self.h.node.handle(b"\x00garbage", "t1", "svc-a")
        self.assertEqual(json.loads(out[1:])["error"], "malformed-frame")

    def test_expired_deadline_never_dispatches(self):
        sig = self.h.pkg.interfaces["store"].functions["put"]
        frame = encode_frame({"interface": "pk:kv/store", "version": "0.2.0", "function": "put",
                              "fp": fingerprint(sig.param_texts(), sig.result_texts()), "deadline": 1.0,
                              "request_id": "00" * 16, "traceparent": ""}, b"")
        self.assertEqual(json.loads(self.h.node.handle(frame, "t1", "svc-a")[1:])["error"], "deadline-exceeded")
        self.assertEqual(self.h.exec_count["put"], 0)

    def test_connection_limit(self):
        self.h.close()
        h = Harness(cfg={"max_connections": 2, "handshake_timeout_s": 2.0})
        try:
            socks = [h.raw() for _ in range(2)]
            time.sleep(0.2)
            extra = h.raw()
            self.assertTrue(self._closed(extra))
            [s.close() for s in socks]
        finally:
            h.close()
        self.h = Harness()


class AdjacentLayerContractTest(unittest.TestCase):
    """M26 - contract stubs for INV-11/36/60/65. These pin INV-61's side of each
    boundary; the real neighbours are not in this archive (see docs/REQUIREMENTS.md)."""

    def test_inv11_interface_language_feeds_fingerprints(self):
        # INV-11 owns interface definitions; INV-61 consumes its WIT text verbatim.
        pkg = wit.parse(SERVER_WIT)
        f = pkg.interfaces["store"].functions["get"]
        self.assertEqual(len(fingerprint(f.param_texts(), f.result_texts())), 16)

    def test_inv60_fabric_routes_opaque_frames(self):
        # INV-60 routes frames between hosts: it must be able to read the header
        # (interface/function) without the argument schema.
        from wrpc.codec import decode_header
        raw = encode_frame({"interface": "pk:kv/store", "version": "0.2.0", "function": "get", "fp": "00" * 8,
                            "deadline": 1.0, "request_id": "00" * 16, "traceparent": ""}, b"\x07opaque")
        self.assertEqual(decode_header(raw)[0]["interface"], "pk:kv/store")

    def test_inv65_provider_receives_typed_errors(self):
        h = Harness()
        try:
            r = h.client().call("store", "boom", [])
            self.assertEqual(set(r), {"error"})
        finally:
            h.close()

    def test_inv36_control_class_frames_are_sealed(self):
        # INV-36 seals control-class frames; INV-61's own records are AEAD-sealed,
        # so a control frame carried here is never in plaintext on the wire.
        kr = S.Keyring()
        psk = os.urandom(32)
        kid = kr.add("c", psk, 60)
        c = S.ClientHandshake("c", kid, psk)
        s = S.ServerHandshake("srv", kr)
        _, chan, _ = c.finish(s.accept(c.hello), "srv")
        self.assertNotIn(b"control-plane", chan.seal(b"control-plane:freeze"))


class FaultInjectionTest(unittest.TestCase):
    """M29 - server killed mid-session, restart with journal, breaker opens, recovery."""

    def test_server_crash_reconnect_and_journal_replay(self):
        with tempfile.TemporaryDirectory() as d:
            jpath = os.path.join(d, "idem.jsonl")
            h = Harness(journal=O.Journal(jpath))
            port = h.port
            c = h.client(retry=C.RetryPolicy(max_attempts=3, base_s=0.01, budget_ratio=10))
            rid = os.urandom(16).hex()
            c.call("store", "put", ["k", 7], request_id=rid)
            h.close()                                             # crash
            self.assertEqual(c.call("store", "get", ["k"], timeout_s=0.5)["error"], "transport")
            h2 = Harness(journal=O.Journal(jpath), cfg={"listen_port": port}, creds_from=h)
            try:
                c.addr = (h2.host, h2.port)
                self.assertEqual(c.call("store", "put", ["k", 7], request_id=rid), {"ok": None})
                self.assertEqual(h2.exec_count["put"], 0)       # outcome replayed from journal, not re-executed
            finally:
                h2.close()

    def test_breaker_opens_on_dead_peer_then_recovers(self):
        now = [0.0]
        br = C.CircuitBreaker(threshold=2, cooldown_s=1, clock=lambda: now[0])
        h = Harness()
        port = h.port
        c = h.client(breaker=br, retry=C.RetryPolicy(max_attempts=1))
        h.close()
        for _ in range(2):
            c.call("store", "get", ["a"], timeout_s=0.3)
        self.assertEqual(c.call("store", "get", ["a"])["error"], "circuit-open")
        h2 = Harness(cfg={"listen_port": port}, creds_from=h)
        try:
            now[0] = 2
            self.assertIn("ok", c.call("store", "get", ["a"]))
            self.assertEqual(br.state, "closed")
        finally:
            h2.close()

    def test_audit_log_survives_restart_and_verifies(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "audit.jsonl")
            h = Harness(audit_path=p)
            h.client().call("store", "get", ["a"])
            head = h.node.audit.head()
            h.close()
            recs = list(O.AuditLog(p).records)
            self.assertTrue(O.AuditLog.verify(recs[: head[0]], head)[0])

    def test_overload_sheds_with_typed_error(self):
        h = Harness(cfg={"max_inflight": 1, "max_queue": 0, "per_tenant_inflight": 1})
        try:
            out = []
            cs = [h.client() for _ in range(4)]
            ts = [threading.Thread(target=lambda c=c: out.append(c.call("store", "slow", [200], idempotent=False)))
                  for c in cs]
            [t.start() for t in ts]
            [t.join() for t in ts]
            self.assertIn({"ok": 200}, out)
            self.assertIn("overloaded", [o.get("error") for o in out])
        finally:
            h.close()


if __name__ == "__main__":
    unittest.main()
