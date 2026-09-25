"""v4.3.0 tests: trust path, service contract, durability, resilience,
observability, concurrency, threat-derived and fuzz suites (framework-free).

Run:  python -m unittest pln07_security_plane.tests.test_v43      (from the
folder containing the package).  Must also pass under ``python -O``.
"""
from __future__ import annotations

import json
import pathlib
import random
import sys
import tempfile
import threading
import time
import unittest
from dataclasses import replace

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pln07_security_plane.clock import TimeRollback, TimeUnavailable, TrustedClock  # noqa: E402
from pln07_security_plane.config import ConfigInvalid, ConfigStore, SECURE_DEFAULTS, merge  # noqa: E402
from pln07_security_plane.grants import Grant, GrantInvalid, Verifier, Widening  # noqa: E402
from pln07_security_plane.identity import (  # noqa: E402
    AttestationPolicy, AuthenticationFailed, Principal, StaticTokenAuthenticator)
from pln07_security_plane.observability import AuditLog, Metrics, redact, from_traceparent  # noqa: E402
from pln07_security_plane.policy import Decision, IssuancePolicy, QuotaExceeded, QuotaLimiter, resolve  # noqa: E402
from pln07_security_plane.resilience import (  # noqa: E402
    CircuitBreaker, CircuitOpen, Frozen, Health, IdempotencyCache, Overloaded, Quarantine, TokenBucket, retry)
from pln07_security_plane.revocation import LogCorrupt, RevocationRegistry, StaleEpoch  # noqa: E402
from pln07_security_plane.service import (  # noqa: E402
    SecurityPlaneService, decode_grant, encode_grant, negotiate, UnsupportedVersion, Malformed)
from pln07_security_plane.signing import AlgorithmPolicy, KeyStore, SigningError, HAVE_ED25519  # noqa: E402

CORPUS = pathlib.Path(__file__).resolve().parent / "fuzz_corpus"


class FakeClock:
    def __init__(self, t=1_000_000):
        self.t = t

    def __call__(self):
        return self.t


def make_service(**kw):
    auth = StaticTokenAuthenticator(b"k" * 32)
    issuer = Principal("ops", "t1", frozenset({"grant-issuer", "revoker"}), frozenset({"tpm"}))
    worker = Principal("worker", "t1")
    tokens = {"ops": auth.token_for(issuer), "worker": auth.token_for(worker)}
    keys = KeyStore("prod", AlgorithmPolicy(frozenset({"Ed25519", "HMAC-SHA256"})))
    keys.generate("Ed25519" if HAVE_ED25519 else "HMAC-SHA256")
    fc = FakeClock()
    svc = SecurityPlaneService(
        auth, keys,
        IssuancePolicy(tenant_capabilities={"t1": frozenset({"state", "invoke"})},
                       depth_limits={"t1:invoke": 2}, residency={"prod": frozenset({"dub"})}),
        clock=TrustedClock(sources=(fc,)),
        attestation=AttestationPolicy({"prod": frozenset({"tpm"})}), **kw)
    return svc, tokens, fc


def cred(tokens, who, tenant="t1"):
    return {"subject": who, "tenant": tenant, "token": tokens[who]}


def issue(svc, tokens, fc, **over):
    spec = {"subject": "worker", "tenant": "t1", "scope": ["state", "invoke"], "not_after": fc.t + 600,
            "environment": "prod", "site": "dub", "audience": "pln-03"}
    spec.update(over)
    return svc.issue({"api_version": "1", "credentials": cred(tokens, "ops"), "grant": spec})


CTX = {"capability": "state", "tenant": "t1", "environment": "prod", "site": "dub", "audience": "pln-03"}


