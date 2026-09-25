"""Service pipeline: isolation, authz, controls, health, observability, audit, explain
(MC-020..023, MC-026, MC-030..038)."""
from __future__ import annotations

import io
import json
import time
import unittest

from _util import AUDIT_KEY, NS_A, NS_B, FakeClock, ctx, make_service, principal, txn_body
from inv05_current_control_state_system.audit import AuditLog
from inv05_current_control_state_system.errors import (
    Cancelled, DeadlineExceeded, FailedClosed, Frozen, InvalidArgument, PermissionDenied, QuotaExceeded,
    Unavailable,
)
from inv05_current_control_state_system.limits import Limits
from inv05_current_control_state_system.observability import StructuredLogger, Tracer
from inv05_current_control_state_system.service import CancelToken

PUT = lambda k, v, **kw: {"put": {"key": k, "value": v, **kw}}
OP = principal(NS_A, "operator", name="op")
SEC = principal(NS_A, "security-admin", name="sec")


class IsolationTest(unittest.TestCase):  # MC-021
    def setUp(self):
        self.svc = make_service()
        self.a = principal(NS_A, "writer")
        self.b = principal(NS_B, "writer")

    def test_same_key_different_tenants_never_collide(self):
        self.svc.txn(ctx(self.a), txn_body(success=[PUT("cfg", "A")]))
        self.svc.txn(ctx(self.b), txn_body(success=[PUT("cfg", "B")]))
        ra = self.svc.range(ctx(self.a), {"schema": "cstate.range/1.1", "key": "cfg"})
        rb = self.svc.range(ctx(self.b), {"schema": "cstate.range/1.1", "key": "cfg"})
        self.assertEqual((ra["kvs"][0]["value"], rb["kvs"][0]["value"]), ("A", "B"))
        self.assertEqual(ra["kvs"][0]["key"], "cfg")  # server prefix is never exposed

    def test_client_cannot_escape_namespace_with_crafted_keys(self):
        self.svc.txn(ctx(self.b), txn_body(success=[PUT("secret", 1)]))
        for k in ("../globex/secret", "/t/globex/e/prod/s/site-a/w/ctrl/secret"):
            r = self.svc.range(ctx(self.a), {"schema": "cstate.range/1.1", "key": k})
            self.assertEqual(r["kvs"], [])
        r = self.svc.range(ctx(self.a), {"schema": "cstate.range/1.1", "key": "", "prefix": True})
        self.assertEqual(r["kvs"], [])

    def test_cross_namespace_target_requires_policy(self):
        with self.assertRaises(PermissionDenied):
            self.svc.range(ctx(self.a), {"schema": "cstate.range/1.1", "key": "x"}, target=NS_B)

    def test_watch_isolated(self):
        w = self.svc.watch(ctx(self.a), {"schema": "cstate.watch/1.1"})
        self.svc.txn(ctx(self.b), txn_body(success=[PUT("x", 1)]))
        self.svc.txn(ctx(self.a), txn_body(success=[PUT("y", 2)]))
        f = w.poll(0.2)
        self.assertEqual([e["key"] for e in f.events], ["y"])

    def test_per_identity_rate_limit(self):
        svc = make_service(Limits(rate_per_identity_rps=1, burst_per_identity=3), clock=FakeClock())
        for _ in range(3):
            svc.range(ctx(self.a), {"schema": "cstate.range/1.1", "key": "k"})
        with self.assertRaises(QuotaExceeded) as cm:
            svc.range(ctx(self.a), {"schema": "cstate.range/1.1", "key": "k"})
        self.assertIn("retry_after_s", cm.exception.to_wire()["details"])
        svc.range(ctx(self.b), {"schema": "cstate.range/1.1", "key": "k"})  # independent budget


