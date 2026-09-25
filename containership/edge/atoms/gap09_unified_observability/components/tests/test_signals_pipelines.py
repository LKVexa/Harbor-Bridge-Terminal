"""Components 20-35 and 40: signal model, trace context, causal graph,
catalogue, adapters, pipelines, export, range query, policy, cardinality,
partition/reconnect."""
import json
import os
import unittest

from fixtures import make_stack, sample, signed, tmpdir
from gap09_unified_observability.components.adapters import (collect_host, from_dns, from_firecracker_metrics, from_flow,
                                                             from_wasm, microvm_lifecycle)
from gap09_unified_observability.components.controls import CircuitBreaker
from gap09_unified_observability.components.durable import WriteAheadBuffer
from gap09_unified_observability.components.errors import DependencyUnavailable, Malformed, QuotaExceeded, Unauthorized
from gap09_unified_observability.components.export import Exporter, FileSink, to_otlp_json
from gap09_unified_observability.components.ingest import reconcile
from gap09_unified_observability.components.pipelines import LogPipeline, MetricsPipeline, ProfilePipeline, TracePipeline
from gap09_unified_observability.components.policy import CardinalityGuard, PolicyEngine, TenantPolicy, find_secrets
from gap09_unified_observability.components.query_service import RangeStore
from gap09_unified_observability.components.signals import CausalGraph, Catalogue, Record, Resource, parse_traceparent

R = Resource("t1", "prod", "s1", "w1", "host", "node-1")
TP = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"


class TestModelAndContext(unittest.TestCase):
    def test_record_kinds_share_provenance(self):
        for k in ("metric", "log", "span", "profile", "event"):
            Record(k, "x", R, 1, {"value": 1} if k == "metric" else {})
        for bad in (dict(kind="blob"), dict(at=-1), dict(trace_id="XYZ"), dict(body={"value": float("nan")})):
            with self.assertRaises(Malformed):
                Record(**{"kind": "metric", "name": "x", "resource": R, "at": 1, **bad})
        with self.assertRaises(Malformed):
            Resource("t1", "prod", "s1", "w1", "mainframe")

    def test_w3c_traceparent(self):
        tc = parse_traceparent(TP, "congo=t61rcWkgMzE,rojo=00f067aa0ba902b7")
        self.assertEqual((tc.trace_id, tc.parent_id, tc.sampled, len(tc.tracestate)),
                         ("4bf92f3577b34da6a3ce929d0e0e4736", "00f067aa0ba902b7", True, 2))
        self.assertEqual(tc.traceparent(), TP)
        self.assertEqual(tc.child("b7ad6b7169203331").headers()["traceparent"],
                         "00-4bf92f3577b34da6a3ce929d0e0e4736-b7ad6b7169203331-01")
        for bad in (TP.upper(), "ff" + TP[2:], "00-" + "0" * 32 + TP[35:], TP[:-3] + "-0" + "0" * 15 + "-01",
                    TP + "-extra", "garbage", None, "x" * 10_000):
            self.assertIsNone(parse_traceparent(bad), bad)
        self.assertIsNotNone(parse_traceparent("01" + TP[2:] + "-future"))     # future version prefix rule
        self.assertEqual(parse_traceparent(TP, "bad key=1").tracestate, ())      # invalid tracestate dropped

    def test_causal_graph_tenant_safe(self):
        g = CausalGraph()
        g.add_node("pod-1", kind="workload", tenant="t1")
        g.add_node("rel-7", kind="release", tenant="t1")
        g.add_node("node-a", kind="node", tenant="*")
        g.add_node("pod-x", kind="workload", tenant="t2")
        g.link("pod-1", "deployed_by", "rel-7"); g.link("pod-1", "runs_on", "node-a")
        with self.assertRaises(Malformed):
            g.link("pod-1", "caused", "pod-x")
        self.assertEqual(len(g.context("pod-1", tenant="t1")), 2)
        self.assertEqual(g.context("pod-1", tenant="t2"), [])

    def test_catalogue_lifecycle_and_schema_shape(self):
        c = Catalogue()
        c.register("cpu.util", kind="gauge", unit="%", owner="obs", description="CPU", actor="t")
        with self.assertRaises(Malformed):
            c.register("cpu.util", kind="counter", unit="%", owner="obs", description="CPU", actor="t")
        with self.assertRaises(Malformed):
            c.register("Bad Name", kind="gauge", unit="%", owner="obs", description="x", actor="t")
        c.transition("cpu.util", "stable", actor="t")
        with self.assertRaises(Malformed):
            c.transition("cpu.util", "experimental", actor="t")
        self.assertTrue(c.accepts("cpu.util", "metric"))
        c.transition("cpu.util", "removed", actor="t")
        self.assertFalse(c.accepts("cpu.util", "metric"))
        self.assertEqual(c.document()["signals"], [])


