"""P1-13..21: deadlines, retry/breaker, freshness, stale policy, health, metrics, logs, explain, admission."""
import io
import json
import pathlib
import random
import sys
import threading
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fixtures.estate import Estate  # noqa: E402

from gap14_data_gravity_manager.errors import G14Error, REGISTRY  # noqa: E402
from gap14_data_gravity_manager.observability import OVERFLOW, Registry, StructuredLogger, TraceContext  # noqa: E402
from gap14_data_gravity_manager.resilience import (AdmissionController, CancellationToken, CircuitBreaker, Deadline,  # noqa: E402
                                                    RetryPolicy, StaleDataPolicy, call_with_resilience)
from gap14_data_gravity_manager.trust import FakeClock  # noqa: E402


class DeadlineCancellationTest(unittest.TestCase):  # P1-13
    def test_slow_dependency_times_out_and_is_not_decided(self):
        e = Estate()
        e.topology.delay = 1.0
        with self.assertRaises(G14Error) as ctx:
            e.decide()
        self.assertIn(ctx.exception.code, ("G14_DEPENDENCY_TIMEOUT", "G14_DEADLINE_EXCEEDED"))

    def test_deadline_exhaustion_mid_pipeline(self):
        e = Estate()
        e.placement.delay = 0.049  # under per-call cap, but repeated slow deps exhaust the 0.5s budget eventually
        e.replication.delay = 0.049
        e.policy.delay = 0.049
        e.topology.delay = 0.049
        d = e.decide()  # 5 calls * 0.049 < 0.5 -> fine
        self.assertIn("recommendation", d)
        e.config.activate(e.signed_config({"schema": "PK_GAP14_CONFIG/1", "revision": 2, "mode": "production",
                                           "knobs": {"decision_deadline_s": 0.1, "dependency_timeout_s": 0.05}}), e.clock.now())
        dl = Deadline(0.1, e.clock)
        e.clock.advance(0.2)
        with self.assertRaises(G14Error) as ctx:
            dl.check("x")
        self.assertEqual(ctx.exception.code, "G14_DEADLINE_EXCEEDED")

    def test_cancellation(self):
        e = Estate()
        tok = CancellationToken()
        tok.cancel("caller went away")
        with self.assertRaises(G14Error) as ctx:
            e.service.decide(e.request(), e.token(), cancel=tok)
        self.assertEqual(ctx.exception.code, "G14_CANCELLED")

    def test_budget_bounds(self):
        for bad in (0, -1, 61):
            with self.assertRaises(G14Error):
                Deadline(bad)


class RetryBreakerTest(unittest.TestCase):  # P1-14
    def setUp(self):
        self.clock = FakeClock()

    def call(self, fn, *, idempotent=True, breaker=None, attempts=3):
        return call_with_resilience(fn, dependency="dep", deadline=Deadline(5, self.clock), timeout_cap_s=1,
                                    breaker=breaker or CircuitBreaker("dep", clock=self.clock),
                                    retry=RetryPolicy(max_attempts=attempts), idempotent=idempotent,
                                    rng=random.Random(1), sleep=lambda s: None)

    def test_transient_failure_retried_for_idempotent_reads(self):
        n = {"c": 0}

        def fn(t):
            n["c"] += 1
            if n["c"] < 3:
                raise G14Error("G14_DEPENDENCY_UNAVAILABLE", "x")
            return "ok"
        self.assertEqual(self.call(fn), "ok")
        self.assertEqual(n["c"], 3)

    def test_non_idempotent_never_retried(self):
        n = {"c": 0}

        def fn(t):
            n["c"] += 1
            raise G14Error("G14_DEPENDENCY_UNAVAILABLE", "x")
        with self.assertRaises(G14Error):
            self.call(fn, idempotent=False)
        self.assertEqual(n["c"], 1)

    def test_security_errors_not_retried(self):
        n = {"c": 0}

        def fn(t):
            n["c"] += 1
            raise G14Error("G14_SIGNATURE_INVALID", "x")
        with self.assertRaises(G14Error):
            self.call(fn)
        self.assertEqual(n["c"], 1)

    def test_breaker_opens_half_opens_and_closes(self):
        br = CircuitBreaker("dep", failure_threshold=2, reset_after_s=10, clock=self.clock)

        def boom(t):
            raise G14Error("G14_DEPENDENCY_UNAVAILABLE", "x")
        for _ in range(2):
            with self.assertRaises(G14Error):
                self.call(boom, breaker=br, attempts=1)
        self.assertEqual(br.state, "open")
        with self.assertRaises(G14Error) as ctx:
            self.call(lambda t: "ok", breaker=br)
        self.assertEqual(ctx.exception.code, "G14_CIRCUIT_OPEN")
        self.clock.advance(10)
        self.assertEqual(br.state, "half-open")
        self.assertEqual(self.call(lambda t: "ok", breaker=br), "ok")
        self.assertEqual(br.state, "closed")

    def test_retry_amplification_bounded(self):
        with self.assertRaises(ValueError):
            RetryPolicy(max_attempts=10)

    def test_backoff_bounded_and_jittered(self):
        p, rng = RetryPolicy(), random.Random(3)
        ds = [p.delay(i, rng) for i in range(10)]
        self.assertTrue(all(0 < d <= p.max_delay_s for d in ds))


