"""End-to-end transport tests over real mTLS sockets (MC-014, MC-017-06, MC-022, MC-025, MC-026,
MC-027, MC-030, MC-046-03/04)."""
from __future__ import annotations

import http.client
import json
import ssl
import threading
import time
import unittest

from _util import make_pki, make_service, tmpdir
from inv05_current_control_state_system.client import Client, Mirror
from inv05_current_control_state_system.errors import (
    IncompatibleVersion, InvalidArgument, LimitExceeded, PermissionDenied, QuotaExceeded, StateError,
)
from inv05_current_control_state_system.limits import Limits
from inv05_current_control_state_system.security import (
    MTLSAuthenticator, TokenAuthenticator, check_tls_context, client_tls_context, server_tls_context,
)
from inv05_current_control_state_system.server import ControlStateHTTPServer
from _util import NS_A

TD = "inv05.local"
URIS = {
    "alice": f"spiffe://{TD}/tenant/acme/env/prod/site/site-a/wl/ctrl/alice",
    "opsadmin": f"spiffe://{TD}/tenant/acme/env/prod/site/site-a/wl/ctrl/admin-ops",
    "mallory": "spiffe://evil.local/tenant/acme/env/prod/site/site-a/wl/ctrl/mallory",
}


class MTLSEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pki = make_pki(tmpdir(), URIS)
        cls.svc = make_service(Limits(rate_per_identity_rps=10_000, burst_per_identity=10_000))
        cls.sctx = server_tls_context(cls.pki["server"], cls.pki["server_key"], cls.pki["ca"])
        cls.srv = ControlStateHTTPServer(("127.0.0.1", 0), cls.svc,
                                         mtls=MTLSAuthenticator(TD, role_map={"client": {"writer"},
                                                                              "admin": {"operator", "writer"}}),
                                         ssl_context=cls.sctx, idle_timeout_s=30)
        cls.port = cls.srv.server_address[1]
        cls.srv.serve_background()

    @classmethod
    def tearDownClass(cls):
        cls.srv.graceful_shutdown(0.5)

    def client(self, who="alice", **kw):
        ctx = client_tls_context(self.pki["ca"], self.pki[who], self.pki[who + "_key"])
        return Client("localhost", self.port, ssl_context=ctx, **kw)

    def test_tls_policy_checks(self):
        self.assertEqual(check_tls_context(self.sctx, server=True), [])
        self.assertEqual(check_tls_context(client_tls_context(self.pki["ca"]), server=False), [])

    def test_txn_and_range_over_mtls(self):
        c = self.client()
        r = c.txn(success=[{"put": {"key": "e2e/a", "value": {"x": 1}}}], request_id="e2e-1")
        self.assertTrue(r["succeeded"])
        got = c.range("e2e/a")
        self.assertEqual(got["kvs"][0]["value"], {"x": 1})
        self.assertEqual(got["kvs"][0]["key"], "e2e/a")

    def test_no_client_cert_rejected(self):
        ctx = client_tls_context(self.pki["ca"])
        c = Client("localhost", self.port, ssl_context=ctx, max_attempts=1)
        with self.assertRaises(StateError) as cm:
            c.range("x")
        self.assertIn(cm.exception.code, ("CSTATE_UNAVAILABLE", "CSTATE_UNAUTHENTICATED"))

    def test_foreign_trust_domain_rejected_and_audited(self):
        c = self.client("mallory", max_attempts=1)
        with self.assertRaises(StateError) as cm:
            c.range("x")
        self.assertEqual(cm.exception.code, "CSTATE_UNAUTHENTICATED")
        self.assertTrue(any(e["class"] == "authn" and e["outcome"] == "failed" for e in self.svc.audit.entries()))

    def test_server_identity_verified_by_client(self):
        bad = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        bad.load_verify_locations(self.pki["ca"])
        conn = http.client.HTTPSConnection("127.0.0.2", self.port, context=bad, timeout=3)
        with self.assertRaises((ssl.SSLError, ssl.CertificateError, OSError)):
            conn.request("GET", "/livez")
            conn.getresponse()

    def test_health_version_metrics(self):
        c = self.client()
        conn = http.client.HTTPSConnection("localhost", self.port, context=client_tls_context(
            self.pki["ca"], self.pki["alice"], self.pki["alice_key"]), timeout=5)
        conn.request("GET", "/readyz")
        self.assertEqual(json.loads(conn.getresponse().read())["status"], "ready")
        conn.request("GET", "/version")
        self.assertIn("capabilities", json.loads(conn.getresponse().read()))
        with self.assertRaises(PermissionDenied):
            c.call("/metrics", method="GET")
        text = self.client("opsadmin").call("/metrics", method="GET")
        self.assertIn("cstate_requests_total", text)

    def test_negotiation_and_schema_errors(self):
        c = self.client(max_attempts=1)
        ok = c.call("/v1/hello", {"schema": "cstate.hello/1.0", "protocol": "PK_CSTATE", "versions": ["1.0", "1.5"]})
        self.assertEqual(ok["version"], "1.1")
        with self.assertRaises(IncompatibleVersion):
            c.call("/v1/hello", {"schema": "cstate.hello/1.0", "protocol": "PK_CSTATE", "versions": ["2.0"]})
        with self.assertRaises(IncompatibleVersion):
            c.call("/v1/range", {"schema": "cstate.range/2.0", "key": "k"})
        with self.assertRaises(InvalidArgument):
            c.call("/v1/range", {"schema": "cstate.range/1.1", "key": "k", "bogus": 1})
        # forward-compatible: newer minor may add fields
        c.call("/v1/range", {"schema": "cstate.range/1.9", "key": "k", "future_field": 1})

    def test_duplicate_keys_and_oversized_body(self):
        conn = http.client.HTTPSConnection("localhost", self.port, context=client_tls_context(
            self.pki["ca"], self.pki["alice"], self.pki["alice_key"]), timeout=5)
        body = b'{"schema":"cstate.range/1.1","key":"a","key":"b"}'
        conn.request("POST", "/v1/range", body=body, headers={"content-type": "application/json"})
        r = conn.getresponse()
        self.assertEqual((r.status, json.loads(r.read())["error"]["code"]), (400, "CSTATE_INVALID_ARGUMENT"))
        conn.request("POST", "/v1/range", body=b"x", headers={"content-length": str(10**9)})
        r = conn.getresponse()
        self.assertEqual(r.status, 413)

    def test_watch_stream_events_and_progress(self):
        c = self.client()
        frames = []

        def consume():
            for f in c.watch("stream/", progress_ms=150, timeout_s=5):
                frames.append(f)
                if sum(len(x.get("events", [])) for x in frames) >= 3 and any(x["type"] == "progress" for x in frames):
                    return
        t = threading.Thread(target=consume)
        t.start()
        time.sleep(0.3)
        for i in range(3):
            c.txn(success=[{"put": {"key": f"stream/{i}", "value": i}}], request_id=f"s{i}")
        t.join(5)
        evs = [e for f in frames for e in f.get("events", [])]
        self.assertEqual([e["key"] for e in evs], ["stream/0", "stream/1", "stream/2"])
        self.assertTrue(any(f["type"] == "progress" and "events" not in f for f in frames))
        self.assertIn("cstate.watch.deliver", {s.name for s in self.svc.tracer.finished})
        self.assertGreater(self.svc.metrics.get("cstate_net_bytes_total", dir="out"), 0)
        self.assertGreater(self.svc.metrics.get("cstate_net_connections_total", result="accepted"), 0)

    def test_mirror_converges_under_writers_and_compaction(self):
        c = self.client()
        prefix = "mirror/"
        for i in range(10):
            c.txn(success=[{"put": {"key": f"{prefix}{i}", "value": 0}}], request_id=f"m-init-{i}")
        stop = threading.Event()
        truth = {}

        def writer():
            i = 0
            wc = self.client()
            while not stop.is_set() and i < 150:
                k = f"{prefix}{i % 10}"
                wc.txn(success=[{"put": {"key": k, "value": i}}], request_id=f"m-{i}")
                truth[k] = i
                if i == 60:  # force the mirror's watch position to be compacted away
                    self.svc.store.compact(self.svc.store.revision)
                i += 1
        m = Mirror(c, prefix)
        t = threading.Thread(target=writer)
        t.start()
        t.join(20)
        m.run(lambda mm: not t.is_alive() and mm.items == {k: v for k, v in truth.items()}
              or False, max_reconnects=50)
        stop.set()
        self.assertEqual(m.items, truth)

    def test_client_retries_respect_retry_after_and_budget(self):
        sleeps = []
        c = self.client(max_attempts=3, sleep=sleeps.append)
        self.svc.controls.freeze_reads = "test"
        try:
            with self.assertRaises(StateError) as cm:
                c.range("x")
            self.assertEqual(cm.exception.code, "CSTATE_FROZEN")
            self.assertEqual(len(sleeps), 2)
        finally:
            self.svc.controls.freeze_reads = ""
        # non-idempotent mutation without request_id is never retried
        sleeps.clear()
        self.svc.controls.freeze_writes = "test"
        try:
            with self.assertRaises(StateError):
                c.txn(success=[{"put": {"key": "nr", "value": 1}}])
            self.assertEqual(sleeps, [])
        finally:
            self.svc.controls.freeze_writes = ""

    def test_server_certificate_rotation_without_restart(self):
        self.sctx.load_cert_chain(self.pki["server2"], self.pki["server2_key"])
        try:
            c = self.client()
            c.txn(success=[{"put": {"key": "rot", "value": 1}}], request_id="rot-1")
            ctx = client_tls_context(self.pki["ca"], self.pki["alice"], self.pki["alice_key"])
            with ctx.wrap_socket(__import__("socket").create_connection(("localhost", self.port)),
                                 server_hostname="localhost") as s:
                cn = dict(x[0] for x in s.getpeercert()["subject"])["commonName"]
            self.assertEqual(cn, "server2")
            self.assertEqual(c.range("rot")["kvs"][0]["value"], 1)
        finally:
            self.sctx.load_cert_chain(self.pki["server"], self.pki["server_key"])


