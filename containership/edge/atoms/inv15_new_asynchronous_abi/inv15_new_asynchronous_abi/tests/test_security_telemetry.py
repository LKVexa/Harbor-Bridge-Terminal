"""Components 40, 43, 45, 47-54: redaction, audit chain, side channels, telemetry."""
import json
import statistics
import time
import unittest

from _util import mk
from inv15_new_asynchronous_abi import handles as H
from inv15_new_asynchronous_abi.errors import AbiError
from inv15_new_asynchronous_abi.host import AsyncHost, Limits
from inv15_new_asynchronous_abi.telemetry import AuditChain, EventLog, Metrics, TraceContext, EVENT_FIELDS


class TestRedaction(unittest.TestCase):
    def test_no_token_anywhere_observable(self):
        h, _ = mk()
        v = h.register("i", tenant="t", workload="w")
        toks = []
        for i in range(10):
            _, x = v.call(trace=TraceContext("a" * 32, "b" * 16))
            toks.append(x.token.hex())
            if i % 2:
                h.complete(x, i)
            if i % 3 == 0:
                v.cancel(x)
        try:
            v.wait([H.Handle(1, 999, 0, bytes(16))])
        except AbiError as e:
            err = str(e) + json.dumps(e.envelope())
        h.refresh_gauges()
        blob = "".join([json.dumps(list(h.events.events), default=str), json.dumps(h.explain(), default=str),
                        h.metrics.render_prometheus(), json.dumps(h.audit.records, default=str), err])
        for t in toks:
            self.assertNotIn(t, blob)
            self.assertNotIn(t[:16], blob)


class TestAudit(unittest.TestCase):
    def test_chain_detects_tamper_and_truncation(self):
        a = AuditChain()
        for i in range(5):
            a.append("foreign_handle", n=i)
        self.assertTrue(a.verify()[0])
        a.records[2]["n"] = 99
        self.assertFalse(a.verify()[0])
        b = AuditChain()
        for i in range(5):
            b.append("x", n=i)
        b.records.pop()
        self.assertFalse(b.verify()[0])

    def test_host_emits_security_events(self):
        h, _ = mk(Limits(instance=1))
        v = h.register("i", tenant="t", workload="w")
        _, x = v.call()
        for fn in (v.call, lambda: v.wait([H.Handle(1, 5, 0, bytes(16))])):
            try:
                fn()
            except AbiError:
                pass
        v.cancel(x)
        try:
            v.take(x)
        except AbiError:
            pass
        kinds = {r["kind"] for r in h.audit.records}
        self.assertTrue({"budget_refusal", "foreign_handle", "use_after_consume"} <= kinds)
        self.assertTrue(h.audit.verify()[0])


class TestSideChannel(unittest.TestCase):
    def test_foreign_vs_cross_tenant_indistinguishable_shape(self):
        h = AsyncHost()
        a = h.register("a", tenant="t1", workload="w")
        b = h.register("b", tenant="t2", workload="w")
        _, x = a.call()
        env = []
        for hd in (x, H.Handle(1, x.slot, x.generation, bytes(16)), H.Handle(1, 4000, 0, bytes(16))):
            try:
                b.wait([hd])
            except AbiError as e:
                env.append(e.envelope())
        self.assertEqual(len({json.dumps(e, sort_keys=True) for e in env}), 1)

    def test_timing_difference_is_measured(self):
        """Measures, does not certify: records median ns for existing-cross-tenant vs
        nonexistent handle lookups. Asserts only that the gap is under 5x (coarse)."""
        h = AsyncHost()
        a = h.register("a", tenant="t1", workload="w")
        b = h.register("b", tenant="t2", workload="w")
        _, x = a.call()
        nx = H.Handle(1, 4000, 0, bytes(16))

        def med(hd):
            s = []
            for _ in range(400):
                t = time.perf_counter_ns()
                try:
                    b.wait([hd])
                except AbiError:
                    pass
                s.append(time.perf_counter_ns() - t)
            return statistics.median(s)

        m1, m2 = med(x), med(nx)
        self.__class__.measured = (m1, m2)
        self.assertLess(max(m1, m2) / min(m1, m2), 5.0)


class TestTelemetry(unittest.TestCase):
    def test_metric_label_guard_and_series_cap(self):
        m = Metrics()
        with self.assertRaises(ValueError):
            m.inc("x", {"reason": "free text with spaces"})
        m.MAX_SERIES = 3
        for i in range(10):
            m.inc("x", {"k": f"v{i}"})
        self.assertEqual(len(m.counters), 3)
        self.assertEqual(m.dropped_series, 7)
        self.assertIn("pk_async_metric_series_dropped_total 7", m.render_prometheus())

    def test_histogram_quantiles(self):
        m = Metrics()
        for i in range(1, 101):
            m.hist["wait_size"].observe(i)
        s = m.hist["wait_size"].summary()
        self.assertEqual((s["count"], s["p50"], s["p99"], s["max"]), (100, 51, 100, 100))

    def test_event_schema_and_sampling(self):
        e = EventLog(sample_rate=0.0)
        e.emit(op="call")
        e.emit(op="foreign_handle")
        self.assertEqual([x["op"] for x in e.events], ["foreign_handle"])
        self.assertEqual(e.sampled_out, 1)
        self.assertEqual(set(e.events[0]), set(EVENT_FIELDS))
        with self.assertRaises(ValueError):
            e.emit(op="x", token="nope")

    def test_trace_propagation(self):
        tc = TraceContext.parse("00-" + "a" * 32 + "-" + "b" * 16 + "-01")
        self.assertEqual(tc.header(), "00-" + "a" * 32 + "-" + "b" * 16 + "-01")
        self.assertIsNone(TraceContext.parse("00-" + "0" * 32 + "-" + "b" * 16 + "-01"))
        self.assertIsNone(TraceContext.parse("garbage"))
        h, _ = mk()
        v = h.register("i", tenant="t", workload="w")
        _, x = v.call(trace=tc)
        h.complete(x, 1)
        evs = [e for e in h.events.events if e["corr"]]
        self.assertTrue(evs and all(e["trace_id"] == "a" * 32 for e in evs))
        self.assertEqual(len({e["span_id"] for e in evs}), 1)
        self.assertNotEqual(evs[0]["span_id"], "b" * 16)

    def test_explain_bounded(self):
        h = AsyncHost()
        for i in range(100):
            h.register(f"i{i}", tenant="t", workload="w")
        e = h.explain(max_instances=10)
        self.assertEqual((len(e["instances"]), e["instances_truncated"]), (10, 90))

    def test_prometheus_exposition(self):
        h, _ = mk()
        v = h.register("i", tenant="t", workload="w")
        _, x = v.call()
        v.cancel(x)
        h.refresh_gauges()
        text = h.metrics.render_prometheus()
        for name in ("pk_async_calls_total", "pk_async_cancellations_total", "pk_async_subtasks_open",
                     "pk_async_cancel_ack_ns_bucket", "pk_async_tombstones"):
            self.assertIn(name, text)


if __name__ == "__main__":
    unittest.main()