class FreshnessStaleTest(unittest.TestCase):  # P1-15 / P1-16
    def test_stale_policy_never_allows_residency_or_convergence_beyond_ttl(self):
        sp = StaleDataPolicy()
        for kind in ("policy_verdict", "convergence_proof", "placement_snapshot"):
            for mode in ("production", "staging", "test"):
                self.assertEqual(sp.allowed_age(kind, 10, mode), 10)
        self.assertEqual(sp.allowed_age("topology_snapshot", 10, "production"), 10)
        self.assertEqual(sp.allowed_age("topology_snapshot", 10, "staging"), 20)

    def test_topology_grace_only_outside_production(self):
        e = Estate(mode="staging")
        e.topology.stale_by = 900
        d = e.decide()
        self.assertFalse(d["executable"])
        self.assertEqual(d["provenance"]["inputs"]["topology"]["age_s"], 900)

    def test_configured_ttl_applies(self):
        e = Estate(config_extra={"ttls": {"topology_snapshot": 30}})
        e.topology.stale_by = 31
        with self.assertRaises(G14Error):
            e.decide()


class ReloadTest(unittest.TestCase):  # F01 reloadable knobs take effect without restart
    def test_ttl_reload_applies_to_next_decision(self):
        e = Estate()
        e.topology.stale_by = 100
        e.decide()
        e.config.activate(e.signed_config({"schema": "PK_GAP14_CONFIG/1", "revision": 2, "mode": "production",
                                           "knobs": {"decision_deadline_s": 0.5, "dependency_timeout_s": 0.05},
                                           "ttls": {"topology_snapshot": 60}}), e.clock.now())
        with self.assertRaises(G14Error) as ctx:
            e.decide()
        self.assertEqual(ctx.exception.code, "G14_STALE_INPUT")


class HealthTest(unittest.TestCase):  # P1-17
    def test_ready_then_not_ready_on_open_breaker(self):
        e = Estate()
        self.assertTrue(e.service.health()["ready"])
        e.policy.outage = True
        for _ in range(3):
            with self.assertRaises(G14Error):
                e.decide()
        h = e.service.health()
        self.assertEqual(h["dependencies"]["GAP-13"], "open")
        self.assertFalse(h["ready"])
        self.assertEqual(h["reason_code"], "G14_NOT_READY")
        self.assertTrue(h["live"])


