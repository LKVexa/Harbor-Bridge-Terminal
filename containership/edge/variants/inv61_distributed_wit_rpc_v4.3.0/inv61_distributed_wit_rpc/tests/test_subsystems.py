"""M05 negotiation, M10/M11 resilience, M12 config, M14-M18 observability,
M19/M20 ownership and durable state."""
import json
import os
import pathlib
import random
import secrets
import tempfile
import unittest

from _harness import KV, Fixture, codec, config, negotiation, observability, resilience, state


class Clock:
    def __init__(self, t=0.0):
        self.t = t

    def __call__(self):
        return self.t


class NegotiationTest(unittest.TestCase):
    def test_choose(self):
        self.assertEqual(negotiation.choose([(2, 0), (2, 1)], (2, 0)), (2, 1))
        self.assertEqual(negotiation.choose([(2, 0)], (2, 0)), (2, 0))
        for offered, mn in [([(1, 0)], (1, 0)), ([(3, 0)], (3, 0)), ([(2, 0)], (2, 1))]:
            with self.assertRaises(negotiation.NegotiationError):
                negotiation.choose(offered, mn)

    def test_downgrade_detected(self):
        k = secrets.token_bytes(32)
        # attacker strips (2,1) from the offer the server sees
        server_blob = negotiation.transcript("c", [(2, 0)], (2, 0), "n", "s", (2, 0), "m")
        mac = negotiation.transcript_mac(k, server_blob)
        client_blob = negotiation.transcript("c", [(2, 0), (2, 1)], (2, 0), "n", "s", (2, 0), "m")
        with self.assertRaises(negotiation.NegotiationError):
            negotiation.verify_ack(k, client_blob, mac, [(2, 0), (2, 1)], (2, 0))

    def test_matrix_consistent_with_code(self):
        m = negotiation.matrix()
        self.assertEqual([tuple(v) for v in m["wire_protocol"]["supported"]], list(negotiation.SUPPORTED))
        self.assertEqual(tuple(m["wire_protocol"]["min_accepted"]), negotiation.MIN_ACCEPTED)


class ResilienceTest(unittest.TestCase):
    def test_retry_classification_and_backoff(self):
        p = resilience.RetryPolicy(rng=random.Random(1))
        self.assertTrue(p.should_retry("overloaded", 1, True, 1.0))
        self.assertFalse(p.should_retry("overloaded", 1, False, 1.0))  # non-idempotent
        self.assertFalse(p.should_retry("permission-denied", 1, True, 1.0))
        self.assertFalse(p.should_retry("overloaded", 4, True, 1.0))
        self.assertFalse(p.should_retry("overloaded", 1, True, 0))
        for a in range(1, 10):
            self.assertLessEqual(p.backoff(a), min(p.cap_s, p.base_s * 2 ** (a - 1)))
        self.assertFalse(resilience.RETRYABLE & resilience.NON_RETRYABLE)

    def test_token_bucket(self):
        c = Clock()
        b = resilience.TokenBucket(10, 2, c)
        self.assertTrue(b.take()); self.assertTrue(b.take()); self.assertFalse(b.take())
        c.t = 0.1
        self.assertTrue(b.take())

    def test_admission(self):
        a = resilience.AdmissionController(max_inflight=2, per_tenant_inflight=1, tenant_rate=100, tenant_burst=100)
        self.assertEqual(a.admit("t1"), "ok")
        self.assertEqual(a.admit("t1"), "overloaded")  # per-tenant
        self.assertEqual(a.admit("t2"), "ok")
        self.assertEqual(a.admit("t3"), "overloaded")  # global
        a.release("t1")
        self.assertEqual(a.admit("t3"), "ok")
        with self.assertRaises(RuntimeError):
            a.release("nobody")

    def test_breaker_state_machine(self):
        c = Clock()
        br = resilience.CircuitBreaker(2, 5, c)
        br.record(False); br.record(False)
        self.assertFalse(br.allow())
        c.t = 5
        self.assertTrue(br.allow()); self.assertFalse(br.allow())  # single probe
        br.record(False)
        self.assertFalse(br.allow())
        c.t = 10
        self.assertTrue(br.allow()); br.record(True)
        self.assertEqual(br.state, "closed")

    def test_idempotency_cache(self):
        c = Clock()
        ic = resilience.IdempotencyCache(ttl_s=10, capacity=2, clock=c)
        self.assertEqual(ic.begin(("k",), "d")[0], "new")
        self.assertEqual(ic.begin(("k",), "d")[0], "running")
        ic.complete(("k",), b"v")
        self.assertEqual(ic.begin(("k",), "d"), ("done", b"v"))
        self.assertEqual(ic.begin(("k",), "other")[0], "conflict")
        ic.begin(("k2",), "d")
        self.assertEqual(ic.begin(("k3",), "d")[0], "full")
        c.t = 20
        self.assertEqual(ic.begin(("k",), "d")[0], "new")  # expired


