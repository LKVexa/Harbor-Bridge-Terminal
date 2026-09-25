"""P1-24 audit ledger, P1-25 metrics, P1-26 logs/traces, P1-27 health, P1-28 alerts,
P1-31 usage accounting — 'telemetry template' .01-.10; P1-29/P1-32 config template."""
from __future__ import annotations

import json
import os
import secrets
import tempfile
import threading
import unittest

from support import Stack, covers, workload_token
from gap11_control.common import REASON_CODES, ControlError, ManualClock, Telemetry
from gap11_control.config import SCHEMA as CFG_SCHEMA, ConfigManager, validate as cfg_validate
from gap11_control.observability import (ALERT_RULES, AuditLedger, Metrics, StructuredLogger, child_trace,
                                         evaluate_alerts, explain, health_report, refusal_class, telemetry_bridge)
from gap11_control.scheduler import ConstraintEngine
from gap11_control.security import Keyring

T = lambda c, *n: tuple(f"GAP11-{c}.{i:02d}" for i in n)
TEL = ("P1-24", "P1-25", "P1-26", "P1-27", "P1-28", "P1-31")


def all_tel(*n):
    return tuple(x for c in TEL for x in T(c, *n))


class AuditLedgerTests(unittest.TestCase):
    def ledger(self):
        kr = Keyring(); kr.add("a1", secrets.token_bytes(32))
        return AuditLedger(os.path.join(tempfile.mkdtemp(), "audit.jsonl"), kr, clock=ManualClock()), kr

    @covers(*T("P1-24", 2, 7, 9), "GAP11-P1-32.09", "GAP11-P1-29.09")
    def test_chain_detects_edit_reorder_delete_and_truncation_against_witness(self):
        led, kr = self.ledger()
        for i in range(5):
            led.append({"action": "ALLOCATE", "i": i, "token": "must-not-appear"})
        witness = led.head()
        self.assertTrue(led.verify(witness)["ok"])
        with open(led.path) as fh:
            raw = fh.read()
        self.assertNotIn("must-not-appear", raw)                                     # redacted at write
        lines = raw.splitlines()
        for mutate in (lambda L: [L[0].replace('"i": 0', '"i": 9')] + L[1:],
                       lambda L: [L[1], L[0]] + L[2:],
                       lambda L: L[:2] + L[3:]):
            with open(led.path, "w") as fh:
                fh.write("\n".join(mutate(list(lines))) + "\n")
            self.assertFalse(led.verify()["ok"])
        with open(led.path, "w") as fh:
            fh.write("\n".join(lines[:3]) + "\n")                                     # tail truncation
        self.assertTrue(led.verify()["ok"])                                          # undetectable alone...
        self.assertFalse(led.verify(witness)["ok"])                                  # ...caught by witness
        with self.assertRaises(ControlError):
            with open(led.path, "w") as fh:
                fh.write(lines[1] + "\n")
            AuditLedger(led.path, kr, clock=ManualClock())

    @covers(*T("P1-24", 1, 3, 5, 6, 10))
    def test_every_controller_mutation_is_audited_with_lineage(self):
        st = Stack()
        a = st.ctl.allocate({"tenant": "t1", "workload": "w"}, request_id="req-aud-0001", actor="spiffe://t1/w")
        st.ctl.release(a["lease_id"], request_id="req-aud-0002", actor="spiffe://t1/w")
        with open(st.audit.path) as fh:
            rows = [json.loads(l) for l in fh]
        acts = [r["event"]["action"] for r in rows]
        self.assertIn("ALLOCATE", acts); self.assertIn("RELEASE", acts); self.assertIn("DEVICE_REGISTER", acts)
        alloc = [r for r in rows if r["event"]["action"] == "ALLOCATE"][0]["event"]
        for k in ("request_id", "actor", "controller_epoch", "revision", "keys"):
            self.assertIn(k, alloc)
        self.assertTrue(st.audit.verify(st.audit.head())["ok"])
        kr = st.keyring; kr.retire("k1")
        with self.assertRaises(ControlError) as cm:                                   # signing key gone -> refuse
            st.audit.append({"action": "X"})
        self.assertEqual(cm.exception.code, "DEPENDENCY_UNAVAILABLE")