class AuthzTest(unittest.TestCase):  # MC-023
    def setUp(self):
        self.svc = make_service()

    def test_deny_by_default(self):
        nobody = principal(NS_A, "unknown-role")
        with self.assertRaises(PermissionDenied):
            self.svc.range(ctx(nobody), {"schema": "cstate.range/1.1", "key": "k"})
        reader = principal(NS_A, "reader")
        with self.assertRaises(PermissionDenied):
            self.svc.txn(ctx(reader), txn_body(success=[PUT("k", 1)]))
        self.assertEqual(self.svc.store.revision, 0)  # denied before mutation
        denials = [e for e in self.svc.audit.entries() if e["class"] == "authz"]
        self.assertEqual(len(denials), 2)

    def test_admin_actions_require_admin_roles(self):
        w = principal(NS_A, "writer")
        for fn in (lambda: self.svc.freeze(ctx(w), "writes", "x"), lambda: self.svc.compact(ctx(w), {"schema": "cstate.compact/1.1", "revision": 0}),
                   lambda: self.svc.break_glass(ctx(w), True, "x"), lambda: self.svc.read_audit(ctx(w))):
            with self.assertRaises(PermissionDenied):
                fn()

    def test_policy_rollout_and_rollback(self):
        w = principal(NS_A, "writer")
        v = self.svc.set_policy(ctx(SEC), {"version": "p2", "rules": [{"roles": ["security-admin"], "actions": ["*"], "namespaces": ["*"]}]})
        self.assertEqual(v, "p2")
        with self.assertRaises(PermissionDenied):
            self.svc.range(ctx(w), {"schema": "cstate.range/1.1", "key": "k"})
        self.svc.rollback_policy(ctx(SEC))
        self.svc.range(ctx(w), {"schema": "cstate.range/1.1", "key": "k"})
        with self.assertRaises(InvalidArgument):
            self.svc.set_policy(ctx(SEC), {"version": "bad", "rules": [{"roles": ["x"], "actions": ["fly"]}]})

    def test_lease_ownership_enforced(self):
        a, a2 = principal(NS_A, "writer", name="one"), principal(NS_A, "writer", name="two")
        l = self.svc.lease_grant(ctx(a), {"schema": "cstate.lease_grant/1.1", "ttl": 10})
        with self.assertRaises(PermissionDenied):
            self.svc.lease_keepalive(ctx(a2), {"schema": "cstate.lease_keepalive/1.1", "id": l["id"]})
        with self.assertRaises(PermissionDenied):
            self.svc.txn(ctx(a2), txn_body(success=[PUT("k", 1, lease=l["id"])]))
        self.svc.txn(ctx(a), txn_body(success=[PUT("k", 1, lease=l["id"])]))


class ControlsTest(unittest.TestCase):  # MC-031
    def setUp(self):
        self.svc = make_service()
        self.w = principal(NS_A, "writer")

    def _write(self):
        return self.svc.txn(ctx(self.w), txn_body(success=[PUT("k", 1)]))

    def test_write_freeze_keeps_reads(self):
        self.svc.freeze(ctx(OP), "writes", "change window")
        with self.assertRaises(Frozen) as cm:
            self._write()
        self.assertEqual(cm.exception.to_wire()["details"]["reason"], "change window")
        self.svc.range(ctx(self.w), {"schema": "cstate.range/1.1", "key": "k"})
        self.assertEqual(self.svc.readiness()["status"], "degraded")
        self.svc.unfreeze(ctx(OP), "writes")
        self._write()

    def test_quarantine_preserves_state(self):
        self._write()
        self.svc.quarantine(ctx(SEC), "suspected disk fault")
        with self.assertRaises(Frozen):
            self.svc.range(ctx(self.w), {"schema": "cstate.range/1.1", "key": "k"})
        self.assertEqual(self.svc.store.get("/t/acme/e/prod/s/site-a/w/ctrl/k").value, 1)
        self.assertEqual(self.svc.readiness()["status"], "not_ready")
        self.assertIsNotNone(self.svc.diagnostics(ctx(OP)))  # forensic access remains

    def test_maintenance_exit_criteria(self):
        self.svc.maintenance(ctx(OP), True, "upgrade")
        with self.assertRaises(Frozen):
            self._write()
        self.svc.maintenance(ctx(OP), False)
        self._write()

    def test_break_glass_is_audited_and_disables_data_plane(self):
        self.svc.break_glass(ctx(SEC), True, "incident 42")
        with self.assertRaises(Frozen):
            self._write()
        with self.assertRaises(Frozen):
            self.svc.watch(ctx(self.w), {"schema": "cstate.watch/1.1"})
        self.svc.break_glass(ctx(SEC), False, "resolved")
        self._write()
        acts = [e["action"] for e in self.svc.audit.entries() if e["class"] == "admin"]
        self.assertIn("break_glass.disable", acts)
        self.assertIn("break_glass.enable", acts)

    def test_drain(self):
        w = self.svc.watch(ctx(self.w), {"schema": "cstate.watch/1.1"})
        self.assertEqual(self.svc.drain(ctx(OP), 0.1)["drained_watches"], 1)
        self.assertEqual(w.poll(0.1).error["code"], "CSTATE_DRAINING")
        self.assertEqual(self.svc.readiness()["status"], "not_ready")

    def test_failed_store_fails_closed(self):
        self.svc.store.fail_closed("test")
        with self.assertRaises(FailedClosed):
            self._write()
        self.assertEqual(self.svc.readiness()["status"], "failed")

    def test_replica_refuses_writes(self):
        self.svc.role = "replica"
        with self.assertRaises(Unavailable):
            self._write()


