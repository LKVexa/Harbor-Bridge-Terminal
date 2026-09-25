"""Config (40-42), observability (44-49), hand-off (36-39), resilience
(33-35, 51-53)."""
from __future__ import annotations

import io
import json
import logging
import os
import tempfile
import unittest

import _support  # noqa: F401
from _support import FakeClock
from inv04_current_orchestration.runtime import objects as o
from inv04_current_orchestration.runtime.config import ConfigManager, config_dict, load_config
from inv04_current_orchestration.runtime.errors import (Cancelled, CircuitOpen, ConfigRejected, DeadlineExceeded,
                                                        DependencyUnavailable, Forbidden, HandoffGap,
                                                        OwnershipConflict, StaleCache, Throttled)
from inv04_current_orchestration.runtime.handoff import (ChangeStream, HandoffSession, OwnershipRegistry, Receiver,
                                                         take_snapshot)
from inv04_current_orchestration.runtime.journal import Journal
from inv04_current_orchestration.runtime.observability import (ConvergenceSLO, Health, JsonFormatter, Registry, Tracer,
                                                               evaluate_alerts, log_event, standard_metrics)
from inv04_current_orchestration.runtime.resilience import (Backoff, CircuitBreaker, Context, RetryBudget,
                                                            StallDetector, TokenBucket, retry_call)
from inv04_current_orchestration.runtime.store import Informer, VersionedStore


class ConfigTest(unittest.TestCase):
    def test_overlays_bounds_unknown_keys(self):
        cfg = load_config({"workers": 4}, {"environment": "prod"}, {"site": "sfo1", "feature_gates": {"drain": False}})
        self.assertEqual((cfg.workers, cfg.environment, cfg.site, cfg.gate("drain"), cfg.gate("reconcile")),
                         (4, "prod", "sfo1", False, True))
        for bad in ({"workerz": 1}, {"workers": 0}, {"workers": True}, {"api_qps": "fast"},
                    {"lease_seconds": 5, "renew_deadline_s": 6}, {"feature_gates": {"drain": "yes"}}):
            with self.assertRaises(ConfigRejected, msg=str(bad)):
                load_config(bad)

    def test_activation_provenance_health_revert_and_restart(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "j.jsonl")
            m = ConfigManager(Journal(path))
            act = m.apply({"workers": 3}, issuer="alice")
            self.assertEqual((act.revision, m.active.workers, len(act.digest)), (1, 3, 64))
            with self.assertRaises(ConfigRejected):
                m.apply({"workers": 8}, issuer="bob", health=lambda c: False)
            self.assertEqual(m.active.workers, 3)  # auto-reverted
            with self.assertRaises(ConfigRejected):
                m.apply({"workers": 5}, issuer="")
            m.apply({"workers": 6}, issuer="carol")
            m.rollback(issuer="carol")
            self.assertEqual(m.active.workers, 3)
            restarted = ConfigManager(Journal(path))
            self.assertEqual(restarted.active.workers, 3)
            phases = [e.phase for e in Journal(path) if e.kind == "config"]
            self.assertIn("reverted", phases)
            self.assertEqual(config_dict(restarted.active)["workers"], 3)


