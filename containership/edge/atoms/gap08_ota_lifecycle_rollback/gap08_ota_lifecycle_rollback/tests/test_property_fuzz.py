"""Component 31: property-based and fuzz testing (stdlib, seeded, reproducible).

Set ``GAP08_FUZZ_ITERS`` to scale (default 300 per property; CI nightly uses 20000).
Every failure prints its seed so it can be replayed exactly.
"""
from __future__ import annotations

import json
import os
import random
import string
import unittest

import _path  # noqa: F401
from gap08_ota_lifecycle_rollback import schema
from gap08_ota_lifecycle_rollback.common import canonical_json
from gap08_ota_lifecycle_rollback.errors import Gap08Error
from gap08_ota_lifecycle_rollback.rollout import Rollout, RolloutError, StateIntegrityError

ITERS = int(os.environ.get("GAP08_FUZZ_ITERS", "300"))
WEIRD = ["", " ", "\u0000", "‮", "ń", "𝔫𝔬𝔡𝔢", "../x", "a" * 5000, "NaN", "null", "퟿"]


def rnd_id(rng):
    if rng.random() < 0.2:
        return rng.choice(WEIRD)
    return "".join(rng.choice(string.ascii_letters + string.digits + "-_.:/") for _ in range(rng.randint(1, 12)))


def rnd_json(rng, depth=0):
    r = rng.random()
    if depth > 3 or r < 0.3:
        return rng.choice([None, True, False, 0, -1, 2 ** 63, 1.5, float("inf"), float("nan"), rnd_id(rng)])
    if r < 0.65:
        return [rnd_json(rng, depth + 1) for _ in range(rng.randint(0, 4))]
    return {rnd_id(rng): rnd_json(rng, depth + 1) for _ in range(rng.randint(0, 4))}


def verification(bundle):
    return {"schema": "PK_VERIFICATION/1", "verified": True, "kind": "bundle", "bundle": bundle}


