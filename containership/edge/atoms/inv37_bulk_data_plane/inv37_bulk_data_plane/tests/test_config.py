"""Configuration schema, layering, preflight, provenance, atomic activation and
rollback (C032-C040)."""
from __future__ import annotations

import json
import os
import pathlib
import tempfile
import unittest

from _support import C, PKG_DIR, Env, pkg


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.env = Env()

    def tearDown(self):
        self.env.close()

    def test_units(self):
        self.assertEqual(C.parse_bytes("16MiB", "x"), 16 << 20)
        self.assertEqual(C.parse_seconds("250ms", "x"), 0.25)
        for bad in ("16MB", "-1", "1.5GiB", True, None):
            self.assertRaises(pkg.ConfigError, C.parse_bytes, bad, "x")

    def test_unknown_key_and_schema_rejected(self):
        self.assertRaises(pkg.ConfigError, C.load_layer, {"limits": {"max_objekt_bytes": 1}}, layer="site")
        self.assertRaises(pkg.ConfigError, C.load_layer, {"schema": "INV37_CONFIG/9"}, layer="site")

    def test_inline_secret_rejected(self):
        with self.assertRaises(pkg.ConfigError) as cm:
            C.load_layer({"security": {"signing_key": "abcd"}}, layer="site")
        self.assertIn("inline secret", cm.exception.message)

    def test_invariant_cannot_be_weakened(self):
        env_layer = C.load_layer({"security": {"require_authentication": False}}, layer="env")
        self.assertRaises(pkg.ConfigError, C.merge, ("env", env_layer))

    def test_not_overridable(self):
        self.assertRaises(pkg.ConfigError, C.load_layer, {"limits": {"max_chunks": 5}}, layer="site")

    def test_prod_requires_key_and_checkpoint_dir(self):
        cfg = C.ConfigManager(check_fs=False).build([], author="t")
        codes = {f.code for f in cfg.findings if f.severity == "fatal"}
        self.assertTrue({"key_file_missing", "checkpoint_dir_missing"} <= codes, codes)
        self.assertFalse(cfg.admission_allowed)
        self.assertRaises(pkg.CodedError, pkg.BulkDataPlane, cfg, keyring=self.env.ring)

    def test_memory_budget_combination(self):
        eff = C.merge(("s", C.load_layer({"limits": {"max_concurrent_transfers": 100, "max_object_bytes": "1GiB",
                                                      "host_memory_budget": "8GiB"}}, layer="s")))
        self.assertIn("memory_budget_exceeded", {f.code for f in C.preflight(eff, check_fs=False)})

    def test_state_in_package_is_fatal(self):
        eff = dict(self.env.cfg.effective)
        eff["checkpoint.directory"] = str(PKG_DIR)
        self.assertIn("state_in_package", {f.code for f in C.preflight(eff)})

    def test_key_file_permissions(self):
        os.chmod(self.env.key_file, 0o644)
        self.assertIn("key_file_permissions", {f.code for f in C.preflight(self.env.cfg.effective)})

    def test_zero_copy_required_but_unavailable(self):
        eff = dict(self.env.cfg.effective)
        eff["transport.require_zero_copy"] = True
        self.assertIn("zero_copy_unavailable", {f.code for f in C.preflight(eff, probe={"shared_memory": False})})
        eff["transport.require_zero_copy"] = False
        sev = {f.code: f.severity for f in C.preflight(eff, probe={"shared_memory": False})}
        self.assertEqual(sev.get("copy_fallback"), "degraded")

    def test_encryption_required_fails_closed(self):
        eff = dict(self.env.cfg.effective)
        eff["security.require_encryption_at_rest"] = True
        self.assertIn("encryption_unavailable", {f.code for f in C.preflight(eff)})

    def test_preflight_is_deterministic_and_side_effect_free(self):
        before = sorted(os.listdir(self.env.dir))
        a = C.preflight(self.env.cfg.effective, probe=self.env.caps)
        b = C.preflight(self.env.cfg.effective, probe=self.env.caps)
        self.assertEqual([vars(x) for x in a], [vars(x) for x in b])
        self.assertEqual(before, sorted(os.listdir(self.env.dir)))

    def test_same_artifact_multiple_profiles(self):
        dev = self.env.mgr.dry_run([("env", C.load_layer({"profile": "dev", "security": {"key_file": str(self.env.key_file)},
                                                          "checkpoint": {"enabled": False},
                                                          "limits": {"host_memory_budget": "64GiB"}}, layer="env"))])
        self.assertTrue(dev.admission_allowed)
        self.assertNotEqual(dev.digest, self.env.cfg.digest)
        self.assertEqual(dev.provenance["package_version"], pkg.__version__)

    def test_provenance_and_digest(self):
        prov = self.env.cfg.provenance
        for k in ("digest", "author", "activated_at", "package_version", "config_schema", "layers"):
            self.assertIn(k, prov)
        self.assertTrue(prov["digest"].startswith("sha256:"))
        self.assertEqual(C.digest(self.env.cfg.effective), self.env.cfg.digest)

    def test_redaction(self):
        r = C.redacted(self.env.cfg.effective)
        self.assertEqual(r["security.key_file"], "<redacted-path>")

    def test_activation_rollback(self):
        mgr = self.env.mgr
        first = mgr.active
        cand = mgr.build([("site", C.load_layer({"security": {"key_file": str(self.env.key_file)},
                                                 "checkpoint": {"directory": str(self.env.dir / "ck")},
                                                 "limits": {"host_memory_budget": "64GiB", "max_concurrent_transfers": 4}},
                                                layer="site"))], author="op")
        with self.assertRaises(pkg.ConfigError):
            mgr.activate(cand, health_check=lambda c: False)
        self.assertIs(mgr.active, first)  # automatic rollback
        mgr.activate(cand, health_check=lambda c: True)
        self.assertIs(mgr.active, cand)
        mgr.rollback(author="op")  # operator rollback
        self.assertIs(mgr.active, first)
        hist = json.loads((self.env.dir / "config-history.json").read_text())
        self.assertEqual([h["action"] for h in hist], ["activated", "auto_rollback", "activated", "operator_rollback"])

    def test_fatal_candidate_never_activates(self):
        bad = self.env.mgr.build([("s", C.load_layer({"retry": {"base_delay": "20s", "max_delay": "1s"}}, layer="s"))],
                                 author="x")
        self.assertRaises(pkg.ConfigError, self.env.mgr.activate, bad)
        self.assertIsNot(self.env.mgr.active, bad)

    def test_config_path_traversal(self):
        with tempfile.TemporaryDirectory() as root, tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            fh.write("{}")
        try:
            self.assertRaises(pkg.ConfigError, C.load_file, fh.name, layer="site", root=root)
        finally:
            os.unlink(fh.name)

    def test_example_profiles_validate(self):
        for p in sorted((PKG_DIR / "config" / "profiles").glob("*.json")):
            layer = C.load_file(p, layer=p.stem)
            eff = C.merge((p.stem, layer))
            fatal = [f.code for f in C.preflight(eff, check_fs=False) if f.severity == "fatal"
                     and f.code not in ("key_file_missing", "checkpoint_dir_missing")]
            self.assertEqual(fatal, [], p.name)


if __name__ == "__main__":
    unittest.main()