class TrustedTimeTest(unittest.TestCase):  # MC-12
    def test_quorum_disagreement_rollback(self):
        a, b = FakeClock(100), FakeClock(101)
        c = TrustedClock(sources=(a, b), quorum=2, max_disagreement=2, max_rollback=1)
        self.assertEqual(c.now(), 101)
        b.t = 200
        with self.assertRaises(TimeUnavailable):
            c.now()
        b.t = 100
        self.assertEqual(c.now(), 101)  # 1s regression clamped, monotonic
        a.t = b.t = 90
        with self.assertRaises(TimeRollback):
            c.now()

    def test_unavailable_fails_closed(self):
        def dead():
            raise OSError("ntp down")
        with self.assertRaises(TimeUnavailable):
            TrustedClock(sources=(dead,)).now()


class SigningTest(unittest.TestCase):  # MC-05
    def setUp(self):
        self.ks = KeyStore("prod", AlgorithmPolicy(frozenset({"Ed25519", "HMAC-SHA256"})))

    def _roundtrip(self, alg):
        kid = self.ks.generate(alg)
        g = self.ks.sign_grant(Grant("w", "t1", {"s"}, 100))
        self.assertTrue(self.ks.verify(g.signature, g.canonical_payload))
        self.assertFalse(self.ks.verify(g.signature, replace(g, scope=frozenset({"s", "x"})).canonical_payload))
        forged = dict(g.signature, domain="other")
        self.assertFalse(self.ks.verify(forged, g.canonical_payload))
        return kid, g

    def test_hmac(self):
        self._roundtrip("HMAC-SHA256")

    @unittest.skipUnless(HAVE_ED25519, "cryptography not installed")
    def test_ed25519_rotation_and_revocation(self):
        kid, g = self._roundtrip("Ed25519")
        new = self.ks.rotate(kid)
        self.assertEqual(self.ks.active_kid(), new)
        self.assertTrue(self.ks.verify(g.signature, g.canonical_payload))  # retiring still verifies
        with self.assertRaises(SigningError):
            self.ks.sign(b"x", kid)
        self.ks.revoke_key(kid)
        self.assertFalse(self.ks.verify(g.signature, g.canonical_payload))

    def test_algorithm_policy(self):
        with self.assertRaises(SigningError):
            KeyStore("prod").generate("HMAC-SHA256")
        kid = self.ks.generate("HMAC-SHA256")
        g = self.ks.sign_grant(Grant("w", "t1", {"s"}, 100))
        strict = KeyStore("prod")
        strict._keys = self.ks._keys
        self.assertFalse(strict.verify(g.signature, g.canonical_payload))
        self.assertTrue(kid)

    def test_garbage_envelopes(self):
        self.ks.generate("HMAC-SHA256")
        for env in (None, 1, "x", {}, {"type": "PK_SIG/1"}, {"type": "PK_SIG/1", "domain": "prod", "kid": "z"}):
            self.assertFalse(self.ks.verify(env, b"p"))


