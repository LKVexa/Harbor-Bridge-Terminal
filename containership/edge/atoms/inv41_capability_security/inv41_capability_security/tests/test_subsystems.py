"""Audit, configuration, identity, broker/telemetry, resilience and fault-injection tests
(Sections 8, 11, 12, 13, 14, 16, 17)."""
from __future__ import annotations

import copy
import json
import random
import threading
import time
import unittest

from _common import rng

from inv41_capability_security import config as cfgmod
from inv41_capability_security import errors
from inv41_capability_security.audit import AuditChain, AuditRejected, AuditUnavailable, verify_chain
from inv41_capability_security.broker import Broker, IllegalTransition
from inv41_capability_security.capabilities import Authority, Forged, Membrane, Revoked, Widening
from inv41_capability_security.identity import HmacTokenAdapter, PrincipalBinder, make_token
from inv41_capability_security.resilience import Admission, CircuitBreaker, FaultInjector, RetryBudget, retry
from inv41_capability_security.telemetry import (
    CardinalityExceeded, Metrics, StructuredLogger, parse_traceparent, redact,
)

KEY = b"a" * 32


class AuditTest(unittest.TestCase):
    def _chain(self, n=6):
        c = AuditChain(KEY)
        for i in range(n):
            c.emit("grant", outcome="success", reason="ALLOW", resource=f"r{i}")
        return c

    def test_AU001_valid_chain_verifies(self):
        c = self._chain()
        v = verify_chain(c.exported, KEY, expected_head=c.head, expected_count=len(c.exported))
        self.assertTrue(v["valid"], v)

    def test_AU002_tamper_modify_delete_dup_reorder_truncate(self):
        c = self._chain()
        ev = c.exported
        cases = {
            "modified": [dict(e) for e in ev],
            "deleted": ev[:2] + ev[3:],
            "duplicated": ev[:3] + [ev[2]] + ev[3:],
            "reordered": ev[:2] + [ev[3], ev[2]] + ev[4:],
            "truncated": ev[:-1],
        }
        cases["modified"][3] = dict(cases["modified"][3], outcome="denied")
        for name, events in cases.items():
            v = verify_chain(events, KEY, expected_head=c.head)
            self.assertFalse(v["valid"], name)
        self.assertFalse(verify_chain(ev, b"b" * 32)["valid"], "wrong key")

    def test_AU006_verifier_checks_prev_link_independently(self):
        # A key-holding insider re-seals an event whose prev link is wrong but seq is intact:
        # only the prev-link check can catch it (the other checks are satisfied by construction).
        import hashlib, hmac as _h
        from inv41_capability_security.audit import canonical
        c = self._chain(3)
        ev = [dict(e) for e in c.exported]
        body = {k: v for k, v in ev[2].items() if k not in ("digest", "mac")}
        body["prev"] = "f" * 64
        d = hashlib.sha256(canonical(body)).hexdigest()
        ev[2] = dict(body, digest=d, mac=_h.new(KEY, d.encode(), hashlib.sha256).hexdigest())
        v = verify_chain(ev, KEY)
        self.assertFalse(v["valid"])
        self.assertTrue(any("prev link" in e for e in v["errors"]), v["errors"])

    def test_AU003_forbidden_and_tokenlike_fields_refused(self):
        c = AuditChain(KEY)
        with self.assertRaises(AuditRejected):
            c.emit("grant", outcome="success", reason="x", token="abc")
        with self.assertRaises(AuditRejected):
            c.emit("grant", outcome="success", reason="x", note="Zm9vYmFyYmF6cXV4cXV1eHF1dXhxdXV4cXV1eHF1dXg")
        with self.assertRaises(AuditRejected):
            c.emit("not.a.type", outcome="success", reason="x")

    def test_AU004_buffer_outage_is_bounded_and_mandatory_fails_closed(self):
        sink_up = {"up": False}

        def sink(e):
            if not sink_up["up"]:
                raise ConnectionError("collector down")

        c = AuditChain(KEY, sink=sink, max_buffer=5)
        for _ in range(4):
            c.emit("grant", outcome="success", reason="x")
        with self.assertRaises(AuditUnavailable):
            c.emit("grant", outcome="success", reason="x")
        self.assertLessEqual(c.buffered, 5)
        sink_up["up"] = True
        c.flush()
        self.assertEqual(c.buffered, 0)
        self.assertTrue(verify_chain(c.exported, KEY, expected_head=c.head)["valid"])

    def test_AU005_restart_links_new_segment(self):
        c1 = self._chain(2)
        c2 = AuditChain(KEY, previous_head=c1.head)
        self.assertEqual(c2.exported[0]["fields"]["previous_segment_head"], c1.head)
        self.assertTrue(verify_chain(c2.exported, KEY)["valid"])


