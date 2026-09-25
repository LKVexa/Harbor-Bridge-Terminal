"""Group E — state, concurrency, persistence and failure containment."""
import json
import os
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from gap12_wan_resilience_and_nat_traversal.tests._covers import covers  # noqa: E402
from gap12_wan_resilience_and_nat_traversal.wan import state as st  # noqa: E402


class StoreTest(unittest.TestCase):
    @covers("G12-E056:spec1,spec2,unit,impl-doc,concurrency-model,race-tests", "G12-E057:unit,impl-doc,atomic,race-tests",
            "G12-H095:unit")
    def test_concurrent_transitions_are_atomic_and_never_torn(self):
        store = st.PathStore(st.FakeClock())
        errors = []

        def prober_ok(s):
            return s == "direct"

        def worker(i):
            try:
                for j in range(200):
                    if (i + j) % 2:
                        store.transition("peer", lambda p, now: p.connect(prober_ok, now))
                    snap = store.snapshot("peer")
                    # invariant: healthy implies a strategy and no retry window
                    if snap["healthy"] and (snap["strategy"] is None or snap["retry_at"] is not None):
                        errors.append(snap)
            except Exception as exc:  # pragma: no cover
                errors.append(repr(exc))
        ts = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(errors, [])
        self.assertEqual(store.snapshot("peer")["generation"], 800)

    @covers("G12-E057:atomic,unit", "G12-E056:atomic")
    def test_failed_transition_is_all_or_nothing(self):
        store = st.PathStore(st.FakeClock())
        store.transition("p", lambda p, now: p.connect(lambda s: s == "direct", now))

        def broken(p, now):
            p.strategy = "relay"
            p.relay_bytes = 999
            raise KeyError("defect mid-transition")
        with self.assertRaises(KeyError):
            store.transition("p", broken)
        snap = store.snapshot("p")
        self.assertEqual((snap["strategy"], snap["relay_bytes"], snap["generation"]), ("direct", 0, 1))

    @covers("G12-E057:idempotency", "G12-E056:idempotency", "G12-E065:unit,impl-doc,idempotency")
    def test_duplicate_events_and_stale_generations(self):
        store = st.PathStore(st.FakeClock())
        r1 = store.transition("p", lambda p, now: p.connect(lambda s: True, now), event_id="ev-1")
        r2 = store.transition("p", lambda p, now: p.connect(lambda s: True, now), event_id="ev-1")
        self.assertEqual(r2, ("duplicate", 1))
        with self.assertRaises(st.StaleGeneration):
            store.transition("p", lambda p, now: None, expect_generation=0)     # late timer
        lease = st.FencedLease()
        t1 = lease.acquire("ctl-1", 0, ttl=5)
        self.assertIsNone(lease.acquire("ctl-2", 1))
        t2 = lease.acquire("ctl-2", 6)
        self.assertFalse(lease.check(t1))                     # stale controller's writes refused
        self.assertTrue(lease.check(t2))

    @covers("G12-E056:bounded", "G12-E057:bounded")
    def test_peer_ceiling_and_event_memory_bounded(self):
        store = st.PathStore(st.FakeClock(), max_peers=5, event_memory=10)
        for i in range(5):
            store.snapshot(f"p{i}")
        with self.assertRaises(OverflowError):
            store.snapshot("p5")
        for i in range(100):
            store.transition("p0", lambda p, now: None, event_id=f"e{i}")
        self.assertEqual(len(store._applied), 10)


