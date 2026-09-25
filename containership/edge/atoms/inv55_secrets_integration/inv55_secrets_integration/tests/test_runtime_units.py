"""Unit/contract tests for each runtime layer (checklist #6, #7, #9, #17-#23, #26-#30, #47, #52-#54, #59, #72-#75, #81)."""
from __future__ import annotations

import io
import json
import os
import pathlib
import random
import tempfile
import unittest

import _support as S
from inv55_secrets_integration.runtime import audit as A
from inv55_secrets_integration.runtime import config as C
from inv55_secrets_integration.runtime import lifecycle as L
from inv55_secrets_integration.runtime import telemetry as T
from inv55_secrets_integration.runtime.authz import ScopePolicy
from inv55_secrets_integration.runtime.cache import LeaseCache
from inv55_secrets_integration.runtime.errors import ERROR_CATALOG, INV55Error, Outcome
from inv55_secrets_integration.runtime.identity import HmacTokenVerifier, Principal
from inv55_secrets_integration.runtime.negotiation import negotiate
from inv55_secrets_integration.runtime.provider import ProviderSecret
from inv55_secrets_integration.runtime.quarantine import Quarantine
from inv55_secrets_integration.runtime.resilience import Bulkhead, CircuitBreaker, Deadline, TokenBucketQuota, retry
from inv55_secrets_integration.runtime.wire import SCHEMAS, validate
from inv55_secrets_integration.reference import _SecretValue


class ErrorModel(unittest.TestCase):
    def test_every_code_serialises_against_error_schema(self):
        for code in ERROR_CATALOG:
            body = INV55Error(code, "operator detail with PLAINTEXT").to_wire("req-1")
            self.assertEqual(validate(body, SCHEMAS["error"]), [], code)
            self.assertNotIn("PLAINTEXT", json.dumps(body))

    def test_unknown_code_collapses_to_internal(self):
        self.assertEqual(INV55Error("NOPE").code, "INV55-E-INTERNAL")

    def test_only_retryable_codes_have_retry_hint(self):
        for s in ERROR_CATALOG.values():
            self.assertEqual(s.retry_after_ms is not None, s.outcome is Outcome.RETRYABLE, s.code)


class Lifecycle(unittest.TestCase):
    def test_legal_and_illegal_transitions(self):
        m = L.StateMachine(L.LEASE, "ISSUED")
        m.to("ACTIVE"); m.to("REVOKED")
        self.assertTrue(m.terminal)
        with self.assertRaises(L.IllegalTransition):
            m.to("ACTIVE")

    def test_every_state_reachable_from_initial(self):
        for name, (table, init) in {"lease": (L.LEASE, "ISSUED"), "version": (L.VERSION, "STAGED"),
                                    "provider": (L.PROVIDER, "UNINITIALISED")}.items():
            seen, todo = {init}, [init]
            while todo:
                for n in table[todo.pop()]:
                    if n not in seen:
                        seen.add(n); todo.append(n)
            self.assertEqual(seen, set(table), name)