class MetricsLogsTraceTests(unittest.TestCase):
    @covers(*all_tel(1), *T("P1-25", 2, 3))
    def test_metric_label_budget_forbids_ids(self):
        m = Metrics()
        m.inc("requests", operation="allocate", code="OK")
        for bad in ({"tenant": "t1"}, {"lease_id": "x"}, {"operation": "allocate", "code": "made-up"}):
            with self.assertRaises(ValueError):
                m.inc("requests", **bad)
        tel = Telemetry(ManualClock())
        with self.assertRaises(ValueError):
            tel.emit("x", "y", tenant="raw-tenant-id")                                 # raw tenant never a label
        with self.assertRaises(ValueError):
            tel.emit("x", "y", code="NOT_A_CODE")

    @covers(*T("P1-25", 3, 4, 8, 10), *T("P1-24", 4, 8))
    def test_histograms_counters_and_refusal_classes(self):
        st = Stack()
        svc, authn = st.service(caps={"t1": {"devices": 1, "memory_gb": 999}})
        body = lambda r, t="t1": json.dumps({"schema": "PK_ACCELERATOR_ALLOCATION_REQUEST/1", "request_id": r, "tenant": t, "workload": "w"}).encode()
        svc.handle("/v1/allocate", body("req-m-00001"), workload_token(authn))
        svc.handle("/v1/allocate", body("req-m-00002"), workload_token(authn))           # quota
        svc.handle("/v1/allocate", body("req-m-00003"), {"kid": "x", "claims": {}, "mac": ""})   # authn
        txt = svc.metrics.expose()
        self.assertIn('gap11_requests_total{code="QUOTA_EXCEEDED",operation="allocate"} 1.0', txt)
        self.assertIn('gap11_requests_total{code="UNAUTHENTICATED",operation="allocate"} 1.0', txt)
        self.assertIn('gap11_request_latency_seconds_bucket{operation="allocate",le="+Inf"} 3', txt)
        classes = {refusal_class(c) for c in REASON_CODES}
        self.assertTrue({"capacity", "policy", "hardware", "scrub", "dependency", "attack_indicator", "software_defect"} <= classes)
        self.assertEqual(refusal_class("QUOTA_EXCEEDED"), "capacity")
        self.assertEqual(refusal_class("POLICY_DENIED"), "policy")
        self.assertEqual(refusal_class("REPLAY_DETECTED"), "attack_indicator")

    @covers(*T("P1-26", 1, 3, 4, 5, 7, 10), *T("P1-24", 5))
    def test_structured_logs_are_utc_redacted_and_sampled(self):
        sink = []
        log = StructuredLogger(sink, clock=ManualClock(), min_level="DEBUG", sample_debug=10)
        line = log.log("INFO", "allocated", lease_id="abc", credential="Bearer xyz.abc", token="t")
        rec = json.loads(line)
        self.assertTrue(rec["ts"].endswith("Z"))
        self.assertEqual(rec["credential"], "[REDACTED]")
        self.assertNotIn("xyz", line)
        for _ in range(100):
            log.log("DEBUG", "tick")
        self.assertEqual(sum(1 for s in sink if '"DEBUG"' in s), 10)                  # bounded sampling
        with self.assertRaises(ValueError):
            log.log("LOUD", "x")

    @covers(*T("P1-26", 8, 9))
    def test_trace_context_continues_or_restarts_safely(self):
        tp = "00-" + "1" * 32 + "-" + "2" * 16 + "-01"
        c = child_trace(tp)
        self.assertEqual((c["trace_id"], c["parent_span_id"]), ("1" * 32, "2" * 16))
        for bad in (None, "garbage", "00-" + "0" * 32 + "-" + "2" * 16 + "-01"):
            self.assertEqual(len(child_trace(bad)["trace_id"]), 32)

    @covers(*all_tel(10))
    def test_broken_subscriber_and_full_buffer_never_break_control_path(self):
        tel = Telemetry(ManualClock(), capacity=5)
        tel.subscribers.append(lambda e: 1 / 0)
        for i in range(20):
            tel.emit("c", "e")
        self.assertEqual(len(tel.events), 5)
        self.assertGreaterEqual(tel.dropped, 15)
        m = Metrics(); telemetry_bridge(tel, m)
        tel.emit("allocator", "allocate")
        self.assertIn("gap11_events_total", m.expose())