class DeadlineTest(unittest.TestCase):  # MC-026
    def test_expired_deadline_and_cancellation_do_not_execute(self):
        clock = FakeClock()
        svc = make_service(clock=clock)
        w = principal(NS_A, "writer")
        c = ctx(w, deadline=clock() - 1)
        with self.assertRaises(DeadlineExceeded):
            svc.txn(c, txn_body(success=[PUT("k", 1)]))
        tok = CancelToken()
        tok.cancel()
        with self.assertRaises(Cancelled):
            svc.txn(ctx(w, cancel=tok), txn_body(success=[PUT("k", 1)]))
        self.assertEqual(svc.store.revision, 0)
        with self.assertRaises(InvalidArgument):
            svc.txn(ctx(w), txn_body(success=[PUT("k", 1)], deadline_ms=0))

    def test_request_id_makes_retries_safe_and_is_scoped_per_identity(self):
        svc = make_service()
        a, b = principal(NS_A, "writer", name="a"), principal(NS_A, "writer", name="b")
        r1 = svc.txn(ctx(a, attempt=1), txn_body(success=[PUT("k", 1)], request_id="op-1"))
        r2 = svc.txn(ctx(a, attempt=2), txn_body(success=[PUT("k", 1)], request_id="op-1"))
        self.assertTrue(r2["replayed"])
        self.assertEqual(r1["revision"], r2["revision"])
        r3 = svc.txn(ctx(b), txn_body(success=[PUT("k", 1)], request_id="op-1"))
        self.assertFalse(r3["replayed"])
        self.assertEqual(svc.metrics.get("cstate_retries_total", op="txn"), 1.0)


class HealthTest(unittest.TestCase):  # MC-030
    def test_liveness_readiness_version(self):
        svc = make_service()
        self.assertEqual(svc.liveness()["status"], "ok")
        self.assertEqual(svc.readiness()["status"], "ready")
        svc.bootstrapped = False
        self.assertEqual(svc.readiness()["reasons"], ["not_bootstrapped"])
        v = svc.version()
        for k in ("version", "commit", "schema", "backend", "capabilities"):
            self.assertIn(k, v)

    def test_liveness_detects_stall(self):
        svc = make_service()
        import threading
        t = threading.Thread(target=lambda: (svc.store.lock.acquire(), time.sleep(3), svc.store.lock.release()))
        t.start()
        time.sleep(0.1)
        self.assertEqual(svc.liveness()["status"], "stalled")
        t.join()

    def test_diagnostics_protected(self):
        svc = make_service()
        with self.assertRaises(PermissionDenied):
            svc.diagnostics(ctx(principal(NS_A, "writer")))


