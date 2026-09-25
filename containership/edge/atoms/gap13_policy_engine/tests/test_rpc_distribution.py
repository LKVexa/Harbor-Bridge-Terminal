"""G13-MC-015 RPC transport and G13-MC-011 distribution controller."""
import base64
import json
import os
import random
import unittest
import urllib.request

import testkit as k
from gap13_policy_engine import errors as E
from gap13_policy_engine.authz import TokenAuthenticator, issue_token
from gap13_policy_engine.distribution import DistributionController, HttpsFetcher
from gap13_policy_engine.rpc import serve

KEY = b"r" * 32


class RpcTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import time
        cls.svc, cls.c = k.service(require_separation_of_duties=False)
        cls.auth = TokenAuthenticator({"i": KEY}, issuer="idp", audience="gap13")
        cls.srv, cls.th = serve(cls.svc, cls.auth, port=0)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def tok(self, sub, roles, kind="human"):
        import time
        now = int(time.time())
        return issue_token(KEY, {"kid": "i", "iss": "idp", "aud": "gap13", "sub": sub, "iat": now, "exp": now + 60,
                                 "jti": os.urandom(8).hex(), "roles": roles, "env": ["prod"], "kind": kind,
                                 "mfa": True, "auth_time": int(self.c.wall())})

    def call(self, method, path, body=None, token=None, headers=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=headers or {})
        if token:
            req.add_header("Authorization", "Bearer " + token)
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.read().decode(), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode(), dict(e.headers)

    def test_flow(self):
        self.assertEqual(self.call("GET", "/v1/health")[0], 200)
        self.assertEqual(self.call("GET", "/v1/ready", token=self.tok("svc-a", ["service"], "service"))[0], 503)
        st, body, _ = self.call("POST", "/v1/evaluate", {"attributes": {"action": "read"}})
        self.assertEqual((st, json.loads(body)["code"]), (401, "G13-E401"))
        env = base64.b64encode(self.svc_env()).decode()
        st, body, _ = self.call("POST", "/v1/bundles/load", {"envelope_b64": env},
                                token=self.tok("svc-a", ["service"], "service"))
        self.assertEqual(st, 403)
        st, body, _ = self.call("POST", "/v1/bundles/load", {"envelope_b64": env}, token=self.tok("alice", ["policy_admin"]))
        self.assertEqual(st, 200, body)
        tp = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
        st, body, hdr = self.call("POST", "/v1/evaluate", {"attributes": {"action": "read"}},
                                  token=self.tok("svc-a", ["service"], "service"), headers={"traceparent": tp})
        v = json.loads(body)
        self.assertEqual((st, v["effect"], v["trace_id"]), (200, "allow", "a" * 32))
        st, body, _ = self.call("POST", "/v1/evaluate", {"attributes": {"tenant": "t9"}},
                                token=self.tok("svc-a", ["service"], "service"))
        self.assertEqual((st, json.loads(body)["code"]), (400, "G13-E201"))
        self.assertEqual(self.call("GET", "/metrics", token=self.tok("svc-a", ["service"], "service"))[0], 200)
        self.assertEqual(self.call("GET", "/v1/status", token=self.tok("svc-a", ["service"], "service"))[0], 200)
        self.assertEqual(self.call("GET", "/v1/nope", token=self.tok("svc-a", ["service"], "service"))[0], 404)
        # replayed token
        t = self.tok("svc-a", ["service"], "service")
        self.call("GET", "/v1/ready", token=t)
        self.assertEqual(self.call("GET", "/v1/ready", token=t)[0], 401)
        # backpressure
        self.svc._inflight = self.svc.config.limits.max_concurrency
        st, _, hdr = self.call("POST", "/v1/evaluate", {"attributes": {"action": "read"}},
                               token=self.tok("svc-a", ["service"], "service"))
        self.svc._inflight = 0
        self.assertEqual((st, hdr.get("Retry-After")), (503, "1"))
        # oversized body
        # oversized body is refused before it is read (client may see 400 or a closed socket)
        try:
            st, _, _ = self.call("POST", "/v1/evaluate", {"attributes": {"action": "x" * 3_000_000}},
                                 token=self.tok("svc-a", ["service"], "service"))
            self.assertEqual(st, 400)
        except urllib.error.URLError:
            pass
        self.assertEqual(self.call("GET", "/v1/health")[0], 200)     # server still healthy

    def svc_env(self):
        return k.envelope(1)


class DistributionTests(unittest.TestCase):
    def test_backoff_full_jitter_capped(self):
        dc = DistributionController(None, None, None, backoff_base_s=1, backoff_max_s=60, rng=random.Random(1))
        self.assertEqual(dc.next_delay(), 30.0)
        dc.failures = 10
        delays = [dc.next_delay() for _ in range(200)]
        self.assertTrue(all(0 <= d <= 60 for d in delays))
        self.assertGreater(len(set(round(d, 3) for d in delays)), 100)

    def test_https_only(self):
        with self.assertRaises(ValueError):
            HttpsFetcher("http://example.invalid/bundle", lambda: "t")

    def test_rejected_bundle_not_retried_until_new(self):
        svc, c = k.service(require_separation_of_duties=False)
        admin = k.principal("alice", clock=c)

        class F:
            data = k.envelope(1, seed=k.ROGUE)

            def fetch(self, *, timeout):
                return self.data
        f = F()
        dc = DistributionController(svc, f, admin)
        self.assertEqual(dc.poll_once(), "rejected")
        self.assertEqual(dc.poll_once(), "unchanged")
        f.data = k.envelope(1)
        self.assertEqual(dc.poll_once(), "applied")

    def test_cancellation(self):
        import threading
        svc, c = k.service(require_separation_of_duties=False)

        class F:
            def fetch(self, *, timeout):
                return None
        dc = DistributionController(svc, F(), None, interval_s=10)
        stop = threading.Event()
        t = threading.Thread(target=dc.run, args=(stop,))
        t.start()
        stop.set()
        t.join(2)
        self.assertFalse(t.is_alive())

    def test_stage_mode_respects_sod(self):
        svc, c = k.service()
        alice, bob = k.principal("alice", clock=c), k.principal("bob", clock=c)

        class F:
            def fetch(self, *, timeout):
                return k.envelope(1)
        dc = DistributionController(svc, F(), alice, mode="stage")
        self.assertEqual(dc.poll_once(), "applied")
        with self.assertRaises(E.NoActivePolicy):
            svc.evaluate(k.principal("svc-a", ("service",), kind="service"), {"action": "read"})
        svc.activate(bob, next(iter(svc._staged)))


if __name__ == "__main__":
    unittest.main()
