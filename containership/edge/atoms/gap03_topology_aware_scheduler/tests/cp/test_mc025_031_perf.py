import json
import math
import os
import threading
import time
import unittest

from gap03_topology_aware_scheduler import Topology
from gap03_topology_aware_scheduler.benchmarks import harness
from gap03_topology_aware_scheduler.controlplane import capacity, objectives
from gap03_topology_aware_scheduler.controlplane.admission import Admission, CircuitBreaker, Limits, TokenBucket
from gap03_topology_aware_scheduler.controlplane.cache import ScoreCache
from gap03_topology_aware_scheduler.controlplane.errors import SchedulerError
from gap03_topology_aware_scheduler.controlplane.faults import ManualClock
from gap03_topology_aware_scheduler.controlplane.latency import LatencyEngine
from gap03_topology_aware_scheduler.controlplane.retry import DedupStore, Policy, Retrier
from gap03_topology_aware_scheduler.scheduler import _score_snapshot
from gap03_topology_aware_scheduler.tests.cp._util import TmpCase, covers

NODE = "spiffe://prod.example/node/"


def topo(n=4):
    t = Topology()
    base = {"a": ("eu", "dub", "r1"), "b": ("eu", "dub", "r2"), "c": ("eu", "ams", "r1"), "d": ("us", "iad", "r1")}
    for k, p in base.items():
        t.place(k, *p)
    return t


class AdmissionT(TmpCase):
    @covers("MC-025", 6, 8, 25)
    def test_mc025_independent_limits(self):
        adm = Admission(Limits(max_candidates=10, max_concurrent_scoring=2, global_rps=1000, global_burst=1000,
                               tenant_rps=1000, tenant_burst=1000), clock=self.clock)
        with self.assertRaises(SchedulerError) as cm:
            adm.admit(kind="score", candidates=11)
        self.assertEqual(cm.exception.code, "PAYLOAD_TOO_LARGE")
        r1 = adm.admit(kind="score", tenant="t", priority="system-critical")
        r2 = adm.admit(kind="score", tenant="t", priority="system-critical")
        with self.assertRaises(SchedulerError):
            adm.admit(kind="score", tenant="t", priority="system-critical")
        r1()
        r1()  # double release is harmless
        adm.admit(kind="score", tenant="t", priority="system-critical")()
        r2()

    @covers("MC-025", 7, 11, 27)
    def test_mc025_noisy_tenant_isolation_with_retry_after(self):
        """adversarial: a noisy tenant is throttled with retry-after while other tenants are unaffected."""
        adm = Admission(Limits(tenant_rps=1, tenant_burst=3, global_rps=1000, global_burst=1000), clock=self.clock)
        ok = 0
        for _ in range(10):
            try:
                adm.admit(kind="score", tenant="noisy")()
                ok += 1
            except SchedulerError as e:
                self.assertEqual(e.code, "OVERLOADED")
                self.assertIn("retry_after_s", e.detail)
        self.assertEqual(ok, 3)
        adm.admit(kind="score", tenant="quiet")()  # other tenant unaffected

    @covers("MC-025", 9, 13)
    def test_mc025_priority_shedding_and_reserved_control_pool(self):
        adm = Admission(Limits(max_concurrent_scoring=4, global_rps=1000, global_burst=1000), clock=self.clock)
        held = [adm.admit(kind="score", priority="production") for _ in range(2)]  # util 0.5
        with self.assertRaises(SchedulerError):
            adm.admit(kind="score", priority="best-effort")
        adm.admit(kind="score", priority="batch")()
        held += [adm.admit(kind="score", priority="production"), adm.admit(kind="score", priority="system-critical")]
        for op in ("health", "freeze", "release", "rollback"):
            adm.admit(kind=op)()  # control-plane ops still admitted at saturation
        self.assertGreater(adm.rejected.get("shed_best-effort", 0), 0)
        [h() for h in held]

    @covers("MC-025", 10, 27)
    def test_mc025_breaker_half_open_recovery(self):
        """fault injection: a failing dependency opens the circuit breaker; half-open probes recover it."""
        br = CircuitBreaker("sch01", threshold=2, cooldown=5, successes=2, clock=self.clock)
        for _ in range(2):
            with self.assertRaises(ZeroDivisionError):
                br.call(lambda: 1 / 0)
        self.assertEqual(br.state, "open")
        with self.assertRaises(SchedulerError):
            br.call(lambda: 1)
        self.clock.advance(6)
        br.call(lambda: 1)
        self.assertEqual(br.state, "half_open")
        br.call(lambda: 1)
        self.assertEqual(br.state, "closed")

    @covers("MC-025", 28)
    def test_mc025_burst_then_recovery_bounded(self):
        clock = ManualClock()
        tb = TokenBucket(100, 100, clock=clock)
        admitted = sum(1 for _ in range(1000) if tb.take() == 0)
        self.assertEqual(admitted, 100)
        clock.advance(1.0)
        self.assertEqual(sum(1 for _ in range(1000) if tb.take() == 0), 100)


