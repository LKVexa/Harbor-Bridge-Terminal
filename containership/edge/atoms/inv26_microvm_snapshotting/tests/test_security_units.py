"""Unit tests for auth, crypto envelope, schema, errors, lifecycle and config
(C015, C016, C022-C024, C026, C028, C029, C033-C039, C044, C047, X006, X009)."""
import base64
import copy
import json
import time
import unittest

from inv26_microvm_snapshotting import config as cfgmod
from inv26_microvm_snapshotting import crypto, lifecycle, schema
from inv26_microvm_snapshotting.auth import (Authenticator, Principal, Signer, TrustedKey, TrustStore, authorize)
from inv26_microvm_snapshotting.errors import CATALOG, SnapshotServiceError
from inv26_microvm_snapshotting.metastore import MetaStore


def _code(fn):
    try:
        fn()
    except SnapshotServiceError as e:
        return e.code
    return None


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.now = 1_800_000_000.0
        self.trust = TrustStore()
        self.s, pub = Signer.ed25519("k1")
        self.trust.add(TrustedKey("k1", "EdDSA", pub, "caller", "prod/site-a"))
        self.a = Authenticator(self.trust, audience="aud", environment="prod", site="site-a", clock=lambda: self.now)

    def tok(self, **over):
        c = {"sub": "x", "aud": "aud", "env": "prod", "site": "site-a", "iat": self.now, "exp": self.now + 60,
             "caps": []}
        c.update(over)
        return self.s.sign(c)

    def test_valid(self):
        self.assertEqual(self.a.authenticate(self.tok()).subject, "x")

    def test_rejections(self):
        cases = {
            "expired": self.tok(iat=self.now - 500, exp=self.now - 100),
            "not yet valid": self.tok(nbf=self.now + 100, exp=self.now + 200),
            "wrong audience": self.tok(aud="other"),
            "wrong env": self.tok(env="dev"),
            "wrong site": self.tok(site="site-b"),
            "lifetime": self.tok(exp=self.now + 7200),
            "malformed": "a.b",
            "garbage": "!!.!!.!!",
        }
        for name, t in cases.items():
            with self.subTest(name):
                self.assertEqual(_code(lambda: self.a.authenticate(t)), "SNAP_UNAUTHENTICATED")

    def test_tampered_signature_and_alg_confusion(self):
        t = self.tok()
        h, c, s = t.split(".")
        claims = json.loads(base64.urlsafe_b64decode(c + "=="))
        claims["caps"] = [{"cap": "snapshot.admin", "tenant": "*", "workload": "*", "environment": "*"}]
        c2 = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
        self.assertEqual(_code(lambda: self.a.authenticate(f"{h}.{c2}.{s}")), "SNAP_UNAUTHENTICATED")
        for alg in ("none", "HS256", "RS256"):
            hdr = base64.urlsafe_b64encode(json.dumps({"alg": alg, "kid": "k1"}).encode()).rstrip(b"=").decode()
            self.assertEqual(_code(lambda: self.a.authenticate(f"{hdr}.{c}.{s}")), "SNAP_UNAUTHENTICATED")

    def test_hs256_only_in_reference_profile(self):
        self.trust.add(TrustedKey("h1", "HS256", b"s" * 32, "caller", "prod/site-a"))
        t = Signer("h1", "HS256", b"s" * 32).sign({"sub": "x", "aud": "aud", "env": "prod", "site": "site-a",
                                                  "iat": self.now, "exp": self.now + 60, "caps": []})
        self.assertEqual(_code(lambda: self.a.authenticate(t)), "SNAP_UNAUTHENTICATED")
        ref = Authenticator(self.trust, audience="aud", environment="prod", site="site-a", profile="reference",
                            clock=lambda: self.now)
        self.assertEqual(ref.authenticate(t).subject, "x")

    def test_revocation_and_trust_domain_and_role(self):
        t = self.tok()
        self.trust.revoke("k1")
        self.assertEqual(_code(lambda: self.a.authenticate(t)), "SNAP_UNAUTHENTICATED")
        with self.assertRaises(ValueError):
            self.trust.add(TrustedKey("k1", "EdDSA", b"x" * 32, "caller", "prod/site-a"))
        s2, pub2 = Signer.ed25519("k2")
        self.trust.add(TrustedKey("k2", "EdDSA", pub2, "caller", "prod/site-b"))  # cloned identity elsewhere
        t2 = s2.sign({"sub": "x", "aud": "aud", "env": "prod", "site": "site-a", "iat": self.now,
                      "exp": self.now + 60, "caps": []})
        self.assertEqual(_code(lambda: self.a.authenticate(t2)), "SNAP_UNAUTHENTICATED")
        s3, pub3 = Signer.ed25519("k3")
        self.trust.add(TrustedKey("k3", "EdDSA", pub3, "grant-issuer", "prod/site-a"))
        t3 = s3.sign({"sub": "x", "aud": "aud", "env": "prod", "site": "site-a", "iat": self.now,
                      "exp": self.now + 60, "caps": []})
        self.assertEqual(_code(lambda: self.a.authenticate(t3)), "SNAP_UNAUTHENTICATED")  # issuer key != caller

    def test_clock_skew_bounded(self):
        t = self.tok(iat=self.now - 80, exp=self.now - 20)  # expired 20 s ago: inside 30 s skew
        self.a.authenticate(t)
        t = self.tok(iat=self.now - 100, exp=self.now - 40)
        self.assertEqual(_code(lambda: self.a.authenticate(t)), "SNAP_UNAUTHENTICATED")

    def test_authorization_matrix(self):
        p = Principal("x", ({"cap": "snapshot.restore", "tenant": "t1", "workload": "w1", "environment": "prod"},
                            {"cap": "snapshot.capture", "tenant": "*", "workload": "*", "environment": "*"}),
                      False, None, "k1", "j")
        authorize(p, "snapshot.restore", tenant="t1", workload="w1", environment="prod")
        for kw in ({"tenant": "t2", "workload": "w1", "environment": "prod"},
                   {"tenant": "t1", "workload": "w2", "environment": "prod"},
                   {"tenant": "t1", "workload": "w1", "environment": "dev"}):
            self.assertEqual(_code(lambda: authorize(p, "snapshot.restore", **kw)), "SNAP_FORBIDDEN")
        # wildcard on a non-admin capability is ignored (no escalation via wildcards)
        self.assertEqual(_code(lambda: authorize(p, "snapshot.capture", tenant="t1")), "SNAP_FORBIDDEN")
        self.assertEqual(_code(lambda: authorize(p, "snapshot.delete", tenant="t1")), "SNAP_FORBIDDEN")
        self.assertEqual(_code(lambda: authorize(p, "snapshot.root", tenant="t1")), "SNAP_FORBIDDEN")