class ConfigTest(unittest.TestCase):
    def base(self):
        return dict(config.DEFAULTS, tls_cert="file:c.pem", tls_key="file:k.pem", tls_ca="file:ca.pem",
                    keyring="file:keys.json", audit_key="env:INV61_AUDIT_KEY")

    def test_validate(self):
        self.assertEqual(config.validate(self.base()), [])
        bad = dict(self.base(), listen_port=70000, bogus=1, tls_key="literal-secret", log_level="LOUD",
                   max_inflight=True)
        errs = " ".join(config.validate(bad))
        for frag in ("range: listen_port", "unknown key: bogus", "secret-literal: tls_key", "log_level", "max_inflight"):
            self.assertIn(frag, errs)
        self.assertIn("require_tls", " ".join(config.validate(dict(self.base(), tls_ca=None))))

    def test_layers_provenance_activation_rollback(self):
        d = pathlib.Path(tempfile.mkdtemp())
        (d / "base.json").write_text(json.dumps({k: v for k, v in self.base().items() if k in
                                                 ("tls_cert", "tls_key", "tls_ca", "keyring", "audit_key")}))
        (d / "prod.json").write_text(json.dumps({"max_inflight": 128}))
        cfg, src = config.load_layers(d / "base.json", d / "prod.json")
        self.assertEqual(cfg["max_inflight"], 128)
        seen = []
        store = config.ConfigStore(on_change=lambda old, new: seen.append((old["max_inflight"], new["max_inflight"])))
        p1 = store.activate(cfg, src, actor="deployer")
        self.assertEqual(p1.generation, 1)
        self.assertEqual(len(p1.sources), 3)
        p2 = store.activate(dict(cfg, max_inflight=64), src, actor="deployer")
        self.assertNotEqual(p1.merged_digest, p2.merged_digest)
        with self.assertRaises(config.ConfigError):
            store.activate(dict(cfg, listen_port=9), src, actor="x")  # immutable
        with self.assertRaises(config.ConfigError):
            store.activate(dict(cfg, max_inflight=0), src, actor="x")  # invalid: nothing swapped
        self.assertEqual(store.active["max_inflight"], 64)
        store.rollback(actor="oncall")
        self.assertEqual(store.active["max_inflight"], 128)
        self.assertEqual(seen, [(128, 64), (64, 128)])
        self.assertEqual(store.redacted()["tls_key"], "file:<redacted>")

    def test_secret_resolution(self):
        os.environ["INV61_T_SECRET"] = "s3"
        self.assertEqual(config.resolve_secret("env:INV61_T_SECRET"), b"s3")
        with self.assertRaises(config.ConfigError):
            config.resolve_secret("plain")