class RetryT(TmpCase):
    def r(self, **kw):
        slept = []
        return Retrier("dep", Policy(**kw), seed=42, sleep=slept.append, clock=self.clock), slept

    @covers("MC-026", 6, 10, 25)
    def test_mc026_only_transient_codes_retried(self):
        r, _ = self.r()
        calls = []

        def perm(**k):
            calls.append(1)
            raise SchedulerError("PERMISSION_DENIED", "no")
        with self.assertRaises(SchedulerError):
            r.run(perm, op_class="read_only", deadline_s=5)
        self.assertEqual(len(calls), 1)
        with self.assertRaises(SchedulerError):
            r.run(lambda **k: 1, op_class="idempotent_mutation", deadline_s=5)  # key required
        calls.clear()

        def flaky(**k):
            calls.append(1)
            raise SchedulerError("DEPENDENCY_UNAVAILABLE", "x")
        with self.assertRaises(SchedulerError):
            r.run(flaky, op_class="non_idempotent_mutation", deadline_s=5)
        self.assertEqual(len(calls), 1)

    @covers("MC-026", 7, 8, 25)
    def test_mc026_deadline_budget_and_jittered_backoff(self):
        r, slept = self.r(max_attempts=10, attempt_timeout_s=2.0)
        timeouts = []

        def f(timeout, attempt):
            timeouts.append(timeout)
            self.clock.advance(1.5)
            raise SchedulerError("DEADLINE_EXCEEDED", "t")
        with self.assertRaises(SchedulerError):
            r.run(f, op_class="read_only", deadline_s=4.0)
        self.assertTrue(all(t <= 2.0 for t in timeouts))
        self.assertLess(timeouts[-1], 2.0)  # last attempt clipped by remaining budget
        self.assertEqual(len({round(s, 6) for s in slept}), len(slept))  # jittered, not fixed
        self.assertTrue(all(s <= 2.0 for s in slept))
        self.assertTrue(r.trace)

    @covers("MC-026", 26)

    @covers("MC-026", 9, 11, 25, 27)
    def test_mc026_idempotency_and_lost_response_probe(self):
        dd = DedupStore()
        r = Retrier("dep", Policy(), seed=1, sleep=lambda s: None, clock=self.clock, dedup=dd)
        applied = []

        def lost(**k):
            applied.append(1)
            raise SchedulerError("DEADLINE_EXCEEDED", "lost")
        out = r.run(lost, op_class="idempotent_mutation", deadline_s=5, idempotency_key="k1",
                    outcome_probe=lambda: (True, {"state": "COMMITTED"}))
        self.assertEqual(out, {"state": "COMMITTED"})
        self.assertEqual(len(applied), 1)  # no semantically duplicate mutation
        self.assertEqual(r.run(lambda **k: "other", op_class="idempotent_mutation", deadline_s=5, idempotency_key="k1"),
                         {"state": "COMMITTED"})
        self.assertEqual(dd.hits, 1)

    @covers("MC-025", 12)

    @covers("MC-026", 12, 13, 27)
    def test_mc026_retry_budget_and_poison_quarantine(self):
        r, _ = self.r(max_attempts=5, budget_min=2, budget_ratio=0.0, poison_after=2)

        def flaky(**k):
            raise SchedulerError("DEPENDENCY_UNAVAILABLE", "x")
        with self.assertRaises(SchedulerError):
            r.run(flaky, op_class="read_only", deadline_s=10)
        with self.assertRaises(SchedulerError) as cm:
            r.run(flaky, op_class="read_only", deadline_s=10)
        self.assertEqual(cm.exception.code, "OVERLOADED")  # budget exhausted
        r2, _ = self.r(poison_after=2)

        def bad(**k):
            raise SchedulerError("INVALID_ARGUMENT", "poison")
        for _ in range(2):
            with self.assertRaises(SchedulerError):
                r2.run(bad, op_class="idempotent_mutation", deadline_s=5, idempotency_key="p")
        with self.assertRaises(SchedulerError) as cm:
            r2.run(bad, op_class="idempotent_mutation", deadline_s=5, idempotency_key="p")
        self.assertIn("quarantined", cm.exception.reason)

    def test_mc026_retry_after_respected(self):
        r, slept = self.r()
        n = []

        def f(**k):
            n.append(1)
            if len(n) < 2:
                raise SchedulerError("OVERLOADED", "busy", detail={"retry_after_s": 0.75})
            return "ok"
        self.assertEqual(r.run(f, op_class="read_only", deadline_s=5), "ok")
        self.assertGreaterEqual(slept[0], 0.75)