class Identity(unittest.TestCase):
    def setUp(self):
        self.v = HmacTokenVerifier({"k1": "key-one-0123456789"}, issuer="iss", audience="aud")
        self.base = {"iss": "iss", "aud": "aud", "nbf": 100, "exp": 700, "sub": "spiffe://x.org/tenant/t1/workload/app1", "roles": ["secret-consumer"]}

    def ok(self, **o):
        return self.v.verify(self.v.issue({**self.base, **o}, "k1"), 200)

    def reason(self, tok, now=200):
        with self.assertRaises(INV55Error) as c:
            self.v.verify(tok, now)
        self.assertEqual(c.exception.code, "INV55-E-UNAUTHENTICATED")
        return c.exception.reason

    def test_valid(self):
        p = self.ok()
        self.assertEqual((p.tenant, p.app), ("t1", "app1"))

    def test_negative_matrix(self):
        good = self.v.issue(self.base, "k1")
        body, sig = good.split(".")
        cases = {
            "malformed_token": ["", "a.b.c", "x" * 5000, "!!!.???"],
            "bad_signature": [body + "." + sig[:-2] + ("AA" if sig[-2:] != "AA" else "BB")],
            "wrong_issuer": [self.v.issue({**self.base, "iss": "evil"}, "k1")],
            "wrong_audience": [self.v.issue({**self.base, "aud": "other"}, "k1")],
            "lifetime_too_long": [self.v.issue({**self.base, "exp": 100 + 7200}, "k1")],
            "bad_subject": [self.v.issue({**self.base, "sub": "root"}, "k1")],
            "bad_roles": [self.v.issue({**self.base, "roles": "admin"}, "k1")],
            "missing_time_claims": [self.v.issue({k: v for k, v in self.base.items() if k != "exp"}, "k1")],
        }
        for want, toks in cases.items():
            for t in toks:
                self.assertEqual(self.reason(t), want, (want, t[:20]))
        self.assertEqual(self.reason(good, now=5000), "expired")
        self.assertEqual(self.reason(good, now=0), "not_yet_valid")

    def test_unknown_key(self):
        other = HmacTokenVerifier({"k9": "zzz"}, issuer="iss", audience="aud")
        self.assertEqual(self.reason(other.issue(self.base, "k9")), "unknown_key")


class Authz(unittest.TestCase):
    def p(self, t="t1", a="app", roles=("secret-consumer",)):
        return Principal(f"spiffe://x/tenant/{t}/workload/{a}", t, a, frozenset(roles), "k")

    def test_deny_by_default_and_reasons(self):
        pol = ScopePolicy()
        self.assertEqual(pol.decide(self.p(), "resolve", "t1/s").reason, "not_in_scope")
        pol.set_scope("t1/s", [("t1", "app")])
        self.assertTrue(pol.decide(self.p(), "resolve", "t1/s").allowed)
        self.assertEqual(pol.decide(self.p(roles=()), "resolve", "t1/s").reason, "role_lacks_verb")
        self.assertEqual(pol.decide(self.p(t="t2"), "resolve", "t1/s").reason, "cross_tenant")
        self.assertEqual(pol.decide(self.p(roles=("secret-consumer",)), "rotate", "t1/s").reason, "role_lacks_verb")

    def test_scope_cannot_cross_tenant_and_digest_moves(self):
        pol = ScopePolicy()
        d0 = pol.digest
        with self.assertRaises(ValueError):
            pol.set_scope("t1/s", [("t2", "app")])
        self.assertEqual(pol.digest, d0)
        pol.set_scope("t1/s", [("t1", "app")])
        self.assertNotEqual(pol.digest, d0)


