import hashlib, json, pathlib, unittest
from inv65_capability_providers.errors.mapping import ProviderFault
from inv65_capability_providers.registry.model import negotiate
from inv65_capability_providers.schemas import load, names, validate

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIX = ROOT / "conformance/fixtures"


class GoldenVectors(unittest.TestCase):
    def test_all_schemas_load_and_use_only_enforced_keywords(self):
        self.assertGreaterEqual(len(names()), 12)
        for n in names():
            validate({}, load(n))  # raises SchemaError on unsupported keyword

    def test_valid_fixtures_pass(self):
        files = sorted((FIX / "v1").glob("*.json")); self.assertGreaterEqual(len(files), 9)
        for f in files:
            d = json.loads(f.read_text())
            self.assertEqual(validate(d["instance"], load(d["schema_name"])), [], f.name)

    def test_invalid_fixtures_fail(self):
        files = sorted((FIX / "invalid").glob("*.json")); self.assertGreaterEqual(len(files), 9)
        for f in files:
            d = json.loads(f.read_text())
            self.assertNotEqual(validate(d["instance"], load(d["schema_name"])), [], f.name)

    def test_every_schema_has_a_valid_fixture_or_is_runtime_generated(self):
        runtime_generated = {"audit_event", "authz_decision", "evidence_record"}  # covered by their own tests
        have = {p.stem for p in (FIX / "v1").glob("*.json")}
        self.assertEqual(set(names()) - have - runtime_generated, set())

    def test_schema_lock_matches(self):
        lock = json.loads((ROOT / "schemas/SCHEMA_LOCK.json").read_text())
        now = {n: hashlib.sha256((ROOT / "schemas" / n / "v1.json").read_bytes()).hexdigest() for n in names()}
        self.assertEqual(lock, now, "schema changed without updating SCHEMA_LOCK.json + fixtures + x-version")

    def test_mixed_version_matrix(self):
        m = json.loads((ROOT / "conformance/mixed_version_matrix.json").read_text())
        for c in m["cases"]:
            if c["expect"].startswith("PK_"):
                with self.assertRaises(ProviderFault):
                    negotiate(c["client"], c["server"])
            else:
                self.assertEqual(negotiate(c["client"], c["server"]), c["expect"])
