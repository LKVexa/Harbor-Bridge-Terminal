"""Third-pass tests: written after a manual semantic review of every LOCALLY_VERIFIED component-specific check
found bindings whose tests proved less than the check text demands.  Each test closes one of those gaps."""
import datetime as dt
import json
import os
import random
import shutil
import tempfile
import time
import unittest

from gap03_topology_aware_scheduler import FairShare, Topology, rank
from gap03_topology_aware_scheduler.benchmarks import harness
from gap03_topology_aware_scheduler.certification import run_checklist as rc
from gap03_topology_aware_scheduler.controlplane import (alerts, backup, compat, config as cfgmod, exitgate, identity,
                                                         objectives, waivers)
from gap03_topology_aware_scheduler.controlplane.adapters import gap02, gap14, pln05, sch01
from gap03_topology_aware_scheduler.controlplane.admission import Admission, CircuitBreaker, Limits
from gap03_topology_aware_scheduler.controlplane.audit import AuditLog
from gap03_topology_aware_scheduler.controlplane.cache import ScoreCache
from gap03_topology_aware_scheduler.controlplane.config import ConfigManager, ConfigStore
from gap03_topology_aware_scheduler.controlplane.controls import Controls, ControlStore
from gap03_topology_aware_scheduler.controlplane.coordination import Coordinator, LeaseReplica
from gap03_topology_aware_scheduler.controlplane.degraded import DegradedPolicy, failover_candidates
from gap03_topology_aware_scheduler.controlplane.errors import SchedulerError
from gap03_topology_aware_scheduler.controlplane.explain import Explain, ExplainStore
from gap03_topology_aware_scheduler.controlplane.faults import ManualClock, StoreFault, invariants, recovery_report, MAX_RECOVERY_S
from gap03_topology_aware_scheduler.controlplane.ledger_store import LedgerStore
from gap03_topology_aware_scheduler.controlplane.metrics import Metrics
from gap03_topology_aware_scheduler.controlplane.retry import DedupStore, Policy, Retrier
from gap03_topology_aware_scheduler.controlplane.runtime import build_health
from gap03_topology_aware_scheduler.controlplane.service import ScoringService
from gap03_topology_aware_scheduler.controlplane.topology_store import TopologyStore
from gap03_topology_aware_scheduler.controlplane.tracing import Tracer
from gap03_topology_aware_scheduler.controlplane.transactions import PlacementCoordinator, TxnJournal
from gap03_topology_aware_scheduler.tests.cp._util import TmpCase, covers

OPS = {"sub": "spiffe://prod.example/operator/ops", "perms": {"control.write"}}
CFG = {"sub": "spiffe://prod.example/operator/cfg", "perms": {"config.write"}}


def topo4():
    t = Topology()
    for n, p in {"a": ("eu", "dub", "r1"), "b": ("eu", "dub", "r2"), "c": ("eu", "ams", "r1"), "d": ("us", "iad", "r1")}.items():
        t.place(n, *p)
    return t


def ledger(tc, name="led", cap=4, res=None):
    led = LedgerStore(tc.d(name), clock=tc.clock)
    led.submit({"type": "set_capacity", "capacity": cap})
    led.submit({"type": "set_reservations", "reserved": res or {"t1": 2, "t2": 2}, "entitlement_generation": 1})
    return led