class Resilience(unittest.TestCase):
    def test_retry_only_retryable_and_bounded(self):
        calls = []
        def f(rem):
            calls.append(1); raise INV55Error("INV55-E-PROVIDER-UNAVAILABLE")
        with self.assertRaises(INV55Error):
            retry(f, attempts=4, base_s=0, deadline=Deadline.after(5), sleep=lambda s: None)
        self.assertEqual(len(calls), 4)
        calls.clear()
        def g(rem):
            calls.append(1); raise INV55Error("INV55-E-DENIED")
        with self.assertRaises(INV55Error):
            retry(g, attempts=4, deadline=Deadline.after(5), sleep=lambda s: None)
        self.assertEqual(len(calls), 1)

    def test_retry_respects_deadline(self):
        clk = S.Clock(0)
        dl = Deadline(1.0, clk)
        def f(rem):
            clk.t += 0.6; raise INV55Error("INV55-E-PROVIDER-UNAVAILABLE")
        with self.assertRaises(INV55Error) as c:
            retry(f, attempts=10, base_s=0, deadline=dl, sleep=lambda s: None)
        self.assertIn(c.exception.code, ("INV55-E-DEADLINE", "INV55-E-PROVIDER-UNAVAILABLE"))

    def test_jitter_within_cap(self):
        rng = random.Random(7)
        delays = []
        def f(rem): raise INV55Error("INV55-E-PROVIDER-UNAVAILABLE")
        with self.assertRaises(INV55Error):
            retry(f, attempts=6, base_s=0.1, cap_s=0.3, deadline=Deadline.after(100), rng=rng, sleep=delays.append)
        self.assertEqual(len(delays), 5)
        self.assertTrue(all(0 <= d <= 0.3 for d in delays))

    def test_breaker_open_half_open_close(self):
        clk = S.Clock(0)
        b = CircuitBreaker(threshold=2, cooldown_s=5, clock=clk)
        def bad(): raise INV55Error("INV55-E-PROVIDER-UNAVAILABLE")
        for _ in range(2):
            with self.assertRaises(INV55Error):
                b.call(bad)
        self.assertEqual(b.state, "open")
        with self.assertRaises(INV55Error) as c:
            b.call(lambda: 1)
        self.assertEqual(c.exception.code, "INV55-E-CIRCUIT-OPEN")
        clk.t = 6
        self.assertEqual(b.call(lambda: 1), 1)
        self.assertEqual(b.state, "closed")

    def test_breaker_ignores_denials(self):
        b = CircuitBreaker(threshold=1)
        with self.assertRaises(INV55Error):
            b.call(lambda: (_ for _ in ()).throw(INV55Error("INV55-E-DENIED")))
        self.assertEqual(b.state, "closed")

    def test_bulkhead_refuses_when_full(self):
        bh = Bulkhead(1)
        with bh:
            with self.assertRaises(INV55Error) as c:
                with bh:
                    pass
        self.assertEqual(c.exception.code, "INV55-E-OVERLOADED")

    def test_quota_refill_and_key_cap(self):
        clk = S.Clock(0)
        q = TokenBucketQuota(1.0, 2, max_keys=2, clock=clk)
        q.take(("a",)); q.take(("a",))
        with self.assertRaises(INV55Error):
            q.take(("a",))
        clk.t = 1.01
        q.take(("a",))
        q.take(("b",))
        with self.assertRaises(INV55Error) as c:
            q.take(("c",))
        self.assertEqual(c.exception.code, "INV55-E-OVERLOADED")


class Cache(unittest.TestCase):
    def s(self, v=1):
        return ProviderSecret("t/s", v, _SecretValue("x"))

    def test_fresh_stale_offline_deny(self):
        c = LeaseCache(fresh_s=5, max_stale_s=10, allow_stale=False)
        c.put(self.s(), 0)
        self.assertIsNotNone(c.get_fresh("t/s", 4))
        self.assertIsNone(c.get_fresh("t/s", 6))
        self.assertIsNone(c.get_stale("t/s", 6))
        c2 = LeaseCache(fresh_s=5, max_stale_s=10, allow_stale=True)
        c2.put(self.s(), 0)
        self.assertIsNotNone(c2.get_stale("t/s", 9))
        self.assertIsNone(c2.get_stale("t/s", 11))

    def test_bounded_lru(self):
        c = LeaseCache(fresh_s=5, max_stale_s=5, allow_stale=False, max_entries=3)
        for i in range(10):
            c.put(ProviderSecret(f"t/{i}", 1, _SecretValue("x")), 0)
        self.assertEqual(len(c), 3)

    def test_invalid_policy(self):
        with self.assertRaises(ValueError):
            LeaseCache(fresh_s=5, max_stale_s=1, allow_stale=True)


