"""Config, resilience primitives, observability, concurrency and performance."""
import json
import os
import threading
import time
import tracemalloc
import unittest

from _support import PKG_DIR, HOSTS, covers, desired, make_env, mod, req

config = mod("config")
errors = mod("errors")
resilience = mod("resilience")
obs = mod("observability")
E = errors.ErrorCode


class ConfigTest(unittest.TestCase):
    @covers(33, 34)
    def test_secure_defaults_and_fail_closed_validation(self):
        cfg = config.compose({})
        self.assertEqual(cfg["environment"], "prod")
        self.assertTrue(cfg["require_signed_artifacts"])
        self.assertFalse(cfg["allow_unauthenticated"])
        for bad in ({"allow_unauthenticated": True}, {"require_signed_artifacts": False},
                    {"require_encryption_at_rest": False}, {"max_inflight": 0}, {"environment": "yolo"},
                    {"unknown": 1}, {"tier": "far-edge", "offline_autonomy_s": 10},
                    {"tenant_quotas": {"a": {"max_instances": -1}}}):
            with self.assertRaises(errors.DeploymentError, msg=bad) as cm:
                config.compose(bad)
            self.assertEqual(cm.exception.code, E.CONFIG_INVALID, bad)
        self.assertFalse(config.compose({"environment": "dev", "allow_unauthenticated": True})["require_signed_artifacts"] is False)

    @covers(39, 34)
    def test_secrets_rejected_in_config(self):
        for bad in ({"secret_refs": {"nats": "SUAJ..."}}, {"site": "-----BEGIN EC PRIVATE KEY-----"},
                    {"residency_labels": {"password": "hunter2"}}):
            with self.assertRaises(errors.DeploymentError, msg=bad) as cm:
                config.compose(bad)
            self.assertEqual(cm.exception.code, E.SECRET_IN_CONFIG)
        config.compose({"secret_refs": {"nats": "env:NATS_CREDS", "tokens": "file:/run/secrets/k"}})

    @covers(35, 32)
    def test_environment_and_site_overlays_without_rebuild(self):
        layers = config.load_layers(PKG_DIR / "deploy/config", "prod", "edge-site-a")
        cfg = config.compose(*layers)
        self.assertEqual((cfg["site"], cfg["tier"]), ("edge-site-a", "far-edge"))
        self.assertGreaterEqual(cfg["offline_autonomy_s"], 300)
        cfg2 = config.compose(*config.load_layers(PKG_DIR / "deploy/config", "staging", "dc-1"))
        self.assertEqual(cfg2["environment"], "staging")

    @covers(36, 37, 38)
    def test_provenance_atomic_activation_and_rollback(self):
        clock = [100.0]
        cs = config.ConfigStore(clock=lambda: clock[0])
        a1 = cs.activate([{"site": "s1"}], "alice", "initial")
        self.assertEqual((a1.version, a1.author, a1.activated_at, a1.previous_digest), (1, "alice", 100.0, None))
        before = cs.active
        with self.assertRaises(errors.DeploymentError):
            cs.activate([{"site": "s2", "max_inflight": -5}], "bob", "bad")
        self.assertIs(cs.active, before)                       # no partial application
        clock[0] = 200.0
        a2 = cs.activate([{"site": "s2"}], "bob", "move")
        self.assertEqual(a2.previous_digest, a1.digest)
        a3 = cs.rollback("carol")
        self.assertEqual(a3.digest, a1.digest)
        self.assertEqual(cs.active["site"], "s1")
        with self.assertRaises(errors.DeploymentError):
            cs.activate([{}], "", "no author")


