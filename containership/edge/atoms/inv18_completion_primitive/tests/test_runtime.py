"""Governed runtime: capabilities, limits, quotas, disable, health, metrics (C006, C017, C024, C028,
C042, C052, C054, C059, C067, C071, C072, C076)."""
import gc
import threading
import unittest

from _util import m, rt as make_rt

runtime = m("runtime")
errors = m("errors")
future = m("future")
telemetry = m("telemetry")


class CapabilityTest(unittest.TestCase):
    def test_capability_kinds_are_separated(self):
        """REQ: C024 C042 C082 INV18-SEC-001"""
        rt = make_rt()
        w, r = rt.create(int)
        o = rt.observer(w)
        for fn, cap in ((rt.take, w), (rt.cancel, w), (rt.take, o)):
            with self.assertRaises(errors.Rejected) as cm:
                fn(cap)
            self.assertEqual(cm.exception.code, "PERMISSION_DENIED")
        for fn, cap in ((rt.resolve, r), (rt.resolve, o)):
            with self.assertRaises(errors.Rejected):
                fn(cap, 1)
        with self.assertRaises(errors.Rejected):
            rt.abandon(o)
        self.assertEqual(rt.inspect(o)["state"], "PENDING")
        rt.resolve(w, 1)
        self.assertEqual(rt.take(r), ("ok", 1))

    def test_writer_drop_abandons(self):
        """REQ: C003 C051 INV18-FR-014 INV18-FR-005"""
        rt = make_rt()
        w, r = rt.create(str)
        del w
        gc.collect()
        with self.assertRaises(future.Abandoned):
            rt.take(r)
        self.assertEqual(rt.outstanding, 0)

    def test_writer_drop_after_resolution_is_harmless(self):
        """REQ: C015 INV18-FR-014"""
        rt = make_rt()
        w, r = rt.create(str)
        rt.resolve(w, "v")
        del w
        gc.collect()
        self.assertEqual(rt.take(r), ("ok", "v"))

    def test_second_receiver_after_release_gets_already_taken(self):
        """REQ: C082 INV18-FR-008 INV18-FR-007"""
        rt = make_rt()
        w, r = rt.create(int)
        rt.resolve(w, 1)
        rt.take(r)
        self.assertEqual(rt.outstanding, 0)
        with self.assertRaises(future.AlreadyTaken):
            rt.take(r)
        with self.assertRaises(future.AlreadyResolved):
            rt.resolve(w, 2)
        self.assertFalse(rt.abandon(w))
        self.assertFalse(rt.cancel(r))
        self.assertEqual(rt.inspect(r)["state"], "RELEASED")

    def test_take_wait_timeout_leaves_future_intact(self):
        """REQ: C025 INV18-FR-015"""
        rt = make_rt()
        w, r = rt.create(int)
        with self.assertRaises(errors.Rejected) as cm:
            rt.take_wait(r, 0.01)
        self.assertEqual(cm.exception.code, "TIMEOUT")
        self.assertTrue(cm.exception.record().retryable)
        rt.resolve(w, 5)
        self.assertEqual(rt.take_wait(r, 1), ("ok", 5))

    def test_cancel_via_runtime(self):
        """REQ: C025 INV18-FR-013"""
        rt = make_rt()
        w, r = rt.create(int)
        self.assertTrue(rt.cancel(r))
        with self.assertRaises(future.Cancelled):
            rt.resolve(w, 1)
        self.assertEqual(rt.outstanding, 0)

    def test_tenant_identifier_validated(self):
        """REQ: C006 C028 INV18-FR-009"""
        rt = make_rt()
        for bad in ("", "a" * 129, "bad tenant", None, "../x"):
            with self.assertRaises(errors.Rejected):
                rt.create(int, tenant=bad)
        with self.assertRaises(TypeError):
            rt.create("int")


