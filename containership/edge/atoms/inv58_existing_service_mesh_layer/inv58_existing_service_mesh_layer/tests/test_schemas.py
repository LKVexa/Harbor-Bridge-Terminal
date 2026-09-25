"""Validate declared JSON Schemas and representative interface payloads."""
from __future__ import annotations

import json
import pathlib
import unittest

try:
    import jsonschema
except ModuleNotFoundError:  # pragma: no cover - optional developer dependency
    jsonschema = None

ROOT = pathlib.Path(__file__).resolve().parents[1]


@unittest.skipIf(jsonschema is None, "jsonschema not installed")
class SchemaTest(unittest.TestCase):
    def _schema(self, name):
        data = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(data)
        return data

    def test_reconcile_schema(self):
        schema = self._schema("PK_MESH_RECONCILE-1.schema.json")
        jsonschema.validate(
            {
                "route": "orders->payments",
                "owner": "app",
                "app": 3,
                "mesh": 1,
                "budget": 3,
                "effective_attempts": 3,
                "reason": "app_preferred_for_idempotency",
            },
            schema,
        )

    def test_identity_schema(self):
        schema = self._schema("PK_MESH_IDENTITY-1.schema.json")
        jsonschema.validate(
            {
                "san": "spiffe://estate.local/ns/shop/sa/orders",
                "trust_domain": "estate.local",
                "runtime_identity": "runtime:ns/shop/sa/orders",
            },
            schema,
        )

    def test_bypass_schema(self):
        schema = self._schema("PK_MESH_BYPASS-1.schema.json")
        jsonschema.validate(
            {"src": "legacy-cron", "dst": "payments", "mtls": False, "bypass": True},
            schema,
        )


if __name__ == "__main__":
    unittest.main()