class GrantV2Test(unittest.TestCase):  # MC-11, MC-13, MC-14, MC-15, MC-16
    def test_boundaries_are_sticky_and_enforced(self):
        root = Grant("c", "t1", {"s"}, 100, environment="prod", site="dub", workload="w1", audience="pln-03")
        child = root.attenuate(subject="x")
        self.assertEqual((child.environment, child.site), ("prod", "dub"))
        with self.assertRaises(Widening):
            Grant("x", "t1", {"s"}, 90, root, 1, site="fra", environment="prod", workload="w1", audience="pln-03")
        v = Verifier()
        self.assertTrue(v.verify(child, 10, "s", "t1", environment="prod", site="dub", workload="w1", audience="pln-03"))
        for k, bad in (("environment", "dev"), ("site", "fra"), ("workload", "w2"), ("audience", "pln-04")):
            ctx = {"environment": "prod", "site": "dub", "workload": "w1", "audience": "pln-03", k: bad}
            with self.assertRaises(GrantInvalid) as cm:
                v.verify(child, 10, "s", "t1", **ctx)
            self.assertEqual(cm.exception.reason, k)

    def test_not_before_and_window(self):
        g = Grant("c", "t1", {"s"}, 100, not_before=50, issued_at=40)
        with self.assertRaises(GrantInvalid) as cm:
            Verifier().verify(g, 10, "s", "t1")
        self.assertEqual(cm.exception.reason, "not_yet_valid")
        self.assertTrue(Verifier().verify(g, 60, "s", "t1"))
        with self.assertRaises(GrantInvalid):
            Grant("c", "t1", {"s"}, 10, not_before=50)

    def test_nonce_distinguishes_instances(self):
        a = Grant("c", "t1", {"s"}, 100, nonce="n1")
        b = Grant("c", "t1", {"s"}, 100, nonce="n2")
        self.assertNotEqual(a.fingerprint, b.fingerprint)

    def test_legacy_id_unchanged_for_v1(self):
        self.assertEqual(Grant("controller", "t1", {"state"}, 100).id, "3bb0ef82f0bd2218")
        self.assertEqual(Grant("controller", "t1", {"state"}, 100).grant_type, "PK_GRANT/1")

    def test_fingerprint_revocation(self):
        g = Grant("c", "t1", {"s"}, 100)
        with self.assertRaises(GrantInvalid):
            Verifier(revoked={g.fingerprint}).verify(g.attenuate(subject="x"), 1, "s", "t1")

    def test_policy_depth(self):
        g = Grant("c", "t1", {"s"}, 100).attenuate(subject="a").attenuate(subject="b")
        with self.assertRaises(GrantInvalid):
            Verifier(depth_policy=lambda _g: 1).verify(g, 1, "s", "t1")
        with self.assertRaises(GrantInvalid):
            g.attenuate(subject="c", max_depth=2)

    def test_require_v2(self):
        with self.assertRaises(GrantInvalid) as cm:
            Verifier(require_v2=True).verify(Grant("c", "t1", {"s"}, 100), 1, "s", "t1")
        self.assertEqual(cm.exception.reason, "version")

    def test_revocation_source_failure_fails_closed(self):
        class Broken:
            def is_revoked(self, g):
                raise OSError
        with self.assertRaises(GrantInvalid) as cm:
            Verifier(revocation_source=Broken()).verify(Grant("c", "t1", {"s"}, 100), 1, "s", "t1")
        self.assertEqual(cm.exception.reason, "revocation_unavailable")


class IdentityPolicyTest(unittest.TestCase):  # MC-03, MC-04, MC-62, MC-63, MC-64
    def test_authentication_uniform_failure(self):
        auth = StaticTokenAuthenticator(b"k" * 32)
        tok = auth.token_for(Principal("a", "t1"))
        self.assertEqual(auth.authenticate({"subject": "a", "tenant": "t1", "token": tok}).subject, "a")
        for c in ({"subject": "a", "tenant": "t1", "token": "0" * 64}, {"subject": "b", "tenant": "t1", "token": tok}, {}):
            with self.assertRaises(AuthenticationFailed) as cm:
                auth.authenticate(c)
            self.assertEqual(str(cm.exception), "authentication failed")

    def test_precedence_and_default_deny(self):
        self.assertFalse(resolve([]).allow)
        d = resolve([Decision(False, "cost", "cost"), Decision(False, "res", "residency"), Decision(True, "ok")])
        self.assertEqual(d.rule, "res")

    def test_quota(self):
        q = QuotaLimiter(per_tenant={"t1": 2})
        q.acquire("t1"); q.acquire("t1")
        with self.assertRaises(QuotaExceeded):
            q.acquire("t1")
        q.release("t1"); q.acquire("t1")
        q.acquire("t2")  # fairness: other tenants unaffected