class HealthAlertTests(unittest.TestCase):
    @covers(*T("P1-27", 1, 2, 3, 5, 6, 7, 9))
    def test_readiness_reflects_leadership_store_and_dependencies(self):
        st = Stack()
        h = health_report(version="4.3.0", config_digest="d", elector=st.elector, store=st.store,
                          dependencies={"identity": True, "policy": True}, reconcile_lag_s=1)
        self.assertTrue(h["ready"]); self.assertEqual(h["role"], "leader")
        st.store.read_only = True
        self.assertFalse(health_report(version="4.3.0", config_digest="d", elector=st.elector, store=st.store,
                                       dependencies={"identity": True}, reconcile_lag_s=1)["ready"])
        st.store.read_only = False
        self.assertFalse(health_report(version="4.3.0", config_digest="d", elector=st.elector, store=st.store,
                                       dependencies={"identity": False}, reconcile_lag_s=1)["ready"])
        self.assertFalse(health_report(version="4.3.0", config_digest="d", elector=st.elector, store=st.store,
                                       dependencies={}, reconcile_lag_s=999)["ready"])
        dec = ConstraintEngine(hard={"security": lambda r, d: d.get("security_tenant") in (None, r["tenant"])}).decide(
            {"tenant": "t1"}, [{"device": "g", "security_tenant": "t9", "memory_gb": 1, "features": [], "topology": {}}])
        self.assertIn("reasons", explain(dec))

    @covers(*T("P1-28", 1, 3, 4, 5, 6, 7, 9, 10), *T("P1-24", 9))
    def test_alert_rules_complete_and_actionable(self):
        ids = [r["id"] for r in ALERT_RULES]
        self.assertEqual(len(ids), len(set(ids)))
        for r in ALERT_RULES:
            for k in ("severity", "class", "expr", "action", "dedupe"):
                self.assertTrue(r[k], (r["id"], k))
            self.assertIn(r["severity"], ("page", "ticket"))
        self.assertEqual(evaluate_alerts({"scrub": 1})[0]["id"], "GAP11-ALERT-001")
        self.assertEqual(evaluate_alerts({}), [])


class UsageAccountingTests(unittest.TestCase):
    @covers(*T("P1-31", 1, 2, 3, 5, 6, 7, 9))
    def test_usage_records_are_durable_and_closed_on_release(self):
        clock = ManualClock()
        st = Stack(clock=clock)
        a = st.ctl.allocate({"tenant": "t1", "workload": "w", "partition": "half"}, request_id=st.rid(), actor="t1")
        clock.advance(125.5); st.elector.renew()
        st.ctl.release(a["lease_id"], request_id=st.rid(), actor="t1")
        from gap11_control.controller import Controller
        from gap11_control.store import LeaseStore
        rec = Controller(LeaseStore(st.store.dir, clock=clock), st.elector).usage_records()[0]
        self.assertEqual((rec["partition"], rec["seconds"], rec["tenant"]), ("half", 125.5, "t1"))
        self.assertTrue(rec["start"].endswith("Z") and rec["end"].endswith("Z"))