class MetricsLoggingTest(unittest.TestCase):  # P1-18 / P1-19
    def test_signals_emitted_without_high_cardinality_labels(self):
        e = Estate()
        for i in range(30):
            e.decide(name=f"ds-{i}", size=1 + i * 20)
        text = e.service.registry.exposition()
        self.assertIn("gap14_gravity_recommendations_total", text)
        self.assertIn('gap14_decision_latency_seconds_bucket{mode="production",le="+Inf"}', text)
        for forbidden in ("t-acme", "ds-1", "wl-etl", "req-", "dec-"):
            self.assertNotIn(forbidden, text)

    def test_cardinality_budget_overflow(self):
        r = Registry()
        c = r.counter("x_total", "x", ("code",), max_series=3)
        for i in range(10):
            c.inc(code=f"c{i}")
        self.assertEqual(len(c.values), 4)
        self.assertIn((OVERFLOW,), c.values)

    def test_logs_redact_and_drop_secrets(self):
        buf = io.StringIO()
        lg = StructuredLogger(buf, redaction_key=b"k" * 32)
        lg.log("info", "x", tenant_id="t-acme", dataset="lake", token={"claims": 1}, nested={"subject": "bob", "ok": 1})
        rec = json.loads(buf.getvalue())
        self.assertNotIn("token", rec)
        self.assertTrue(rec["tenant_id"].startswith("h:"))
        self.assertNotIn("t-acme", buf.getvalue())
        self.assertNotIn("bob", buf.getvalue())
        self.assertEqual(rec["nested"]["ok"], 1)

    def test_decision_logs_are_redacted_and_carry_trace(self):
        e = Estate()
        e.decide()
        rec = json.loads(e.logs.getvalue().splitlines()[-1])
        self.assertRegex(rec["trace_id"], "^[0-9a-f]{32}$")
        self.assertNotIn("t-acme", e.logs.getvalue())

    def test_traceparent_parse_and_reject_invalid(self):
        good = TraceContext.from_traceparent("00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01")
        self.assertEqual(good.parent_id, "00f067aa0ba902b7")
        for bad in (None, "", "01-xx", "00-" + "0" * 32 + "-00f067aa0ba902b7-01"):
            self.assertIsNone(TraceContext.from_traceparent(bad).parent_id)


class ExplainTest(unittest.TestCase):  # P1-20
    def test_explain_links_inputs_alternatives_and_audit(self):
        e = Estate()
        d = e.decide(name="customers", cls="pii", size=1)
        ex = e.service.explain(d["provenance"]["decision_id"], e.token())
        self.assertEqual(ex["input_digest"], d["provenance"]["input_digest"])
        self.assertEqual(ex["audit"], d["audit"])
        self.assertEqual(ex["eliminated"][0]["code"], "RESIDENCY_FORBIDDEN")
        self.assertIn("move-compute to dub", ex["summary"])

    def test_explain_requires_scope(self):
        e = Estate()
        d = e.decide()
        with self.assertRaises(G14Error) as ctx:
            e.service.explain(d["provenance"]["decision_id"], e.token(scopes=("gravity:recommend",)))
        self.assertEqual(ctx.exception.code, "G14_FORBIDDEN")


class AdmissionTest(unittest.TestCase):  # P1-21
    def test_payload_bound(self):
        e = Estate(config_extra={"knobs": {"max_payload_bytes": 1024, "decision_deadline_s": 0.5, "dependency_timeout_s": 0.05}})
        r = e.request(profile={"shards": [{"name": f"s{i}", "size_gb": 0.01, "needed": True} for i in range(100)]})
        with self.assertRaises(G14Error) as ctx:
            e.service.decide(r, e.token())
        self.assertEqual(ctx.exception.code, "G14_PAYLOAD_TOO_LARGE")

    def test_concurrency_bound(self):
        ac = AdmissionController(max_concurrent=2, acquire_timeout_s=0.01)
        with ac, ac:
            with self.assertRaises(G14Error) as ctx:
                with ac:
                    pass
        self.assertEqual(ctx.exception.code, "G14_OVERLOADED")
        with ac:
            self.assertEqual(ac.inflight, 1)

    def test_concurrent_decisions_are_consistent(self):  # E07 race test
        e = Estate()
        reqs = [e.request(name=f"d{i}", size=float(i % 50)) for i in range(40)]
        tok = e.token()
        out, errs = [], []

        def run(r):
            try:
                out.append(e.service.decide(r, tok))
            except G14Error as exc:
                errs.append(exc.code)
        ts = [threading.Thread(target=run, args=(r,)) for r in reqs]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(out) + len(errs), 40)
        self.assertTrue(set(errs) <= {"G14_OVERLOADED"})
        seqs = sorted(d["audit"]["seq"] for d in out)
        self.assertEqual(len(set(seqs)), len(seqs))