class ResilienceTest(unittest.TestCase):
    @covers(53, 25)
    def test_bounded_retry_with_jitter_only_for_retryable_idempotent(self):
        calls = []
        slept = []
        rp = resilience.RetryPolicy(max_attempts=4, sleep=slept.append)

        def flaky():
            calls.append(1)
            raise errors.DeploymentError(E.DEPENDENCY_UNAVAILABLE, "x")
        with self.assertRaises(errors.DeploymentError):
            rp.run(flaky, idempotent=True)
        self.assertEqual(len(calls), 4)
        self.assertEqual(len(slept), 3)
        self.assertTrue(all(0 <= s <= rp.cap_s for s in slept))
        self.assertGreater(len(set(slept)), 1)                   # jittered
        calls.clear()
        with self.assertRaises(errors.DeploymentError):
            rp.run(flaky, idempotent=False)
        self.assertEqual(len(calls), 1)                          # never retried
        calls.clear()

        def terminal():
            calls.append(1)
            raise errors.DeploymentError(E.FORBIDDEN, "x")
        with self.assertRaises(errors.DeploymentError):
            rp.run(terminal, idempotent=True)
        self.assertEqual(len(calls), 1)

    @covers(54, 60)
    def test_circuit_breaker(self):
        t = [0.0]
        cb = resilience.CircuitBreaker(2, 5.0, clock=lambda: t[0])

        def bad():
            raise errors.DeploymentError(E.DEPENDENCY_UNAVAILABLE, "down")
        for _ in range(2):
            with self.assertRaises(errors.DeploymentError):
                cb.call(bad)
        with self.assertRaises(errors.DeploymentError) as cm:
            cb.call(lambda: 1)
        self.assertEqual(cm.exception.code, E.CIRCUIT_OPEN)
        t[0] = 6.0
        self.assertEqual(cb.call(lambda: 7), 7)
        self.assertEqual(cb.state, cb.CLOSED)

    @covers(54, 67, 63)
    def test_admission_shedding_and_quota(self):
        t = [0.0]
        a = resilience.Admission(max_inflight=5, tenant_rate=1, tenant_burst=3, queue_depth=2, clock=lambda: t[0])
        for _ in range(3):
            a.enter("t1")
        with self.assertRaises(errors.DeploymentError) as cm:
            a.enter("t1")
        self.assertEqual(cm.exception.code, E.QUOTA_EXCEEDED)      # fairness: t1 cannot starve t2
        a.enter("t2")
        with self.assertRaises(errors.DeploymentError) as cm:
            a.enter("t3", "batch")                                  # 4/5 = 80% -> batch shed
        self.assertEqual(cm.exception.code, E.OVERLOADED)
        a.enter("t3")
        with self.assertRaises(errors.DeploymentError):
            a.enter("t4")
        a.enter("t4", "critical")                                   # critical admitted at cap
        a.enqueue(("x", 1)); a.enqueue(("x", 2))
        with self.assertRaises(errors.DeploymentError):
            a.enqueue(("x", 3))
        t[0] = 10.0
        for _ in range(6):
            a.leave()
        a.enter("t1")

    @covers(60, 89, 54)
    def test_fault_injection_breaker_trips_and_recovers(self):
        env = make_env()
        req(env, "set_desired", desired(env))
        env.lattice.partitioned = True
        for _ in range(env.cfg["circuit_failure_threshold"]):
            env.svc.tick()
        self.assertEqual(env.svc.breaker.state, "open")
        env.lattice.partitioned = False
        env.mono.advance(11)
        self.assertEqual(env.svc.resync()["pending"], 0)
        self.assertEqual(env.svc.breaker.state, "closed")
        self.assertEqual(len(env.lattice.running), 3)


class ObservabilityTest(unittest.TestCase):
    def setUp(self):
        self.env = make_env()
        req(self.env, "set_desired", desired(self.env))
        req(self.env, "reconcile", {"tenant": "acme", "component": "api"},
            traceparent="00-" + "a" * 32 + "-" + "b" * 16 + "-01")

    @covers(72, 80)
    def test_red_use_metrics(self):
        m = self.env.svc.metrics
        self.assertEqual(m.get("requests", op="reconcile", outcome="SUCCESS"), 1)
        self.assertEqual(m.get("actions", kind="start"), 3)
        self.assertIsNotNone(m.quantile("request_latency_ms", 0.99, op="reconcile"))
        req(self.env, "reconcile", {"tenant": "acme", "component": "ghost"})
        self.assertEqual(m.get("errors", op="reconcile", code="INV63-E-PRECONDITION"), 1)
        text = m.exposition()
        for name in ("inv63_requests_total", "inv63_errors_total", "inv63_request_latency_ms_bucket",
                     "inv63_control_plane_up"):
            self.assertIn(name, text)

    @covers(73, 75)
    def test_structured_logs_have_stable_ids_and_no_secrets(self):
        tok = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ4In0"
        req(self.env, "reconcile", {"tenant": "acme", "component": "ghost", "password": "hunter2"})
        rec = self.env.svc.log.records[-1]
        for k in obs.REQUIRED_LOG_FIELDS:
            self.assertIn(k, rec)
        blob = json.dumps(self.env.svc.log.records)
        self.assertNotIn("hunter2", blob)
        self.env.svc.log.log("info", "t", leaked=tok)
        self.assertNotIn(tok, json.dumps(self.env.svc.log.records[-1]))
        exported = obs.export_records(self.env.svc.log.records)
        self.assertNotIn('"acme"', json.dumps(exported))

    @covers(74)
    def test_trace_context_propagates(self):
        spans = self.env.svc.tracer.spans
        self.assertTrue(any(s.ctx.trace_id == "a" * 32 and s.parent == "b" * 16 for s in spans))
        self.assertEqual(self.env.svc.decisions.items[-1].trace_id, "a" * 32)
        ctx = obs.SpanContext.parse("00-" + "0" * 32 + "-" + "b" * 16 + "-01")
        self.assertNotEqual(ctx.trace_id, "0" * 32)       # invalid ids restart trace

    @covers(76, 77, 78)
    def test_every_decision_has_reason_and_explain_view(self):
        ex = req(self.env, "explain", {"tenant": "acme", "component": "api"}, roles=("tenant-viewer",))["result"]
        self.assertGreaterEqual(len(ex["decisions"]), 2)
        for d in ex["decisions"]:
            self.assertTrue(d["why"])
            self.assertTrue(d["release"].startswith("inv63-"))
            self.assertTrue(d["topology"].startswith("sha256:"))
        self.assertIn("reconcile", ex["text"])
        with self.assertRaises(ValueError):
            self.env.svc.decisions.record(tenant="t", component="c", action="a", reason="", inputs={}, policies=[],
                                          constraints={}, trace_id="x")

    @covers(75, 79, 67)
    def test_cardinality_guard_and_pseudonymous_ids(self):
        m = obs.Metrics()
        for i in range(obs.MAX_LABEL_SETS + 50):
            m.inc("x", tenant=str(i))
        self.assertEqual(m.dropped_series, 50)
        self.assertNotIn("acme", obs.tenant_hash("acme"))
        self.assertEqual(obs.tenant_hash("acme"), obs.tenant_hash("acme"))

    @covers(80)
    def test_alert_classes_and_dashboard_definitions(self):
        self.assertEqual(obs.classify_alert("INV63-E-QUOTA"), "ordinary_load")
        self.assertEqual(obs.classify_alert("INV63-E-POLICY"), "policy_rejection")
        self.assertEqual(obs.classify_alert("INV63-E-DEPENDENCY-UNAVAILABLE"), "dependency_failure")
        self.assertEqual(obs.classify_alert("INV63-E-FORBIDDEN"), "security_event")
        alerts = json.loads((PKG_DIR / "observability/alerts.json").read_text())
        self.assertEqual({a["class"] for a in alerts["rules"]} | {"stall"}, set(obs.ALERT_CLASSES) | {"stall"})
        req(self.env, "reconcile", {"tenant": "acme", "component": "ghost"})
        self.env.svc.tick()
        text = self.env.svc.metrics.exposition()
        for rule in alerts["rules"]:
            self.assertIn(rule["metric"], text, rule["name"])
        dash = json.loads((PKG_DIR / "observability/dashboard.json").read_text())
        self.assertGreaterEqual(len(dash["panels"]), 6)


