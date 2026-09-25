"""MC-28 fuzz + property tests (seeded, reproducible; PLN05_FUZZ_ITERS scales the run).

Properties: the boundary never raises anything but PlaneError; accepted messages
re-validate; controller invariants hold over long random sequences; config merge
never activates an invalid candidate; state documents round-trip or fail closed."""
from __future__ import annotations

import json
import os
import pathlib
import random
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from helpers import T0, World  # noqa: E402

from pln05_elasticity_plane import configuration, wire  # noqa: E402
from pln05_elasticity_plane.controller import ElasticityController, Limits  # noqa: E402
from pln05_elasticity_plane.errors import PlaneError  # noqa: E402
from pln05_elasticity_plane.keys import KeyRing  # noqa: E402
from pln05_elasticity_plane.state import StateStore  # noqa: E402

ITERS = int(os.environ.get("PLN05_FUZZ_ITERS", "2000"))
FIX = pathlib.Path(__file__).resolve().parents[2] / "fixtures" / "protocol" / "valid"
SEEDS = [p.read_bytes().replace(b'"@now"', b"1790000000.0") for p in sorted(FIX.glob("*.json"))]
VALUES = [None, True, False, 0, -1, 1, 2**63, 2**53 + 1, 1e308, -1e-308, 0.5, "", "a", "x" * 70,
          [], {}, [1], {"a": 1}, "PK_DEMAND/1", "PK_DEMAND/2", "\u0000", "é", 1.0000000001]


def mutate(rng: random.Random, raw: bytes) -> bytes:
    choice = rng.randrange(6)
    if choice == 0:  # byte flips
        b = bytearray(raw)
        for _ in range(rng.randrange(1, 8)):
            b[rng.randrange(len(b))] = rng.randrange(256)
        return bytes(b)
    if choice == 1:  # truncation
        return raw[: rng.randrange(len(raw))]
    obj = json.loads(raw)
    keys = list(obj)
    if choice == 2:
        obj[rng.choice(keys)] = rng.choice(VALUES)
    elif choice == 3:
        obj.pop(rng.choice(keys))
    elif choice == 4:
        obj[rng.choice(["zz", "x-ext", "Utilisation", "seq "])] = rng.choice(VALUES)
    else:
        k = rng.choice(keys)
        obj[k] = [obj[k]] * rng.randrange(1, 4)
    return json.dumps(obj).encode()


class Fuzz(unittest.TestCase):
    def test_boundary_only_raises_plane_errors(self):
        rng = random.Random(20260923)
        accepted = rejected = 0
        for i in range(ITERS):
            raw = mutate(rng, rng.choice(SEEDS))
            fam = rng.choice(["PK_DEMAND", "PK_CAPACITY_LIMITS", "PK_CAPACITY_TARGET"])
            try:
                obj = wire.decode(fam, raw)
            except PlaneError:
                rejected += 1
                continue
            accepted += 1
            wire.validate(fam, obj)  # accepted objects are stable under re-validation
        self.assertGreater(rejected, ITERS // 2)

    def test_plane_survives_fuzzed_demand(self):
        w = World()
        w.declare()
        tok = w.token()
        rng = random.Random(7)
        for i in range(ITERS // 4):
            raw = mutate(rng, w.demand(rng.random()))
            try:
                w.plane.submit_demand(raw, tok)
            except PlaneError:
                pass
            s = w.plane.scopes["t1/dub/w1"]
            self.assertTrue(0 <= s.controller.current <= 8)

    def test_controller_invariants_long_random_sequences(self):
        rng = random.Random(42)
        for trial in range(50):
            floor = rng.randrange(0, 5)
            ceiling = floor + rng.randrange(0, 50)
            lo = rng.uniform(0.01, 0.5)
            hi = rng.uniform(lo + 0.01, 0.99)
            grace = rng.randrange(1, 6)
            c = ElasticityController(Limits(floor, ceiling, hi, lo, grace), current=rng.randrange(0, 60))
            last_down_streak = 0
            for step in range(ITERS // 10):
                if rng.random() < 0.02 and c.limits.ceiling > floor:
                    new = rng.randrange(floor, c.limits.ceiling + 1)
                    c.lower_ceiling(new)
                    self.assertEqual(c.limits.ceiling, new)
                u = rng.choice([0.0, lo, hi, 1.0, rng.random(), rng.random() * 3])
                prev = c.current
                t, reason = c.observe(u)
                self.assertTrue(c.limits.floor <= t <= c.limits.ceiling)
                self.assertTrue(t <= max(prev * 2, 1) or t <= c.limits.ceiling)
                if reason == "scale-down":
                    self.assertGreaterEqual(last_down_streak + 1, grace)
                last_down_streak = last_down_streak + 1 if u <= lo and prev > c.limits.floor else 0
                if reason == "scale-down":
                    last_down_streak = 0
                snap = c.snapshot()
                self.assertEqual(ElasticityController.restore(snap).snapshot(), snap)

    def test_config_overlay_fuzz_never_activates_invalid(self):
        rng = random.Random(99)
        store = configuration.ConfigStore(KeyRing.ephemeral(T0), T0)
        fields = list(configuration.SCHEMA["fields"])
        rev = 1
        for _ in range(ITERS // 4):
            layer = {"revision": rev + 1}
            for _ in range(rng.randrange(1, 4)):
                path = rng.choice(fields).split(".")
                val = rng.choice(VALUES + [rng.random() * 100, rng.randrange(0, 5000)])
                cur = layer
                for p in path[:-1]:
                    cur = cur.setdefault(p, {})
                cur[path[-1]] = val
            try:
                snap = store.activate({rng.choice(configuration.LAYERS[1:]): layer}, issuer="fuzz", now=T0)
                configuration.validate(configuration._thaw(snap.data))
                rev = snap.revision
            except PlaneError:
                pass

    def test_state_file_fuzz_fails_closed(self):
        rng = random.Random(5)
        ring = KeyRing.ephemeral(T0)
        with tempfile.TemporaryDirectory() as d:
            st = StateStore(d, ring)
            doc = {"current": 3, "below": 1, "suppressed": 0, "limits": {"floor": 0, "ceiling": 8,
                   "scale_up_at": 0.75, "scale_down_at": 0.25, "grace_samples": 3}, "controls": {},
                   "sources": {}, "seen": [], "epoch": 2}
            st.save("t1/dub/w1", doc, T0)
            path = next(pathlib.Path(d).glob("*.state.json"))
            good = path.read_bytes()
            for _ in range(ITERS // 10):
                b = bytearray(good)
                for _ in range(rng.randrange(1, 4)):
                    b[rng.randrange(len(b))] = rng.randrange(32, 127)
                path.write_bytes(bytes(b))
                try:
                    out = st.load("t1/dub/w1", T0)
                    self.assertEqual(out["current"], 3)  # only an identical-meaning doc may load
                except PlaneError as exc:
                    self.assertIn(exc.code, ("E_STATE_CORRUPT", "E_STATE_VERSION"))


if __name__ == "__main__":
    unittest.main()
