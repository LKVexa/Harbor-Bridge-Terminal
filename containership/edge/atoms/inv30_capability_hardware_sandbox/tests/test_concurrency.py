# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Race/concurrency tests (GAP-032).

Semantics under test: check/derive/invalidate on one Capability are linearisable
(each holds the capability lock). Therefore an access either completed *before*
the invalidation's linearisation point or raises Invalidated — never "succeeds
after invalidation". The service table is guarded by one RLock.
"""
import threading
import unittest

from ..core import Capability, Invalidated
from ._util import access, derive, invalidate, make_service, mint


class ConcurrencyTest(unittest.TestCase):
    def test_no_success_after_invalidation(self):
        for _ in range(30):
            cap = Capability(0, 4096, {"read"})
            inv_done = threading.Event()
            late_success = []
            barrier = threading.Barrier(9)

            def reader():
                barrier.wait()
                for _ in range(2000):
                    try:
                        cap.check(address=0, size=8, operation="read")
                        if inv_done.is_set():
                            late_success.append(1)
                    except Invalidated:
                        return

            def killer():
                barrier.wait()
                cap.invalidate()
                inv_done.set()
            ts = [threading.Thread(target=reader) for _ in range(8)] + [threading.Thread(target=killer)]
            [t.start() for t in ts]
            [t.join() for t in ts]
            self.assertEqual(late_success, [])
            self.assertFalse(cap.valid)

    def test_concurrent_resurrection_attempts_fail(self):
        cap = Capability(0, 16, {"read"})
        cap.invalidate()
        errs = []

        def resurrect():
            try:
                cap.valid = True
            except Invalidated:
                errs.append(1)
        ts = [threading.Thread(target=resurrect) for _ in range(16)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(errs), 16)
        self.assertFalse(cap.valid)

    def test_service_parallel_derive_and_sweep(self):
        svc = make_service()
        root = mint(svc)["handle"]
        handles, lock = [], threading.Lock()

        def worker():
            for i in range(50):
                r = derive(svc, root, 0x1000 + i, 1, ["read"])
                if "handle" in r:
                    with lock:
                        handles.append(r["handle"])
        ts = [threading.Thread(target=worker) for _ in range(6)]
        [t.start() for t in ts]
        invalidate(svc, root)
        [t.join() for t in ts]
        invalidate(svc, root)  # second sweep catches children created before the first sweep's snapshot
        for h in handles:
            self.assertEqual(access(svc, h, 0x1000).get("code"), "INVALIDATED")
        self.assertEqual(svc.health()["active_capabilities"], 0)

    def test_quota_is_not_exceeded_under_contention(self):
        svc = make_service(limits={"max_capabilities_per_tenant": 20})
        root = mint(svc)["handle"]
        ok = []

        def worker():
            for _ in range(20):
                r = derive(svc, root, 0x1000, 1)
                if "handle" in r:
                    ok.append(1)
        ts = [threading.Thread(target=worker) for _ in range(5)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(ok) + 1, 20)


if __name__ == "__main__":
    unittest.main()