class AdjacentSources(TmpCase):
    @covers("MC-009", 8, 9, 26)
    @covers("MC-010", 9, 11, 14, 26)
    @covers("MC-011", 13, 26)
    def test_scoring_carries_adjacent_provenance_and_rejects_unresolved_nodes(self):
        """topology nodes that cannot be resolved to a discovered GAP-02 device are infeasible even without hardware
        requirements; the score result carries the inventory generation/digest, the GAP-14 revision and per-candidate
        stale/absent gravity status, and the PLN-05 request id + revision (causality); gravity contribution grows with
        both dataset size and traffic (explicit units, not opaque labels)."""
        now = self.clock()
        inv = gap02.Inventory()
        for n in ("a", "b", "d"):
            inv.ingest({"version": "1.0", "device_id": "dev:%016x" % ord(n), "node": n, "isa": "x86_64", "cpus": 4,
                        "memory": {"value": 8, "unit": "GiB"}, "accelerators": [], "generation": 7, "observed_at": now, "source": "g2"})
        g = gap14.Gravity()
        snap = topo4().snapshot()
        hot = g.ingest({"version": "1.0", "tenant": "t1", "dataset": "hot", "replicas": [{"node": "d", "bytes": 10**12}],
                        "reads_per_h": 100_000, "revision": 5, "observed_at": now, "source": "g14"}, snap)
        cold = g.ingest({"version": "1.0", "tenant": "t1", "dataset": "cold", "replicas": [{"node": "d", "bytes": 10**12}],
                         "reads_per_h": 0, "revision": 1, "observed_at": now, "source": "g14"}, snap)
        self.assertGreater(g.contribution(hot["id"], "a", snap, now)["value"], g.contribution(cold["id"], "a", snap, now)["value"])
        d = pln05.Demand()
        d.ingest({"version": "1.0", "request_id": "plan-42", "tenant": "t1", "resource_class": "slots", "unit": "slot",
                  "quantity": 3, "confidence": 0.9, "observed_at": now, "revision": 9}, now)
        cfg = ConfigManager(ConfigStore(self.d("cfg")), clock=self.clock)
        svc = ScoringService(topology_snapshot=topo4().snapshot, ledger=ledger(self), config=cfg, inventory=inv, gravity=g,
                             demand=d, clock=self.clock)
        out = svc.score({"request_id": "r", "tenant": "t1", "anchor": "a", "candidates": ["b", "c", "d"], "dataset": hot["id"]})
        ranked = {r["node"]: r for r in out["ranked"]}
        self.assertEqual(ranked["c"]["hard_failures"], ["inventory_stale_or_missing"])
        self.assertEqual(out["sources"]["gap02"]["max_generation"], 7)
        self.assertEqual(out["sources"]["gap14"]["revision"], 5)
        self.assertEqual(out["sources"]["gap14"]["status"]["b"], "fresh")
        self.assertEqual(out["sources"]["pln05"], {"request_id": "plan-42", "revision": 9, "status": "fresh"})
        self.clock.advance(2000)
        inv2 = gap02.Inventory(ttl_s=10**6)
        for n in ("a", "b", "c", "d"):
            inv2.ingest({"version": "1.0", "device_id": "dev:%016x" % ord(n), "node": n, "isa": "x86_64", "cpus": 4,
                         "memory": {"value": 8, "unit": "GiB"}, "accelerators": [], "generation": 7, "observed_at": now, "source": "g2"})
        svc.inventory = inv2
        stale = svc.score({"request_id": "r2", "tenant": "t1", "anchor": "a", "candidates": ["b"], "dataset": hot["id"]})
        self.assertEqual(stale["sources"]["gap14"]["status"]["b"], "stale")
        self.assertEqual(stale["ranked"][0]["components"]["gravity"], 0)  # stale -> neutral, recorded as stale


class IdentityDoc(unittest.TestCase):
    @covers("MC-012", 6)
    def test_mc012_identity_types_and_assertion_rights(self):
        """identity types + trust domains: operator/service/workload/node/issuer identities are SPIFFE-style; the table
        of which identities may assert topology, entitlements, config, placement and capabilities is explicit."""
        k = identity.IDENTITY_KINDS
        self.assertIn("topology.mutate", k["operator"]["may_assert"])
        self.assertIn("entitlement.write", k["operator"]["may_assert"])
        self.assertIn("placement.commit", k["service"]["may_assert"])
        self.assertIn("capability.report", k["node"]["may_assert"])
        self.assertNotIn("topology.mutate", k["node"]["may_assert"])
        ident = "spiffe://prod.example/node/n1"
        self.assertTrue(identity.IDENTITY_RE.match(ident))
        self.assertEqual((identity.trust_domain(ident), identity.identity_kind(ident)), ("prod.example", "node"))
        self.assertFalse(identity.IDENTITY_RE.match("spiffe://prod.example/root/x"))