class CryptoTests(unittest.TestCase):
    def setUp(self):
        self.kms = crypto.LocalKeyService()
        self.kms.create("kek")
        self.ctx = {"snapshot_id": "s", "tenant": "t1", "workload": "w", "environment": "prod", "site": "a",
                    "fingerprint": "f" * 64, "generation": 1}
        self.pt = bytes(range(256)) * 100  # 25,600 bytes -> 7 chunks of 4096
        self.env, self.blob = crypto.seal_envelope(self.pt, ctx=self.ctx, kms=self.kms, key_id="kek", chunk_size=4096)

    def open(self, blob=None, env=None, ctx=None):
        return crypto.open_envelope(blob if blob is not None else self.blob, env=env or self.env,
                                    ctx=ctx or self.ctx, kms=self.kms)

    def test_roundtrip_and_no_plaintext(self):
        self.assertEqual(self.open(), self.pt)
        self.assertNotIn(self.pt[:64], self.blob)
        self.assertEqual(self.env["chunks"], 7)

    def fixup(self, blob):
        import hashlib
        return blob, dict(self.env, ciphertext_sha256=hashlib.sha256(blob).hexdigest())

    def test_chunk_reorder_drop_duplicate_truncate_and_context_rebinding(self):
        c = 4096 + 16
        chunks = [self.blob[i * c:(i + 1) * c] for i in range(7)]
        attacks = {
            "reorder": b"".join([chunks[1], chunks[0]] + chunks[2:]),
            "duplicate": b"".join(chunks[:2] + [chunks[1]] + chunks[3:]),
            "bitflip": self.blob[:100] + bytes([self.blob[100] ^ 1]) + self.blob[101:],
        }
        for name, blob in attacks.items():
            with self.subTest(name):
                b, env = self.fixup(blob)
                self.assertEqual(_code(lambda: self.open(b, env)), "SNAP_CIPHERTEXT_INVALID")
        b, env = self.fixup(b"".join(chunks[:-1]))  # drop final chunk, even with consistent metadata
        env = dict(env, chunks=6, plaintext_bytes=6 * 4096)
        self.assertEqual(_code(lambda: self.open(b, env)), "SNAP_CIPHERTEXT_INVALID")
        for field in ("tenant", "workload", "environment", "snapshot_id", "fingerprint"):
            with self.subTest(field):
                ctx = dict(self.ctx, **{field: "x" * 64 if field == "fingerprint" else "other"})
                self.assertIn(_code(lambda: self.open(ctx=ctx)), ("SNAP_CIPHERTEXT_INVALID",))
        self.assertEqual(_code(lambda: self.open(self.blob[:-1])), "SNAP_CIPHERTEXT_INVALID")
        # the digest check remains available for scrub/read-back
        bad = self.blob[:10] + bytes([self.blob[10] ^ 1]) + self.blob[11:]
        self.assertEqual(_code(lambda: crypto.open_envelope(bad, env=self.env, ctx=self.ctx, kms=self.kms,
                                                            verify_digest=True)), "SNAP_STORAGE_CORRUPT")
        # without fixing up the digest, AEAD alone still rejects every attack
        for blob in attacks.values():
            self.assertEqual(_code(lambda: self.open(blob)), "SNAP_CIPHERTEXT_INVALID")

    def test_cross_snapshot_chunk_substitution(self):
        ctx2 = dict(self.ctx, snapshot_id="s2")
        env2, blob2 = crypto.seal_envelope(self.pt, ctx=ctx2, kms=self.kms, key_id="kek", chunk_size=4096)
        c = 4096 + 16
        mixed = self.blob[:c] + blob2[c:2 * c] + self.blob[2 * c:]
        b, env = self.fixup(mixed)
        self.assertEqual(_code(lambda: self.open(b, env)), "SNAP_CIPHERTEXT_INVALID")

    def test_rotation_rewrap_revocation_destroy(self):
        v2 = self.kms.rotate("kek")
        self.assertEqual(v2, 2)
        self.assertEqual(self.open(), self.pt)  # old version still decrypts
        nv, nw = self.kms.rewrap("kek", self.env["key_version"], self.env["wrapped_dek"], self.ctx)
        env2 = dict(self.env, key_version=nv, wrapped_dek=nw)
        self.assertEqual(self.open(env=env2), self.pt)
        self.kms.set_state("kek", 1, "destroyed")  # crypto-erase of everything wrapped under v1
        self.assertEqual(_code(lambda: self.open()), "SNAP_KEY_REVOKED")
        self.assertEqual(self.open(env=env2), self.pt)
        with self.assertRaises(ValueError):
            self.kms.set_state("kek", 1, "enabled")

    def test_kms_outage_and_wrapped_dek_context_binding(self):
        self.kms.available = False
        self.assertEqual(_code(lambda: self.open()), "SNAP_KMS_UNAVAILABLE")
        self.kms.available = True
        self.assertEqual(_code(lambda: self.kms.unwrap("kek", 1, self.env["wrapped_dek"], dict(self.ctx, tenant="t2"))),
                         "SNAP_CIPHERTEXT_INVALID")

    def test_empty_plaintext(self):
        env, blob = crypto.seal_envelope(b"", ctx=self.ctx, kms=self.kms, key_id="kek")
        self.assertEqual(crypto.open_envelope(blob, env=env, ctx=self.ctx, kms=self.kms), b"")