class LimitsTest(unittest.TestCase):
    def test_process_limit_boundary(self):
        """REQ: C017 C028 C054 C067 INV18-NFR-001"""
        rt = make_rt(max_outstanding=10, soft_outstanding=8, max_per_tenant=10)
        caps = [rt.create(int) for _ in range(10)]          # exact boundary admitted
        with self.assertRaises(errors.Rejected) as cm:       # boundary + 1 refused
            rt.create(int)
        self.assertEqual(cm.exception.code, "RESOURCE_EXHAUSTED")
        self.assertEqual(rt.metrics.counter("inv18_limit_hits_total", limit="process"), 1)
        self.assertIn("SOFT_LIMIT_EXCEEDED", rt.health()["reasons"])
        w, r = caps[0]
        rt.resolve(w, 1); rt.take(r)
        rt.create(int)                                       # capacity recovered
        self.assertEqual(rt.decisions.summary().get("OVERLOAD_REJECTED"), 1)

    def test_tenant_quota_isolates_noisy_neighbour(self):
        """REQ: C017 C046 C064 INV18-NFR-001"""
        rt = make_rt(max_outstanding=100, soft_outstanding=100, max_per_tenant=5)
        for _ in range(5):
            rt.create(int, tenant="noisy")
        with self.assertRaises(errors.Rejected) as cm:
            rt.create(int, tenant="noisy")
        self.assertEqual(cm.exception.code, "RESOURCE_EXHAUSTED")
        rt.create(int, tenant="quiet")                        # other tenants unaffected
        self.assertEqual(rt.tenant_outstanding("noisy"), 5)
        self.assertEqual(rt.tenant_outstanding("quiet"), 1)

    def test_release_reclaims_registry(self):
        """REQ: C067 INV18-NFR-002"""
        rt = make_rt()
        for _ in range(1000):
            w, r = rt.create(int); rt.resolve(w, 1); rt.take(r)
        self.assertEqual(rt.outstanding, 0)
        self.assertEqual(rt.metrics.gauge("inv18_futures_open"), 0)
        self.assertLessEqual(len(rt._tombs), runtime.TOMBSTONES)

    def test_bounded_rings(self):
        """REQ: C067 C075"""
        rt = make_rt(max_diag_records=16, telemetry_queue_max=16)
        w, r = rt.create(int)
        rt.resolve(w, 1)
        for _ in range(100):
            try:
                rt.resolve(w, 2)
            except future.AlreadyResolved:
                pass
        self.assertLessEqual(len(rt.decisions.records), 16)
        self.assertLessEqual(len(rt.log.records), 16)


class DisableTest(unittest.TestCase):
    def test_drain_and_freeze(self):
        """REQ: C059 C092 INV18-OPS-004"""
        rt = make_rt()
        admin = rt.admin_capability()
        w, r = rt.create(int)
        w2, r2 = rt.create(int)
        rt.resolve(w2, 7)
        rt.disable(admin, mode="drain", reason="test")
        with self.assertRaises(errors.Rejected) as cm:
            rt.create(int)
        self.assertEqual(cm.exception.code, "COMPONENT_DISABLED")
        self.assertFalse(rt.health()["ready"])
        rt.resolve(w, 1)                                     # drain: existing may finish
        rt.disable(admin, mode="freeze")
        w3 = None
        self.assertEqual(rt.take(r2), ("ok", 7))             # freeze: resolved values still deliverable
        rt.enable(admin)
        self.assertTrue(rt.health()["ready"])
        actions = [e["action"] for e in rt.audit.events]
        self.assertIn("component.disable", actions)
        self.assertIn("component.enable", actions)

    def test_freeze_refuses_mutation(self):
        """REQ: C059 INV18-OPS-004"""
        rt = make_rt()
        admin = rt.admin_capability()
        w, r = rt.create(int)
        rt.disable(admin, mode="freeze")
        with self.assertRaises(errors.Rejected) as cm:
            rt.resolve(w, 1)
        self.assertEqual(cm.exception.code, "COMPONENT_DISABLED")

    def test_tenant_scope(self):
        """REQ: C059 C046"""
        rt = make_rt()
        rt.disable(rt.admin_capability(), scope="tenant:bad", mode="drain")
        with self.assertRaises(errors.Rejected):
            rt.create(int, tenant="bad")
        rt.create(int, tenant="good")
        with self.assertRaises(errors.Rejected):
            rt.disable(rt.admin_capability(), scope="site:x")

    def test_unauthorized_disable_refused(self):
        """REQ: C059 C042 C050 INV18-SEC-006"""
        rt = make_rt()
        other = make_rt()
        for cap in (None, other.admin_capability(), runtime.AdminCap(rt.runtime_id, "0" * 32)):
            with self.assertRaises(errors.Rejected) as cm:
                rt.disable(cap)
            self.assertEqual(cm.exception.code, "PERMISSION_DENIED")
        self.assertTrue(rt.health()["ready"])
        self.assertTrue(any(e["action"] == "admin.denied" for e in rt.audit.events))

    def test_disable_under_load(self):
        """REQ: C059 C089"""
        rt = make_rt()
        admin = rt.admin_capability()
        stop = threading.Event()
        errs = []
        def load():
            while not stop.is_set():
                try:
                    w, r = rt.create(int); rt.resolve(w, 1); rt.take(r)
                except errors.Rejected as exc:
                    if exc.code != "COMPONENT_DISABLED":
                        errs.append(exc.code)
        ts = [threading.Thread(target=load) for _ in range(4)]
        [t.start() for t in ts]
        rt.disable(admin); rt.enable(admin); rt.disable(admin)
        stop.set(); [t.join() for t in ts]
        self.assertEqual(errs, [])
        self.assertEqual(rt.metrics.counter("inv18_double_resolutions_total"), 0)


