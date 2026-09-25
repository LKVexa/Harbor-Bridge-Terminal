"""Threat-model-derived adversarial suite (checklist #48, #86, #38, #40, #43, #49, #50).

Each test names the threat ID from docs/security/threat-model.md in its docstring.
"""
from __future__ import annotations

import base64
import copy
import io
import json
import pickle
import unittest

from helpers import SECRET, Env
from inv55_secrets_integration.audit import MemoryAuditSink
from inv55_secrets_integration.errors import ErrorCode, redact_text
from inv55_secrets_integration.secretvalue import SecretValue
from inv55_secrets_integration.telemetry import JsonLogger


def code(r):
    return r["error"]["code"]


class Spoofing(unittest.TestCase):
    def setUp(self):
        self.e = Env()
        self.e.seed()

    def test_alg_none_rejected(self):
        """S-1 forged token with alg=none."""
        tok = self.e.cred()
        h, b, _ = tok.split(".")
        none_h = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).rstrip(b"=").decode()
        r = self.e.svc.resolve({"protocol": "PK_SECRET_RESOLVE/1", "credential": f"{none_h}.{b}.",
                                "name": "db-password"})
        self.assertEqual(code(r), ErrorCode.UNAUTHENTICATED.value.code)

    def test_tampered_claims_rejected(self):
        """S-2 tenant switch by editing claims."""
        h, b, s = self.e.cred().split(".")
        claims = json.loads(base64.urlsafe_b64decode(b + "=="))
        claims["tenant"] = "globex"
        nb = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
        r = self.e.svc.resolve({"protocol": "PK_SECRET_RESOLVE/1", "credential": f"{h}.{nb}.{s}",
                                "name": "db-password"})
        self.assertEqual(code(r), ErrorCode.UNAUTHENTICATED.value.code)

    def test_expired_token_rejected(self):
        """S-3 replay of an expired credential."""
        tok = self.e.authn.issue("orders", "acme", ["consumer"], ttl_s=1)
        self.e.clock.advance(120)
        r = self.e.svc.resolve({"protocol": "PK_SECRET_RESOLVE/1", "credential": tok, "name": "db-password"})
        self.assertEqual(code(r), ErrorCode.UNAUTHENTICATED.value.code)

    def test_oversized_and_garbage_credentials(self):
        """S-4 parser abuse."""
        for c in [None, "", "a.b", "x" * 9000, "a.b.c", "....", "\x00.\x00.\x00"]:
            r = self.e.svc.resolve({"protocol": "PK_SECRET_RESOLVE/1", "credential": c, "name": "db-password"})
            self.assertEqual(code(r), ErrorCode.UNAUTHENTICATED.value.code, repr(c))


class Elevation(unittest.TestCase):
    def setUp(self):
        self.e = Env()
        self.e.seed()

    def test_cross_tenant_read_denied(self):
        """E-1 tenant B reads tenant A's secret with the same name/app."""
        r = self.e.resolve(tenant="globex")
        self.assertEqual(code(r), ErrorCode.DENIED.value.code)

    def test_lease_replay_by_other_app(self):
        """E-2 lease id stolen and replayed by another workload."""
        r = self.e.resolve()
        u = self.e.use(r["lease_id"], sub="marketing")
        self.assertIn(code(u), (ErrorCode.CONTEXT_MISMATCH.value.code, ErrorCode.DENIED.value.code))

    def test_lease_replay_cross_tenant(self):
        """E-3 lease replayed from another tenant."""
        r = self.e.resolve()
        self.assertEqual(code(self.e.use(r["lease_id"], tenant="globex")), ErrorCode.CONTEXT_MISMATCH.value.code)

    def test_consumer_cannot_rotate_or_scope(self):
        """E-4 least privilege: consumer role lacks rotate/scope."""
        c = self.e.cred(roles=("consumer",))
        r = self.e.svc.rotate({"protocol": "PK_SECRET_ROTATE/1", "credential": c, "name": "db-password",
                               "value": "evil", "idempotency_key": "idem-evil-01"})
        self.assertEqual(code(r), ErrorCode.DENIED.value.code)
        s = self.e.svc.set_scope({"protocol": "PK_SECRET_SCOPE/1", "credential": c, "name": "db-password",
                                  "apps": ["attacker"]})
        self.assertEqual(code(s), ErrorCode.DENIED.value.code)

    def test_glob_injection_in_name(self):
        """E-5 identifier alphabet excludes glob metacharacters."""
        for n in ["*", "db-*", "db?", "[a]"]:
            self.assertEqual(code(self.e.resolve(name=n)), ErrorCode.INVALID_REFERENCE.value.code)

    def test_quota_charged_to_authenticated_tenant(self):
        """D-3 a caller cannot exhaust another tenant's quota by spoofing request fields."""
        from inv55_secrets_integration.resilience import AdmissionController
        e = Env(admission=None)
        e.seed()
        e.svc.admission = AdmissionController(e.clock, tenant_rate=0.0001, tenant_burst=3,
                                              workload_rate=0.0001, workload_burst=3)
        for _ in range(5):
            e.svc.resolve({"protocol": "PK_SECRET_RESOLVE/1", "credential": e.cred("x", "globex"),
                           "name": "nope", "tenant": "acme", "app": "orders"})
        self.assertTrue(e.resolve()["ok"])


    def test_path_traversal_in_names_rejected(self):
        """E-7 '..'/'.'/empty segments cannot traverse into another tenant's provider path."""
        for n in ["x/../../globex/db-password", "a/./b", "a//b", "a/", "..", "a/.."]:
            self.assertEqual(code(self.e.resolve(name=n)), ErrorCode.INVALID_REFERENCE.value.code, n)

    def test_tenant_claim_cannot_contain_path_separator(self):
        """E-8 a signed token whose tenant contains '/' is rejected (tenant is a path segment)."""
        for tenant in ["acme/db-password", "..", "acme\n"]:
            tok = self.e.authn.issue("orders", tenant, ["consumer"])
            r = self.e.svc.resolve({"protocol": "PK_SECRET_RESOLVE/1", "credential": tok, "name": "x"})
            self.assertEqual(code(r), ErrorCode.UNAUTHENTICATED.value.code, tenant)

    def test_malformed_signed_claims_are_unauthenticated_and_audited(self):
        """S-5 structurally odd but correctly signed tokens fail as UNAUTHENTICATED, not INTERNAL."""
        import hashlib, hmac as _h
        def sign(header, body):
            enc = lambda o: base64.urlsafe_b64encode(json.dumps(o).encode()).rstrip(b"=").decode()
            hb = f"{enc(header)}.{enc(body)}"
            sig = base64.urlsafe_b64encode(_h.new(b"k" * 32, hb.encode(), hashlib.sha256).digest()).rstrip(b"=")
            return f"{hb}.{sig.decode()}"
        now = self.e.clock()
        good = {"iss": "inv55-idp", "aud": "inv55", "sub": "orders", "tenant": "acme", "nbf": now, "exp": now + 60}
        for header, body in [([], good), ({"alg": "HS256"}, []), ({"alg": "HS256"}, {**good, "roles": 5}),
                             ({"alg": "HS256"}, {**good, "roles": [1]})]:
            before = len(self.e.sink.lines)
            r = self.e.svc.resolve({"protocol": "PK_SECRET_RESOLVE/1", "credential": sign(header, body),
                                    "name": "db-password"})
            self.assertEqual(code(r), ErrorCode.UNAUTHENTICATED.value.code, (header, body))
            self.assertEqual(len(self.e.sink.lines), before + 1, "failed authentication must be audited")


