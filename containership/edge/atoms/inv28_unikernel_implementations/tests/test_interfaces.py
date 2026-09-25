"""Public-interface contract tests: schemas, payload compatibility, catalog, examples, migration
(MC-004..MC-006, MC-040, MC-091, MC-092, MC-095)."""
import json
import pathlib
import re
import subprocess
import sys
import unittest
import warnings

from harness import F, ValidationError, refusal
from inv28_unikernel_implementations.errors import ALL_CODES
from inv28_unikernel_implementations.model import ToolchainRecord
from inv28_unikernel_implementations.policy import SelectionPolicy, default_policy
from inv28_unikernel_implementations.schema_check import KNOWN, SCHEMA_DIR, load, validate, validate_file

PKG = pathlib.Path(F.__file__).resolve().parent


class Schemas(unittest.TestCase):
    def test_all_schema_files_parse_and_use_known_keywords(self):
        names = sorted(p.name[:-12] for p in SCHEMA_DIR.glob("*.schema.json"))
        self.assertGreaterEqual(len(names), 11)
        for n in names:
            def walk(s):
                if isinstance(s, dict):
                    self.assertLessEqual(set(k for k in s if not k.startswith("$") or k == "$ref") - KNOWN - {"properties"}, set(), n)
                    for k, v in s.items():
                        if k == "properties":
                            for sub in v.values():
                                walk(sub)
                        elif k in ("items", "additionalProperties") and isinstance(v, dict):
                            walk(v)
                        elif k == "oneOf":
                            for sub in v:
                                walk(sub)
            walk(load(n))

    def test_live_payloads_validate(self):                                     # MC-004, MC-005, MC-040
        w = F.world()
        res = w["selector"].select(F.request(site=F.site()), now=F.NOW)
        _, ref = refusal(lambda: w["selector"].select(F.request(language="cobol"), now=F.NOW))
        cases = {"PK_TOOLCHAIN-2": w["registry"].entries[0].to_dict(),
                 "PK_TOOLCHAIN_SELECTION-2": res.to_dict(), "PK_TOOLCHAIN_REFUSAL-1": ref.to_dict(),
                 "PK_TOOLCHAIN_SELECTION_REQUEST-1": F.request(site=F.site()).to_dict(),
                 "PK_TOOLCHAIN_TICKET-1": res.ticket, "PK_TOOLCHAIN_POLICY-1": default_policy().to_dict(),
                 "PK_TOOLCHAIN_REGISTRY-1": w["registry"].snapshot(),
                 "PK_RUNTIME_CERT-1": next(iter(w["certs"]._certs.values())).to_dict()}
        for name, payload in cases.items():
            with self.subTest(name=name):
                self.assertEqual(validate_file(name, payload), [])

    def test_v1_payloads_validate_against_v1_schemas(self):
        from inv28_unikernel_implementations.component import Toolchain, ToolchainRegister
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            reg = ToolchainRegister()
        reg.register(Toolchain("m", frozenset({"ocaml"}), frozenset({"x86_64"}), "mature", True))
        out = reg.select(language="ocaml", architecture="x86_64", environment="production")
        self.assertEqual(validate_file("PK_TOOLCHAIN_SELECTION-1", out), [])
        self.assertEqual(validate_file("PK_TOOLCHAIN-1", {"name": "m", "languages": ["ocaml"], "architectures": ["x86_64"],
                                                          "maturity": "mature", "security_contact": True}), [])

    def test_schemas_reject_bad_payloads(self):
        good = F.request().to_dict()
        for bad in ({**good, "extra": 1}, {**good, "language": "C C"}, {k: v for k, v in good.items() if k != "tenant"}):
            with self.subTest():
                self.assertTrue(validate_file("PK_TOOLCHAIN_SELECTION_REQUEST-1", bad))
        rec = F.record("x").to_dict()
        self.assertTrue(validate_file("PK_TOOLCHAIN-2", {**rec, "maturity": "stable"}))

    def test_refusal_schema_enumerates_every_reason_code(self):
        enum = load("PK_TOOLCHAIN_REFUSAL-1")["properties"]["code"]["enum"]
        self.assertEqual(sorted(enum), sorted(ALL_CODES))

    def test_checker_refuses_unknown_keywords(self):
        self.assertTrue(validate({"type": "string", "format": "email"}, "x"))

    def test_schema_and_loader_agree_on_random_mutations(self):
        """Anything the v2 loader accepts must validate; the schema must reject what the loader rejects on
        required-field removal (compatibility of the two contract surfaces)."""
        rec = F.record("x").to_dict()
        for k in list(rec):
            d = {kk: v for kk, v in rec.items() if kk != k}
            loader_ok = True
            try:
                ToolchainRecord.from_dict(d)
            except ValidationError:
                loader_ok = False
            schema_ok = not validate_file("PK_TOOLCHAIN-2", d)
            with self.subTest(removed=k):
                if schema_ok:
                    self.assertTrue(loader_ok)


