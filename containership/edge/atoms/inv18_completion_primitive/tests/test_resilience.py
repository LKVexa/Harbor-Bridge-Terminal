"""Resilience: faults, retries, circuit breaking, failover/fencing, partition, restart, degraded
operation (C018, C051-C060, C089)."""
import json
import os
import signal
import subprocess
import sys
import time
import unittest

from _util import m, PKG_DIR, ROOT, rt as make_rt

fault = m("fault")
retry = m("retry")
errors = m("errors")
adapters = m("adapters")
auth = m("auth")


def _net(rt=None):
    rt = rt or make_rt()
    kr = auth.KeyRing(); kr.add("k1", b"k" * 32)
    au = auth.Authenticator(kr)
    ep = adapters.RemoteEndpoint(rt, au)
    link = adapters.Link(ep)
    return rt, au, ep, link


class FaultTest(unittest.TestCase):
    def test_fault_suite(self):
        """REQ: C060 C051 C089 C056"""
        res = fault.run_all()
        self.assertEqual(len(res), len(fault.SCENARIOS))
        failed = [r for r in res if not r["passed"]]
        self.assertEqual(failed, [])
        for r in res:
            self.assertEqual(r["invariants"], [])

    def test_invariant_checker_detects_violation(self):
        """REQ: C060 — the harness must be able to fail"""
        rt = make_rt()
        rt.record_invariant_violation("synthetic")
        self.assertTrue(fault.invariants(rt))
        rt2 = make_rt()
        rt2._per_tenant["ghost"] = 3
        self.assertIn("tenant accounting drift", fault.invariants(rt2))


class RetryTest(unittest.TestCase):
    def test_bounded_retries_with_jitter(self):
        """REQ: C053"""
        sleeps = []
        p = retry.RetryPolicy(max_attempts=4, base_delay_s=0.1, max_delay_s=0.3, max_total_s=10, seed=5,
                              sleep=sleeps.append)
        calls = []
        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise errors.Rejected("down", code="DEPENDENCY_UNAVAILABLE")
            return "ok"
        self.assertEqual(p.call(flaky), "ok")
        self.assertEqual(len(calls), 3)
        self.assertEqual(len(sleeps), 2)
        self.assertTrue(all(0 <= s <= 0.3 for s in sleeps))
        self.assertNotEqual(sleeps[0], sleeps[1])

    def test_permanent_failure_does_not_retry_forever(self):
        """REQ: C053"""
        n = []
        p = retry.RetryPolicy(max_attempts=5, base_delay_s=0, seed=1, sleep=lambda s: None)
        def down():
            n.append(1); raise errors.Rejected("down", code="DEPENDENCY_UNAVAILABLE")
        with self.assertRaises(errors.Rejected) as cm:
            p.call(down)
        self.assertEqual(cm.exception.code, "DEPENDENCY_UNAVAILABLE")
        self.assertEqual(len(n), 5)
        n.clear()
        def terminal():
            n.append(1); raise errors.Rejected("no", code="PERMISSION_DENIED")
        with self.assertRaises(errors.Rejected):
            p.call(terminal)
        self.assertEqual(len(n), 1)                     # non-retryable codes never retry

    def test_retry_honours_deadline_and_cancellation(self):
        """REQ: C053 C025"""
        now = [0.0]
        def sleep(s):
            now[0] += s
        p = retry.RetryPolicy(max_attempts=100, base_delay_s=1.0, max_delay_s=1.0, max_total_s=1000, seed=2,
                              sleep=sleep, clock=lambda: now[0])
        def down():
            raise errors.Rejected("down", code="TIMEOUT")
        with self.assertRaises(errors.Rejected):
            p.call(down, deadline=3.0)
        self.assertLessEqual(now[0], 3.0)
        flag = {"c": False}
        def cancel_after_first():
            flag["c"] = True
            raise errors.Rejected("down", code="TIMEOUT")
        with self.assertRaises(errors.Rejected) as cm:
            retry.RetryPolicy(max_attempts=5, base_delay_s=0, sleep=lambda s: None).call(
                cancel_after_first, cancelled=lambda: flag["c"])
        self.assertEqual(cm.exception.code, "FUTURE_CANCELLED")

    def test_local_transitions_are_not_retryable(self):
        """REQ: C053 INV18-FR-001"""
        rt = make_rt()
        w, r = rt.create(int)
        rt.resolve(w, 1)
        p = retry.RetryPolicy(max_attempts=5, base_delay_s=0, sleep=lambda s: None)
        with self.assertRaises(m("future").AlreadyResolved):
            p.call(lambda: rt.resolve(w, 2))
        self.assertEqual(p.attempts_made, 1)


