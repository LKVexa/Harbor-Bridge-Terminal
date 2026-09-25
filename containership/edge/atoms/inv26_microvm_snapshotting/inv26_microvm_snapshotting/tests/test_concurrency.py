"""Concurrency and race tests (C086 expanded, C058).

Threads: concurrent grant replay, capture-vs-capture on one id, restore-vs-restore,
delete-vs-restore, quarantine-vs-restore, admission ceilings under contention.
Processes: multi-process compare-and-swap on the durable metastore (the lock is
fcntl.flock, so this exercises the cross-process path), and a stale controller
fenced out by a newer lease holder.
"""
import multiprocessing as mp
import secrets
import tempfile
import threading
import time
import unittest

from inv26_microvm_snapshotting.errors import SnapshotServiceError
from inv26_microvm_snapshotting.metastore import MetaStore
from inv26_microvm_snapshotting.tests.harness import Rig


def _race(n, fn):
    barrier = threading.Barrier(n)
    out = [None] * n

    def run(i):
        barrier.wait()
        out[i] = fn(i)
    ts = [threading.Thread(target=run, args=(i,)) for i in range(n)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(30)
    return out


class ThreadRaces(unittest.TestCase):
    def setUp(self):
        self.r = Rig(cfg_over={"admission": {"max_inflight": 64, "per_tenant": 64, "max_queue": 128,
                                             "tenant_rate_per_s": 1000.0, "tenant_burst": 1000.0}})
        self.snap = self.r.capture()

    def test_concurrent_replay_of_one_grant_commits_once(self):
        g = self.r.grant(self.snap)
        res = _race(12, lambda i: self.r.restore(self.snap, grant=g, vm="vm-2"))
        ok = [b for st, b in res if st == 200]
        self.assertEqual(len(ok), 1, [b.get("code") for _, b in res])
        self.assertTrue(all(b["code"] in ("SNAP_GRANT_REPLAYED", "SNAP_STALE_GENERATION") for st, b in res if st != 200))
        self.assertEqual(self.r.metrics.total("inv26_reseeds_total"), 1)

    def test_capture_vs_capture_same_id(self):
        for i in range(8):
            self.r.boot(f"cv-{i}")
        res = _race(8, lambda i: self.r.svc.handle("capture", self.r.token(),
                                                   self.r.capture_req("dup", vm=f"cv-{i}")))
        self.assertEqual(sum(1 for st, _ in res if st == 200), 1)
        self.assertEqual({b["code"] for st, b in res if st != 200}, {"SNAP_DUPLICATE"})

    def test_many_distinct_restores_in_parallel(self):
        res = _race(16, lambda i: self.r.restore(self.snap, vm=f"par-{i}"))
        self.assertTrue(all(st == 200 for st, _ in res), [b for st, b in res if st != 200][:2])
        proofs = {b["entropy_proof_sha256"] for _, b in res}
        self.assertEqual(len(proofs), 16)  # no two clones share entropy

    def test_delete_vs_restore(self):
        adm = self.r.admin_token()
        grants = [self.r.grant(self.snap, vm=f"dr-{i}") for i in range(10)]

        def go(i):
            if i == 5:
                return self.r.svc.handle("delete", adm, {"snapshot_id": "s1"})
            return self.r.restore(self.snap, grant=grants[i], vm=f"dr-{i}")
        res = _race(10, go)
        self.assertEqual(res[5][0], 200, res[5][1])
        for i, (st, b) in enumerate(res):
            if i != 5 and st != 200:
                self.assertIn(b["code"], ("SNAP_NOT_FOUND", "SNAP_ILLEGAL_TRANSITION", "SNAP_STORAGE_CORRUPT",
                                          "SNAP_KEY_REVOKED", "SNAP_CIPHERTEXT_INVALID"))
        self.assertEqual(self.r.meta.get("snap/s1")[1]["state"], "DELETED")
        # every guest that is Running got a reseed; no guest is left paused/half-loaded
        for vm, v in self.r.hv.vms.items():
            if vm.startswith("dr-"):
                self.assertEqual(v["state"], "Running")
                self.assertIsNotNone(v["rng"])

    def test_admission_ceiling_holds(self):
        r = Rig(cfg_over={"admission": {"max_inflight": 2, "per_tenant": 2, "max_queue": 0,
                                        "tenant_rate_per_s": 1000.0, "tenant_burst": 1000.0}})
        snap = r.capture()
        r.hv.delay_s = 0.05
        peak = []
        orig = r.hv.load

        def load(*a):
            peak.append(r.svc._admission.inflight)
            return orig(*a)
        r.hv.load = load
        res = _race(8, lambda i: r.restore(snap, vm=f"ad-{i}"))
        self.assertLessEqual(max(peak), 2)
        self.assertTrue(any(b.get("code") == "SNAP_OVERLOADED" for st, b in res if st != 200))


def _cas_worker(root, n, q):
    m = MetaStore(root)
    wins = 0
    for _ in range(n):
        while True:
            cur = m.get("counter")
            gen, val = cur if cur else (0, 0)
            try:
                m.transact({"counter": (gen, val + 1)})
                wins += 1
                break
            except SnapshotServiceError:
                continue
    q.put(wins)


class ProcessRaces(unittest.TestCase):
    def test_multiprocess_cas_loses_no_updates(self):
        root = tempfile.mkdtemp()
        MetaStore(root)
        q = mp.get_context("fork").Queue()
        ps = [mp.get_context("fork").Process(target=_cas_worker, args=(root, 40, q)) for _ in range(4)]
        for p in ps:
            p.start()
        for p in ps:
            p.join(60)
        self.assertEqual(sum(q.get() for _ in ps), 160)
        self.assertEqual(MetaStore(root).get("counter")[1], 160)

    def test_stale_controller_is_fenced(self):
        now = [1000.0]
        root = tempfile.mkdtemp()
        a, b = MetaStore(root, clock=lambda: now[0]), MetaStore(root, clock=lambda: now[0])
        ta = a.acquire_lease("controller", "A", ttl_s=10)
        a.transact({"x": (None, 1)}, fence=("controller", ta))
        with self.assertRaises(SnapshotServiceError):
            b.acquire_lease("controller", "B", ttl_s=10)  # still held
        now[0] += 11  # A paused past its lease (GC pause / partition)
        tb = b.acquire_lease("controller", "B", ttl_s=10)
        self.assertGreater(tb, ta)
        with self.assertRaises(SnapshotServiceError) as cm:
            a.transact({"x": (None, 2)}, fence=("controller", ta))
        self.assertEqual(cm.exception.code, "SNAP_FENCED")
        b.transact({"x": (None, 3)}, fence=("controller", tb))
        self.assertEqual(MetaStore(root).get("x")[1], 3)

    def test_compaction_seen_by_other_process_view(self):
        from inv26_microvm_snapshotting import metastore as ms
        root = tempfile.mkdtemp()
        a, b = MetaStore(root), MetaStore(root)
        old = ms.COMPACT_EVERY
        ms.COMPACT_EVERY = 5
        try:
            for i in range(12):
                a.transact({f"k{i}": (0, i)})
            b.transact({"late": (0, "b")})
            for i in range(3):
                a.transact({f"z{i}": (0, i)})
        finally:
            ms.COMPACT_EVERY = old
        c = MetaStore(root)
        self.assertEqual(len(c.scan("k")), 12)
        self.assertEqual(c.get("late")[1], "b")
        self.assertEqual(len(c.scan("z")), 3)
        self.assertEqual(len(b.scan("")), 16)


if __name__ == "__main__":
    unittest.main()