class TestAdapters(unittest.TestCase):
    def test_wasm_microvm_host_network(self):
        r = from_wasm("comp-a", "i1", {"type": "log", "at": 5, "message": "hi", "traceparent": TP}, base=R)
        self.assertEqual((r.resource.boundary, r.trace_id), ("wasm", TP[3:35]))
        ms = from_firecracker_metrics("vm-1", "host-1", {"vcpu": {"exit_io_in": 3, "flag": True}, "api": "x"}, base=R, at=9)
        self.assertEqual([m.name for m in ms], ["microvm.vcpu.exit_io_in"])
        self.assertEqual(microvm_lifecycle("vm-1", "started", base=R, at=1).resource.boundary, "microvm")
        host = collect_host(base=R, at=1)
        self.assertIn("host.cpu.count", [h.name for h in host])
        owners = {"10.0.0.1": "t1", "10.0.0.2": "t2"}
        f = from_flow({"src": "10.0.0.1", "dst": "10.0.0.2", "proto": "tcp", "bytes": 10, "packets": 1, "at": 3},
                      base=R, salt=b"s", owner_of=owners)
        self.assertEqual(f.body["src"], "10.0.0.1")
        self.assertTrue(f.body["dst"].startswith("ip:"))            # foreign endpoint pseudonymised
        with self.assertRaises(Malformed):
            from_flow({"src": "10.0.0.2", "dst": "10.0.0.9", "proto": "tcp", "bytes": 1, "packets": 1, "at": 3},
                      base=R, salt=b"s", owner_of=owners)
        self.assertEqual(from_dns({"qname": "Example.COM.", "at": 1}, base=R).body["qname"], "example.com")


