"""Tests for effects (SG-04), identity (SG-02), errors (MC-14), config (MC-21..25),
resilience (MC-38/MC-07), telemetry (MC-48/49), status (MC-47) and the gate (MC-57/65)."""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import shutil
import tempfile
import unittest

from . import _path  # noqa: F401

from inv57_durable_execution import config as cfgmod
from inv57_durable_execution import effects, errors
from inv57_durable_execution.acceptance import absent_artifact_claims, evaluate, valid_waiver
from inv57_durable_execution.durable import ActivityInDoubt, Crash, NonDeterminism, Worker
from inv57_durable_execution.errors import (ConfigRejected, EffectUnresolved, InvalidIdentity,
                                            Overloaded, OwnershipConflict, Unauthorized)
from inv57_durable_execution.identity import WorkflowIdentity, bind_to_principal
from inv57_durable_execution.resilience import AdmissionController, CircuitBreaker, RetryPolicy
from inv57_durable_execution.sqlite_store import SQLiteBackend, SQLiteHistoryStore
from inv57_durable_execution.status import StatusSurface
from inv57_durable_execution.telemetry import Logger, Metrics, ObservedWorker, redact, traceparent

PKG = str(_path.ROOT / "inv57_durable_execution")


class Provider:
    """Fake provider with conditional create keyed by effect_id."""

    def __init__(self, dedupe=True, lookup=True):
        self.applied: dict[str, dict] = {}
        self.submits = 0
        self.dedupe, self.can_lookup = dedupe, lookup
        self.crash_after_apply = False

    def submit(self, eid, request):
        self.submits += 1
        if self.dedupe and eid in self.applied:
            return self.applied[eid]
        receipt = {"receipt": f"r-{len(self.applied)}", "eid": eid}
        self.applied[eid] = receipt
        if self.crash_after_apply:
            self.crash_after_apply = False
            raise Crash()                   # provider committed, response lost
        return receipt

    def lookup(self, eid):
        return self.applied.get(eid) if self.can_lookup else None


def ident(wf="wf-1", tenant="tenant-a"):
    return WorkflowIdentity(tenant, "test", "site-1", "orders", wf, "run-1")


class EffectTests(unittest.TestCase):
    def setUp(self):
        self.db = os.path.join(tempfile.mkdtemp(), "e.db")
        self.b = SQLiteBackend(self.db)

    def store(self):
        return SQLiteHistoryStore(self.b, ident(), self.b.acquire(ident(), "w", 60))

    def test_effect_id_stable_and_replay_does_not_resubmit(self):
        p = Provider()
        wf = lambda w: effects.run_effect(w, "charge", p, {"amt": 5}, effect_class="idempotent")
        r1 = Worker(self.store()).run(wf)
        r2 = Worker(self.store()).run(wf)
        self.assertEqual(r1, r2)
        self.assertEqual(p.submits, 1)

    def test_crash_after_provider_commit_reconciled_without_duplicate(self):
        for cls in ("idempotent", "lookup_only"):
            with self.subTest(cls=cls):
                self.b = SQLiteBackend(os.path.join(tempfile.mkdtemp(), "e.db"))
                p = Provider(dedupe=(cls == "idempotent"))
                p.crash_after_apply = True
                wf = lambda w: effects.run_effect(w, "charge", p, {"amt": 5}, effect_class=cls)
                with self.assertRaises(Crash):
                    Worker(self.store()).run(wf)
                w = Worker(self.store())
                with self.assertRaises(ActivityInDoubt):
                    w.run(wf)
                receipt = effects.reconcile_in_doubt(w, p)
                self.assertEqual(len(p.applied), 1)
                self.assertEqual(Worker(self.store()).run(wf), receipt)

    def test_unsafe_class_goes_to_operator(self):
        p = Provider(dedupe=False, lookup=False)
        p.crash_after_apply = True
        wf = lambda w: effects.run_effect(w, "fax", p, {}, effect_class="unsafe")
        with self.assertRaises(Crash):
            Worker(self.store()).run(wf)
        w = Worker(self.store())
        with self.assertRaises(ActivityInDoubt):
            w.run(wf)
        with self.assertRaises(EffectUnresolved):
            effects.reconcile_in_doubt(w, p)
        self.assertEqual(p.submits, 1)

    def test_request_change_is_nondeterminism(self):
        p = Provider()
        Worker(self.store()).run(lambda w: effects.run_effect(w, "c", p, {"amt": 5}, effect_class="idempotent"))
        with self.assertRaises(NonDeterminism):
            Worker(self.store()).run(lambda w: effects.run_effect(w, "c", p, {"amt": 6}, effect_class="idempotent"))

    def test_requires_persistent_store_and_valid_class(self):
        with self.assertRaises(TypeError):
            Worker().run(lambda w: effects.run_effect(w, "c", Provider(), {}, effect_class="idempotent"))
        with self.assertRaises(ValueError):
            Worker(self.store()).run(lambda w: effects.run_effect(w, "c", Provider(), {}, effect_class="x"))