class ObservabilityTest(unittest.TestCase):  # MC-032..036
    def test_metrics_catalog_and_exposition(self):
        svc = make_service()
        w = principal(NS_A, "writer")
        svc.txn(ctx(w), txn_body(success=[PUT("k", 1)]))
        svc.txn(ctx(w), txn_body(compare=[{"key": "k", "target": "VERSION", "op": "==", "operand": 7}]))
        svc.refresh_gauges()
        text = svc.metrics.render()
        for name in ("cstate_requests_total", "cstate_request_duration_seconds_bucket", "cstate_txn_conflicts_total 1.0",
                     "cstate_revision 1.0", "process_open_fds"):
            self.assertIn(name, text)
        self.assertNotIn("acme", text)  # no tenant data in labels

    def test_cardinality_cap(self):
        from inv05_current_control_state_system.observability import Metrics
        m = Metrics(max_series_per_metric=3)
        for i in range(10):
            m.inc("cstate_authz_denials_total", action=f"a{i}")
        self.assertEqual(len(m._values["cstate_authz_denials_total"]), 4)  # 3 + overflow

    def test_structured_log_schema_redaction_and_storm_control(self):
        buf = io.StringIO()
        clock = FakeClock()
        log = StructuredLogger(buf, per_event_rate=1, burst=5, clock=clock)
        for _ in range(50):
            log.log("INFO", "CS1100", "done", token="abc", request_id="r")
        lines = [json.loads(l) for l in buf.getvalue().splitlines()]
        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[0]["token"], "[REDACTED]")
        self.assertEqual(lines[0]["schema"], "cstate.log/1")
        clock.advance(10)
        log.log("INFO", "CS1100", "done")
        self.assertEqual(json.loads(buf.getvalue().splitlines()[-1])["suppressed_since_last"], 45)
        with self.assertRaises(ValueError):
            log.log("INFO", "CS0000", "unregistered")

    def test_trace_propagation_and_error_bias(self):
        tr = Tracer(ratio=0.0)
        tp = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
        with tr.span("outer", tp, op="txn", password="x") as sp:
            with tr.span("inner") as inner:
                pass
        self.assertEqual(sp.trace_id, "a" * 32)
        self.assertEqual(inner.parent_id, sp.span_id)
        self.assertNotIn("password", sp.attributes)
        try:
            with tr.span("unsampled-error"):
                raise ValueError()
        except ValueError:
            pass
        self.assertEqual(tr.finished[-1].status, "ERROR")  # retained despite ratio 0
        self.assertIsNone(Tracer.parse("00-" + "0" * 32 + "-" + "b" * 16 + "-01"))

    def test_operational_spans(self):
        svc = make_service()
        w = principal(NS_A, "writer")
        svc.txn(ctx(w), txn_body(success=[PUT("k", 1)]))
        svc.compact(ctx(OP), {"schema": "cstate.compact/1.1", "revision": 1})
        names = {s.name for s in svc.tracer.finished}
        for n in ("cstate.txn", "cstate.authz", "cstate.txn.evaluate", "cstate.compaction"):
            self.assertIn(n, names)
        comp = next(s for s in svc.tracer.finished if s.name == "cstate.compaction")
        parent = next(s for s in svc.tracer.finished if s.name == "cstate.compact")
        self.assertEqual(comp.parent_id, parent.span_id)

    def test_explain_record(self):
        svc = make_service()
        w = principal(NS_A, "writer")
        c = ctx(w)
        svc.txn(c, txn_body(compare=[{"key": "k", "target": "EXISTS", "op": "==", "operand": False}],
                            success=[PUT("k", {"password": "p"})]))
        e = svc.get_explanation(ctx(OP), c.request_id)
        self.assertEqual(e["schema"], "cstate.explain/1")
        self.assertEqual(e["branch"], "success")
        self.assertEqual(e["predicates"][0]["held"], True)
        self.assertEqual(e["policy_version"], "builtin-1")
        self.assertNotIn(w.subject, json.dumps(e))  # pseudonymous
        with self.assertRaises(PermissionDenied):
            svc.get_explanation(ctx(w), c.request_id)


class AuditTest(unittest.TestCase):  # MC-038
    def test_chain_verifies_and_detects_tampering(self):
        svc = make_service()
        w = principal(NS_A, "writer")
        for i in range(5):
            svc.txn(ctx(w), txn_body(success=[PUT("k", i)]))
        svc.freeze(ctx(OP), "writes", "x")
        entries = svc.read_audit(ctx(SEC))
        anchor = svc.audit.anchor()
        self.assertEqual(AuditLog.verify(entries, AUDIT_KEY, anchor), [])
        for e in entries:
            for f in ("ts", "actor", "action", "target", "outcome", "request_id", "revision", "source"):
                self.assertIn(f, e)
        bad = [dict(e) for e in entries]
        bad[2]["outcome"] = "forged"
        self.assertTrue(AuditLog.verify(bad, AUDIT_KEY))
        self.assertTrue(AuditLog.verify(entries[:2] + entries[3:], AUDIT_KEY))
        self.assertTrue(AuditLog.verify(entries[:-1], AUDIT_KEY, anchor))  # tail truncation vs anchor
        self.assertTrue(AuditLog.verify(entries, b"x" * 32))

    def test_file_backed_audit_resumes_chain(self):
        import os
        from _util import tmpdir
        p = os.path.join(tmpdir(), "audit.log")
        a = AuditLog(p, AUDIT_KEY)
        a.record("admin", "x", actor="me")
        a2 = AuditLog(p, AUDIT_KEY)
        a2.record("admin", "y", actor="me")
        self.assertEqual(AuditLog.verify(a2.entries(), AUDIT_KEY), [])
        self.assertEqual(os.stat(p).st_mode & 0o077, 0)


if __name__ == "__main__":
    unittest.main()
