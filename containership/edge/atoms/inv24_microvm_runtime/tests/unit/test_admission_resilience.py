"""MC-005, MC-027..MC-033, MC-037, MC-051: admission, quotas, idempotency, leases, controls, races, faults."""
import os
import random
import threading
import time
import unittest

from inv24_microvm_runtime.tests.helpers import keyring, tmpdir

from inv24_microvm_runtime.admission import AdmissionController, Capacity
from inv24_microvm_runtime.errors import Inv24Error
from inv24_microvm_runtime.resilience import (CancelToken, CircuitBreaker, ControlPlane, Deadline, HealthMonitor,
                                              LeaseStore, OperationJournal, RetryPolicy, retry)
from inv24_microvm_runtime.security.identity import TokenAuthority

CAP = Capacity(max_instances=4, max_instances_per_tenant=2, vcpus_total=8, memory_mib_total=2048,
               queue_depth=8, per_tenant_queue_depth=4)


class Harness:
    def __init__(self, capacity=CAP, launcher=None):
        self.dir = tmpdir()
        self.auth = TokenAuthority(keyring())
        self.launched = []
        self.decisions = []
        self.controls = ControlPlane()
        self.journal = OperationJournal(os.path.join(self.dir, "ops.jsonl"))
        self.ac = AdmissionController(authority=self.auth, journal=self.journal, controls=self.controls,
                                      capacity=capacity, launcher=launcher or self._launch,
                                      on_decision=self.decisions.append,
                                      release={"runtime": "4.3.0"}, policy={"config_revision": 1})

    def _launch(self, req):
        self.launched.append(req["workload"])
        return {"instance": req["workload"], "state": "running"}

    def req(self, key, tenant="t1", workload=None, **kw):
        r = {"schema": "PK_MICROVM_ADMISSION/1", "operation_key": key, "tenant": tenant,
             "workload": workload or key, "environment": "datacenter", "site": "s1", "vcpus": 1,
             "memory_mib": 128, "devices": ["serial"], "deadline_ms": 2000,
             "capability_token": self.auth.issue("svc", "workload", {"microvm:create"}, tenant=tenant)}
        r.update(kw)
        return r