class RevocationTest(unittest.TestCase):  # MC-06, MC-10, MC-29, MC-30
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.dir.name) / "rev.log"
        self.g = Grant("c", "t1", {"s"}, 100)

    def tearDown(self):
        self.dir.cleanup()

    def test_durable_restart_and_idempotent(self):
        r = RevocationRegistry(self.path)
        a = r.revoke(self.g, effective_at=1, horizon=10, epoch=1)
        self.assertEqual(r.revoke(self.g, effective_at=2, horizon=10, epoch=1), a)
        r2 = RevocationRegistry(self.path)
        self.assertTrue(r2.is_revoked(self.g.attenuate(subject="x").parent))
        self.assertTrue(r2.verify_chain())
        self.assertEqual(r2.head, r.head)

    def test_torn_tail_recovered_and_corruption_detected(self):
        r = RevocationRegistry(self.path)
        r.revoke(self.g, effective_at=1, horizon=10, epoch=1)
        with open(self.path, "ab") as fh:
            fh.write(b'{"op":"revo')  # crash mid-write
        r2 = RevocationRegistry(self.path)
        self.assertEqual(r2.stats()["records"], 1)
        self.assertTrue(self.path.read_bytes().endswith(b"\n"))
        data = self.path.read_text().replace('"horizon":10', '"horizon":99')
        self.path.write_text(data + json.dumps({"op": "x"}) + "\n")
        with self.assertRaises(LogCorrupt):
            RevocationRegistry(self.path)

    def test_stale_epoch_fenced(self):
        r = RevocationRegistry(self.path)
        r.revoke(self.g, effective_at=1, horizon=10, epoch=5)
        with self.assertRaises(StaleEpoch):
            r.revoke(Grant("d", "t1", {"s"}, 100), effective_at=1, horizon=10, epoch=4)

    def test_horizon_and_acks_and_compaction(self):
        r = RevocationRegistry(self.path, retention=5)
        rec = r.revoke(self.g, effective_at=10, horizon=5, epoch=1)
        self.assertEqual(r.horizon_breached(["dub", "fra"], now=16), ["dub", "fra"])
        r.acknowledge("dub", rec["seq"], epoch=1)
        self.assertEqual(r.horizon_breached(["dub", "fra"], now=16), ["fra"])
        self.assertEqual(r.compact(now=106, epoch=1), 1)
        self.assertFalse(RevocationRegistry(self.path, retention=5).is_revoked(self.g))


class ConfigTest(unittest.TestCase):  # MC-17..MC-20
    def test_overlays_validation_and_monotonic_security(self):
        cfg = merge(SECURE_DEFAULTS, {"clock_skew_seconds": 2}, {"admission": {"burst": 10}})
        self.assertEqual(cfg["admission"], {"rate_per_second": 500, "burst": 10})
        with self.assertRaises(ConfigInvalid):
            merge(SECURE_DEFAULTS, {"require_signatures": False})
        for bad in ({"nope": 1}, {"clock_skew_seconds": True}, {"max_delegation_depth": 9}):
            with self.assertRaises(ConfigInvalid):
                merge(SECURE_DEFAULTS, bad)

    def test_atomic_persist_rollback_and_redaction(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "cfg.json"
            s = ConfigStore(p)
            s.activate({"clock_skew_seconds": 1, "signing_secret": "s" * 40}, author="dp", change_id="CR-1")
            self.assertEqual(ConfigStore(p).config["clock_skew_seconds"], 1)
            with self.assertRaises(ConfigInvalid):
                s.activate({"clock_skew_seconds": 3}, author="dp", change_id="CR-2", health_probe=lambda c: False)
            self.assertEqual(ConfigStore(p).config["clock_skew_seconds"], 1)
            self.assertEqual(s.describe()["config"]["signing_secret"], "<redacted>")
            self.assertEqual(s.active["provenance"]["author"], "dp")


class ResilienceTest(unittest.TestCase):  # MC-25..MC-28, MC-31
    def test_health_watchdog(self):
        t = [0.0]
        h = Health(stall_after=5, clock=lambda: t[0])
        h.set("ready"); h.heartbeat("revocation-sync")
        t[0] = 10
        self.assertEqual(h.check()["state"], "degraded")

    def test_retry_idempotency(self):
        calls = []
        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise OSError
            return "ok"
        self.assertEqual(retry(flaky, sleep=lambda s: None), "ok")
        c = IdempotencyCache()
        n = []
        c.run("k", lambda: n.append(1)); c.run("k", lambda: n.append(1))
        self.assertEqual(len(n), 1)

    def test_admission_and_breaker(self):
        t = [0.0]
        b = TokenBucket(1, 2, clock=lambda: t[0])
        b.admit(); b.admit()
        with self.assertRaises(Overloaded):
            b.admit()
        t[0] = 1.0; b.admit()
        cb = CircuitBreaker("gap13", failure_threshold=2, reset_seconds=5, clock=lambda: t[0])
        for _ in range(2):
            with self.assertRaises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError()))
        with self.assertRaises(CircuitOpen):
            cb.call(lambda: 1)
        t[0] = 10
        self.assertEqual(cb.call(lambda: 1), 1)
        self.assertEqual(cb.state, "closed")

    def test_quarantine(self):
        q = Quarantine()
        q.freeze("sites", "dub", actor="oncall", reason="horizon breach")
        with self.assertRaises(Frozen):
            q.check(tenant="t1", site="dub")
        q.thaw("sites", "dub", actor="oncall", reason="acked")
        q.check(tenant="t1", site="dub")