class ObservabilityTest(unittest.TestCase):
    def test_metrics_exposition_and_cardinality_cap(self):
        reg = Registry()
        m = standard_metrics(reg)
        m["drains_total"].inc(outcome="completed", reason="drained")
        m["reconcile_seconds"].observe(0.2)
        text = reg.render()
        self.assertIn('inv04_drains_total{outcome="completed",reason="drained"} 1', text)
        self.assertIn('inv04_reconcile_duration_seconds_bucket{le="+Inf"} 1', text)
        with self.assertRaises(ValueError):
            m["drains_total"].inc(outcome="x")
        g = reg.gauge("t", "t", ("k",))
        for i in range(600):
            g.set(1, k=str(i))
        self.assertEqual(len(g.values), 500)
        self.assertEqual(g.overflow, 100)

    def test_structured_logs_redact_secrets(self):
        buf = io.StringIO()
        log = logging.getLogger("inv04.test.redact")
        h = logging.StreamHandler(buf)
        h.setFormatter(JsonFormatter())
        log.addHandler(h)
        log.propagate = False
        log.setLevel(logging.INFO)
        log_event(log, "drain", op_id="op1", node="n1", authorization="Bearer abc", nested={"password": "p"})
        rec = json.loads(buf.getvalue())
        self.assertEqual((rec["op_id"], rec["authorization"], rec["nested"]["password"]), ("op1", "[REDACTED]", "[REDACTED]"))

    def test_trace_propagation_and_error_status(self):
        t = Tracer()
        with t.span("drain", op_id="x") as root:
            with t.span("evict") as child:
                tp = t.traceparent()
        self.assertEqual(child.parent_id, root.span_id)
        self.assertTrue(tp.startswith(f"00-{root.trace_id}-"))
        with self.assertRaises(Forbidden):
            with t.span("api", traceparent=tp):
                raise Forbidden("x")
        self.assertEqual(t.finished[-1].trace_id, root.trace_id)
        self.assertEqual(t.finished[-1].status, "error:ORCH_FORBIDDEN")

    def test_health_probes_report_degraded(self):
        h = Health()
        h.add("informer", lambda: (False, "not synced"))
        self.assertEqual(h.readiness()[0], 503)
        h.started = True
        code, body = h.readiness()
        self.assertEqual((code, body["degraded"]), (503, ["informer"]))
        self.assertEqual(h.liveness()[0], 200)

    def test_slo_measurement_and_burn_rate_alerts(self):
        clock = FakeClock(0)
        slo = ConvergenceSLO(30, 0.99, clock=clock)
        slo.observe("web", 3, 2)
        clock.advance(10)
        slo.observe("web", 3, 3)
        self.assertEqual(slo.report()["convergence_ratio"], 1.0)
        for _ in range(5):
            slo.observe("api", 3, 1)
            clock.advance(45)
            slo.observe("api", 3, 3)
        r = slo.report()
        self.assertLess(r["convergence_ratio"], 0.99)
        self.assertFalse(r["convergence_slo_met"])
        alerts = evaluate_alerts(slo)
        self.assertTrue(any(a["severity"] == "page" for a in alerts))
        self.assertTrue(all(a["severity"] != "page" for a in evaluate_alerts(slo, maintenance=True)))
        slo.observe("stuck", 3, 0)
        clock.advance(31)
        self.assertEqual(slo.report()["overdue_open"], 1)
        slo.record_drain(breached_budget=True)
        self.assertEqual(evaluate_alerts(slo, maintenance=True)[0]["alert"], "drain_budget_breach")


class HandoffTest(unittest.TestCase):
    def pods(self, n):
        return [o.make_pod(f"web-{i}", "web", f"n{i % 2}") for i in range(n)]

    def test_snapshot_identity_ack_diff_resume(self):
        base = take_snapshot(self.pods(3), 10, clock=lambda: 1.0)
        self.assertEqual(base.inventory(), {"web": ["n0", "n0", "n1"]})
        self.assertEqual(take_snapshot(self.pods(3), 10, clock=lambda: 2.0).digest, base.digest)
        stream = ChangeStream(base)
        sess = HandoffSession(stream)
        with self.assertRaises(HandoffGap):
            sess.pending()
        sess.ack_snapshot(base.digest)
        rx = Receiver(base)
        stream.publish(take_snapshot(self.pods(4), 11))
        stream.publish(take_snapshot(self.pods(2), 12))
        msgs = sess.pending()
        self.assertEqual([m["seq"] for m in msgs], [1, 2])
        self.assertTrue(rx.apply(msgs[0]))
        self.assertFalse(rx.apply(msgs[0]))  # duplicate is ignored
        sess.ack(1, msgs[0]["to_digest"])
        self.assertEqual([m["seq"] for m in sess.pending()], [2])  # resume after ack
        rx.apply(msgs[1])
        self.assertEqual(rx.state_digest(12), stream.current.digest)

    def test_gap_detection(self):
        base = take_snapshot(self.pods(2), 1)
        stream = ChangeStream(base)
        stream.publish(take_snapshot(self.pods(3), 2))
        m2 = stream.publish(take_snapshot(self.pods(4), 3))
        with self.assertRaises(HandoffGap):
            Receiver(base).apply(m2)

    def test_ownership_single_authority(self):
        reg = OwnershipRegistry()
        reg.claim("web", "inv04")
        with self.assertRaises(OwnershipConflict):
            reg.claim("web", "sch01")
        self.assertFalse(reg.may_reconcile("web", "sch01"))
        reg.transfer("web", "inv04", "sch01")
        self.assertTrue(reg.may_reconcile("web", "sch01"))
        self.assertFalse(reg.may_reconcile("web", "inv04"))


