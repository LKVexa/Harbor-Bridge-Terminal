"""Controller end-to-end, lifecycle, fencing, resilience, observability, runtime plan."""
import itertools
import random
import threading
import unittest

from _harness import FAKE_ARTIFACTS, Answer, Clock, build, token

from inv71_heavy_agent_sandbox.control import compat, lifecycle, qualify, resilience, telemetry
from inv71_heavy_agent_sandbox.control.config import merge
from inv71_heavy_agent_sandbox.control.errors import REGISTRY, ControlError, Outcome, RetryClass, map_exception
from inv71_heavy_agent_sandbox.control.lifecycle import State
from inv71_heavy_agent_sandbox.control.resilience import Shape
from inv71_heavy_agent_sandbox.control.runtime_plan import plan_session, reconcile
from inv71_heavy_agent_sandbox.sandbox import EgressDenied, LimitExceeded, SessionClosed


def code(tc, fn):
    with tc.assertRaises(ControlError) as cm:
        fn()
    return cm.exception.code.code


class EndToEndTest(unittest.TestCase):
    """[C030][C014][C015][C046][C083] create -> egress -> teardown with verified proof (reference path)."""

    def setUp(self):
        self.c, self.ta, self.clock, self.res, self.host, self.anchors = build()

    def create(self, sid="s1", tenant="t1", key="k1", shape=Shape(1, 512)):
        return self.c.create(token(self.ta, tenant=tenant), sid=sid, tenant=tenant, shape=shape,
                             idempotency_key=key, correlation_id="corr-1", release="app@sha256:" + "0" * 64)

    def test_full_lifecycle(self):
        r = self.create()
        self.assertEqual(r["state"], "READY")
        e = self.c.connect(token(self.ta), sid="s1", host="pypi.org", port=443)
        self.assertEqual(e["address"], "151.101.0.223")
        self.assertEqual(self.c.sessions["s1"].lifecycle.state, State.RUNNING)
        td = self.c.teardown(token(self.ta), sid="s1", epoch=r["epoch"])
        self.assertTrue(td["verified"])
        self.assertEqual(self.c.sessions["s1"].lifecycle.state, State.CLOSED)
        self.assertEqual(self.c.admission.usage("t1"), (0, 0, 0))
        hist = [h[1] for h in self.c.sessions["s1"].lifecycle.history]
        self.assertEqual(hist, ["VALIDATING", "ALLOCATING", "STARTING", "READY", "RUNNING", "DRAINING",
                                "STOPPING", "VERIFYING_TEARDOWN", "CLOSED"])
        from inv71_heavy_agent_sandbox.control.audit_log import verify_file
        self.assertTrue(verify_file(self.c.audit.path, key=b"a" * 32, anchors=self.anchors)[0])

    def test_idempotent_create_replay(self):
        a = self.create()
        b = self.create()
        self.assertEqual(a, b)
        self.assertEqual(self.c.admission.usage("t1")[0], 1)
        self.assertEqual(code(self, lambda: self.create(sid="s9")), "VALIDATION.MALFORMED_REQUEST")  # key reuse, new body

    def test_leaked_resource_blocks_closed(self):
        r = self.create()
        self.host.extra.add(("tap", self.c.sessions["s1"].plan.owned and
                             next(x for x in self.c.sessions["s1"].plan.owned if x[0] == "tap")[1]))
        self.assertEqual(code(self, lambda: self.c.teardown(token(self.ta), sid="s1", epoch=r["epoch"])),
                         "TEARDOWN.VERIFICATION_FAILED")
        self.assertEqual(self.c.sessions["s1"].lifecycle.state, State.QUARANTINED)
        self.assertEqual(self.c.metrics.value("heavybox_teardown_failures_total"), 1)

    def test_stale_epoch_rejected(self):
        r = self.create()
        self.c.leases.acquire("s1", "controller-b")  # failover took ownership
        self.assertEqual(code(self, lambda: self.c.teardown(token(self.ta), sid="s1", epoch=r["epoch"])),
                         "LIFECYCLE.STALE_EPOCH")

    def test_cross_tenant_and_forbidden_egress(self):
        self.create()
        self.assertEqual(code(self, lambda: self.c.connect(token(self.ta, tenant="t2"), sid="s1", host="pypi.org", port=443)),
                         "AUTHZ.TENANT_MISMATCH")
        self.assertEqual(code(self, lambda: self.c.connect(token(self.ta), sid="s1", host="evil.com", port=443)),
                         "POLICY.EGRESS_DENIED")
        self.assertEqual(self.c.metrics.value("heavybox_egress_denied_total", reason="POLICY.EGRESS_DENIED"), 1)
        ex = self.c.explain.explain("s1")
        self.assertTrue(any(r["reason_code"] == "POLICY.EGRESS_DENIED" for r in ex))
        self.assertEqual(self.c.explain.explain("s1", caller_sessions=frozenset({"other"})), [])

    def test_emergency_controls(self):
        br = token(self.ta, role="break-glass", tenant="", sub="op1")
        self.c.emergency_disable(br, scope="global", reason="suspected escape", incident="INC-1")
        self.assertEqual(code(self, self.create), "POLICY.EMERGENCY_DISABLED")
        self.assertFalse(self.c.status(privileged=False)["ready_for_new_sessions"])
        with self.assertRaises(ControlError):  # re-enable needs a second person
            self.c.emergency_enable(token(self.ta, role="break-glass", tenant="", sub="op1"),
                                    token(self.ta, role="break-glass", tenant="", sub="op1"), scope="global", incident="INC-1")
        self.c.emergency_enable(token(self.ta, role="break-glass", tenant="", sub="op1"),
                                token(self.ta, role="break-glass", tenant="", sub="op2"), scope="global", incident="INC-1")
        self.create()

    def test_freeze_then_terminate(self):
        r = self.create()
        self.c.freeze(token(self.ta, role="operator-contain", tenant="", sub="op"), sid="s1", reason="forensics", incident="INC-2")
        self.assertEqual(self.c.sessions["s1"].lifecycle.state, State.FROZEN)
        self.assertTrue(self.c.teardown(token(self.ta), sid="s1", epoch=r["epoch"])["verified"])

    def test_trust_dependency_outage_fails_closed(self):
        self.c.deps.mark("attestation", False)
        self.assertEqual(code(self, self.create), "DEPENDENCY.TRUST_UNAVAILABLE")
        self.c.deps.mark("attestation", True)
        self.c.deps.mark("identity", False)
        self.create()  # within 300 s grace
        self.clock.advance(301)
        self.assertEqual(code(self, lambda: self.create(sid="s2", key="k2")), "DEPENDENCY.TRUST_UNAVAILABLE")

    def test_noncritical_outage_is_degraded_not_bypass(self):
        self.c.deps.mark("telemetry", False)
        st = self.c.status(privileged=True)
        self.assertEqual(st["state"], "DEGRADED")
        self.assertTrue(st["ready_for_new_sessions"])
        self.create()
        self.assertNotIn("sessions_by_state", self.c.status(privileged=False))

    def test_audit_outage_fails_create_without_committing(self):
        self.c.audit.max_bytes = 1
        self.assertEqual(code(self, self.create), "AUDIT.SINK_UNAVAILABLE")
        self.assertNotIn("s1", self.c.sessions)                 # nothing acknowledged or retained
        self.assertEqual(self.c.admission.usage("t1"), (0, 0, 0))  # reservation released

    def test_shape_above_ceiling(self):
        self.assertEqual(code(self, lambda: self.create(shape=Shape(64, 512))), "CAPACITY.SESSION_LIMIT")

    def test_watchdog_stall(self):
        lc = lifecycle.Lifecycle("x", self.clock)
        lc.transition(State.VALIDATING, initiator="controller")
        self.clock.advance(3)
        self.assertTrue(lc.overdue())
        lc.transition(State.FAILED, initiator="watchdog")
        lc.transition(State.REAPING, initiator="watchdog")
        self.clock.advance(31)
        self.assertTrue(lc.overdue())
        lc.transition(State.QUARANTINED, initiator="watchdog")
        self.assertEqual(code(self, lambda: lc.transition(State.CLOSED, initiator="node", proof={"verified": True})),
                         "LIFECYCLE.ILLEGAL_TRANSITION")


