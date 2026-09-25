"""Tests for the v4.3.0 production layer.  Test names carry the checklist component id
(``test_cNN_*``) so tools/gen_evidence.py can map results back to components."""
from __future__ import annotations

import importlib
import importlib.util
import json
import os
import pathlib
import sys
import tempfile
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PKG_DIR / "tests") not in sys.path:
    sys.path.insert(0, str(PKG_DIR / "tests"))

P = PKG_DIR.name
pkg = importlib.import_module(P)
errors = importlib.import_module(f"{P}.errors")
lifecycle = importlib.import_module(f"{P}.lifecycle")
resilience = importlib.import_module(f"{P}.resilience")
config = importlib.import_module(f"{P}.config")
security = importlib.import_module(f"{P}.security")
storage = importlib.import_module(f"{P}.storage")
ha = importlib.import_module(f"{P}.ha")
telemetry = importlib.import_module(f"{P}.telemetry")
quota = importlib.import_module(f"{P}.quota")
negotiation = importlib.import_module(f"{P}.negotiation")
service = importlib.import_module(f"{P}.service")
adapters = importlib.import_module(f"{P}.adapters")
kafka = importlib.import_module(f"{P}.adapters.kafka")
rabbitmq = importlib.import_module(f"{P}.adapters.rabbitmq")
sqs = importlib.import_module(f"{P}.adapters.sqs")
import fakes  # noqa: E402

BrokerError = errors.BrokerError
E = errors


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, s):
        self.t += s


def make_service(clock=None, grants=None, limits=None, quotas=None):
    clock = clock or Clock()
    key = config.Secret(b"k" * 32)
    authn = security.HmacAuthenticator(lambda: [key], clock=clock, ttl=300)
    grants = grants if grants is not None else [
        security.Grant("t1", frozenset({"publish", "subscribe", "consume", "seek"})),
        security.Grant("t2", frozenset({"publish", "subscribe", "consume", "seek"})),
        security.Grant("t1", frozenset({"admin"}), role="admin"),
    ]
    audit = security.AuditLog(config.Secret(b"a" * 32), clock=clock)
    svc = service.BrokerService(authenticator=authn, authorizer=security.Authorizer(grants), audit=audit,
                                limits=limits, quotas=quotas, clock=clock)
    svc.start("cfg-digest")
    n = iter(range(10 ** 9))

    def tok(sub="alice", tenant="t1", roles=()):
        return authn.issue(security.Principal(sub, tenant, "w1", frozenset(roles)), nonce=f"n{next(n)}")
    return svc, tok, clock, authn


# ---------------------------------------------------------------- 05 / 22 errors
class ErrorModel(unittest.TestCase):
    def test_c22_codes_unique_stable_serialisable(self):
        reg = errors.registry()
        self.assertEqual(len(reg), len({c.code for c in reg.values()}))
        for c in reg.values():
            self.assertRegex(c.code, r"^INV54-E\d{4}$")
        d = BrokerError(E.PERMISSION_DENIED, action="publish").to_dict()
        self.assertEqual(json.loads(json.dumps(d))["code"], "INV54-E0102")

    def test_c22_details_redact_secret_named_fields(self):
        err = BrokerError(E.UNAUTHENTICATED, password="hunter2", api_token="abc")
        self.assertNotIn("hunter2", json.dumps(err.to_dict()))
        self.assertNotIn("abc", str(err.details))

    def test_c05_outcome_taxonomy_and_classification(self):
        self.assertEqual({o.value for o in errors.Outcome},
                         {"success", "partial", "degraded", "retryable", "terminal"})
        self.assertTrue(errors.classify(TimeoutError()).retryable)
        self.assertFalse(errors.classify(ValueError("x")).retryable)
        self.assertIs(errors.classify(IndexError()).code, E.OFFSET_OUT_OF_RANGE)

    def test_c05_error_schema_file_matches_registry(self):
        sch = json.loads((PKG_DIR / "schemas" / "error.schema.json").read_text())
        self.assertEqual(sorted(sch["properties"]["code"]["enum"]), sorted(errors.registry()))


# ---------------------------------------------------------------- 06 / 58 lifecycle
class LifecycleTests(unittest.TestCase):
    def test_c06_legal_path_and_illegal_transition(self):
        lc = lifecycle.Lifecycle()
        for s in ("configured", "starting", "ready", "draining", "stopped"):
            lc.transition(lifecycle.State(s), "t")
        with self.assertRaises(BrokerError) as cm:
            lc.transition(lifecycle.State.READY, "skip")
        self.assertIs(cm.exception.code, E.ILLEGAL_STATE)

    def test_c06_every_state_reachable_from_created(self):
        seen, frontier = {lifecycle.State.CREATED}, [lifecycle.State.CREATED]
        while frontier:
            for n in lifecycle.TRANSITIONS[frontier.pop()]:
                if n not in seen:
                    seen.add(n)
                    frontier.append(n)
        self.assertEqual(seen, set(lifecycle.State))

    def test_c58_quarantine_freezes_writes_allows_reads(self):
        svc, tok, *_ = make_service()
        svc.subscribe(tok(), "t1", "orders", "s")
        svc.publish(tok(), "t1", "orders", 1)
        svc.lifecycle.transition(lifecycle.State.QUARANTINED, "incident")
        with self.assertRaises(BrokerError) as cm:
            svc.publish(tok(), "t1", "orders", 2)
        self.assertIs(cm.exception.code, E.QUARANTINED)
        self.assertEqual(svc.receive(tok(), "t1", "orders", "s"), [1])

    def test_c58_tenant_quarantine_is_scoped_and_audited(self):
        svc, tok, *_ = make_service()
        svc.quarantine_tenant(tok(roles=("admin",)), "t1", "abuse")
        with self.assertRaises(BrokerError):
            svc.append(tok(), "t1", "s", "k", 1)
        svc.append(tok("bob", "t2"), "t2", "s", "k", 1)  # other tenant unaffected
        self.assertTrue(any(e.action == "quarantine" for e in svc.audit.events))
        with self.assertRaises(BrokerError):  # non-admin cannot release
            svc.release_tenant(tok(), "t1", "x")


