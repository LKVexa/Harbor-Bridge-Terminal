"""GAP-026 concurrency/race tests: place/unplace/resolve/call, revision monotonicity,
admission accounting and policy/transport callback concurrency."""
import threading, unittest
from _support import E, AdmissionController, Residency, build, ctx

THREADS = 16
N = 300


class ConcurrencyTest(unittest.TestCase):
    def test_residency_races_keep_revision_monotonic_and_tenant_stable(self):
        res = Residency("h")
        revs, errs = [], []
        def writer(tid):
            for i in range(N):
                try:
                    revs.append(res.place(f"c{i % 20}", "acme", lambda *a: 1))
                    if i % 3 == 0:
                        res.unplace(f"c{(i + tid) % 20}", tenant="acme")
                    p = res.resolve(f"c{i % 20}")
                    if p is not None:
                        assert p.tenant == "acme"
                except Exception as e:  # noqa: BLE001
                    errs.append(e)
        def hijacker():
            for i in range(N):
                try:
                    res.place(f"c{i % 20}", "evil", lambda *a: 2)
                except E.CrossTenantChain:
                    pass
        ts = [threading.Thread(target=writer, args=(t,)) for t in range(THREADS)] + \
             [threading.Thread(target=hijacker) for _ in range(4)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(errs, [])
        self.assertEqual(len(revs), len(set(revs)), "revision reused")
        for name, (tenant, _) in res.table.items():
            self.assertIn(tenant, ("acme", "evil"))

    def test_concurrent_calls_admission_accounting_and_counters(self):
        ch, res, prov, v = build(grants=[("acme", "svc", "invoke")])
        barrier = threading.Barrier(THREADS)
        res.place("svc", "acme", lambda hop, r: r, abi="hop")
        out, errs = [], []
        def run(tid):
            barrier.wait()
            for i in range(50):
                try:
                    out.append(ch.invoke("svc", (tid, i), ctx(v, trace=f"t{tid}-{i}")))
                except E.Overloaded:
                    pass
                except Exception as e:  # noqa: BLE001
                    errs.append(e)
        ts = [threading.Thread(target=run, args=(t,)) for t in range(THREADS)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(errs, [])
        self.assertEqual(ch.admission.snapshot()["in_flight"], 0)
        self.assertEqual(ch.hops_local, len(out))

    def test_admission_never_exceeds_cap_under_contention(self):
        a = AdmissionController(max_in_flight=4, max_in_flight_per_tenant=4)
        peak, lock, cur = [0], threading.Lock(), [0]
        def run():
            for _ in range(200):
                try:
                    with a.admit("t"):
                        with lock:
                            cur[0] += 1; peak[0] = max(peak[0], cur[0])
                        with lock:
                            cur[0] -= 1
                except E.Overloaded:
                    pass
        ts = [threading.Thread(target=run) for _ in range(THREADS)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertLessEqual(peak[0], 4); self.assertEqual(a.in_flight, 0)

    def test_policy_revocation_racing_calls_never_grants_after_invalidate(self):
        ch, res, prov, v = build(grants=[("acme", "svc", "invoke")])
        res.place("svc", "acme", lambda hop, r: "ok", abi="hop")
        stop = threading.Event()
        errs = []
        def caller():
            while not stop.is_set():
                try:
                    ch.invoke("svc", 0, ctx(v))
                except (E.CapabilityRefused, E.Overloaded):
                    pass
                except E.ProviderUnavailable as e:
                    # in-flight decision computed at the pre-revocation revision: fail closed
                    if e.details.get("reason") != "stale_policy":
                        errs.append(e)
                except Exception as e:  # noqa: BLE001
                    errs.append(e)
        ts = [threading.Thread(target=caller) for _ in range(6)]
        [t.start() for t in ts]
        prov.revoke("acme", "svc"); ch.policy.invalidate(min_policy_revision=prov.revision)
        stop.set(); [t.join() for t in ts]
        self.assertEqual(errs, [])
        with self.assertRaises(E.CapabilityRefused):
            ch.invoke("svc", 0, ctx(v))


if __name__ == "__main__":
    unittest.main()
