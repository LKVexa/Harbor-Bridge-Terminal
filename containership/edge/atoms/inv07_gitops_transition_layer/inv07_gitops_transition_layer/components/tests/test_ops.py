"""Components 16 (retry), 17 (admission/breakers), 18 (offline), 20 (freeze),
28 (time), 31 (IaC migration), 35 (metrics), 36 (logging), 37 (tracing),
38 (explain) and the operator HTTP server."""
from __future__ import annotations

import json
import os
import random
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

import fixtures as F
from inv07_gitops_transition_layer.components import errors as E
from inv07_gitops_transition_layer.components.audit import AuditLedger
from inv07_gitops_transition_layer.components.authz import Authorizer, TokenAuthority
from inv07_gitops_transition_layer.components.migration import Partition, compare
from inv07_gitops_transition_layer.components.operations import FreezeRegistry, OfflinePolicy, TimeAuthority
from inv07_gitops_transition_layer.components.resilience import (AdmissionQueue, CircuitBreaker, IdempotencyCache,
                                                                  RetryBudget, RetryPolicy)
from inv07_gitops_transition_layer.components.server import serve
from inv07_gitops_transition_layer.components.telemetry import (EventLog, ExplainStore, Registry, Tracer,
                                                                 parse_traceparent)


class TestRetry(unittest.TestCase):
    def test_retries_only_retryable_with_full_jitter(self):
        sleeps, n = [], {"i": 0}

        def flaky():
            n["i"] += 1
            if n["i"] < 3:
                raise E.RepositoryUnavailable("down")
            return "ok"
        rp = RetryPolicy(max_attempts=5, base=1, cap=4, sleep=sleeps.append, rng=random.Random(1))
        self.assertEqual(rp.call(flaky), "ok")
        self.assertEqual(len(sleeps), 2)
        self.assertTrue(0 <= sleeps[0] <= 1 and 0 <= sleeps[1] <= 2)
        calls = {"i": 0}

        def trust():
            calls["i"] += 1
            raise E.Unsigned("no")
        with self.assertRaises(E.Unsigned):
            RetryPolicy(sleep=lambda s: None).call(trust)
        self.assertEqual(calls["i"], 1)

    def test_attempt_cap_deadline_cancel_budget(self):
        always = lambda: (_ for _ in ()).throw(E.RepositoryUnavailable("x"))  # noqa: E731
        rp = RetryPolicy(max_attempts=3, base=0, cap=0, sleep=lambda s: None)
        with self.assertRaises(E.RepositoryUnavailable):
            rp.call(always)
        self.assertEqual(rp.attempts_made, 3)
        t = {"now": 0.0}
        with self.assertRaises(E.DeadlineExceeded):
            RetryPolicy(base=10, cap=10, sleep=lambda s: None, clock=lambda: t["now"],
                        rng=random.Random(0)).call(always, deadline=0.5)
        ev = threading.Event()
        ev.set()
        with self.assertRaises(E.Cancelled):
            RetryPolicy().call(always, cancel=ev)
        with self.assertRaises(E.Throttled):
            RetryPolicy(budget=RetryBudget(0.0, 0.0), sleep=lambda s: None).call(always)

    def test_idempotency_replay_suppression(self):
        c, runs = IdempotencyCache(ttl=60), []
        self.assertEqual(c.run("k", lambda: runs.append(1) or "r"), ("r", False))
        self.assertEqual(c.run("k", lambda: runs.append(1) or "r2"), ("r", True))
        self.assertEqual(len(runs), 1)


class TestAdmission(unittest.TestCase):
    def test_breaker_states(self):
        t = {"now": 0.0}
        b = CircuitBreaker("git", threshold=2, cooldown=10, clock=lambda: t["now"])
        bad = lambda: (_ for _ in ()).throw(E.RepositoryUnavailable("x"))  # noqa: E731
        for _ in range(2):
            with self.assertRaises(E.RepositoryUnavailable):
                b.call(bad)
        self.assertEqual(b.state, "open")
        with self.assertRaises(E.CircuitOpen):
            b.call(lambda: 1)
        t["now"] = 11
        self.assertEqual(b.call(lambda: 1), 1)
        self.assertEqual(b.state, "closed")
        with self.assertRaises(E.Unsigned):     # terminal errors do not trip the breaker
            b.call(lambda: (_ for _ in ()).throw(E.Unsigned("x")))
        self.assertEqual(b.state, "closed")

    def test_bounded_fair_priority_queue_with_shedding(self):
        q = AdmissionQueue(3)
        q.put("a", "a1", 5)
        q.put("a", "a2", 5)
        q.put("b", "b1", 5)
        with self.assertRaises(E.Throttled):
            q.put("c", "c1", 1)                  # lowest priority refused when full
        q.put("c", "c9", 9)                      # higher priority sheds a low one
        self.assertEqual(q.shed, 1)
        order = [q.get()[0] for _ in range(3)]
        self.assertEqual(len(set(order)), 3)     # round-robin across tenants
        self.assertIsNone(q.get())
        rq = AdmissionQueue(100, tenant_rate=0.0001, tenant_burst=1)
        rq.put("t", 1)
        with self.assertRaises(E.Throttled):
            rq.put("t", 2)
        self.assertLessEqual(rq.saturation(), 1.0)