class Disclosure(unittest.TestCase):
    def test_secret_never_in_any_diagnostic(self):
        """I-1 value must not appear in audit, metrics, traces, ledger, health, errors."""
        e = Env()
        e.seed()
        r = e.resolve()
        e.use(r["lease_id"])
        e.resolve(sub="marketing")
        e.use("bogus")
        e.svc.rotate({"protocol": "PK_SECRET_ROTATE/1", "credential": e.cred("admin"), "name": "db-password",
                      "value": SECRET + "-v2", "idempotency_key": "idem-000009"})
        self.assertNotIn(SECRET, e.all_diagnostics())

    def test_error_payload_is_fixed_text(self):
        """I-2 error messages never echo caller input."""
        e = Env()
        r = e.resolve(name="password=" + SECRET)
        self.assertNotIn(SECRET, json.dumps(r))

    def test_secret_value_not_str_and_not_serialisable(self):
        """I-3 materialisation via inherited APIs / pickle / copy."""
        v = SecretValue(SECRET)
        self.assertNotIsInstance(v, str)
        self.assertEqual(f"{v}|{v!r}|{v!s}|{v:>20}".count(SECRET), 0)
        for f in (lambda: pickle.dumps(v), lambda: copy.copy(v), lambda: copy.deepcopy(v)):
            with self.assertRaises(TypeError):
                f()
        with self.assertRaises(TypeError):
            hash(v)

    def test_wipe_zeroises_buffer(self):
        """I-4 best-effort memory hygiene."""
        v = SecretValue(SECRET)
        buf = v._buf
        v.wipe()
        self.assertEqual(set(buf), {0})
        with self.assertRaises(ValueError):
            v.reveal()

    def test_logger_redacts_credential_shapes(self):
        """I-5 structured logging redaction."""
        s = io.StringIO()
        JsonLogger(s, lambda: 0).log("info", "x", msg="token=hvs.ABCDEFGHIJKLMNOPQRSTU and AKIAABCDEFGHIJKLMNOP",  # inv55-scan: allow (synthetic redaction fixture)
                                     obj=SecretValue(SECRET))
        out = s.getvalue()
        self.assertNotIn("hvs.ABCDEFGH", out)
        self.assertNotIn("AKIAABCDEFGHIJKLMNOP", out)  # inv55-scan: allow (synthetic redaction fixture)
        self.assertNotIn(SECRET, out)
        self.assertEqual(redact_text("pw " + SECRET, (SECRET,)), "pw ***")

    def test_log_injection_blocked(self):
        """T-2 control characters cannot enter audit records via identifiers."""
        e = Env()
        r = e.resolve(name="a\n{\"allowed\":true}")
        self.assertEqual(code(r), ErrorCode.INVALID_REFERENCE.value.code)


class FailClosed(unittest.TestCase):
    def test_audit_sink_failure_denies(self):
        """R-1 no audit, no access."""
        e = Env()
        e.seed()
        e.sink.fail = True
        r = e.resolve()
        self.assertEqual(code(r), ErrorCode.AUDIT_UNAVAILABLE.value.code)

    def test_clock_rollback_denies(self):
        """T-3 clock rollback cannot extend a lease."""
        e = Env()
        e.seed()
        r = e.resolve(ttl_s=5)
        e.clock.advance(6)
        self.assertFalse(e.use(r["lease_id"])["ok"])
        e.clock.t -= 10
        self.assertEqual(code(e.use(r["lease_id"])), ErrorCode.CLOCK_ROLLBACK.value.code)

    def test_policy_change_takes_effect_immediately(self):
        """E-6 revoked policy is enforced at next call (no stale decision cache)."""
        e = Env()
        e.seed()
        r = e.resolve()
        e.policy.replace([])
        self.assertEqual(code(e.use(r["lease_id"])), ErrorCode.DENIED.value.code)


if __name__ == "__main__":
    unittest.main()