class SchemaTests(unittest.TestCase):
    def test_canonical_serialization(self):
        a = schema.canonical_bytes({"b": 1, "a": [1, "é"]})
        self.assertEqual(a, '{"a":[1,"é"],"b":1}'.encode())
        with self.assertRaises(ValueError):
            schema.canonical_bytes({"x": 1.5})

    def test_bounded_parse(self):
        self.assertEqual(_code(lambda: schema.parse_json(b"x" * (70 * 1024), "PK_SNAPSHOT_ERROR/1")),
                         "SNAP_LIMIT_EXCEEDED")
        self.assertEqual(_code(lambda: schema.parse_json(b"[" * 5000, "PK_SNAPSHOT_ERROR/1")), "SNAP_INVALID_REQUEST")
        self.assertEqual(_code(lambda: schema.parse_json(b'{"a": NaN}', "PK_SNAPSHOT_ERROR/1")), "SNAP_INVALID_REQUEST")
        self.assertEqual(_code(lambda: schema.parse_json(b"\xff\xfe", "PK_SNAPSHOT_ERROR/1")), "SNAP_INVALID_REQUEST")

    def test_generated_schema_files_match(self):
        import pathlib
        d = pathlib.Path(schema.__file__).parent / "schemas"
        for sid, body in schema.SCHEMAS.items():
            doc = json.loads((d / (sid.replace("/", "_") + ".schema.json")).read_text())
            self.assertEqual({k: v for k, v in doc.items() if not k.startswith("$") and k != "title"},
                             json.loads(json.dumps(body)), sid)

    def test_conformance_fixtures(self):
        import pathlib
        d = pathlib.Path(schema.__file__).parent / "tests" / "fixtures" / "conformance"
        cases = json.loads((d / "cases.json").read_text())
        self.assertGreaterEqual(len(cases), 20)
        for c in cases:
            with self.subTest(c["name"]):
                errs = schema.validate(c["doc"], c["schema"])
                self.assertEqual(not errs, c["valid"], errs)