class LifecyclePropertyTest(unittest.TestCase):
    """[C015-IMP-05][C086] random walks: no path reaches CLOSED without proof; illegal edges rejected."""

    def test_random_walks(self):
        from inv71_heavy_agent_sandbox.control.lifecycle import TeardownProof
        rng = random.Random(71)
        states, inits = list(State), ("controller", "node", "operator", "watchdog")
        good = TeardownProof("p", True, (), ())
        proofs = [None, {"verified": True}, TeardownProof("p", False, (), ()), TeardownProof("p", True, (("tap", "x"),), ()),
                  TeardownProof("other", True, (), ()), good]
        closed = 0
        for _ in range(3000):
            lc = lifecycle.Lifecycle("p", Clock())
            for _ in range(40):
                if rng.random() < 0.7:  # bias toward legal edges so deep states (and CLOSED) are reached
                    t = rng.choice([t for t in lifecycle.TRANSITIONS if t.src is lc.state] or list(lifecycle.TRANSITIONS))
                    dst, ini = t.dst, t.initiator
                else:
                    dst, ini = rng.choice(states), rng.choice(inits)
                proof = rng.choice(proofs)
                legal = lifecycle.legal(lc.state, dst, ini)
                try:
                    lc.transition(dst, initiator=ini, proof=proof)
                    self.assertIsNotNone(legal)
                    if dst is State.CLOSED:
                        self.assertIs(proof, good)  # only a verified, leak-free proof for this sid
                        closed += 1
                except ControlError:
                    self.assertTrue(legal is None or dst is State.CLOSED)
                if lc.state is State.CLOSED:
                    self.assertTrue(all(lifecycle.legal(State.CLOSED, s, i) is None for s in states for i in inits))
                    break
        self.assertGreater(closed, 0)  # the walk does reach CLOSED legitimately

    def test_every_transition_declares_event_and_recovery(self):
        for t in lifecycle.TRANSITIONS:
            self.assertTrue(t.event and t.crash_recovery and t.guard)
        self.assertEqual({t.dst for t in lifecycle.TRANSITIONS if t.dst is State.CLOSED and t.src is not State.VERIFYING_TEARDOWN}, set())