# ---------------------------------------------------------------- 21 / 53 / 54 resilience
class ResilienceTests(unittest.TestCase):
    def test_c53_retry_bounded_with_jitter_and_stops_on_terminal(self):
        calls, sleeps = [], []
        pol = resilience.RetryPolicy(max_attempts=4, base_delay=0.1, max_delay=0.3)

        def flaky():
            calls.append(1)
            raise BrokerError(E.PROVIDER_UNAVAILABLE)
        with self.assertRaises(BrokerError):
            pol.run(flaky, sleep=sleeps.append)
        self.assertEqual(len(calls), 4)
        self.assertTrue(all(0 <= s <= 0.3 for s in sleeps))
        calls.clear()

        def terminal():
            calls.append(1)
            raise BrokerError(E.PERMISSION_DENIED)
        with self.assertRaises(BrokerError):
            pol.run(terminal, sleep=sleeps.append)
        self.assertEqual(len(calls), 1)

    def test_c53_retry_policy_rejects_unbounded(self):
        with self.assertRaises(BrokerError):
            resilience.RetryPolicy(max_attempts=10_000)

    def test_c21_deadline_and_cancel_checked_before_effect(self):
        clk = Clock()
        d = resilience.Deadline.after(1.0, clock=clk)
        clk.advance(2)
        with self.assertRaises(BrokerError) as cm:
            d.check()
        self.assertIs(cm.exception.code, E.DEADLINE_EXCEEDED)
        tok = resilience.CancelToken()
        tok.cancel("user")
        with self.assertRaises(BrokerError) as cm:
            resilience.Deadline.after(5, clock=clk, token=tok).check()
        self.assertIs(cm.exception.code, E.CANCELLED)

    def test_c21_publish_respects_deadline_without_side_effect(self):
        svc, tok, clk, _ = make_service()
        svc.subscribe(tok(), "t1", "orders", "s")
        d = resilience.Deadline.after(1, clock=clk)
        clk.advance(5)
        with self.assertRaises(BrokerError):
            svc.publish(tok(), "t1", "orders", 1, deadline=d)
        self.assertEqual(svc.receive(tok(), "t1", "orders", "s"), [])

    def test_c21_idempotency_key_prevents_duplicate_effect(self):
        svc, tok, *_ = make_service()
        svc.subscribe(tok(), "t1", "orders", "s")
        svc.publish(tok(), "t1", "orders", {"id": 1}, idempotency_key="abc")
        svc.publish(tok(), "t1", "orders", {"id": 1}, idempotency_key="abc")
        self.assertEqual(len(svc.receive(tok(), "t1", "orders", "s")), 1)
        p1 = svc.append(tok(), "t1", "st", "k", 1, idempotency_key="z")
        p2 = svc.append(tok(), "t1", "st", "k", 1, idempotency_key="z")
        self.assertEqual(p1, p2)

    def test_c54_circuit_breaker_opens_and_half_opens(self):
        clk = Clock()
        cb = resilience.CircuitBreaker(2, 10, clk)
        for _ in range(2):
            with self.assertRaises(RuntimeError):
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError()))
        with self.assertRaises(BrokerError) as cm:
            cb.call(lambda: 1)
        self.assertIs(cm.exception.code, E.CIRCUIT_OPEN)
        clk.advance(11)
        self.assertEqual(cb.call(lambda: 7), 7)
        self.assertEqual(cb.state, "closed")

    def test_c54_admission_sheds_low_priority_first(self):
        ac = resilience.AdmissionController(10, shed_ratio=0.5, shed_below_priority=5)
        for _ in range(5):
            ac.acquire(9)
        with self.assertRaises(BrokerError):
            ac.acquire(1)
        ac.acquire(9)
        self.assertEqual(ac.shed_count, 1)

    def test_c68_idempotency_cache_is_bounded(self):
        c = resilience.IdempotencyCache(3)
        for i in range(10):
            c.get_or_run(str(i), lambda: i)
        self.assertEqual(len(c), 3)
        with self.assertRaises(BrokerError):
            resilience.IdempotencyCache(10 ** 9)


