"""MC-29 soak / burst / fleet tests with leak and drift detectors.

Scaled by PLN05_SOAK_DECISIONS (default 60000; release tier should use >= 1,000,000) and
PLN05_FLEET_SCOPES (default 5000).  Emits $PLN05_EVIDENCE_DIR/soak.json when set.
Reference infrastructure for fleet targets is NOT available here: the fleet numbers
below are single-process demonstrations, not fleet-scale certification."""
from __future__ import annotations

import json
import os
import pathlib
import random
import sys
import tempfile
import threading
import time
import tracemalloc
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from helpers import World  # noqa: E402

from pln05_elasticity_plane.errors import PlaneError  # noqa: E402

DECISIONS = int(os.environ.get("PLN05_SOAK_DECISIONS", "60000"))
FLEET = int(os.environ.get("PLN05_FLEET_SCOPES", "5000"))
REPORT: dict = {"params": {"decisions": DECISIONS, "fleet_scopes": FLEET}}


def p95(xs):
    xs = sorted(xs)
    return xs[int(0.95 * (len(xs) - 1))]


class Soak(unittest.TestCase):
    def test_soak_no_unbounded_growth_or_drift(self):
        rng = random.Random(2026)
        w = World()
        for i in range(4):
            w.declare(workload=f"w{i}", ceiling=64)
        toks = {i: w.token(source=f"r{i}", lifetime=3600) for i in range(4)}
        warm = min(40000, DECISIONS // 2)
        tracemalloc.start()
        windows, timeline, errors = [], [], 0
        mem_after_warm = None
        for n in range(DECISIONS):
            i = n % 4
            phase = (n // 2000) % 5
            u = {0: 0.5, 1: rng.uniform(0.7, 1.5), 2: rng.uniform(0.0, 0.3),
                 3: 0.75 + rng.uniform(-0.01, 0.01), 4: rng.random()}[phase]  # steady/burst/low/edge/random
            if n % 5000 == 4999:
                w.leases.available = False  # periodic dependency failure
            if n % 5000 == 0:
                w.leases.available = True
            if n % 20000 == 10000:  # config rotation during soak
                w.plane.activate_config(w.token("platform_operator", tenant="*"),
                                        {"site": {"revision": w.plane.config.active.revision + 1,
                                                  "stale_after_s": 30 + (n // 20000) % 3}})
            w.clock.advance(0.01)
            s = time.perf_counter()
            try:
                w.plane.submit_demand(w.demand(u, workload=f"w{i}", source=f"r{i}"), toks[i])
            except PlaneError:
                errors += 1
            windows.append((time.perf_counter() - s) * 1000)
            if n == warm:
                mem_after_warm = tracemalloc.get_traced_memory()[0]
            if len(windows) == 5000:
                timeline.append({"at": n + 1, "p95_ms": p95(windows), "mem": tracemalloc.get_traced_memory()[0],
                                 "queue": len(w.plane.admission), "series": w.plane.metrics.series(),
                                 "errors": errors})
                windows = []
        mem_end = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()
        growth = (mem_end - mem_after_warm) / max(1, mem_after_warm)
        REPORT["soak"] = {"timeline": timeline, "mem_after_warm": mem_after_warm, "mem_end": mem_end,
                          "growth_ratio_after_warm": growth, "errors": errors}
        self.assertLess(growth, 0.05, "memory kept growing after bounded stores filled")
        self.assertTrue(all(t["queue"] == 0 for t in timeline))
        self.assertLess(max(t["series"] for t in timeline), 200)
        first, last = timeline[0]["p95_ms"], timeline[-1]["p95_ms"]
        self.assertLess(last, max(3 * first, first + 0.5), "latency drifted")
        for s in w.plane.scopes.values():
            self.assertLessEqual(len(s.seen), 256)

    def test_burst_then_recovery_without_reset(self):
        w = World()
        w.declare(ceiling=1000)
        tok = w.token(lifetime=3600)
        rejected = 0
        for _ in range(5000):
            try:
                w.plane.enqueue_demand(w.demand(0.9), tok)
            except PlaneError:
                rejected += 1
        self.assertGreater(rejected, 0)
        w.plane.process()
        self.assertEqual(len(w.plane.admission), 0)
        self.assertTrue(w.plane.health()["ready"])
        self.assertTrue(w.observe(0.5, token=tok)["published"])
        REPORT["burst"] = {"offered": 5000, "rejected": rejected}

    def test_fleet_scale_single_process(self):
        with tempfile.TemporaryDirectory() as d:
            w = World(d)
            tok_ip = [w.token("intent_plane", lifetime=3600) for _ in range(1)]
            t0 = time.perf_counter()
            for i in range(FLEET):
                w.plane.submit_limits(w.limits(workload=f"w{i}"), w.issuer.mint(
                    sub="intent_plane-1", actor_class="intent_plane", tenant="t1", sites=("dub",), now=w.clock()))
            tok = w.token(lifetime=3600)
            for i in range(FLEET):
                w.plane.submit_demand(w.demand(0.9, workload=f"w{i}"), tok)
            dt = time.perf_counter() - t0
            files = len(list((pathlib.Path(d) / "state").glob("*.state.json")))
            self.assertEqual(files, FLEET)  # state size grows with scopes only
            REPORT["fleet"] = {"scopes": FLEET, "seconds": dt, "state_files": files,
                               "decisions_per_s": FLEET / dt,
                               "note": "single process, persisted state; not fleet certification"}


def _emit():
    out = os.environ.get("PLN05_EVIDENCE_DIR")
    if out:
        pathlib.Path(out).mkdir(parents=True, exist_ok=True)
        (pathlib.Path(out) / "soak.json").write_text(json.dumps(REPORT, indent=1, sort_keys=True))


if __name__ == "__main__":
    import atexit
    atexit.register(_emit)
    unittest.main()