class ResilienceTest(unittest.TestCase):
    def test_deadline_and_cancellation_propagate(self):
        clock = FakeClock(0)
        parent = Context(timeout=10, clock=clock)
        child = parent.child(timeout=100)
        self.assertEqual(child.deadline, 10)
        clock.advance(11)
        with self.assertRaises(DeadlineExceeded):
            child.check()
        p2 = Context()
        c2 = p2.child()
        p2.cancel("shutdown")
        with self.assertRaises(Cancelled):
            c2.check()

    def test_retry_classification_budget_and_deadline(self):
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise DependencyUnavailable("x")
            return "ok"
        self.assertEqual(retry_call(flaky, sleep=lambda s: None, backoff=Backoff(base=0.001)), "ok")
        calls.clear()
        with self.assertRaises(Forbidden):
            retry_call(lambda: calls.append(1) or (_ for _ in ()).throw(Forbidden("no")), sleep=lambda s: None)
        self.assertEqual(len(calls), 1)  # terminal errors are never retried
        budget = RetryBudget(ratio=0.0, min_per_window=0)
        with self.assertRaises(DependencyUnavailable):
            retry_call(lambda: (_ for _ in ()).throw(DependencyUnavailable("x")), budget=budget, sleep=lambda s: None)
        clock = FakeClock(0)
        with self.assertRaises(DeadlineExceeded):
            retry_call(lambda: (_ for _ in ()).throw(DependencyUnavailable("x")), ctx=Context(timeout=0.5, clock=clock),
                       backoff=Backoff(base=1, jitter=0), sleep=clock.advance)

    def test_backoff_jitter_bounds(self):
        b = Backoff(base=1, cap=8, jitter=1.0)
        for attempt in range(10):
            d = b.delay(attempt)
            self.assertTrue(0 <= d <= min(8, 2 ** attempt))

    def test_token_bucket(self):
        clock = FakeClock(0)
        tb = TokenBucket(2, 2, clock=clock)
        tb.acquire(); tb.acquire()
        with self.assertRaises(Throttled):
            tb.acquire()
        clock.advance(0.5)
        tb.acquire()

    def test_circuit_breaker_open_half_open_close(self):
        clock = FakeClock(0)
        cb = CircuitBreaker("api", threshold=2, reset=10, clock=clock)
        boom = lambda: (_ for _ in ()).throw(DependencyUnavailable("x"))  # noqa: E731
        for _ in range(2):
            with self.assertRaises(DependencyUnavailable):
                cb.call(boom)
        with self.assertRaises(CircuitOpen):
            cb.call(lambda: 1)
        clock.advance(11)
        self.assertEqual(cb.call(lambda: 1), 1)
        self.assertEqual(cb.state, "closed")

    def test_stall_detector(self):
        clock = FakeClock(0)
        sd = StallDetector(max_age=30, max_conflicts=3, clock=clock)
        sd.begin("web"); sd.begin("api")
        for _ in range(3):
            sd.conflict("api")
        clock.advance(31)
        sd.mark_progress("api")
        sd.conflict("api"); sd.conflict("api"); sd.conflict("api")
        got = {s["key"]: s["reasons"] for s in sd.stalled()}
        self.assertEqual(got, {"web": ["no_progress"], "api": ["repeated_conflicts"]})

    def test_partition_staleness_blocks_decisions(self):
        s = VersionedStore()
        inf = Informer(s, "Pod")
        with self.assertRaises(StaleCache):
            inf.require_fresh(10)  # never synced -> no writes on a blind cache
        inf.poll()
        for i in range(20):
            s.create("Pod", str(i), {})
        with self.assertRaises(StaleCache):
            inf.require_fresh(10)


if __name__ == "__main__":
    unittest.main()
