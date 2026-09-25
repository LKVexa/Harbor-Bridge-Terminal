"""MC-06: normative schemas accept valid, reject invalid; runtime outputs conform."""

import json
import pathlib
import unittest

from tests._boot import PKG_DIR, mod

schema = mod("schema")
base = mod("backends.base")
claim = mod("claim")
own = mod("ownership")
model = mod("model")
FIX = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "schema"


def fixtures(prefix):
    for p in sorted(FIX.glob(prefix + "_*.json")):
        yield p.stem, json.loads(p.read_text())


class SchemaTest(unittest.TestCase):
    def test_valid_fixtures(self):
        n = 0
        for name, doc in fixtures("valid"):
            with self.subTest(name):
                schema.validate(doc)
                n += 1
        self.assertGreaterEqual(n, 6)

    def test_invalid_fixtures(self):
        n = 0
        for name, doc in fixtures("invalid"):
            with self.subTest(name):
                sid = "PK_VIRT_PRIMITIVE/2" if "version_mismatch" in name else None
                with self.assertRaises(schema.SchemaError):
                    schema.validate(doc, sid)
                n += 1
        self.assertGreaterEqual(n, 15)

    def test_nan_and_unknown_schema(self):
        _, doc = next(f for f in fixtures("valid") if f[0] == "valid_claim_ok")
        doc["acquired_at"] = float("nan")
        with self.assertRaises(schema.SchemaError):
            schema.validate(doc)
        with self.assertRaises(schema.SchemaError):
            schema.validate({"schema": "PK_VIRT_CLAIM/9"})

    def test_reference_validator_agrees(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed (installed in CI via .[test])")
        for kind in ("valid", "invalid"):
            for name, doc in fixtures(kind):
                s = schema.load(doc.get("schema") if doc.get("schema") in schema.SCHEMA_FILES else "PK_VIRT_PRIMITIVE/2")
                jsonschema.Draft202012Validator.check_schema(s)
                errs = list(jsonschema.Draft202012Validator(s).iter_errors(doc))
                if kind == "valid":
                    self.assertEqual(errs, [], name)

    def test_runtime_outputs_validate(self):
        r = base.ProbeResult(
            host="n",
            backend="linux-kvm",
            backend_version="1.0.0",
            platform="linux",
            architecture="x86_64",
            state="usable",
            reason="ok",
            facility_usable=True,
            virtualized=False,
            nesting_depth=0,
            cpu_capable=True,
        )
        schema.validate_probe_report(r.to_report())
        vp = model.VirtPrimitive("n", True, True, True)
        schema.validate(vp.report())
        schema.validate(vp.claim("vmm"))
        p = own.MemoryClaimProvider()
        c = p.acquire("vmm")
        resp = claim.ClaimManager.response(r, c)
        self.assertNotIn("token", resp)
        rec = p._load("hw-virt")
        schema.validate(rec, "PK_VIRT_OWNERSHIP/1")

    def test_schemas_are_package_data(self):
        for f in schema.SCHEMA_FILES.values():
            self.assertTrue((PKG_DIR / "schemas" / f).is_file(), f)


if __name__ == "__main__":
    unittest.main()