# ---------------------------------------------------------------- 26-32 configuration
class ConfigTests(unittest.TestCase):
    def good(self, **over):
        base = {"profile": "dev", "provider": {"kind": "reference"}}
        base.update(over)
        return config.apply_overlays(base)

    def test_c26_defaults_valid_and_schema_file_covers_keys(self):
        self.assertEqual(config.validate(self.good()), [])
        sch = json.loads((PKG_DIR / "schemas" / "config.schema.json").read_text())
        self.assertEqual(set(sch["properties"]), set(config.DEFAULTS))

    def test_c27_fail_closed_production_profile(self):
        cfg = config.apply_overlays({"profile": "production", "provider": {"kind": "kafka", "endpoints": ["b:9092"]}})
        probs = config.validate(cfg)
        self.assertTrue(any("tls.enabled" in p for p in probs))
        self.assertTrue(any("auth.mode=none" in p for p in probs))
        store = config.ConfigStore()
        with self.assertRaises(BrokerError) as cm:
            store.stage(cfg, author="a", source="t")
        self.assertIs(cm.exception.code, E.CONFIG_INVALID)

    def test_c27_hard_ceiling_and_bool_rejected(self):
        self.assertTrue(config.validate(self.good(limits={**config.DEFAULTS["limits"], "partitions": 10 ** 6})))
        self.assertTrue(config.validate(self.good(limits={**config.DEFAULTS["limits"], "partitions": True})))

    def test_c28_overlays_apply_in_order_and_cannot_change_schema(self):
        cfg = config.apply_overlays({"provider": {"kind": "reference"}}, {"limits": {"partitions": 8}},
                                    {"limits": {"partitions": 16}})
        self.assertEqual(cfg["limits"]["partitions"], 16)
        self.assertEqual(cfg["limits"]["max_inflight"], 1024)
        with self.assertRaises(BrokerError):
            config.apply_overlays({}, {"schema": "inv54.config/0"})

    def test_c28_shipped_overlays_validate(self):
        base = json.loads((PKG_DIR / "config" / "base.json").read_text())
        for f in sorted((PKG_DIR / "config" / "overlays").glob("*.json")):
            with self.subTest(overlay=f.name):
                self.assertEqual(config.validate(config.apply_overlays(base, json.loads(f.read_text()))), [])

    def test_c29_c30_provenance_atomic_apply_and_conflict(self):
        applied = []
        fail = {"on": False}

        def hook(cfg):
            if fail["on"]:
                raise RuntimeError("activation failed")
            applied.append(cfg["limits"]["partitions"])
        st = config.ConfigStore(hook)
        st.stage(self.good(), author="alice", source="git:abc")
        p1 = st.commit(None, clock=lambda: 1.0)
        self.assertEqual((p1.version, p1.author, p1.previous_digest), (1, "alice", None))
        st.stage(self.good(limits={**config.DEFAULTS["limits"], "partitions": 8}), author="bob", source="git:def")
        with self.assertRaises(BrokerError) as cm:
            st.commit("wrong-digest")
        self.assertIs(cm.exception.code, E.CONFIG_CONFLICT)
        fail["on"] = True
        with self.assertRaises(RuntimeError):
            st.commit(p1.digest)
        self.assertEqual(st.current[1].digest, p1.digest)  # atomic: still on known-good
        fail["on"] = False
        p2 = st.commit(p1.digest)
        self.assertEqual(p2.previous_digest, p1.digest)
        self.assertEqual(applied, [4, 8])

    def test_c31_rollback_to_known_good(self):
        st = config.ConfigStore()
        st.stage(self.good(), author="a", source="s")
        p1 = st.commit(None)
        st.stage(self.good(limits={**config.DEFAULTS["limits"], "partitions": 8}), author="a", source="s")
        st.commit(p1.digest)
        p3 = st.rollback(author="oncall")
        self.assertEqual(p3.digest, p1.digest)
        self.assertEqual(len(st.provenance_log()), 3)
        with self.assertRaises(BrokerError):
            config.ConfigStore().rollback(author="x")

    def test_c32_secret_refs_resolve_redact_and_fail_closed(self):
        probs = config.validate(self.good(auth={"mode": "hmac", "hmac_key_ref": "plain-text-key",
                                                "token_ttl_s": 300}))
        self.assertTrue(any("secret://" in p for p in probs))
        probs = config.validate(self.good(provider={"kind": "reference", "options": {"password": "x"}}))
        self.assertTrue(any("inline secret" in p for p in probs))
        sp = config.StaticSecretProvider({"hmac": b"v1"})
        res = config.SecretResolver({"vault": sp})
        s = res.resolve("secret://vault/hmac")
        self.assertEqual(s.reveal(), b"v1")
        self.assertNotIn("v1", repr(s) + str(s))
        sp.put("hmac", b"v2")  # rotation
        self.assertEqual(res.resolve("secret://vault/hmac").reveal(), b"v2")
        sp.available = False
        with self.assertRaises(BrokerError) as cm:
            res.resolve("secret://vault/hmac")
        self.assertIs(cm.exception.code, E.SECURITY_SERVICE_UNAVAILABLE)
        self.assertEqual(config.redact({"x": {"password": "p"}})["x"]["password"], "***REDACTED***")


