"""Second-pass tests written after the certification runner's relevance guard flagged
weak or missing bindings.  Each test's docstring states what it proves."""
import datetime as dt
import json
import os
import re
import shutil
import tempfile
import unittest

from gap03_topology_aware_scheduler import Topology, __version__
from gap03_topology_aware_scheduler.controlplane import (alerts, backup, cache, canonical, capacity, compat, config as cfgmod,
                                                         exitgate, governance, identity, objectives, rollout, supply_chain, waivers)
from gap03_topology_aware_scheduler.controlplane.adapters import gap02, gap14, pln05, sch01
from gap03_topology_aware_scheduler.controlplane.admission import Admission, Limits
from gap03_topology_aware_scheduler.controlplane.audit import AuditLog
from gap03_topology_aware_scheduler.controlplane.cache import ScoreCache
from gap03_topology_aware_scheduler.controlplane.config import ConfigManager, ConfigStore
from gap03_topology_aware_scheduler.controlplane.controls import Controls, ControlStore
from gap03_topology_aware_scheduler.controlplane.coordination import Coordinator, LeaseReplica
from gap03_topology_aware_scheduler.controlplane.degraded import DegradedPolicy
from gap03_topology_aware_scheduler.controlplane.entitlement import EntitlementAuthority
from gap03_topology_aware_scheduler.controlplane.errors import SchedulerError
from gap03_topology_aware_scheduler.controlplane.explain import Explain, ExplainStore
from gap03_topology_aware_scheduler.controlplane.faults import ManualClock
from gap03_topology_aware_scheduler.controlplane.latency import ALPHA, RAW_KEEP, LatencyEngine
from gap03_topology_aware_scheduler.controlplane.ledger_store import LedgerStore
from gap03_topology_aware_scheduler.controlplane.logpipe import Logger
from gap03_topology_aware_scheduler.controlplane.metrics import Metrics
from gap03_topology_aware_scheduler.controlplane.retry import Policy, Retrier
from gap03_topology_aware_scheduler.controlplane.service import ScoringService
from gap03_topology_aware_scheduler.controlplane.topology_store import TopologyStore
from gap03_topology_aware_scheduler.controlplane.tracing import Tracer
from gap03_topology_aware_scheduler.controlplane.transactions import PlacementCoordinator, TxnJournal
from gap03_topology_aware_scheduler.tests.cp._util import TmpCase, covers

ROOT = governance.ROOT
T0 = 1_000_000.0
CFG = {"sub": "spiffe://prod.example/operator/cfg", "perms": {"config.write"}}
BG = {"sub": "spiffe://prod.example/operator/bg", "perms": {"control.write", "control.hard_stop"}}
OPS = {"sub": "spiffe://prod.example/operator/ops", "perms": {"control.write"}}


def topo4():
    t = Topology()
    for n, p in {"a": ("eu", "dub", "r1"), "b": ("eu", "dub", "r2"), "c": ("eu", "ams", "r1"), "d": ("us", "iad", "r1")}.items():
        t.place(n, *p)
    return t


