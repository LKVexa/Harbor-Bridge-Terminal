"""MC-28 compatibility: schema evolution rules, state migration window, declared runtime."""
from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import helpers  # noqa: E402,F401

from pln05_elasticity_plane import wire  # noqa: E402
from pln05_elasticity_plane.state import migrate  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("schema_compat", ROOT / "tools" / "schema_compat.py")
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)


class Compat(unittest.TestCase):
    def test_current_schemas_compatible_with_released_baseline(self):
        res = sc.check(ROOT / "compatibility" / "baseline-4.2.0", ROOT / "schemas")
        self.assertEqual({k: v for k, v in res.items() if v}, {})

    def test_checker_detects_breaking_changes(self):
        base = wire.SCHEMAS["PK_DEMAND"]
        for mutate, expect in [
            (lambda s: s["properties"].pop("confidence"), "removed"),
            (lambda s: s["required"].append("confidence"), "required"),
            (lambda s: s["properties"]["utilisation"].__setitem__("maximum", 10), "maximum tightened"),
            (lambda s: s["properties"]["seq"].__setitem__("type", "number"), "type changed"),
        ]:
            new = copy.deepcopy(base)
            mutate(new)
            self.assertTrue(any(expect in m for m in sc.compare(base, new)), expect)
        widened = copy.deepcopy(base)
        widened["properties"]["utilisation"]["maximum"] = 2000
        widened["properties"]["x_new_optional"] = {"type": "string"}
        self.assertEqual(sc.compare(base, widened), [])

    def test_state_window(self):
        v1 = {"schema": "PLN05_STATE/1", "current": 1, "limits": {"floor": 0, "ceiling": 2, "scale_up_at": 0.7,
              "scale_down_at": 0.2, "grace_samples": 2}}
        self.assertEqual(migrate(v1)["schema"], "PLN05_STATE/2")

    def test_declared_runtime(self):
        matrix = json.loads((ROOT / "compatibility" / "supported-versions.json").read_text())
        self.assertGreaterEqual(sys.version_info[:2], (3, 10))
        self.assertLess(sys.version_info[:2], (3, 14))
        self.assertIn("UNRESOLVED", matrix["framework"]["pk_core"]["status"])

    def test_peer_version_negotiation_mixed_fleet(self):
        self.assertEqual(wire.negotiate("PK_CAPACITY_TARGET", [1]), 1)
        self.assertEqual(wire.negotiate("PK_CAPACITY_TARGET", [0, 1, 7]), 1)


if __name__ == "__main__":
    unittest.main()