class Properties(unittest.TestCase):
    def test_random_rollout_programs_preserve_invariants(self):
        """Random op sequences: invariants hold after every op; snapshot round-trips byte-exact."""
        for it in range(ITERS):
            seed = 1000 + it
            rng = random.Random(seed)
            n = rng.randint(1, 30)
            nodes = [f"n{i}" for i in range(n)]
            rng.shuffle(nodes)
            sizes, left = [], n
            while left:
                prev = sizes[-1] if sizes else 1
                s = max(prev, rng.randint(1, max(1, left)))
                if s > left or left - s < s:      # remainder would shrink: absorb it
                    s = left
                sizes.append(s)
                left -= s
            waves, i = [], 0
            for s in sizes:
                waves.append(nodes[i:i + s])
                i += s
            r = Rollout("v2", waves=waves)
            r.pin({x: "v1" for x in nodes})
            r.admit(verification("v2"))
            try:
                for _ in range(rng.randint(1, 10)):
                    op = rng.random()
                    if r.rolled_back:
                        break
                    if op < 0.6 and r.wave_index < len(r.waves):
                        wave = r.waves[r.wave_index]
                        off = set(rng.sample(wave, rng.randint(0, len(wave))))
                        healthy = rng.random() < 0.85
                        on_bundle = set(r.fleet_on("v2")) | (set(wave) - off)
                        fails = set(rng.sample(sorted(on_bundle), rng.randint(0, min(2, len(on_bundle))))) \
                            if not healthy else set()
                        r.run_wave(healthy=healthy, offline=off, rollback_failures=fails)
                    elif op < 0.8 and r.deferred:
                        pick = rng.sample(r.deferred, rng.randint(1, len(r.deferred)))
                        r.retry_deferred(healthy=rng.random() < 0.9, nodes=pick)
                    elif op < 0.85:
                        r.rollback(reason="random operator rollback")
                    snap = r.snapshot()                       # validates invariants + audit chain
                    again = Rollout.from_snapshot(json.loads(json.dumps(snap))).snapshot()
                    self.assertEqual(canonical_json(snap), canonical_json(again), f"seed={seed}")
                    schema.validate(snap, "PK_ROLLOUT_STATE/1")
                    # safety: never 'complete' with deferred nodes; failures always quarantined
                    self.assertFalse(r.state.value == "complete" and r.deferred, f"seed={seed}")
                    self.assertTrue(set(r.rollback_failed) <= set(r.quarantined), f"seed={seed}")
                    if r.rolled_back:
                        self.assertEqual(set(r.fleet_on("v2")), set(r.rollback_failed), f"seed={seed}")
            except RolloutError as exc:
                self.fail(f"seed={seed}: legal program raised {exc!r}")

    def test_hostile_snapshots_never_restore_silently(self):
        base = Rollout("v2", waves=[["a"], ["b", "c"]])
        base.pin({"a": "v1", "b": "v1", "c": "v1"})
        base.admit(verification("v2"))
        base.run_wave(healthy=True)
        good = base.snapshot()
        for it in range(ITERS):
            seed = 5000 + it
            rng = random.Random(seed)
            snap = json.loads(json.dumps(good))
            key = rng.choice(sorted(snap))
            snap[key] = rnd_json(rng)
            try:
                r = Rollout.from_snapshot(snap)
            except (RolloutError, StateIntegrityError, ValueError, TypeError, KeyError, AttributeError):
                continue
            # only acceptable if the mutation was a no-op
            self.assertEqual(canonical_json(r.snapshot()), canonical_json(good), f"seed={seed} key={key}")

    def test_hostile_snapshots_with_recomputed_digest(self):
        """An attacker who recomputes the outer digest still cannot restore an invariant-violating state."""
        import hashlib
        base = Rollout("v2", waves=[["a"], ["b", "c"]])
        base.pin({"a": "v1", "b": "v1", "c": "v1"})
        base.admit(verification("v2"))
        base.run_wave(healthy=True)
        good = base.snapshot()
        accepted = 0
        for it in range(ITERS):
            rng = random.Random(7000 + it)
            snap = json.loads(json.dumps(good))
            snap.pop("state_digest")
            key = rng.choice(sorted(snap))
            snap[key] = rnd_json(rng)
            try:
                snap["state_digest"] = hashlib.sha256(canonical_json(snap)).hexdigest()
                r = Rollout.from_snapshot(snap)
            except (RolloutError, StateIntegrityError, ValueError, TypeError, KeyError, AttributeError):
                continue
            accepted += 1
            r.snapshot()  # must still satisfy every invariant + audit chain
        self.assertLess(accepted, ITERS)

    def test_hostile_verification_payloads(self):
        for it in range(ITERS):
            rng = random.Random(9000 + it)
            r = Rollout("v2", waves=[["a"]])
            r.pin({"a": "v1"})
            payload = rnd_json(rng) if rng.random() < 0.5 else {**verification("v2"), rnd_id(rng): rnd_json(rng),
                                                               "bundle": rng.choice(["v2", "v3", rnd_id(rng)])}
            try:
                r.admit(payload)
            except (RolloutError, ValueError, TypeError):
                continue
            # accepted => it really was bound to v2
            self.assertIn("v2", [payload.get(k) for k in ("bundle", "artifact", "artifact_id", "subject")])

    def test_pathological_identifiers_and_huge_wave_sets(self):
        for w in WEIRD:
            try:
                Rollout("v2", waves=[[w]])
            except (RolloutError, ValueError):
                pass
        big = [[f"n{i}"] for i in range(1)] + [[f"m{i}" for i in range(20_000)]]
        r = Rollout("v2", waves=big)
        r.pin({n: "v1" for wave in big for n in wave})
        self.assertEqual(len(r.scheduled_nodes), 20_001)
        with self.assertRaises(RolloutError):
            Rollout("v2", waves=[["a", "b"], ["c"]])          # shrinking

    def test_schema_validator_fuzz_never_crashes(self):
        for it in range(ITERS):
            rng = random.Random(12000 + it)
            try:
                schema.validate(rnd_json(rng), "PK_CONTROLLER_STATE/1")
            except Gap08Error:
                pass


if __name__ == "__main__":
    unittest.main()