class AdmissionTest(unittest.TestCase):
    def test_accept_and_decision_record(self):
        h = Harness()
        self.assertEqual(h.ac.admit(h.req("op-00001"))["state"], "running")
        d = h.decisions[-1].to_dict()
        self.assertEqual((d["outcome"], d["policy"]["config_revision"], d["release"]["runtime"]), ("accepted", 1, "4.3.0"))

    def test_rejections_happen_before_side_effects(self):
        h = Harness()
        cases = [
            (h.req("op-00002", capability_token="bogus"), "UNAUTHENTICATED"),
            (h.req("op-00003", tenant="t2", capability_token=h.auth.issue("s", "workload", {"microvm:create"}, tenant="t1")), "TENANT_MISMATCH"),
            (h.req("op-00004", capability_token=h.auth.issue("s", "workload", {"microvm:stop"}, tenant="t1")), "UNAUTHORIZED"),
            (h.req("op-00005", devices=["pci"]), "SCHEMA_VIOLATION"),
            (h.req("op-00006", vcpus=64), "SCHEMA_VIOLATION"),
            ({**h.req("op-00007"), "extra": 1}, "SCHEMA_VIOLATION"),
        ]
        for req, code in cases:
            with self.subTest(code=code), self.assertRaises(Inv24Error) as cm:
                h.ac.admit(req)
            self.assertEqual(cm.exception.code, code)
        self.assertEqual(h.launched, [])
        self.assertTrue(all(d.outcome == "rejected" for d in h.decisions))

    def test_quota_fleet_tenant_and_headroom(self):
        h = Harness()
        h.ac.admit(h.req("op-a0001"))
        h.ac.admit(h.req("op-a0002"))
        with self.assertRaises(Inv24Error) as cm:
            h.ac.admit(h.req("op-a0003"))
        self.assertEqual(cm.exception.code, "QUOTA_EXCEEDED")
        with self.assertRaises(Inv24Error):
            h.ac.admit(h.req("op-b0001", tenant="t2", memory_mib=4096))
        h.ac.release_instance("op-a0001")
        h.ac.admit(h.req("op-a0003"))

    def test_idempotent_retry_and_restart(self):
        h = Harness()
        r = h.req("op-idem0001")
        h.ac.admit(r)
        again = dict(r, capability_token=h.auth.issue("svc", "workload", {"microvm:create"}, tenant="t1"))
        self.assertTrue(h.ac.admit(again)["idempotent_replay"])
        self.assertEqual(h.launched, ["op-idem0001"])
        # controller restart: new journal object from the same file
        h2 = Harness()
        h2.journal = OperationJournal(h.journal.path)
        h2.ac.journal = h2.journal
        again2 = dict(r, capability_token=h2.auth.issue("svc", "workload", {"microvm:create"}, tenant="t1"))
        h2.ac.authority = h2.auth
        self.assertTrue(h2.ac.admit(again2)["idempotent_replay"])
        self.assertEqual(h2.launched, [])
        with self.assertRaises(Inv24Error) as cm:
            h2.ac.admit(dict(again2, vcpus=2, capability_token=h2.auth.issue("svc", "workload", {"microvm:create"}, tenant="t1")))
        self.assertEqual(cm.exception.code, "DUPLICATE_OPERATION")

    def test_torn_journal_line_tolerated(self):
        path = os.path.join(tmpdir(), "ops.jsonl")
        j = OperationJournal(path)
        j.record("k1", "d", "done", {})
        with open(path, "a") as fh:
            fh.write('{"key": "k2", "dig')
        self.assertIsNotNone(OperationJournal(path).lookup("k1", "d"))

    def test_launcher_failure_releases_reservation(self):
        def boom(req):
            raise Inv24Error("GUEST_BOOT_FAILED", "x")
        h = Harness(launcher=boom)
        with self.assertRaises(Inv24Error):
            h.ac.admit(h.req("op-fail0001"))
        self.assertEqual(h.ac.stats()["running"], 0)

    def test_overload_is_bounded_and_fair(self):
        gate = threading.Event()
        order = []

        def slow(req):
            order.append(req["tenant"])
            gate.wait(2)
            return {"instance": req["workload"]}
        cap = Capacity(100, 100, 1000, 100000, queue_depth=6, per_tenant_queue_depth=3)
        h = Harness(cap, launcher=slow)
        errors = []

        def go(key, tenant):
            try:
                h.ac.admit(h.req(key, tenant=tenant))
            except Inv24Error as e:
                errors.append(e.code)
        threads = [threading.Thread(target=go, args=(f"op-x{t}{i:05d}", t)) for t in ("a", "b") for i in range(5)]
        threads.insert(0, threading.Thread(target=go, args=("op-first0001", "c")))
        for t in threads:
            t.start()
            time.sleep(0.01)
        time.sleep(0.2)
        self.assertLessEqual(h.ac.stats()["queued"], 6)
        gate.set()
        for t in threads:
            t.join(10)
        self.assertIn("OVERLOADED", errors)
        # after the first, tenants alternate a/b rather than one tenant draining first
        seq = [x for x in order if x in "ab"]
        self.assertTrue(all(seq[i] != seq[i + 1] for i in range(min(len(seq), 4) - 1)), seq)

    def test_queued_deadline_times_out(self):
        gate = threading.Event()
        h = Harness(launcher=lambda r: gate.wait(1) or {"ok": 1})
        t = threading.Thread(target=h.ac.admit, args=(h.req("op-hold0001"),))
        t.start()
        time.sleep(0.05)
        with self.assertRaises(Inv24Error) as cm:
            h.ac.admit(h.req("op-late0001", tenant="t2", deadline_ms=100))
        self.assertEqual(cm.exception.code, "TIMEOUT")
        gate.set()
        t.join()

    def test_concurrent_admissions_never_exceed_caps(self):
        cap = Capacity(10, 10, 1000, 100000, queue_depth=200, per_tenant_queue_depth=200)
        h = Harness(cap)
        errs = []

        def go(i):
            try:
                h.ac.admit(h.req(f"op-race{i:05d}", tenant="t1"))
            except Inv24Error as e:
                errs.append(e.code)
        ts = [threading.Thread(target=go, args=(i,)) for i in range(50)]
        [t.start() for t in ts]
        [t.join(10) for t in ts]
        self.assertEqual(len(h.launched), 10)
        self.assertEqual(len(set(h.launched)), 10)
        self.assertEqual(set(errs), {"QUOTA_EXCEEDED"})


class ControlsTest(unittest.TestCase):
    def test_quarantine_freeze_degraded(self):
        h = Harness()
        op = h.auth.verify(h.auth.issue("ops", "operator", {"operator:quarantine", "operator:freeze"}))
        with self.assertRaises(Inv24Error):
            h.controls.quarantine(None, "tenant", "t1", "x")
        weak = h.auth.verify(h.auth.issue("svc", "workload", {"microvm:create"}, tenant="t1"))
        with self.assertRaises(Inv24Error):
            h.controls.freeze(weak, True, "x")
        h.controls.quarantine(op, "tenant", "t1", "incident-1")
        with self.assertRaises(Inv24Error) as cm:
            h.ac.admit(h.req("op-q0000001"))
        self.assertEqual(cm.exception.code, "QUARANTINED")
        self.assertFalse(h.controls.may_keep_running(tenant="t1", instance="i"))
        h.controls.release(op, "tenant", "t1", "resolved")
        h.controls.freeze(op, True, "rollout halt")
        with self.assertRaises(Inv24Error) as cm:
            h.ac.admit(h.req("op-q0000002"))
        self.assertEqual(cm.exception.code, "ADMISSION_FROZEN")
        h.controls.freeze(op, False, "resume")
        h.controls.set_mode("offline", "control plane partitioned")
        with self.assertRaises(Inv24Error) as cm:
            h.ac.admit(h.req("op-q0000003"))
        self.assertEqual(cm.exception.code, "DEGRADED_REFUSED")
        self.assertFalse(h.controls.may_keep_running(tenant="t2", instance="i"))
        serve = ControlPlane(degraded_policy="serve_existing")
        serve.set_mode("degraded", "x")
        self.assertTrue(serve.may_keep_running(tenant="t2", instance="i"))