def _signed(version=2, **over):
    base = {"schema": "INV41_CONFIG/1", "config_version": version, "profile": "test", "policy": {"store": ["read", "write"]},
            "limits": {"max_concurrent_checks": 4},
            "provenance": {"author": "ci", "source": "repo@abc", "change_request": "CR-7", "created": "2026-09-22T00:00:00Z"}}
    base.update(over)
    return cfgmod.sign(base, KEY, "k1")


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.store = cfgmod.ConfigStore(trusted_keys={"k1": KEY})
        self.store.activate(_signed(1))

    def test_CF001_rejects_bad_configs(self):
        bad = [
            dict(_signed(2), policy={"store": ["read"]}),               # digest mismatch after edit
            {k: v for k, v in _signed(2).items() if k != "signature"},  # unsigned
            cfgmod.sign(dict(_signed(2), signature=None), b"z" * 32, "k9"),  # untrusted signer
            _signed(1),                                                 # stale/rollback attack
            cfgmod.sign({"schema": "INV41_CONFIG/1", "config_version": 3, "profile": "test", "policy": {"s": ["r"] * 2},
                         "provenance": {"author": "a", "source": "s", "change_request": "c", "created": "t"}}, KEY, "k1"),
            _signed(2, profile="mars"),
            dict(_signed(2), signature=dict(_signed(2)["signature"], mac="0" * 64)),  # trusted key id, forged MAC
        ]
        for i, c in enumerate(bad):
            with self.assertRaises((errors.ConfigRejected, errors.StaleState), msg=i):
                self.store.activate(c)
        self.assertEqual(self.store.active.config["config_version"], 1)

    def test_CF002_revoked_key_rejected(self):
        self.store.revoke_key("k1")
        with self.assertRaises(errors.ConfigRejected):
            self.store.activate(_signed(2))

    def test_CF003_crash_at_every_phase_leaves_no_partial_state(self):
        before = self.store.active
        for phase in ("preflight", "stage", "commit"):
            def hook(p, phase=phase):
                if p == phase:
                    raise RuntimeError(f"crash@{p}")
            self.store.fault_hook = hook
            with self.assertRaises(RuntimeError):
                self.store.activate(_signed(2))
            self.assertIs(self.store.active, before, phase)
        self.store.fault_hook = None
        self.store.activate(_signed(2))
        self.assertEqual(self.store.active.config["config_version"], 2)

    def test_CF004_concurrent_reads_see_complete_snapshots(self):
        stop = threading.Event()
        bad = []

        def reader():
            while not stop.is_set():
                a = self.store.active
                if a.authority.policy.keys() != {r for r in a.config["policy"]}:
                    bad.append(a)

        ts = [threading.Thread(target=reader) for _ in range(4)]
        for t in ts:
            t.start()
        for v in range(2, 40):
            self.store.activate(_signed(v, policy={f"res{v}": ["read"]}))
        stop.set()
        for t in ts:
            t.join()
        self.assertEqual(bad, [])

    def test_CF005_rollback_requires_operator_and_never_resurrects(self):
        old_auth = self.store.active.authority
        m = Membrane("cfg")
        ref = m.wrap(old_auth.grant("store"))
        m.revoke()
        self.store.activate(_signed(2))
        with self.assertRaises(errors.ConfigRejected):
            self.store.rollback(operator_authorized=False)
        rb = self.store.rollback(operator_authorized=True)
        self.assertEqual(rb.config["config_version"], 1)
        self.assertIsNot(rb.authority, old_auth)
        with self.assertRaises(Revoked):
            ref.invoke("read")
        with self.assertRaises(Exception):
            rb.authority.bind_holder("h", {"s": ref})
        self.assertIn("config.rollback", [e[0] for e in self.store.events])

    def test_CF006_migration_v0_to_v1(self):
        v0 = {"schema": "INV41_CONFIG/0", "config_version": 5, "profile": "test", "grants": {"q": ["send"]},
              "provenance": {"author": "a", "source": "s", "change_request": "c", "created": "t"}}
        self.store.activate(cfgmod.sign(v0, KEY, "k1"))
        self.assertEqual(self.store.active.config["schema"], "INV41_CONFIG/1")
        self.assertIn("q", self.store.active.authority.policy)

    def test_CF007_default_profiles_are_valid(self):
        for p in cfgmod.PROFILES:
            cfgmod.validate(cfgmod.default_profile(p))

    def test_CF008_canonical_digest_is_order_independent(self):
        a = {"b": 1, "a": {"y": 2, "x": 1}}
        b = {"a": {"x": 1, "y": 2}, "b": 1}
        self.assertEqual(cfgmod.digest(a), cfgmod.digest(b))