class Audit(unittest.TestCase):
    def test_chain_file_roundtrip_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "audit.jsonl")
            log = A.AuditLog(p, seal_key="audit-seal-key")
            for i in range(5):
                log.append(op="resolve", tenant="t", app="a", secret_ref=f"t/s{i}", allowed=True, reason="granted", at=i)
            head = log.head
            ok, info = A.verify_file(p, seal_key="audit-seal-key", expected_head=head)
            self.assertTrue(ok, info)
            lines = pathlib.Path(p).read_text().splitlines()
            # edit
            bad = json.loads(lines[2]); bad["allowed"] = False
            pathlib.Path(p).write_text("\n".join(lines[:2] + [json.dumps(bad)] + lines[3:]) + "\n")
            self.assertEqual(A.verify_file(p, seal_key="audit-seal-key")[1]["error"], "hash_mismatch")
            # delete a middle line
            pathlib.Path(p).write_text("\n".join(lines[:2] + lines[3:]) + "\n")
            self.assertFalse(A.verify_file(p)[0])
            # truncate tail - only detectable with the external head
            pathlib.Path(p).write_text("\n".join(lines[:4]) + "\n")
            self.assertTrue(A.verify_file(p)[0])
            self.assertEqual(A.verify_file(p, expected_head=head)[1]["error"], "head_mismatch_truncation_or_fork")
            # wrong seal key
            pathlib.Path(p).write_text("\n".join(lines) + "\n")
            self.assertEqual(A.verify_file(p, seal_key="other")[1]["error"], "bad_seal")

    def test_refuses_values_and_unknown_fields(self):
        log = A.AuditLog()
        with self.assertRaises(ValueError):
            log.append(op="x", detail=_SecretValue("v"))
        with self.assertRaises(ValueError):
            log.append(op="x", value="v")

    def test_reopen_continues_chain_and_refuses_corrupt(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.jsonl")
            A.AuditLog(p).append(op="a", at=1)
            l2 = A.AuditLog(p)
            l2.append(op="b", at=2)
            self.assertEqual(A.verify_file(p)[1]["count"], 2)
            pathlib.Path(p).write_text(pathlib.Path(p).read_text() + "garbage\n")
            with self.assertRaises(RuntimeError):
                A.AuditLog(p)


class Telemetry(unittest.TestCase):
    def test_prometheus_export_and_cardinality_cap(self):
        m = T.Metrics(max_series=3)
        for i in range(10):
            m.inc("requests", tenant=f"t{i}")
        self.assertEqual(m.dropped, 7)
        m2 = T.Metrics()
        m2.observe_ms("lat", 0.3, op="R"); m2.observe_ms("lat", 7, op="R")
        text = m2.prometheus()
        self.assertIn('inv55_lat_ms_bucket{op="R",le="+Inf"} 2', text)
        self.assertEqual(m2.quantile_ms("lat", 0.5, op="R"), 0.5)

    def test_logger_scrubs_and_refuses_secret(self):
        buf = io.StringIO()
        lg = T.JsonLogger(buf)
        lg.log("info", "x", note="password=hunter2 and hvs.ABCDEFGHIJKLMNOPQRSTUVWX")
        self.assertNotIn("hunter2", buf.getvalue())
        self.assertNotIn("hvs.ABCDEF", buf.getvalue())
        with self.assertRaises(ValueError):
            lg.log("info", "x", v=_SecretValue("s"))

    def test_trace_spans(self):
        tr = T.Tracer()
        tid = tr.new_trace_id()
        with tr.span("a", tid):
            pass
        self.assertEqual(tr.spans[0]["trace_id"], tid)
        self.assertRegex(T.Tracer.traceparent(tid, "0" * 16), r"^00-[0-9a-f]{32}-0{16}-01$")


class Config(unittest.TestCase):
    def test_valid_base(self):
        self.assertEqual(C.check(S.cfg()), [])

    def test_negative_cases(self):
        bad = {
            "insecure outside test": S.cfg(environment="staging", provider={"kind": "vault-kv2", "address": "http://127.0.0.1:1", "allow_insecure_loopback": True}),
            "memory in prod": S.cfg(environment="production"),
            "credential in config": S.cfg(provider={"kind": "memory", "namespace": "token=abc123"}),
            "ttl > max": S.cfg(lease={"ttl_s": 500, "max_ttl_s": 100}),
            "unknown key": {**S.cfg(), "debug": True},
            "stale in prod": S.cfg(environment="production", provider={"kind": "vault-kv2", "address": "https://v"}, cache={"allow_stale": True}),
        }
        for label, doc in bad.items():
            self.assertTrue(C.check(doc), label)

    def test_overlay_locked_keys(self):
        with self.assertRaises(INV55Error):
            C.deep_merge(S.cfg(), {"provider": {"kind": "vault-kv2"}})
        merged = C.deep_merge(S.cfg(), {"lease": {"ttl_s": 30}, "site": "edge-1"})
        self.assertEqual(merged["lease"], {"ttl_s": 30, "max_ttl_s": 300})

    def test_transactional_activation_and_rollback(self):
        cc = C.ConfigController(clock=lambda: 0)
        cc.stage(S.cfg(), author="alice", source="git:abc")
        d1 = cc.commit(approved_by="bob", require_approval=True)
        with self.assertRaises(INV55Error):
            cc.stage(S.cfg(lease={"ttl_s": 999, "max_ttl_s": 10}), author="alice", source="git:bad")
        self.assertEqual(cc.active_digest, d1)          # invalid config never activated
        cc.stage(S.cfg(), {"lease": {"ttl_s": 30}}, author="alice", source="git:def")
        with self.assertRaises(INV55Error):
            cc.commit(approved_by="alice", require_approval=True)   # self-approval
        with self.assertRaises(INV55Error):
            cc.commit(approved_by=None, require_approval=True)
        d2 = cc.commit(approved_by="bob", require_approval=True)
        self.assertNotEqual(d1, d2)
        self.assertEqual(cc.rollback(actor="op", reason="bad canary"), d1)
        self.assertEqual([p["event"] for p in cc.provenance], ["stage", "commit", "stage", "stage", "commit", "rollback"])


class WireAndNegotiation(unittest.TestCase):
    def test_negotiation(self):
        self.assertEqual(negotiate("RESOLVE", ["PK_SECRET_RESOLVE/1", "PK_SECRET_RESOLVE/9"]), "PK_SECRET_RESOLVE/1")
        for offered in ([], ["PK_SECRET_RESOLVE/2"], ["PK_SECRET_ROTATE/1"], None, [1]):
            with self.assertRaises(INV55Error):
                negotiate("RESOLVE", offered)

    def test_schema_files_match_code(self):
        from inv55_secrets_integration.runtime.wire import SCHEMA_DIR
        for k, s in SCHEMAS.items():
            f = SCHEMA_DIR / f"{k.replace('/', '_')}.schema.json"
            self.assertTrue(f.exists(), f)
            on_disk = json.loads(f.read_text()); on_disk.pop("$schema")
            self.assertEqual(on_disk, json.loads(json.dumps(s)), k)

    def test_fixtures_conform(self):
        import pathlib
        fx = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wire"
        files = sorted(fx.glob("*.json"))
        self.assertGreaterEqual(len(files), 8)
        for f in files:
            d = json.loads(f.read_text())
            errs = validate(d["message"], SCHEMAS[d["schema"]])
            self.assertEqual(bool(errs), not d["valid"], (f.name, errs))


class QuarantineTest(unittest.TestCase):
    def test_scopes(self):
        q = Quarantine()
        q.freeze("secret:t/s", "incident")
        with self.assertRaises(INV55Error):
            q.check(tenant="t", secret="t/s", op="resolve")
        q.check(tenant="t", secret="t/other", op="resolve")
        q.unfreeze("secret:t/s")
        q.check(tenant="t", secret="t/s", op="resolve")
        with self.assertRaises(ValueError):
            q.freeze("everything", "x")


if __name__ == "__main__":
    unittest.main()