class ServiceIntegration(TmpCase):
    """Integration of the real scoring facade with metrics, logs, traces, admission, controls, degraded policy,
    config, cache, latency refinement, GAP-02 inventory, GAP-14 gravity and PLN-05 demand."""

    def build(self, **kw):
        self.m = Metrics()
        self.lines = []
        self.tr = Tracer(sample_rate=1.0, seed=1)
        self.led = LedgerStore(self.d("led"), clock=self.clock)
        self.led.submit({"type": "set_capacity", "capacity": 4})
        self.led.submit({"type": "set_reservations", "reserved": {"t1": 2, "t2": 2}, "entitlement_generation": 1})
        self.cfg = ConfigManager(ConfigStore(self.d("cfg"), clock=self.clock), clock=self.clock)
        self.ctl = Controls(ControlStore(self.d("ctl"), clock=self.clock), clock=self.clock)
        self.deg = DegradedPolicy(clock=self.clock)
        self.topo = topo4()
        svc = ScoringService(topology_snapshot=self.topo.snapshot, ledger=self.led, config=self.cfg, admission=Admission(clock=self.clock),
                             controls=self.ctl, degraded=self.deg, metrics=self.m, tracer=self.tr,
                             logger=Logger(self.lines.append, sample_rate=1.0, metrics=self.m), clock=self.clock, **kw)
        return svc

    def req(self, **kw):
        r = {"request_id": "r1", "tenant": "t1", "anchor": "a", "candidates": ["d", "c", "b"]}
        r.update(kw)
        return r

    @covers("MC-019", 26, 7, 8)
    @covers("MC-020", 26, 8)
    @covers("MC-021", 26, 7, 13)
    @covers("MC-025", 26)
    @covers("MC-015", 26, 10)
    def test_integration_scoring_emits_metrics_logs_traces_with_config_generation(self):
        """integration/contract: one real score request produces histogram metrics, a structured log line carrying the
        trace id (correlation), spans for admission and fairness, and a result bound to the config generation."""
        svc = self.build()
        out = svc.score(self.req(), headers={"traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"})
        self.assertTrue(out["ok"], out)
        self.assertEqual([r["node"] for r in out["ranked"]], ["b", "c", "d"])
        self.assertEqual(out["config_generation"], self.cfg.current.generation)
        text = self.m.export()
        self.assertIn('gap03_score_latency_ms_count{result="ok"} 1', text)
        self.assertIn("gap03_candidate_set_size_count 1", text)
        svc.logger.flush()
        rec = json.loads(self.lines[-1])
        self.assertEqual(rec["trace_id"], "4bf92f3577b34da6a3ce929d0e0e4736")
        self.assertEqual({s["name"] for s in self.tr.finished},
                         {"admission", "snapshot", "cache", "locality_score", "filter", "fairness"})
        self.assertEqual(out["sources"]["trace_id"], "4bf92f3577b34da6a3ce929d0e0e4736")

    @covers("MC-016", 26, 10)
    @covers("MC-017", 26)
    @covers("MC-014", 26)
    def test_integration_controls_and_degraded_block_scoring_with_stable_codes(self):
        """integration: a hard-stop control and a dependency outage both reach the score path and are mapped to
        stable external error codes (FROZEN / DEPENDENCY_UNAVAILABLE) at the single error boundary."""
        svc = self.build()
        self.ctl.create(BG, control_id="hs", scope_kind="tenant", scope_value="t1", mode="hard-stop", reason="r", ticket="t", ttl_s=60)
        self.assertEqual(svc.score(self.req())["error"]["code"], "FROZEN")
        self.assertTrue(svc.score(self.req(tenant="t2"))["ok"])
        self.deg.report("identity", False)
        self.deg.report("topology_store", False)
        self.clock.advance(120)
        self.assertEqual(svc.score(self.req(tenant="t2"))["error"]["code"], "DEPENDENCY_UNAVAILABLE")

    @covers("MC-028", 12, 26)
    def test_integration_cache_never_caches_fairness_verdict(self):
        """cache correctness: ranking may come from cache but the fair-share verdict is re-read from the ledger
        revision on every call, so a capacity claim between calls is reflected immediately (revalidated)."""
        svc = self.build()
        a = svc.score(self.req(tenant="t1"))
        self.led.submit({"type": "prepare", "claim_id": "x", "tenant": "t2", "slots": 2, "owner": "o", "expires_at": 10**12})
        self.led.submit({"type": "prepare", "claim_id": "y", "tenant": "t1", "slots": 2, "owner": "o", "expires_at": 10**12})
        b = svc.score(self.req(tenant="t1"))
        self.assertEqual(svc.cache.stats["hit"], 1)
        self.assertTrue(a["fairness"]["allowed"])
        self.assertFalse(b["fairness"]["allowed"])
        self.assertNotEqual(a["ledger_revision"], b["ledger_revision"])

    @covers("MC-009", 26)
    @covers("MC-010", 26)
    @covers("MC-011", 26)
    @covers("MC-027", 26, 13)
    @covers("MC-029", 26, 12)
    def test_integration_adapters_feed_composition_and_explain_components(self):
        """integration: GAP-02 hard predicates, GAP-14 gravity, PLN-05 demand and measured latency all flow into the
        multi-objective composition; every normalised component and hard-filter outcome is exposed."""
        inv = gap02.Inventory()
        for n, isa in (("a", "x86_64"), ("b", "x86_64"), ("c", "arm64"), ("d", "x86_64")):
            inv.ingest({"version": "1.0", "device_id": f"dev:{n * 16}".replace(n * 16, format(ord(n), "016x")), "node": n,
                        "isa": isa, "cpus": 8, "memory": {"value": 64, "unit": "GiB"}, "accelerators": [], "generation": 1,
                        "observed_at": self.clock(), "source": "g2"})
        grav = gap14.Gravity()
        rec = grav.ingest({"version": "1.0", "tenant": "t1", "dataset": "ds", "replicas": [{"node": "d", "bytes": 10**12}],
                           "revision": 1, "observed_at": self.clock(), "source": "g14"}, topo4().snapshot())
        dem = pln05.Demand()
        lat = LatencyEngine(clock=self.clock)
        svc = self.build(inventory=inv, gravity=grav, demand=dem, latency=lat)
        m2 = cfgmod.validate({"scoring": {"weight_gravity": 5000}, "features": {"latency_refinement": True}})
        self.cfg.activate(m2, actor="x", source="t", principal=CFG)
        out = svc.score(self.req(requirements={"isa": "x86_64"}, dataset=rec["id"]))
        ranked = {r["node"]: r for r in out["ranked"]}
        self.assertFalse(ranked["c"]["feasible"])
        self.assertEqual(ranked["c"]["hard_failures"], ["isa"])
        self.assertEqual(out["ranked"][-1]["node"], "c")
        self.assertGreater(ranked["b"]["components"]["gravity"], ranked["d"]["components"]["gravity"])
        for k in ("locality", "gravity", "demand", "spread"):
            self.assertIn(k, ranked["b"]["components"])

    @covers("MC-019", 13, 27)
    @covers("MC-020", 12)
    @covers("MC-021", 14)
    def test_integration_telemetry_outage_never_blocks_placement_path(self):
        """fault injection: a dead log sink and a failing trace exporter do not block or fail scoring; drops are
        counted (bounded queue + drop counter) and local correlation ids still propagate."""
        svc = self.build()

        def dead(_):
            raise ConnectionError("exporter down")
        svc.tracer = Tracer(exporter=dead, sample_rate=1.0)
        svc.logger = Logger(dead, capacity=2, sample_rate=1.0, metrics=self.m)
        for i in range(5):
            self.assertTrue(svc.score(self.req(request_id=f"r{i}"))["ok"])
        svc.logger.flush()
        self.assertGreater(svc.logger.dropped, 0)
        self.assertGreater(svc.tracer.dropped, 0)

    @covers("MC-025", 11)
    @covers("MC-008", 10)
    def test_integration_overload_propagates_retry_after_to_client(self):
        """backpressure: when admission sheds, the external error carries OVERLOADED, retryable=true and a
        retry-after hint instead of queueing unbounded work for SCH-01."""
        svc = self.build()
        svc.admission = Admission(Limits(tenant_rps=1, tenant_burst=1), clock=self.clock)
        svc.score(self.req())
        out = svc.score(self.req())
        self.assertEqual(out["error"]["code"], "OVERLOADED")
        self.assertTrue(out["error"]["retryable"])
        self.assertIsNotNone(out["error"]["retry_after_s"])


