"""P0-12 wire schemas, P0-13 transport — 'interface template' .01-.10; also P2-33
fixtures and P2-35 fuzzing entry points."""
from __future__ import annotations

import http.client
import json
import os
import random
import threading
import unittest
from pathlib import Path

from support import Stack, covers, workload_token
from gap11_control.common import REASON_CODES, ControlError
from gap11_control.service import encode_credential, serve_http
from gap11_control.wire import (HTTP_STATUS, MAX_MESSAGE_BYTES, RETRYABLE, SCHEMAS, decode, error_envelope, validate)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
T = lambda c, *n: tuple(f"GAP11-{c}.{i:02d}" for i in n)


class SchemaTests(unittest.TestCase):
    @covers(*T("P0-12", 1, 2), *T("P0-13", 1, 2))
    def test_every_schema_has_limits_and_every_code_is_registered(self):
        for name, s in SCHEMAS.items():
            self.assertIn("required", s, name)
            self.assertIn("additionalProperties", s, name)
        self.assertEqual(set(SCHEMAS["PK_ERROR/1"]["properties"]["code"]["enum"]), set(REASON_CODES))
        self.assertTrue(RETRYABLE <= set(REASON_CODES))
        self.assertTrue(set(HTTP_STATUS) <= set(REASON_CODES))
        env = error_envelope(ControlError("CAPACITY_EXHAUSTED", "x", tenant="t1", previous_tenant="t9", device="gpu0"), "req-1")
        self.assertEqual(validate(env, SCHEMAS["PK_ERROR/1"]), [])
        self.assertNotIn("tenant", env["details"]); self.assertNotIn("previous_tenant", env["details"])   # disclosure

    @covers(*T("P0-12", 3), *T("P0-13", 3))
    def test_compatibility_rules_closed_requests_open_responses(self):
        req = {"schema": "PK_ACCELERATOR_ALLOCATION_REQUEST/1", "request_id": "req-00000001", "tenant": "t", "workload": "w"}
        self.assertEqual(validate(req, SCHEMAS["PK_ACCELERATOR_ALLOCATION_REQUEST/1"]), [])
        self.assertTrue(validate({**req, "memroy_gb": 4}, SCHEMAS["PK_ACCELERATOR_ALLOCATION_REQUEST/1"]))   # typo refused
        resp = {"schema": "PK_ACCELERATOR_RELEASE/1", "lease_id": "a" * 32, "device": "g", "released": True, "future_field": 1}
        self.assertEqual(validate(resp, SCHEMAS["PK_ACCELERATOR_RELEASE/1"]), [])                           # additive ok
        self.assertTrue(validate({**req, "schema": "PK_ACCELERATOR_ALLOCATION_REQUEST/2"}, SCHEMAS["PK_ACCELERATOR_ALLOCATION_REQUEST/1"]))

    @covers(*T("P0-12", 4), *T("P0-13", 4))
    def test_limits_enforced_before_business_logic(self):
        big = b'{"a":"' + b"x" * MAX_MESSAGE_BYTES + b'"}'
        with self.assertRaises(ControlError) as cm:
            decode(big, "PK_SCRUB_REQUEST/1")
        self.assertEqual(cm.exception.code, "MESSAGE_TOO_LARGE")
        deep = b"[" * 50 + b"]" * 50
        with self.assertRaises(ControlError) as cm:
            decode(deep, "PK_SCRUB_REQUEST/1")
        self.assertEqual(cm.exception.code, "MESSAGE_TOO_LARGE")
        for bad in (b'{"schema":"PK_SCRUB_REQUEST/1","schema":"x"}', b"\xff\xfe", b"NaN", b'{"x": Infinity}'):
            with self.assertRaises(ControlError):
                decode(bad, "PK_SCRUB_REQUEST/1")
        with self.assertRaises(ControlError):
            decode(json.dumps({"schema": "PK_ACCELERATOR_ALLOCATION_REQUEST/1", "request_id": "req-00000001", "tenant": "t",
                               "workload": "w", "memory_gb": 10 ** 12}).encode(), "PK_ACCELERATOR_ALLOCATION_REQUEST/1")

    @covers(*T("P0-12", 9), *T("P0-13", 9), "GAP11-P2-33.01", "GAP11-P2-33.02", "GAP11-P2-33.09")
    def test_golden_fixtures_decode_and_reencode(self):
        files = sorted(FIXTURES.glob("*.json"))
        self.assertGreaterEqual(len(files), 8)
        for f in files:
            spec = json.loads(f.read_text())
            if spec["expect"] == "valid":
                obj = decode(json.dumps(spec["message"]).encode(), spec["schema"])
                self.assertEqual(json.loads(json.dumps(obj, sort_keys=True)), spec["message"], f.name)
            else:
                with self.assertRaises(ControlError, msg=f.name) as cm:
                    decode(json.dumps(spec["message"]).encode(), spec["schema"])
                self.assertEqual(cm.exception.code, spec["expect"], f.name)

    @covers(*T("P0-12", 10), *T("P0-13", 10), "GAP11-P2-35.03", "GAP11-P2-35.08")
    def test_decoder_fuzz_never_raises_untyped(self):
        rng = random.Random(1103)                                                     # recorded seed
        corpus = [f.read_bytes() for f in sorted(FIXTURES.glob("*.json"))]
        seeds = [json.dumps(json.loads(c)["message"]).encode() for c in corpus]
        n = 0
        for _ in range(3000):
            s = bytearray(rng.choice(seeds))
            for _ in range(rng.randint(1, 6)):
                op = rng.randint(0, 4)
                i = rng.randrange(len(s) or 1)
                if op == 0 and s: s[i] = rng.randrange(256)
                elif op == 1: s[i:i] = bytes([rng.randrange(256)])
                elif op == 2 and s: del s[i]
                elif op == 3: s = s[: rng.randrange(len(s) + 1)]                      # truncation
                else: s = s + s[: rng.randrange(len(s) + 1)]                          # duplication
            for schema in ("PK_ACCELERATOR_ALLOCATION_REQUEST/1", "PK_SCRUB_REQUEST/1"):
                try:
                    decode(bytes(s), schema)
                except ControlError as exc:
                    self.assertIn(exc.code, REASON_CODES)
                n += 1
        self.assertEqual(n, 6000)