class IdentityTests(unittest.TestCase):
    def test_rejects_bad_fields(self):
        for bad in ["", "a" * 129, "tén", "a|b", "../x", " a", "a\n", "-a"]:
            with self.subTest(bad=bad), self.assertRaises(InvalidIdentity):
                WorkflowIdentity(bad, "e", "s", "n", "w", "r")
        with self.assertRaises(InvalidIdentity):
            WorkflowIdentity(5, "e", "s", "n", "w", "r")

    def test_key_injective_and_roundtrip(self):
        a = WorkflowIdentity("ab", "c", "s", "n", "w", "r")
        b = WorkflowIdentity("a", "bc", "s", "n", "w", "r")
        self.assertNotEqual(a.key(), b.key())
        self.assertEqual(WorkflowIdentity.from_dict(a.to_dict()), a)
        with self.assertRaises(InvalidIdentity):
            WorkflowIdentity.from_dict({**a.to_dict(), "evil": 1})

    def test_next_run_and_generated(self):
        a = WorkflowIdentity.new(tenant="t", environment="e", site="s", namespace="n")
        b = a.next_run()
        self.assertEqual(a.workflow_id, b.workflow_id)
        self.assertNotEqual(a.run_id, b.run_id)
        self.assertEqual(len(a.log_ref()), 16)

    def test_spoofing_rejected(self):
        with self.assertRaises(Unauthorized):
            bind_to_principal(ident(tenant="tenant-b"), principal_tenant="tenant-a",
                              principal_environment="test")
        bind_to_principal(ident(), principal_tenant="tenant-a", principal_environment="test")


class ErrorModelTests(unittest.TestCase):
    def test_codes_unique_and_unsafe_detail_hidden(self):
        codes = [r["code"] for r in errors.registry()]
        self.assertEqual(len(codes), len(set(codes)))
        d = errors.describe(ActivityInDoubt("tenant secret-thing"))
        self.assertIsNone(d["detail"])
        self.assertEqual(d["code"], "INV57-E005")
        self.assertEqual(errors.describe(NonDeterminism("x"))["detail"], "x")
        self.assertEqual(errors.describe(KeyError("k"))["code"], "INV57-E999")


class ConfigTests(unittest.TestCase):
    def test_defaults_valid_and_secure(self):
        c = cfgmod.validate({})
        self.assertFalse(c["telemetry_payload_capture"])
        self.assertEqual(c["in_doubt_policy"], "halt")

    def test_rejections(self):
        cases = [{"nope": 1}, {"max_history_events": 1}, {"max_history_events": "5"},
                 {"in_doubt_policy": "retry"}, {"state_encryption_key_secret_ref": "hunter2"},
                 {"environment": "prod"}, {"retry_base_delay_seconds": 50.0, "retry_max_delay_seconds": 1.0},
                 {"max_history_events": True}]
        for c in cases:
            with self.subTest(c=c), self.assertRaises(ConfigRejected):
                cfgmod.validate(c)

    def test_overlays(self):
        c = cfgmod.merge_overlays({"environment": "staging"}, {"site": "eu-1"},
                                  {"retry_max_attempts": 5})
        self.assertEqual((c["site"], c["retry_max_attempts"]), ("eu-1", 5))
        with self.assertRaises(ConfigRejected):
            cfgmod.merge_overlays({}, {"environment": "prod"})

    def test_activation_ledger_and_rollback(self):
        d = tempfile.mkdtemp()
        m = cfgmod.ConfigManager(d)
        c1 = m.activate({"site": "a"}, actor="op", reason="init")
        m.activate({"site": "b"}, actor="op", reason="move")
        with self.assertRaises(ConfigRejected):
            m.activate({"site": "c", "bogus": 1}, actor="op", reason="bad")
        self.assertEqual(m.active()["site"], "b")        # rejected config never activated
        m.rollback(cfgmod.digest(c1), actor="op", reason="revert")
        self.assertEqual(m.active()["site"], "a")
        self.assertEqual([r["action"] for r in cfgmod.ConfigManager(d).ledger],
                         ["activate", "activate", "rollback"])
        with self.assertRaises(ConfigRejected):
            m.rollback("0" * 64, actor="op", reason="x")
        ledger = pathlib.Path(d, "config-ledger.jsonl")
        lines = ledger.read_text().splitlines()
        lines[0] = lines[0].replace('"init"', '"forged"')
        ledger.write_text("\n".join(lines) + "\n")
        with self.assertRaises(ConfigRejected):
            cfgmod.ConfigManager(d)