class IdentityTest(unittest.TestCase):
    def setUp(self):
        self.now = 1_000_000.0
        self.up = True
        self.ad = HmacTokenAdapter(issuer="iss", audience="inv41", keys={"k": KEY}, clock=lambda: self.now,
                                   available=lambda: self.up)
        self.claims = {"kid": "k", "iss": "iss", "aud": "inv41", "sub": "svc-a", "typ": "service", "tenant": "t1",
                       "env": "prod", "nbf": self.now - 10, "exp": self.now + 300}
        self.n = 0

    def tok(self, **over):
        self.n += 1
        return make_token(dict(self.claims, nonce=f"n{self.n}", **over), KEY)

    def test_ID001_valid_then_rejections(self):
        p = self.ad.authenticate(self.tok())
        self.assertEqual(p.principal_id, "svc-a")
        cases = {
            "expired": (self.tok(exp=self.now - 100), errors.StaleState),
            "not-yet": (self.tok(nbf=self.now + 100), errors.AuthenticationFailed),
            "aud": (self.tok(aud="other"), errors.AuthenticationFailed),
            "iss": (self.tok(iss="evil"), errors.AuthenticationFailed),
            "malformed": ("garbage", errors.AuthenticationFailed),
            "badsig": (self.tok()[:-2] + "00", errors.AuthenticationFailed),
            "multi-sub": (self.tok(sub=["a", "b"]), errors.AuthenticationFailed),
            "bad-type": (self.tok(typ="root"), errors.AuthenticationFailed),
        }
        for name, (tok, exc) in cases.items():
            with self.assertRaises(exc, msg=name):
                self.ad.authenticate(tok)

    def test_ID002_replay_and_revocation(self):
        t = self.tok()
        self.ad.authenticate(t)
        with self.assertRaises(errors.AuthenticationFailed):
            self.ad.authenticate(t)
        self.ad.revoked_subjects.add("svc-a")
        with self.assertRaises(errors.AuthenticationFailed):
            self.ad.authenticate(self.tok())

    def test_ID003_outage_fails_closed_and_recovers(self):
        self.up = False
        with self.assertRaises(errors.Unavailable):
            self.ad.authenticate(self.tok())
        self.up = True
        self.ad.authenticate(self.tok())

    def test_ID004_authentication_is_not_authorization_and_ids_cannot_impersonate(self):
        binder = PrincipalBinder({"iss|t1|prod|service|svc-a": {"store": {"read"}}})
        p = self.ad.authenticate(self.tok())
        auth = binder.bind(p, now=self.now)
        with self.assertRaises(Widening):
            auth.grant("store", {"write"})
        other = self.ad.authenticate(self.tok(sub="svc-b"))
        with self.assertRaises(errors.AuthenticationFailed):
            binder.bind(other, now=self.now)
        cross = self.ad.authenticate(self.tok(tenant="t2"))
        with self.assertRaises(errors.AuthenticationFailed):
            binder.bind(cross, now=self.now)
        impostor = Authority({"store": {"read", "write"}}, authority_id=auth.authority_id)
        with self.assertRaises(Exception):
            auth.bind_holder("h", {"s": impostor.grant("store")})

    def test_ID005_rotation_terminates_old_domain(self):
        binder = PrincipalBinder({"iss|t1|prod|service|svc-a": {"store": {"read"}}})
        p = self.ad.authenticate(self.tok())
        a1 = binder.bind(p, now=self.now)
        ref = a1.grant("store")
        binder.terminate(p)
        a2 = binder.bind(self.ad.authenticate(self.tok()), now=self.now)
        self.assertIsNot(a1, a2)
        with self.assertRaises(Exception):
            a2.bind_holder("h", {"s": ref})
        with self.assertRaises(errors.StaleState):
            binder.bind(p, now=p.expires_at + 1)