class ConcurrencyTest(unittest.TestCase):
    """[C086][C058] concurrent duplicate creates/teardowns keep invariants."""

    def test_parallel_duplicate_create_and_teardown(self):
        c, ta, clock, *_ = build()
        toks = [token(ta) for _ in range(64)]
        results, errors = [], []

        def run(t):
            try:
                results.append(c.create(t, sid="dup", tenant="t1", shape=Shape(1, 512), idempotency_key="same"))
            except ControlError as e:
                errors.append(e.code.code)
        ths = [threading.Thread(target=run, args=(t,)) for t in toks]
        [t.start() for t in ths]; [t.join() for t in ths]
        self.assertEqual(len(results), 64)
        self.assertEqual(len({r["epoch"] for r in results}), 1)
        self.assertEqual(c.admission.usage("t1")[0], 1)
        ep = results[0]["epoch"]
        outs = []
        ths = [threading.Thread(target=lambda t=token(ta): outs.append(c.teardown(t, sid="dup", epoch=ep))) for _ in range(16)]
        [t.start() for t in ths]; [t.join() for t in ths]
        self.assertEqual(len(outs), 16)
        self.assertTrue(all(o["verified"] for o in outs))
        self.assertEqual(c.admission.usage("t1"), (0, 0, 0))
        self.assertEqual(c.metrics.value("heavybox_teardowns_verified_total"), 1)

    def test_admission_accounting_never_negative(self):
        adm = resilience.AdmissionController(resilience.NodeCapacity(64, 1 << 20, 1000),
                                             {"t": resilience.TenantQuota(1000, 64, 1 << 20)})
        def worker():
            for _ in range(200):
                try:
                    adm.admit("t", Shape(1, 1))
                    adm.release("t", Shape(1, 1))
                except ControlError:
                    pass
        ths = [threading.Thread(target=worker) for _ in range(8)]
        [t.start() for t in ths]; [t.join() for t in ths]
        self.assertEqual(adm.usage("t"), (0, 0, 0))
        with self.assertRaises(ValueError):
            adm.release("t", Shape(1, 1))


