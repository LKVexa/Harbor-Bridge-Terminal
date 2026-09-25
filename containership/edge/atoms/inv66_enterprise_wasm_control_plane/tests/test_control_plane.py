"""Self-contained security and regression tests for the local INV-66 decision engine."""
from __future__ import annotations

import importlib.util
import math
import pathlib
import sys
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("inv66_control_plane_standalone", PKG_DIR / "control_plane.py")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
if SPEC.loader is None:
    raise RuntimeError("cannot load control_plane.py")
SPEC.loader.exec_module(MODULE)
ControlPlane = MODULE.ControlPlane


class ControlPlaneTest(unittest.TestCase):
    def cp(self, **kwargs):
        config = dict(
            roles={("dev", "staging"): "deployer", ("ops", "prod"): "deployer"},
            registries={"registry.estate.local"},
            signers={"release-signer"},
        )
        config.update(kwargs)
        return ControlPlane(**config)

    @staticmethod
    def manifest(name="api"):
        return {"components": [{"name": name, "image": f"registry.estate.local/{name}:1", "signer": "release-signer"}]}

    def test_admission_and_rbac(self):
        cp = self.cp()
        self.assertTrue(cp.admit("ops", "prod", self.manifest())["admitted"])
        denied = cp.admit("dev", "prod", self.manifest())
        self.assertFalse(denied["admitted"])
        self.assertIn("dev may not deploy to prod", denied["reasons"])
        self.assertEqual(len(cp.forwarded), 1)
        self.assertTrue(cp.verify_audit())

    def test_malformed_component_never_crashes_or_forwards(self):
        cp = self.cp()
        malformed = {"components": [{"image": "registry.estate.local/api:1", "signer": "release-signer"}]}
        decision = cp.admit("ops", "prod", malformed)
        self.assertFalse(decision["admitted"])
        self.assertTrue(any("name" in reason for reason in decision["reasons"]))
        self.assertEqual(cp.forwarded, ())

    def test_untrusted_registry_and_signer_are_both_reported(self):
        cp = self.cp()
        m = {"components": [{"name": "api", "image": "ghcr.evil.example/api:1", "signer": "unknown"}]}
        decision = cp.admit("ops", "prod", m)
        self.assertFalse(decision["admitted"])
        self.assertEqual(sum("not approved" in r for r in decision["reasons"]), 2)

    def test_duplicate_names_and_component_limit_fail_closed(self):
        cp = self.cp(max_components=2)
        m = {"components": [
            {"name": "a", "image": "registry.estate.local/a:1", "signer": "release-signer"},
            {"name": "a", "image": "registry.estate.local/a:2", "signer": "release-signer"},
            {"name": "b", "image": "registry.estate.local/b:1", "signer": "release-signer"},
        ]}
        d = cp.admit("ops", "prod", m)
        self.assertFalse(d["admitted"])
        self.assertTrue(any("limit is 2" in r for r in d["reasons"]))
        self.assertTrue(any("duplicate component name" in r for r in d["reasons"]))

    def test_noncanonical_json_fails_closed(self):
        cp = self.cp()
        m = self.manifest()
        m["value"] = math.nan
        d = cp.admit("ops", "prod", m)
        self.assertFalse(d["admitted"])
        self.assertIsNone(d["manifest_sha256"])
        self.assertTrue(any("canonical JSON" in r for r in d["reasons"]))

    def test_policy_input_is_defensively_copied(self):
        roles = {("ops", "prod"): "deployer"}
        cp = ControlPlane(roles=roles, registries={"registry.estate.local"}, signers={"release-signer"})
        roles[("attacker", "prod")] = "admin"
        self.assertFalse(cp.admit("attacker", "prod", self.manifest())["admitted"])
        with self.assertRaises(TypeError):
            cp.roles[("attacker", "prod")] = "admin"

    def test_forwarded_manifest_is_defensively_copied(self):
        cp = self.cp()
        m = self.manifest()
        cp.admit("ops", "prod", m)
        m["components"][0]["image"] = "evil.example/api:9"
        snapshot = cp.forwarded
        self.assertEqual(snapshot[0]["components"][0]["image"], "registry.estate.local/api:1")
        snapshot[0]["components"][0]["image"] = "other.example/api:2"
        self.assertEqual(cp.forwarded[0]["components"][0]["image"], "registry.estate.local/api:1")

    def test_audit_snapshot_is_defensive_and_tamper_evident(self):
        cp = self.cp()
        decision = cp.admit("ops", "prod", self.manifest())
        decision["admitted"] = False
        exported = cp.export_audit()
        self.assertTrue(exported[0]["entry"]["admitted"])
        exported[0]["entry"]["admitted"] = False
        self.assertFalse(cp.verify_audit(exported))
        self.assertTrue(cp.verify_audit())

    def test_audit_records_manifest_digest_and_sequence(self):
        cp = self.cp()
        d = cp.admit("ops", "prod", self.manifest())
        audit = cp.export_audit()
        self.assertEqual(audit[0]["sequence"], 1)
        self.assertEqual(audit[0]["entry"]["manifest_sha256"], d["manifest_sha256"])
        self.assertRegex(d["manifest_sha256"], r"^[0-9a-f]{64}$")

    def test_concurrent_admissions_keep_audit_chain_valid(self):
        cp = self.cp()
        threads = [threading.Thread(target=cp.admit, args=("ops", "prod", self.manifest(f"api{i}"))) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(cp.audit), 50)
        self.assertEqual(len(cp.forwarded), 50)
        self.assertTrue(cp.verify_audit())
        self.assertEqual([r["sequence"] for r in cp.audit], list(range(1, 51)))

    def test_invalid_policy_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            self.cp(roles={("ops", "prod"): "superuser"})
        with self.assertRaises(ValueError):
            self.cp(registries=set())
        with self.assertRaises(ValueError):
            self.cp(signers={""})
        with self.assertRaises(ValueError):
            self.cp(registries="registry.estate.local")


if __name__ == "__main__":
    unittest.main()