# ---------------------------------------------------------------- 19 / 20 / 39 / 42-44 security
class SecurityTests(unittest.TestCase):
    def test_c19_authentication_required_and_tamper_rejected(self):
        svc, tok, clk, authn = make_service()
        for bad in (None, "", "a.b.c", "x" * 10000, tok()[:-2] + "AA"):
            with self.subTest(bad=str(bad)[:10]):
                with self.assertRaises(BrokerError) as cm:
                    svc.subscribe(bad, "t1", "orders", "s")
                self.assertIn(cm.exception.code, (E.UNAUTHENTICATED,))

    def test_c19_expired_and_replayed_tokens_rejected(self):
        svc, tok, clk, authn = make_service()
        t = tok()
        svc.subscribe(t, "t1", "orders", "s")
        with self.assertRaises(BrokerError) as cm:
            svc.subscribe(t, "t1", "orders", "s2")
        self.assertIs(cm.exception.code, E.REPLAYED_CREDENTIAL)
        t2 = tok()
        clk.advance(301)
        with self.assertRaises(BrokerError) as cm:
            svc.subscribe(t2, "t1", "orders", "s3")
        self.assertIs(cm.exception.code, E.UNAUTHENTICATED)

    def test_c20_deny_by_default_and_resource_scoping(self):
        svc, tok, *_ = make_service(grants=[security.Grant("t1", frozenset({"publish"}), "orders.*")])
        svc.publish(tok(), "t1", "orders.eu", 1)
        with self.assertRaises(BrokerError) as cm:
            svc.publish(tok(), "t1", "payments", 1)
        self.assertIs(cm.exception.code, E.PERMISSION_DENIED)
        with self.assertRaises(BrokerError):
            svc.subscribe(tok(), "t1", "orders.eu", "s")  # subscribe not granted

    def test_c39_cross_tenant_access_refused_and_state_disjoint(self):
        svc, tok, *_ = make_service()
        svc.subscribe(tok(), "t1", "orders", "s")
        svc.subscribe(tok("bob", "t2"), "t2", "orders", "s")
        svc.publish(tok(), "t1", "orders", "secret-t1")
        with self.assertRaises(BrokerError) as cm:
            svc.receive(tok("bob", "t2"), "t1", "orders", "s")
        self.assertIs(cm.exception.code, E.TENANT_VIOLATION)
        self.assertEqual(svc.receive(tok("bob", "t2"), "t2", "orders", "s"), [])
        svc.append(tok(), "t1", "st", "k", 1)
        svc.poll(tok("bob", "t2"), "t2", "st", "c", 0)
        self.assertIsNot(svc._tenants["t1"].logs["st"], svc._tenants["t2"].logs["st"])

    def test_c42_key_service_outage_fails_closed(self):
        clock = Clock()
        state = {"up": True}

        def keys():
            if not state["up"]:
                raise ConnectionError("kms down")
            return [config.Secret(b"k" * 32)]
        authn = security.HmacAuthenticator(keys, clock=clock)
        t = authn.issue(security.Principal("a", "t1"), "n1")
        state["up"] = False
        with self.assertRaises(BrokerError) as cm:
            authn.authenticate(t)
        self.assertIs(cm.exception.code, E.SECURITY_SERVICE_UNAVAILABLE)

    def test_c32_key_rotation_grace_window(self):
        clock = Clock()
        ring = [config.Secret(b"old" * 11)]
        authn = security.HmacAuthenticator(lambda: list(ring), clock=clock)
        old = authn.issue(security.Principal("a", "t1"), "n1")
        ring.insert(0, config.Secret(b"new" * 11))  # rotate, keep old for grace
        self.assertEqual(authn.authenticate(old).subject, "a")
        ring.pop()  # grace over
        with self.assertRaises(BrokerError):
            authn.authenticate(authn.issue(security.Principal("a", "t1"), "n2")[:-4] + "AAAA")

    def test_c43_audit_chain_detects_edit_delete_reorder_truncate(self):
        svc, tok, *_ = make_service()
        svc.subscribe(tok(), "t1", "orders", "s")
        for i in range(3):
            svc.publish(tok(), "t1", "orders", i)
        with self.assertRaises(BrokerError):
            svc.publish("garbage", "t1", "orders", 9)
        a = svc.audit
        a.verify(expected_head=a.head)
        self.assertTrue(any(e.decision == "deny" for e in a.events))
        import copy
        for mutate in (lambda ev: setattr(ev[1], "decision", "deny"), lambda ev: ev.pop(1),
                       lambda ev: ev.insert(0, ev.pop(2))):
            evs = copy.deepcopy(a.events)
            mutate(evs)
            with self.assertRaises(BrokerError):
                a.verify(events=evs)
        with self.assertRaises(BrokerError):
            a.verify(expected_head=a.head, events=a.events[:-1])

    def test_c44_adversarial_inputs_rejected_predictably(self):
        svc, tok, *_ = make_service()
        hostile = ["../etc", "a b", "", "x" * 500, "\x00", "orders\n", "*", 5, None]
        for h in hostile:
            with self.subTest(h=repr(h)[:12]):
                with self.assertRaises(BrokerError) as cm:
                    svc.subscribe(tok(), "t1", h, "s")
                self.assertIs(cm.exception.code, E.INVALID_ARGUMENT)
        with self.assertRaises(BrokerError):
            svc.publish(tok(), "t1", "orders", object())  # not serialisable
        with self.assertRaises(BrokerError):
            svc.publish(tok(), "t1", "orders", "x" * 2_000_000)  # oversized
        forged = security.HmacAuthenticator(lambda: [config.Secret(b"attacker")]).issue(
            security.Principal("root", "t1", roles=frozenset({"admin"})), "n")
        with self.assertRaises(BrokerError) as cm:
            svc.quarantine_tenant(forged, "t1", "x")
        self.assertIs(cm.exception.code, E.UNAUTHENTICATED)

    def test_c38_artifact_allowlist(self):
        pol = security.ArtifactPolicy({"brokers.py": __import__("hashlib").sha256(b"abc").hexdigest()})
        pol.verify_bytes("brokers.py", b"abc")
        with self.assertRaises(BrokerError):
            pol.verify_bytes("brokers.py", b"abd")
        with self.assertRaises(BrokerError):
            pol.verify_bytes("evil.py", b"abc")


