"""Public-interface contract tests (C022, C026, C027, C029, C082).

Schema validation uses ``jsonschema`` (pinned in constraints.txt).  When it is not
installed the schema-validation tests SKIP and ``tools/ci.py`` reports the
``contract-schemas`` lane NOT RUN.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

from inv45_sfi_mechanisms.tests.support import PKG_DIR, Harness
from inv45_sfi_mechanisms.production import config, errors, sfi
from inv45_sfi_mechanisms.production.errors import SfiError

try:
    import jsonschema
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
except ImportError:  # pragma: no cover
    jsonschema = None

SCHEMAS = PKG_DIR / "schemas"
FIX = PKG_DIR / "fixtures"


def _registry_digest() -> str:
    rows = [[s.code, s.wire, s.category, s.retryable] for s in errors.REGISTRY.values()]
    return hashlib.sha256(json.dumps(sorted(rows)).encode()).hexdigest()


def _validator(name: str):
    reg = Registry()
    for p in SCHEMAS.glob("*.schema.json"):
        s = json.loads(p.read_text())
        reg = reg.with_resource(s["$id"], Resource.from_contents(s))
    return Draft202012Validator(json.loads((SCHEMAS / f"{name}.schema.json").read_text()), registry=reg)


@unittest.skipIf(jsonschema is None, "jsonschema not installed: contract-schemas lane NOT RUN")
class SchemaContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = Harness()
        cls.r = cls.h.submit()

    @classmethod
    def tearDownClass(cls):
        cls.h.close()

    def test_all_schemas_are_valid_2020_12_with_stable_ids(self):
        ids = set()
        for p in SCHEMAS.glob("*.schema.json"):
            s = json.loads(p.read_text())
            Draft202012Validator.check_schema(s)
            self.assertTrue(s["$id"].startswith("urn:pk:schema:"))
            self.assertNotIn(s["$id"], ids)
            ids.add(s["$id"])

    def test_live_outputs_conform(self):
        _validator("PK_SFI_PROOF_1").validate(self.r["proof"])
        _validator("PK_SFI_SEALED_DESCRIPTOR_1").validate(self.r["descriptor"])
        _validator("PK_SFI_HEALTH_1").validate(self.h.svc.health())
        _validator("PK_SFI_CONFIG_1").validate(self.h.svc.cfg)
        for line in (self.h.root / "audit" / "audit.jsonl").read_text().splitlines():
            _validator("PK_SFI_AUDIT_1").validate(json.loads(line))
        for code in errors.REGISTRY:
            _validator("PK_SFI_ERROR_1").validate(SfiError(code, "m", limit=1).as_dict())
        _validator("PK_SFI_ARTIFACT_STATEMENT_1").validate(self.h.sign(b"x")["statement"])

    def test_negative_documents_rejected(self):
        v = _validator("PK_SFI_PROOF_1")
        bad = dict(self.r["proof"], result="MAYBE")
        self.assertFalse(v.is_valid(bad))
        self.assertFalse(v.is_valid(dict(self.r["proof"], unknown_field=1)))
        self.assertFalse(v.is_valid(dict(self.r["proof"], artifact_bytes=-1)))
        d = _validator("PK_SFI_SEALED_DESCRIPTOR_1")
        self.assertFalse(d.is_valid(dict(self.r["descriptor"], schema="PK_SFI_SEALED_DESCRIPTOR/2")))
        self.assertFalse(d.is_valid({k: v for k, v in self.r["descriptor"].items() if k != "mac"}))
        q = _validator("PK_SFI_QUARANTINE_REQUEST_1")
        self.assertTrue(q.is_valid({"schema": "PK_SFI_QUARANTINE_REQUEST/1", "scope": "tenant", "target": "t1",
                                    "action": "freeze", "reason": "x"}))
        self.assertFalse(q.is_valid({"schema": "PK_SFI_QUARANTINE_REQUEST/1", "scope": "tenant", "target": "t1",
                                     "action": "delete", "reason": "x"}))
        s = _validator("PK_SFI_SUBMIT_REQUEST_1")
        self.assertFalse(s.is_valid({"schema": "PK_SFI_SUBMIT_REQUEST/1", "tenant": "T1!", "workload": "w",
                                     "version": 1, "artifact_b64": "", "signed_statement": {}}))


class ErrorContractTest(unittest.TestCase):
    def test_registry_pinned(self):
        pin = (PKG_DIR / "schemas" / "ERROR_REGISTRY.pin").read_text().strip()
        self.assertEqual(_registry_digest(), pin, "error registry changed: regenerate docs and pin deliberately")

    def test_generated_catalog_matches_registry(self):
        self.assertEqual((PKG_DIR / "docs" / "security" / "ERROR_CATALOG.md").read_text(), errors.registry_markdown())

    def test_error_codes_survive_optimised_mode(self):
        code = ("import sys; sys.path.insert(0, %r); from inv45_sfi_mechanisms.production import sfi, builder;"
                "from inv45_sfi_mechanisms.production.errors import SfiError\n"
                "try:\n sfi.verify(builder.rw_module(), sfi.Profile(65536,16))\n"
                "except SfiError as e: print(e.code)") % str(PKG_DIR.parent)
        out = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), "SFI_UNMASKED_ACCESS", out.stderr)


class FixtureConformanceTest(unittest.TestCase):
    """Runs the canonical fixture suite against this implementation (C029)."""

    def test_manifest_cases(self):
        m = json.loads((FIX / "MANIFEST.json").read_text())
        self.assertGreaterEqual(len(m["cases"]), 20)
        for case in m["cases"]:
            with self.subTest(case["name"]):
                data = (FIX / case["file"]).read_bytes()
                self.assertEqual(sfi.sha256_hex(data), case["input_sha256"])
                prof = sfi.Profile(**{k: tuple(v) if isinstance(v, list) else v for k, v in case["profile"].items()})
                try:
                    if case["stage"] == "rewrite+verify":
                        data = sfi.rewrite(data, prof).artifact
                        self.assertEqual(sfi.sha256_hex(data), case["rewritten_sha256"])
                    proof = sfi.verify(data, prof)
                    self.assertEqual(case["expect"], "VERIFIED")
                    self.assertEqual(sfi.proof_digest(proof), case["proof_sha256"])
                except SfiError as e:
                    self.assertEqual(e.code, case["expect"])

    def test_generator_is_deterministic(self):
        before = {p: p.read_bytes() for p in FIX.rglob("*") if p.is_file()}
        out = subprocess.run([sys.executable, str(PKG_DIR / "tools" / "gen_fixtures.py")], capture_output=True,
                             text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        after = {p: p.read_bytes() for p in FIX.rglob("*") if p.is_file()}
        self.assertEqual(before, after)


class CompatibilityPolicyTest(unittest.TestCase):
    """C027 / C016: version handling is explicit match + deterministic UNSUPPORTED_VERSION."""

    def test_versions_supported_matrix(self):
        compat = json.loads((PKG_DIR / "release" / "compatibility.json").read_text())
        self.assertIn(sfi.PROFILE_ID, compat["profiles"])
        self.assertIn(config.CONFIG_SCHEMA, compat["schemas"]["config"])
        with self.assertRaises(SfiError) as cm:
            sfi.Profile(65536, 16, profile_id="PK-SFI-WASM32-MVP-0")
        self.assertEqual(cm.exception.code, "SFI_UNSUPPORTED_VERSION")


if __name__ == "__main__":
    unittest.main()
