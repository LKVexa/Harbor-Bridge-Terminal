"""Public-interface contract tests (MC-071) driven by the reference fixture
corpus (MC-019) and the exported schemas (MC-012)."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import unittest

from support import TENANT, seeded

from inv62_edge_topology.production import wire
from inv62_edge_topology.production.schema import SchemaViolation, Validator

PKG = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = sorted((PKG / "fixtures").glob("*.json"))


class FixtureCorpusTest(unittest.TestCase):
    def test_corpus_is_present(self):
        self.assertGreaterEqual(len(FIXTURES), 20)

    def test_every_fixture_behaves_as_documented(self):
        for path in FIXTURES:
            fx = json.loads(path.read_text())
            with self.subTest(fixture=fx["id"]):
                svc, feed = seeded()
                if "raw" in fx:
                    raw = fx["raw"].encode("latin-1")
                else:
                    req = json.loads(json.dumps(fx["request"]))
                    if req["credential"] == "@CREDENTIAL":
                        role, _, node = (fx["role"] or "scheduler").partition(":")
                        req["credential"] = svc.authn.issue("fixture", role, [TENANT], node=node or None)
                    raw = wire.encode(req)
                resp = json.loads(svc.handle(raw))
                wire.validate_response(resp)
                exp = fx["expect"]
                self.assertEqual(resp["outcome"], exp["outcome"], resp)
                self.assertEqual(resp.get("error", {}).get("code"), exp.get("code"), resp)
                if "result_keys" in exp:
                    self.assertEqual(sorted(resp["result"]), exp["result_keys"])


class ExportedSchemaTest(unittest.TestCase):
    def test_exported_schemas_in_sync(self):
        r = subprocess.run([sys.executable, str(PKG / "tools" / "export_schemas.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_exported_schemas_validate_fixtures_independently(self):
        validators = {name: Validator(json.loads((PKG / "schemas" / f"{name.lower()}.request.schema.json").read_text()))
                      for name in wire.SUPPORTED}
        for path in FIXTURES:
            fx = json.loads(path.read_text())
            if "request" not in fx:
                continue
            fam = fx["request"]["protocol"].split("/")[0]
            ok = fx["expect"].get("code") not in ("TOPO.INVALID_REQUEST",)
            with self.subTest(fixture=fx["id"]):
                req = dict(fx["request"], credential="x" * 32)
                if ok:
                    validators[fam].validate(req)
                else:
                    with self.assertRaises(SchemaViolation):
                        validators[fam].validate(req)

    def test_validator_refuses_unknown_keywords(self):
        with self.assertRaises(ValueError):
            Validator({"type": "object", "patternProperties": {}})


if __name__ == "__main__":
    unittest.main()
