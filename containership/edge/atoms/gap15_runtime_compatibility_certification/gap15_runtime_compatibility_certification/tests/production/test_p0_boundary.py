"""P0 boundaries: schemas (09), ingestion (10), revocation/quarantine (13), service host (14), fuzzing (35)."""
import http.client
import json
import os
import random
import tempfile
import threading
import time
import unittest

from fixtures import ENV, PART, PART2, T0, World, art
from gap15_runtime_compatibility_certification.production import canonical, schemas
from gap15_runtime_compatibility_certification.production.canonical import CanonicalError, canonical_bytes, parse
from gap15_runtime_compatibility_certification.production.http_api import ApiServer
from gap15_runtime_compatibility_certification.production.service import ServiceError
from gap15_runtime_compatibility_certification.production.state import CertKey


class SchemaTest(unittest.TestCase):
    def test_published_schemas_match_runtime_validator(self):
        """controls: 09-01 09-02 09-06"""
        d = tempfile.mkdtemp()
        paths = schemas.publish(d)
        self.assertEqual(len(paths), 4)
        for p in paths:
            doc = json.load(open(p))
            self.assertEqual(doc["x-gap15-schema-set"], schemas.SCHEMA_SET_VERSION)
            sid = doc["title"]
            body = {k: v for k, v in doc.items() if k not in ("$schema", "title", "x-gap15-schema-set")}
            self.assertEqual(json.loads(json.dumps(schemas.SCHEMAS[sid])), body)

    def test_semantic_cross_field_invariants(self):
        """controls: 09-03"""
        v = {"schema": "PK_CERTIFICATION/1", "verdict": "untested", "reason_code": "R_NO_EVIDENCE", "reason": "x",
             "deployable": True, "key": {"partition": PART, "artifact_digest": art(1), "runtime": "r", "profile_id": "p"},
             "matrix_revision": 0, "ledger_seq": 0, "policy_revision": "p", "evaluated_at": 1}
        with self.assertRaises(schemas.SchemaError) as cm:
            schemas.validate("PK_CERTIFICATION/1", v)
        self.assertEqual(cm.exception.code, "E_SCHEMA_SEMANTIC")

    def test_unknown_duplicate_null_unicode_numbers(self):
        """controls: 09-04 09-07 35-03"""
        for raw, code in ((b'{"a":1,"a":2}', "E_DUPLICATE_KEY"), (b'{"a":1.5}', "E_FLOAT"), (b'{"a":NaN}', "E_NON_FINITE"),
                          (b'{"a":"e\\u0301"}', "E_UNICODE_NFC"), (b'\xff', "E_ENCODING"), (b"[" * 40 + b"]" * 40, "E_DEPTH"),
                          (b'{"a":' + str(2**64).encode() + b'}', "E_INT_RANGE"), (b'{"a":"\\ud800"}', "E_UNICODE_SURROGATE")):
            with self.assertRaises(CanonicalError) as cm:
                parse(raw)
            self.assertEqual(cm.exception.code, code, raw[:20])
        with self.assertRaises(CanonicalError) as cm:
            parse(b'{"b":1, "a":2}', require_canonical=True)
        self.assertEqual(cm.exception.code, "E_NON_CANONICAL")
        with self.assertRaises(schemas.SchemaError) as cm:
            schemas.validate("PK_COMPATIBILITY_MATRIX/1", {"schema": "PK_COMPATIBILITY_MATRIX/1", "partition": PART,
                                                           "revision": 0, "results": [], "surprise": 1})
        self.assertEqual(cm.exception.code, "E_SCHEMA_UNKNOWN_FIELD")
        with self.assertRaises(schemas.SchemaError):
            schemas.validate("PK_RUNTIME_LIFECYCLE/1", {"schema": "PK_RUNTIME_LIFECYCLE/1", "partition": PART, "revision": None, "runtimes": []})

    def test_versioning_and_breaking_change_diff(self):
        """controls: 09-05 09-10 33-06"""
        old = schemas.SCHEMAS["PK_COMPATIBILITY_MATRIX/1"]
        self.assertEqual(schemas.diff(old, old), [])
        new = json.loads(json.dumps(old))
        new["required"].append("site")
        del new["properties"]["revision"]
        br = schemas.diff(old, new)
        self.assertTrue(any("new required" in b for b in br) and any("removed" in b for b in br))
        with self.assertRaises(schemas.SchemaError) as cm:
            schemas.validate("PK_CERTIFICATION/2", {})
        self.assertEqual(cm.exception.code, "E_SCHEMA_UNSUPPORTED")

    def test_conformance_fixtures_valid_and_invalid(self):
        """controls: 09-08"""
        w = World()
        env = parse(w.evidence())
        schemas.validate("GAP15_EVIDENCE/1", env)
        bad = dict(env, result="maybe")
        with self.assertRaises(schemas.SchemaError):
            schemas.validate("GAP15_EVIDENCE/1", bad)
        inc = dict(env, result="incompatible")
        with self.assertRaises(schemas.SchemaError):
            schemas.validate("GAP15_EVIDENCE/1", inc)  # incompatible without failure_class