class ReasonCodeRegistryTest(unittest.TestCase):  # B01/B02
    def test_every_code_classified(self):
        for code, r in REGISTRY.items():
            self.assertIn(r.category, {"caller", "dependency", "security", "stale-data", "internal", "policy"})
            self.assertIn(r.disposition, {"fail-closed", "retryable", "degradable", "operator-actionable"})
            self.assertTrue(r.operator_action)

    def test_unregistered_code_cannot_be_raised(self):
        with self.assertRaises(KeyError):
            G14Error("MADE_UP", "x")



class HardeningAdditionsTest(unittest.TestCase):
    def test_drain_removes_readiness_and_refuses(self):  # P1-17 A10/E04
        e = Estate()
        e.service.drain()
        self.assertFalse(e.service.health()["ready"])
        with self.assertRaises(G14Error) as ctx:
            e.decide()
        self.assertEqual(ctx.exception.code, "G14_NOT_READY")

    def test_per_tenant_fairness(self):  # P1-21 A07/E02
        ac = AdmissionController(max_concurrent=4, max_per_tenant=1)
        with ac, ac.tenant_slot("t1"):
            with self.assertRaises(G14Error):
                with ac.tenant_slot("t1"):
                    pass
            with ac.tenant_slot("t2"):
                pass

    def test_explain_access_audited(self):  # P1-20 A10
        e = Estate()
        d = e.decide()
        e.service.explain(d["provenance"]["decision_id"], e.token())
        self.assertEqual(e.audit.records[-1]["event"], "explain.accessed")

    def test_oversized_log_fields_truncated(self):  # P1-19 A09/E03
        buf = io.StringIO()
        lg = StructuredLogger(buf, redaction_key=b"k" * 32)
        lg.log("info", "x", blob="y" * 100_000, items=list(range(1000)))
        line = buf.getvalue()
        self.assertLess(len(line), 9000)
        self.assertIn('"event": "x"', line)

    def test_log_sink_failure_does_not_break_decisions(self):  # P1-19 G03 / P1-18 E04
        class Broken(io.StringIO):
            def write(self, *_):
                raise OSError("disk full")
        e = Estate()
        e.service.log.stream = Broken()
        self.assertIn("recommendation", e.decide())

    def test_degraded_inputs_marked_in_provenance(self):  # P1-16 A08/E03
        e = Estate(mode="staging")
        e.topology.stale_by = 900
        d = e.decide()
        self.assertEqual(d["provenance"]["quality"], {"status": "degraded", "stale_sources": ["topology_snapshot"]})
        self.assertIn('gap14_degraded_decisions_total{source="topology_snapshot"} 1.0', e.service.registry.exposition())

    def test_retry_error_records_attempts_and_first_error(self):  # P1-14 A10
        e = Estate()
        e.policy.outage = True
        with self.assertRaises(G14Error) as ctx:
            e.decide()
        self.assertEqual(ctx.exception.details["attempts"], 2)
        self.assertEqual(ctx.exception.details["first_error"], "G14_DEPENDENCY_UNAVAILABLE")

    def test_ttl_boundaries(self):  # P1-15 E01
        for delta, ok in ((-0.001, True), (0.0, True), (0.001, False)):
            e = Estate()
            e.replication.stale_by = 60 + delta
            if ok:
                e.decide()
            else:
                with self.assertRaises(G14Error):
                    e.decide()

    def test_probe_payload_has_no_tenant_or_secret(self):  # P1-17 E03
        e = Estate()
        e.decide()
        blob = json.dumps(e.service.health())
        for s in ("t-acme", "wl-etl", "lake", "mac", "secret"):
            self.assertNotIn(s, blob)