class TokenLoopbackAndShutdown(unittest.TestCase):
    def test_bearer_tokens_and_graceful_drain(self):
        svc = make_service()
        tokens = TokenAuthenticator({"k": b"t" * 32}, "k")
        srv = ControlStateHTTPServer(("127.0.0.1", 0), svc, mtls=MTLSAuthenticator(TD, role_map={}), tokens=tokens)
        srv.serve_background()
        port = srv.server_address[1]
        c = Client("127.0.0.1", port, token=tokens.issue("svc", NS_A, ["writer"]))
        c.txn(success=[{"put": {"key": "k", "value": 1}}], request_id="t1")
        frames = []

        def consume():
            for f in c.watch("", progress_ms=100, timeout_s=10):
                frames.append(f)
        t = threading.Thread(target=consume)
        t.start()
        time.sleep(0.3)
        srv.graceful_shutdown(1.0)
        t.join(5)
        self.assertFalse(t.is_alive())
        self.assertEqual(frames[-1]["type"], "canceled")
        self.assertEqual(frames[-1]["error"]["code"], "CSTATE_DRAINING")
        reader = Client("127.0.0.1", port, token=tokens.issue("r", NS_A, ["reader"]), max_attempts=1)
        with self.assertRaises(StateError):
            reader.range("k")  # server gone

    def test_quota_maps_to_429_with_retry_after(self):
        svc = make_service(Limits(rate_per_identity_rps=0.5, burst_per_identity=1))
        tokens = TokenAuthenticator({"k": b"t" * 32}, "k")
        srv = ControlStateHTTPServer(("127.0.0.1", 0), svc, mtls=MTLSAuthenticator(TD, role_map={}), tokens=tokens)
        srv.serve_background()
        try:
            tok = tokens.issue("svc", NS_A, ["writer"])
            conn = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=5)
            for expect in (200, 429):
                conn.request("POST", "/v1/range", body=json.dumps({"schema": "cstate.range/1.1", "key": "k"}),
                             headers={"authorization": f"Bearer {tok}", "content-type": "application/json"})
                r = conn.getresponse()
                r.read()
                self.assertEqual(r.status, expect)
            self.assertIsNotNone(r.getheader("retry-after"))
        finally:
            srv.graceful_shutdown(0.1)


if __name__ == "__main__":
    unittest.main()
