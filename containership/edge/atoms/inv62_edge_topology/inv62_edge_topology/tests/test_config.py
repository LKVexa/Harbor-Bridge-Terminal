"""Configuration: schema, secure defaults, overlays, pre-activation
validation, provenance, CAS activation, rollback, signing, secrets
(MC-022 .. MC-029)."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from support import SECRETS, base_config, make_service, seeded

from inv62_edge_topology.production import config as C, errors


class SchemaAndDefaultsTest(unittest.TestCase):
    def test_defaults_are_secure(self):
        d = C.DEFAULTS
        self.assertTrue(d["security"]["require_auth"])
        self.assertTrue(d["policy"]["residency_required"])
        self.assertFalse(d["policy"]["allow_cross_site_failover"])
        self.assertEqual(d["policy"]["stale_link_behaviour"], "exclude")
        self.assertFalse(d["telemetry"]["expose_node_names"])
        self.assertTrue(d["security"]["audit_fsync"])

    def test_auth_cannot_be_disabled(self):
        cfg = base_config(security={"require_auth": False})
        with self.assertRaises(errors.TopoError) as cm:
            C.validate(cfg, C.StaticSecretProvider(SECRETS))
        self.assertEqual(cm.exception.details["path"], "$.security.require_auth")

    def test_inline_secret_rejected(self):
        cfg = base_config()
        cfg["secrets"]["audit_key"] = "hunter2hunter2hunter2hunter2hunter2"
        with self.assertRaises(errors.TopoError):
            C.validate(cfg, C.StaticSecretProvider(SECRETS))

    def test_unknown_keys_rejected(self):
        with self.assertRaises(errors.TopoError):
            C.validate(base_config(tuning={"x": 1}), C.StaticSecretProvider(SECRETS))

    def test_semantic_rules(self):
        bad = [
            base_config(health={"stale_after_s": 1.0, "probe_interval_s": 5.0}),
            base_config(election={"lease_ttl_s": 2.0, "renew_before_s": 3.0}),
            base_config(environment="prod", telemetry={"log_level": "debug"}),
            base_config(environment="prod", policy={"residency_required": False}),
            base_config(security={"encrypt_at_rest": True}, secrets={"state_key": "secret://state"}) | {"secrets": {"token_keys": {"k1": "secret://keys/k1"}, "audit_key": "secret://audit"}},
            base_config(secrets={"active_token_key": "k7"}),
        ]
        for cfg in bad:
            with self.subTest(cfg=str(cfg)[:60]):
                with self.assertRaises(errors.TopoError):
                    C.validate(cfg, C.StaticSecretProvider(SECRETS))

    def test_short_or_missing_secret_rejected(self):
        with self.assertRaises(errors.TopoError):
            C.validate(base_config(), C.StaticSecretProvider({**SECRETS, "secret://audit": b"short"}))
        p = C.StaticSecretProvider(SECRETS)
        p.available = False
        with self.assertRaises(errors.TopoError) as cm:
            C.validate(base_config(), p)
        self.assertEqual(cm.exception.code, "TOPO.DEPENDENCY_UNAVAILABLE")


class OverlayTest(unittest.TestCase):
    def test_precedence_and_no_null_deletion(self):
        eff = C.compose({"environment": "staging", "cloud_node": "c", "secrets": {}},
                        {"health": {"stale_after_s": 45.0}}, {"site": "s1", "health": {"max_flaps": 9}})
        self.assertEqual(eff["health"]["stale_after_s"], 45.0)
        self.assertEqual(eff["health"]["max_flaps"], 9)
        self.assertEqual(eff["health"]["probe_interval_s"], C.DEFAULTS["health"]["probe_interval_s"])
        self.assertEqual(eff["site"], "s1")
        with self.assertRaises(errors.TopoError):
            C.compose({"cloud_node": "c"}, {"security": None})


class GenerationTest(unittest.TestCase):
    def test_provenance_cas_and_rollback(self):
        svc = make_service()
        g1 = svc.config.active.provenance
        self.assertEqual((g1.generation, g1.author, g1.previous), (1, "test", None))
        self.assertEqual(g1.digest, C.canonical_digest(base_config()))
        with self.assertRaises(errors.TopoError) as cm:
            svc.activate_config(base_config(), author="x", source="y", expected_generation=None)
        self.assertEqual(cm.exception.code, "TOPO.CONFLICT")
        g2 = svc.activate_config(base_config(telemetry={"retention_days": 7}), author="ops", source="change-42",
                                 expected_generation=1)
        self.assertEqual((g2.generation, g2.previous), (2, 1))
        op = svc.authn.issue("op", "operator", ["tenant-a"])
        out = svc.admin(op, "rollback_config", reason="bad change")
        self.assertEqual(out["generation"], 3)
        self.assertEqual(svc.config.active.resolved.config["telemetry"]["retention_days"], 30)
        self.assertIn("rollback:1", svc.config.active.provenance.source)
        self.assertEqual([h["generation"] for h in svc.config.history()], [1, 2, 3])

    def test_failed_activation_is_atomic(self):
        svc, feed = seeded()
        before = svc.config.active.provenance.generation
        bad = base_config(limits={"max_links": 1})
        with self.assertRaises(errors.TopoError):
            svc.activate_config(bad, author="x", source="y", expected_generation=before)
        self.assertEqual(svc.config.active.provenance.generation, before)

        def boom(gen):
            raise RuntimeError("runtime build failed")
        svc.config.on_activate = boom
        with self.assertRaises(RuntimeError):
            svc.activate_config(base_config(telemetry={"retention_days": 9}), author="x", source="y",
                                expected_generation=before)
        self.assertEqual(svc.config.active.provenance.generation, before)
        self.assertTrue(svc.health()["ready"])

    def test_signed_config_enforced(self):
        cfg = base_config(security={"require_signed_config": True})
        cfg["secrets"]["config_signing_key"] = "secret://cfgsign"
        store = C.ConfigStore(C.StaticSecretProvider(SECRETS))
        with self.assertRaises(errors.TopoError):
            store.activate(cfg, author="a", source="s", expected_generation=None)
        with self.assertRaises(errors.TopoError):
            store.activate(cfg, author="a", source="s", expected_generation=None, signature="0" * 64)
        sig = C.sign_config(cfg, SECRETS["secret://cfgsign"])
        self.assertEqual(store.activate(cfg, author="a", source="s", expected_generation=None, signature=sig).generation, 1)

    def test_generations_persist_atomically(self):
        with tempfile.TemporaryDirectory() as d:
            svc = make_service(state_dir=d)
            files = sorted(p.name for p in (Path(d) / "config").iterdir())
            self.assertEqual(files, ["ACTIVE", "gen-000001.json"])
            self.assertEqual((Path(d) / "config" / "ACTIVE").read_text(), "1")
            del svc


class FileSecretTest(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "POSIX permission semantics")
    def test_permissions_and_escape(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "k"
            p.write_bytes(b"x" * 40)
            os.chmod(p, 0o600)
            prov = C.FileSecretProvider(d)
            self.assertEqual(prov.resolve("secret://k"), b"x" * 40)
            os.chmod(p, 0o644)
            with self.assertRaises(errors.TopoError):
                prov.resolve("secret://k")
            with self.assertRaises(errors.TopoError):
                prov.resolve("secret://../../etc/passwd")


if __name__ == "__main__":
    unittest.main()