class InstrumentationContractTest(unittest.TestCase):
    """Asserts the documented metric set is actually emitted (D-section items)."""

    def test_documented_series_are_emitted(self):
        e = Estate()
        e.decide(name="customers", cls="pii", size=1)                 # eliminated RESIDENCY_FORBIDDEN
        e.topology.unavailable.add(("dub", "ams"))
        d = e.decide(size=2)                                         # eliminated ROUTE_UNAVAILABLE
        e.service.explain(d["provenance"]["decision_id"], e.token())
        e.service.simulate({"request": e.request(size=2), "residency": {"dub": ["public"], "ams": ["public"]},
                            "routes": [{"from": "ams", "to": "dub", "locality_multiplier": 1, "egress_per_gb": 1},
                                       {"from": "dub", "to": "ams", "locality_multiplier": 1, "egress_per_gb": 1}],
                            "compute_sites": ["dub"]}, e.token())
        with self.assertRaises(G14Error):
            e.service.decide(e.request(), None)                      # refusal by code
        e.config.activate(e.signed_config({"schema": "PK_GAP14_CONFIG/1", "revision": 2, "mode": "production",
                                           "knobs": {"decision_deadline_s": 0.5, "dependency_timeout_s": 0.05}}), e.clock.now())
        e.decide()                                                   # applies revision 2 -> build_info
        e.service.health()
        text = e.service.registry.exposition()
        for needle in ('gap14_illegal_options_eliminated_total{direction="move-data",code="RESIDENCY_FORBIDDEN"}',
                       'gap14_illegal_options_eliminated_total{direction="move-data",code="ROUTE_UNAVAILABLE"}',
                       'gap14_dependency_latency_seconds_count{dependency="GAP-13",outcome="ok"}',
                       'gap14_dependency_latency_seconds_bucket{dependency="GAP-03",outcome="ok",le="0.05"}',
                       'gap14_refusals_total{code="G14_UNAUTHENTICATED",category="security"}',
                       'gap14_explain_requests_total{outcome="ok"}', 'gap14_simulations_total{outcome="ok"}',
                       'gap14_build_info{version="4.3.0",config_revision="2",mode="production"}',
                       'gap14_config_activations_total{result="activated"}', 'gap14_readiness_transitions_total{to="ready"}',
                       'gap14_audit_records_total{result="ok"}', 'gap14_move_cost_estimate_count{direction="move-compute"}',
                       'gap14_gravity_recommendations_total{direction="none",outcome="refused",mode="production"}'):
            self.assertIn(needle, text)

    def test_latency_buckets_bracket_the_slo(self):
        from gap14_data_gravity_manager.observability import LATENCY_BUCKETS
        self.assertIn(0.05, LATENCY_BUCKETS)       # p99 SLO boundary is an exact bucket edge
        self.assertLess(LATENCY_BUCKETS[0], 0.005)

    def test_admission_rejections_counted(self):
        e = Estate(config_extra={"knobs": {"max_payload_bytes": 1024, "decision_deadline_s": 0.5, "dependency_timeout_s": 0.05}})
        with self.assertRaises(G14Error):
            e.service.decide(e.request(profile={"shards": [{"name": f"s{i}", "size_gb": 0.01, "needed": True} for i in range(100)]}), e.token())
        self.assertIn('gap14_admission_rejected_total{code="G14_PAYLOAD_TOO_LARGE"}', e.service.registry.exposition())

    def test_health_answers_while_admission_is_saturated(self):  # P1-13 A10
        e = Estate()
        ac = e.service.admission
        for _ in range(ac.max_concurrent):
            ac._sem.acquire()
        try:
            with self.assertRaises(G14Error) as ctx:
                e.decide()
            self.assertEqual(ctx.exception.code, "G14_OVERLOADED")
            h = e.service.health()
            self.assertTrue(h["live"])
        finally:
            for _ in range(ac.max_concurrent):
                ac._sem.release()

    def test_liveness_reflects_internal_deadlock_not_dependencies(self):
        e = Estate()
        e.policy.outage = True
        self.assertTrue(e.service.health()["live"])
        held = threading.Event()
        release = threading.Event()

        def hog():
            with e.service._rec_lock:
                held.set()
                release.wait(2)
        t = threading.Thread(target=hog)
        t.start()
        held.wait(1)
        self.assertFalse(e.service.health()["live"])
        release.set()
        t.join()
        self.assertTrue(e.service.health()["live"])


if __name__ == "__main__":
    unittest.main()