class TestOffline(unittest.TestCase):
    def test_modes(self):
        self.assertFalse(OfflinePolicy("fail_closed", max_cached_ref_age=60).decide(online=False, last_fetch_ok=0, now=1)["mutate"])
        ro = OfflinePolicy("read_only", max_cached_ref_age=60).decide(online=False, last_fetch_ok=0, now=1)
        self.assertEqual((ro["mutate"], ro["source"]), (False, "cache"))
        cb = OfflinePolicy("cache_backed", max_cached_ref_age=60, max_trust_age=100)
        self.assertTrue(cb.decide(online=False, last_fetch_ok=0, now=30, trust_loaded_at=0)["mutate"])
        self.assertFalse(cb.decide(online=False, last_fetch_ok=0, now=61, trust_loaded_at=0)["mutate"])
        self.assertFalse(cb.decide(online=False, last_fetch_ok=0, now=30, trust_loaded_at=None)["mutate"])
        with self.assertRaises(E.StaleRef):
            OfflinePolicy.reconnect_check("a" * 40, remote_contains=False)

    def _offline_env(self, mode):
        e = F.Env(offline_mode=mode)
        e.commit({"a.json": F.configmap()})
        c = e.controller()
        self.assertEqual(c.reconcile("refs/heads/main")["outcome"], "applied")
        c.retry.max_attempts, c.retry.sleep = 1, (lambda s: None)
        shutil.move(e.work, e.work + ".gone")
        return e, c

    def test_offline_fail_closed_end_to_end(self):
        e, c = self._offline_env("fail_closed")
        try:
            r = c.reconcile("refs/heads/main")
            self.assertEqual((r["outcome"], r["error"]["code"]), ("failed", "PKG-REPO-002"))
        finally:
            e.cleanup()

    def test_offline_read_only_reports_drift_without_mutating(self):
        e, c = self._offline_env("read_only")
        try:
            rid = list(c.target.list())[0]
            c.target.tamper(rid, lambda o: o["data"].__setitem__("mode", "hotfix"))
            r = c.reconcile("refs/heads/main")
            self.assertEqual(r["outcome"], "read_only")
            self.assertEqual(r["drift"], ["_/ConfigMap/team-a/settings"])
            self.assertEqual(c.target.get(rid)[0]["data"]["mode"], "hotfix")
            self.assertEqual(c.state.s["drift"][-1]["action"], "reported_only")
        finally:
            e.cleanup()


class TestFreeze(unittest.TestCase):
    def test_scopes_expiry_durability_override(self):
        d = tempfile.mkdtemp()
        try:
            t = {"now": 0.0}
            a = AuditLedger()
            f = FreezeRegistry(os.path.join(d, "f.json"), audit=a, clock=lambda: t["now"])
            f.freeze("ref", "refs/heads/main", reason="incident", actor="alice", until=100)
            with self.assertRaises(E.Quarantined):
                f.check(tenant="acme", ref="refs/heads/main", target="t")
            f.check(tenant="acme", ref="refs/heads/other", target="t")
            t["now"] = 101
            f.check(tenant="acme", ref="refs/heads/main", target="t")          # expired
            f.freeze("global", "*", reason="kill switch", actor="alice")
            f2 = FreezeRegistry(os.path.join(d, "f.json"), clock=lambda: t["now"])   # restart
            with self.assertRaises(E.Quarantined):
                f2.check(tenant="x", ref="y", target="z")
            with self.assertRaises(E.Quarantined):
                f2.release("global", "*", actor="alice")                        # global needs override
            f2.release("global", "*", actor="bob", override=True)
            f2.check(tenant="x", ref="y", target="z")
            self.assertGreaterEqual(len(a.entries()), 2)
        finally:
            shutil.rmtree(d)

    def test_frozen_controller_does_not_mutate(self):
        e = F.Env()
        try:
            e.commit({"a.json": F.configmap()})
            c = e.controller()
            c.freezes.freeze("tenant", "acme", reason="change freeze", actor="ops")
            r = c.reconcile("refs/heads/main")
            self.assertEqual((r["outcome"], r["error"]["code"]), ("frozen", "PKG-OPS-001"))
            self.assertEqual(c.target.list(), {})
            self.assertEqual(c.status()["health"], "blocked")
        finally:
            e.cleanup()