class ErrorCatalogTests(unittest.TestCase):
    def test_catalog_file_in_sync_and_unique(self):
        import pathlib
        from inv26_microvm_snapshotting.errors import catalog_document
        p = pathlib.Path(schema.__file__).parent / "ERRORS.json"
        self.assertEqual(json.loads(p.read_text()), json.loads(json.dumps(catalog_document())))
        self.assertEqual(len({s.number for s in CATALOG.values()}), len(CATALOG))
        for needed in ("SNAP_NOT_FOUND", "SNAP_DUPLICATE", "SNAP_TENANT_MISMATCH", "SNAP_WORKLOAD_MISMATCH",
                       "SNAP_ENVIRONMENT_MISMATCH", "SNAP_MODEL_MISMATCH", "SNAP_UNSUPPORTED_VERSION",
                       "SNAP_SIGNATURE_INVALID", "SNAP_KMS_UNAVAILABLE", "SNAP_ENTROPY_FAILED",
                       "SNAP_STORAGE_CORRUPT", "SNAP_TIMEOUT", "SNAP_OVERLOADED", "SNAP_QUARANTINED"):
            self.assertIn(needed, CATALOG)

    def test_unknown_code_is_internal(self):
        self.assertEqual(SnapshotServiceError("NOPE").code, "SNAP_INTERNAL")


class LifecycleTests(unittest.TestCase):
    def test_model_generated_transitions(self):
        for kind, table, states in (("snapshot", lifecycle.SNAPSHOT_TRANSITIONS, lifecycle.SNAPSHOT_STATES),
                                    ("restore", lifecycle.RESTORE_TRANSITIONS, lifecycle.RESTORE_STATES)):
            for a in states:
                for b in states:
                    ok = b in table.get(a, ())
                    with self.subTest(kind=kind, a=a, b=b):
                        self.assertEqual(_code(lambda: lifecycle.check_transition(kind, a, b)) is None, ok)

    def test_ready_only_after_reseeding(self):
        preds = [a for a, nxt in lifecycle.RESTORE_TRANSITIONS.items() if "READY" in nxt]
        self.assertEqual(preds, ["RESEEDING"])
        self.assertEqual([a for a, n in lifecycle.SNAPSHOT_TRANSITIONS.items() if "AVAILABLE" in n],
                         ["VERIFYING", "QUARANTINED"])

    def test_every_transient_state_has_recovery(self):
        for s in lifecycle.TRANSIENT_SNAPSHOT:
            self.assertIn(lifecycle.recovery_action("snapshot", s), ("FAILED", "DELETED"))
        for s in lifecycle.TRANSIENT_RESTORE:
            self.assertEqual(lifecycle.recovery_action("restore", s), "FAILED")
        self.assertIsNone(lifecycle.recovery_action("snapshot", "AVAILABLE"))


