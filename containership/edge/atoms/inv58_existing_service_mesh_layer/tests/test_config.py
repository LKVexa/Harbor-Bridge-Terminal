"""MC-009 / MC-014: declarative config, overlays, validation, provenance, atomic activation, rollback, secrets."""
from __future__ import annotations

import threading
import unittest

from _support import Clock, base_config, config, secret_refs


class ValidationTest(unittest.TestCase):
    def test_secure_defaults_are_valid_on_their_own(self):
        v = config.validate(config.compose())
        self.assertEqual(v["trust_outage_policy"]["identity"], "fail_closed")
        self.assertTrue(v["telemetry"]["redact_high_cardinality"])

    def test_overlays_change_site_behaviour_without_rebuild(self):
        env = {"version": "prod-7", "default_budget": 2}
        site = {"limits": {"max_inflight": 64}, "meshed_destinations": ["payments"]}
        doc = config.compose(env, site)
        v = config.validate(doc)
        self.assertEqual((v["default_budget"], v["limits"]["max_inflight"], v["limits"]["max_routes"]), (2, 64, 10_000))

    def test_security_downgrades_are_rejected(self):
        bad = [
            {"trust_outage_policy": {"identity": "fail_open"}},
            {"trust_outage_policy": {"time": "fail_safe_degraded"}},
            {"telemetry": {"redact_high_cardinality": False}},
            {"audit_key_ref": "plaintext-key"},
            {"token_key_ref": "-----BEGIN RSA PRIVATE KEY-----abc"},
            {"policy": {"roles": {"ops": ["control.break_glass"]}}},
            {"policy": {"roles": {"ops": ["*"]}}},
            {"spiffe_bindings": {"runtime:x": {"actor_type": "operator", "roles": []}}},
            {"meshed_destinations": [" payments"]},
            {"default_budget": 9, "max_budget": 3},
            {"surprise": 1},
            {"schema": "PK_MESH_CONFIG/2"},
            {"trust_domain": "a..b"},
            {"retry": {"base_delay_ms": 5000, "max_delay_ms": 10}},
            {"notes": "password = hunter2"},
        ]
        for over in bad:
            with self.subTest(over=over):
                with self.assertRaises(config.ConfigError):
                    config.validate(config.compose(over))

    def test_literal_secret_anywhere_is_rejected(self):
        doc = config.compose({"meshed_destinations": ["api_key=AKIAABCDEFGHIJKLMNOP"]})
        with self.assertRaises(config.ConfigError) as cm:
            config.validate(doc)
        self.assertNotIn("AKIAABCDEFGHIJKLMNOP", str(cm.exception))

    def test_boundaries(self):
        for b, ok in ((1, True), (10, True), (0, False), (11, False)):
            doc = config.compose({"max_budget": b, "default_budget": 1})
            if ok:
                config.validate(doc)
            else:
                with self.assertRaises(config.ConfigError):
                    config.validate(doc)

    def test_size_ceiling(self):
        doc = config.compose({"meshed_destinations": [f"svc-{i:06d}" for i in range(30_000)]})
        with self.assertRaises(config.ConfigError):
            config.validate(doc)

    def test_non_mapping(self):
        for bad in (None, [], "x", 3):
            with self.assertRaises(config.ConfigError):
                config.validate(bad)

    def test_digest_is_canonical(self):
        a = config.compose({"version": "1"})
        b = dict(reversed(list(a.items())))
        self.assertEqual(config.digest(a), config.digest(b))


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.store = config.ConfigStore(clock=self.clock)

    def test_provenance_recorded(self):
        p = self.store.activate(base_config(), author="alice", source="git:abc")
        self.assertEqual((p.author, p.source, p.version, p.activated_at, p.previous_digest),
                         ("alice", "git:abc", "1", self.clock(), None))
        self.assertTrue(p.digest.startswith("sha256:"))

    def test_provenance_required(self):
        with self.assertRaises(config.ConfigError):
            self.store.activate(base_config(), author="", source="x")

    def test_invalid_config_never_activates(self):
        self.store.activate(base_config(), author="a", source="s")
        before = self.store.active()[1].digest
        with self.assertRaises(config.ConfigError):
            self.store.activate(config.compose({"trust_outage_policy": {"key": "fail_open"}}), author="a", source="s")
        self.assertEqual(self.store.active()[1].digest, before)

    def test_optimistic_concurrency(self):
        p1 = self.store.activate(base_config(), author="a", source="s")
        with self.assertRaises(config.ConfigError):
            self.store.activate(base_config(version="2"), author="a", source="s", expected_digest="sha256:bogus")
        p2 = self.store.activate(base_config(version="2"), author="a", source="s", expected_digest=p1.digest)
        self.assertEqual(p2.previous_digest, p1.digest)

    def test_automatic_rollback_on_failed_health_probe(self):
        p1 = self.store.activate(base_config(), author="a", source="s")
        for probe in (lambda c: False, lambda c: 1 / 0):
            with self.assertRaises(config.ConfigError):
                self.store.activate(base_config(version="bad"), author="a", source="s", health_probe=probe)
            self.assertEqual(self.store.active()[1].digest, p1.digest)

    def test_operator_rollback_and_to_digest(self):
        p1 = self.store.activate(base_config(version="1"), author="a", source="s")
        p2 = self.store.activate(base_config(version="2"), author="a", source="s")
        self.store.activate(base_config(version="3"), author="a", source="s")
        r = self.store.rollback(author="op", to_digest=p1.digest)
        self.assertEqual((r.digest, r.source, r.author), (p1.digest, "rollback", "op"))
        self.assertEqual(self.store.active()[0]["version"], "1")
        with self.assertRaises(config.ConfigError):
            self.store.rollback(author="op", to_digest="sha256:nope")
        self.assertIn(p2.digest, [h.digest for h in self.store.history()])

    def test_rollback_with_no_history(self):
        with self.assertRaises(config.ConfigError):
            self.store.rollback(author="op")

    def test_history_is_bounded(self):
        s = config.ConfigStore(clock=self.clock, max_history=3)
        for i in range(10):
            s.activate(base_config(version=str(i)), author="a", source="s")
        self.assertEqual(len(s.history()), 3)

    def test_active_is_a_defensive_copy(self):
        self.store.activate(base_config(), author="a", source="s")
        doc, _ = self.store.active()
        doc["tenants"].append("mallory")
        self.assertNotIn("mallory", self.store.active()[0]["tenants"])

    def test_concurrent_activation_is_atomic(self):
        errors = []

        def worker(i):
            try:
                self.store.activate(base_config(version=str(i)), author=f"w{i}", source="s")
            except Exception as e:  # pragma: no cover
                errors.append(e)

        def reader():
            for _ in range(200):
                a = self.store.active()
                if a is not None:
                    doc, prov = a
                    if config.digest(doc) != prov.digest:
                        errors.append("torn read")

        ts = [threading.Thread(target=worker, args=(i,)) for i in range(16)] + [threading.Thread(target=reader) for _ in range(4)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(errors, [])


class SecretRefTest(unittest.TestCase):
    def test_resolution_is_explicit_and_redacted(self):
        r = secret_refs.SecretResolver({"kms": lambda n: b"k" * 32})
        s = r.resolve("secretref://kms/inv58/audit")
        self.assertNotIn("kkkk", repr(s) + str(s))
        with self.assertRaises(secret_refs.SecretResolutionError):
            r.resolve("secretref://vault/x")
        with self.assertRaises(secret_refs.SecretResolutionError):
            r.resolve("file:///etc/shadow")

    def test_provider_error_text_does_not_leak(self):
        def boom(name):
            raise RuntimeError("the key is hunter2")
        r = secret_refs.SecretResolver({"kms": boom})
        with self.assertRaises(secret_refs.SecretResolutionError) as cm:
            r.resolve("secretref://kms/a")
        self.assertNotIn("hunter2", str(cm.exception))

    def test_redact(self):
        out = secret_refs.redact({"password": "x", "token_key_ref": "secretref://kms/a", "note": "token: abc", "n": 3})
        self.assertEqual(out["password"], secret_refs.REDACTED)
        self.assertEqual(out["token_key_ref"], "secretref://kms/a")
        self.assertEqual(out["note"], secret_refs.REDACTED)
        self.assertEqual(out["n"], 3)


if __name__ == "__main__":
    unittest.main()