class LatencyT(TmpCase):
    def eng(self):
        e = LatencyEngine(clock=self.clock)
        return e

    def feed(self, e, src, dst, vals, start=0):
        out = []
        for i, v in enumerate(vals):
            out.append(e.ingest(NODE + src, {"src": src, "dst": dst, "rtt_us": v, "ts": self.clock(), "sample_id": f"{src}{dst}{start + i}"}))
        return out

    @covers("MC-027", 15)

    @covers("MC-027", 17, 18)

    @covers("MC-027", 6, 7, 8, 25, 27)
    def test_mc027_producer_ownership_and_bounds(self):
        """authorization/adversarial: a producer that does not own the source endpoint is refused; negative, NaN, future and duplicate samples are rejected."""
        e = self.eng()
        with self.assertRaises(SchedulerError):
            e.ingest(NODE + "evil", {"src": "a", "dst": "b", "rtt_us": 1, "ts": self.clock(), "sample_id": "x"})
        for bad in (-1, float("nan"), float("inf"), 10**9, True, "5"):
            with self.assertRaises(SchedulerError):
                e.ingest(NODE + "a", {"src": "a", "dst": "b", "rtt_us": bad, "ts": self.clock(), "sample_id": f"b{bad}"})
        with self.assertRaises(SchedulerError):
            e.ingest(NODE + "a", {"src": "a", "dst": "b", "rtt_us": 5, "ts": self.clock() + 3600, "sample_id": "fut"})
        self.assertEqual(self.feed(e, "a", "c", [100])[0], "accepted")
        self.assertEqual(e.ingest(NODE + "a", {"src": "a", "dst": "c", "rtt_us": 100, "ts": self.clock(), "sample_id": "ac0"}),
                         "duplicate")

    @covers("MC-027", 9, 10, 11, 13, 15, 27)
    def test_mc027_poisoning_route_change_stale_sparse(self):
        """adversarial poisoning: a spike is held, only self-consistent persistent deviations are accepted as a route change; stale/sparse evidence falls back."""
        snap = topo().snapshot()
        e = self.eng()
        self.feed(e, "a", "c", [1000] * 3)
        self.assertEqual(e.refined_cost(snap, "a", "c")["status"], "sparse")
        self.feed(e, "a", "c", [1000] * 5, start=3)
        base = e.refined_cost(snap, "a", "c")
        self.assertEqual(base["status"], "measured")
        self.assertEqual(self.feed(e, "a", "c", [900_000], start=10), ["outlier_held"])  # spike ignored
        self.assertEqual(e.refined_cost(snap, "a", "c")["cost_milli"], base["cost_milli"])
        r = self.feed(e, "a", "c", [40_000, 40_000, 40_000], start=20)
        self.assertEqual(r, ["outlier_held", "outlier_held", "route_change_accepted"])  # spike excluded from the streak
        self.assertEqual(self.feed(e, "a", "c", [41_000], start=30), ["accepted"])  # new regime is the baseline
        self.assertGreater(e.refined_cost(snap, "a", "c")["cost_milli"], base["cost_milli"])
        self.clock.advance(200)
        self.assertEqual(e.refined_cost(snap, "a", "c")["status"], "stale")

    @covers("MC-027", 15)

    @covers("MC-027", 12, 25)
    def test_mc027_never_crosses_class_and_directional(self):
        snap = topo().snapshot()
        e = self.eng()
        self.feed(e, "a", "c", [10**7 - 1] * 8)   # absurdly slow same-region path
        self.feed(e, "a", "d", [1] * 8)            # absurdly fast cross-region path
        c, d = e.refined_cost(snap, "a", "c"), e.refined_cost(snap, "a", "d")
        self.assertLess(c["cost_milli"], 101_000)
        self.assertEqual(d["cost_milli"], 101_000)  # cross-region band has zero width
        self.assertLess(c["cost_milli"], d["cost_milli"])
        rev = e.refined_cost(snap, "c", "a")
        self.assertEqual(rev["direction"], "reverse_assumed")

    @covers("MC-027", 14, 28)
    def test_mc027_invalidation_and_bounded_state(self):
        e = self.eng()
        e.invalidate(1)
        self.feed(e, "a", "c", [10])
        e.invalidate(2)
        self.assertEqual(len(e.pairs), 0)


