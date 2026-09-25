"""MC-08 contract tests: every fixture goes through the real boundary (bytes -> wire.decode
or the live plane), never through internal constructors."""
from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from helpers import World  # noqa: E402

from pln05_elasticity_plane import wire  # noqa: E402
from pln05_elasticity_plane.errors import PlaneError  # noqa: E402

FIX = pathlib.Path(__file__).resolve().parents[2] / "fixtures" / "protocol"
MANIFEST = json.loads((FIX / "manifest.json").read_text())


def materialise(data: bytes, now: float) -> bytes:
    if data.startswith(b"b64:"):
        return base64.b64decode(data[4:])
    return data.replace(b'"@now"', repr(now).encode())


class FixtureIntegrity(unittest.TestCase):
    def test_manifest_pins_every_file(self):
        seen = set()
        for group in ("valid", "invalid", "sequences"):
            for name, meta in MANIFEST[group].items():
                fname = meta.get("file", f"{name}.json")
                data = (FIX / group / fname).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), meta["sha256"], f"{group}/{fname} edited")
                seen.add(f"{group}/{fname}")
        on_disk = {f"{p.parent.name}/{p.name}" for p in FIX.glob("*/*")}
        self.assertEqual(on_disk, seen, "unmanifested fixture files")

    def test_every_constrained_field_has_a_negative_fixture(self):
        names = " ".join(MANIFEST["invalid"])
        for fam, fname in (("PK_DEMAND", "demand"), ("PK_CAPACITY_LIMITS", "limits")):
            for req in wire.SCHEMAS[fam]["required"]:
                if req == "schema":
                    continue
                self.assertIn(f"{fname}_missing_{req}", names)


class FixtureDecode(unittest.TestCase):
    NOW = 1_790_000_000.0

    def test_valid_fixtures_decode_and_round_trip(self):
        for name, meta in MANIFEST["valid"].items():
            with self.subTest(name):
                raw = materialise((FIX / "valid" / f"{name}.json").read_bytes(), self.NOW)
                obj = wire.decode(meta["family"], raw)
                again = wire.decode(meta["family"], wire.encode(meta["family"], obj))
                self.assertEqual(obj, again)  # no semantic drift through a round trip

    def test_invalid_fixtures_fail_with_expected_code(self):
        for name, meta in MANIFEST["invalid"].items():
            with self.subTest(name):
                raw = materialise((FIX / "invalid" / meta["file"]).read_bytes(), self.NOW)
                with self.assertRaises(PlaneError) as cm:
                    wire.decode(meta["family"], raw)
                self.assertEqual(cm.exception.code, meta["expect"])
                # errors never echo payload bytes
                self.assertNotIn("NaN", str(cm.exception))


class FixtureSequences(unittest.TestCase):
    def test_sequences_against_live_plane(self):
        for name, meta in MANIFEST["sequences"].items():
            seq = json.loads((FIX / "sequences" / f"{name}.json").read_text())
            with self.subTest(name):
                w = World()
                w.declare()
                tok = w.token()
                got = []
                for m in seq["messages"]:
                    kw = dict(m)
                    age = kw.pop("age_s", 0)
                    raw = w.demand(0.5, observed_at=w.clock() - age, **kw)
                    try:
                        w.plane.submit_demand(raw, tok)
                        got.append("OK")
                    except PlaneError as exc:
                        got.append(exc.code)
                self.assertEqual(got, seq["expect"])


if __name__ == "__main__":
    unittest.main()