class BrokerTelemetryTest(unittest.TestCase):
    def setUp(self):
        self.audit = AuditChain(KEY)
        self.b = Broker(Authority({"store": {"read", "write"}}, authority_id="brk"), audit=self.audit)
        self.b.selfcheck_passed = True
        self.h = self.b.bind_holder("api", {"s": self.b.grant("store")})

    def test_BT001_allow_deny_are_counted_audited_and_explained(self):
        tp = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
        self.b.use(self.h, "s", "read", traceparent=tp)
        with self.assertRaises(Forged):
            self.b.use(self.h, "s", "admin")
        self.assertEqual(self.b.metrics.total("inv41_uses_allowed_total"), 1)
        self.assertEqual(self.b.metrics.total("inv41_uses_denied_total"), 1)
        types = [e["type"] for e in self.audit.exported]
        self.assertIn("use.allowed", types)
        self.assertIn("use.denied", types)
        exp = self.b.explain("a" * 32)
        self.assertEqual(exp[0]["outcome"], "success")
        self.assertEqual(exp[0]["kind"], "historical")
        self.assertTrue(verify_chain(self.audit.exported, KEY, expected_head=self.audit.head)["valid"])

    def test_BT002_nothing_secret_in_logs_audit_reasons_health_metrics(self):
        ref = self.h.held["s"]
        try:
            self.b.use(self.h, "s", "admin")
        except Forged:
            pass
        blob = json.dumps([self.b.log.sink, self.audit.exported, self.b.reasons, self.b.health(),
                           self.b.metrics.exposition(), self.b.tracer.spans], default=str)
        for secret in (ref.token, ref._signature, self.b._authority._authority_seal.hex(), "brk"):
            self.assertNotIn(secret, blob)

    def test_BT003_health_readiness_and_degraded_mode(self):
        self.assertTrue(self.b.health()["ready"])
        self.b.set_dependency("audit", "unavailable")
        h = self.b.health()
        self.assertFalse(h["ready"])
        self.assertEqual(h["status_code"], 503)
        with self.assertRaises(errors.Degraded):
            self.b.use(self.h, "s", "read")
        self.b.set_dependency("audit", "healthy")
        self.assertTrue(self.b.use(self.h, "s", "read")["permitted"])

    def test_BT004_quarantine_denies_but_revocation_still_works(self):
        m = Membrane("q")
        w = self.b.wrap(m, self.h.held["s"])
        self.b.quarantine()
        with self.assertRaises(errors.Degraded):
            self.b.use(self.h, "s", "read")
        self.assertTrue(self.b.revoke(m)["revoked"])
        with self.assertRaises(Revoked):
            w.invoke("read")

    def test_BT005_lifecycle_illegal_transitions(self):
        with self.assertRaises(IllegalTransition):
            self.b.transition("initializing")
        self.b.transition("terminated")
        with self.assertRaises(IllegalTransition):
            self.b.transition("ready")

    def test_BT006_metric_cardinality_is_bounded(self):
        m = Metrics()
        with self.assertRaises(CardinalityExceeded):
            m.inc("inv41_grants_total", resource="user-12345")
        with self.assertRaises(CardinalityExceeded):
            m.inc("inv41_uses_denied_total", outcome="made-up")
        with self.assertRaises(KeyError):
            m.inc("unregistered_metric")

    def test_BT007_log_schema_redaction_and_sampling(self):
        lg = StructuredLogger(component_version="t", success_sample_every=10)
        for i in range(20):
            lg.log("info", "use", "success", "ALLOW", "c")
        lg.log("warning", "use", "denied", "FORGED", "c", token="SECRET", note="x" * 50)
        self.assertEqual(len(lg.sink), 3)
        rec = json.loads(lg.sink[-1])
        for k in ("schema", "ts", "severity", "component", "version", "operation", "outcome", "reason", "correlation_id"):
            self.assertIn(k, rec)
        self.assertEqual(rec["token"], "<redacted>")
        self.assertEqual(rec["note"], "<redacted>")

    def test_BT008_trace_context(self):
        good = parse_traceparent("00-" + "1" * 32 + "-" + "2" * 16 + "-01")
        self.assertEqual(good["trace_id"], "1" * 32)
        for bad in (None, "junk", "00-" + "0" * 32 + "-" + "2" * 16 + "-01"):
            self.assertIsNone(parse_traceparent(bad)["parent_id"])

    def test_BT009_audit_outage_turns_allow_into_denial(self):
        c = AuditChain(KEY, sink=lambda e: (_ for _ in ()).throw(ConnectionError()), max_buffer=4)
        b = Broker(Authority({"s": {"read"}}), audit=c)
        b.selfcheck_passed = True
        h = b.bind_holder("h", {"s": b.grant("s")})
        outcomes = []
        for _ in range(6):
            try:
                b.use(h, "s", "read")
                outcomes.append("allowed")
            except errors.Degraded:
                outcomes.append("denied")
        self.assertIn("denied", outcomes)
        self.assertEqual(outcomes[outcomes.index("denied"):], ["denied"] * (6 - outcomes.index("denied")))