class ObservabilityTest(unittest.TestCase):
    def test_metrics_render_and_cardinality_cap(self):
        m = observability.Metrics(max_series=3)
        for i in range(10):
            m.inc("x_total", tenant_class=f"c{i}")
        text = m.render()
        self.assertIn('x_total{tenant_class="__overflow__"} 7', text)
        m.observe("lat_seconds", 0.0004, interface="i")
        m.observe("lat_seconds", 0.2, interface="i")
        t = m.render()
        self.assertIn('lat_seconds_count{interface="i"} 2', t)
        self.assertIn('le="+Inf"', t)
        self.assertEqual(m.quantile("lat_seconds", 0.5, interface="i"), 0.0005)

    def test_logger_schema_and_redaction(self):
        lines = []
        lg = observability.StructuredLogger("n1", sink=lines.append)
        lg.info("evt", mac=b"xx", nested={"password": "p"}, request_id="r1", args=[1])
        rec = json.loads(lines[0])
        self.assertEqual(rec["schema"], observability.LOG_SCHEMA)
        self.assertEqual(rec["mac"], "<redacted>")
        self.assertEqual(rec["nested"]["password"], "<redacted>")
        self.assertEqual(rec["args"], "<redacted>")
        broken = observability.StructuredLogger("n", sink=lambda _l: 1 / 0)
        broken.info("x")
        self.assertEqual(broken.dropped, 1)

    def test_traceparent(self):
        tc = observability.TraceContext.new(True)
        p = observability.TraceContext.parse(tc.traceparent)
        self.assertEqual(p, tc)
        for bad in (None, "", "00-" + "0" * 32 + "-" + "1" * 16 + "-01", "zz" + tc.traceparent[2:], tc.traceparent + "x"):
            self.assertIsNone(observability.TraceContext.parse(bad))
        tr = observability.Tracer(sample_rate=1.0, capacity=1)
        s = tr.start("op", tc)
        self.assertEqual(s.ctx.trace_id, tc.trace_id)
        self.assertEqual(s.parent_span_id, tc.span_id)
        tr.finish(s, "ok", **{"rpc.function": "f", "tenant.raw": "secret-tenant"})
        self.assertNotIn("tenant.raw", tr.finished[0].attrs)
        tr.finish(tr.start("op2", tc), "ok")
        self.assertEqual(tr.dropped, 1)

    def test_trace_propagated_through_service(self):
        fx = Fixture(tracer=observability.Tracer(sample_rate=1.0))
        parent = observability.TraceContext.new(True)
        fx.call(fx.envelope("get", ["a"], trace=parent.traceparent))
        self.assertEqual(fx.svc.tracer.finished[-1].ctx.trace_id, parent.trace_id)

    def test_health(self):
        fx = Fixture()
        h = fx.svc.health
        self.assertEqual(h.readiness()["status"], "pass")
        self.assertIn("inv61:kv/store@2.1.0#get", h.readiness()["capabilities"])
        h.checks.append(observability.DependencyCheck("store", lambda: False))
        self.assertEqual(h.readiness()["dependencies"]["store"], "fail")
        self.assertEqual(h.readiness()["status"], "fail")
        h.checks[-1] = observability.DependencyCheck("cache", lambda: 1 / 0, critical=False)
        self.assertEqual(h.readiness()["status"], "pass")
        h.stall_after_s = -1
        self.assertEqual(h.liveness()["status"], "fail")

    def test_telemetry_policy(self):
        p = observability.TelemetryPolicy(export_allowlist=("otel.internal:4317",))
        self.assertTrue(p.exporter_allowed("otel.internal:4317"))
        self.assertFalse(p.exporter_allowed("evil.example:4317"))
        self.assertFalse(p.raw_tenant_ids_in_metrics)


class OwnershipStateTest(unittest.TestCase):
    def test_lease_no_split_brain_and_fencing(self):
        c = Clock()
        la = state.LeaseAuthority(c)
        a = la.acquire("r", "A", 10)
        self.assertIsNone(la.acquire("r", "B", 10))
        c.t = 11
        b = la.acquire("r", "B", 10)
        self.assertGreater(b.epoch, a.epoch)
        fr = state.FencedResource()
        fr.check(b.epoch)
        with self.assertRaises(state.FenceError):
            fr.check(a.epoch)  # zombie old owner

    def test_restart_preserves_idempotency_disable_and_epoch(self):
        d = tempfile.mkdtemp()
        fx = Fixture(d)
        e = fx.envelope("put", [{"key": "a", "value": 1, "tags": []}, "strong"], idem="op-9")
        self.assertEqual(fx.call(e)["status"], "ok")
        epoch = fx.svc.leases.epoch
        fx.svc.set_disabled(True, "oncall")
        fx.svc.close()
        fx2 = Fixture(d)  # restart on same state/audit files
        self.assertTrue(fx2.svc.disabled)
        self.assertGreaterEqual(fx2.svc.leases.epoch, epoch)
        fx2.svc.set_disabled(False, "oncall")
        e2 = fx2.envelope("put", [{"key": "a", "value": 1, "tags": []}, "strong"], idem="op-9")
        r = fx2.call(e2)
        self.assertEqual((r["status"], r["detail"]), ("ok", "idempotent-replay"))
        self.assertEqual(fx2.calls["put"], 0)  # not re-executed after restart

    def test_corrupt_checkpoint_refused(self):
        d = pathlib.Path(tempfile.mkdtemp())
        s = state.StateStore(d / "s.json")
        s.save({"a": 1})
        doc = json.loads((d / "s.json").read_text()); doc["state"]["a"] = 2
        (d / "s.json").write_text(json.dumps(doc))
        with self.assertRaises(ValueError):
            s.load()


if __name__ == "__main__":
    unittest.main()