class ConfigTests(unittest.TestCase):
    def test_examples_validate(self):
        import pathlib
        d = pathlib.Path(schema.__file__).parent / "examples"
        for name in ("config.production.json", "config.restrictive.json"):
            self.assertEqual(cfgmod.validate(json.loads((d / name).read_text())), [], name)

    def test_secure_defaults_and_locked_invariants(self):
        for path in cfgmod.LOCKED:
            doc = cfgmod.example()
            sect, key = path.split(".")
            doc[sect][key] = False
            self.assertTrue(any(path in e for e in cfgmod.validate(doc)), path)
        with self.assertRaises(SnapshotServiceError):
            cfgmod.compose(("base", {}), ("site", {"security": {"deny_cross_boundary_restore": False}}))

    def test_negative_values(self):
        bad = {
            "profile": "yolo", "tier": "moon", "environment": "Bad Env",
            "runtime": {"adapter": "reference", "version": "1", "arch": "x86_64"},  # prod forbids reference
            "timeouts_ms": dict(cfgmod.DEFAULTS["timeouts_ms"], restore=5),
            "admission": dict(cfgmod.DEFAULTS["admission"], per_tenant=10 ** 6),
            "retry": dict(cfgmod.DEFAULTS["retry"], attempts=True),
            "kms": {"key_id": "-----BEGIN PRIVATE KEY-----"},
            "auth": {"audience": "a", "password": "hunter22"},
            "restore_budget_ms": float("nan"),
        }
        for k, v in bad.items():
            with self.subTest(k):
                doc = cfgmod.example()
                doc[k] = v
                errs = cfgmod.validate(doc)
                self.assertTrue(errs, k)
                self.assertFalse(any("hunter22" in e or "PRIVATE KEY" in e for e in errs))

    def test_overlay_order_and_emergency_scope(self):
        base = {"environment": "prod", "site": "site-a", "region": "eu-west", "kms": {"key_id": "k"},
                "auth": {"audience": "a"}, "residency": {"allowed_sites": ["site-a"], "allowed_regions": ["eu-west"]}}
        doc = cfgmod.compose(("base", base), ("site", {"admission": {"max_inflight": 8, "per_tenant": 4}}),
                             ("emergency", {"admission": {"max_inflight": 2, "per_tenant": 1}}))
        self.assertEqual(doc["admission"]["max_inflight"], 2)
        self.assertEqual(cfgmod.validate(doc), [])
        with self.assertRaises(SnapshotServiceError):
            cfgmod.compose(("site", {}), ("base", base))
        with self.assertRaises(SnapshotServiceError):
            cfgmod.compose(("base", base), ("emergency", {"kms": {"key_id": "evil"}}))
        with self.assertRaises(SnapshotServiceError):
            cfgmod.compose(("base", dict(base, surprise=1)))

    def test_atomic_activation_provenance_rollback(self):
        meta = MetaStore()
        store = cfgmod.ConfigStore(meta)
        a = cfgmod.example()
        p1 = store.activate(a, author="alice", source="git:abc", approval_ref="CR-1", expect_revision=0)
        b = copy.deepcopy(a)
        b["admission"]["max_inflight"] = 32
        store.activate(b, author="bob", source="git:def", approval_ref="CR-2", expect_revision=1)
        with self.assertRaises(SnapshotServiceError) as cm:  # stale writer
            store.activate(a, author="mallory", source="x", approval_ref=None, expect_revision=1)
        self.assertEqual(cm.exception.code, "SNAP_STALE_GENERATION")
        bad = copy.deepcopy(b)
        bad["security"]["require_encryption"] = False
        with self.assertRaises(SnapshotServiceError):
            store.activate(bad, author="eve", source="x", approval_ref=None, expect_revision=2)
        self.assertEqual(store.active()[0], 2)  # last-known-good kept
        store.rollback(to_revision=1, author="carol", reason="latency regression")
        rev, doc = store.active()
        self.assertEqual((rev, doc["admission"]["max_inflight"]), (3, a["admission"]["max_inflight"]))
        hist = store.history()
        self.assertEqual([h["revision"] for h in hist], [1, 2, 3])
        self.assertEqual(hist[0]["digest"], p1["digest"])
        self.assertEqual(hist[2]["previous_revision"], 2)
        self.assertEqual(store.governing(2)["provenance"]["author"], "bob")

    def test_crash_during_activation_is_all_or_nothing(self):
        import tempfile
        root = tempfile.mkdtemp()
        meta = MetaStore(root)
        store = cfgmod.ConfigStore(meta)
        store.activate(cfgmod.example(), author="a", source="s", approval_ref=None, expect_revision=0)
        meta.fail_after_wal_write = True  # crash after the WAL line is durable
        b = cfgmod.example()
        b["admission"]["max_inflight"] = 20
        with self.assertRaises(OSError):
            store.activate(b, author="a", source="s", approval_ref=None, expect_revision=1)
        again = cfgmod.ConfigStore(MetaStore(root))
        rev, doc = again.active()
        self.assertEqual((rev, doc["admission"]["max_inflight"]), (2, 20))  # wholly new
        # torn tail: a half-written line is discarded -> wholly old
        with open(f"{root}/wal.jsonl", "ab") as fh:
            fh.write(b'{"seq": 99, "ops": [')
        m3 = MetaStore(root)
        self.assertEqual(cfgmod.ConfigStore(m3).active()[0], 2)
        self.assertEqual(m3.torn_lines_discarded, 1)


if __name__ == "__main__":
    unittest.main()