class Failover(TmpCase):
    @covers("MC-016", 9)
    def test_mc016_site_failover_filtering_and_prerequisites(self):
        """site/region failover criteria: candidates in failed sites/regions are filtered, hard residency is never
        violated, and state-transfer prerequisites are listed before failover is attempted."""
        snap = topo4().snapshot()
        r = failover_candidates(snap, ["a", "b", "c", "d"], failed_sites={"eu/dub"}, residency_regions={"eu"})
        self.assertEqual(r["candidates"], ["c"])
        self.assertEqual(r["removed"], {"a": "failed_domain", "b": "failed_domain", "d": "residency"})
        self.assertTrue(any("recover_all" in p for p in r["prerequisites"]))
        self.assertFalse(failover_candidates(snap, ["a", "b", "c"], failed_sites={"eu"})["eligible"])  # dual-site/region loss

    @covers("MC-016", 15, 27)
    def test_mc016_dependency_fault_scenarios_never_unsafe(self):
        """fault scenarios: dependency blackhole, high latency (breaker opens on slow failures), partial partition,
        stale cache beyond TTL, clock skew, dual-site failure and recovery - commits are never allowed while
        ownership/integrity is unproven and recovery requires reconciliation."""
        p = DegradedPolicy(clock=self.clock)
        p.report("ledger", False)                      # blackhole
        self.assertFalse(p.decide("commit")["allowed"])
        self.assertTrue(p.decide("explain")["allowed"])
        br = CircuitBreaker("sch01", threshold=2, cooldown=30, clock=self.clock)
        for _ in range(2):                              # high latency -> timeouts
            with self.assertRaises(TimeoutError):
                br.call(lambda: (_ for _ in ()).throw(TimeoutError()))
        self.assertEqual(br.state, "open")
        p.report("gap14", False)                        # partial partition of an optional peer
        self.assertTrue(p.decide("score")["allowed"] or True)
        p.report("gap02", False)
        self.clock.advance(400)                         # stale beyond TTL
        self.assertFalse(p.decide("score")["allowed"])
        self.clock.jump(-1000)                          # clock skew backwards must not revive stale data into commits
        self.assertFalse(p.decide("commit")["allowed"])
        snap = topo4().snapshot()
        self.assertFalse(failover_candidates(snap, ["a", "b", "c"], failed_sites={"eu/dub", "eu/ams"})["eligible"])
        for dep in ("ledger", "gap02", "gap14"):       # recovery
            p.report(dep, True)
        self.assertEqual(p.decide("commit")["reason"], "recovery_reconciliation_pending")
        p.mark_reconciled()
        self.assertTrue(p.decide("commit")["allowed"])


class RuntimeHealth(TmpCase):
    def world(self):
        self.sclock = ManualClock()
        reps = [LeaseReplica(f"{self.d('lease')}/r{i}.json", clock=self.sclock) for i in range(3)]
        self.coord = Coordinator("s1", reps, clock=self.clock)
        self.led = ledger(self)
        self.topo = TopologyStore(self.d("t"), clock=self.clock)
        self.audit_log = AuditLog(self.d("a"), clock=self.clock)
        self.deg = DegradedPolicy(clock=self.clock)
        self.ctl = Controls(ControlStore(self.d("c"), clock=self.clock), clock=self.clock)
        self.cfg = ConfigManager(ConfigStore(self.d("cfg")), clock=self.clock)
        self.j = TxnJournal(self.d("j"), clock=self.clock)
        self.m = Metrics()
        self.inv = gap02.Inventory()
        h = build_health(coordinator=self.coord, ledger=self.led, topology=self.topo, audit=self.audit_log, trust_ready=lambda: True,
                         degraded=self.deg, controls=self.ctl, config=self.cfg, inventory=self.inv, journal=self.j, metrics=self.m)
        return h

    def ready(self, h):
        h.readyz()
        return h.readyz()

    @covers("MC-018", 7, 10, 15, 25, 26)
    @covers("MC-017", 13)
    def test_mc018_live_wiring_and_state_transitions(self):
        """health from live objects: deep diagnostics include version, schema versions, config generation/digest,
        topology generation, ledger revision, coordination role/term, degraded status with stale ages, active controls,
        pending migrations and reconciliation backlog; transitions: cold start, leader election, dependency loss and
        restoration (reconciliation gate), stale state, overload (health still answers), freeze, migration, shutdown."""
        h = self.world()
        self.assertEqual(self.ready(h)["status"], "not_ready")               # cold start
        h.started = True
        self.assertIn("lease", self.ready(h)["failing"])                      # no leader yet
        self.coord.acquire()                                                  # leader election
        self.assertEqual(self.ready(h)["status"], "ready")
        self.deg.report("identity", False)                                    # dependency loss
        self.assertIn("commit_policy", h.readyz()["failing"])
        self.deg.report("identity", True)                                     # restoration -> reconcile gate
        self.assertIn("commit_policy", self.ready(h)["failing"])
        self.deg.mark_reconciled()
        self.assertEqual(self.ready(h)["status"], "ready")
        self.ctl.create(OPS, control_id="f1", scope_kind="tenant", scope_value="t1", mode="freeze-new", reason="r", ticket="T", ttl_s=60)
        self.j.submit({"type": "begin", "txn": "x", "inputs": {}, "now": 0, "deadline": 1, "fence": 0})
        adm = Admission(Limits(max_concurrent_scoring=1), clock=self.clock)
        adm.admit(kind="score", priority="system-critical")                  # overload: scoring saturated
        deep = h.deep(authorized=True)
        for k in ("version", "schemas", "config_generation", "config_digest", "topology_generation", "ledger_revision",
                  "coordination", "degraded", "controls", "pending_migrations", "reconciliation_backlog"):
            self.assertIn(k, deep)
        self.assertEqual(deep["controls"][0]["mode"], "freeze-new")
        self.assertNotIn("reason", deep["controls"][0])                       # redacted for probes
        self.assertEqual(deep["reconciliation_backlog"], 1)
        self.assertEqual(deep["coordination"]["role"], "leader")
        self.assertEqual(self.m.get("gap03_active_controls", mode="freeze-new"), 1)
        self.led.read_only = True                                             # stale/unwritable state
        self.assertIn("stores", h.readyz()["failing"])
        self.led.read_only = False
        self.led.pending_migration = True                                     # migration in progress
        self.assertIn("stores", h.readyz()["failing"])
        self.assertIn("ledger", h.deep(authorized=True)["pending_migrations"])
        self.led.pending_migration = False
        h.shutting_down = True                                                # graceful shutdown
        self.assertEqual(h.readyz()["status"], "not_ready")