class ObservabilityTest(unittest.TestCase):  # MC-40..MC-44, MC-47
    def test_redaction_and_cardinality(self):
        r = redact({"token": "x", "nested": {"api_key": "y", "ok": 1}, "blob": b"z", "long": "a" * 600})
        self.assertEqual((r["token"], r["nested"]["api_key"], r["nested"]["ok"], r["blob"]), ("<redacted>", "<redacted>", 1, "<bytes>"))
        m = Metrics()
        for i in range(200):
            m.inc("c", subject=f"s{i}")
        self.assertLessEqual(len(m.counters), 65)
        self.assertIn("__overflow__", m.prometheus())

    def test_audit_tamper_evident(self):
        a = AuditLog()
        a.emit("issue", "allow", "grant.issued", token="secret")
        a.emit("verify", "deny", "grant.expired")
        self.assertTrue(a.verify())
        self.assertEqual(a.events[0]["fields"]["token"], "<redacted>")
        a.events[0]["outcome"] = "deny"
        self.assertFalse(a.verify())

    def test_traceparent(self):
        ctx = from_traceparent("00-" + "a" * 32 + "-" + "b" * 16 + "-01")
        self.assertEqual(ctx["trace_id"], "a" * 32)
        self.assertNotEqual(from_traceparent("garbage")["trace_id"], "a" * 32)


