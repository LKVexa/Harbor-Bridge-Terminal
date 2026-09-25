"""Two plane instances sharing one state directory, lease service and consumer, driven by a
seeded random schedule of limits/ceiling changes, demand, clock jumps (both directions),
coordination outages, restarts, freezes, resumes and ticks.  Adapted from the independent
review's fuzzer that found the stale-leader and decision-id-collision defects.

Invariants after every step: every applied target is inside its own envelope; fencing
tokens applied are non-decreasing; no exception other than PlaneError escapes; after a
successful envelope change the consumer's latest target is inside the new envelope.
PLN05_MULTI_SEEDS scales the run (default 60; release tier 400)."""
from __future__ import annotations

import os
import pathlib
import random
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from helpers import World  # noqa: E402

from pln05_elasticity_plane.errors import PlaneError  # noqa: E402

SEEDS = int(os.environ.get("PLN05_MULTI_SEEDS", "60"))


def run(seed: int, steps: int = 300):
    rng = random.Random(seed)
    with tempfile.TemporaryDirectory() as d:
        a = World(d, instance="ctl-a")
        mk = lambda inst: World(d, instance=inst, ring=a.ring, leases=a.leases, sink=a.sink, clock=a.clock, mono=a.mono)  # noqa: E731
        worlds = [a, mk("ctl-b")]
        rev, seq, env = 0, 0, None
        for i in range(steps):
            w = rng.choice(worlds)
            op = rng.random()
            changed = False
            try:
                if op < 0.12:
                    rev += 1
                    f = rng.randint(0, 4)
                    c = rng.randint(f, 20)
                    w.plane.submit_limits(w.limits(floor=f, ceiling=c, revision=rev), w.token("intent_plane"))
                    env, changed = (f, c), True
                elif op < 0.2:
                    c = rng.randint(0, 20)
                    w.plane.lower_ceiling(w.token("power_thermal"), tenant="t1", site="dub", workload="w1", ceiling=c)
                    env, changed = (env[0], min(env[1], c)), True
                elif op < 0.65:
                    seq += 1
                    w.observe(rng.choice([0.0, 0.1, 0.5, 0.9, 1.5, rng.random()]), seq=seq)
                elif op < 0.75:
                    w.clock.advance(rng.choice([1, 5, 30, 120, -3, -50]))
                elif op < 0.8:
                    a.leases.available = not a.leases.available
                elif op < 0.85:
                    worlds[worlds.index(w)] = mk(w.plane.instance_id)
                elif op < 0.9:
                    w.plane.control(w.token("operator"), "freeze", tenant="t1", site="dub", workload="w1", reason="r", ticket="T")
                elif op < 0.95:
                    w.plane.resume(w.admin(sub=rng.choice(["a1", "a2"])), tenant="t1", site="dub", workload="w1", ticket="T")
                else:
                    w.plane.tick()
            except PlaneError:
                pass
            except Exception as exc:  # noqa: BLE001
                return f"seed {seed} step {i}: non-PlaneError {exc!r}"
            high = 0
            for t in a.sink.applied:
                if not t["floor"] <= t["target"] <= t["ceiling"]:
                    return f"seed {seed} step {i}: applied target outside its envelope {t}"
                if t["fencing_token"] < high:
                    return f"seed {seed} step {i}: fencing token decreased"
                high = t["fencing_token"]
            if changed and a.sink.applied and env is not None:
                last = a.sink.applied[-1]
                if not env[0] <= last["target"] <= env[1]:
                    return f"seed {seed} step {i}: consumer target {last['target']} outside new envelope {env}"
    return None


class MultiInstance(unittest.TestCase):
    def test_shared_state_two_instances_hold_invariants(self):
        problems = [p for p in (run(s) for s in range(SEEDS)) if p]
        self.assertEqual(problems, [])

    def test_two_holds_at_same_instant_get_distinct_ids(self):
        w = World()
        w.declare(ceiling=8)
        for _ in range(3):
            w.observe(0.9)
        tok = w.token("intent_plane")
        w.plane.submit_limits(w.limits(revision=2, ceiling=3), tok)
        w.plane.submit_limits(w.limits(revision=3, ceiling=2), w.token("intent_plane"))
        ids = [t["decision_id"] for t in w.sink.applied]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(w.sink.applied[-1]["target"], 2)


if __name__ == "__main__":
    unittest.main()