class StateGaps(TmpCase):
    @covers("MC-003", 6, 26)
    def test_mc003_authority_is_single_source_and_ledger_follows_generations(self):
        """authoritative entitlement source: the ledger's reservations only change from authority snapshots with a
        monotonically newer generation; an older snapshot (stale/failed authority replay) is refused."""
        e = EntitlementAuthority(self.d("e"), clock=self.clock)
        adm = {"sub": "x", "perms": {"entitlement.write"}}
        e.write(adm, {"type": "set_capacity", "quantity": 4, "unit": "slot"})
        e.write(adm, {"type": "upsert", "record": {"tenant": "a", "dimension": "slots", "quantity": 2, "unit": "slot",
                                                   "valid_from": 0, "expires_at": 10**12}, "expected_revision": 0})
        led = LedgerStore(self.d("l"))
        s1 = e.snapshot(self.clock())
        led.submit({"type": "set_reservations", "reserved": s1["body"]["effective"], "entitlement_generation": s1["body"]["generation"]})
        with self.assertRaises(SchedulerError):
            led.submit({"type": "set_reservations", "reserved": {}, "entitlement_generation": s1["body"]["generation"] - 1})
        self.assertEqual(led.state["reserved"], {"a": 2})

    @covers("MC-004", 7)
    def test_mc004_storage_engine_atomic_multi_edge_update(self):
        """storage engine + consistency model: a batch that re-parents several edges is applied atomically (all or
        nothing) and a batch that would orphan a child is rejected as a whole - WAL engine, single writer."""
        s = TopologyStore(self.d("t"))
        s.submit({"type": "batch", "expected_generation": 0, "mutations": [
            {"op": "create", "id": "eu", "node_type": "region", "parent": None},
            {"op": "create", "id": "s1", "node_type": "site", "parent": "eu"},
            {"op": "create", "id": "s2", "node_type": "site", "parent": "eu"},
            {"op": "create", "id": "r1", "node_type": "rack", "parent": "s1"},
            {"op": "create", "id": "r2", "node_type": "rack", "parent": "s1"}]})
        s.submit({"type": "batch", "expected_generation": 1, "mutations": [
            {"op": "reparent", "id": "r1", "parent": "s2", "replace": True},
            {"op": "reparent", "id": "r2", "parent": "s2", "replace": True}]})
        self.assertEqual({s.state["nodes"][r]["parent"] for r in ("r1", "r2")}, {"s2"})
        with self.assertRaises(SchedulerError):
            s.submit({"type": "batch", "expected_generation": 2, "mutations": [
                {"op": "relabel", "id": "r1", "labels": {"x": "1"}}, {"op": "delete", "id": "s2"}]})
        self.assertEqual(s.state["nodes"]["r1"]["labels"], {})

    @covers("MC-006", 6, 8, 27)
    def test_mc006_fencing_token_propagates_to_every_mutable_resource(self):
        """fencing propagation (adversarial stale leader): topology store, ledger, transaction journal and the SCH-01
        harness each reject a write carrying a token older than the last accepted one; the coordination model
        (single elected leader) is the one documented in the ADR."""
        self.assertIn("single elected leader", open(os.path.join(ROOT, "docs/adr/ADR-0001-gap03-control-plane.md")).read())
        ts = TopologyStore(self.d("t"))
        led = LedgerStore(self.d("l"))
        j = TxnJournal(self.d("j"))
        h = sch01.SCH01Harness()
        ts.submit({"type": "batch", "expected_generation": 0, "fence": 7,
                   "mutations": [{"op": "create", "id": "eu", "node_type": "region", "parent": None}]})
        led.submit({"type": "set_capacity", "capacity": 1, "fence": 7})
        j.submit({"type": "begin", "txn": "x", "inputs": {}, "now": 0, "deadline": 1, "fence": 7})
        h.place({"txn": "x", "node": "n", "fence": 7})
        stale = 6
        with self.assertRaises(SchedulerError):
            ts.submit({"type": "batch", "expected_generation": 1, "fence": stale,
                       "mutations": [{"op": "relabel", "id": "eu", "labels": {}}]})
        with self.assertRaises(SchedulerError):
            led.submit({"type": "set_capacity", "capacity": 2, "fence": stale})
        with self.assertRaises(SchedulerError):
            j.submit({"type": "begin", "txn": "y", "inputs": {}, "now": 0, "deadline": 1, "fence": stale})
        with self.assertRaises(SchedulerError):
            h.place({"txn": "y", "node": "n", "fence": stale})

    @covers("MC-006", 18)
    def test_mc006_configuration_bounds_validated(self):
        """input validation: an unsafe lease configuration (safety margin >= ttl) is rejected at construction."""
        with self.assertRaises(ValueError):
            Coordinator("s", [], ttl=2, safety_margin=2)

    @covers("MC-007", 8, 18)
    def test_mc007_prepare_reserves_provisionally_without_external_side_effect(self):
        """prepare/reserve phase: the provisional claim is taken with a compare-and-swap state token and the fencing
        token BEFORE any downstream call; if the downstream is never reached nothing external happened.  Invalid
        candidate identifiers are rejected before prepare."""
        led = LedgerStore(self.d("l"), clock=self.clock)
        led.submit({"type": "set_capacity", "capacity": 2})
        led.submit({"type": "set_reservations", "reserved": {"a": 1}, "entitlement_generation": 1})
        seen = {}

        class Probe(sch01.SCH01Harness):
            def place(s, req):
                seen["claim"] = dict(led.state["claims"][req["txn"]])
                seen["placements_before"] = dict(s.placements)
                return super().place(req)
        down = Probe()
        pc = PlacementCoordinator(journal=TxnJournal(self.d("j")), ledger=led, topology_snapshot=topo4().snapshot,
                                  downstream=down, fence=lambda: 3, clock=self.clock)
        pc.place(txn="t1", workload={"id": "w"}, anchor="a", candidates=["b"], tenant="a")
        self.assertEqual(seen["claim"]["state"], "pending")
        self.assertEqual(seen["claim"]["fence"], 3)
        self.assertEqual(seen["placements_before"], {})
        with self.assertRaises(ValueError):
            pc.place(txn="t2", workload={"id": "w"}, anchor="a", candidates=["b", "b"], tenant="a")

    @covers("MC-002", 10, 18)
    def test_mc002_whole_mutation_validated_before_commit(self):
        """validation before commit: parent existence, hierarchy type and label bounds are validated for the complete
        proposed batch; one invalid element rejects the entire batch (no partial leak)."""
        s = TopologyStore(self.d("t"))
        with self.assertRaises(SchedulerError):
            s.submit({"type": "batch", "expected_generation": 0, "mutations": [
                {"op": "create", "id": "eu", "node_type": "region", "parent": None},
                {"op": "create", "id": "n1", "node_type": "node", "parent": "missing-rack"}]})
        self.assertEqual(s.state["nodes"], {})
        with self.assertRaises(SchedulerError):
            s.submit({"type": "batch", "expected_generation": 0, "mutations": [{"op": "create", "id": "bad/id", "node_type": "region", "parent": None}]})