class CircuitTest(unittest.TestCase):
    def test_transitions_with_hysteresis(self):
        """REQ: C054"""
        now = [0.0]
        cb = retry.CircuitBreaker(failure_threshold=3, reset_s=10, close_successes=2, clock=lambda: now[0])
        def bad():
            raise errors.Rejected("x", code="DEPENDENCY_UNAVAILABLE")
        for _ in range(3):
            with self.assertRaises(errors.Rejected):
                cb.call(bad)
        self.assertEqual(cb.state, "open")
        with self.assertRaises(errors.Rejected) as cm:
            cb.call(lambda: 1)
        self.assertEqual(cm.exception.code, "DEPENDENCY_UNAVAILABLE")
        now[0] = 11
        self.assertEqual(cb.call(lambda: 1), 1)
        self.assertEqual(cb.state, "half_open")          # one success is not enough (no flapping)
        cb.call(lambda: 1)
        self.assertEqual(cb.state, "closed")
        for _ in range(3):
            with self.assertRaises(errors.Rejected):
                cb.call(bad)
        now[0] = 30
        cb.allow()
        with self.assertRaises(errors.Rejected):
            cb.call(bad)
        self.assertEqual(cb.state, "open")               # half-open failure reopens immediately
        self.assertIn("half_open->open", cb.transitions)

    def test_terminal_errors_do_not_trip_breaker(self):
        """REQ: C054"""
        cb = retry.CircuitBreaker(failure_threshold=2)
        for _ in range(5):
            with self.assertRaises(errors.Rejected):
                cb.call(lambda: (_ for _ in ()).throw(errors.Rejected("bad", code="INVALID_ARGUMENT")))
        self.assertEqual(cb.state, "closed")


