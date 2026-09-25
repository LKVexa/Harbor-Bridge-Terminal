"""Typed configuration, overlays, provenance, secrets, bootstrap, backend boundary (MC-001, MC-004, MC-005, MC-028, MC-029)."""
from __future__ import annotations

import json
import os
import unittest

from _util import tmpdir
from inv05_current_control_state_system import config
from inv05_current_control_state_system.backend import (
    ExternalBackendContract, LocalBackend, classify_backend_error, runtime_self_test,
)
from inv05_current_control_state_system.bootstrap import build_service
from inv05_current_control_state_system.errors import InvalidArgument, Unavailable
from inv05_current_control_state_system.security import SecretProvider
from inv05_current_control_state_system.observability import NullStream
from inv05_current_control_state_system.store import ControlStore


def secrets_dir():
    d = tmpdir()
    for n in ("data-key", "audit-key", "token-key"):
        p = os.path.join(d, n)
        with open(p, "w") as fh:
            fh.write(os.urandom(16).hex())
        os.chmod(p, 0o600)
    return d


class ConfigTest(unittest.TestCase):
    def test_defaults_are_secure(self):
        c = config.build()
        self.assertTrue(c["tls.enabled"])
        self.assertTrue(c["storage.encrypt_at_rest"])
        self.assertEqual(c["storage.durability"], "fsync")
        self.assertFalse(c["auth.allow_tokens"])
        self.assertEqual(c["listen.host"], "127.0.0.1")

    def test_overlay_precedence_and_provenance(self):
        c = config.build(base={"compaction.retain_revisions": 1000}, environment={"compaction.retain_revisions": 2000},
                         site={"node.site": "edge-7"}, overrides={"compaction.retain_revisions": 3000})
        self.assertEqual(c["compaction.retain_revisions"], 3000)
        self.assertEqual(c.provenance["compaction.retain_revisions"], "overrides")
        self.assertEqual(c.provenance["node.site"], "site")
        self.assertEqual(c.provenance["listen.port"], "defaults")
        self.assertEqual(len(c.sha256), 64)
        self.assertEqual(config.build(site={"node.site": "edge-7"}).sha256,
                         config.build(site={"node.site": "edge-7"}).sha256)

    def test_validation_fails_closed(self):
        bad = [{"nope": 1}, {"listen.port": 70000}, {"storage.durability": "none"}, {"listen.port": True},
               {"storage.data_key": "plaintext-key"}, {"deadlines.default_ms": 90000},
               {"listen.host": "0.0.0.0"}, {"listen.host": "0.0.0.0", "tls.enabled": False}]
        for b in bad:
            with self.subTest(b), self.assertRaises(InvalidArgument):
                config.build(base=b)
        with self.assertRaises(InvalidArgument):
            config.build(bogus_layer={})

    def test_restart_required_classification_and_redaction(self):
        a, b = config.build(), config.build(base={"listen.port": 9999, "telemetry.trace_ratio": 0.5})
        self.assertEqual(a.restart_required_diff(b), ["listen.port"])
        self.assertEqual(a.redacted()["storage.data_key"], "[REF]")
        self.assertIn("storage.data_key", config.schema_document())


class BootstrapTest(unittest.TestCase):
    def test_bootstrap_is_deterministic_and_idempotent(self):
        d, s = tmpdir(), secrets_dir()
        cfg = config.build(base={"storage.data_dir": d, "audit.path": os.path.join(d, "audit.log")})
        svc, art = build_service(cfg, SecretProvider(s), log_stream=NullStream())
        self.assertEqual(len(art["checks"]["markers_created"]), 4)
        self.assertTrue(svc.readiness()["status"] == "ready")
        rev = svc.store.revision
        svc.stop()
        svc2, art2 = build_service(cfg, SecretProvider(s), log_stream=NullStream())
        self.assertEqual(art2["checks"]["markers_created"], [])  # rerun converges, no new writes
        self.assertEqual(svc2.store.revision, rev)
        with open(os.path.join(d, "bootstrap.json")) as fh:
            doc = json.load(fh)
        for k in ("build", "config_sha256", "audit_anchor", "checks", "sha256", "revision"):
            self.assertIn(k, doc)
        svc2.stop()

    def test_bootstrap_refuses_without_keys(self):
        d = tmpdir()
        cfg = config.build(base={"storage.data_dir": d, "audit.path": os.path.join(d, "a.log")})
        with self.assertRaises(InvalidArgument):
            build_service(cfg, SecretProvider(tmpdir(), env_prefix="NOPE_"))
        self.assertEqual([f for f in os.listdir(d) if f.startswith("wal")], [])  # nothing initialised


class BackendBoundaryTest(unittest.TestCase):
    def test_external_backend_fails_closed_until_pinned(self):
        ext = ExternalBackendContract()
        problems = ext.preflight()
        self.assertTrue(any("APPROVED" in p for p in problems))
        with self.assertRaises(Unavailable):
            ext.connect()

    def test_pinned_backend_artifact_digest_verification(self):
        d = tmpdir()
        art = os.path.join(d, "etcd.tar.gz")
        with open(art, "wb") as fh:
            fh.write(b"artifact")
        pin = os.path.join(d, "pin.json")
        import hashlib
        with open(pin, "w") as fh:
            json.dump({"status": "APPROVED", "backend": "etcd", "version": "3.6.0", "approved_by": "x",
                       "approved_on": "2026-09-22", "artifact_sha256": hashlib.sha256(b"artifact").hexdigest(),
                       "features": list(ExternalBackendContract.REQUIRED_FEATURES)}, fh)
        ext = ExternalBackendContract(pin)
        self.assertEqual(ext.preflight(), [])
        self.assertTrue(ext.verify_artifact(art))
        with open(art, "ab") as fh:
            fh.write(b"tampered")
        self.assertFalse(ext.verify_artifact(art))

    def test_error_classification(self):
        cases = {TimeoutError(): "CSTATE_TIMEOUT", ConnectionRefusedError(): "CSTATE_UNAVAILABLE",
                 PermissionError(): "CSTATE_PERMISSION_DENIED", RuntimeError("mvcc: required revision has been compacted"): "CSTATE_COMPACTED",
                 RuntimeError("etcdserver: too many requests"): "CSTATE_OVERLOADED", ValueError("bad"): "CSTATE_INVALID_ARGUMENT",
                 RuntimeError("database file corrupt"): "CSTATE_FAILED", RuntimeError("x509: certificate expired"): "CSTATE_UNAUTHENTICATED"}
        for exc, code in cases.items():
            self.assertEqual(classify_backend_error(exc).code, code, exc)

    def test_local_backend_identity_and_runtime_self_test(self):
        b = LocalBackend(ControlStore())
        self.assertEqual(b.identity()["members"], 1)
        self.assertTrue(b.healthy())
        rt = runtime_self_test()
        self.assertTrue(rt["ok"], rt)
        self.assertIsNone(rt["pk_core"])
        self.assertFalse(runtime_self_test(require_pk_core=True)["ok"])  # absent framework is reported, not hidden


if __name__ == "__main__":
    unittest.main()