class ResilienceTest(unittest.TestCase):
    """[C025][C053][C054][C056][C017][C028][C067]"""

    def test_retry_only_retryable_with_bounded_jitter(self):
        clock, sleeps = Clock(), []
        calls = itertools.count()

        def flaky():
            if next(calls) < 3:
                raise ControlError("DEPENDENCY.UNAVAILABLE")
            return "ok"
        out = resilience.call_with_retry(flaky, policy=resilience.RetryPolicy(), clock=clock,
                                         sleep=lambda s: (sleeps.append(s), clock.advance(s)), rnd=lambda: 1.0)
        self.assertEqual(out, "ok")
        self.assertEqual(sleeps, [0.1, 0.2, 0.4])
        for c in ("AUTHZ.DENIED", "ARTIFACT.DIGEST_MISMATCH", "DEPENDENCY.DEADLINE_EXCEEDED"):
            n = itertools.count()
            def denied(c=c):
                next(n); raise ControlError(c)
            with self.assertRaises(ControlError):
                resilience.call_with_retry(denied, policy=resilience.RetryPolicy(), clock=clock, sleep=lambda s: None)
            self.assertEqual(next(n), 1, c)

    def test_retry_caps_attempts_and_deadline(self):
        clock, n = Clock(), itertools.count()
        def down():
            next(n); raise ControlError("DEPENDENCY.UNAVAILABLE")
        with self.assertRaises(ControlError):
            resilience.call_with_retry(down, policy=resilience.RetryPolicy(max_attempts=4), clock=clock,
                                       sleep=clock.advance, rnd=lambda: 0.5)
        self.assertEqual(next(n), 4)
        dl = resilience.Deadline.after(0.01, clock)
        with self.assertRaises(ControlError) as cm:
            resilience.call_with_retry(down, policy=resilience.RetryPolicy(), clock=clock, sleep=clock.advance,
                                       rnd=lambda: 1.0, deadline=dl)
        self.assertEqual(cm.exception.code.code, "DEPENDENCY.DEADLINE_EXCEEDED")

    def test_circuit_breaker(self):
        clock = Clock()
        br = resilience.CircuitBreaker("policy", clock=clock, failure_threshold=2, reset_after_s=5)
        def bad():
            raise ControlError("DEPENDENCY.UNAVAILABLE")
        for _ in range(2):
            with self.assertRaises(ControlError):
                br.call(bad)
        self.assertEqual(code(self, lambda: br.call(lambda: 1)), "DEPENDENCY.CIRCUIT_OPEN")
        clock.advance(5)
        with self.assertRaises(ControlError):
            br.call(bad)  # half-open probe fails -> open again
        self.assertEqual(br.state, resilience.BreakerState.OPEN)
        clock.advance(5)
        self.assertEqual(br.call(lambda: 7), 7)
        self.assertEqual(br.state, resilience.BreakerState.CLOSED)

    def test_admission_reserve_quota_fairness(self):
        adm = resilience.AdmissionController(resilience.NodeCapacity(vcpu=10, mem_mib=10_000, max_sessions=100),
                                             {"a": resilience.TenantQuota(100, 10, 10_000, 1),
                                              "b": resilience.TenantQuota(100, 10, 10_000, 1),
                                              "q": resilience.TenantQuota(1, 10, 10_000, 1)})
        adm.admit("q", Shape(1, 10))
        self.assertEqual(code(self, lambda: adm.admit("q", Shape(1, 10))), "CAPACITY.TENANT_QUOTA")
        for _ in range(5):
            adm.admit("a", Shape(1, 10))
        adm.admit("b", Shape(1, 10))                    # total 7 of 10 vCPU
        # contention (>75%): a is above its weighted share (9 * 1/3 = 3) and is shed first
        self.assertEqual(code(self, lambda: adm.admit("a", Shape(1, 10))), "CAPACITY.ADMISSION_REJECTED")
        self.assertEqual(adm.rejections.get("fair_share"), 1)
        adm.admit("b", Shape(1, 10)); adm.admit("b", Shape(1, 10))   # b still under its share; total 9
        self.assertEqual(code(self, lambda: adm.admit("b", Shape(1, 10))), "CAPACITY.ADMISSION_REJECTED")
        self.assertEqual(adm.rejections.get("node_saturated"), 1)   # 10% reserve held back
        adm.admit("b", Shape(1, 10), priority="management")  # reserve slice usable for containment
        self.assertEqual(code(self, lambda: adm.admit("zz", Shape(1, 1))), "AUTHZ.DENIED")

    def test_idempotency_window(self):
        clock = Clock()
        st = resilience.IdempotencyStore(clock=clock, window_s=10, capacity=2)
        st.put("k", "d", {"x": 1})
        self.assertEqual(st.get("k", "d"), {"x": 1})
        self.assertEqual(code(self, lambda: st.get("k", "other")), "VALIDATION.MALFORMED_REQUEST")
        clock.advance(11)
        self.assertIsNone(st.get("k", "d"))
        for i in range(5):
            st.put(f"k{i}", "d", {})
        self.assertLessEqual(len(st._d), 2)

    def test_operation_table_complete(self):
        for op, (dl, rc, _) in resilience.OPERATIONS.items():
            self.assertGreater(dl, 0)
            self.assertIsInstance(rc, RetryClass)