class FuzzTest(unittest.TestCase):
    SEED = 20260922

    def test_mutation_fuzz_parser_and_validator_fail_closed(self):
        """controls: 09-09 35-01 35-02 35-04 35-05 35-10"""
        rnd = random.Random(self.SEED)
        w = World()
        seed_docs = [w.evidence(), canonical_bytes({"schema": "PK_COMPATIBILITY_MATRIX/1"}), b"{}", b"[]", b'"x"']
        crashes = []
        t0 = time.perf_counter()
        for i in range(3000):
            data = bytearray(rnd.choice(seed_docs))
            for _ in range(rnd.randint(1, 8)):
                op = rnd.random()
                pos = rnd.randrange(len(data)) if data else 0
                if op < 0.4 and data:
                    data[pos] = rnd.randrange(256)
                elif op < 0.7:
                    data[pos:pos] = rnd.choice([b"{", b"[", b'"', b"\\u0000", b"1e999", b",", b"\xc3", b"-0", b"null"])
                elif data:
                    del data[pos:pos + rnd.randint(1, 16)]
            try:
                v = parse(bytes(data))
                if isinstance(v, dict):
                    schemas.validate("GAP15_EVIDENCE/1", v)
            except (CanonicalError, schemas.SchemaError):
                pass
            except Exception as exc:  # any other exception is a fail-open/crash finding
                crashes.append((i, type(exc).__name__, bytes(data[:60])))
        self.assertEqual(crashes, [], f"seed={self.SEED}")
        self.assertLess(time.perf_counter() - t0, 60)

    def test_canonical_differential_two_encodings_one_digest(self):
        """controls: 35-06 35-07"""
        a = parse(b'{"b":[1,2],"a":"x"}')
        b = parse(b'{ "a" : "x" , "b" : [ 1 , 2 ] }')
        self.assertEqual(canonical.digest(a), canonical.digest(b))
        self.assertNotEqual(canonical.digest(a), canonical.digest(parse(b'{"a":"x","b":[2,1]}')))

    def test_pathological_sizes_bounded(self):
        """controls: 32-06 35-05 36-06"""
        with self.assertRaises(CanonicalError) as cm:
            parse(b"[" + b"1," * 200000 + b"1]")
        self.assertIn(cm.exception.code, ("E_PAYLOAD_TOO_LARGE", "E_COLLECTION_SIZE"))
        with self.assertRaises(CanonicalError):
            parse(b'"' + b"a" * 9000 + b'"')