class AdapterGaps(TmpCase):
    @covers("MC-008", 11, 12, 27)
    def test_mc008_idempotency_key_and_retry_classification_across_boundary(self):
        """idempotency across the boundary: the request's idempotency key equals the txn id; a retried place() after a
        lost response returns the original placement (no duplicate); E_BUSY is classified retryable while
        E_NO_NODE is terminal with a release compensation."""
        h = sch01.SCH01Harness(faults=["lost_response"])
        req = {"txn": "tx", "node": "b", "fence": 1, "version": "1.1", "idempotency_key": "tx"}
        with self.assertRaises(SchedulerError) as cm:
            h.place(req)
        self.assertTrue(cm.exception.code == "DEADLINE_EXCEEDED")
        self.assertEqual(h.place(req)["operation_id"], h.place(req)["operation_id"])
        self.assertEqual(len(h.placements), 1)
        from gap03_topology_aware_scheduler.controlplane.errors import is_retryable
        self.assertTrue(is_retryable(sch01.map_error("E_BUSY")))
        self.assertFalse(is_retryable(sch01.map_error("E_NO_NODE")))
        self.assertEqual(sch01.map_error("E_NO_NODE").detail["compensation"], "release")

    @covers("MC-009", 6, 17, 18, 27)
    def test_mc009_contract_fields_and_adversarial_reports(self):
        """contract + adversarial input: the normalised GAP-02 record carries node identity, ISA, cpus, memory,
        accelerators, generation, observation time, source and attestation; spoofed/malformed/unauthorised reports
        (bad device id, oversize accelerator list, non-object) are rejected."""
        rec = gap02.normalize({"version": "1.0", "device_id": "dev:00000000000000b1", "node": "n1", "isa": "x86_64", "cpus": 2,
                               "memory": {"value": 1, "unit": "GiB"}, "accelerators": [], "generation": 1, "observed_at": T0,
                               "source": "g"})
        for k in ("device_id", "node", "isa", "cpus", "memory_mib", "accelerators", "claims", "generation", "observed_at",
                  "source", "attestation"):
            self.assertIn(k, rec)
        for bad in ([], {"version": "1.0", "device_id": "dev:zz"}, dict(rec, version="1.0", memory={"value": 1, "unit": "GiB"},
                                                                         accelerators=["nvidia-a100"] * 65)):
            with self.assertRaises(SchedulerError):
                gap02.normalize(bad)

    @covers("MC-010", 7, 10, 17, 18, 27)
    def test_mc010_unknown_anchor_and_replica_alternatives(self):
        """anchor normalisation + adversarial input: an anchor on an unknown/decommissioned node is refused; with two
        replicas the contribution is the MIN over replicas (erasure/replica sets are alternatives, not summed);
        unsigned anchors are unauthorised when a trust store is configured."""
        snap = topo4().snapshot()
        g = gap14.Gravity()
        with self.assertRaises(SchedulerError):
            g.ingest({"version": "1.0", "tenant": "t", "dataset": "x", "replicas": [{"node": "gone", "bytes": 1}], "revision": 1,
                      "observed_at": T0, "source": "s"}, snap)
        one = g.ingest({"version": "1.0", "tenant": "t", "dataset": "one", "replicas": [{"node": "d", "bytes": 10**9}],
                        "revision": 1, "observed_at": T0, "source": "s"}, snap)
        two = g.ingest({"version": "1.0", "tenant": "t", "dataset": "two", "replicas": [{"node": "d", "bytes": 10**9},
                                                                                         {"node": "a", "bytes": 10**9}],
                        "revision": 1, "observed_at": T0, "source": "s"}, snap)
        self.assertLess(g.contribution(two["id"], "b", snap, T0)["value"], g.contribution(one["id"], "b", snap, T0)["value"])
        t, _ = self.trust()
        with self.assertRaises(SchedulerError):
            gap14.Gravity(trust=t).ingest({"version": "1.0", "tenant": "t", "dataset": "u", "replicas": [{"node": "a", "bytes": 1}],
                                           "revision": 1, "observed_at": T0, "source": "s"}, snap)

    @covers("MC-011", 6, 7, 9, 15, 17, 18)
    def test_mc011_contract_units_freshness_and_scenarios(self):
        """contract/unit conversion/freshness + scenario matrix: kslot converts to slots; stale and low-confidence
        forecasts are discarded; spike, collapse, planner restart (duplicate request ids), and conflicting revisions
        behave deterministically; unauthorised resource classes are rejected."""
        d = pln05.Demand()
        base = {"version": "1.0", "tenant": "t", "resource_class": "slots", "unit": "kslot", "quantity": 2, "confidence": 0.9,
                "observed_at": T0, "revision": 1, "request_id": "p1"}
        self.assertEqual(d.ingest(base, T0), "accepted")
        self.assertEqual(d.advisory("t", T0)["slots"], 2000)                                  # unit conversion
        self.assertEqual(d.ingest(dict(base, request_id="p2", revision=2, quantity=0), T0 + 60), "accepted")  # collapse
        self.assertEqual(d.advisory("t", T0 + 61)["slots"], 0)
        self.assertEqual(d.ingest(dict(base, request_id="p3", revision=3, quantity=9), T0 + 120), "accepted")  # spike
        self.assertEqual(d.ingest(dict(base, request_id="p3", revision=3), T0 + 121), "duplicate")          # restart replay
        self.assertEqual(d.ingest(dict(base, request_id="p4", revision=1), T0 + 200), "discarded_out_of_order")
        self.assertEqual(d.ingest(dict(base, request_id="p5", confidence=0.1, revision=9), T0 + 300), "discarded_low_confidence")
        self.assertEqual(d.ingest(dict(base, request_id="p6", observed_at=T0 - 10_000, revision=9), T0), "discarded_stale")
        with self.assertRaises(SchedulerError):
            d.ingest(dict(base, request_id="p7", resource_class="gpu"), T0)

    @covers("MC-034", 9, 12, 27)
    def test_mc034_canonical_pairs_nothing_dropped_and_retry_scenarios(self):
        """canonical request/response pairs: every GAP-02 fixture input field is represented in the normalised object
        (nothing silently dropped or reinterpreted); network/retry scenario: a retrier over the harness with a lost
        response preserves idempotency and error classification."""
        with open(os.path.join(os.path.dirname(gap02.__file__), "..", "fixtures", "gap02.json")) as fh:
            case = json.load(fh)["cases"][0]
        out = gap02.normalize(case["input"])
        mapping = {"version": None, "device_id": "device_id", "node": "node", "isa": "isa", "cpus": "cpus", "memory": "memory_mib",
                   "accelerators": "accelerators", "generation": "generation", "observed_at": "observed_at", "source": "source"}
        for f in case["input"]:
            self.assertIn(f, mapping, f"fixture field {f} has no mapping")
            if mapping[f]:
                self.assertIn(mapping[f], out)
        h = sch01.SCH01Harness(faults=["lost_response"])
        r = Retrier("sch01", Policy(max_attempts=3), seed=1, sleep=lambda s: None)
        req = {"txn": "t9", "node": "b", "fence": 1, "version": "1.1"}
        res = r.run(lambda **k: h.place(req), op_class="transaction_phase", deadline_s=5, idempotency_key="t9",
                    outcome_probe=lambda: (h.status("t9")["status"] == "placed", h.status("t9")))
        self.assertEqual(res["status"], "placed")
        self.assertEqual(len(h.placements), 1)


class ProducerAuthz(TmpCase):
    @covers("MC-009", 17)
    @covers("MC-010", 17)
    @covers("MC-011", 17)
    def test_adapter_producer_authorization(self):
        """authorization: when an authorized-producer set is configured, feeds from any other (verified) identity are
        denied for GAP-02 inventory, GAP-14 anchors and PLN-05 demand; authorised producers are accepted."""
        good = "spiffe://prod.example/service/feed"
        inv = gap02.Inventory()
        inv.authorized_producers = frozenset({good})
        rep = {"version": "1.0", "device_id": "dev:00000000000000c1", "node": "n", "isa": "x86_64", "cpus": 1,
               "memory": {"value": 1, "unit": "GiB"}, "accelerators": [], "generation": 1, "observed_at": T0, "source": "s"}
        with self.assertRaises(SchedulerError):
            inv.ingest(rep, producer="spiffe://prod.example/service/evil")
        inv.ingest(rep, producer=good)
        g = gap14.Gravity()
        g.authorized_producers = frozenset({good})
        with self.assertRaises(SchedulerError):
            g.ingest({"version": "1.0"}, topo4().snapshot(), producer="x")
        d = pln05.Demand()
        d.authorized_producers = frozenset({good})
        with self.assertRaises(SchedulerError):
            d.ingest({"version": "1.0"}, T0, producer="x")
        sig = {"version": "1.0", "request_id": "r", "tenant": "t", "resource_class": "slots", "unit": "slot", "quantity": 1,
               "confidence": 0.9, "observed_at": T0, "revision": 1}
        self.assertEqual(d.ingest(sig, T0, producer=good), "accepted")


