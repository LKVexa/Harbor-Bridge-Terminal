"""Concurrency/race tests (item 52): threads hammer shared primitives and
competing controllers; invariants must hold with no duplicate launch."""
import threading
import unittest

import _support as S


def hammer(n_threads, fn):
    barrier = threading.Barrier(n_threads)
    errs = []

    def run(i):
        barrier.wait()
        try:
            fn(i)
        except Exception as e:  # noqa: BLE001
            errs.append(e)
    ts = [threading.Thread(target=run, args=(i,)) for i in range(n_threads)]
    [t.start() for t in ts]
    [t.join(30) for t in ts]
    return errs


class Races(unittest.TestCase):
    def test_admission_never_exceeds_ceilings(self):
        a = S.resilience.Admission(8, {}, 3, 1e9, 1e9, S.Clock())
        peak = {"g": 0}
        lock = threading.Lock()

        def work(i):
            t = f"t{i % 4}"
            for _ in range(200):
                try:
                    a.acquire(t)
                except S.lifecycle.PlaneError:
                    continue
                with lock:
                    peak["g"] = max(peak["g"], a.total)
                    assert a.inflight[t] <= 3
                a.release(t)
        self.assertEqual(hammer(16, work), [])
        self.assertLessEqual(peak["g"], 8)
        self.assertEqual(a.total, 0)

    def test_audit_chain_stays_valid_under_concurrent_appends(self):
        log = S.audit.AuditLog()
        self.assertEqual(hammer(12, lambda i: [log.append(f"a{i}", "x", "t", "ok") for _ in range(100)]), [])
        self.assertEqual(len(log.records), 1200)
        self.assertTrue(S.audit.AuditLog.verify(log.records, log.head)[0])

    def test_single_leader_among_contenders(self):
        lease, clock = S.leader.LeaseStore(), S.Clock()
        els = [S.leader.Elector(lease, f"e{i}", 15, clock) for i in range(10)]
        wins = []
        lock = threading.Lock()

        def go(i):
            if els[i].try_acquire_or_renew():
                with lock:
                    wins.append(i)
        self.assertEqual(hammer(10, go), [])
        self.assertEqual(len(wins), 1)

    def test_runtime_idempotency_under_concurrent_duplicate_places(self):
        rt = S.downstream.InMemoryRuntime()
        env = S.downstream.envelope({"units": [{"name": "c"}]}, {"appId": "app-1"}, "uid00000/g1/a1", 1)
        self.assertEqual(hammer(16, lambda i: rt.place(env)), [])
        self.assertEqual(rt.launches, 1)

    def test_two_controllers_racing_on_one_cluster(self):
        kube, rt, lease, clock = S.kube.FakeKube(), S.downstream.InMemoryRuntime(), S.leader.LeaseStore(), S.Clock()
        hs = [S.Harness(kube_=kube, runtime=rt, lease_store=lease, clock=clock, ident=f"c{i}") for i in range(2)]
        for i in range(20):
            kube.apply(S.workload(name=f"w{i}"))
        self.assertEqual(hammer(2, lambda i: hs[i].settle(5)), [])
        self.assertEqual(rt.launches, 20)
        for i in range(20):
            self.assertEqual(kube.get("team-a", f"w{i}")["status"]["state"], "Placed")

    def test_config_activation_is_atomic_for_readers(self):
        st = S.config.ConfigStore({})
        seen = set()

        def w(i):
            for k in range(50):
                if i == 0:
                    st.activate({"maxInflight": 10 + k % 2, "defaultTenantInflight": 10 + k % 2}, source="t", activator="t")
                else:
                    c = st.active
                    seen.add((c["maxInflight"], c["defaultTenantInflight"]))
        self.assertEqual(hammer(4, w), [])
        self.assertTrue(all(a == b or (a, b) == (256, 16) for a, b in seen), seen)


if __name__ == "__main__":
    unittest.main()
