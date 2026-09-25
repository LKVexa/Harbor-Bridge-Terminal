# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Configuration system, secret handling, integrity/SBOM, license, dependency pinning (GAP-001, 023-026, 071)."""
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from .. import config, integrity
from ..deps import _parse, pk_core_status
from ..errors import ConfigInvalid
from ..secret_refs import redact, resolve

PKG = Path(__file__).resolve().parents[1]


class ConfigTest(unittest.TestCase):
    def test_all_contexts_validate_and_differ(self):
        digests = {c: config.digest(config.load(c)) for c in ("cloud", "datacenter", "near-edge", "far-edge")}
        self.assertEqual(len(set(digests.values())), 4)
        with self.assertRaises(ConfigInvalid):
            config.load("moon")

    def test_secure_defaults(self):
        cfg = config.load()
        self.assertFalse(cfg["rollout"]["allow_model_for_hardware_workloads"])
        self.assertEqual(cfg["rollout"]["stage"], "off")

    def test_production_fail_closed(self):
        with self.assertRaises(ConfigInvalid):
            config.load(mode="production")  # no minting key ref
        with self.assertRaises(ConfigInvalid):
            config.load(mode="production", extra={"secret_refs": {"minting_key": "env:K"},
                                                   "telemetry": {"log_level": "debug"}})
        with self.assertRaises(ConfigInvalid):
            config.load(mode="production", extra={"secret_refs": {"minting_key": "env:K"},
                                                   "rollout": {"allow_model_for_hardware_workloads": True}})
        cfg = config.load(mode="production", extra={"secret_refs": {"minting_key": "env:K"}})
        self.assertEqual(cfg["mode"], "production")

    def test_inline_secrets_refused(self):
        with self.assertRaises(ConfigInvalid):
            config.load(extra={"auth": {"minting_key": "0123456789abcdef0123456789abcdef"}})
        with self.assertRaises(ConfigInvalid):
            config.load(extra={"secret_refs": {"minting_key": "raw-value"}})
        with self.assertRaises(ConfigInvalid):
            config.load(extra={"limits": {"max_inflight": 0}})
        with self.assertRaises(ConfigInvalid):
            config.load(extra={"unknown_knob": 1})

    def test_atomic_activation_provenance_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            st = config.ConfigStore(Path(d) / "active.json")
            a = st.activate(config.load("cloud"), author="alice", reason="initial")
            self.assertTrue(a["digest"].startswith("sha256:"))
            st.activate(config.load("far-edge"), author="bob", reason="edge")
            bad = config.load("cloud")
            bad["limits"] = {"max_inflight": -1}
            with self.assertRaises(ConfigInvalid):
                st.activate(bad, author="eve", reason="bad")
            self.assertEqual(st.active["deployment_context"], "far-edge")  # untouched on failure
            r = st.rollback(author="bob", reason="edge regression")
            self.assertEqual(st.active["deployment_context"], "cloud")
            self.assertEqual(r["version"], 3)
            reloaded = config.ConfigStore(Path(d) / "active.json")
            self.assertEqual([h["author"] for h in reloaded.history], ["alice", "bob", "bob"])


class SecretTest(unittest.TestCase):
    def test_resolve_env_and_file(self):
        os.environ["INV30_TEST_KEY"] = "x" * 40
        self.assertEqual(len(resolve("env:INV30_TEST_KEY")), 40)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "k"
            p.write_text("y" * 40)
            os.chmod(p, 0o644)
            if os.name == "posix":
                with self.assertRaises(ConfigInvalid):
                    resolve(f"file:{p}")
            os.chmod(p, stat.S_IRUSR | stat.S_IWUSR)
            self.assertEqual(len(resolve(f"file:{p}")), 40)
        os.environ["INV30_TEST_KEY"] = "short"
        with self.assertRaises(ConfigInvalid):
            resolve("env:INV30_TEST_KEY")

    def test_redaction(self):
        r = redact({"minting_key": "abc", "minting_key_ref": "env:K", "note": "blob " + "ab" * 20,
                    "nested": [{"password": "p"}]})
        self.assertEqual(r["minting_key"], "[REDACTED]")
        self.assertEqual(r["minting_key_ref"], "env:K")
        self.assertIn("[REDACTED-HEX]", r["note"])
        self.assertEqual(r["nested"][0]["password"], "[REDACTED]")


class IntegrityTest(unittest.TestCase):
    def test_manifest_detects_tamper(self):
        m = integrity.manifest()
        self.assertEqual(integrity.verify_tree(PKG, m), [])
        m2 = json.loads(json.dumps(m))
        k = next(iter(m2["files"]))
        m2["files"][k] = "0" * 64
        self.assertEqual(integrity.verify_tree(PKG, m2), [f"modified: {k}"])

    def test_signature(self):
        m = integrity.manifest()
        sig = integrity.sign_manifest(m, b"S" * 32)
        self.assertTrue(integrity.verify_manifest(m, sig, b"S" * 32))
        self.assertFalse(integrity.verify_manifest(m, sig, b"T" * 32))

    def test_sbom_names_pk_core_digest(self):
        st = pk_core_status()
        s = integrity.sbom("4.3.0", st["version"], integrity.pk_core_digest())
        self.assertEqual(s["bomFormat"], "CycloneDX")
        if st["state"] == "ok":
            self.assertEqual(s["components"][1]["name"], "pk_core")
            self.assertEqual(len(s["components"][1]["hashes"][0]["content"]), 64)

    def test_license_headers_and_files(self):
        self.assertEqual(integrity.license_check(), [])
        self.assertTrue((PKG / "LICENSE").exists() and (PKG / "NOTICE").exists())

    def test_version_parse_and_pin(self):
        self.assertEqual(_parse("4.0.0"), (4, 0, 0))
        self.assertEqual(_parse("5.0.0rc1"), (5, 0, 0))
        text = (PKG / "pyproject.toml").read_text()
        self.assertIn('"pk-core>=4.0.0,<5.0.0"', text)
        self.assertIn('version = "4.3.0"', text)


if __name__ == "__main__":
    unittest.main()


class TraceabilityTest(unittest.TestCase):
    def test_matrix_complete_and_paths_exist(self):
        from .. import traceability
        m = traceability.build()
        self.assertEqual(traceability.check(m), [])
        committed = json.loads((PKG / "docs" / "TRACEABILITY.json").read_text())
        self.assertEqual(committed, m, "docs/TRACEABILITY.json is stale; run traceability.py")


class OwnersAndScanTest(unittest.TestCase):
    def test_owners_metadata_valid(self):
        o = json.loads((PKG / "OWNERS.json").read_text())
        self.assertTrue(o["accountable_owner"]["name"])
        for k in ("contract_change", "backend_change", "vulnerability_response", "emergency_disable",
                  "production_certification"):
            self.assertEqual(set(o["raci"][k]), {"R", "A", "C", "I"})
        self.assertIn("@", (PKG / "CODEOWNERS").read_text())

    def test_secret_scan_clean_and_detects(self):
        self.assertEqual(integrity.secret_scan(), [])
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "leak.py").write_text('minting_key = "0123456789abcdef0123456789abcdef"\n')
            self.assertEqual(len(integrity.secret_scan(Path(d))), 1)

    def test_waiver_gate(self):
        from ..release import expired_waivers
        self.assertEqual(expired_waivers("2026-09-23"), [])