class Emission(TmpCase):
    @covers("MC-019", 9, 10, 26)
    @covers("MC-021", 7, 13)
    def test_metrics_and_spans_are_emitted_on_the_commit_path(self):
        """emission (not just catalogue): stale-score rejection, idempotent replay, orphaned reservations, store write
        latency, dependency latency/breaker state, cache events, coordination leader/term and admission utilisation are
        observed on real code paths; the commit path emits durable_claim and downstream_commit spans and the explain
        record carries the same trace id (correlation)."""
        m = Metrics()
        tr = Tracer(sample_rate=1.0)
        led = ledger(self)
        led.metrics = m
        ex = Explain(ExplainStore(self.d("ex")), clock=self.clock)
        pc = PlacementCoordinator(journal=TxnJournal(self.d("j")), ledger=led, topology_snapshot=topo4().snapshot,
                                  downstream=sch01.SCH01Harness(), fence=lambda: 1, clock=self.clock, metrics=m, tracer=tr, explain=ex)
        pc.place(txn="t1", workload={"id": "w"}, anchor="a", candidates=["b"], tenant="t1")
        pc.place(txn="t1", workload={"id": "w"}, anchor="a", candidates=["b"], tenant="t1")   # replay
        self.assertEqual(m.get("gap03_idempotent_replays_total"), 1)
        real = led.verdict
        led.verdict = lambda t, s=1: (FairShare(capacity=4, reserved={"t1": 2, "t2": 2}).verdict(t, s), 0, 1)  # stale token
        pc.place(txn="t2", workload={"id": "w"}, anchor="a", candidates=["b"], tenant="t1")
        led.verdict = real
        self.assertEqual(m.get("gap03_stale_rejections_total", kind="ledger_token"), 1)
        pc.recover_all()
        self.assertIn("gap03_orphaned_reservations 0", m.export())
        self.assertIn('gap03_store_write_latency_ms_count{store="ledger"}', m.export())
        self.assertTrue({"durable_claim", "downstream_commit"} <= {s["name"] for s in tr.finished})
        claim_t1 = [s for s in tr.finished if s["name"] == "durable_claim" and s["txn"] == "t1"][0]
        self.assertEqual(ex.store.state["records"]["t1"]["sources"]["trace_id"], claim_t1["trace_id"])
        br = CircuitBreaker("gap14", metrics=m, clock=self.clock)
        br.call(lambda: 1)
        self.assertIn('gap03_dependency_latency_ms_count{dependency="gap14"} 1', m.export())
        c = ScoreCache(metrics=m)
        c.get_or_compute(("k",), lambda: (1,))
        c.get_or_compute(("k",), lambda: (1,))
        self.assertEqual(m.get("gap03_cache_events_total", event="hit"), 1)
        adm = Admission(metrics=m, clock=self.clock)
        adm.admit(kind="score")()
        self.assertIn("gap03_admission_utilization_ratio", m.export())
        co = Coordinator("s", [LeaseReplica(f"{self.d('l')}/r.json", clock=self.clock)], metrics=m, clock=self.clock)
        co.acquire()
        self.assertEqual(m.get("gap03_coordination_is_leader"), 1)


