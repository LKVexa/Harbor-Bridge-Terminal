"""Stdlib checks that emitted interface shapes stay aligned with their JSON Schemas."""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("inv39_sandbox_shapes", PKG_DIR / "sandbox.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load sandbox.py test target")
sandbox = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sandbox
SPEC.loader.exec_module(sandbox)


class ContractShapeTest(unittest.TestCase):
    def schema(self, filename: str):
        return json.loads((PKG_DIR / "schemas" / filename).read_text(encoding="utf-8"))

    def test_profile_shape_has_every_required_schema_field(self):
        p = sandbox.SandboxProfile("svc", {"read", "write"})
        payload = p.as_dict()
        schema = self.schema("PK_SANDBOX_PROFILE-1.schema.json")
        self.assertEqual(payload["schema"], schema["properties"]["schema"]["const"])
        self.assertTrue(set(schema["required"]).issubset(payload))
        self.assertEqual(set(payload), set(schema["properties"]))

    def test_applied_shape_has_every_required_schema_field(self):
        p = sandbox.SandboxProfile("svc", {"read"})
        box = sandbox.Sandbox("p1", p)
        payload = box.start(readback=box.requested_state())
        schema = self.schema("PK_SANDBOX_APPLIED-1.schema.json")
        self.assertEqual(payload["schema"], schema["properties"]["schema"]["const"])
        self.assertTrue(set(schema["required"]).issubset(payload))
        self.assertEqual(set(payload), set(schema["properties"]))


if __name__ == "__main__":
    unittest.main()