class DistributedTest(unittest.TestCase):
    def test_duplicate_delivery_is_idempotent(self):
        """REQ: C025 C058 C089 — T13 lost responses and retries never double-resolve"""
        rt, au, ep, link = _net()
        cli = adapters.RemoteClient(link, au, "t", ["create", "resolve", "receive"])
        fid = cli.create("int")["result"]["future_id"]
        link.drop_responses = 3
        r = cli.resolve(fid, 11, key="op-1")
        self.assertTrue(r["ok"])
        self.assertEqual(link.delivered, 5)             # 1 create + 4 deliveries of the same resolve
        self.assertEqual(rt.metrics.counter("inv18_double_resolutions_total"), 0)
        self.assertEqual(cli.take(fid, "int")["result"], {"outcome": "ok", "value": 11})

    def test_stale_owner_fenced(self):
        """REQ: C055 C058 — T14 split brain"""
        rt, au, ep, link = _net()
        old = adapters.RemoteClient(link, au, "t", ["create", "resolve", "receive"])
        admin = adapters.RemoteClient(link, au, "t", ["administer"])
        fid = old.create("int", epoch=1)["result"]["future_id"]
        self.assertTrue(admin.fence(fid, 2, "int")["ok"])              # failover to epoch 2
        stale = old.resolve(fid, 1, epoch=1)
        self.assertEqual(stale["error"]["code"], "STALE_EPOCH")
        self.assertTrue(old.resolve(fid, 2, epoch=2)["ok"])            # new owner resolves
        self.assertEqual(admin.fence(fid, 2, "int")["error"]["code"], "STALE_EPOCH")  # no epoch reuse
        self.assertEqual(old.take(fid, "int")["result"]["value"], 2)
        other = adapters.RemoteClient(link, au, "other-tenant", ["administer", "create"])
        fid2 = old.create("int")["result"]["future_id"]
        self.assertEqual(other.fence(fid2, 9, "int")["error"]["code"], "PERMISSION_DENIED")  # cross-tenant fence

    def test_simultaneous_owners_single_winner(self):
        """REQ: C058 C086"""
        import threading
        rt, au, ep, link = _net()
        c = adapters.RemoteClient(link, au, "t", ["create", "resolve", "receive"])
        fid = c.create("int")["result"]["future_id"]
        outs = []
        def owner(i):
            cl = adapters.RemoteClient(link, au, "t", ["resolve"])
            outs.append(cl.resolve(fid, i, key=f"owner-{i}")["ok"])
        ts = [threading.Thread(target=owner, args=(i,)) for i in range(8)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(outs.count(True), 1)

    def test_partition_and_reconnect(self):
        """REQ: C018 C089"""
        rt, au, ep, link = _net()
        cli = adapters.RemoteClient(link, au, "t", ["create", "resolve", "receive"])
        fid = cli.create("str")["result"]["future_id"]
        link.partitioned = True
        with self.assertRaises(errors.Rejected) as cm:
            cli.resolve(fid, "v", key="k-part")
        self.assertEqual(cm.exception.code, "DEPENDENCY_UNAVAILABLE")
        link.partitioned = False                                       # heal
        self.assertTrue(cli.resolve(fid, "v", key="k-part")["ok"])
        self.assertTrue(cli.resolve(fid, "v", key="k-part")["ok"])     # delayed duplicate absorbed
        self.assertEqual(cli.take(fid, "str")["result"]["value"], "v")

    def test_remote_producer_disappears(self):
        """REQ: C018 C025 C089 — receiver deadline + explicit abandon"""
        rt, au, ep, link = _net()
        cli = adapters.RemoteClient(link, au, "t", ["create", "resolve", "receive", "abandon"])
        fid = cli.create("int")["result"]["future_id"]
        self.assertEqual(cli.take(fid, "int")["result"], {"pending": True})
        self.assertTrue(cli.abandon(fid, reason="writer_crashed")["ok"])
        self.assertEqual(cli.take(fid, "int")["error"]["code"], "FUTURE_ABANDONED")
        self.assertEqual(ep.live, 0)

    def test_endpoint_state_bounded(self):
        """REQ: C067 C028"""
        rt, au, ep, link = _net()
        ep._released_max = 50
        ep._idem_max = 50
        cli = adapters.RemoteClient(link, au, "t", ["create", "resolve", "receive"])
        for i in range(200):
            fid = cli.create("int")["result"]["future_id"]
            cli.resolve(fid, i); cli.take(fid, "int")
        self.assertEqual(ep.live, 0)
        self.assertLessEqual(len(ep._released), 50)
        self.assertLessEqual(len(ep._idem), 50)


class RestartTest(unittest.TestCase):
    def test_process_termination_and_restart(self):
        """REQ: C057 C089 C051 — pending futures do not survive; old epoch is fenced"""
        code = (
            "import sys,time,json; sys.path.insert(0,%r); import %s.runtime as r;"
            "rt=r.Runtime({'environment':'test'}); w,q=rt.create(int);"
            "print(json.dumps({'epoch':rt.epoch,'fid':w.future_id}),flush=True); time.sleep(60)"
        ) % (str(ROOT), PKG_DIR.name)
        p = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
        first = json.loads(p.stdout.readline())
        p.send_signal(signal.SIGKILL if hasattr(signal, "SIGKILL") else signal.SIGTERM)
        p.wait(10)
        p.stdout.close()
        rt2 = make_rt()                                             # restarted process: empty, new epoch
        self.assertEqual(rt2.outstanding, 0)
        self.assertNotEqual(rt2.epoch, first["epoch"])
        stale = m("runtime").ResolverCap(first["fid"], "default", "0" * 32, "resolver")
        with self.assertRaises(errors.Rejected) as cm:
            rt2.resolve(stale, 1)
        self.assertEqual(cm.exception.code, "PERMISSION_DENIED")

    def test_crash_at_transition_boundary(self):
        """REQ: C057 C060 — an exception inside the observer hook after commit leaves a consistent state"""
        rt = make_rt()
        w, r = rt.create(int)
        orig = rt.metrics.inc
        def boom(*a, **k):
            raise RuntimeError("crash mid-telemetry")
        rt.metrics.inc = boom
        rt.resolve(w, 5)                                            # telemetry crash swallowed after commit
        rt.metrics.inc = orig
        self.assertEqual(rt.take(r), ("ok", 5))
        self.assertEqual(fault.invariants(rt, telemetry=False), [])


class DegradedTest(unittest.TestCase):
    def test_each_noncritical_dependency_disabled(self):
        """REQ: C056 C089"""
        def broken(_):
            raise OSError("sink down")
        rt = m("runtime").Runtime(m("config").ConfigStore({"environment": "test"}), log_sink=broken)
        w, r = rt.create(int)
        try:
            rt.resolve(w, "bad")
        except TypeError:
            pass
        rt.resolve(w, 1)
        self.assertEqual(rt.take(r), ("ok", 1))
        h = rt.health()
        self.assertEqual(h["state"], "DEGRADED")
        self.assertEqual(h["dependencies"]["telemetry_sink"], "unavailable")
        self.assertTrue(h["ready"])                                 # still serving
        self.assertGreater(rt.metrics.counter("inv18_telemetry_dropped_total"), 0)
        rt.set_dependency("pk_core", "unavailable")                 # audit integration down
        w, r = rt.create(int); rt.resolve(w, 2); self.assertEqual(rt.take(r), ("ok", 2))


if __name__ == "__main__":
    unittest.main()