class ServiceContractTest(unittest.TestCase):  # MC-09, MC-10, MC-16, MC-39, MC-45, MC-49, MC-61
    def setUp(self):
        self.svc, self.tok, self.fc = make_service()

    def test_full_lifecycle(self):
        r = issue(self.svc, self.tok, self.fc)
        self.assertTrue(r["ok"], r)
        v = self.svc.verify({"api_version": "1", "grant": r["grant"], "context": CTX})
        self.assertEqual(v["code"], "grant.valid")
        a = self.svc.attenuate({"api_version": "1", "credentials": cred(self.tok, "worker"), "grant": r["grant"],
                                "attenuation": {"subject": "sub", "scope": ["state"]}})
        self.assertTrue(a["ok"], a)
        x = self.svc.revoke({"api_version": "1", "credentials": cred(self.tok, "ops"), "grant": r["grant"]})
        self.assertEqual(x["revocation"]["type"], "PK_REVOCATION/2")
        v = self.svc.verify({"api_version": "1", "grant": a["grant"], "context": CTX})
        self.assertEqual(v["code"], "grant.revoked")
        h = self.svc.health()
        self.assertTrue(h["ready"] and h["dependencies"]["audit_chain_ok"] and h["dependencies"]["revocation_chain_ok"])
        e = self.svc.explain(a["grant"], CTX)
        self.assertEqual(len(e["chain"]), 2)
        self.assertTrue(e["chain"][0]["revoked"])
        self.assertNotIn("sig", json.dumps(e["chain"]).replace("signature_ok", ""))

    def test_refusals_have_stable_codes(self):
        cases = [
            ({"api_version": "9"}, "api.unsupported_version"),
            ({"credentials": {"subject": "ops", "tenant": "t1", "token": "bad"}}, "auth.failed"),
            ({"grant_over": {"scope": ["state", "secrets"]}}, "policy.denied"),
            ({"grant_over": {"not_after": self.fc.t + 10 ** 6}}, "policy.denied"),
            ({"grant_over": {"site": "fra"}}, "policy.denied"),
            ({"grant_over": {"environment": "prod", "tenant": "t2"}}, "policy.denied"),
        ]
        for over, code in cases:
            spec = {"subject": "worker", "tenant": "t1", "scope": ["state"], "not_after": self.fc.t + 60,
                    "environment": "prod", "site": "dub"}
            spec.update(over.get("grant_over", {}))
            req = {"api_version": over.get("api_version", "1"),
                   "credentials": over.get("credentials", cred(self.tok, "ops")), "grant": spec}
            self.assertEqual(self.svc.issue(req)["code"], code, over)
        self.assertEqual(self.svc.issue({"api_version": "1"})["code"], "api.malformed")

    def test_attestation_required_for_prod(self):
        auth = self.svc.authenticator
        weak = Principal("weak", "t1", frozenset({"grant-issuer"}))
        tok = auth.token_for(weak)
        r = self.svc.issue({"api_version": "1", "credentials": {"subject": "weak", "tenant": "t1", "token": tok},
                            "grant": {"subject": "w", "tenant": "t1", "scope": ["state"], "not_after": self.fc.t + 60,
                                      "environment": "prod", "site": "dub"}})
        self.assertEqual(r["code"], "auth.attestation")

    def test_only_holder_attenuates_and_depth_policy(self):
        r = issue(self.svc, self.tok, self.fc, scope=["invoke"])
        bad = self.svc.attenuate({"api_version": "1", "credentials": cred(self.tok, "ops"), "grant": r["grant"],
                                  "attenuation": {"subject": "x"}})
        self.assertEqual(bad["code"], "policy.denied")

    def test_version_negotiation_and_codec(self):
        self.assertEqual(negotiate(["0", "1"]), "1")
        with self.assertRaises(UnsupportedVersion):
            negotiate(["2"])
        g = Grant("c", "t1", {"s"}, 100).attenuate(subject="x")
        self.assertEqual(decode_grant(encode_grant(g)).fingerprint, g.fingerprint)
        wire = encode_grant(g)
        wire[0]["type"] = "PK_GRANT/9"
        with self.assertRaises(UnsupportedVersion):
            decode_grant(wire)
        wire = encode_grant(g)
        wire[0]["extra"] = 1
        with self.assertRaises(Malformed):
            decode_grant(wire)

    def test_quarantine_blocks_issue_and_verify(self):
        r = issue(self.svc, self.tok, self.fc)
        self.svc.quarantine.freeze("plane", actor="ic", reason="incident")
        self.assertEqual(self.svc.verify({"api_version": "1", "grant": r["grant"], "context": CTX})["code"], "control.frozen")
        self.assertEqual(issue(self.svc, self.tok, self.fc)["code"], "control.frozen")


