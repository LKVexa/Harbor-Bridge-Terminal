# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Service semantics: lifecycle, idempotency, quarantine, disable, health, metrics, logs, traces (GAP-012, 018, 038, 048-053)."""
import io
import json
import unittest

from .. import lifecycle
from ..telemetry import child_traceparent, parse_traceparent
from ._util import access, derive, invalidate, make_service, mint


class ServiceTest(unittest.TestCase):
    def setUp(self):
        self.svc = make_service()
        self.root = mint(self.svc)["handle"]

    def test_lifecycle_tables(self):
        with self.assertRaises(ValueError):
            lifecycle.transition(lifecycle.CAPABILITY_TRANSITIONS, "invalidated", "active")
        with self.assertRaises(ValueError):
            lifecycle.transition(lifecycle.SERVICE_TRANSITIONS, "disabled", "ready")
        self.assertEqual(lifecycle.result_state({"schema": "PK_FAILURE/1", "retryable": True}),
                         lifecycle.RETRYABLE)
        self.assertEqual(lifecycle.result_state({"permitted": True}), lifecycle.SUCCESS)

    def test_idempotency(self):
        a = derive(self.svc, self.root, 0x1000, 16, idempotency_key="k1")
        b = derive(self.svc, self.root, 0x1000, 16, idempotency_key="k1")
        self.assertEqual(a["handle"], b["handle"])
        c = derive(self.svc, self.root, 0x1000, 32, idempotency_key="k1")
        self.assertEqual(c["code"], "IDEMPOTENCY_CONFLICT")

    def test_deadline_bounds(self):
        b = {"schema": "PK_CAPABILITY_ACCESS/1", "handle": self.root, "tenant": "tenant-a", "address": 0x1000,
             "size": 8, "operation": "read", "deadline_ms": 0}
        from ._util import signed
        self.assertEqual(self.svc.access(b, signed("access", b))["code"], "SCHEMA_INVALID")

    def test_tenant_quarantine_allows_only_invalidation(self):
        self.svc.quarantine_tenant("tenant-a", operator="op", reason="suspicious")
        self.assertEqual(access(self.svc, self.root, 0x1000)["code"], "QUARANTINED")
        self.assertEqual(invalidate(self.svc, self.root)["invalidated"], 1)
        self.svc.release_tenant("tenant-a", operator="op", reason="cleared")
        self.assertEqual(access(self.svc, self.root, 0x1000)["code"], "INVALIDATED")

    def test_global_quarantine_and_emergency_disable(self):
        self.svc.set_state("quarantined", operator="op", reason="drill")
        self.assertEqual(self.svc.health()["status"], "quarantined")
        self.assertEqual(access(self.svc, self.root, 0x1000)["code"], "QUARANTINED")
        self.svc.set_state("disabled", operator="op", reason="drill")
        self.assertEqual(access(self.svc, self.root, 0x1000)["code"], "DISABLED")
        self.assertEqual(self.svc.health()["active_capabilities"], 0)
        self.assertFalse(self.svc.health()["ready"])
        self.assertEqual(self.svc.audit.verify(), [])

    def test_health_reports_everything(self):
        h = self.svc.health()
        for k in ("version", "enforcement", "config_digest", "dependencies", "active_capabilities", "mode"):
            self.assertIn(k, h)
        self.assertEqual(h["enforcement"], "semantic-model")
        self.assertEqual(h["dependencies"]["GAP-02"], "ok")

    def test_metrics_cover_contract_signals(self):
        access(self.svc, self.root, 0x9000)
        access(self.svc, self.root, 0x1000, op="execute")
        derive(self.svc, self.root, 0x1000, 16)
        invalidate(self.svc, self.root)
        access(self.svc, self.root, 0x1000)
        prom = self.svc.metrics.prometheus()
        for sig in ("capability_derivations", "bounds_violations", "permission_violations", "invalidated_uses",
                    "requests_total", "latency_ms_bucket", "active_capabilities"):
            self.assertIn(sig, prom)

    def test_structured_logs_have_stable_ids(self):
        buf = io.StringIO()
        self.svc.log.stream = buf
        r = access(self.svc, self.root, 0x1000)
        rec = json.loads(buf.getvalue().splitlines()[-1])
        for k in ("node", "component", "tenant_bucket", "workload", "operation", "correlation_id", "trace_id"):
            self.assertIn(k, rec)
        self.assertEqual(rec["correlation_id"], r["correlation_id"])

    def test_trace_propagation(self):
        tp = "00-" + "ab" * 16 + "-" + "cd" * 8 + "-01"
        b = {"schema": "PK_CAPABILITY_ACCESS/1", "handle": self.root, "tenant": "tenant-a", "address": 0x1000,
             "size": 8, "operation": "read", "traceparent": tp}
        from ._util import signed
        r = self.svc.access(b, signed("access", b))
        self.assertTrue(r["traceparent"].startswith("00-" + "ab" * 16 + "-"))
        self.assertNotEqual(r["traceparent"], tp)
        self.assertIsNone(parse_traceparent("00-" + "0" * 32 + "-" + "1" * 16 + "-01"))
        self.assertIsNone(parse_traceparent("garbage"))
        self.assertEqual(len(child_traceparent(None)[1]), 55)

    def test_revocation_sweep_is_transitive(self):
        a = derive(self.svc, self.root, 0x1000, 0x100)["handle"]
        b = derive(self.svc, a, 0x1000, 0x10)["handle"]
        self.assertEqual(invalidate(self.svc, a)["invalidated"], 2)
        self.assertEqual(access(self.svc, b, 0x1000)["code"], "INVALIDATED")
        self.assertTrue(access(self.svc, self.root, 0x1000)["permitted"])