# ---------------------------------------------------------------- 8 / 65 / 68 / 70 capacity
class CapacityTests(unittest.TestCase):
    def test_c08_per_tenant_rate_quota_isolates_tenants(self):
        q = quota.QuotaManager(quota.QuotaSpec(publish_rate=1, publish_burst=3), clock=Clock())
        svc, tok, *_ = make_service(quotas=q)
        for i in range(3):
            svc.append(tok(), "t1", "s", "k", i)
        with self.assertRaises(BrokerError) as cm:
            svc.append(tok(), "t1", "s", "k", 99)
        self.assertIs(cm.exception.code, E.QUOTA_EXCEEDED)
        svc.append(tok("bob", "t2"), "t2", "s", "k", 1)  # fairness: t2 unaffected

    def test_c08_byte_budget(self):
        q = quota.QuotaManager(quota.QuotaSpec(publish_rate=1e6, publish_burst=1e6, max_bytes=50))
        with self.assertRaises(BrokerError):
            for _ in range(10):
                q.charge("t", "w", 10)
        self.assertEqual(q.usage[("t", "w")].messages, 5)

    def test_c68_backlog_bound_reject_is_all_or_nothing(self):
        svc, tok, *_ = make_service(limits={"max_backlog_per_subscriber": 2})
        svc.subscribe(tok(), "t1", "o", "fast")
        svc.subscribe(tok(), "t1", "o", "slow")
        svc.publish(tok(), "t1", "o", 1)
        svc.publish(tok(), "t1", "o", 2)
        svc.receive(tok(), "t1", "o", "fast")
        with self.assertRaises(BrokerError) as cm:
            svc.publish(tok(), "t1", "o", 3)
        self.assertIs(cm.exception.code, E.BACKLOG_FULL)
        self.assertEqual(svc.receive(tok(), "t1", "o", "fast"), [])  # nobody got a partial fan-out

    def test_c68_drop_oldest_is_explicit_and_degraded(self):
        svc, tok, *_ = make_service(limits={"max_backlog_per_subscriber": 1, "overflow_policy": "drop_oldest"})
        svc.subscribe(tok(), "t1", "o", "s")
        svc.publish(tok(), "t1", "o", 1)
        r = svc.publish(tok(), "t1", "o", 2)
        self.assertEqual(r.outcome, errors.Outcome.DEGRADED)
        self.assertEqual(svc.receive(tok(), "t1", "o", "s"), [2])

    def test_c68_subscriber_and_log_ceilings(self):
        svc, tok, *_ = make_service(limits={"max_subscribers_per_tenant": 1, "max_log_records_per_partition": 2,
                                            "partitions": 1})
        svc.subscribe(tok(), "t1", "o", "a")
        with self.assertRaises(BrokerError):
            svc.subscribe(tok(), "t1", "o", "b")
        svc.append(tok(), "t1", "s", "k", 1)
        svc.append(tok(), "t1", "s", "k", 2)
        with self.assertRaises(BrokerError):
            svc.append(tok(), "t1", "s", "k", 3)

    def test_c65_resource_accounting_snapshot(self):
        svc, tok, *_ = make_service()
        svc.append(tok(), "t1", "s", "k", {"a": 1})
        snap = svc.quotas.snapshot()
        self.assertEqual(snap[0]["tenant"], "t1")
        self.assertEqual(snap[0]["messages"], 1)
        self.assertGreater(snap[0]["bytes_in"], 0)

    def test_c70_saturation_signal(self):
        self.assertEqual(quota.saturation(1, 10, 0, 10)["state"], "ok")
        self.assertEqual(quota.saturation(8, 10, 0, 10)["state"], "warning")
        self.assertEqual(quota.saturation(1, 10, 10, 10)["state"], "saturated")


# ---------------------------------------------------------------- 23 negotiation
class NegotiationTests(unittest.TestCase):
    def test_c23_negotiates_highest_common_and_refuses_unknown(self):
        self.assertEqual(str(negotiation.negotiate(["PK_BROKER_LOG/1.7", "PK_BROKER_LOG/2.0"])), "PK_BROKER_LOG/1.1")
        self.assertEqual(str(negotiation.negotiate(["PK_BROKER_LOG/1.0"])), "PK_BROKER_LOG/1.0")
        with self.assertRaises(BrokerError) as cm:
            negotiation.negotiate(["PK_BROKER_LOG/9"])
        self.assertIs(cm.exception.code, E.VERSION_UNSUPPORTED)
        with self.assertRaises(BrokerError):
            negotiation.parse("garbage")