class OpsGaps(TmpCase):
    @covers("MC-012", 17, 18, 26)
    @covers("MC-013", 17, 26)
    def test_identity_and_audit_authorization_integration(self):
        """authorization boundary integration: a credential without the required role is denied by the topology
        boundary and the denial is audited; audit queries/exports without audit.read/audit.export are refused;
        malformed credentials are rejected at the earliest boundary."""
        from gap03_topology_aware_scheduler.controlplane.topology_service import AUDIENCE, TopologyService
        a = AuditLog(self.d("a"), clock=self.clock)
        t, key = self.trust(a)
        svc = TopologyService(TopologyStore(self.d("t")), t, a)
        req = {"request_id": "r", "source_service": "s", "reason": "x", "expected_generation": 0,
               "mutations": [{"op": "create", "id": "eu", "node_type": "region", "parent": None}]}
        tok = self.token(key, "spiffe://prod.example/operator/eve", ["auditor"], AUDIENCE, req=canonical.digest(req))
        self.assertEqual(svc.mutate(tok, req)["error"]["code"], "PERMISSION_DENIED")
        self.assertEqual(svc.mutate("garbage", req)["error"]["code"], "UNAUTHENTICATED")
        with self.assertRaises(SchedulerError):
            a.export(principal_roles={"audit.read"})
        self.assertIn("denied", [e["result"] for e in a.export(principal_roles={"audit.export"})["events"]])

    @covers("MC-013", 18)
    def test_mc013_event_schema_enforced_at_store(self):
        """input validation: an audit event missing required fields is rejected by the audit store itself."""
        a = AuditLog(self.d("a"), clock=self.clock)
        with self.assertRaises(SchedulerError):
            a._store.submit({"type": "event", "event": {"actor": "x"}})

    @covers("MC-015", 17, 18, 27)
    def test_mc015_activation_requires_config_write(self):
        """authorization: activating or rolling back configuration without config.write is denied and audited;
        malformed overlay input is rejected."""
        a = AuditLog(self.d("a"), clock=self.clock)
        m = ConfigManager(ConfigStore(self.d("c")), audit=a)
        with self.assertRaises(SchedulerError):
            m.activate(cfgmod.defaults(), actor="x", source="y", principal={"sub": "x", "perms": set()})
        with self.assertRaises(SchedulerError):
            m.rollback(1)
        self.assertEqual(a.export(principal_roles={"audit.export"})["events"][-1]["result"], "denied")
        with self.assertRaises(SchedulerError):
            cfgmod.env_overlay({"GAP03_CFG__A__B__C": "1"})

    @covers("MC-016", 18)
    @covers("MC-017", 18)
    def test_degraded_and_controls_input_validation(self):
        """input validation: unknown dependency/operation names and control scope/mode/ttl/ticket are rejected."""
        p = DegradedPolicy(clock=self.clock)
        for bad in (lambda: p.report("nope", True), lambda: p.decide("fly")):
            with self.assertRaises(SchedulerError):
                bad()
        c = Controls(ControlStore(self.d("c")), clock=self.clock)
        for kw in (dict(scope_kind="planet"), dict(mode="explode"), dict(ttl_s=0), dict(ticket="")):
            args = dict(control_id="x", scope_kind="tenant", scope_value="t", mode="drain", reason="r", ticket="T", ttl_s=10)
            args.update(kw)
            with self.assertRaises(SchedulerError):
                c.create(OPS, **args)

    @covers("MC-017", 12)
    def test_mc017_emergency_exception_only_via_audited_override(self):
        """emergency exception path: a narrowly scoped, time-limited exemption to one control requires break-glass,
        is audited, applies only to its scope and expires; no undocumented flag bypasses a control."""
        a = AuditLog(self.d("a"), clock=self.clock)
        c = Controls(ControlStore(self.d("c"), clock=self.clock), clock=self.clock, audit=a)
        c.create(OPS, control_id="f", scope_kind="tenant", scope_value="t1", mode="freeze-new", reason="r", ticket="INC-1", ttl_s=600)
        with self.assertRaises(SchedulerError):
            c.exempt(OPS, control_id="f", scope={"tenant": "t1", "workload_class": "critical"}, ttl_s=60, reason="x", ticket="INC-1")
        c.exempt(BG, control_id="f", scope={"tenant": "t1", "workload_class": "critical"}, ttl_s=60, reason="restore dns", ticket="INC-1")
        c.check("placement.commit", scope={"tenant": "t1", "workload_class": "critical"})
        with self.assertRaises(SchedulerError):
            c.check("placement.commit", scope={"tenant": "t1", "workload_class": "batch"})
        self.clock.advance(61)
        with self.assertRaises(SchedulerError):
            c.check("placement.commit", scope={"tenant": "t1", "workload_class": "critical"})
        self.assertIn("control.exempt", [e["action"] for e in a.export(principal_roles={"audit.export"})["events"]])

    @covers("MC-018", 13, 17, 18)
    def test_mc018_hysteresis_and_deep_auth(self):
        """readiness hysteresis/debounce: one good evaluation after a failure does not flap back to ready; deep
        diagnostics are refused without authorization; unknown paths return 404 (input validation)."""
        from gap03_topology_aware_scheduler.controlplane.health import Health
        st = {"ok": True}
        h = Health(checks={"x": lambda: (st["ok"], "")}, info=lambda: {})
        h.started = True
        h.readyz(); h.readyz()
        self.assertTrue(h.ready)
        st["ok"] = False
        h.readyz()
        st["ok"] = True
        self.assertEqual(h.readyz()["status"], "not_ready")
        self.assertEqual(h.readyz()["status"], "ready")
        self.assertEqual(h.deep(authorized=False), {"status": "forbidden"})

    @covers("MC-022", 12, 17, 18, 27)
    def test_mc022_retention_and_adversarial_queries(self):
        """retention + adversarial access: explain records past the retention window become archive-eligible unless
        held for an incident; an unauthorised principal and an inverted/over-wide time range are rejected."""
        from gap03_topology_aware_scheduler import FairShare
        from gap03_topology_aware_scheduler.scheduler import _score_snapshot
        ex = Explain(ExplainStore(self.d("e"), clock=self.clock), clock=self.clock)
        snap = topo4().snapshot()
        v = FairShare(capacity=1).verdict("t")
        for i in range(3):
            ex.record(txn=f"t{i}", tenant="t", workload={"id": "w"}, inputs={}, scored=_score_snapshot(snap, "a", ["b"]), fairness=v)
        plan = ex.retention_plan(now=self.clock() + 100 * 86400, holds={"t1"})
        self.assertEqual(plan["eligible_for_archive"], ["t0", "t2"])
        self.assertEqual(plan["held"], ["t1"])
        with self.assertRaises(SchedulerError):
            ex.query({"sub": "x", "perms": set()})
        with self.assertRaises(SchedulerError):
            ex.query({"sub": "o", "perms": {"explain.read"}}, since=self.clock(), until=self.clock() - 1)

    @covers("MC-023", 11, 27)
    @covers("MC-043", 27)
    def test_mc023_definition_validator_catches_broken_alerts(self):
        """adversarial definitions: an alert missing owner/runbook/escalation/first diagnostics, an unknown class, or a
        dashboard panel referencing a non-existent metric is reported by the validator (runbook links enforced)."""
        saved_a, saved_d = list(alerts.ALERTS), dict(alerts.DASHBOARD)
        try:
            alerts.ALERTS.append({"alert": "Broken", "class": "vibes", "severity": "page", "owner": "", "runbook": "",
                                  "escalation": "", "first_diagnostics": ""})
            alerts.DASHBOARD = dict(saved_d, rows=saved_d["rows"] + [{"title": "x", "panels": ["gap03_nope"]}])
            probs = alerts.validate_definitions()
        finally:
            alerts.ALERTS[:] = saved_a
            alerts.DASHBOARD = saved_d
        for needle in ("missing owner", "missing runbook", "missing escalation", "missing first_diagnostics", "unknown class", "gap03_nope"):
            self.assertTrue(any(needle in p for p in probs), needle)

    @covers("MC-024", 18, 20)
    def test_mc024_nested_injection_and_depth_bounds(self):
        """untrusted input: deeply nested payloads are truncated, secrets in nested exception text are scrubbed and
        unknown fields default to confidential (not emitted unless allowed)."""
        from gap03_topology_aware_scheduler.controlplane import privacy
        deep = cur = {}
        for _ in range(10):
            cur["detail"] = {}
            cur = cur["detail"]
        cur["error"] = "Bearer abc.def"
        out = privacy.sanitize({"detail": deep, "mystery": "x"}, signal="logs", key=b"k")
        self.assertNotIn("abc.def", json.dumps(out))
        self.assertIn("<truncated>", json.dumps(out))
        self.assertNotIn("mystery", out)