class ErrorContractTest(unittest.TestCase):
    """[C026][C014][C082] every code well-formed; exceptions map; records safe."""

    def test_registry(self):
        for k, e in REGISTRY.items():
            self.assertEqual(k, e.code)
            self.assertRegex(k, r"^[A-Z]+\.[A-Z_]+$")
            self.assertIsInstance(e.outcome, Outcome)
            if e.outcome is Outcome.SECURITY_REJECTED:
                self.assertIn(e.retry, (RetryClass.NEVER, RetryClass.IDEMPOTENT))
            self.assertTrue(e.user_message and e.operator_action)
        with self.assertRaises(KeyError):
            ControlError("NOT.REGISTERED")

    def test_mapping_and_no_leak(self):
        self.assertEqual(map_exception(EgressDenied("x")).code.code, "POLICY.EGRESS_DENIED")
        self.assertEqual(map_exception(LimitExceeded("x")).code.code, "CAPACITY.SESSION_LIMIT")
        self.assertEqual(map_exception(SessionClosed("x")).code.code, "LIFECYCLE.SESSION_CLOSED")
        e = map_exception(RuntimeError("secret path /etc/shadow"))
        rec = e.to_record(correlation_id="c")
        self.assertEqual(rec["code"], "INTERNAL.UNCLASSIFIED")
        self.assertNotIn("shadow", str(rec))
        self.assertEqual(e.fields["privileged_type"], "RuntimeError")


class TelemetryTest(unittest.TestCase):
    """[C072][C074][C075][C076][C080]"""

    def test_bounded_labels(self):
        m = telemetry.Metrics()
        m.inc("heavybox_requests_total", operation="session.create", outcome="SUCCESS")
        for bad in ({"operation": "session-123", "outcome": "SUCCESS"}, {"operation": "session.create"}):
            with self.assertRaises(telemetry.CardinalityError):
                m.inc("heavybox_requests_total", **bad)
        m.observe("heavybox_operation_seconds", 0.03, operation="session.create")
        text = m.exposition()
        self.assertIn('heavybox_operation_seconds_bucket{operation="session.create",le="0.05"} 1', text)
        self.assertIn("# TYPE heavybox_requests_total counter", text)

    def test_traceparent(self):
        good = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        tc = telemetry.parse_traceparent(good, trusted=True)
        self.assertEqual(tc.trace_id, "4bf92f3577b34da6a3ce929d0e0e4736")
        self.assertNotEqual(telemetry.parse_traceparent(good, trusted=False).trace_id, tc.trace_id)
        for bad in ("00-" + "0" * 32 + "-00f067aa0ba902b7-01", "garbage", None, good.upper()):
            self.assertNotEqual(telemetry.parse_traceparent(bad, trusted=True).trace_id, tc.trace_id)
        self.assertEqual(tc.child().trace_id, tc.trace_id)
        self.assertTrue(telemetry.parse_traceparent(None, trusted=True, force_sample=True).sampled)

    def test_explain_reason_codes_not_free_text(self):
        ex = telemetry.ExplainLog()
        with self.assertRaises(ValueError):
            ex.record(decision="deny", reason_code="guest said so", operation="x", session="s", tenant_tier="gold", inputs={})

    def test_every_code_classified(self):
        for k in REGISTRY:
            self.assertIn(telemetry.classify(k), telemetry.EVENT_CLASSES)


