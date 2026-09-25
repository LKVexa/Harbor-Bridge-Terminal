"""HTTP surface, GitOps ingestion, INV-64/INV-63/GAP-13 adapters and resilience (MC-019/020/021/041/049/056)."""
from __future__ import annotations

import json
import pathlib
import random
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from support import Harness, component, request
from inv66_enterprise_wasm_control_plane import gitops
from inv66_enterprise_wasm_control_plane.adapters import HttpDeploymentManager, HttpPolicyEngine
from inv66_enterprise_wasm_control_plane.errors import ControlPlaneError, fail
from inv66_enterprise_wasm_control_plane.http_api import serve
from inv66_enterprise_wasm_control_plane.resilience import (Bulkhead, CircuitBreaker, Deadline, RetryPolicy,
                                                            TokenBucket, call_with_policy)


def fake_dependency(handler_fn):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            code, out = handler_fn(body, self.headers)
            data = json.dumps(out).encode()
            self.send_response(code)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/"


class HttpTest(unittest.TestCase):
    def setUp(self):
        self.h = Harness()
        self.srv = serve(self.h.svc, port=0)
        self.base = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.h.close()

    def call(self, method, path, body=None, tok=None):
        req = urllib.request.Request(self.base + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else None)
        if tok:
            req.add_header("Authorization", f"Bearer {tok}")
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                raw = r.read()
                return r.status, (json.loads(raw) if r.headers["Content-Type"].startswith("application/json") else raw.decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_endpoints(self):
        self.assertEqual(self.call("GET", "/healthz")[0], 200)
        code, ready = self.call("GET", "/readyz")
        self.assertEqual((code, ready["leader"]), (200, True))
        code, ver = self.call("GET", "/version")
        self.assertEqual(ver["version"], "4.3.0")
        code, r = self.call("POST", "/v1/admit", request(), self.h.tok())
        self.assertEqual(code, 200)
        code, r2 = self.call("POST", "/v1/admit", request([component("x", signer="n")], rid="b"), self.h.tok())
        self.assertEqual((code, r2["errors"][0]["code"]), (403, "SIGNER_NOT_APPROVED"))
        code, e = self.call("POST", "/v1/admit", request())
        self.assertEqual((code, e["error"]["code"]), (401, "AUTHN_MISSING"))
        code, ex = self.call("GET", f"/v1/decisions/{r['decision_id']}/explain", tok=self.h.tok("user:auditor"))
        self.assertEqual(code, 200)
        code, inv = self.call("GET", "/v1/inventory?tenant=payments", tok=self.h.tok("user:auditor"))
        self.assertIn("payments/prod-eu", inv["lattices"])
        code, aud = self.call("GET", "/v1/audit?kind=admission", tok=self.h.tok("user:auditor"))
        self.assertEqual(len(aud["records"]), 2)
        code, m = self.call("GET", "/metrics")
        self.assertIn("inv66_admissions_total", m)
        code, fz = self.call("POST", "/v1/freeze", {"scope": "org:acme", "on": True, "reason": "drill"}, self.h.tok("user:root"))
        self.assertEqual(code, 200)
        code, e = self.call("POST", "/v1/admit", request(rid="c"), self.h.tok())
        self.assertEqual((code, e["error"]["code"]), (423, "FROZEN"))
        self.assertEqual(self.call("GET", "/nope")[0], 404)


class AdapterTest(unittest.TestCase):
    def test_http_policy_engine_and_deployment_manager(self):
        seen = {}

        def policy(body, headers):
            seen["tp"] = headers.get("traceparent")
            return 200, {"allowed": "debug" not in json.dumps(body), "policy_version": "b7", "rule": "r"}

        def deploy(body, headers):
            seen["idem"] = headers.get("Idempotency-Key")
            return 200, {"delivery_id": body["delivery_id"], "accepted": True, "ref": "x"}
        ps, purl = fake_dependency(policy)
        ds, durl = fake_dependency(deploy)
        h = Harness()
        h.svc.policy_engine = HttpPolicyEngine(purl, "b7")
        h.svc.deployer = HttpDeploymentManager(durl)
        r = h.svc.admit(h.tok(), request())
        self.assertTrue(r["admitted"])
        self.assertEqual(h.svc.state["decisions"][r["decision_id"]]["state"], "deployed")
        self.assertEqual(seen["idem"], r["decision_id"])
        self.assertTrue(seen["tp"].startswith("00-" + r["trace_id"]))
        self.assertFalse(h.svc.admit(h.tok(), request([component("debug")], rid="d"))["admitted"])
        h.svc.policy_engine = HttpPolicyEngine(purl, "b8")          # version pin mismatch -> fail closed
        r = h.svc.admit(h.tok(), request(rid="e"))
        self.assertEqual(r["errors"][0]["code"], "POLICY_UNAVAILABLE")
        ps.shutdown(); ds.shutdown(); ps.server_close(); ds.server_close(); h.close()

    def test_https_required_for_remote_policy(self):
        with self.assertRaises(ValueError):
            HttpPolicyEngine("http://policy.example/", "v")

    def test_gitops_changeset_ingestion(self):
        h = Harness()
        root = pathlib.Path(tempfile.mkdtemp())
        c = component("web")
        app = {"apiVersion": "core.oam.dev/v1beta1", "kind": "Application", "metadata": {"name": "web"},
               "spec": {"components": [{"name": "web", "type": "component", "properties": {
                   k: c[k] for k in ("image", "signer", "signature", "attestations")}}]}}
        (root / "web.json").write_text(json.dumps(app))
        (root / "CHANGESET.json").write_text(json.dumps({"schema": "PK_ECP_CHANGESET/1", "commit": "a" * 40,
                                                         "tenant": "payments", "lattice": "prod-eu", "applications": ["web.json"]}))
        out = gitops.ingest(h.svc, h.tok("service:gitops"), root)
        self.assertTrue(out["all_admitted"], out)
        again = gitops.ingest(h.svc, h.tok("service:gitops"), root)
        self.assertTrue(again["results"][0]["replayed"])
        (root / "CHANGESET.json").write_text(json.dumps({"schema": "PK_ECP_CHANGESET/1", "commit": "b" * 40,
                                                         "tenant": "payments", "lattice": "prod-eu", "applications": ["../x.json"]}))
        with self.assertRaises(ControlPlaneError):
            gitops.ingest(h.svc, h.tok("service:gitops"), root)
        h.close()


class ResilienceTest(unittest.TestCase):
    def test_breaker_retry_deadline(self):
        t = [0.0]
        clock = lambda: t[0]
        br = CircuitBreaker("dep", failure_threshold=2, reset_after_s=10, clock=clock)
        calls = []

        def boom():
            calls.append(1)
            raise ConnectionError()
        with self.assertRaises(ControlPlaneError) as cm:
            call_with_policy(boom, br, RetryPolicy(3), Deadline(5, clock), "POLICY_UNAVAILABLE", sleep=lambda s: None,
                             rng=random.Random(1))
        self.assertEqual(br.state, "open")
        self.assertEqual(len(calls), 2)                           # breaker opened before the 3rd attempt
        t[0] = 11
        self.assertTrue(br.allow())
        self.assertEqual(br.state, "half-open")
        self.assertEqual(call_with_policy(lambda: 7, br, RetryPolicy(), Deadline(5, clock), "POLICY_UNAVAILABLE"), 7)
        self.assertEqual(br.state, "closed")
        d = Deadline(1, clock)
        t[0] = 20
        with self.assertRaises(ControlPlaneError) as cm:
            d.check()
        self.assertEqual(cm.exception.error.code, "DEADLINE_EXCEEDED")

    def test_non_retryable_is_not_retried(self):
        calls = []

        def deny():
            calls.append(1)
            raise fail("POLICY_DENIED", "no")
        br = CircuitBreaker("x")
        with self.assertRaises(ControlPlaneError):
            call_with_policy(deny, br, RetryPolicy(5), Deadline(5), "POLICY_UNAVAILABLE", sleep=lambda s: None)
        self.assertEqual(len(calls), 1)
        self.assertEqual(br.state, "closed")

    def test_bulkhead_and_bucket(self):
        b = Bulkhead(1)
        with b:
            with self.assertRaises(ControlPlaneError) as cm:
                with b:
                    pass
            self.assertEqual(cm.exception.error.code, "OVERLOADED")
        t = [0.0]
        tb = TokenBucket(clock=lambda: t[0])
        self.assertEqual(sum(tb.take("k", 5) for _ in range(10)), 5)
        t[0] = 12
        self.assertTrue(tb.take("k", 5))

    def test_overload_sheds_instead_of_queueing(self):
        h = Harness()
        h.svc.bulkhead = Bulkhead(1)
        gate = threading.Event()
        orig = h.svc.policy_engine.evaluate

        def slow(*a):
            gate.wait(5)
            return orig(*a)
        h.svc.policy_engine.evaluate = slow
        t = threading.Thread(target=lambda: h.svc.admit(h.tok(), request(rid="slow")))
        t.start()
        import time
        for _ in range(100):
            if h.svc.bulkhead.inflight:
                break
            time.sleep(0.01)
        with self.assertRaises(ControlPlaneError) as cm:
            h.svc.admit(h.tok(), request(rid="fast"))
        self.assertEqual(cm.exception.error.code, "OVERLOADED")
        gate.set(); t.join()
        h.close()


if __name__ == "__main__":
    unittest.main()