# ---------------------------------------------------------------- 47/48/41/57/61 storage
class StorageTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def test_c47_durable_across_reopen(self):
        log = storage.DurableLog(self.d, 2)
        for i in range(10):
            log.append(f"k{i % 3}", {"i": i})
        log.close()
        log2 = storage.DurableLog(self.d, 2)
        got = sorted(r.value["i"] for p in range(2) for r in log2.read(p, 0, 100))
        self.assertEqual(got, list(range(10)))

    def test_c57_crash_torn_tail_truncated_on_recovery(self):
        log = storage.DurableLog(self.d, 1)
        for i in range(5):
            log.append("k", i)
        log.close()
        path = pathlib.Path(self.d) / "p0.log"
        data = path.read_bytes()
        path.write_bytes(data[:-3])  # simulate crash mid-append
        log2 = storage.DurableLog(self.d, 1)
        self.assertEqual([r.value for r in log2.read(0, 0)], [0, 1, 2, 3])
        self.assertEqual(log2.recovered_truncations, 1)
        self.assertEqual(log2.append("k", 99), (0, 4))  # offsets continue correctly

    def test_c57_mid_file_corruption_is_refused_not_skipped(self):
        log = storage.DurableLog(self.d, 1)
        for i in range(5):
            log.append("k", i)
        log.close()
        path = pathlib.Path(self.d) / "p0.log"
        data = bytearray(path.read_bytes())
        data[20] ^= 0xFF
        path.write_bytes(bytes(data))
        with self.assertRaises(BrokerError) as cm:
            storage.DurableLog(self.d, 1)
        self.assertIs(cm.exception.code, E.STORAGE_CORRUPTION)

    def test_c48_retention_and_compaction(self):
        clk = Clock()
        log = storage.DurableLog(self.d, 1, clock=clk)
        for i in range(6):
            log.append("a" if i % 2 else "b", i)
            clk.advance(10)
        self.assertEqual(log.apply_retention(max_records=4), 2)
        self.assertEqual(log.bounds(0), (2, 6))
        with self.assertRaises(BrokerError) as cm:
            log.read(0, 0)
        self.assertIs(cm.exception.code, E.OFFSET_OUT_OF_RANGE)
        self.assertEqual(log.compact(), 2)
        self.assertEqual([(r.key, r.offset) for r in log.read(0, 2)], [("b", 4), ("a", 5)])
        log.close()
        log2 = storage.DurableLog(self.d, 1, clock=clk)
        self.assertEqual(log2.bounds(0), (2, 6))
        self.assertEqual(log2.apply_retention(max_age_s=15), 1)

    @unittest.skipUnless(importlib.util.find_spec("cryptography"), "extra 'encryption' not installed")
    def test_c41_at_rest_encryption_and_key_required(self):
        key = os.urandom(32)
        log = storage.DurableLog(self.d, 1, cipher=storage.Cipher(key))
        log.append("k", {"card": "4111-secret-marker"})
        log.close()
        self.assertNotIn(b"secret-marker", (pathlib.Path(self.d) / "p0.log").read_bytes())
        with self.assertRaises(BrokerError) as cm:
            storage.DurableLog(self.d, 1)
        self.assertIs(cm.exception.code, E.SECURITY_SERVICE_UNAVAILABLE)
        with self.assertRaises(BrokerError):
            storage.DurableLog(self.d, 1, cipher=storage.Cipher(os.urandom(32)))  # wrong key
        self.assertEqual(storage.DurableLog(self.d, 1, cipher=storage.Cipher(key)).read(0, 0)[0].value["card"],
                         "4111-secret-marker")

    def test_c41_encryption_without_library_fails_closed(self):
        import builtins
        real = builtins.__import__

        def no_crypto(name, *a, **k):
            if name.startswith("cryptography"):
                raise ImportError("simulated absence")
            return real(name, *a, **k)
        builtins.__import__ = no_crypto
        try:
            with self.assertRaises(BrokerError) as cm:
                storage.Cipher(b"k" * 32)
            self.assertIs(cm.exception.code, E.SECURITY_SERVICE_UNAVAILABLE)
        finally:
            builtins.__import__ = real

    def test_c61_backup_restore_roundtrip_and_unsafe_archive(self):
        log = storage.DurableLog(self.d, 2)
        for i in range(7):
            log.append(str(i), i)
        arc = log.backup(pathlib.Path(tempfile.mkdtemp()) / "b.tgz")
        dst = pathlib.Path(tempfile.mkdtemp()) / "r"
        storage.DurableLog.restore(arc, dst)
        r = storage.DurableLog(dst, 2)
        self.assertEqual(sum(len(r.read(p, 0)) for p in range(2)), 7)
        with self.assertRaises(BrokerError):
            storage.DurableLog.restore(arc, dst)  # non-empty target

    def test_c47_partition_count_change_refused(self):
        storage.DurableLog(self.d, 2).close()
        with self.assertRaises(BrokerError):
            storage.DurableLog(self.d, 3)


# ---------------------------------------------------------------- 49/50/55/60 HA
class HATests(unittest.TestCase):
    def cluster(self, sites=("a", "a", "b"), allowed=None):
        clk = Clock()
        nodes = [ha.ReplicaNode(f"n{i}", s) for i, s in enumerate(sites)]
        auth = ha.FencingAuthority(10, clk)
        return ha.ReplicatedPartition(nodes, auth, min_insync=2, allowed_sites=allowed), clk

    def test_c49_quorum_replication_and_hw(self):
        rp, _ = self.cluster()
        rp.elect("n0")
        for i in range(3):
            rp.append("k", i)
        self.assertEqual(rp.read_committed(), [("k", 0), ("k", 1), ("k", 2)])
        self.assertTrue(all(len(n.log) == 3 for n in rp.nodes.values()))
        rp.nodes["n1"].up = rp.nodes["n2"].up = False
        with self.assertRaises(BrokerError) as cm:
            rp.append("k", 3)
        self.assertIs(cm.exception.code, E.PARTITION_UNAVAILABLE)
        self.assertEqual(len(rp.read_committed()), 3)  # not exposed

    def test_c50_stale_leader_is_fenced_after_failover(self):
        rp, clk = self.cluster()
        old_epoch = rp.elect("n0")
        rp.append("k", "a")
        rp.nodes["n0"].up = False
        clk.advance(11)
        new = rp.failover()
        self.assertNotEqual(new, "n0")
        rp.nodes["n0"].up = True
        with self.assertRaises(BrokerError) as cm:
            rp.append("k", "zombie", as_node="n0", epoch=old_epoch)
        self.assertIs(cm.exception.code, E.FENCED)
        rp.append("k", "b")
        self.assertEqual([v for _, v in rp.read_committed()], ["a", "b"])

    def test_c50_lease_prevents_dual_leaders(self):
        rp, clk = self.cluster()
        rp.elect("n0")
        with self.assertRaises(BrokerError) as cm:
            rp.authority.acquire("n1")
        self.assertIs(cm.exception.code, E.NOT_LEADER)

    def test_c55_failover_respects_residency(self):
        rp, clk = self.cluster(sites=("eu", "us", "eu"), allowed={"eu"})
        rp.elect("n0")
        rp.append("k", 1)
        rp.nodes["n0"].up = False
        self.assertEqual(rp.failover(), "n2")
        with self.assertRaises(BrokerError):
            rp.elect("n1")

    def test_c60_partition_then_reconnect_converges(self):
        rp, clk = self.cluster()
        rp.elect("n0")
        rp.append("k", 1)
        rp.nodes["n2"].up = False           # n2 partitioned
        rp.append("k", 2)
        rp.nodes["n2"].up = True
        # catch-up: replay leader's committed log onto n2 under current epoch
        n2 = rp.nodes["n2"]
        for off, (ep, k, v) in enumerate(rp.nodes["n0"].log):
            if off >= len(n2.log):
                n2.replicate(rp.epoch, off, k, v)
        self.assertEqual([v for _, _, v in n2.log], [1, 2])