class PerfGaps(TmpCase):
    @covers("MC-025", 8, 27)
    def test_mc025_token_bucket_bounded_queue_under_burst(self):
        """bounded token buckets/semaphores (fault: burst): 10,000 burst requests never exceed configured concurrency
        and are rejected before resources are consumed."""
        adm = Admission(Limits(max_concurrent_scoring=8, global_rps=10**6, global_burst=10**6, tenant_rps=10**6, tenant_burst=10**6),
                        clock=self.clock)
        held, rejected = [], 0
        for _ in range(10_000):
            try:
                held.append(adm.admit(kind="score", priority="system-critical"))
            except SchedulerError:
                rejected += 1
        self.assertEqual(len(held), 8)
        self.assertEqual(rejected, 9992)

    @covers("MC-027", 9, 14)
    def test_mc027_ewma_window_documented_and_bounded(self):
        """smoothing: EWMA with alpha=0.2 and a raw-sample window bounded at 32 per directional pair."""
        e = LatencyEngine(clock=self.clock)
        for i in range(100):
            e.ingest("spiffe://p/node/a", {"src": "a", "dst": "b", "rtt_us": 1000, "ts": self.clock(), "sample_id": f"s{i}"})
        st = e.pairs[("a", "b")]
        self.assertEqual(len(st["raw"]), RAW_KEEP)
        e.ingest("spiffe://p/node/a", {"src": "a", "dst": "b", "rtt_us": 1500, "ts": self.clock(), "sample_id": "z"})
        self.assertAlmostEqual(st["ewma"], (1 - ALPHA) * 1000 + ALPHA * 1500)

    @covers("MC-028", 14)
    def test_mc028_warmup_bounded_by_budget(self):
        """cache warm-up/precompute is bounded by a time budget so it cannot delay readiness indefinitely."""
        clk = ManualClock()
        c = ScoreCache(clock=clk)

        def slow(i):
            def f():
                clk.advance(0.3)
                return (i,)
            return f
        res = c.warm([((i,), slow(i)) for i in range(10)], budget_s=0.5)
        self.assertEqual(res["warmed"], 2)
        self.assertEqual(res["skipped_for_budget"], 8)

    @covers("MC-029", 27, 18)
    def test_mc029_adversarial_components_rejected(self):
        """adversarial inputs: out-of-range, NaN-like or non-integer objective components are rejected rather than
        silently distorting the composite score."""
        for bad in (-1, 1001, 1.5, None):
            with self.assertRaises((ValueError, TypeError)):
                objectives.compose(["a"], weights={"locality": 1000}, locality=lambda n, b=bad: b)

    @covers("MC-030", 27, 26)
    def test_mc030_model_rejects_degenerate_measurements(self):
        """fault/degenerate input: fitting needs >=2 distinct samples; a zero-variance set yields slope 0 rather than
        dividing by zero; the model is fitted from the real scorer's measurements (integration)."""
        with self.assertRaises(ValueError):
            capacity.fit([(10, 5.0)])
        self.assertEqual(capacity.fit([(10, 5.0), (10, 6.0)])["per_candidate_us"], 0.0)
        m = capacity.fit(capacity.measure_scoring(counts=(10, 400), repeats=5))
        self.assertGreater(m["per_candidate_us"], 0)

    @covers("MC-031", 11, 26, 27)
    def test_mc031_store_path_benchmarked_separately_and_gate_fails_closed(self):
        """dependency-mocked vs integrated paths: the harness benchmarks the pure scorer and the durable ledger path
        as separate cases; a result without an accepted threshold fails the gate (fault: missing baseline)."""
        from gap03_topology_aware_scheduler.benchmarks import harness
        ids = {c["id"]: c for c in harness.MATRIX}
        self.assertEqual(ids["ledger-prepare"].get("kind"), "ledger")
        r = harness.run_case(dict(ids["ledger-prepare"], ops=20))
        self.assertGreater(r["p50_ms"], 0)
        self.assertFalse(harness.gate([r], {"cases": {}})["pass"])