class TestTime(unittest.TestCase):
    def test_sync_age_and_jump_detection(self):
        s = {"wall": 1000.0, "sync": 1000.0, "mono": 0.0}
        ta = TimeAuthority(lambda: (s["wall"], s["sync"]), max_sync_age=60, max_jump=5, mono=lambda: s["mono"])
        self.assertEqual(ta.now(), 1000.0)
        s["wall"] += 10
        s["mono"] += 10
        s["sync"] = s["wall"]
        ta.now()
        s["wall"] += 3600                           # wall clock jumps an hour, monotonic 1s
        s["mono"] += 1
        s["sync"] = s["wall"]
        with self.assertRaises(E.TimeUntrusted):
            ta.now()
        self.assertEqual(ta.degraded_reason, "clock_jump")
        s["sync"] = s["wall"] - 120
        with self.assertRaises(E.TimeUntrusted):
            ta.now()

    def test_untrusted_time_blocks_mutation(self):
        e = F.Env(time_source=lambda: (F.NOW, F.NOW - 3600))
        try:
            e.commit({"a.json": F.configmap()})
            r = e.controller().reconcile("refs/heads/main")
            self.assertEqual((r["outcome"], r["error"]["code"]), ("refused", "PKG-TIME-001"))
        finally:
            e.cleanup()


class TestMigration(unittest.TestCase):
    def test_states_detector_cutover(self):
        a = AuditLedger()
        p = Partition("team-a", audit=a, required_clean_runs=2)
        with self.assertRaises(E.Conflict):
            p.transition("gitops_owned", actor="x")
        p.transition("dual_observe", actor="x")
        p.observe(compare({"r1": "d"}, {"r1": "e"}))
        self.assertEqual(p.clean_runs, 0)
        self.assertEqual(compare({"r1": "d"}, {"r1": "e"})["conflicts"], ["r1"])
        p.transition("dual_run", actor="x")
        self.assertTrue(p.may_mutate(True) and not p.may_mutate(False))
        for _ in range(2):
            p.observe(compare({"r1": "d"}, {"r1": "d"}))
        with self.assertRaises(E.Unauthorized):
            p.transition("gitops_owned", actor="x", approver="x")
        p.transition("gitops_owned", actor="x", approver="y", iac_digest="abc", first_oid="f" * 40)
        self.assertEqual([r["to"] for r in p.lineage], ["dual_observe", "dual_run", "gitops_owned"])
        self.assertEqual(len(a.entries()), 3)
        with self.assertRaises(E.Conflict):
            p.transition("iac_owned", actor="x")      # past the rollback boundary


class TestTelemetry(unittest.TestCase):
    def test_metrics_exposition(self):
        r = Registry()
        r.counter("inv07_syncs_total", "x")
        r.inc("inv07_syncs_total", outcome="applied")
        r.histogram("inv07_reconcile_seconds", "y", buckets=(0.1, 1))
        r.observe("inv07_reconcile_seconds", 0.5)
        txt = r.exposition()
        self.assertIn('inv07_syncs_total{outcome="applied"} 1', txt)
        self.assertIn('inv07_reconcile_seconds_bucket{le="1"} 1', txt)
        self.assertIn('inv07_reconcile_seconds_bucket{le="0.1"} 0', txt)
        with self.assertRaises(ValueError):
            r.counter("bad name")

    def test_structured_events_redaction_and_sink_failure(self):
        lines = []
        m = Registry()
        m.counter("inv07_log_drops_total")
        log = EventLog(lines.append, tenant="acme", site="s", metrics=m, max_bytes=400)
        rec = log.emit("PKG-X", "info", "hello", cid="c", token="abc", url="https://u:p@h/x")
        self.assertEqual(rec["fields"]["token"], "<redacted>")
        self.assertNotIn("u:p@", lines[0])
        log.emit("PKG-Y", "info", "big", blob="x" * 2000)
        self.assertLessEqual(len(lines[-1]), 400)
        self.assertIsNone(log.emit("PKG-Z", "debug", "filtered"))
        bad = EventLog(lambda l: 1 / 0, tenant="a", site="s", metrics=m)
        bad.emit("PKG-W", "error", "x")
        self.assertEqual(m.value("inv07_log_drops_total"), 1)

    def test_trace_propagation(self):
        spans = []
        tr = Tracer(sink=spans.append)
        tp = "00-" + "1" * 32 + "-" + "2" * 16 + "-01"
        with tr.span("root", traceparent=tp, secret_token="x") as root:
            with tr.span("child") as ch:
                pass
        self.assertEqual(root["trace_id"], "1" * 32)
        self.assertEqual(root["parent"], "2" * 16)
        self.assertEqual(ch["parent"], root["span_id"])
        self.assertEqual(root["attrs"]["secret_token"], "<redacted>")
        self.assertIsNone(parse_traceparent("00-" + "0" * 32 + "-" + "2" * 16 + "-01"))
        with self.assertRaises(ZeroDivisionError):
            with tr.span("boom"):
                1 / 0
        self.assertEqual(spans[-1]["status"], "error")

    def test_reconcile_spans_cover_pipeline(self):
        e = F.Env()
        try:
            e.commit({"a.json": F.configmap()})
            c = e.controller()
            c.reconcile("refs/heads/main", traceparent="00-" + "a" * 32 + "-" + "b" * 16 + "-01")
            names = {s["name"] for s in c.tracer.spans if s["trace_id"] == "a" * 32}
            for n in ("inv07.reconcile", "inv07.git.fetch", "inv07.verify.signature", "inv07.verify.provenance",
                      "inv07.policy", "inv07.live.read", "inv07.apply"):
                self.assertIn(n, names)
        finally:
            e.cleanup()