class ConcurrencyTest(unittest.TestCase):
    @covers(86, 58)
    def test_concurrent_requests_keep_state_consistent(self):
        env = make_env(config_over={"max_inflight": 1000})
        for i in range(8):
            req(env, "set_desired", desired(env, component=f"c{i}", count=2))
        lock = threading.Lock()            # the service is single-writer; callers serialize via this lock
        errs = []

        def worker(i):
            try:
                for _ in range(5):
                    with lock:
                        r = req(env, "reconcile", {"tenant": "acme", "component": f"c{i}"})
                    if r["outcome"] not in ("SUCCESS",):
                        errs.append(r)
            except Exception as exc:
                errs.append(exc)
        ts = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(errs, [])
        self.assertEqual(len(env.lattice.running), 16)
        self.assertTrue(env.journal.verify())

    @covers(86, 58)
    def test_two_handles_cannot_interleave_journal_writes(self):
        env = make_env()
        store = mod("store")
        other = store.Journal(env.journal.dir, clock=env.clock, sealer=env.sealer)
        other.epoch = env.journal.epoch                  # pretend same epoch (worst case)
        env.journal.append("x", {"a": 1})
        with self.assertRaises(errors.DeploymentError) as cm:
            other.append("y", {"b": 2})
        self.assertEqual(cm.exception.code, E.CONFLICT)
        self.assertTrue(env.journal.verify())

    @covers(86)
    def test_metrics_thread_safety(self):
        m = obs.Metrics()
        ts = [threading.Thread(target=lambda: [m.inc("n") for _ in range(2000)]) for _ in range(8)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(m.get("n"), 16000)


class PerformanceTest(unittest.TestCase):
    """Fast smoke versions of perf/bench.py so the unit suite catches gross regressions."""

    @covers(61, 62, 70, 88)
    def test_diff_p99_under_threshold_1000_instances(self):
        th = json.loads((PKG_DIR / "perf/thresholds.json").read_text())
        Manager = mod("manager").Manager
        hosts = {f"h{i}": f"z{i % 10}" for i in range(200)}
        m = Manager(hosts)
        m.apply(m.diff("api", "v1", 1000))
        samples = []
        for _ in range(60):
            t0 = time.perf_counter()
            m.diff("api", "v1", 1000)
            samples.append((time.perf_counter() - t0) * 1000)
        samples.sort()
        p99 = samples[int(0.99 * len(samples)) - 1]
        self.assertLess(p99, th["diff_1000_noop_ms"]["p99"] * th["ci_slack_factor"])

    @covers(67, 64)
    def test_memory_bounded_under_many_decisions(self):
        dl = obs.DecisionLog(max_records=1000)
        tracemalloc.start()
        for i in range(5000):
            dl.record(tenant="t", component="c", action="a", reason="r", inputs={}, policies=[], constraints={},
                      trace_id="x")
        cur, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self.assertLessEqual(len(dl.items), 1000)
        self.assertLess(peak, 8 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