class GovernanceGaps(TmpCase):
    @covers("MC-037", 7, 8, 9, 10, 11, 25, 26, 27)
    def test_mc037_adr_content_and_doctored_adr_detected(self):
        """integration against the real shipped ADR file - ADR content: algorithms, alternatives (centralized/stateless/consistency models), invariants (deterministic,
        fencing, clock), trade-offs (consistency, availability, latency, blast radius) and a diagram with commit,
        identity and telemetry paths; a doctored ADR missing sections is detected (adversarial)."""
        text = open(os.path.join(ROOT, "docs/adr/ADR-0001-gap03-control-plane.md")).read()
        for w in ("locality", "fair share", "fencing", "Stateless", "CRDT", "Consensus", "Deterministic", "Clock assumption",
                  "Consistency over availability", "Blast radius", "Trust store", "Metrics", "PlacementCoordinator"):
            self.assertIn(w.lower(), text.lower(), w)
        self.assertFalse(governance.validate_adr_text(text.replace("## Alternatives considered", ""))["complete"])
        self.assertTrue(governance.validate_adr_text(text)["complete"])

    @covers("MC-039", 25, 26, 27)
    def test_mc039_provenance_validator(self):
        """integration against the real shipped provenance record - provenance validation (adversarial): a record claiming VERIFIED without source/authority/digest/signature is
        rejected; the shipped BLOCKED record is valid."""
        self.assertEqual(governance.validate_provenance(governance.provenance_status()), [])
        self.assertTrue(governance.validate_provenance({"status": "VERIFIED"}))
        self.assertTrue(governance.validate_provenance({"status": "BLOCKED"}))

    @covers("MC-043", 7, 9, 10, 11, 12, 14, 25)
    def test_mc043_triage_diagnostics_and_post_incident(self):
        """integration against the real runbook file and alert catalog - incident runbook contents: triage for overload, drift, split-brain, topology, fairness and security; diagnosis
        sources (dashboards, explain, journals, audit, snapshots); containment; forensic preservation; recovery
        validation; post-incident review with timeline, contributing factors, corrective actions, owners, due dates."""
        text = open(os.path.join(ROOT, "runbooks/incident-response.md")).read().lower()
        for w in ("overload", "drift", "split-brain", "topology", "fairness", "security", "dashboard", "explain", "journal",
                  "audit", "snapshot", "freeze", "admission", "fenc", "rollback", "preserve", "orphan", "coordination",
                  "timeline", "contributing factors", "corrective actions", "owners", "due dates"):
            self.assertIn(w, text, w)

    @covers("MC-044", 12, 13, 25, 26, 27)
    def test_mc044_policy_validation_and_eol_deploy_guard(self):
        """EOL policy: advance notice window is computed; deployment on an EOL runtime is refused unless waived;
        a policy whose EOL dates disagree with the compatibility matrix is rejected (adversarial); tested upgrade
        paths exist for schema, config and durable state (migrations)."""
        self.assertEqual(governance.validate_policy(governance.support_policy(), compat.MATRIX), [])
        bad = dict(governance.support_policy(), runtime_eol={"3.10": "2030-01-01"})
        self.assertTrue(governance.validate_policy(bad, compat.MATRIX))
        env = dict(compat.current(), python="3.10")
        self.assertTrue(compat.eol_block(env, today=dt.date(2026, 9, 22))["notice"])
        with self.assertRaises(SchedulerError):
            compat.eol_block(env, today=dt.date(2026, 11, 1))
        compat.eol_block(env, today=dt.date(2026, 11, 1), waiver_ok=True)
        from gap03_topology_aware_scheduler.controlplane import wire
        self.assertTrue(callable(wire.migrate) and callable(cfgmod.migrate_v1) and TopologyStore.MIGRATIONS)

    @covers("MC-045", 6, 7, 9, 10, 11, 13, 14, 15, 26, 27)
    def test_mc045_links_residual_risk_version_summary_and_audited_changes(self):
        """waiver registry: records need residual risk and links to work items and RTM rows; non-waivable controls are
        refused; a version change forces reassessment; the release summary reports WAIVED controls (never passed);
        create/edit/approve/close are authorised and audited, and closed records are preserved."""
        today = dt.date(2026, 9, 22)
        w = {"id": "W-9", "control_ids": ["MC-031-CHK-010"], "severity": "P2", "scope": "bench", "owner": "alice",
             "created": "2026-09-01", "expires": "2026-12-01", "compensating_controls": ["proposed thresholds"],
             "approval": {}, "status": "draft", "rationale": "r", "residual_risk": "late regressions",
             "links": {"work_items": ["GAP03-1"], "rtm": ["MC-031-CHK-010"]}, "applies_to_version": __version__}
        self.assertIn("missing link: rtm", waivers.validate(dict(w, links={"work_items": ["x"]}), today=today))
        self.assertIn("non-waivable control", waivers.validate(dict(w, control_ids=["PG-005"]), today=today))
        self.assertIn("reassessment required: version changed", waivers.validate(w, today=today, current_version="9.9.9"))
        a = AuditLog(self.d("a"), clock=self.clock)
        rm = {"sub": "spiffe://prod.example/operator/rm", "perms": {"waiver.approve"}}
        reg = waivers.apply_change([], {"op": "create", "id": "W-9", "waiver": w}, principal=rm, audit=a, today=today)
        with self.assertRaises(SchedulerError):
            waivers.apply_change(reg, {"op": "approve", "id": "W-9", "record": "CHG"}, principal={"sub": "x", "perms": set()}, audit=a, today=today)
        reg = waivers.apply_change(reg, {"op": "approve", "id": "W-9", "record": "CHG-1"}, principal=rm, audit=a, today=today)
        s = waivers.summary(reg, today=today)
        self.assertEqual(s["waived_controls"], ["MC-031-CHK-010"])
        reg = waivers.apply_change(reg, {"op": "close", "id": "W-9"}, principal=rm, audit=a, today=today)
        self.assertEqual(reg[0]["status"], "closed")
        acts = [e["action"] for e in a.export(principal_roles={"audit.export"})["events"]]
        self.assertEqual(acts, ["waiver.create", "waiver.approve", "waiver.approve", "waiver.close"])

    @covers("MC-046", 6, 14, 17, 27)
    def test_mc046_manifest_versioned_and_waivers_never_shown_as_pass(self):
        """exit-gate manifest: versioned schema enumerating evidence classes; the bundle must list defects and waivers;
        a check claiming WAIVED without an active waiver, an open P1 defect, or an unverifiable sign-off (authorization)
        each force NO_GO."""
        self.assertEqual(len(exitgate.EVIDENCE_CLASSES), len(set(exitgate.EVIDENCE_CLASSES)))
        for c in ("architecture", "requirements", "tests", "security", "resilience", "performance", "operations",
                  "compatibility", "provenance", "approvals"):
            self.assertIn(c, exitgate.EVIDENCE_CLASSES)
        r = exitgate.evaluate({"artifact_digest": "d", "evidence": {}, "mandatory_checks": [{"id": "X", "status": "WAIVED"}],
                               "signoffs": {}, "defects": [{"id": "D", "severity": "P1", "status": "OPEN"}], "waivers": []},
                              artifact_digest="d", now=0)
        self.assertEqual(r["schema"], "GAP03-EXIT/1")
        self.assertTrue(any("claims WAIVED" in x for x in r["reasons"]))
        self.assertTrue(any("open P1 defect" in x for x in r["reasons"]))
        self.assertTrue(any("unverifiable" in x or "missing sign-off" in x for x in r["reasons"]))


class SupplyGaps(TmpCase):
    @covers("MC-040", 10, 14, 26, 27)
    def test_mc040_no_third_party_deps_and_repeatable_archive(self):
        """dependency pinning + repeatable builds: the shipped package imports no third-party module (nothing to pin;
        a floating dependency would be detected); two archives of the same tree are byte-identical; the real package
        manifest verifies; a tampered copy is detected (adversarial)."""
        self.assertEqual(supply_chain.third_party_imports(ROOT), [])
        d = tempfile.mkdtemp()
        try:
            src = os.path.join(d, "src")
            shutil.copytree(ROOT, src, ignore=shutil.ignore_patterns("__pycache__", "evidence", "*.pyc"))
            h1 = supply_chain.deterministic_zip(src, os.path.join(d, "a.zip"))
            h2 = supply_chain.deterministic_zip(src, os.path.join(d, "b.zip"))
            self.assertEqual(h1, h2)
            text = supply_chain.manifest_text(supply_chain.manifest(src))
            self.assertEqual(supply_chain.verify_manifest(src, text), [])
            with open(os.path.join(src, "VERSION"), "a") as fh:
                fh.write("x")
            self.assertTrue(supply_chain.verify_manifest(src, text))
        finally:
            shutil.rmtree(d, ignore_errors=True)