class ResilienceTests(unittest.TestCase):
    def test_retry_only_after_backoff_class(self):
        sleeps = []
        p = RetryPolicy(max_attempts=4, base=0.1, cap=1.0, seed=7, sleep=sleeps.append)
        n = {"i": 0}

        def flaky():
            n["i"] += 1
            if n["i"] < 3:
                raise OwnershipConflict("busy")
            return "ok"
        self.assertEqual(p.call(flaky), "ok")
        self.assertEqual(len(sleeps), 2)
        self.assertTrue(all(0 <= s <= 1.0 for s in sleeps))
        calls = []
        with self.assertRaises(ActivityInDoubt):
            p.call(lambda: calls.append(1) or (_ for _ in ()).throw(ActivityInDoubt("x")))
        self.assertEqual(len(calls), 1)                   # ambiguous outcomes never retried

    def test_retry_bounded(self):
        p = RetryPolicy(max_attempts=3, base=0.01, cap=0.02, seed=1, sleep=lambda s: None)
        calls = []
        with self.assertRaises(OwnershipConflict):
            p.call(lambda: calls.append(1) or (_ for _ in ()).throw(OwnershipConflict("x")))
        self.assertEqual(len(calls), 3)

    def test_circuit(self):
        t = {"now": 0.0}
        cb = CircuitBreaker(threshold=2, reset_seconds=10, clock=lambda: t["now"])
        for _ in range(2):
            with self.assertRaises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError()))
        self.assertEqual(cb.state, "open")
        with self.assertRaises(Overloaded):
            cb.call(lambda: 1)
        t["now"] = 11
        self.assertEqual(cb.state, "half_open")
        self.assertEqual(cb.call(lambda: 1), 1)
        self.assertEqual(cb.state, "closed")

    def test_admission_fairness(self):
        a = AdmissionController(max_inflight=3, per_tenant=2)
        a.acquire("t1"); a.acquire("t1")
        with self.assertRaises(Overloaded):
            a.acquire("t1")                                # noisy tenant capped
        a.acquire("t2")
        with self.assertRaises(Overloaded):
            a.acquire("t3")                                # global cap
        a.release("t1")
        a.acquire("t3")
        self.assertEqual(a.snapshot()["shed_total"], 2)
        with self.assertRaises(ValueError):
            a.release("t9")


