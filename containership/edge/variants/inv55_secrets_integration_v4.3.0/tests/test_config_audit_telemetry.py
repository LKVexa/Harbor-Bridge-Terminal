"""Config schema/overlays/provenance/activation/rollback; audit chain; telemetry (#26-#30, #47, #71-#77)."""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest

from helpers import ROOT, SECRET, Env
from inv55_secrets_integration.audit import (AuditChain, FileAuditSink, MemoryAuditSink, pseudonymise,
                                             resume_from_file, verify_chain)
from inv55_secrets_integration.config import (ConfigController, ConfigError, deep_merge, load_layers,
                                              validate_config)
from inv55_secrets_integration.telemetry import JsonLogger, Metrics, Tracer


class ConfigTests(unittest.TestCase):
    def test_all_shipped_overlays_valid(self):
        for env, site in [("dev", None), ("staging", None), ("prod", None), ("prod", "edge-1")]:
            c = ConfigController()
            a = c.activate(load_layers(ROOT / "config", env, site))
            self.assertTrue(a.digest.startswith("sha256:"))
            self.assertEqual(len(a.layers), 2 + (site is not None))

    def test_overlay_precedence_and_delete(self):
        self.assertEqual(deep_merge({"a": {"b": 1, "c": 2}}, {"a": {"b": 3, "c": None}}), {"a": {"b": 3}})

    def test_rejects_plaintext_credentials_and_unknown_keys(self):
        base = load_layers(ROOT / "config", "prod")
        bad = [("x", {"provider": {"token": "hvs.x"}}), ("y", {"surprise": 1}),
               ("z", {"provider": {"address": "http://vault.prod:8200"}})]
        for name, layer in bad:
            with self.assertRaises(ConfigError, msg=name):
                ConfigController().activate(base + [(name, layer)])

    def test_transactional_activation_keeps_previous_on_failure(self):
        c = ConfigController()
        good = c.activate(load_layers(ROOT / "config", "prod"))

        def pre(cfg):
            raise RuntimeError("preflight failed")
        c.preflight = pre
        with self.assertRaises(RuntimeError):
            c.activate(load_layers(ROOT / "config", "staging"))
        self.assertIs(c.active, good)

    def test_rollback(self):
        c = ConfigController()
        a = c.activate(load_layers(ROOT / "config", "prod"))
        c.activate(load_layers(ROOT / "config", "prod", "edge-1"))
        r = c.rollback()
        self.assertEqual(r.digest, a.digest)
        self.assertEqual(r.generation, 3)
        self.assertEqual(c.provenance()["layers"][-1]["name"], "rollback")
        with self.assertRaises(ConfigError):
            ConfigController().rollback()

    def test_unknown_env_refused(self):
        with self.assertRaises(ConfigError):
            load_layers(ROOT / "config", "qa")


class AuditTests(unittest.TestCase):
    def test_chain_verifies_and_detects_tamper_delete_reorder(self):
        s = MemoryAuditSink()
        a = AuditChain(s, hmac_key=b"k")
        for i in range(5):
            a.record({"op": "resolve", "i": i})
        self.assertEqual(verify_chain(s.lines, b"k"), (True, 5, "ok"))
        tampered = list(s.lines)
        tampered[2] = tampered[2].replace(b'"i":2', b'"i":9')
        self.assertFalse(verify_chain(tampered, b"k")[0])
        self.assertFalse(verify_chain(s.lines[:2] + s.lines[3:], b"k")[0])
        self.assertFalse(verify_chain([s.lines[1], s.lines[0]], b"k")[0])
        self.assertFalse(verify_chain(s.lines, b"wrong-key")[0])

    def test_file_sink_resume(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "a.jsonl")
            a = AuditChain(FileAuditSink(path), hmac_key=b"k")
            a.record({"op": "x"})
            b = resume_from_file(path, FileAuditSink(path), b"k")
            self.assertEqual((b.seq, b.head), (a.seq, a.head))
            b.record({"op": "y"})
            with open(path, "rb") as fh:
                self.assertTrue(verify_chain(fh.read().splitlines(), b"k")[0])
            self.assertEqual(oct(os.stat(path).st_mode & 0o777), "0o600")
            with open(path, "ab") as fh:
                fh.write(b'{"seq":99}\n')
            with self.assertRaises(ValueError):
                resume_from_file(path, FileAuditSink(path), b"k")

    def test_service_audit_is_complete_and_secret_free(self):
        e = Env()
        e.seed()
        r = e.resolve()
        e.use(r["lease_id"])
        e.resolve(sub="marketing")
        ops = [json.loads(l)["op"] for l in e.sink.lines]
        self.assertEqual(ops.count("use"), 1)
        self.assertIn("resolve", ops)
        self.assertTrue(verify_chain(e.sink.lines, b"audit-key")[0])
        self.assertNotIn(SECRET.encode(), b"".join(e.sink.lines))

    def test_pseudonymise_is_keyed_and_stable(self):
        self.assertEqual(pseudonymise("db", b"k"), pseudonymise("db", b"k"))
        self.assertNotEqual(pseudonymise("db", b"k"), pseudonymise("db", b"k2"))
        self.assertNotIn("db", pseudonymise("db", b"k")[3:])


class TelemetryTests(unittest.TestCase):
    def test_prometheus_exposition(self):
        e = Env()
        e.seed()
        e.resolve()
        e.resolve(sub="marketing")
        text = e.svc.metrics.exposition()
        self.assertIn('inv55_requests_total{op="resolve",outcome="success"} 1.0', text)
        self.assertIn('inv55_denials_total{reason="out_of_scope"}', text)
        self.assertIn('inv55_request_seconds_bucket{op="resolve",le="+Inf"} 2', text)

    def test_bounded_cardinality(self):
        m = Metrics(max_series=3)
        for i in range(10):
            m.inc("x", k=f"v{i}")
        self.assertEqual(m.dropped_series, 7)
        with self.assertRaises(ValueError):
            m.inc("x", k="has space")

    def test_trace_propagation(self):
        t = Tracer(lambda: 0)
        tp = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
        s = t.start("resolve", tp)
        self.assertEqual((s.trace_id, s.parent_id), ("a" * 32, "b" * 16))
        self.assertNotEqual(t.start("x", "garbage").trace_id, "a" * 32)

    def test_service_propagates_trace_and_explains(self):
        e = Env()
        e.seed()
        tp = "00-" + "c" * 32 + "-" + "d" * 16 + "-01"
        r = e.resolve(request_id="req-42", traceparent=tp)
        self.assertTrue(r["ok"])
        self.assertIn("c" * 32, [s.trace_id for s in e.svc.tracer.finished])
        x = e.svc.ledger.explain("req-42")
        self.assertEqual(x["decision"], "allowed")
        self.assertEqual(x["trace_id"], "c" * 32)
        self.assertTrue(x["evaluated_against"]["policy"].startswith("sha256:"))
        self.assertEqual(x["evaluated_against"]["release"], "4.3.0")
        e.resolve(request_id="req-43", sub="marketing")
        self.assertEqual(e.svc.ledger.explain("req-43")["why"], "out_of_scope")

    def test_json_logger_one_object_per_line(self):
        s = io.StringIO()
        lg = JsonLogger(s, lambda: 1.5)
        lg.log("info", "a", n=1)
        lg.log("warn", "b", msg="line\nbreak")
        lines = s.getvalue().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[1])["msg"], "line\nbreak")


if __name__ == "__main__":
    unittest.main()