class PersistenceTest(unittest.TestCase):
    @covers("G12-E058:unit,impl-doc,crash-recovery", "G12-E056:crash-recovery", "G12-E066:unit,impl-doc",
            "G12-I113:unit")
    def test_atomic_snapshot_restore_revalidates_and_migrates(self):
        clk = st.FakeClock()
        store = st.PathStore(clk)
        store.transition("a", lambda p, now: p.connect(lambda s: s == "relay", now))
        store.transition("a", lambda p, now: p.record_relay_bytes(123))
        try:
            store.transition("b", lambda p, now: p.connect(lambda s: False, now))
        except Exception:
            pass
        d = tempfile.mkdtemp()
        path = os.path.join(d, "state.json")
        store.save(path)
        self.assertEqual([f for f in os.listdir(d) if f.startswith(".g12")], [])     # no temp left behind
        clk2 = st.FakeClock(mono=5.0)                                              # new process, new monotonic epoch
        r = st.PathStore.restore(path, clk2)
        a = r.snapshot("a")
        self.assertEqual((a["status"], a["relay_bytes"], a["revalidate"]), ("unknown", 123, True))  # not "healthy"
        b = r.snapshot("b")
        self.assertEqual(b["status"], "backing_off")                               # remaining window preserved
        raw = json.load(open(path))
        raw["peers"]["a"]["relay_bytes"] = 1
        json.dump(raw, open(path, "w"))
        with self.assertRaises(ValueError):
            st.PathStore.restore(path)                                               # tamper/corruption detected
        v1 = {"schema": 1, "peers": {"x": {"strategy": "direct", "failures": 2, "retry_at": 99999.0}}}
        json.dump(v1, open(path, "w"))
        r = st.PathStore.restore(path)
        self.assertEqual(r.snapshot("x")["failures"], 2)
        json.dump({"schema": 9, "peers": {}}, open(path, "w"))
        with self.assertRaises(ValueError):
            st.PathStore.restore(path)                                               # future schema refused


class ClockTest(unittest.TestCase):
    @covers("G12-E059:spec1,spec2,unit,impl-doc", "G12-E060:unit,impl-doc,fault")
    def test_fake_clock_and_jump_suspend_detection(self):
        c = st.FakeClock()
        w = st.ClockWatch(tolerance=2)
        self.assertEqual(w.check(c), "ok")
        c.advance(10)
        self.assertEqual(w.check(c), "ok")
        c.jump_wall(-3600)
        self.assertEqual(w.check(c), "wall_backward_jump")
        c.suspend(600)
        self.assertEqual(w.check(c), "suspend_or_forward_jump")
        # retry timing is on monotonic time: a wall jump does not shorten a backoff
        store = st.PathStore(c)
        try:
            store.transition("p", lambda p, now: p.connect(lambda s: False, now))
        except Exception:
            pass
        before = store.snapshot("p")["retry_in"]
        c.jump_wall(10 ** 6)
        self.assertEqual(store.snapshot("p")["retry_in"], before)


class SupervisorTest(unittest.TestCase):
    @covers("G12-E061:unit,impl-doc,fault")
    def test_restart_backoff_then_give_up(self):
        clk = [0.0]
        sleeps = []
        runs = []

        def worker(stop):
            runs.append(1)
            raise RuntimeError("crash")
        sup = st.Supervisor(worker, st.RestartPolicy(max_restarts=3, window=60), clock=lambda: clk[0], sleep=sleeps.append)
        sup.run()
        self.assertTrue(sup.gave_up)
        self.assertEqual(len(runs), 4)
        self.assertEqual(sleeps, [0.5, 1.0, 2.0])


class DependencyTest(unittest.TestCase):
    @covers("G12-E062:unit,impl-doc", "G12-E063:unit,impl-doc", "G12-G078:deps")
    def test_dependency_view_and_degraded_policy(self):
        h = st.DependencyHealth(stale_after=30)
        for d in st.DEPENDENCIES:
            h.report(d, True, 0)
        self.assertEqual(st.degraded_policy(h.view(10))["new_sessions"], "allowed")
        h.report("identity", False, 10)
        pol = st.degraded_policy(h.view(10))
        self.assertEqual(pol["new_sessions"], "refused")
        self.assertEqual(pol["existing_trusted_sessions"], "continue_until_trust_expiry")
        self.assertEqual(h.state("dns", 100), "stale")
        self.assertEqual(st.degraded_policy(h.view(100))["config_changes"], "frozen_last_known_good")
        with self.assertRaises(KeyError):
            h.report("unknown-dep", True, 0)


class QuarantineTest(unittest.TestCase):
    @covers("G12-E064:unit,impl-doc")
    def test_quarantine_with_expiry_and_release(self):
        q = st.Quarantine()
        q.add("backend:upnp", reason="crash loop", actor="op", until=100)
        self.assertTrue(q.blocked("backend:upnp", 50))
        self.assertFalse(q.blocked("backend:upnp", 100))
        q.add("peer:x", reason="abuse", actor="auto")
        q.release("peer:x")
        self.assertFalse(q.blocked("peer:x", 0))


if __name__ == "__main__":
    unittest.main()