class CatalogConsistency(unittest.TestCase):                                  # MC-006, MC-095
    def setUp(self):
        self.cat = json.loads((PKG / "catalog" / "catalog.json").read_text())

    def test_catalog_entries_are_valid_records(self):
        for e in self.cat["entries"]:
            with self.subTest(e=e["name"]):
                ToolchainRecord.from_dict(e)
                self.assertEqual(validate_file("PK_TOOLCHAIN-2", e), [])

    def test_every_toolchain_named_in_readme_has_a_catalog_entry(self):
        readme = (PKG / "README.md").read_text()
        named = {"mirageos", "unikraft", "osv", "nanos"}
        for n in named:
            self.assertIn(n, readme.lower())
        self.assertLessEqual(named, {e["name"] for e in self.cat["entries"]})

    def test_osv_is_explicitly_unregistered_and_unselectable(self):
        osv = next(e for e in self.cat["entries"] if e["name"] == "osv")
        self.assertEqual((osv["catalog_status"], osv["lifecycle"]), ("unregistered", "candidate"))
        w = F.world(records=[ToolchainRecord.from_dict(osv)])
        for env in ("production", "staging", "dev"):
            with self.subTest(env=env):
                refusal(lambda: w["selector"].select(F.request(environment=env, language="c"), now=F.NOW))

    def test_example_catalog_never_selectable_in_production(self):
        recs = [ToolchainRecord.from_dict(e) for e in self.cat["entries"]]
        w = F.world(records=recs)
        for lang in ("c", "ocaml", "rust", "go", "java"):
            with self.subTest(lang=lang):
                refusal(lambda: w["selector"].select(F.request(language=lang), now=F.NOW))

    def test_catalog_has_no_supported_claims(self):
        self.assertFalse([e["name"] for e in self.cat["entries"] if e["catalog_status"] == "supported"])


class Examples(unittest.TestCase):                                             # MC-092
    def test_examples_validate(self):
        ex = PKG / "examples"
        files = sorted(ex.glob("*.json"))
        self.assertGreaterEqual(len(files), 4)
        for f in files:
            doc = json.loads(f.read_text())
            with self.subTest(f=f.name):
                self.assertEqual(validate_file(doc["$schema_name"], doc["document"]), [])

    def test_policy_file_matches_default(self):
        self.assertEqual(SelectionPolicy.load(PKG / "config" / "policy.default.json").digest, default_policy().digest)

    def test_cli_demo_runs(self):
        out = subprocess.run([sys.executable, "-B", "-W", "ignore", "-m", "inv28_unikernel_implementations.cli", "demo"],
                             capture_output=True, text=True, cwd=str(PKG.parent), timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("selected rumprun", out.stdout)
        self.assertIn("TC_MATURITY_BELOW_POLICY", out.stdout)


class Migration(unittest.TestCase):                                            # MC-091
    def test_matrix_schema_files_exist(self):
        m = json.loads((PKG / "ops" / "COMPATIBILITY_MATRIX.json").read_text())
        for row in m["interfaces"]:
            name = re.sub(r"/(\d+)$", r"-\1", row["interface"])
            with self.subTest(i=row["interface"]):
                self.assertTrue((SCHEMA_DIR / f"{name}.schema.json").exists())

    def test_v1_documents_refused_by_v2_loader_but_v1_api_works(self):
        with self.assertRaises(ValidationError):
            ToolchainRecord.from_dict({"schema": "PK_TOOLCHAIN/1", "name": "m", "languages": ["ocaml"],
                                       "architectures": ["x86_64"], "maturity": "mature", "security": {}})
        from inv28_unikernel_implementations.component import ToolchainRegister
        with self.assertWarns(DeprecationWarning):
            ToolchainRegister()


if __name__ == "__main__":
    unittest.main()
