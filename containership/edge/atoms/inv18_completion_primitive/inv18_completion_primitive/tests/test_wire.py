"""Wire contracts, versioning, limits, fixtures, reference example (C016, C021, C022, C027, C028, C029)."""
import json
import subprocess
import sys
import unittest

from _util import m, PKG_DIR, ROOT

wire = m("wire")
errors = m("errors")


class SchemaTest(unittest.TestCase):
    def test_generated_schema_files_match_source(self):
        """REQ: C022 C021"""
        for name, sch in wire.SCHEMAS.items():
            p = PKG_DIR / "schemas" / (name.replace("/", "_v") + ".json")
            self.assertTrue(p.exists(), p)
            self.assertEqual(json.loads(p.read_text()), sch)

    def test_contract_shapes(self):
        """REQ: C022 INV18-CMP-001"""
        for n in ("PK_FUTURE/1", "PK_FUTURE_RESOLVE/1", "PK_FUTURE_ABANDON/1", "PK_FUTURE_ERROR/1", "PK_FUTURE_STATUS/1"):
            s = wire.SCHEMAS[n]
            self.assertFalse(s["additionalProperties"])
            self.assertIn("schema", s["required"])
        ok = {"schema": "PK_FUTURE_RESOLVE/1", "future_id": "f1", "outcome": "ok", "value": 1, "epoch": 1,
              "idempotency_key": "k"}
        self.assertEqual(wire.validate(ok, "PK_FUTURE_RESOLVE/1"), [])
        bad_disc = dict(ok, outcome="error")
        self.assertTrue(wire.validate(bad_disc, "PK_FUTURE_RESOLVE/1"))
        both = dict(ok, error={})
        self.assertTrue(wire.validate(both, "PK_FUTURE_RESOLVE/1"))
        self.assertTrue(wire.validate(dict(ok, future_id="bad id!"), "PK_FUTURE_RESOLVE/1"))
        self.assertTrue(wire.validate(dict(ok, epoch=True), "PK_FUTURE_RESOLVE/1"))
        self.assertTrue(wire.validate(dict(ok, epoch=-1), "PK_FUTURE_RESOLVE/1"))

    def test_canonical_encoding(self):
        """REQ: C022"""
        a = wire.encode({"b": 1, "a": [1, 2], "c": "é"})
        self.assertEqual(a, '{"a":[1,2],"b":1,"c":"é"}'.encode())
        with self.assertRaises(ValueError):
            wire.encode({"x": float("nan")})


class LimitTest(unittest.TestCase):
    def test_size_checked_before_parse(self):
        """REQ: C028 C067"""
        doc = wire.encode({"schema": "PK_FUTURE/1", "future_id": "f", "value_type": "int", "epoch": 1})
        wire.decode(doc, "PK_FUTURE/1", max_bytes=len(doc))                 # exact boundary
        with self.assertRaises(errors.Rejected) as cm:
            wire.decode(doc, "PK_FUTURE/1", max_bytes=len(doc) - 1)         # boundary - 1 byte
        self.assertEqual(cm.exception.code, "RESOURCE_EXHAUSTED")
        with self.assertRaises(errors.Rejected) as cm:
            wire.decode(b"{" * 10_000_000, "PK_FUTURE/1", max_bytes=1024)  # would be expensive to parse
        self.assertEqual(cm.exception.code, "RESOURCE_EXHAUSTED")

    def test_identifier_length_limit(self):
        """REQ: C028"""
        base = {"schema": "PK_FUTURE/1", "value_type": "int", "epoch": 1}
        self.assertEqual(wire.validate(dict(base, future_id="a" * 128), "PK_FUTURE/1"), [])
        self.assertTrue(wire.validate(dict(base, future_id="a" * 129), "PK_FUTURE/1"))


class VersionTest(unittest.TestCase):
    def test_negotiation(self):
        """REQ: C027 C016 INV18-CMP-001"""
        self.assertEqual(wire.negotiate([1]), 1)
        self.assertEqual(wire.negotiate([1, 2, 3]), 1)      # newer peer that still speaks 1
        for offer, side in (([2, 3], "newer"), ([0], "older")):
            with self.assertRaises(errors.Rejected) as cm:
                wire.negotiate(offer)
            self.assertEqual(cm.exception.code, "INCOMPATIBLE_VERSION")
            self.assertIn(side, str(cm.exception))
        with self.assertRaises(errors.Rejected):
            wire.negotiate(["1"])

    def test_other_major_refused_not_downgraded(self):
        """REQ: C027 INV18-CMP-001"""
        doc = wire.encode({"schema": "PK_FUTURE/2", "future_id": "f", "value_type": "int", "epoch": 1})
        with self.assertRaises(errors.Rejected) as cm:
            wire.decode(doc, "PK_FUTURE/1", max_bytes=10_000)
        self.assertEqual(cm.exception.code, "INCOMPATIBLE_VERSION")

    def test_schema_extension_via_ext(self):
        """REQ: C027 C022"""
        doc = {"schema": "PK_FUTURE/1", "future_id": "f", "value_type": "int", "epoch": 1, "ext": {"new": 1}}
        self.assertEqual(wire.validate(doc, "PK_FUTURE/1"), [])
        self.assertTrue(wire.validate(dict(doc, new=1), "PK_FUTURE/1"))

    def test_api_snapshot_compatibility(self):
        """REQ: C016 C027"""
        out = subprocess.run([sys.executable, str(PKG_DIR / "tools/api_snapshot.py")], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_undeclared_break_detected(self):
        """REQ: C016"""
        sys.path.insert(0, str(PKG_DIR / "tools"))
        import api_snapshot
        old = json.loads((PKG_DIR / "conformance/API_SNAPSHOT.json").read_text())
        new = json.loads(json.dumps(old))
        new["error_codes"].remove("TIMEOUT")
        self.assertTrue(api_snapshot.check(old, new))           # removal without major bump
        new2 = json.loads(json.dumps(old)); new2["error_codes"].append("NEW_CODE")
        self.assertTrue(api_snapshot.check(old, new2))          # addition without minor bump
        new2["version"] = "4.4.0"
        self.assertFalse(api_snapshot.check(old, new2))


class FixtureTest(unittest.TestCase):
    def test_every_fixture_passes(self):
        """REQ: C029 C022 C026 C082"""
        res = m("fixtures_runner").run_all()
        self.assertGreaterEqual(len(res), 15)
        self.assertEqual([r for r in res if not r["passed"]], [])

    def test_fixtures_are_versioned_and_machine_readable(self):
        """REQ: C029"""
        for p in (PKG_DIR / "fixtures/v1").glob("*.json"):
            d = json.loads(p.read_text())
            self.assertEqual(d["schema"], "INV18_FIXTURE/1")
            self.assertEqual(d["contract_major"], 1)

    def test_reference_example_runs(self):
        """REQ: C029 C096"""
        out = subprocess.run([sys.executable, str(PKG_DIR / "examples/producer_consumer.py")],
                             capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("('ok', 42)", out.stdout)
        self.assertIn("FUTURE_ABANDONED", out.stdout)


if __name__ == "__main__":
    unittest.main()