class CacheT(unittest.TestCase):
    def setUp(self):
        self.snap = topo().snapshot()

    def key(self, **over):
        kw = dict(topology_generation=self.snap.generation, config_generation=1, schema_version="1.1", scoring_version="s",
                  anchor="a", candidates=["b", "c"], spread_from=[])
        kw.update(over)
        return ScoreCache.key(**kw)

    @covers("MC-028", 6, 9, 12, 25)
    def test_mc028_key_dimensions_and_generation_invalidation(self):
        """cache key includes every state dimension; generation change invalidates; fairness/claims are never part of cached values."""
        base = self.key()
        for dim, val in dict(topology_generation=99, config_generation=2, schema_version="1.0", scoring_version="t", anchor="b",
                             candidates=["c", "b"], spread_from=["a"]).items():
            self.assertNotEqual(self.key(**{dim: val}), base, dim)
        c = ScoreCache()
        c.set_namespace(1, 1)
        c.get_or_compute(base, lambda: _score_snapshot(self.snap, "a", ["b", "c"]))
        self.assertEqual(c.size(), 1)
        c.set_namespace(2, 1)
        self.assertEqual(c.size(), 0)

    @covers("MC-028", 7, 8, 27)
    def test_mc028_immutable_values_bounded_eviction(self):
        c = ScoreCache(max_entries=3)
        v = c.get_or_compute(("k",), lambda: [1, 2])
        self.assertIsInstance(v, tuple)
        for i in range(10):
            c.get_or_compute((i,), lambda: [i])
        self.assertEqual(c.size(), 3)
        self.assertGreater(c.stats["evict"], 0)

    @covers("MC-028", 10, 11, 27)
    def test_mc028_single_flight_under_concurrency(self):
        c = ScoreCache()
        calls = []
        gate = threading.Event()

        def slow():
            calls.append(1)
            gate.wait(1)
            return (1,)
        ts = [threading.Thread(target=c.get_or_compute, args=(("k",), slow)) for _ in range(8)]
        [t.start() for t in ts]
        time.sleep(0.05)
        gate.set()
        [t.join() for t in ts]
        self.assertEqual(len(calls), 1)

    @covers("MC-028", 11)

    @covers("MC-028", 14, 28)
    def test_mc028_cache_equivalence_ttl_and_disable(self):
        clock = ManualClock()
        c = ScoreCache(ttl_s=10, clock=clock)
        k = self.key()
        direct = _score_snapshot(self.snap, "a", ["b", "c"])
        self.assertEqual(c.get_or_compute(k, lambda: direct), tuple(direct))
        clock.advance(11)
        c.get_or_compute(k, lambda: direct)
        self.assertEqual(c.stats["stale"], 1)
        off = ScoreCache(enabled=False)
        self.assertEqual(off.get_or_compute(k, lambda: direct), direct)
        self.assertEqual(off.size(), 0)


class ObjectivesT(unittest.TestCase):
    @covers("MC-029", 6, 7, 8, 25)
    def test_mc029_weights_validation_and_normalisation(self):
        for bad in ({"locality": -1}, {"locality": 0}, {"locality": 1.5}, {"locality": 10**6}, {"locality": True}):
            with self.assertRaises(ValueError):
                objectives.validate_weights(bad)
        self.assertEqual(objectives.normalise_locality(101_000), 1000)
        self.assertEqual(objectives.normalise_locality(0), 0)

    @covers("MC-029", 9, 10, 11, 12, 25)
    def test_mc029_hard_gates_outside_sum_missing_signals_tiebreak(self):
        res = objectives.compose(["b", "a", "c"], weights={"locality": 1000, "gravity": 1000},
                                 locality=lambda n: 10, gravity=lambda n: None if n == "c" else 0,
                                 hard=lambda n: ("isa",) if n == "a" else ())
        self.assertEqual([r.node for r in res], ["b", "c", "a"])  # tie broken by id; infeasible last
        self.assertFalse(res[-1].feasible)
        self.assertEqual(dict(res[1].components)["gravity"], 0)  # neutral for missing
        self.assertIn(("locality", 1000), res[0].weights)

    @covers("MC-029", 13, 14)
    def test_mc029_monotonicity_and_sensitivity(self):
        nodes = [f"n{i}" for i in range(12)]
        loc = {n: (i * 37) % 900 for i, n in enumerate(nodes)}
        grav = {n: (i * 53) % 1000 for i, n in enumerate(nodes)}
        w = {"locality": 1000, "gravity": 500}
        base = {r.node: r.total for r in objectives.compose(nodes, weights=w, locality=loc.get, gravity=grav.get)}
        better = dict(loc, n5=max(0, loc["n5"] - 100))
        after = {r.node: r.total for r in objectives.compose(nodes, weights=w, locality=better.get, gravity=grav.get)}
        self.assertLessEqual(after["n5"], base["n5"])
        s = objectives.sensitivity(nodes, weights=w, locality=loc.get, gravity=grav.get, perturb=5)
        self.assertLess(s["instability"], 0.2)

    @covers("MC-029", 15, 26)
    def test_mc029_formula_version_and_strict_spread_preserved(self):
        self.assertEqual(objectives.FORMULA_VERSION, "gap03-score/2")
        res = objectives.compose(["near", "far"], weights={"locality": 1000, "gravity": 10000},
                                 locality=lambda n: 0 if n == "near" else 1000, gravity=lambda n: 0,
                                 spread=lambda n: 1000 if n == "near" else 0)
        self.assertEqual(res[0].node, "far")  # used failure domain always sorts behind unused


