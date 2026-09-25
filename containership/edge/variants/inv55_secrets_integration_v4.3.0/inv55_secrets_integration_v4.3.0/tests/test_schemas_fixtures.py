"""Typed wire contracts + conformance fixture corpus (checklist #17, #21, #24).

Requires ``jsonschema`` (test-only dependency, pinned in requirements-test.txt)."""
from __future__ import annotations

import json
import unittest

from helpers import ROOT, SECRET, Env

try:
    import jsonschema
    from referencing import Registry, Resource
except ModuleNotFoundError:  # pragma: no cover
    jsonschema = None

SCHEMAS = ROOT / "inv55_secrets_integration" / "schemas"
PROTO = {"resolve": "PK_SECRET_RESOLVE/1", "use": "PK_SECRET_RESOLVE/1", "revoke": "PK_SECRET_RESOLVE/1",
         "rotate": "PK_SECRET_ROTATE/1", "retire": "PK_SECRET_ROTATE/1", "set_scope": "PK_SECRET_SCOPE/1"}
SCHEMA_OF = {"set_scope": "scope"}


@unittest.skipIf(jsonschema is None, "MANDATORY-SKIP: jsonschema not installed")
class Schemas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        docs = {p.name: json.loads(p.read_text()) for p in SCHEMAS.glob("*.json")}
        cls.registry = Registry().with_resources(
            [(name, Resource.from_contents(d)) for name, d in docs.items()])
        cls.docs = docs

    def validator(self, name):
        d = self.docs[name]
        jsonschema.Draft202012Validator.check_schema(d)
        return jsonschema.Draft202012Validator(d, registry=self.registry)

    def test_all_schemas_are_valid(self):
        for name in self.docs:
            jsonschema.Draft202012Validator.check_schema(self.docs[name])

    def test_fixture_corpus(self):
        fixtures = json.loads((ROOT / "fixtures" / "conformance" / "fixtures.json").read_text())
        for fx in fixtures:
            with self.subTest(fx["id"]):
                e = Env()
                e.seed()
                lease = e.resolve()["lease_id"]
                e.clock.advance(fx.get("advance_s", 0))
                req = dict(fx["request"])
                req.setdefault("protocol", PROTO[fx["op"]])
                if req.get("lease_id") == "$LEASE":
                    req["lease_id"] = lease
                req["credential"] = e.cred(fx["as"])
                base = SCHEMA_OF.get(fx["op"], fx["op"])
                if fx["expect"]["ok"] and fx["op"] != "set_scope":
                    self.validator(f"{base}.request.schema.json").validate(req)
                r = getattr(e.svc, fx["op"])(req)
                exp = fx["expect"]
                self.assertEqual(r["ok"], exp["ok"], r)
                if r["ok"]:
                    self.validator(f"{base}.response.schema.json").validate(r)
                    for k, v in exp.items():
                        if k != "ok":
                            self.assertEqual(r[k], SECRET if v == "$SECRET" else v)
                else:
                    self.validator("error.schema.json").validate(r)
                    self.assertEqual(r["error"]["code"], exp["code"])
                    self.assertNotIn(SECRET, json.dumps(r))

    def test_every_error_code_documented(self):
        from inv55_secrets_integration.errors import ErrorCode
        doc = (ROOT / "docs" / "architecture" / "outcome-semantics.md").read_text()
        missing = [c.value.code for c in ErrorCode if c.value.code not in doc]
        self.assertEqual(missing, [], "outcome-semantics.md must list every public error code")


if __name__ == "__main__":
    unittest.main()