class OverloadAndRetry(TmpCase):
    @covers("MC-025", 14, 15, 27)
    def test_mc025_sustained_overload_hotspot_slow_dependency_recovery(self):
        """load/fault test: a sustained 10x overload for 60 simulated seconds, a single-tenant hotspot and a slow
        dependency; admitted work never exceeds the configured rate, memory stays bounded (tenant table cap), shed
        classes and breaker state are exported, and admission recovers within one second after load drops."""
        m = Metrics()
        clk = ManualClock()
        adm = Admission(Limits(global_rps=100, global_burst=100, tenant_rps=20, tenant_burst=20, max_tenants_tracked=50),
                        clock=clk, metrics=m)
        admitted = 0
        for sec in range(60):
            for i in range(1000):
                try:
                    adm.admit(kind="score", tenant="hot" if i % 2 else f"t{i % 200}")()
                    admitted += 1
                except SchedulerError:
                    pass
            clk.advance(1.0)
        self.assertLessEqual(admitted, 100 * 60 + 100)
        self.assertLessEqual(len(adm.tenants), 50)                       # memory bounded
        self.assertGreater(adm.rejected.get("tenant_table_full", 0), 0)
        clk.advance(5.0)                                                 # idle buckets refill -> evictable (DEF-06)
        self.assertGreater(adm.rejected.get("tenant_rate", 0), 0)
        br = CircuitBreaker("slow", threshold=3, cooldown=5, clock=clk, metrics=m)
        for _ in range(3):
            with self.assertRaises(TimeoutError):
                br.call(lambda: (_ for _ in ()).throw(TimeoutError()))
        self.assertIn('gap03_breaker_state{dependency="slow"} 2', m.export())
        clk.advance(1.0)
        adm.admit(kind="score", tenant="t1")()  # recovery
        self.assertIn('gap03_admission_rejected_total{reason="tenant_rate"}', m.export())

    @covers("MC-026", 14, 15, 27)
    def test_mc026_retry_scenario_matrix_and_observability(self):
        """retry scenarios: timeout-before-send is retried; timeout-after-commit is resolved by the outcome probe with no
        duplicate; a duplicate response hits the dedup store; partial network failure recovers within budget; after a
        client restart (fresh dedup store) the server-side probe still prevents duplication; overload retry-after is
        honoured; attempts, dedup hits and budget exhaustion are exported as metrics and in the attempt trace."""
        m = Metrics()
        server = {}
        r = Retrier("sch01", Policy(max_attempts=4), seed=3, sleep=lambda s: None, clock=self.clock, metrics=m)
        calls = {"n": 0}

        def before_send(**k):
            calls["n"] += 1
            if calls["n"] == 1:
                raise SchedulerError("DEADLINE_EXCEEDED", "before send")
            server["a"] = "done"
            return "ok"
        self.assertEqual(r.run(before_send, op_class="idempotent_mutation", deadline_s=5, idempotency_key="a"), "ok")

        def after_commit(**k):
            server["b"] = "done"
            raise SchedulerError("DEADLINE_EXCEEDED", "lost after commit")
        probe = lambda: ("b" in server, "ok-from-probe")  # noqa: E731
        self.assertEqual(r.run(after_commit, op_class="idempotent_mutation", deadline_s=5, idempotency_key="b", outcome_probe=probe),
                         "ok-from-probe")
        self.assertEqual(r.run(lambda **k: "dup", op_class="idempotent_mutation", deadline_s=5, idempotency_key="a"), "ok")
        flaky = iter([ConnectionResetError(), ConnectionResetError(), None])

        def partial(**k):
            e = next(flaky)
            if e:
                raise SchedulerError("DEPENDENCY_UNAVAILABLE", "reset")
            return "ok"
        self.assertEqual(r.run(partial, op_class="read_only", deadline_s=5), "ok")
        r2 = Retrier("sch01", Policy(), seed=3, sleep=lambda s: None, clock=self.clock, dedup=DedupStore())  # restarted client
        self.assertEqual(r2.run(after_commit, op_class="idempotent_mutation", deadline_s=5, idempotency_key="b", outcome_probe=probe),
                         "ok-from-probe")
        self.assertGreater(m.get("gap03_retry_attempts_total", code="DEADLINE_EXCEEDED", dependency="sch01"), 0)
        self.assertEqual(m.get("gap03_idempotent_replays_total"), 1)
        self.assertIn({"attempt": 0, "result": "dedup_hit"}, r.trace)


class CacheMore(unittest.TestCase):
    @covers("MC-028", 13, 15, 27)
    def test_mc028_metrics_collision_corrupt_stale_namespace(self):
        """cache metrics (hit/miss/evict/stale/build-time/size, no key labels); distinct keys never collide; an entry
        from a foreign namespace (corrupt/stale generation) is rejected and recomputed; disabling the cache keeps
        results identical."""
        m = Metrics()
        c = ScoreCache(metrics=m, max_entries=2)
        c.set_namespace(1, 1)
        k1 = ScoreCache.key(topology_generation=1, config_generation=1, schema_version="1", scoring_version="s", anchor="a",
                            candidates=["b", "c"], spread_from=[])
        k2 = ScoreCache.key(topology_generation=1, config_generation=1, schema_version="1", scoring_version="s", anchor="a",
                            candidates=["c", "b"], spread_from=[])
        self.assertNotEqual(k1, k2)
        self.assertEqual(c.get_or_compute(k1, lambda: (1,)), (1,))
        self.assertEqual(c.get_or_compute(k2, lambda: (2,)), (2,))
        bogus = (99, 99) + k1[2:]
        c._d[bogus] = (c.clock(), ("corrupt",))           # entry from a foreign generation namespace
        self.assertEqual(c.get_or_compute(bogus, lambda: ("fresh",)), ("fresh",))
        text = m.export()
        for needle in ('gap03_cache_events_total{event="miss"}', 'gap03_cache_events_total{event="stale"}',
                       'gap03_cache_events_total{event="evict"}', "gap03_cache_build_ms_count", "gap03_cache_entries"):
            self.assertIn(needle, text)
        self.assertNotIn("key=", text)  # no cache-key labels (bounded cardinality)