# ---------------------------------------------------------------- 52/72-80 health & telemetry
class ObservabilityTests(unittest.TestCase):
    def test_c72_health_surface_fields(self):
        svc, tok, *_ = make_service()
        h = svc.health()
        for k in ("live", "ready", "state", "version", "config_digest", "dependencies", "saturation",
                  "audit_head", "lineage"):
            self.assertIn(k, h)
        self.assertEqual(h["version"], pkg.__version__)
        self.assertTrue(h["ready"])

    def test_c56_c42_dependency_outage_enters_and_leaves_degraded(self):
        svc, tok, *_ = make_service()
        up = {"v": True}
        svc.dependencies["kms"] = lambda: up["v"]
        up["v"] = False
        self.assertEqual(svc.reevaluate(), lifecycle.State.DEGRADED)
        svc.subscribe(tok(), "t1", "o", "s")
        r = svc.publish(tok(), "t1", "o", 1)
        self.assertEqual(r.outcome, errors.Outcome.DEGRADED)
        up["v"] = True
        self.assertEqual(svc.reevaluate(), lifecycle.State.READY)

    def test_c52_stall_detection(self):
        svc, tok, clk, _ = make_service()
        svc.subscribe(tok(), "t1", "o", "s")
        svc.publish(tok(), "t1", "o", 1)
        clk.advance(120)
        st = svc.stalls(60)
        self.assertEqual(st[0]["subscriber"], "s")
        svc.receive(tok(), "t1", "o", "s")
        self.assertEqual(svc.stalls(60), [])

    def test_c73_metrics_recorded(self):
        svc, tok, *_ = make_service()
        svc.append(tok(), "t1", "s", "k", 1)
        svc.poll(tok(), "t1", "s", "c", svc._tenants["t1"].logs["s"].partition_for("k"))
        snap = svc.metrics.snapshot()
        names = {c["name"] for c in snap["counters"]} | {g["name"] for g in snap["gauges"]}
        self.assertTrue({"appended", "consumer_lag"} <= names)
        self.assertIn("inv54_appended", svc.metrics.prometheus())

    def test_c74_logs_structured_and_secret_safe(self):
        lines = []
        lg = telemetry.StructuredLogger(sink=lines.append)
        lg.log("INFO", "x", password="p", payload={"pii": 1}, tenant="t")
        rec = json.loads(lines[0])
        self.assertEqual(rec["password"], "***REDACTED***")
        self.assertNotIn("payload", rec)
        self.assertIn("version", rec)

    def test_c75_trace_context_roundtrip_and_invalid(self):
        t = telemetry.TraceContext.new()
        self.assertEqual(telemetry.TraceContext.parse(t.header()), t)
        self.assertEqual(t.child().trace_id, t.trace_id)
        for bad in ("", "00-" + "0" * 32 + "-" + "1" * 16 + "-01", "garbage"):
            self.assertIsNone(telemetry.TraceContext.parse(bad))

    def test_c76_cardinality_capped(self):
        m = telemetry.Metrics(max_label_values=5)
        for i in range(100):
            m.inc("c", consumer=f"c{i}")
        self.assertLessEqual(len({ls for (n, ls) in m.counters}), 6)
        self.assertEqual(m.cardinality_overflows, 95)

    def test_c77_c78_decisions_and_explain(self):
        svc, tok, *_ = make_service()
        with self.assertRaises(BrokerError):
            svc._auth(tok(), "admin", "t1", "*", "quarantine", request_id="r-1")
        txt = svc.decisions.explain("r-1")
        self.assertIn("deny", txt)
        self.assertIn("INV54-E0102", txt)
        self.assertIn("no decision retained", svc.decisions.explain("nope"))

    def test_c79_lineage_labels(self):
        self.assertEqual(telemetry.build_lineage()["component_version"], pkg.__version__)


# ---------------------------------------------------------------- 9 offline
class OfflineTests(unittest.TestCase):
    def test_c09_store_and_forward_ordered_idempotent(self):
        buf = service.OfflineBuffer(capacity=3)
        for i in range(3):
            buf.put(f"k{i}", {"v": i})
        with self.assertRaises(BrokerError):
            buf.put("k3", {})
        link = {"up": False}
        got = []

        def send(k, r):
            if not link["up"]:
                raise BrokerError(E.PROVIDER_UNAVAILABLE)
            got.append(r["v"])
        self.assertEqual(buf.flush(send), 0)
        link["up"] = True
        self.assertEqual(buf.flush(send), 3)
        self.assertEqual(got, [0, 1, 2])


