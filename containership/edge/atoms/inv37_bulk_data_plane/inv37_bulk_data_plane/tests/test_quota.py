"""Quotas, fairness, contention, freeze (C017, C028, C054, C064, C067, C086)."""
from __future__ import annotations

import threading
import time
import unittest

from _support import pkg
from inv37_bulk_data_plane.quota import FairAdmission, TenantQuota


def adm(**kw):
    base = dict(max_active=4, max_bytes=1 << 30, max_pending=16, default=TenantQuota(1, 2, 1 << 28))
    base.update(kw)
    return FairAdmission(**base)


class QuotaTest(unittest.TestCase):
    def test_tenant_cap(self):
        a = adm()
        a.acquire("t1", 10); a.acquire("t1", 10)
        with self.assertRaises(pkg.CodedError) as cm:
            a.acquire("t1", 10)
        self.assertEqual(cm.exception.code, "quota_exceeded")
        a.acquire("t2", 10)  # other tenant unaffected

    def test_bytes_quota(self):
        a = adm(default=TenantQuota(1, 10, 100))
        a.acquire("t", 60)
        self.assertRaises(pkg.CodedError, a.acquire, "t", 60)
        self.assertRaises(pkg.CodedError, a.acquire, "t", 101)

    def test_limit_boundaries(self):
        a = adm(max_active=3, default=TenantQuota(1, 10, 1 << 28))
        gs = [a.acquire(f"t{i}", 1) for i in range(3)]  # limit
        self.assertRaises(pkg.CodedError, a.acquire, "t9", 1)  # limit+1
        a.release(gs[0])
        a.release(gs[0])  # idempotent release
        a.acquire("t9", 1)
        self.assertEqual(a.metrics()["active"], 3)

    def test_one_tenant_cannot_starve_others(self):
        a = adm(max_active=4, default=TenantQuota(1, 4, 1 << 28))
        hog = [a.acquire("hog", 1) for _ in range(4)]
        order = []

        def want(t):
            g = a.acquire(t, 1, timeout=5)
            order.append(t)
            return g

        th = [threading.Thread(target=want, args=("hog",)), threading.Thread(target=want, args=("small",))]
        th[0].start(); time.sleep(0.05); th[1].start(); time.sleep(0.05)
        a.release(hog[0])  # one slot frees; fairness picks the tenant with lowest active/weight
        time.sleep(0.1)
        self.assertEqual(order, ["small"])
        a.release(hog[1])
        for t in th:
            t.join(2)
        self.assertEqual(order, ["small", "hog"])

    def test_weights(self):
        a = FairAdmission(max_active=1, max_bytes=1 << 30, max_pending=8,
                          tenants={"gold": TenantQuota(4, 4, 1 << 28), "bronze": TenantQuota(1, 4, 1 << 28)})
        g = a.acquire("gold", 1)
        a.acquire_gold = None
        got = []
        ts = [threading.Thread(target=lambda t=t: got.append((t, a.acquire(t, 1, timeout=5)))) for t in ("bronze", "gold")]
        # gold has active=1 weight 4 -> 0.25 ; bronze active=0 -> 0; bronze first
        for t in ts:
            t.start(); time.sleep(0.03)
        a.release(g); time.sleep(0.1)
        self.assertEqual(got[0][0], "bronze")
        a.release(got[0][1])
        for t in ts:
            t.join(2)

    def test_pending_queue_bound_and_freeze(self):
        a = adm(max_active=1, max_pending=0)
        a.acquire("t", 1)
        with self.assertRaises(pkg.CodedError) as cm:
            a.acquire("u", 1)
        self.assertEqual(cm.exception.code, "admission_rejected")
        b = adm()
        b.freeze(True)
        with self.assertRaises(pkg.CodedError) as cm:
            b.acquire("t", 1)
        self.assertEqual(cm.exception.code, "admission_frozen")

    def test_concurrent_contention_never_exceeds_limits(self):
        a = adm(max_active=5, max_pending=1000, default=TenantQuota(1, 3, 1 << 28))
        peak = {"v": 0}
        lock = threading.Lock()

        def worker(t):
            for _ in range(20):
                try:
                    g = a.acquire(t, 1, timeout=1)
                except pkg.CodedError:
                    continue
                m = a.metrics()
                with lock:
                    peak["v"] = max(peak["v"], m["active"])
                    self.assertLessEqual(m["tenants"][t]["active"], 3)
                a.release(g)

        ths = [threading.Thread(target=worker, args=(f"t{i % 4}",)) for i in range(16)]
        for t in ths: t.start()
        for t in ths: t.join()
        self.assertLessEqual(peak["v"], 5)
        self.assertEqual(a.metrics()["active"], 0)


if __name__ == "__main__":
    unittest.main()