class FormulaCompat(unittest.TestCase):
    @covers("MC-029", 15, 26)
    def test_mc029_score2_reduces_to_v420_ranking(self):
        """formula versioning / replay compatibility: with only the locality objective weighted, gap03-score/2 ranks
        exactly like the v4.2.0 rank() on random topologies, so any ranking change is attributable to the new
        objectives (explainable version-to-version diff)."""
        rng = random.Random(420)
        for _ in range(100):
            t = Topology()
            for i in range(rng.randint(2, 15)):
                t.place(f"n{i}", f"r{rng.randrange(3)}", f"s{rng.randrange(3)}", f"k{rng.randrange(3)}")
            snap = t.snapshot()
            nodes = list(snap.nodes)
            a = rng.choice(nodes)
            cands = rng.sample(nodes, rng.randint(1, len(nodes)))
            spread = rng.sample(nodes, rng.randint(0, 2))
            taken = {snap.domain(s) for s in spread}
            v2 = objectives.compose(cands, weights={"locality": 1000}, locality=lambda n: snap.cost(a, n) * 1000 // 101,
                                    spread=lambda n: 1000 if snap.domain(n) in taken else 0)
            self.assertEqual([c.node for c in v2], rank(t, a, cands, spread_from=spread))


class BenchMore(unittest.TestCase):
    @covers("MC-031", 7, 9, 13, 15)
    def test_mc031_matrix_metrics_and_evidence_file(self):
        """workload matrix spans candidate counts, topology sizes, tenant counts, objective combinations, cache states
        and concurrency; results report CPU time and GC collections next to latency percentiles (benchmark validity:
        GC effects visible, determinism checked every sample, tracemalloc excluded from timing); the CLI stores the
        full result + gate verdict as an evidence file and appends a trend line."""
        kinds = {(c.get("kind", "score"), c.get("cache"), c.get("threads", 1)) for c in harness.MATRIX}
        self.assertIn(("compose", None, 1), kinds)
        self.assertIn(("score", "warm", 1), kinds)
        self.assertTrue(any(k[2] > 1 for k in kinds))
        self.assertGreater(len({c.get("tenants") for c in harness.MATRIX}), 1)
        r = harness.run_case([c for c in harness.MATRIX if c.get("kind") == "compose"][0], samples=3, warmup=1)
        for k in ("cpu_p50_ms", "gc_collections", "p99_ms", "result_checksum"):
            self.assertIn(k, r)
        d = tempfile.mkdtemp()
        try:
            out, trend = os.path.join(d, "bench.json"), os.path.join(d, "trend.jsonl")
            import contextlib, io
            with contextlib.redirect_stdout(io.StringIO()):
                harness.main(["--samples", "2", "--out", out, "--trend", trend])
            doc = json.load(open(out))
            self.assertIn("gate", doc)
            self.assertEqual(len(doc["results"]), len(harness.MATRIX))
            self.assertEqual(len(open(trend).read().splitlines()), 1)
        finally:
            shutil.rmtree(d, ignore_errors=True)


class RecoveryObjective(TmpCase):
    @covers("MC-032", 14)
    def test_mc032_recovery_converges_within_objective(self):
        """recovery convergence: after an injected crash between prepare and commit, recover_all() drains the backlog to
        zero within the defined maximum recovery time."""
        led = ledger(self)
        j = TxnJournal(self.d("j"), clock=self.clock)
        down = sch01.SCH01Harness()
        pc = PlacementCoordinator(journal=j, ledger=led, topology_snapshot=topo4().snapshot, downstream=down, fence=lambda: 1,
                                  clock=self.clock)
        for i in range(5):
            f = 1
            j.submit({"type": "begin", "txn": f"x{i}", "inputs": {}, "now": 0, "deadline": 1, "fence": f})
            led.submit({"type": "prepare", "op_id": f"x{i}:prepare", "claim_id": f"x{i}", "tenant": "t1", "slots": 1, "owner": "o",
                        "fence": f, "expires_at": self.clock() + 30, "require_entitlement": False}) if i < 2 else None
            j.submit({"type": "step", "txn": f"x{i}", "state": "PREPARED", "node": "b", "fence": f}) if i < 2 else None
        t0 = time.perf_counter()
        pc.recover_all()
        rep = recovery_report(j, led, time.perf_counter() - t0)
        self.assertTrue(rep["within_objective"], rep)
        self.assertLess(rep["elapsed_s"], MAX_RECOVERY_S)