class TestPipelines(unittest.TestCase):
    def setUp(self):
        self.pol = PolicyEngine(TenantPolicy(retention_seconds=100))

    def test_logs_redact_multiline_encoding(self):
        lp = LogPipeline(self.pol)
        self.assertIsNone(lp.ingest_raw(b"Traceback:", resource=R, at=1, continuation=True))
        r = lp.ingest_raw(b"password=hunter22 \xff end", resource=R, at=2)
        self.assertIn("Traceback:", r.body["text"])
        self.assertIn("<redacted:password_assignment>", r.body["text"])
        self.assertNotIn("hunter22", r.body["text"])
        self.assertIn("�", r.body["text"])
        self.assertTrue(lp.ingest_raw(b"x" * 20000, resource=R, at=3).body["truncated"])

    def test_metrics_counter_reset_delta_histogram(self):
        m = MetricsPipeline()
        k = ("t1", "req")
        for at, v in ((1, 100), (2, 150), (3, 20), (4, 30)):
            last = m.counter(k, v, at)
        self.assertEqual((last, m.series(k).resets), (80.0, 1))
        with self.assertRaises(Malformed):
            m.counter(k, 40, 4)                                         # out of order
        m.counter(("t1", "d"), 5, 1, temporality="delta"); self.assertEqual(m.counter(("t1", "d"), 5, 2, temporality="delta"), 10)
        with self.assertRaises(Malformed):
            m.counter(("t1", "d"), 5, 3)                                 # temporality change
        for v in (1, 2, 3, 50, 500):
            m.histogram(("t1", "lat"), v, 1, buckets=(5, 100))
        self.assertEqual(m.series(("t1", "lat")).counts, [3, 1, 1])
        self.assertEqual(m.quantile(("t1", "lat"), 0.5), 5)
        self.assertEqual(MetricsPipeline.downsample([(0, 1), (5, 3), (10, 2)], 10, "max"), [(0, 3), (10, 2)])

    def test_traces_out_of_order_and_incomplete(self):
        tp = TracePipeline(self.pol, max_wait=10)
        tid = "a" * 32
        tp.add_span(trace_id=tid, span_id="2" * 16, parent_id="1" * 16, name="child", resource=R, start=2, end=3, arrived=0)
        self.assertEqual(tp.sweep(1), [])                                # parent missing, still waiting
        tp.add_span(trace_id=tid, span_id="1" * 16, parent_id=None, name="root", resource=R, start=1, end=5, arrived=2)
        out = tp.sweep(2)
        self.assertEqual((len(out), out[0]["incomplete"]), (1, False))
        tp.add_span(trace_id="b" * 32, span_id="3" * 16, parent_id="9" * 16, name="orphan", resource=R, start=1, end=2, arrived=0,
                    baggage="x" * 9000)
        out = tp.sweep(10)
        self.assertEqual((out[0]["incomplete"], out[0]["orphans"], out[0]["spans"][0]["baggage"]), (True, ["3" * 16], ""))

    def test_profiles_budget_privacy(self):
        pp = ProfilePipeline(tenant_budget_bytes=200)
        r = pp.ingest(resource=R, at=1, ptype="cpu", folded={"/home/alice/app/main.py;handler;token=abcdefghij": 3})
        self.assertEqual(list(r.body["folded"]), ["main.py;handler;<redacted>"])
        with self.assertRaises(QuotaExceeded):
            pp.ingest(resource=R, at=2, ptype="cpu", folded={"f" * 300: 1})