class IngestTest(unittest.TestCase):
    def setUp(self):
        self.w = World()

    def test_happy_path_commits_everything_atomically(self):
        """controls: 02-01 10-01 10-03 10-05 33-05"""
        r = self.w.svc.ingest(self.w.producer(), self.w.evidence())
        self.assertEqual(r["status"], "accepted")
        e = self.w.store.events()[-1]
        for f in ("provenance", "attestation", "signer_key_id", "trust_store_revision", "test_suite", "payload_digest"):
            self.assertIn(f, e)
        self.assertEqual(self.w.store.revision, 1)
        self.assertEqual(self.w.store.head("audit")[0], 1)

    def test_exact_retry_idempotent_conflicting_resubmission_quarantines(self):
        """controls: 10-04 02-05 31-01 31-02 37-02"""
        raw = self.w.evidence(event_id="pe-fixed")
        self.w.svc.ingest(self.w.producer(), raw)
        again = self.w.svc.ingest(self.w.producer(), raw)
        self.assertEqual(again["status"], "duplicate")
        self.assertEqual(self.w.store.revision, 1)
        clash = self.w.evidence(event_id="pe-fixed", result="incompatible")
        r = self.w.svc.ingest(self.w.producer(), clash)
        self.assertEqual(r["status"], "conflict")
        k = self.w.key_for({"profile_id": self.w.store.events()[0]["profile_id"]})
        d = self.w.svc.certify(self.w.reader(), k)
        self.assertEqual((d["verdict"], d["reason_code"]), ("quarantined", "R_CONFLICT"))

    def test_rejections_have_stable_categories(self):
        """controls: 10-02 10-07 14-05"""
        w = self.w
        cases = [
            (lambda: w.svc.ingest("garbage", w.evidence()), "authn"),
            (lambda: w.svc.ingest(w.reader(), w.evidence()), "authz"),
            (lambda: w.svc.ingest(w.producer(), b'{"schema":"GAP15_EVIDENCE/1"}'), "validation"),
            (lambda: w.svc.ingest(w.producer("producer-b"), w.evidence()), "authz"),  # producer mismatch
            (lambda: w.svc.ingest(w.producer(), w.evidence(key_id="producer-b-key")), "validation"),
            (lambda: w.svc.ingest(w.producer(), w.evidence(nonce="ab" * 16)), "validation"),  # nonce not issued
            (lambda: w.svc.ingest(w.producer(), w.evidence(observed_at=T0 + 3600)), "validation"),
            (lambda: w.svc.ingest(w.producer(), w.evidence(runtime=("wasmtime", "21.0.0"), mutate=lambda e: e.update(runtime="wasmtime@22.0.0"))), "validation"),
        ]
        for fn, cat in cases:
            with self.assertRaises(ServiceError) as cm:
                fn()
            self.assertEqual(cm.exception.category, cat, cm.exception.code)
        self.assertEqual(w.store.revision, 0)

    def test_batch_all_or_nothing_with_per_item_status(self):
        """controls: 10-09"""
        w = self.w
        good = [w.evidence(digest=art(i)) for i in range(3)]
        with self.assertRaises(ServiceError):
            w.svc.ingest_batch(w.producer(), good[:2] + [b"{bad"])
        self.assertEqual(w.store.revision, 0)
        r = w.svc.ingest_batch(w.producer(), [w.evidence(digest=art(i)) for i in range(3)])
        self.assertEqual([i["status"] for i in r["items"]], ["accepted"] * 3)
        self.assertEqual(w.store.revision, 3)

    def test_rejection_forensics_without_raw_payload(self):
        """controls: 10-08 12-06"""
        w = self.w
        with self.assertRaises(ServiceError):
            w.svc.ingest(w.producer(), b'{"schema":"GAP15_EVIDENCE/1","secret":"hunter2"}')
        rej = [a for a in w.store.audit_events() if a["action"] == "evidence.rejected"][-1]
        self.assertIn("payload_sha256", rej["detail"])
        self.assertNotIn("hunter2", canonical_bytes(rej).decode())

    def test_backpressure_rate_limit_and_overload(self):
        """controls: 10-06 32-02 32-03 36-06"""
        from gap15_runtime_compatibility_certification.production.capacity import RateLimiter
        w = self.w
        w.svc.limiter = RateLimiter(per_key_rate=0.001, per_key_burst=2, global_rate=1000, global_burst=1000, clock=lambda: 0.0)
        w.svc.ingest(w.producer(), w.evidence(digest=art(1)))
        w.svc.ingest(w.producer(), w.evidence(digest=art(2)))
        with self.assertRaises(ServiceError) as cm:
            w.svc.ingest(w.producer(), w.evidence(digest=art(3)))
        self.assertEqual(cm.exception.category, "rate-limit")
        self.assertGreater(cm.exception.retry_after, 0)

    def test_dependency_outage_and_retry_after_crash(self):
        """controls: 10-10 38-05"""
        crashes = {"n": 0}

        def hook(stage):
            if stage == "before_commit" and crashes["n"] == 0:
                crashes["n"] += 1
                raise OSError("transient disk")
        w = World(fault_hook=hook)
        raw = w.evidence(event_id="pe-retry")
        with self.assertRaises(OSError):
            w.svc.ingest(w.producer(), raw)
        self.assertEqual(w.store.revision, 0)
        nonce_raw = w.evidence(event_id="pe-retry")  # producer retries with a fresh attestation nonce
        self.assertEqual(w.svc.ingest(w.producer(), nonce_raw)["status"], "accepted")


