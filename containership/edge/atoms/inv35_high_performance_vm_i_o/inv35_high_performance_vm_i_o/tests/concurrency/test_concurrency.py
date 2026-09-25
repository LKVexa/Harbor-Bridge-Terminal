"""INV-35-C086: submit/complete contention through the full facade."""
from __future__ import annotations

import os
import random
import threading
import unittest

from _support import Inv35Error, VirtQueue, REGION, one, pkg, stack

THREADS = int(os.environ.get("INV35_STRESS_THREADS", "8"))
OPS = int(os.environ.get("INV35_STRESS_OPS", "1500"))


class ContentionTest(unittest.TestCase):
    def test_facade_invariants_under_contention(self):
        r, cp, dp, ctl, bulk = stack(submit_rate_per_s=1e9, submit_burst=1e9, tenant_share=1.0)
        q = r.queues["q0"].vq
        violations, lost_wakeups = [], []
        start = threading.Barrier(THREADS)

        def worker(seed):
            rng = random.Random(seed)
            start.wait()
            for _ in range(OPS):
                try:
                    if rng.random() < 0.55:
                        n = rng.randint(1, 4)
                        chain = {i: pkg.Descriptor(i, 0x10000 + 64 * i, 64, i + 1 if i + 1 < n else None) for i in range(n)}
                        dp.submit(bulk, tenant="t1", queue="q0", chain=chain, head=0)
                    else:
                        res = dp.complete(bulk, tenant="t1", queue="q0", guest_wants_notification=rng.random() < 0.3)
                        if res["pending"] > 0 and not res["notified"]:
                            lost_wakeups.append(res)
                except Inv35Error as exc:
                    if exc.code not in ("INV35-E200", "INV35-E205"):
                        violations.append(exc.code)
                if q.in_flight_descriptors > q.depth_limit or q.in_flight_descriptors < 0:
                    violations.append(("bound", q.in_flight_descriptors))

        threads = [threading.Thread(target=worker, args=(s,)) for s in range(THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(violations, [])
        self.assertEqual(lost_wakeups, [])
        self.assertEqual(r.quota.used.get("t1", 0), q.in_flight_descriptors)
        self.assertEqual(sum(r.queues["q0"].reservations), q.in_flight_descriptors)
        while q.in_flight:
            dp.complete(bulk, tenant="t1", queue="q0", guest_wants_notification=True)
        self.assertEqual((q.in_flight, q.pending, q.in_flight_descriptors, r.quota.used["t1"]), (0, 0, 0, 0))

    def test_raw_model_many_queues_isolated(self):
        queues = [VirtQueue(f"q{i}", REGION) for i in range(8)]
        errs = []

        def worker(q):
            try:
                for _ in range(OPS):
                    q.submit(one(), 0)
                    q.complete(guest_wants_notification=False)
            except Exception as exc:  # pragma: no cover - failure path
                errs.append(exc)

        ts = [threading.Thread(target=worker, args=(q,)) for q in queues]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(errs, [])
        self.assertTrue(all(q.in_flight_descriptors == 0 for q in queues))

    def test_concurrent_config_updates_are_serialised(self):
        from _support import config
        r, cp, dp, ctl, bulk = stack()
        gens, errs = [], []

        def upd(i):
            try:
                gens.append(cp.apply_config(ctl, tenant="t1", queue="q0", environment={"stall_threshold_s": 0.1 + i / 100}).generation)
            except Inv35Error as exc:  # pragma: no cover
                errs.append(exc)

        ts = [threading.Thread(target=upd, args=(i,)) for i in range(16)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(errs, [])
        self.assertEqual(sorted(gens), list(range(2, 18)))


if __name__ == "__main__":
    unittest.main()