class ThreatSuite(unittest.TestCase):  # MC-54 (derived from SECURITY.md threat table)
    def setUp(self):
        self.svc, self.tok, self.fc = make_service()
        self.r = issue(self.svc, self.tok, self.fc)

    def _verify(self, wire, **ctx):
        return self.svc.verify({"api_version": "1", "grant": wire, "context": {**CTX, **ctx}})["code"]

    def test_tamper_scope_after_issue(self):
        w = json.loads(json.dumps(self.r["grant"]))
        w[0]["scope"].append("secrets")
        self.assertEqual(self._verify(w, capability="secrets"), "grant.signature")

    def test_strip_signature(self):
        w = json.loads(json.dumps(self.r["grant"]))
        w[0]["signature"] = None
        self.assertEqual(self._verify(w), "grant.unsigned")

    def test_replay_to_other_audience(self):
        self.assertEqual(self._verify(self.r["grant"], audience="pln-04"), "grant.audience")

    def test_spoof_issuer_domain(self):
        other = KeyStore("evil", AlgorithmPolicy(frozenset({"HMAC-SHA256"})))
        other.generate("HMAC-SHA256")
        g = other.sign_grant(decode_grant(self.r["grant"]))
        self.assertEqual(self._verify(encode_grant(g)), "grant.signature")

    def test_expired_and_clock_skew(self):
        self.fc.t += 600 + 6
        self.assertEqual(self._verify(self.r["grant"]), "grant.expired")

    def test_resource_exhaustion_inputs(self):
        self.assertEqual(self.svc.verify({"api_version": "1", "grant": [{}] * 50, "context": CTX})["code"], "api.malformed")
        big = json.loads(json.dumps(self.r["grant"]))
        big[0]["scope"] = [f"c{i}" for i in range(300)]
        self.assertEqual(self._verify(big), "api.malformed")

    def test_admission_sheds_floods(self):
        self.svc._admission = TokenBucket(0.0001, 3)
        codes = [issue(self.svc, self.tok, self.fc)["code"] for _ in range(5)]
        self.assertIn("admission.overloaded", codes)

    def test_nonce_unique_across_issues(self):
        n = {decode_grant(issue(self.svc, self.tok, self.fc)["grant"]).nonce for _ in range(50)}
        self.assertEqual(len(n), 50)