class ResilienceTest(unittest.TestCase):
    def test_RS001_retry_bounded_and_terminal_never_retried(self):
        calls = []
        with self.assertRaises(errors.Unavailable):
            retry(lambda: calls.append(1) or (_ for _ in ()).throw(TimeoutError()), attempts=4, sleep=lambda s: None)
        self.assertEqual(len(calls), 4)
        calls.clear()
        with self.assertRaises(Forged):
            retry(lambda: calls.append(1) or (_ for _ in ()).throw(Forged("x")), attempts=4, sleep=lambda s: None)
        self.assertEqual(len(calls), 1)

    def test_RS002_retry_budget_prevents_storm(self):
        budget = RetryBudget(capacity=3, refill_per_s=0, clock=lambda: 0.0)
        calls = []
        for _ in range(3):
            with self.assertRaises(errors.Unavailable):
                retry(lambda: calls.append(1) or (_ for _ in ()).throw(TimeoutError()), attempts=5, budget=budget,
                      sleep=lambda s: None)
        self.assertLessEqual(len(calls), 3 + 3)

    def test_RS003_circuit_breaker_hysteresis(self):
        t = [0.0]
        cb = CircuitBreaker(failure_threshold=2, cooldown_s=10, success_threshold=2, clock=lambda: t[0])
        for _ in range(2):
            with self.assertRaises(errors.Unavailable):
                cb.call(lambda: (_ for _ in ()).throw(errors.Unavailable("x")))
        self.assertEqual(cb.state, "open")
        with self.assertRaises(errors.Unavailable):
            cb.call(lambda: 1)
        t[0] = 11
        cb.call(lambda: 1)
        self.assertEqual(cb.state, "half-open")
        cb.call(lambda: 1)
        self.assertEqual(cb.state, "closed")
        with self.assertRaises(Forged):
            cb.call(lambda: (_ for _ in ()).throw(Forged("deny")))
        self.assertEqual(cb.failures, 0, "a denial is not a dependency failure")

    def test_RS004_admission_rejects_early_and_priority_lane(self):
        adm = Admission(max_concurrent=2, max_queue=1, priority_reserve=1, wait_s=0.01)
        s1, s2 = adm(), adm()
        s1.__enter__(); s2.__enter__()
        with self.assertRaises(errors.Overloaded):
            with adm():
                pass
        with adm(priority=True):
            pass
        s1.__exit__(None, None, None); s2.__exit__(None, None, None)
        self.assertEqual(adm.in_flight, 0)

    def test_RS005_fault_injection_never_fails_open(self):
        fi = FaultInjector()
        audit = AuditChain(KEY)
        b = Broker(Authority({"s": {"read"}}), audit=audit)
        b.selfcheck_passed = True
        h = b.bind_holder("h", {"s": b.grant("s")})
        m = Membrane("fi")
        w = m.wrap(h.held["s"])
        m.revoke()
        for kind in FaultInjector.KINDS:
            fi.set("policy", kind)

            def guarded():
                fi.check("policy")
                return h.use("s", "read")
            try:
                b._decide("use", guarded, resource="s", operation="read", traceparent=None)
                allowed = True
            except Exception:
                allowed = False
            self.assertFalse(allowed and kind != "clock_skew", kind)
            with self.assertRaises(Revoked):
                w.invoke("read")  # recovery never resurrects
        fi.set("policy", None)
        self.assertTrue(b.use(h, "s", "read")["permitted"])


if __name__ == "__main__":
    unittest.main()
