"""Config, controls, audit, telemetry, trust, errors (C015, C017, C025, C026, C032-C040, C049, C053, C054,
C059, C071-C077)."""
from __future__ import annotations

import copy
import io
import json
import os
import random
import tempfile
import unittest
from pathlib import Path

from inv45_sfi_mechanisms.tests import support  # noqa: F401
from inv45_sfi_mechanisms.production import audit, config, controls, errors, telemetry, trust
from inv45_sfi_mechanisms.production.errors import SfiError


def code(fn, *a, **k):
    try:
        fn(*a, **k)
    except SfiError as e:
        return e.code
    return "OK"


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = config.GenerationStore(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_secure_defaults(self):
        cfg = config.validate(dict(config.DEFAULTS))
        self.assertFalse(cfg["profile"]["allow_memory_grow"])
        self.assertFalse(cfg["profile"]["allow_memory_export"])
        self.assertEqual(cfg["profile"]["function_import_allowlist"], [])

    def test_unknown_and_wrongly_typed_keys(self):
        for mut in (lambda c: c.update(bogus=1), lambda c: c["limits"].update(max_module_bytes="1"),
                    lambda c: c["limits"].update(max_module_bytes=1.5), lambda c: c["profile"].update(allow_memory_grow=1),
                    lambda c: c["limits"].update(deadline_seconds=float("nan")),
                    lambda c: c["telemetry"].update(log_level="trace"),
                    lambda c: c["admission"].update(max_per_tenant=10, max_concurrent=2),
                    lambda c: c["trust"].update(api_token="x"), lambda c: c["profile"].update(region_base=3)):
            cfg = copy.deepcopy(config.DEFAULTS)
            mut(cfg)
            self.assertEqual(code(config.validate, cfg), "SFI_CONFIG_INVALID")

    def test_strict_json(self):
        self.assertEqual(code(config.load_json_strict, '{"a":1,"a":2}'), "SFI_CONFIG_INVALID")
        self.assertEqual(code(config.load_json_strict, '{"a":NaN}'), "SFI_CONFIG_INVALID")
        self.assertEqual(code(config.load_json_strict, '{"a":'), "SFI_SCHEMA_INVALID")

    def test_overlays_precedence(self):
        env = {"environment": "prod", "telemetry": {"retention_days": 90}}
        site = {"site": "edge-7", "telemetry": {"retention_days": 14}, "admission": {"max_concurrent": 2,
                                                                                     "max_per_tenant": 1}}
        eff = config.validate(config.merge(config.DEFAULTS, env, site))
        self.assertEqual((eff["environment"], eff["site"], eff["telemetry"]["retention_days"]), ("prod", "edge-7", 14))

    def test_generations_provenance_activation_rollback(self):
        n1 = self.store.activate(dict(config.DEFAULTS), author="alice", source="test", approval="CR-1",
                                 expected_current=0)
        cfg2 = copy.deepcopy(config.DEFAULTS)
        cfg2["telemetry"]["retention_days"] = 60
        n2 = self.store.activate(cfg2, author="bob", source="test", approval=None, expected_current=n1)
        rec = self.store.read(n2)
        self.assertEqual(rec["provenance"]["author"], "bob")
        self.assertEqual(rec["provenance"]["supersedes"], n1)
        self.assertEqual(code(self.store.activate, cfg2, author="c", source="t", approval=None, expected_current=n1),
                         "SFI_CONFIG_CONFLICT")
        n3 = self.store.rollback(n1, author="alice", reason="regression")
        self.assertEqual(self.store.active()[1]["telemetry"]["retention_days"], 30)
        self.assertTrue((Path(self.tmp.name) / "activations" / f"act-{n3:06d}.json").exists())

    def test_invalid_generation_never_activates(self):
        bad = copy.deepcopy(config.DEFAULTS)
        bad["limits"]["deadline_seconds"] = 0
        self.assertEqual(code(self.store.activate, bad, author="a", source="t", approval=None, expected_current=0),
                         "SFI_CONFIG_INVALID")
        self.assertEqual(self.store.current_number(), 0)
        self.assertEqual(list((Path(self.tmp.name) / "generations").iterdir()), [])


class ControlsTest(unittest.TestCase):
    def test_lifecycle_legal_and_illegal(self):
        lc = controls.Lifecycle()
        for s in ("VALIDATED", "VERIFIED", "SEALED", "LOADED", "RUNNING", "LOADED", "QUARANTINED", "STOPPED"):
            lc.to(s, "t")
        self.assertEqual(code(lc.to, "RUNNING", "x"), "SFI_ILLEGAL_TRANSITION")
        self.assertEqual(code(controls.Lifecycle().to, "LOADED", "skip verify"), "SFI_ILLEGAL_TRANSITION")
        # exhaustive: no path reaches LOADED without passing VERIFIED and SEALED
        for s, nxt in controls.TRANSITIONS.items():
            if "LOADED" in nxt:
                self.assertIn(s, ("SEALED", "RUNNING"))

    def test_admission_quotas(self):
        a = controls.Admission(max_concurrent=2, max_per_tenant=1, max_queue=0, queue_timeout=0.01)
        with a.slot("t1"):
            self.assertEqual(code(lambda: a.slot("t1").__enter__()), "SFI_OVERLOADED")
            with a.slot("t2"):
                e = code(lambda: a.slot("t3").__enter__())
                self.assertEqual(e, "SFI_OVERLOADED")
        self.assertEqual(a.snapshot()["active"], 0)
        self.assertEqual(a.snapshot()["shed"], 2)

    def test_retry_only_retryable_with_bounded_jitter(self):
        sleeps = []
        calls = {"n": 0}

        def transient():
            calls["n"] += 1
            if calls["n"] < 3:
                raise SfiError("SFI_OVERLOADED", "busy")
            return "ok"
        self.assertEqual(controls.retry(transient, sleep=sleeps.append, rng=random.Random(1)), "ok")
        self.assertTrue(all(0 <= s <= 1.0 for s in sleeps))
        calls["n"] = 0

        def terminal():
            calls["n"] += 1
            raise SfiError("SFI_UNMASKED_ACCESS", "no")
        self.assertEqual(code(controls.retry, terminal, sleep=lambda s: None), "SFI_UNMASKED_ACCESS")
        self.assertEqual(calls["n"], 1)  # deterministic verifier rejection is never retried

    def test_circuit_breaker(self):
        t = [0.0]
        cb = controls.CircuitBreaker("dep", threshold=2, cooldown=10, clock=lambda: t[0])

        def down():
            raise SfiError("SFI_DEPENDENCY_UNAVAILABLE", "x", dependency="dep")
        for _ in range(2):
            code(cb.call, down)
        self.assertEqual(cb.state, "open")
        self.assertEqual(code(cb.call, lambda: 1), "SFI_DEPENDENCY_UNAVAILABLE")
        t[0] = 11
        self.assertEqual(cb.state, "half-open")
        self.assertEqual(cb.call(lambda: 1), 1)
        self.assertEqual(cb.state, "closed")

    def test_deadline(self):
        t = [0.0]
        d = controls.Deadline(1.0, clock=lambda: t[0])
        d.check("x")
        t[0] = 2
        self.assertEqual(code(d.check, "x"), "SFI_DEADLINE_EXCEEDED")
        d2 = controls.Deadline(5)
        d2.cancel()
        self.assertEqual(code(d2.check, "x"), "SFI_CANCELLED")

    def test_durable_state_quarantine_floors_and_fencing(self):
        with tempfile.TemporaryDirectory() as td:
            s = controls.DurableState(Path(td), "ctl-a")
            s.set_quarantine("tenant", "t1", "freeze", "r", ["op"])
            s.enforce_floor("wl", 3)
            s2 = controls.DurableState(Path(td), "ctl-a")  # restart: state survives
            self.assertEqual(s2.blocked("t1", "d")["action"], "freeze")
            self.assertEqual(code(s2.enforce_floor, "wl", 2), "SFI_ROLLBACK_REJECTED")
            self.assertEqual(code(controls.DurableState, Path(td), "ctl-b"), "SFI_CONFIG_CONFLICT")
            controls.DurableState(Path(td), "ctl-b", force=True)  # operator takeover
            self.assertEqual(code(s2.set_quarantine, "tenant", "t2", "freeze", "r", []), "SFI_CONFIG_CONFLICT")
            self.assertEqual(code(s.set_quarantine, "bogus", "t", "freeze", "r", []), "SFI_SCHEMA_INVALID")


class AuditTest(unittest.TestCase):
    def test_chain_detects_edit_delete_reorder_truncate(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "a.jsonl"
            log = audit.AuditLog(p, fsync=False)
            for i in range(6):
                log.emit({"event": "e", "target": str(i), "secret": "x", "artifact": b"\x00" * 10})
            cp = log.checkpoint()
            self.assertEqual(audit.verify_chain(p, cp)["events"], 6)
            self.assertNotIn('"secret"', p.read_text())
            lines = p.read_text().splitlines(True)
            for name, mutated in (("edit", lines[:2] + [lines[2].replace('"2"', '"9"')] + lines[3:]),
                                  ("delete", lines[:2] + lines[3:]), ("reorder", [lines[1], lines[0]] + lines[2:])):
                q = Path(td) / f"{name}.jsonl"
                q.write_text("".join(mutated))
                self.assertEqual(code(audit.verify_chain, q), "SFI_AUDIT_TAMPERED", name)
            q = Path(td) / "trunc.jsonl"
            q.write_text("".join(lines[:4]))
            audit.verify_chain(q)  # chain alone cannot see truncation...
            self.assertEqual(code(audit.verify_chain, q, cp), "SFI_AUDIT_TAMPERED")  # ...checkpoint can
            log2 = audit.AuditLog(p, fsync=False)  # restart continues the chain
            log2.emit({"event": "after-restart"})
            self.assertEqual(audit.verify_chain(p)["events"], 7)


class TelemetryTest(unittest.TestCase):
    def test_metrics_bounded_labels_and_export(self):
        m = telemetry.Metrics()
        for i in range(telemetry.MAX_SERIES + 50):
            m.inc("sfi_x", tenant=f"t{i}")
        self.assertLessEqual(len(m.counters), telemetry.MAX_SERIES + 1)
        m.observe_ms("sfi_lat_ms", 3.0)
        text = m.prometheus()
        self.assertIn('sfi_lat_ms_bucket{le="5"} 1', text)
        self.assertIn('series="__overflow__"', text)

    def test_traceparent(self):
        t = telemetry.Trace.from_header("00-" + "a" * 32 + "-" + "b" * 16 + "-01")
        self.assertEqual(t.trace_id, "a" * 32)
        self.assertNotEqual(t.span_id, "b" * 16)
        for bad in (None, "garbage", "00-" + "0" * 32 + "-" + "b" * 16 + "-01"):
            self.assertNotEqual(telemetry.Trace.from_header(bad).trace_id, "0" * 32)

    def test_structured_log_fields_and_redaction(self):
        s = io.StringIO()
        lg = telemetry.Logger(stream=s, node="n1")
        lg.log("info", "submit", telemetry.Trace.new(), tenant="t1", workload="w", password="p")
        rec = json.loads(s.getvalue())
        for k in ("node", "component", "operation", "tenant", "workload", "trace_id", "span_id"):
            self.assertIn(k, rec)
        self.assertNotIn("password", rec)

    def test_explain(self):
        ex = telemetry.Explainer(capacity=2)
        d = ex.record(decision="submit", outcome="rejected", inputs={"tenant": "t"}, policy={"generation": 1},
                      topology={"node": "n"}, constraint="SFI_UNMASKED_ACCESS")
        self.assertIn("SFI_UNMASKED_ACCESS", ex.explain(d))
        for _ in range(3):
            ex.record(decision="d", outcome="o", inputs={}, policy={}, topology={}, constraint="c")
        self.assertIn("expired", ex.explain(d))


class ErrorsTest(unittest.TestCase):
    def test_registry_unique_and_complete(self):
        specs = list(errors.REGISTRY.values())
        self.assertEqual(len({s.wire for s in specs}), len(specs))
        self.assertTrue(all(s.category in {"input", "policy", "security", "auth", "resource", "dependency",
                                           "internal", "compatibility"} for s in specs))
        self.assertFalse([s for s in specs if s.category in ("security", "policy") and s.retryable])

    def test_unregistered_code_becomes_invariant_and_details_allowlisted(self):
        e = SfiError("SFI_MADE_UP", "x", secret="s", artifact_sha256="a", module=b"\x00" * 50)
        self.assertEqual(e.code, "SFI_INTERNAL_INVARIANT")
        e = SfiError("SFI_UNMASKED_ACCESS", "x", secret="s", module=b"\x00" * 50, limit=3)
        self.assertNotIn("secret", e.details)
        self.assertEqual(e.details["module"], "<50 bytes redacted>")


class TrustTest(unittest.TestCase):
    def test_secret_ref(self):
        self.assertEqual(code(trust.SecretRef, "plaintext"), "SFI_CONFIG_INVALID")
        os.environ["INV45_SHORT"] = "short"
        try:
            self.assertEqual(code(trust.SecretRef("env:INV45_SHORT").resolve), "SFI_CONFIG_INVALID")
        finally:
            os.environ.pop("INV45_SHORT")
        self.assertEqual(code(trust.SecretRef("env:INV45_DOES_NOT_EXIST").resolve), "SFI_DEPENDENCY_UNAVAILABLE")
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write("k" * 40 + "\n")
        try:
            self.assertEqual(len(trust.SecretRef("file:" + f.name).resolve()), 40)
        finally:
            os.unlink(f.name)

    def test_key_validity_window(self):
        os.environ["INV45_K"] = "k" * 64
        try:
            kr = trust.KeyRing(clock=lambda: 100.0, loaded_at=100.0)
            kr.add(trust.HmacKey("k", trust.SecretRef("env:INV45_K"), not_before=200), activate=True)
            self.assertEqual(code(kr.sign, b"x"), "SFI_SIGNATURE_INVALID")
        finally:
            os.environ.pop("INV45_K")


if __name__ == "__main__":
    unittest.main()