if __name__ == "__main__":
    unittest.main()


class PriorityTest(unittest.TestCase):
    def test_invalidation_not_shed_under_overload(self):
        svc = make_service()
        h = mint(svc)["handle"]
        svc.admission.max_inflight = 0
        self.assertEqual(access(svc, h, 0x1000)["code"], "OVERLOADED")
        self.assertEqual(invalidate(svc, h)["invalidated"], 1)

    def test_health_separates_hardware_readiness(self):
        h = make_service().health()
        self.assertTrue(h["ready"])
        self.assertFalse(h["ready_for_hardware_workloads"])
        self.assertIn(h["hardware"]["state"], ("absent", "unprobed", "present"))


class DiagnosticsAndDeterminismTest(unittest.TestCase):
    def test_deep_diagnostics_requires_admin_and_expires(self):
        from ._util import signed, KEY_A
        svc = make_service()
        svc.auth.register("root-op", b"R" * 32, {"admin"}, {"*"})
        body = {"op": "deep_diagnostics", "ttl_s": 60, "reason": "incident 42"}
        with self.assertRaises(Exception):
            svc.open_deep_diagnostics(operator="x", principal_auth=signed("admin", body), ttl_s=60, reason="incident 42")
        tok = svc.open_deep_diagnostics(operator="alice", principal_auth=signed("admin", body, "root-op", b"R" * 32),
                                        ttl_s=60, reason="incident 42")
        mint(svc)
        self.assertEqual(svc.deep_diagnostics(tok)["per_tenant_capabilities"], {"tenant-a": 1})
        svc._diag["expires"] = 0
        with self.assertRaises(Exception):
            svc.deep_diagnostics(tok)
        self.assertIn("diagnostics.open", [e["action"] for e in svc.audit.events])

    def test_decisions_are_deterministic_for_same_inputs(self):
        """Replay: identical request sequences on fresh services yield identical decision/reason streams."""
        def run():
            svc = make_service()
            h = mint(svc)["handle"]
            for addr, op in [(0x1000, "read"), (0x3000, "read"), (0x1000, "execute"), (0x1FF8, "write")]:
                access(svc, h, addr, op=op)
            derive(svc, h, 0x0, 1)
            invalidate(svc, h)
            access(svc, h, 0x1000)
            return [(r["decision"], r["reason"], r["inputs"]["op"]) for r in svc.decisions.records]
        self.assertEqual(run(), run())