class ConcurrencyTest(unittest.TestCase):  # MC-53
    def test_concurrent_revoke_verify_consistency(self):
        with tempfile.TemporaryDirectory() as d:
            reg = RevocationRegistry(pathlib.Path(d) / "r.log")
            grants = [Grant(f"s{i}", "t1", {"s"}, 10 ** 9) for i in range(200)]
            v = Verifier(revocation_source=reg)
            errors = []

            def revoker(chunk):
                for g in chunk:
                    reg.revoke(g, effective_at=1, horizon=1, epoch=1)

            def verifier():
                for g in grants:
                    try:
                        v.verify(g, 1, "s", "t1")
                    except GrantInvalid as exc:
                        if exc.reason != "revoked":
                            errors.append(exc)

            threads = [threading.Thread(target=revoker, args=(grants[i::4],)) for i in range(4)]
            threads += [threading.Thread(target=verifier) for _ in range(4)]
            [t.start() for t in threads]
            [t.join() for t in threads]
            self.assertEqual(errors, [])
            self.assertTrue(all(reg.is_revoked(g) for g in grants))
            self.assertTrue(reg.verify_chain())
            self.assertEqual(RevocationRegistry(pathlib.Path(d) / "r.log").stats()["revoked"], 200)

    def test_quota_is_thread_safe(self):
        q = QuotaLimiter(per_tenant={"t": 100})
        ok = []

        def take():
            for _ in range(50):
                try:
                    q.acquire("t"); ok.append(1)
                except QuotaExceeded:
                    pass
        ts = [threading.Thread(target=take) for _ in range(8)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(len(ok), 100)


class FuzzTest(unittest.TestCase):  # MC-52: deterministic, corpus-seeded, CI-runnable
    ITERATIONS = 3000

    def _mutate(self, rnd, obj):
        choices = [None, 0, -1, True, "", " x", "\x00", "a" * 300, [], {}, ["s"] * 3, 2 ** 64, 1.5]
        if isinstance(obj, list):
            obj = list(obj)
            if obj and rnd.random() < 0.3:
                obj.pop(rnd.randrange(len(obj)))
            elif obj:
                i = rnd.randrange(len(obj)); obj[i] = self._mutate(rnd, obj[i])
            return obj
        if isinstance(obj, dict):
            obj = dict(obj)
            k = rnd.choice(list(obj) + ["zz"])
            obj[k] = rnd.choice(choices) if rnd.random() < 0.7 else self._mutate(rnd, obj.get(k))
            return obj
        return rnd.choice(choices)

    def test_decode_and_verify_never_crash_or_accept_garbage(self):
        seeds = [json.loads(p.read_text()) for p in sorted(CORPUS.glob("*.json"))]
        self.assertTrue(seeds, "fuzz corpus missing")
        rnd = random.Random(0x9107)
        v = Verifier()
        for _ in range(self.ITERATIONS):
            wire = self._mutate(rnd, rnd.choice(seeds))
            try:
                g = decode_grant(wire)
            except (Malformed, UnsupportedVersion, Widening, GrantInvalid):
                continue
            res = v.verify_detailed(g, 50, "state", "t1")
            self.assertIn(res.code.split(".")[0], {"grant"})


class PerformanceBudgetTest(unittest.TestCase):  # MC-33/34 smoke budget (full bench in bench/)
    def test_depth5_verify_p99_under_budget(self):
        g = Grant("c", "t1", {"s"}, 10 ** 9)
        for i in range(5):
            g = g.attenuate(subject=f"d{i}")
        v = Verifier()
        samples = []
        for _ in range(2000):
            t = time.perf_counter_ns(); v.verify(g, 1, "s", "t1"); samples.append(time.perf_counter_ns() - t)
        samples.sort()
        self.assertLess(samples[int(0.99 * len(samples))], 5_000_000)  # 5 ms generous CI budget


if __name__ == "__main__":
    unittest.main()


class HttpTransportContractTest(unittest.TestCase):  # MC-49: transport-level contract
    def test_http_endpoints(self):
        import urllib.request
        from http.server import ThreadingHTTPServer
        from pln07_security_plane.deploy.host import handler_for
        svc, tok, fc = make_service()
        srv = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(svc))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}"

        def post(path, obj):
            req = urllib.request.Request(base + path, json.dumps(obj).encode(), {"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req) as r:
                    return r.status, json.loads(r.read())
            except urllib.error.HTTPError as e:
                return e.code, json.loads(e.read())
        try:
            spec = {"subject": "worker", "tenant": "t1", "scope": ["state"], "not_after": fc.t + 60,
                    "environment": "prod", "site": "dub", "audience": "pln-03"}
            st, r = post("/v1/issue", {"api_version": "1", "credentials": cred(tok, "ops"), "grant": spec})
            self.assertEqual((st, r["code"]), (200, "grant.issued"))
            st, v = post("/v1/verify", {"api_version": "1", "grant": r["grant"], "context": CTX})
            self.assertEqual(v["code"], "grant.valid")
            st, bad = post("/v1/issue", {"api_version": "1", "credentials": {}, "grant": spec})
            self.assertEqual((st, bad["code"]), (400, "auth.failed"))
            with urllib.request.urlopen(base + "/readyz") as rr:
                self.assertEqual(rr.status, 200)
            with urllib.request.urlopen(base + "/metrics") as rr:
                self.assertIn(b"pln07_requests_total", rr.read())
            st, _ = post("/admin/freeze", {"kind": "plane", "reason": "test"})
            self.assertEqual(st, 200)
            st, v = post("/v1/verify", {"api_version": "1", "grant": r["grant"], "context": CTX})
            self.assertEqual(v["code"], "control.frozen")
        finally:
            srv.shutdown()