class TelemetryStatusTests(unittest.TestCase):
    def test_metrics_logs_and_redaction(self):
        m, lg = Metrics(), Logger()
        ow = ObservedWorker(Worker(), m, lg, wf_ref="abc")
        ow.run(lambda w: w.activity("a", lambda: 1))
        with self.assertRaises(NonDeterminism):
            ow.run(lambda w: w.activity("b", lambda: 1))
        self.assertEqual(m.value("replays_total"), 2)
        self.assertEqual(m.value("nondeterminism_total"), 1)
        self.assertEqual(m.value("activities_executed_total"), 1)
        self.assertIn("inv57_replays_total 2", m.exposition())
        rec = json.loads(lg.records[-1])
        self.assertEqual(rec["code"], "INV57-E001")
        r = lg.log("info", "x", reason="password=hunter2 ok", tenant_payload="SECRET")
        self.assertNotIn("hunter2", json.dumps(r))
        self.assertNotIn("tenant_payload", r)
        self.assertEqual(redact("api_key: abc"), "api_key=[REDACTED]")
        self.assertRegex(traceparent("a" * 32, "b" * 16), r"^00-a{32}-b{16}-01$")

    def test_status_transitions_and_probe_cache(self):
        state = {"db": True, "n": 0}

        def db():
            state["n"] += 1
            return (state["db"], "ok" if state["db"] else "unreachable")
        t = {"now": 0.0}
        s = StatusSurface(version="4.3.0", config_digest="d", config_generation=1, environment="test",
                          site="s", probes={"config": lambda: (True, "ok"), "history_backend": db,
                                            "time_source": lambda: (True, "ok"),
                                            "broken": lambda: 1 / 0},
                          probe_ttl=5, clock=lambda: t["now"])
        self.assertTrue(s.readiness()["ready"])
        state["db"] = False
        self.assertTrue(s.readiness()["ready"])          # cached within TTL
        self.assertEqual(state["n"], 1)
        t["now"] = 6
        self.assertEqual(s.readiness()["reasons"], ["history_backend:unreachable"])
        doc = s.document()
        self.assertEqual(doc["mode"], "degraded")
        self.assertEqual(doc["dependencies"]["broken"]["code"], "probe_error:ZeroDivisionError")
        state["db"] = True
        t["now"] = 12
        self.assertEqual(s.document()["mode"], "ready")   # recovers without restart
        s.frozen_reason = "operator"
        self.assertEqual(s.document()["mode"], "frozen")
        self.assertFalse(s.readiness()["ready"])


class GateTests(unittest.TestCase):
    def test_package_gate_is_no_go_with_reasons(self):
        m = evaluate(PKG)
        self.assertEqual(m["verdict"], "NO_GO")
        self.assertTrue(any("unsigned" in b for b in m["blockers"]))
        self.assertEqual(sum(m["c_items"].values()), 100)

    def test_gate_rejects_unresolved_evidence_and_skipped_tests(self):
        d = tempfile.mkdtemp()
        root = os.path.join(d, "pkg")
        shutil.copytree(PKG, root, ignore=shutil.ignore_patterns("__pycache__"))
        with open(os.path.join(root, "STATUS_REGISTER.json")) as fh:
            reg = json.load(fh)
        reg["components"][0]["status"] = "CLOSED"
        reg["components"][0]["evidence"] = ["nope.py::x"]
        reg["components"][0]["tests"] = ["tests.fake::skipped_one"]
        with open(os.path.join(root, "STATUS_REGISTER.json"), "w") as fh:
            json.dump(reg, fh)
        with open(os.path.join(root, "test-report.json"), "w") as fh:
            json.dump({"tests": {"tests.fake::skipped_one": "skipped"}}, fh)
        m = evaluate(root)
        probs = [p["problem"] for p in m["problems"]]
        self.assertIn("evidence does not resolve: nope.py", probs)
        self.assertIn("test tests.fake::skipped_one is skipped", probs)
        # The swapped-in report drops every other test, so every component that claimed
        # IMPLEMENTED_LOCAL/CLOSED must be demoted too: nothing passes on stale evidence.
        reg_claims = sum(1 for c in reg["components"] if c["status"] in ("CLOSED", "IMPLEMENTED_LOCAL"))
        self.assertEqual(m["components"].get("EVIDENCE_FAILED"), reg_claims)
        self.assertEqual(m["verdict"], "NO_GO")

    def test_waivers(self):
        today = dt.date(2026, 9, 22)
        self.assertEqual(valid_waiver({"id": "W1", "target": "MC-01", "approver": "x", "reason": "r",
                                       "expires": "2026-09-21"}, today), (False, "expired"))
        self.assertEqual(valid_waiver({"id": "W1", "target": "MC-01", "reason": "r",
                                       "expires": "2027-01-01"}, today), (False, "missing approver"))
        self.assertTrue(valid_waiver({"id": "W1", "target": "MC-01", "approver": "x", "reason": "r",
                                      "expires": "2027-01-01"}, today)[0])

    def test_rg08_claim_check(self):
        d = tempfile.mkdtemp()
        pathlib.Path(d, "A.md").write_text("See MASTER.md for the spec.")
        pathlib.Path(d, "B.md").write_text("MASTER.md is absent and retired.")
        self.assertEqual(absent_artifact_claims(d), ["A.md"])
        self.assertEqual(absent_artifact_claims(PKG), [])


if __name__ == "__main__":
    unittest.main()