class RuntimePlanTest(unittest.TestCase):
    """[INV71-X003][C017-IMP-04][C021][C032][C042][C043][C046] rendered plan (not executed)."""

    def test_plan_contents(self):
        p = plan_session("s1", merge({}), FAKE_ARTIFACTS, allowed=[("151.101.0.223", 443, "tcp")])
        self.assertTrue(p.vm_config["drives"][0]["is_read_only"])
        self.assertFalse(p.vm_config["machine-config"]["smt"])
        self.assertIn("--new-pid-ns", p.jailer_argv)
        self.assertNotIn("--no-seccomp", p.jailer_argv)
        self.assertEqual(p.cgroup["memory.swap.max"], "0")
        self.assertIn("policy drop", p.nft)
        self.assertIn("ip daddr 151.101.0.223 tcp dport 443", p.nft)
        self.assertLessEqual(len(next(x for x in p.owned if x[0] == "tap")[1]), 15)
        self.assertGreaterEqual(p.uid, 200_000)

    def test_distinct_sessions_share_nothing(self):
        a = plan_session("a", merge({}), FAKE_ARTIFACTS)
        b = plan_session("b", merge({}), FAKE_ARTIFACTS)
        self.assertFalse(a.owned & b.owned)
        self.assertNotEqual(a.uid, b.uid)

    def test_refusals(self):
        self.assertEqual(code(self, lambda: plan_session("s", merge({}), {})), "ARTIFACT.UNAPPROVED_VERSION")
        cfg = dict(merge({}), **{"host.devices": ["/dev/sda"]})
        self.assertEqual(code(self, lambda: plan_session("s", cfg, FAKE_ARTIFACTS)), "CONFIG.FORBIDDEN_OVERRIDE")
        self.assertEqual(code(self, lambda: plan_session("../x", merge({}), FAKE_ARTIFACTS)), "VALIDATION.MALFORMED_REQUEST")

    def test_reconcile_leaks_and_orphans(self):
        a = plan_session("a", merge({}), FAKE_ARTIFACTS)
        tap = next(x for x in a.owned if x[0] == "tap")
        r = reconcile([a], {tap, ("cgroup", "/sys/fs/cgroup/firecracker/hb-deadbeef0000")}, closing=["a"])
        self.assertFalse(r.verified)
        self.assertEqual(r.leaked, (tap,))
        self.assertEqual(len(r.orphans), 1)
        self.assertTrue(reconcile([a], set(), closing=["a"]).verified)


class CompatQualifyTest(unittest.TestCase):
    """[C016][C027][C084][C093][C012][C040]"""

    def test_negotiation(self):
        n = compat.negotiate({"control_api": "1.0", "event_schema": "1.3"}, ["dns_bound_egress", "resumable_sessions"])
        self.assertEqual(n.features, frozenset({"dns_bound_egress"}))
        self.assertEqual(code(self, lambda: compat.negotiate({"control_api": "3.0"}, [])), "COMPAT.UNSUPPORTED_VERSION")
        self.assertEqual(code(self, lambda: compat.negotiate({"control_api": "1.0"}, [], ["resumable_sessions"])),
                         "COMPAT.UNSUPPORTED_VERSION")
        compat.negotiate({"control_api": "1.0", "future_surface": "7.0"}, [])  # unknown optional surface ignored

    def test_skew_and_matrix(self):
        compat.check_skew("1.0", "1.4", "1.0", "1.2")
        self.assertEqual(code(self, lambda: compat.check_skew("3.0", "1.0", "1.0", "1.0")), "COMPAT.UNSUPPORTED_VERSION")
        self.assertEqual(code(self, lambda: compat.check_skew("1.0", "1.0", "2.0", "1.0")), "COMPAT.UNSUPPORTED_VERSION")
        self.assertFalse(compat.deployable({"arch": "x86_64", "cpu": "intel"}))  # untested -> not deployable
        self.assertFalse(compat.deployable({"arch": "riscv64"}))

    def test_qualification(self):
        good = {"arch": "x86_64", "kernel": "6.1.90", "kvm": True, "cgroup2": True, "mem_mib": 262144,
                "cpu_flags": ["vmx"], "nested": False, "time_sync": True}
        self.assertEqual(qualify.qualify(good, "datacenter")["verdict"], "ADMIT")
        for bad in ({"kvm": False}, {"kernel": "4.19.0"}, {"nested": True}, {"cpu_flags": []}, {"mem_mib": 1024}):
            self.assertEqual(qualify.qualify({**good, **bad}, "datacenter")["verdict"], "REJECT", bad)
        self.assertEqual(qualify.qualify(qualify.probe_local(), "cloud")["schema"], "PK_HEAVYBOX_NODE_QUALIFICATION/1")


if __name__ == "__main__":
    unittest.main()