class RevocationTest(unittest.TestCase):
    def setUp(self):
        self.w = World()
        r = self.w.svc.ingest(self.w.producer(), self.w.evidence())
        self.k = self.w.key_for(r)

    def test_revocation_overrides_valid_evidence_and_history_kept(self):
        """controls: 13-01 13-02 13-04 13-06"""
        w = self.w
        self.assertEqual(w.svc.certify(w.reader(), self.k)["verdict"], "certified")
        w.svc.revoke(w.operator(), subject_type="runtime", subject_id="wasmtime@21.0.0", partition=PART, reason="CVE-1", severity="critical")
        self.assertEqual(w.svc.certify(w.reader(), self.k)["verdict"], "revoked")
        with self.assertRaises(ServiceError) as cm:
            w.svc.reinstate(w.operator(), w.operator(), subject_type="runtime", subject_id="wasmtime@21.0.0", partition=PART, reason="x")
        self.assertEqual(cm.exception.category, "authz")
        w.svc.reinstate(w.operator("alice"), w.operator("bob"), subject_type="runtime", subject_id="wasmtime@21.0.0",
                        partition=PART, reason="patched")
        self.assertEqual(w.svc.certify(w.reader(), self.k)["verdict"], "certified")
        types = [e["event_type"] for e in w.store.events()]
        self.assertEqual(types, ["evidence", "revoke", "reinstate"])

    def test_quarantine_distinct_and_expiring(self):
        """controls: 13-05"""
        w = self.w
        w.svc.revoke(w.operator(), subject_type="producer", subject_id="producer-a", partition=PART, reason="investigating",
                     severity="medium", quarantine=True, expires_at=T0 + 100)
        self.assertEqual(w.svc.certify(w.reader(), self.k)["verdict"], "quarantined")
        w.advance(101)
        self.assertEqual(w.svc.certify(w.reader(), self.k)["verdict"], "certified")

    def test_signer_compromise_enumerates_affected_evidence(self):
        """controls: 13-07 36-03"""
        w = self.w
        out = w.svc.revoke(w.operator(), subject_type="signer", subject_id="producer-a-key", partition=PART,
                           reason="key leak", severity="critical")
        self.assertEqual(len(out["affected_evidence"]), 1)
        self.assertEqual(w.svc.certify(w.reader(), self.k)["verdict"], "revoked")
        with self.assertRaises(ServiceError):
            w.svc.ingest(w.producer(), w.evidence(digest=art(5)))  # compromised key rejected at ingest

    def test_bulk_revocation_requires_preview_and_guard(self):
        """controls: 13-08"""
        w = self.w
        for i in range(2, 6):
            w.svc.ingest(w.producer(), w.evidence(digest=art(i)))
        prev = w.svc.bulk_revoke_preview({"runtime": "wasmtime@21.0.0"})
        self.assertFalse(prev["allowed"])  # would hit 100% of the fleet
        with self.assertRaises(ServiceError):
            w.svc.bulk_revoke(w.operator(), {"runtime": "wasmtime@21.0.0"}, prev["preview_digest"], partition=PART, reason="x")
        one = w.svc.bulk_revoke_preview({"artifact_digest": art(3)})
        self.assertTrue(one["allowed"])
        self.assertEqual(w.svc.bulk_revoke(w.operator(), {"artifact_digest": art(3)}, one["preview_digest"], partition=PART, reason="x")["revoked"], 1)
        with self.assertRaises(ServiceError):
            w.svc.bulk_revoke(w.operator(), {"artifact_digest": art(3)}, "sha256:stale", partition=PART, reason="x")

    def test_revocation_audit_and_restore_preserves_it(self):
        """controls: 13-09 13-10 46-07"""
        w = self.w
        w.svc.revoke(w.operator(), subject_type="artifact", subject_id=art(1), partition=PART, reason="cve", severity="high")
        from gap15_runtime_compatibility_certification.production.store import Store
        s2 = Store(w.db_path)  # a restarted/rolled-back binary replays the same ledger
        self.assertEqual(s2.certify(self.k, T0)["verdict"], "revoked")
        self.assertTrue(any(a["action"] == "revoke" for a in w.store.audit_events()))


class ApiHostTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = World()
        cls.srv = ApiServer(cls.w.svc, metrics_token="m" * 32).start()
        cls.host, cls.port = cls.srv.address

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def req(self, method, path, body=None, token=None, headers=None):
        c = http.client.HTTPConnection(self.host, self.port, timeout=10)
        h = {"Content-Type": "application/json"}
        if token:
            h["Authorization"] = f"Bearer {token}"
        h.update(headers or {})
        data = body if isinstance(body, bytes) else (json.dumps(body).encode() if body is not None else None)
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        out = r.status, r.read(), dict(r.getheaders())
        c.close()
        return out

    def test_contract_routes_and_error_codes(self):
        """controls: 14-01 14-05 14-08"""
        w = self.w
        st, body, _ = self.req("POST", "/v1/evidence", w.evidence(), w.producer())
        self.assertEqual(st, 200, body)
        pid = json.loads(body)["profile_id"]
        st, body, _ = self.req("POST", "/v1/certify", {"key": CertKey(PART, art(1), "wasmtime@21.0.0", pid).as_dict()}, w.reader())
        self.assertEqual((st, json.loads(body)["verdict"]), (200, "certified"))
        dec = json.loads(body)["decision_id"]
        st, body, _ = self.req("GET", f"/v1/explain/{dec}", token=w.reader())
        self.assertEqual(json.loads(body)["replay_consistent"], True)
        st, body, _ = self.req("GET", f"/v1/matrix?partition={PART}", token=w.reader())
        self.assertEqual(json.loads(body)["schema"], "PK_COMPATIBILITY_MATRIX/1")
        st, body, _ = self.req("GET", "/v2/matrix")
        self.assertEqual((st, json.loads(body)["error"]["code"]), (400, "E_API_VERSION_UNSUPPORTED"))
        st, body, _ = self.req("POST", "/v1/certify", {"key": {}}, "bad")
        self.assertEqual((st, json.loads(body)["error"]["category"]), (401, "authn"))

    def test_body_limits_content_type_and_encoding(self):
        """controls: 14-02 14-06 10-10 32-06"""
        w = self.w
        st, body, _ = self.req("POST", "/v1/evidence", b"x" * (1024 * 1024 + 10), w.producer())
        self.assertEqual(json.loads(body)["error"]["code"], "E_PAYLOAD_TOO_LARGE")
        st, body, _ = self.req("POST", "/v1/evidence", b"{}", w.producer(), headers={"Content-Type": "text/plain"})
        self.assertEqual(json.loads(body)["error"]["code"], "E_CONTENT_TYPE")
        st, body, _ = self.req("POST", "/v1/evidence", b"{}", w.producer(), headers={"Content-Encoding": "gzip"})
        self.assertEqual(json.loads(body)["error"]["code"], "E_CONTENT_ENCODING_UNSUPPORTED")

    def test_health_ready_metrics_protected(self):
        """controls: 14-03 14-09 26-07"""
        st, body, _ = self.req("GET", "/healthz")
        self.assertEqual(st, 200)
        st, body, _ = self.req("GET", "/readyz")
        self.assertEqual((st, json.loads(body)["ready"]), (200, True))
        st, body, _ = self.req("GET", "/metrics")
        self.assertEqual(st, 401)
        st, body, _ = self.req("GET", "/metrics", headers={"Authorization": "Bearer " + "m" * 32})
        self.assertEqual(st, 200)
        self.assertIn(b"gap15_certifications_total", body)
        self.assertNotIn(b"sha256:", body)
        st, body, _ = self.req("GET", "/version")
        self.assertIn(b"truststore", body)

    def test_graceful_shutdown_drains_and_readiness_flips(self):
        """controls: 14-04 38-09"""
        w = World()
        srv = ApiServer(w.svc).start()
        w.svc.begin_shutdown()
        self.assertFalse(w.svc.readiness()["ready"])
        with self.assertRaises(ServiceError) as cm:
            w.svc.ingest(w.producer(), w.evidence())
        self.assertEqual(cm.exception.code, "E_SHUTTING_DOWN")
        self.assertTrue(srv.shutdown(2.0)["clean"])

    def test_tls_context_policy(self):
        """controls: 14-07"""
        import ssl
        from gap15_runtime_compatibility_certification.production.http_api import tls_context
        with self.assertRaises((FileNotFoundError, ssl.SSLError, OSError)):
            tls_context("/nonexistent.pem", "/nonexistent.key")  # no silent plaintext fallback


if __name__ == "__main__":
    unittest.main()
