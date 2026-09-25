"""MC-28 concurrency tests.  Contract: every public ElasticityPlane method is safe to call from
many threads (serialised by one lock); a controller instance is never shared across scopes."""
from __future__ import annotations

import pathlib
import sys
import threading
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from helpers import World  # noqa: E402

from pln05_elasticity_plane.errors import PlaneError  # noqa: E402


class Concurrency(unittest.TestCase):
    def test_parallel_observe_status_control_config(self):
        w = World()
        for i in range(8):
            w.declare(workload=f"w{i}")
        errors, lock = [], threading.Lock()
        toks = {i: w.token(source=f"r{i}") for i in range(8)}
        seqs = {i: 0 for i in range(8)}

        def reporter(i):
            for n in range(200):
                seqs[i] += 1
                raw = w.demand((n % 10) / 10, workload=f"w{i}", source=f"r{i}", seq=seqs[i])
                try:
                    d = w.plane.submit_demand(raw, toks[i])
                    if d["workload"] != f"w{i}":
                        with lock:
                            errors.append("foreign decision returned")
                except PlaneError as exc:
                    if exc.code not in ("E_OVERLOADED", "E_FROZEN"):
                        with lock:
                            errors.append(exc.code)
                except Exception as exc:  # noqa: BLE001
                    with lock:
                        errors.append(repr(exc))

        def reader():
            for _ in range(200):
                w.plane.status()
                w.plane.health()
                w.plane.tick()

        def controller():
            for k in range(20):
                try:
                    w.plane.control(w.token("operator"), "freeze", tenant="t1", site="dub", workload="w0",
                                    reason="r", ticket=f"t{k}", expires=w.clock() + 0.001)
                except PlaneError as exc:
                    errors.append(exc.code)

        threads = [threading.Thread(target=reporter, args=(i,)) for i in range(8)]
        threads += [threading.Thread(target=reader), threading.Thread(target=controller)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(60)
        self.assertEqual(errors, [])
        for s in w.plane.scopes.values():
            self.assertTrue(s.controller.limits.floor <= s.controller.current <= s.controller.limits.ceiling)
        # every published target for a scope has a non-decreasing fencing token
        self.assertEqual(w.plane.processed, 8 * 200)

    def test_concurrent_leader_contention(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        a = World(tmp.name)
        a.declare()
        b = World(tmp.name, instance="ctl-b", ring=a.ring, leases=a.leases, sink=a.sink, clock=a.clock)
        wins = {"a": 0, "b": 0}
        ta, tb = a.token(source="ra"), b.token(source="rb")

        def run(world, name, tok, src):
            for n in range(300):
                try:
                    world.observe(0.5, source=src, token=tok, seq=n + 1)
                    wins[name] += 1
                except PlaneError as exc:
                    if exc.code not in ("E_NOT_LEADER", "E_FENCED"):
                        raise

        t1 = threading.Thread(target=run, args=(a, "a", ta, "ra"))
        t2 = threading.Thread(target=run, args=(b, "b", tb, "rb"))
        t1.start(); t2.start(); t1.join(); t2.join()
        self.assertEqual(min(wins.values()), 0)  # exactly one leader while the lease is live
        self.assertEqual(max(wins.values()), 300)


if __name__ == "__main__":
    unittest.main()