class TestExplain(unittest.TestCase):
    def test_durable_explanations_link_everything(self):
        e = F.Env()
        try:
            e.commit({"a.json": F.configmap()})
            c = e.controller()
            r = c.reconcile("refs/heads/main")
            ex = ExplainStore(os.path.join(c.tenancy.root, "state", "explain.jsonl")).get(r["decision_id"])  # reload
            self.assertEqual(ex["oid"], r["oid"])
            self.assertEqual(ex["signer"]["key_id"], "dev")
            self.assertEqual(ex["provenance"]["builder"], F.BUILDER)
            self.assertEqual(ex["policy"]["version"], 1)
            self.assertEqual(ex["actions"], r["actions"])
            self.assertTrue(ex["audit_seq"])
            self.assertEqual(ex["trace_id"], r["trace_id"])
        finally:
            e.cleanup()


class TestServer(unittest.TestCase):
    def test_routes_auth_and_errors(self):
        e = F.Env()
        try:
            e.commit({"a.json": F.configmap()})
            c = e.controller()
            ta = TokenAuthority({"k1": F.KEYS["token"][1]}, audience="inv07")
            import time as _t
            now = int(_t.time())
            tok = lambda roles, sub="alice": TokenAuthority.issue(F.KEYS["token"][0], "k1", {  # noqa: E731
                "sub": sub, "tenant": "acme", "roles": roles, "iat": now, "exp": now + 300, "aud": "inv07",
                "jti": sub + roles[0]})
            srv = serve(c, ta, Authorizer(tenant="acme", audit=c.audit), c.m)
            base = f"http://127.0.0.1:{srv.server_address[1]}"

            def call(path, token=None, method="GET", body=None):
                req = urllib.request.Request(base + path, method=method, data=body)
                if token:
                    req.add_header("Authorization", "Bearer " + token)
                try:
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        return resp.status, resp.read()
                except urllib.error.HTTPError as err:
                    return err.code, err.read()
            try:
                self.assertEqual(call("/healthz")[0], 200)
                self.assertEqual(call("/metrics")[0], 401)
                self.assertEqual(call("/v1/status")[0], 401)
                st, body = call("/v1/sync?ref=refs/heads/main", tok(["viewer"]), "POST", b"{}")
                self.assertEqual(st, 403)
                self.assertEqual(json.loads(body)["code"], "PKG-AUTH-002")
                st, body = call("/v1/sync?ref=refs/heads/main", tok(["operator"]), "POST", b"{}")
                self.assertEqual((st, json.loads(body)["outcome"]), (200, "applied"))
                did = json.loads(body)["decision_id"]
                self.assertEqual(json.loads(call("/v1/explain/" + did, tok(["viewer"]))[1])["decision_id"], did)
                st, body = call("/metrics", tok(["viewer"]))
                self.assertIn(b"inv07_syncs_total", body)
                self.assertEqual(call("/v1/freeze", tok(["operator"]), "POST", b"x" * 20000)[0], 413)
                st, _ = call("/v1/freeze", tok(["operator"]), "POST",
                             json.dumps({"scope": "tenant", "name": "acme", "reason": "r"}).encode())
                self.assertEqual(st, 200)
                self.assertEqual(call("/readyz", tok(["viewer"]))[0], 503)
            finally:
                srv.shutdown()
                srv.server_close()
        finally:
            e.cleanup()


if __name__ == "__main__":
    unittest.main()