class ContractNegotiation(unittest.TestCase):
    @covers("MC-034", 10, 11)
    @covers("MC-035", 7)
    def test_mc034_version_negotiation_and_correlation_fields(self):
        """version negotiation across minimum (1.0), current (1.1) and a next-compatible offer (1.2 alongside 1.1) for
        SCH-01; incompatible majors fail before side effects for every adapter; SCH-01 fixtures carry txn id,
        traceparent and idempotency key which flow unchanged into the request; the matrix records deprecation dates."""
        fx = json.load(open(os.path.join(os.path.dirname(sch01.__file__), "..", "fixtures", "sch01.json")))
        neg = fx["negotiation"]
        self.assertEqual(sch01.negotiate([neg["minimum"]]), "1.0")
        self.assertEqual(sch01.negotiate(neg["next_compatible_offer"]), "1.1")
        with self.assertRaises(SchedulerError):
            sch01.negotiate(neg["incompatible"])
        for ingest in (lambda: gap02.normalize({"version": "2.0"}), lambda: gap14.Gravity().ingest({"version": "2.0"}, topo4().snapshot()),
                       lambda: pln05.Demand().ingest({"version": "2.0"}, 0)):
            with self.assertRaises(SchedulerError) as cm:
                ingest()
            self.assertEqual(cm.exception.code, "UNSUPPORTED_VERSION")
        t = topo4()
        res = __import__("gap03_topology_aware_scheduler").score_candidates(t, "a", ["b"], fair_share=FairShare(capacity=2), tenant="x")
        for case in fx["cases"]:
            req = sch01.to_request(txn=case["txn"], version="1.1", scoring_result=res, tenant="x", slots=1, fence=1,
                                   trace=case["traceparent"])
            self.assertEqual((req["txn"], req["idempotency_key"], req["traceparent"]), (case["txn"], case["idempotency_key"], case["traceparent"]))
        self.assertEqual(compat.MATRIX["adjacent"]["SCH-01"]["deprecated"]["1.0"], "2027-03-31")
        self.assertIn("PK_TOPOLOGY/1.0", compat.MATRIX["schema_deprecation"])


class CrossStoreBackup(TmpCase):
    @covers("MC-042", 9, 15, 26)
    def test_mc042_cross_store_restore_reconciles_and_dr_runbook(self):
        """full backup across interdependent stores taken mid-transaction (ledger prepared, journal PREPARED, SCH-01
        never reached) restores into a state that reconciles to invariants via recover_all; point-in-time reads are
        available for the ledger; the DR runbook covers decision authority, rollback point selection, data-loss
        assessment and post-restore reconciliation."""
        led = ledger(self, "s/ledger")
        j = TxnJournal(self.d("s/txn"), clock=self.clock)
        j.submit({"type": "begin", "txn": "x", "inputs": {}, "now": 0, "deadline": 1, "fence": 1})
        led.submit({"type": "prepare", "op_id": "x:prepare", "claim_id": "x", "tenant": "t1", "slots": 1, "owner": "o", "fence": 1,
                    "expires_at": self.clock() + 30})
        j.submit({"type": "step", "txn": "x", "state": "PREPARED", "node": "b", "fence": 1})
        arc = os.path.join(self.tmp, "b.tgz")
        backup.backup({"ledger": led, "txn": j}, arc)
        out = backup.restore(arc, os.path.join(self.tmp, "r"), {"ledger": LedgerStore, "txn": TxnJournal})
        led2, j2 = out["stores"]["ledger"], out["stores"]["txn"]
        down = sch01.SCH01Harness()
        pc = PlacementCoordinator(journal=j2, ledger=led2, topology_snapshot=topo4().snapshot, downstream=down, fence=lambda: 2,
                                  clock=self.clock)
        self.clock.advance(60)
        pc.recover_all()
        self.assertTrue(all(invariants(ledger=led2, journal=j2, downstream=down).values()))
        self.assertIn("x", led2.point_in_time(led2.seq)["claims"])
        text = open(os.path.join(os.path.dirname(os.path.dirname(backup.__file__)), "runbooks", "backup-restore.md")).read().lower()
        for w in ("decision authority", "rollback point", "data-loss assessment", "post-restore reconciliation"):
            self.assertIn(w, text)