class TestPolicyExportQuery(unittest.TestCase):
    def test_retention_residency_sampling(self):
        pe = PolicyEngine(TenantPolicy(100), {"eu": TenantPolicy(50, residency="eu-west", export_allowed=True)})
        self.assertTrue(pe.expired("t1", 0, 100)); self.assertFalse(pe.expired("t1", 1, 100))
        self.assertTrue(pe.may_export("eu", destination_region="eu-west"))
        self.assertFalse(pe.may_export("eu", destination_region="us-east"))
        self.assertFalse(pe.may_export("t1", destination_region="eu-west"))

    def test_cardinality_guard(self):
        g = CardinalityGuard(max_values_per_label=2)
        g.apply("t1", "req", {"route": "a"}); g.apply("t1", "req", {"route": "b"})
        self.assertEqual(g.apply("t1", "req", {"route": "c"})["route"], "__overflow__")
        self.assertTrue(g.apply("t1", "req", {"user": "bearer abcdefghijklmnopqrstu"})["user"].startswith("<secret:"))
        with self.assertRaises(Malformed):
            g.apply("t1", "req", {f"l{i}": 1 for i in range(20)})
        self.assertEqual(find_secrets("nothing here"), [])

    def test_export_retry_and_breaker(self):
        class Flaky:
            def __init__(self, fails): self.fails, self.got = fails, []
            def send(self, p):
                if self.fails: self.fails -= 1; raise OSError()
                self.got.append(p)
        sleeps = []
        ex = Exporter(Flaky(2), breaker=CircuitBreaker("sink", threshold=10, cooldown=5), sleep=sleeps.append)
        self.assertEqual(ex.export({"a": 1}), 3)
        self.assertEqual(sleeps, [0.5, 1.0])
        ex2 = Exporter(Flaky(99), breaker=CircuitBreaker("sink", threshold=3, cooldown=5), max_attempts=3)
        with self.assertRaises(DependencyUnavailable):
            ex2.export({"a": 1})
        with self.assertRaises(DependencyUnavailable):
            ex2.export({"a": 1})                                          # breaker now open
        p = os.path.join(tmpdir(), "out.jsonl")
        otlp = to_otlp_json([Record("metric", "cpu", R, 2, {"value": 1.5}), Record("log", "l", R, 3, {"text": "x"})])
        FileSink(p).send(otlp)
        got = json.loads(open(p).read())
        self.assertEqual(got["resourceData"][0]["scopeMetrics"][0]["metrics"][0]["gauge"]["dataPoints"][0]["asDouble"], 1.5)

    def test_range_query_pagination_consistency(self):
        rs = RangeStore(cursor_key=b"k" * 32)
        key = ("t1", "prod", "s1", "w1", "cpu")
        for at in range(10):
            rs.add(key, at, float(at), exemplar="e" if at == 3 else None)
        rs.add(("t2", "prod", "s1", "w1", "cpu"), 1, 99.0)
        p1 = rs.query(scope_tenants=frozenset({"t1"}), tenant="t1", signal="cpu", start=0, end=10, limit=4)
        rs.add(key, 5, 555.0)                                              # write after page 1
        p2 = rs.query(scope_tenants=frozenset({"t1"}), tenant="t1", signal="cpu", start=0, end=10, limit=4, cursor=p1["next_cursor"])
        self.assertNotIn(555.0, [i["value"] for i in p2["items"]])         # same snapshot watermark
        self.assertEqual(p2["watermark"], p1["watermark"])
        agg = rs.query(scope_tenants=frozenset({"t1"}), tenant="t1", signal="cpu", start=0, end=10, agg="sum", step=5)
        self.assertEqual([i["value"] for i in agg["items"]], [0 + 1 + 2 + 3 + 4, 5 + 555 + 6 + 7 + 8 + 9])
        self.assertEqual(agg["items"][0]["exemplar"], "e")
        with self.assertRaises(Unauthorized):
            rs.query(scope_tenants=frozenset({"t1"}), tenant="t2", signal="cpu", start=0, end=10)
        bad = p1["next_cursor"][:-4] + "AAAA"
        with self.assertRaises(Malformed):
            rs.query(scope_tenants=frozenset({"t1"}), tenant="t1", signal="cpu", start=0, end=10, cursor=bad)


class TestReconnect(unittest.TestCase):
    def test_reconcile_dups_poison_and_order(self):
        d = tmpdir()
        ingest, *_ = make_stack(d)
        wal = WriteAheadBuffer(os.path.join(d, "site.wal"))
        def entry(sid, at, **kw):
            a = signed([sample(at=at)], sid=sid)
            a["samples"] = [{f: getattr(s, f) for f in ("signal", "value", "tenant", "environment", "site", "workload", "at")}
                            for s in a["samples"]]
            a.update(kw)
            return a
        e1 = entry("w1", 100)
        ingest.submit(**{**e1, "samples": [sample(at=100)]})             # hub got it, site never saw the ack
        wal.append(e1); wal.append(entry("w2", 101)); wal.append(entry("w3", 102, signature="0" * 128)); wal.append(entry("w4", 103))
        out = reconcile(wal, ingest)
        self.assertEqual((out["delivered"], out["duplicates"], [r["code"] for r in out["rejected"]]), (2, 1, ["reporter_untrusted"]))
        self.assertEqual(wal.pending(), [])
        self.assertEqual(ingest.store.read(caller_tenant="t1", tenant="t1", environment="prod", site="s1", workload="w1",
                                           signal="cpu", now=1000)["sample_at"], 103)


if __name__ == "__main__":
    unittest.main()