class RetryBreakerTest(unittest.TestCase):
    def test_retry_only_retryable_and_bounded(self):
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise Inv24Error("OVERLOADED", "busy")
            return "ok"
        self.assertEqual(retry(flaky, policy=RetryPolicy(5, 0.001, 0.01), rng=random.Random(1)), "ok")
        calls.clear()

        def fatal():
            calls.append(1)
            raise Inv24Error("UNAUTHORIZED", "no")
        with self.assertRaises(Inv24Error):
            retry(fatal)
        self.assertEqual(len(calls), 1)

    def test_retry_respects_deadline_and_cancel(self):
        def busy():
            raise Inv24Error("OVERLOADED", "x")
        with self.assertRaises(Inv24Error) as cm:
            retry(busy, policy=RetryPolicy(10, 1.0, 5.0), deadline=Deadline.after_ms(50), rng=random.Random(0))
        self.assertEqual(cm.exception.code, "TIMEOUT")
        tok = CancelToken()
        tok.cancel("shutdown")
        with self.assertRaises(Inv24Error) as cm:
            retry(busy, cancel=tok)
        self.assertEqual(cm.exception.code, "CANCELLED")
        with self.assertRaises(Inv24Error):
            Deadline.after_ms(0)

    def test_jitter_is_bounded(self):
        p = RetryPolicy(10, 0.1, 1.0)
        rng = random.Random(7)
        self.assertTrue(all(0 <= p.delay(a, rng) <= 1.0 for a in range(20)))

    def test_breaker_open_half_open_close(self):
        t = [0.0]
        b = CircuitBreaker("kvm", failure_threshold=2, reset_s=5, clock=lambda: t[0])
        for _ in range(2):
            with self.assertRaises(RuntimeError):
                b.call(lambda: (_ for _ in ()).throw(RuntimeError()))
        with self.assertRaises(Inv24Error) as cm:
            b.call(lambda: 1)
        self.assertEqual(cm.exception.code, "CIRCUIT_OPEN")
        t[0] = 6
        self.assertEqual(b.call(lambda: 1), 1)
        self.assertEqual(b.state, "closed")


class LeaseTest(unittest.TestCase):
    def test_fencing_and_takeover(self):
        t = [100.0]
        ls = LeaseStore(os.path.join(tmpdir(), "leases.json"), clock=lambda: t[0])
        e1 = ls.acquire("vm1", "ctl-a", ttl_s=10)
        with self.assertRaises(Inv24Error) as cm:
            ls.acquire("vm1", "ctl-b")
        self.assertEqual(cm.exception.code, "LEASE_HELD")
        t[0] += 11                                  # ctl-a partitioned; lease expires
        e2 = ls.acquire("vm1", "ctl-b")
        self.assertEqual(e2, e1 + 1)
        with self.assertRaises(Inv24Error) as cm:   # stale owner comes back
            ls.fence("vm1", e1)
        self.assertEqual(cm.exception.code, "STALE_EPOCH")
        with self.assertRaises(Inv24Error):
            ls.renew("vm1", "ctl-a", e1)
        ls.fence("vm1", e2)

    def test_concurrent_acquire_single_winner(self):
        ls = LeaseStore(os.path.join(tmpdir(), "leases.json"))
        wins = []

        def go(o):
            try:
                ls.acquire("vmX", o)
                wins.append(o)
            except Inv24Error:
                pass
        ts = [threading.Thread(target=go, args=(f"c{i}",)) for i in range(20)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(wins), 1)


class HealthTest(unittest.TestCase):
    def test_probes_timeouts_stalls_and_mode(self):
        t = [0.0]
        hm = HealthMonitor(stall_after_s=5, probe_timeout_s=0.1, clock=lambda: t[0])
        hm.register("kvm", lambda: True)
        hm.register("hang", lambda: time.sleep(1) or True, required=False)
        hm.register("crash", lambda: 1 / 0, required=False)
        hm.beat("vm1")
        hm.beat("vm2")
        t[0] = 3
        hm.beat("vm2")
        t[0] = 6
        r = hm.report()
        self.assertTrue(r.ready)
        self.assertEqual(r.stalled, ["vm1"])
        detail = {p.name: p for p in r.probes}
        self.assertEqual(detail["hang"].detail, "probe timed out")
        self.assertFalse(detail["crash"].ok)
        hm.register("kvm", lambda: False)
        self.assertFalse(hm.report().ready)
        hm.register("kvm", lambda: True)
        hm.mode_fn = lambda: "degraded"
        self.assertFalse(hm.report().ready)


if __name__ == "__main__":
    unittest.main()