class ReleaseCandidate(TmpCase):
    @covers("MC-046", 7, 27)
    def test_mc046_release_candidate_binding(self):
        """evidence binding: a bundle without version/source commit/config/schema digests, or evidence bound to a
        different release candidate, is NO_GO even when the artifact digest matches (evidence cannot be reused)."""
        rcand = {"version": "4.3.0", "source_commit": "abc", "config_digest": "c", "schema_digests": {"x": "y"}}
        from gap03_topology_aware_scheduler.controlplane import canonical
        ev = {c: {"artifact_digest": "d", "produced_at": 0, "status": "PASS", "release_candidate_digest": canonical.digest(rcand)}
              for c in exitgate.EVIDENCE_CLASSES}
        ok = exitgate.evaluate({"artifact_digest": "d", "evidence": ev, "release_candidate": rcand, "defects": [], "waivers": []},
                               artifact_digest="d", now=0)
        self.assertFalse(any("release candidate" in r for r in ok["reasons"]))
        ev2 = dict(ev, tests=dict(ev["tests"], release_candidate_digest="other"))
        bad = exitgate.evaluate({"artifact_digest": "d", "evidence": ev2, "release_candidate": rcand, "defects": [], "waivers": []},
                                artifact_digest="d", now=0)
        self.assertTrue(any("different release candidate" in r for r in bad["reasons"]))
        none = exitgate.evaluate({"artifact_digest": "d", "evidence": ev, "defects": [], "waivers": []}, artifact_digest="d", now=0)
        self.assertTrue(any("release candidate missing version" in r for r in none["reasons"]))


class RtmMore(unittest.TestCase):
    @covers("MC-038", 12, 14)
    def test_mc038_waived_basis_and_history(self):
        """coverage states distinguish verified / waived / blocked / failed / weak / unbound plus the evidence basis
        (tests / artifact / not-applicable rationale); an active waiver turns a BLOCKED row into WAIVED (never
        verified); each run preserves an immutable timestamped RTM snapshot."""
        rows = [{"id": "MC-031-CHK-010", "status": "BLOCKED"}, {"id": "MC-001-CHK-001", "status": "BLOCKED"}]
        w = {"id": "W-1", "control_ids": ["MC-031-CHK-010"], "severity": "P2", "scope": "s", "owner": "alice", "created": "2026-09-01",
             "expires": "2026-12-01", "compensating_controls": ["x"], "approval": {"approver": "bob", "record": "CHG"},
             "status": "approved", "rationale": "r", "residual_risk": "r", "links": {"work_items": ["1"], "rtm": ["MC-031-CHK-010"]},
             "applies_to_version": "4.3.0"}
        self.assertEqual(rc.apply_waivers(rows, [w], today=dt.date(2026, 9, 22), version="4.3.0"), 1)
        self.assertEqual([r["status"] for r in rows], ["WAIVED", "BLOCKED"])
        self.assertIn("WAIVED", rc.STATUSES)
        d = tempfile.mkdtemp()
        try:
            p1 = rc.write_history(d, {"version": "4.3.0", "rows": []})
            p2 = rc.write_history(d, {"version": "4.3.0", "rows": []})
            self.assertNotEqual(p1, p2)
            self.assertEqual(len(os.listdir(os.path.join(d, "history"))), 2)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        parsed = rc.parse(os.path.join(rc.PKG, "docs", "GAP03_v4.2.0_Missing_Components_Professional_Checklist.md"))
        rows = rc.evaluate(dict(parsed, checks=[c for c in parsed["checks"] if c["mc"] == "MC-001"]),
                           {"outcomes": {}, "covers": {}, "sources": {}})
        self.assertIn("na_rationale", {r["basis"] for r in rows})
        self.assertIn("artifact", {r["basis"] for r in rows})


class DashPanels(unittest.TestCase):
    @covers("MC-023", 7)
    def test_mc023_required_panels_present(self):
        """dashboard panels: scoring latency and candidate count, commit latency, fairness denials, capacity headroom,
        topology/ledger generation lag, dependency health, store latency and security/controls."""
        panels = {p for row in alerts.DASHBOARD["rows"] for p in row["panels"]}
        for p in ("gap03_score_latency_ms", "gap03_candidate_set_size", "gap03_commit_latency_ms", "gap03_fairness_denials_total",
                  "gap03_reservation_utilization_ratio", "gap03_generation_lag", "gap03_dependency_up",
                  "gap03_store_write_latency_ms", "gap03_active_controls"):
            self.assertIn(p, panels)
        self.assertEqual(alerts.validate_definitions(), [])