class ConfigTests(unittest.TestCase):
    @covers(*T("P1-29", 1, 2, 5, 10))
    def test_schema_validation_secure_defaults_dangerous_opt_in(self):
        self.assertEqual(cfg_validate({k: s["default"] for k, s in CFG_SCHEMA.items()}), [])
        self.assertTrue(cfg_validate({"lease_ttl_s": 1.0}))
        self.assertTrue(cfg_validate({"lease_tll_s": 30.0}))                          # unknown key
        self.assertTrue(cfg_validate({"queue_capacity": True}))
        self.assertTrue(cfg_validate({"authn_key_ref": "plaintext-key"}))
        self.assertTrue(cfg_validate({"dangerous_allow_unattested_devices": True}))
        self.assertEqual(cfg_validate({"dangerous_allow_unattested_devices": True},
                                      opt_in_dangerous={"dangerous_allow_unattested_devices"}), [])
        self.assertTrue(cfg_validate({"dangerous_skip_scrub": True}, opt_in_dangerous={"dangerous_skip_scrub"}))
        self.assertTrue(cfg_validate({"leader_ttl_s": 3.0, "leader_safety_margin_s": 3.0}))   # cross-field

    @covers(*T("P1-29", 3, 4, 6, 7, 9))
    def test_precedence_provenance_atomic_apply_and_rollback(self):
        audit = []
        cm = ConfigManager(audit=audit.append)
        cm.apply("site", {"lease_ttl_s": 60}, actor="ops")
        cm.apply("override", {"lease_ttl_s": 90}, actor="ops")
        cm.apply("environment", {"lease_ttl_s": 45}, actor="ops")
        self.assertEqual((cm.active["lease_ttl_s"], cm.provenance["lease_ttl_s"]), (90.0, "override"))
        good = cm.digest()
        def failing_hook(eff):
            raise RuntimeError("scheduler refused new config")
        with self.assertRaises(ControlError):
            cm.apply("override", {"queue_capacity": 10}, actor="ops", activate_hook=failing_hook)
        self.assertEqual(cm.digest(), good)                                           # nothing half-applied
        cm.apply("override", {"queue_capacity": 10}, actor="ops")
        cm.rollback(actor="ops")
        self.assertEqual(cm.digest(), good)
        self.assertEqual([a["action"] for a in audit][-3:], ["CONFIG_ROLLBACK", "CONFIG_APPLIED", "CONFIG_ROLLBACK"])
        with self.assertRaises(ControlError):
            cm.apply("default", {"lease_ttl_s": 5}, actor="ops")

    @covers(*T("P1-29", 10))
    def test_concurrent_updates_are_serialised(self):
        cm = ConfigManager()
        errs = []
        def worker(v):
            try:
                cm.apply("site", {"queue_capacity": v}, actor="ops")
            except Exception as e:
                errs.append(e)
        ts = [threading.Thread(target=worker, args=(v,)) for v in range(10, 60)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(errs, [])
        self.assertEqual(cm.generation, 51)

    @covers("GAP11-P1-32.02", "GAP11-P1-32.09")
    def test_operator_drain_freeze_and_quarantine_controls(self):
        st = Stack()
        st.ctl.set_draining("gpu1", True, request_id=st.rid(), actor="op")
        st.ctl.set_draining("gpu2", True, request_id=st.rid(), actor="op")
        with self.assertRaises(ControlError):
            st.ctl.allocate({"tenant": "t1", "workload": "w", "memory_gb": 70}, request_id=st.rid(), actor="t1")
        st.ctl.freeze(True)
        with self.assertRaises(ControlError) as cm:
            st.ctl.set_draining("gpu1", False, request_id=st.rid(), actor="op")
        self.assertEqual(cm.exception.code, "MAINTENANCE_MODE")
        self.assertTrue(st.ctl.devices())                                             # reads still served
        st.ctl.freeze(False)
        st.ctl.quarantine("gpu0", request_id=st.rid(), actor="op", reason="suspected residue")
        self.assertEqual(st.store.get("dev/gpu0")[1]["quarantine_reason"], "suspected residue")
        self.assertTrue(any(h["reason"] == "QUARANTINE" and h["actor"] == "op" for h in st.store.history))


if __name__ == "__main__":
    unittest.main()