class TransportTests(unittest.TestCase):
    def body(self, rid, **kw):
        return json.dumps({"schema": "PK_ACCELERATOR_ALLOCATION_REQUEST/1", "request_id": rid, "tenant": "t1", "workload": "w", **kw}).encode()

    @covers(*T("P0-13", 6), *T("P0-12", 6))
    def test_bounded_inflight_returns_overloaded_not_queueing_forever(self):
        st = Stack()
        svc, authn = st.service(max_inflight=1)
        gate = threading.Event(); entered = threading.Event()
        orig = svc.ctl.allocate
        def slow(*a, **k):
            entered.set(); gate.wait(5); return orig(*a, **k)
        svc.ctl.allocate = slow
        out = {}
        t = threading.Thread(target=lambda: out.setdefault("a", svc.handle("/v1/allocate", self.body("req-ovl-0001"), workload_token(authn))))
        t.start(); entered.wait(5)
        s, r = svc.handle("/v1/allocate", self.body("req-ovl-0002"), workload_token(authn))
        self.assertEqual((s, r["code"], r["retryable"]), (503, "OVERLOADED", True))
        gate.set(); t.join(5)
        self.assertEqual(out["a"][0], 200)

    @covers(*T("P0-13", 7), *T("P0-12", 7))
    def test_deadline_exceeded_before_state_change(self):
        st = Stack()
        svc, authn = st.service()
        orig = svc.authn.authenticate
        def slow_auth(tok):
            st.clock.advance(2.0); return orig(tok)
        svc.authn.authenticate = slow_auth
        st.elector.ttl = 1000; st.elector.renew()
        s, r = svc.handle("/v1/allocate", self.body("req-dl-00001", deadline_ms=500), workload_token(authn))
        self.assertEqual(r["code"], "DEADLINE_EXCEEDED")
        self.assertEqual(len(st.ctl.leases()), 0)

    @covers(*T("P0-13", 5), *T("P0-12", 5), "GAP11-P1-26.02", "GAP11-P1-26.06")
    def test_trace_and_request_id_propagate_end_to_end(self):
        st = Stack()
        svc, authn = st.service()
        tp = "00-" + "ab" * 16 + "-" + "cd" * 8 + "-01"
        s, r = svc.handle("/v1/allocate", self.body("req-tr-00001"), workload_token(authn), traceparent=tp)
        self.assertTrue(r["traceparent"].startswith("00-" + "ab" * 16))
        ev = st.tel.find(event="allocate")[-1]
        self.assertEqual(ev["request_id"], "t1:req-tr-00001")
        self.assertEqual(st.tel.find(event="allocate", request_id="t1:req-tr-00001")[0]["lease_id"], r["lease_id"])
        self.assertTrue(st.tel.find(component="service", trace_id="ab" * 16))

    @covers(*T("P0-13", 8), *T("P0-12", 8))
    def test_http_binding_end_to_end_with_retry_idempotency(self):
        st = Stack()
        svc, authn = st.service()
        srv = serve_http(svc)
        try:
            port = srv.server_address[1]
            def post(path, body, tok):
                c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                c.request("POST", path, body, {"Authorization": encode_credential(tok), "Content-Type": "application/json"})
                r = c.getresponse(); data = json.loads(r.read()); c.close()
                return r.status, data
            s1, r1 = post("/v1/allocate", self.body("req-http-001"), workload_token(authn))
            s2, r2 = post("/v1/allocate", self.body("req-http-001"), workload_token(authn))     # client retry
            self.assertEqual((s1, s2), (200, 200))
            self.assertEqual(r1["lease_id"], r2["lease_id"])
            s3, r3 = post("/v1/allocate", self.body("req-http-002"), {"kid": "nope", "claims": {}, "mac": ""})
            self.assertEqual((s3, r3["code"]), (401, "UNAUTHENTICATED"))
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            c.request("GET", "/metrics"); m = c.getresponse().read().decode(); c.close()
            self.assertIn('gap11_requests_total{code="OK",operation="allocate"}', m)
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            c.putrequest("POST", "/v1/allocate"); c.putheader("Content-Length", str(MAX_MESSAGE_BYTES + 1)); c.endheaders()
            self.assertEqual(c.getresponse().status, 413); c.close()
        finally:
            srv.shutdown(); srv.server_close()
        with self.assertRaises(ControlError):
            serve_http(svc, host="0.0.0.0")


if __name__ == "__main__":
    unittest.main()