class CapacityT(unittest.TestCase):
    @covers("MC-030", 6, 7, 8, 10, 25)
    def test_mc030_fit_from_measurement(self):
        samples = capacity.measure_scoring(counts=(10, 200, 800), repeats=7)
        m = capacity.fit(samples)
        self.assertGreater(m["per_candidate_us"], 0)
        p = capacity.plan(m, rps=200, candidates=1000)
        for k in ("replicas", "per_replica_rps", "commit_ceiling_rps", "commit_bottleneck", "est_queue_wait_ms", "scale_signals"):
            self.assertIn(k, p)
        self.assertGreaterEqual(p["replicas"], capacity.MIN_REPLICAS)

    @covers("MC-030", 9, 11, 12, 13)
    def test_mc030_bottlenecks_and_burst(self):
        m = {"base_us": 50.0, "per_candidate_us": 5.0}
        p = capacity.plan(m, rps=1000, candidates=1000, store_us=2000)
        self.assertTrue(p["commit_bottleneck"])  # single leader, serial fsync caps commits at 500/s
        self.assertEqual(p["commit_ceiling_rps"], 500.0)
        self.assertEqual(capacity.erlang_c(2, 3.0), 1.0)
        self.assertIn("stabilization_window_s", p["scale_signals"])

    @covers("MC-030", 14, 15)
    def test_mc030_recalibration_and_envelope(self):
        m = {"base_us": 50.0, "per_candidate_us": 5.0}
        self.assertFalse(capacity.recalibrate(m, [(100, 550.0)])["recalibrate"])
        self.assertTrue(capacity.recalibrate(m, [(100, 2000.0)])["recalibrate"])
        self.assertGreater(capacity.envelope(m)["max_candidates_for_p99_target"], 0)


class BenchT(unittest.TestCase):
    @covers("MC-031", 6, 8)
    def test_mc031_harness_runs_matrix_with_metadata(self):
        r = harness.run_case(harness.MATRIX[0], samples=5, warmup=1)
        for k in ("p50_ms", "p90_ms", "p95_ms", "p99_ms", "max_ms", "stdev_ms", "throughput_per_s", "peak_mem_kib", "result_checksum"):
            self.assertIn(k, r)
        env = harness.env_meta()
        for k in ("python", "platform", "machine", "cpu_count", "timer_resolution_s", "optimized"):
            self.assertIn(k, env)
        self.assertEqual(harness.run_case(harness.MATRIX[0], samples=3, warmup=1)["result_checksum"], r["result_checksum"])
        self.assertGreaterEqual(len(harness.MATRIX), 5)

    @covers("MC-031", 10, 13)
    def test_mc031_gate_fails_on_regression_unless_waived(self):
        th = {"cases": {"x": {"p99_ms": 10, "peak_mem_kib": 100, "regression_budget": 0.2}}, "status": "PROPOSED"}
        self.assertTrue(harness.gate([{"id": "x", "p99_ms": 11.9, "peak_mem_kib": 100}], th)["pass"])
        self.assertFalse(harness.gate([{"id": "x", "p99_ms": 12.1, "peak_mem_kib": 100}], th)["pass"])
        self.assertTrue(harness.gate([{"id": "x", "p99_ms": 99, "peak_mem_kib": 1}], th, waivers=[{"benchmarks": ["x"]}])["pass"])
        self.assertFalse(harness.gate([{"id": "y", "p99_ms": 1, "peak_mem_kib": 1}], th)["pass"])