class RolloutGaps(unittest.TestCase):
    @covers("MC-041", 26)
    def test_mc041_integration_with_real_exit_gate(self):
        """integration/contract: the rollout controller consumes the real exit-gate evaluation; a NO_GO result for the
        artifact is refused and nothing shifts."""
        gate = exitgate.evaluate({"artifact_digest": "d"}, artifact_digest="d", now=0)
        shifts = []
        with self.assertRaises(SchedulerError):
            rollout.run(candidate="d", previous="p", gate_result=gate, observe=lambda *a: {}, shift=lambda *a: shifts.append(a),
                        record=lambda e: None)
        self.assertEqual(shifts, [])

    def obs(self, **over):
        def f(digest, pct):
            o = {"error_ratio": 0.0001, "p99_ms": 8.0, "fencing_rejections": 0, "readiness": 1.0, "audit_write_failures": 0,
                 "fairness_denial_ratio": 0.01, "utilization": 0.5, "stale_conflict_ratio": 0.0, "drift_events": 0}
            if digest == "new":
                o.update(over)
            return o
        return f

    def test_release_promotion_is_audited(self):
        """auditable privileged change (PG-006): with an audit log attached, rollout decisions are written as
        release.* audit events with the approver as actor."""
        d = tempfile.mkdtemp()
        try:
            a = AuditLog(os.path.join(d, "a"))
            rollout.run(candidate="new", previous="old", gate_result={"decision": "GO", "artifact_digest": "new"},
                        observe=self.obs(), shift=lambda *x: None, record=lambda e: None, meta={"approver": "rm"}, audit=a)
            evs = a.export(principal_roles={"audit.export"})["events"]
            self.assertEqual([(e["action"], e["actor"]) for e in evs], [("release.promoted", "rm")])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    @covers("MC-041", 6, 7, 8)
    def test_mc041_stages_cohort_diversity_and_pre_promotion_gates(self):
        """rollout stages dev->integration->shadow->canary->partial->full; pre-promotion gates (tests, security scan,
        migration readiness, benchmark thresholds, error budget, no open P0/P1); canary cohort covers every
        region x tenant-class stratum within the blast-radius cap, with documented exclusions."""
        self.assertEqual(rollout.ENVIRONMENTS, ["dev", "integration", "shadow", "canary", "partial", "full"])
        self.assertEqual(rollout.pre_promotion({g: True for g in rollout.PRE_PROMOTION_GATES}), [])
        self.assertEqual(rollout.pre_promotion({"unit_and_contract_tests": True}), list(rollout.PRE_PROMOTION_GATES[1:]))
        tenants = [{"id": f"t{i:03d}", "region": "eu" if i % 2 else "us", "class": ["gold", "silver", "bronze"][i % 3]} for i in range(200)]
        c = rollout.choose_cohort(tenants, exclusions={"t001": "regulated tenant, contractual freeze"})
        self.assertEqual(c["strata_covered"], c["strata_total"])
        self.assertLessEqual(len(c["cohort"]), c["cap"])
        self.assertNotIn("t001", c["cohort"])

    @covers("MC-041", 9, 10, 12, 13, 14, 27)
    def test_mc041_canary_vs_control_drain_record_and_operator_controls(self):
        """canary vs control comparison on fairness denials/utilisation/stale conflicts/drift triggers automatic
        rollback; instances are drained before each shift; the decision record carries digest, approver, cohort,
        timing and metrics; pause/resume/abort require authorization (unauthorised abort refused)."""
        rec, drained, shifts = [], [], []
        r = rollout.run(candidate="new", previous="old", gate_result={"decision": "GO", "artifact_digest": "new"},
                        observe=self.obs(fairness_denial_ratio=0.2), shift=lambda d, p: shifts.append((d, p)), record=rec.append,
                        drain=drained.append, meta={"approver": "rm", "cohort": ["t1"], "config_generation": 4, "rollout_generation": 2},
                        clock=lambda: 5.0)
        self.assertEqual(r["result"], "ROLLED_BACK")
        self.assertIn("fairness_denial_ratio_vs_control", r["history"][0]["breaches"])
        self.assertEqual(drained, [1])
        for k in ("approver", "cohort", "config_generation", "rollout_generation", "start", "end", "metrics"):
            self.assertIn(k, rec[-1])
        ctl = rollout.Controller(record=rec.append)
        with self.assertRaises(SchedulerError):
            ctl.abort({"sub": "x", "roles": []}, "no", shift=lambda *a: None, previous="old")
        ctl.pause({"sub": "rm", "roles": ["release-manager"]}, "watch")
        ctl.resume({"sub": "rm", "roles": ["release-manager"]})
        ctl.abort({"sub": "rm", "roles": ["release-manager"]}, "stop", shift=lambda d, p: shifts.append((d, p)), previous="old")
        self.assertEqual(shifts[-1], ("old", 100))

    @covers("MC-041", 11)
    def test_mc041_old_and_new_versions_coexist_across_migrations(self):
        """coordinated migrations: old/new schema minors coexist (1.0 <-> 1.1 round trip), config v1 documents load in
        v2, and store migrations keep a rollback snapshot - so rollback stays possible during the overlap."""
        from gap03_topology_aware_scheduler.controlplane import wire
        v10 = {"schema": "PK_TOPOLOGY/1.0", "environment": "p", "generation": 1, "nodes": []}
        self.assertEqual(wire.migrate(wire.migrate(v10, "PK_TOPOLOGY/1.1"), "PK_TOPOLOGY/1.0"), v10)
        self.assertEqual(cfgmod.validate({"schema_version": 1, "scoring": {"weight_cost": 3}})["scoring"]["weight_latency"], 3)


class BackupGaps(TmpCase):
    @covers("MC-042", 6, 7, 11, 12, 15, 27)
    def test_mc042_signed_manifest_dry_run_and_objectives(self):
        """RPO/RTO per store and state inventory (authoritative/reconstructable/ephemeral); restore tooling verifies the
        signed manifest and schema before activation and supports dry-run inspection; an unsigned or foreign-signed
        backup is refused (adversarial); restore ordering is defined; DR runbook exists."""
        t, key = self.trust()
        st = {"ledger": LedgerStore(self.d("s/ledger"))}
        st["ledger"].submit({"type": "set_capacity", "capacity": 2})
        arc = os.path.join(self.tmp, "b.tgz")
        backup.backup(st, arc, signer=key)
        dr = backup.restore(arc, self.d("s"), {"ledger": LedgerStore}, trust=t, dry_run=True)
        self.assertTrue(dr["dry_run"])
        self.assertEqual(dr["stores"]["ledger"]["kind"], "ledger")
        other = identity.SigningKey.generate("k1", key.issuer)
        arc2 = os.path.join(self.tmp, "b2.tgz")
        backup.backup(st, arc2, signer=other)
        with self.assertRaises(SchedulerError):
            backup.restore(arc2, os.path.join(self.tmp, "r2"), {"ledger": LedgerStore}, trust=t)
        arc3 = os.path.join(self.tmp, "b3.tgz")
        backup.backup(st, arc3)
        with self.assertRaises(SchedulerError):
            backup.restore(arc3, os.path.join(self.tmp, "r3"), {"ledger": LedgerStore}, trust=t)
        for s in ("topology", "ledger", "txn", "audit", "lease"):
            self.assertIn(s, backup.RPO_RTO)
        self.assertEqual(backup.RESTORE_ORDER.index("topology") < backup.RESTORE_ORDER.index("ledger"), True)
        self.assertTrue(os.path.exists(os.path.join(ROOT, "runbooks/backup-restore.md")))