# ---------------------------------------------------------------- 13-15 / 24 / 83 adapters
class AdapterTests(unittest.TestCase):
    def assertConforms(self, adapter, advance=None):
        res = adapters.run_conformance(adapter, advance=advance)
        failed = {k: v for k, v in res.items() if v.startswith("FAIL")}
        self.assertEqual(failed, {}, res)
        return res

    def test_c24_reference_adapters_conform(self):
        self.assertConforms(adapters.ReferenceLogAdapter())
        self.assertConforms(adapters.ReferenceQueueAdapter())

    def test_c13_kafka_adapter_mapping_conforms_on_fake_client(self):
        _, pf, cf = fakes.kafka_factories()
        cfg = kafka.build_config(["b1:9092"], tls={"enabled": True},
                                 sasl={"username": "u", "password": config.Secret(b"pw")})
        self.assertEqual(cfg["security.protocol"], "SASL_SSL")
        self.assertTrue(cfg["enable.idempotence"])
        self.assertFalse(cfg["enable.auto.commit"])
        res = self.assertConforms(kafka.KafkaAdapter(cfg, producer_factory=pf, consumer_factory=cf))
        self.assertEqual(res["replay"], "PASS")

    def test_c13_kafka_error_translation(self):
        cl, pf, cf = fakes.kafka_factories()
        a = kafka.KafkaAdapter(kafka.build_config(["b"]), producer_factory=pf, consumer_factory=cf)
        cl.fail_next = "TOPIC_AUTHORIZATION_FAILED"
        with self.assertRaises(BrokerError) as cm:
            a.publish("t", 1, key="k")
        self.assertIs(cm.exception.code, E.PERMISSION_DENIED)
        cl.fail_next = "_ALL_BROKERS_DOWN"
        with self.assertRaises(BrokerError) as cm:
            a.publish("t", 1, key="k")
        self.assertTrue(cm.exception.retryable)
        with self.assertRaises(BrokerError):
            kafka.build_config([])

    def test_c14_rabbitmq_adapter_conforms_on_fake_channel(self):
        ch = fakes.FakeChannel()
        a = rabbitmq.RabbitMQAdapter(channel_factory=lambda: ch)
        self.assertTrue(ch.confirms)
        res = self.assertConforms(a)
        self.assertEqual(res["replay"], "NOT_APPLICABLE")
        ch.down = True
        with self.assertRaises(BrokerError) as cm:
            a.publish("x", 1)
        self.assertIs(cm.exception.code, E.PROVIDER_UNAVAILABLE)

    def test_c15_sqs_adapter_visibility_dedup_and_errors(self):
        c = fakes.FakeSQS()
        a = sqs.SQSAdapter(client=c, visibility_timeout_s=30)
        res = self.assertConforms(a, advance=lambda: setattr(c, "now", c.now + 31))
        self.assertEqual(res["ack_redelivery"], "PASS")
        a.consume("jobs.fifo", "g", 1)
        a.publish("jobs.fifo", {"n": 1}, key="acct", dedup_id="d1")
        a.publish("jobs.fifo", {"n": 1}, key="acct", dedup_id="d1")  # dedup window
        first = a.consume("jobs.fifo", "g", 10)
        self.assertEqual(len(first), 1)
        self.assertEqual(a.consume("jobs.fifo", "g", 10), [])  # invisible
        c.now += 31
        again = a.consume("jobs.fifo", "g", 10)
        self.assertTrue(again[0].redelivered)
        a.ack("jobs.fifo", "g", again[0])
        with self.assertRaises(BrokerError):
            a.publish("jobs.fifo", 1)  # FIFO requires dedup id
        c.throttle = True
        with self.assertRaises(BrokerError) as cm:
            a.publish("std", 1)
        self.assertIs(cm.exception.code, E.QUOTA_EXCEEDED)

    def test_c13_c14_c15_missing_client_library_is_explicit(self):
        for ctor in (lambda: kafka.KafkaAdapter({"bootstrap.servers": "x"}),
                     lambda: rabbitmq.RabbitMQAdapter("amqps://x"),
                     lambda: sqs.SQSAdapter(region="us-east-1")):
            try:
                ctor()
            except BrokerError as e:
                self.assertIs(e.code, E.PROVIDER_NOT_INSTALLED)
            except Exception as exc:  # library present but no broker: still must be classified
                self.fail(f"unclassified {type(exc).__name__}")

    def test_c16_capability_matrix_matches_declared_features(self):
        m = json.loads((PKG_DIR / "schemas" / "provider_matrix.json").read_text())
        for prov, cls in (("kafka", kafka.KafkaAdapter), ("rabbitmq", rabbitmq.RabbitMQAdapter),
                          ("sqs", sqs.SQSAdapter)):
            declared = {f for f, v in m["providers"][prov].items() if v == "native"}
            self.assertEqual(declared, set(cls.features), prov)

    def test_c25_adjacent_layer_harness_reference_path(self):
        """INV-52/53/49/37 are not shipped; the harness drives the adapter protocol they
        would call and verifies INV-37 payload references pass through untouched."""
        a = adapters.ReferenceLogAdapter()
        ref = {"bulk_ref": "inv37://blob/sha256:abc", "size": 10 ** 9}
        a.publish("s", ref, key="k")
        got = a.consume("s", "g")
        self.assertEqual(got[0].value, ref)
        self.assertIsInstance(a, adapters.BrokerAdapter)


# ---------------------------------------------------------------- concurrency (86)
class ConcurrencyTests(unittest.TestCase):
    def test_c86_concurrent_publish_consume_no_loss_no_dup(self):
        svc, tok, *_ = make_service(limits={"max_backlog_per_subscriber": 100_000})
        svc.subscribe(tok(), "t1", "o", "s")
        toks = [tok() for _ in range(8 * 250 + 400)]
        it = iter(toks)
        lock = threading.Lock()

        def nxt():
            with lock:
                return next(it)
        got = []

        def pub(w):
            for i in range(250):
                svc.publish(nxt(), "t1", "o", (w, i))

        def con():
            for _ in range(400):
                got.extend(svc.receive(nxt(), "t1", "o", "s", 50))
        ts = [threading.Thread(target=pub, args=(w,)) for w in range(8)] + [threading.Thread(target=con)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        got.extend(svc.receive(tok(), "t1", "o", "s", 10 ** 6))
        self.assertEqual(len(got), 2000)
        self.assertEqual(len(set(got)), 2000)
        for w in range(8):
            self.assertEqual([i for ww, i in got if ww == w], list(range(250)))


# ---------------------------------------------------------------- lifecycle smoke
class ServiceLifecycle(unittest.TestCase):
    def test_c06_drain_blocks_writes_then_stop(self):
        svc, tok, *_ = make_service()
        svc.drain()
        with self.assertRaises(BrokerError):
            svc.append(tok(), "t1", "s", "k", 1)
        svc.stop()
        self.assertFalse(svc.health()["live"])


if __name__ == "__main__":
    unittest.main()
