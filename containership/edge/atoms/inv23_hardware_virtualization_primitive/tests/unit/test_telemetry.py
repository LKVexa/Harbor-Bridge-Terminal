"""MC-07: signals emitted, bounded labels, redaction, isolation."""

import tempfile
import threading
import unittest

from tests._boot import mod

tel = mod("telemetry")
own = mod("ownership")
posix = mod("ownership.posix")


class Broken(tel.Sink):
    def metric(self, *a):
        raise RuntimeError("exporter down")

    def event(self, *a):
        raise RuntimeError("exporter down")

    def span(self, *a):
        raise RuntimeError("exporter down")


class TelemetryTest(unittest.TestCase):
    def test_every_contract_signal_is_declared(self):
        for sig in (
            "inv23_virt_primitive",
            "inv23_nesting_depth",
            "inv23_claim_conflicts_total",
            "inv23_probe_failures_total",
            "inv23_probe_latency_seconds",
        ):
            self.assertIn(sig, tel.METRICS)

    def test_unbounded_labels_rejected(self):
        t = tel.Telemetry()
        with self.assertRaises(tel.LabelError):
            t.count("inv23_claim_conflicts_total", holder="vmm-a")
        with self.assertRaises(tel.LabelError):
            t.count("inv23_probe_failures_total", reason="anything-goes", backend="linux-kvm")
        with self.assertRaises(tel.LabelError):
            t.gauge("inv23_virt_primitive", 1, state="usable", backend="linux-kvm", platform="myhost.example")

    def test_claim_signals_and_redaction(self):
        sink = tel.MemorySink()
        p = own.MemoryClaimProvider(telemetry=tel.Telemetry(sink))
        c = p.acquire("vmm-secret-holder")
        with self.assertRaises(own.ClaimConflict):
            p.acquire("other")
        p.release(c)
        self.assertEqual(sink.counters[("inv23_claim_conflicts_total", (("provider", "memory"),))], 1)
        ids = [e["event_id"] for e in sink.events]
        self.assertEqual(ids, ["INV23-E003", "INV23-E004", "INV23-E005"])
        dump = repr(sink.events) + repr(sink.spans) + repr(sink.counters)
        self.assertNotIn(c.token, dump)
        self.assertEqual(
            tel.redact({"token": "x", "a": {"token_sha256": "y"}}), {"token": "[REDACTED]", "a": {"token_sha256": "[REDACTED]"}}
        )

    def test_exporter_failure_isolated(self):
        t = tel.Telemetry(Broken())
        p = posix.PosixClaimProvider(tempfile.mkdtemp(), telemetry=t)
        c = p.acquire("a")
        with self.assertRaises(own.ClaimConflict):
            p.acquire("b")
        p.release(c)
        self.assertGreater(t.errors, 0)

    def test_concurrent_updates_and_cardinality(self):
        sink = tel.MemorySink()
        t = tel.Telemetry(sink)

        def work():
            for _ in range(500):
                t.count("inv23_probe_failures_total", reason="probe_timeout", backend="linux-kvm")

        ts = [threading.Thread(target=work) for _ in range(8)]
        for x in ts:
            x.start()
        for x in ts:
            x.join()
        self.assertEqual(sum(sink.counters.values()), 4000)
        self.assertLessEqual(sink.series_count(), tel.MAX_SERIES)

    def test_invalid_input_emits_nothing(self):
        sink = tel.MemorySink()
        p = own.MemoryClaimProvider(telemetry=tel.Telemetry(sink))
        with self.assertRaises(ValueError):
            p.acquire("")
        self.assertEqual((sink.events, sink.counters), ([], {}))

    def test_event_snapshot_shape(self):
        sink = tel.MemorySink()
        tel.Telemetry(sink, component_version="5.0.0").event("INV23-E002", backend="linux-kvm", reason="permission_denied")
        e = sink.events[0]
        self.assertEqual(
            {k: e[k] for k in ("event_id", "event", "component_version", "semconv", "reason")},
            {
                "event_id": "INV23-E002",
                "event": "probe.failure",
                "component_version": "5.0.0",
                "semconv": "inv23.telemetry/1",
                "reason": "permission_denied",
            },
        )


if __name__ == "__main__":
    unittest.main()