class HealthTest(unittest.TestCase):
    def test_states_and_reasons(self):
        """REQ: C052 C071 INV18-OPS-001"""
        now = [0.0]
        rt = runtime.Runtime(m("config").ConfigStore({"environment": "test", "stall_threshold_s": 10.0}),
                             clock=lambda: now[0])
        self.assertEqual(rt.health()["state"], "HEALTHY")
        caps = [rt.create(int) for _ in range(5)]
        now[0] = 11.0
        h = rt.health()
        self.assertEqual(h["stalled"], 5)
        self.assertIn("STALLED_FUTURES", h["reasons"])
        self.assertEqual(h["state"], "DEGRADED")
        rt.record_invariant_violation("synthetic")
        self.assertEqual(rt.health()["state"], "FAILED")
        self.assertFalse(rt.health()["ready"])

    def test_single_slow_producer_does_not_degrade(self):
        """REQ: C052 — transient/isolated delay is application delay, not malfunction"""
        now = [0.0]
        rt = runtime.Runtime(m("config").ConfigStore({"environment": "test", "stall_threshold_s": 10.0}),
                             clock=lambda: now[0])
        keep = rt.create(int)
        caps = []
        now[0] = 11.0
        for _ in range(20):
            caps.append(rt.create(int))
        h = rt.health()
        self.assertEqual(h["stalled"], 1)
        self.assertEqual(h["state"], "HEALTHY")


class ClockTest(unittest.TestCase):
    def test_clock_anomaly_affects_only_telemetry(self):
        """REQ: C051 C052"""
        vals = iter([100.0, 50.0, 50.0, 10.0] + [0.0] * 50)
        rt = runtime.Runtime(m("config").ConfigStore({"environment": "test"}), clock=lambda: next(vals))
        w, r = rt.create(int)
        rt.resolve(w, 1)
        self.assertEqual(rt.take(r), ("ok", 1))


class MetricsTest(unittest.TestCase):
    def test_metric_contract_under_deterministic_workload(self):
        """REQ: C072 INV18-OPS-005"""
        rt = make_rt()
        for i in range(10):
            w, r = rt.create(int)
            if i < 5:
                rt.resolve(w, 1)
            elif i < 8:
                rt.resolve_error(w, "e")
            else:
                rt.abandon(w)
            try:
                rt.take(r)
            except future.Abandoned:
                pass
        w, r = rt.create(int); rt.resolve(w, 1)
        with self.assertRaises(future.AlreadyResolved):
            rt.resolve(w, 2)
        c = rt.metrics.counter
        self.assertEqual(c("inv18_futures_created_total"), 11)
        self.assertEqual(c("inv18_values_resolved_total"), 6)
        self.assertEqual(c("inv18_errors_resolved_total"), 3)
        self.assertEqual(c("inv18_abandonments_total"), 2)
        self.assertEqual(c("inv18_takes_total"), 10)
        self.assertEqual(c("inv18_double_resolutions_total"), 1)
        self.assertEqual(c("inv18_rejections_total", code="FUTURE_ALREADY_RESOLVED"), 1)
        self.assertEqual(rt.metrics.gauge("inv18_futures_open"), 1)
        self.assertEqual(rt.metrics.percentiles("inv18_resolution_latency_seconds")["n"], 12 - 1)
        with self.assertRaises(KeyError):
            rt.metrics.inc("undeclared_metric")

    def test_label_cardinality_bounded(self):
        """REQ: C072 C075 INV18-OPS-005"""
        mt = telemetry.Metrics()
        for i in range(500):
            mt.inc("inv18_rejections_total", code=f"C{i}")
        keys = {k for k in mt.counters if k[0] == "inv18_rejections_total"}
        self.assertLessEqual(len(keys), telemetry.MAX_LABEL_VALUES + 1)
        self.assertEqual(mt.counter("inv18_rejections_total"), 500)


class PrecedenceTest(unittest.TestCase):
    def test_security_before_capacity_and_reason_codes(self):
        """REQ: C019 C076 C024"""
        rt = make_rt(max_outstanding=1, soft_outstanding=1, max_per_tenant=1)
        rt.create(int)
        rt.disable(rt.admin_capability())
        with self.assertRaises(errors.Rejected) as cm:      # both disabled and full: disabled wins
            rt.create(int)
        self.assertEqual(cm.exception.code, "COMPONENT_DISABLED")
        rec = rt.decisions.records[-1]
        self.assertEqual(rec["reason"], "DISABLED_REJECTED")
        self.assertEqual(rec["policy_version"], runtime.POLICY_VERSION)
        self.assertTrue(rec["config_revision"].startswith("cfg-"))

    def test_every_rejection_branch_has_a_decision(self):
        """REQ: C076"""
        rt = make_rt(max_outstanding=2, soft_outstanding=2, max_per_tenant=2)
        w, r = rt.create(int)
        rt.resolve(w, 1)
        keep = []
        for fn in (lambda: rt.resolve(w, 2), lambda: (rt.take(r), rt.take(r)), lambda: rt.take(w),
                   lambda: [keep.append(rt.create(int)) for _ in range(3)]):
            try:
                fn()
            except errors.FutureError:
                pass
        reasons = set(rt.decisions.summary())
        self.assertTrue({"RESOLVE_REJECTED", "TAKE_REJECTED", "AUTHZ_REJECTED", "OVERLOAD_REJECTED"} <= reasons, reasons)
        with self.assertRaises(KeyError):
            rt.decisions.record("NOT_DECLARED", code=None, config_revision=None, policy_version="x")


if __name__ == "__main__":
    unittest.main()
