"""4.3.0 missing-component tests: positive and negative/abuse cases per control (stdlib unittest).

Run from the directory containing the package:  python -m unittest inv64_application_model.tests.test_v43
"""
from __future__ import annotations

import base64
import copy
import datetime as dt
import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path

from inv64_application_model import __version__
from inv64_application_model import manifest as M
from inv64_application_model.activation import TRANSITIONS, ConfigStore, SimulatedCrash
from inv64_application_model.adjacent import Faults, default_adjacent
from inv64_application_model.audit import AuditChainBroken, AuditLog, AuditUnavailable
from inv64_application_model.auth import Authenticator, Principal, TrustConfig, TrustUnavailable, mint
from inv64_application_model.authz import Authorizer, PolicyError, load_policy
from inv64_application_model.errors import CATALOG, Inv64Error, Outcome, error_envelope, outcome_for
from inv64_application_model.explain import DecisionLog, dominant, explain
from inv64_application_model.oam_profile import from_oam, to_oam
from inv64_application_model.overlay import Scope, merge
from inv64_application_model.redaction import REDACTED, find_secrets, redact
from inv64_application_model.rollout import Rollout, rollback_drill
from inv64_application_model.semantics import (OPERATIONS, AdmissionController, CancelToken, Deadline,
                                               IdempotencyStore, RetryPolicy, negotiate)
from inv64_application_model.service import ApplicationModelService
from inv64_application_model.telemetry import (MAX_SERIES_PER_METRIC, Metrics, StructuredLog, child_traceparent,
                                               parse_traceparent)
from inv64_application_model.tenancy import SharedResources, TenantRegistry, check_manifest_tenancy
from inv64_application_model.trust import TrustPolicy, TrustStore, verify_artifact
from inv64_application_model import provenance as P

PKG = Path(__file__).resolve().parents[1]
K = b"k" * 32
GOOD = {"schema": "app/v1", "components": [{"name": "api"}, {"name": "worker"}], "providers": [{"name": "kv"}],
        "links": [{"from": "api", "to": "kv"}], "traits": [{"type": "spread", "component": "api"}]}


class Clock:
    def __init__(self, t=1_800_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


def trust_cfg(**kw):
    return TrustConfig("trust-1", "inv64", {"https://idp": {"k1": ("HS256", K)}}, **kw)


def claims(clk, **over):
    c = {"iss": "https://idp", "sub": "alice", "aud": "inv64", "tid": "acme", "kind": "human", "roles": ["dev"],
         "iat": clk(), "exp": clk() + 600, "jti": "j-" + str(over.pop("n", 0))}
    c.update(over)
    return c


POLICY = {"format": "PK_APP_AUTHZ_POLICY/1", "version": "p1", "grants": [
    {"id": "dev", "roles": ["dev"], "capabilities": ["app.submit", "app.validate", "app.canonicalize"],
     "tenants": ["acme"], "environments": ["prod"], "sites": ["*"], "resources": ["apps/*"]},
    {"id": "cp", "roles": ["control-plane"], "capabilities": ["app.validate"], "tenants": ["acme", "globex"],
     "environments": ["prod"], "sites": ["*"], "resources": ["*"], "kinds": ["service"]}]}


# --------------------------------------------------------------------------- MC-14 / manifest
class SecretsTest(unittest.TestCase):
    CASES = {
        "password field": {"properties": {"DB_PASSWORD": "hunter2"}},
        "nested credentials": {"properties": {"credentials": {"user": "u", "pass": "p"}}},
        "aws key": {"env": "AKIAABCDEFGHIJKLMNOP"},
        "pem": {"x": "-----BEGIN RSA PRIVATE KEY-----\nMIIB"},
        "jwt": {"x": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"},
        "url creds": {"x": "postgres://user:pa55@db/x"},
        "conn string": {"x": "Server=db;User Id=sa;Password=Hunter2;"},
        "signed url": {"x": "https://b.s3/obj?X-Amz-Signature=abcdef0123456789abcdef"},
        "percent-encoded": {"x": "postgres%3A%2F%2Fuser%3Apa55%40db"},
        "base64 pem": {"x": base64.b64encode(b"-----BEGIN PRIVATE KEY-----").decode()},
        "fullwidth key": {"properties": {"ｐａｓｓｗｏｒｄ": "x"}},
        "alt casing": {"properties": {"Api-Key": "zzz"}},
        "array": {"list": ["ok", "ghp_" + "a" * 36]},
    }

    def test_every_inline_secret_class_is_refused_without_echo(self):
        for name, extra in self.CASES.items():
            with self.subTest(name):
                m = copy.deepcopy(GOOD)
                m["components"][0].update(extra)
                issues = M.validate_issues(m)
                self.assertIn("secret.inline", {i.code for i in issues})
                text = " ".join(str(i) for i in issues)
                for v in ("hunter2", "AKIAABCDEFGHIJKLMNOP", "pa55", "Hunter2"):
                    self.assertNotIn(v, text)
                with self.assertRaises(M.ManifestValidationError):
                    M.canonical(m)

    def test_secret_references_are_accepted_and_hashed_as_references(self):
        m = copy.deepcopy(GOOD)
        m["components"][0]["properties"] = {"password": "secretref://vault/db/pw@3", "tokenTTL": 30}
        self.assertEqual(M.validate(m), [])
        self.assertIn(b"secretref://vault/db/pw@3", M.canonical_document(m))

    def test_redaction_of_logs_exceptions_and_nested(self):
        r = redact({"a": {"Password": "x", "note": "Bearer abcdefghijklmnopqrstuvwxyz"},
                    "e": ValueError("postgres://u:p@h/db")})
        self.assertEqual(r["a"]["Password"], REDACTED)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz", json.dumps(r))
        self.assertNotIn("u:p@", r["e"])

    def test_message_never_echoes_credential_like_names(self):
        n = "c0AKIAABCDEFGHIJKLMNOP"
        issues = M.validate_issues({"schema": "app/v1", "components": [{"name": n}, {"name": n}]})
        self.assertFalse(any("AKIA" in str(i) for i in issues))

    def test_benign_values_not_flagged(self):
        m = copy.deepcopy(GOOD)
        m["components"][0]["properties"] = {"image": "registry.local/app:1.2.3", "url": "https://example.com/x?y=1",
                                            "replicas": 3, "tokenLifetime": 60}
        self.assertEqual(find_secrets(m), [])


class ParserHardeningTest(unittest.TestCase):
    def test_deep_nesting_is_a_valueerror_not_recursionerror(self):  # 4.2.0 defect (fuzz R001)
        with self.assertRaises(M.ManifestDepthError):
            M.parse_manifest_json("[" * 100_000 + "]" * 100_000)
        deep: object = 1
        for _ in range(M.MAX_DEPTH + 2):
            deep = [deep]
        self.assertEqual(M.validate_issues(dict(GOOD, x=deep))[0].code, "manifest.too_deep")

    def test_depth_limit_boundary(self):
        ok = "[" * (M.MAX_DEPTH - 1) + "]" * (M.MAX_DEPTH - 1)
        raw = '{"schema":"app/v1","x":' + ok + "}"
        M.parse_manifest_json(raw)
        with self.assertRaises(M.ManifestDepthError):
            M.parse_manifest_json('{"schema":"app/v1","x":' + "[" * M.MAX_DEPTH + "]" * M.MAX_DEPTH + "}")

    def test_brackets_inside_strings_do_not_count(self):
        M.parse_manifest_json(json.dumps(dict(GOOD, note="[" * 500)))

    def test_too_large_has_its_own_type(self):
        with self.assertRaises(M.ManifestTooLargeError):
            M.parse_manifest_json(" " * (M.MAX_MANIFEST_BYTES + 1))


# --------------------------------------------------------------------------- MC-06
class ErrorContractTest(unittest.TestCase):
    def test_envelope_shape_and_catalog(self):
        e = error_envelope("auth.expired", "cid-1", {"x": 1})
        self.assertEqual(set(e), {"version", "code", "status", "message", "retryable", "correlation_id", "details"})
        self.assertEqual(e["version"], "PK_APP_ERROR/1")
        self.assertEqual(error_envelope("no.such.code", None)["code"], "internal")
        for code, (retry, status, msg) in CATALOG.items():
            self.assertIsInstance(retry, bool)
            self.assertTrue(msg)
            self.assertIn(outcome_for(code), Outcome.ALL)

    def test_schemas_parse_and_match_catalog(self):
        schema = json.loads((PKG / "schema" / "error-v1.schema.json").read_text())
        self.assertEqual(sorted(schema["properties"]["code"]["enum"]), sorted(CATALOG))
        for f in (PKG / "schema").glob("*.json"):
            json.loads(f.read_text())


# --------------------------------------------------------------------------- MC-07
class AuthnTest(unittest.TestCase):
    def setUp(self):
        self.clk = Clock()
        self.a = Authenticator(lambda: trust_cfg(), clock=self.clk)

    def tok(self, **kw):
        return mint(claims(self.clk, **kw), kid="k1", key=K)

    def code(self, token, **kw):
        with self.assertRaises(Inv64Error) as cm:
            self.a.authenticate(token, **kw)
        return cm.exception.code

    def test_valid(self):
        p = self.a.authenticate(self.tok())
        self.assertEqual((p.subject, p.tenant, p.roles), ("alice", "acme", ("dev",)))

    def test_negative_paths(self):
        t = self.tok(n=1)
        parts = t.split(".")
        forged = ".".join(parts[:3] + [base64.urlsafe_b64encode(b"x" * 32).decode().rstrip("=")])
        none_alg = "v1." + base64.urlsafe_b64encode(b'{"alg":"none","kid":"k1"}').decode().rstrip("=") + "." + parts[2] + "."
        self.assertEqual(self.code(None), "auth.missing")
        self.assertEqual(self.code("garbage"), "auth.malformed")
        self.assertEqual(self.code(forged), "auth.signature")
        self.assertEqual(self.code(none_alg), "auth.algorithm")
        self.assertEqual(self.code(mint(claims(self.clk, n=2), kid="k1", key=b"x" * 32)), "auth.signature")
        self.assertEqual(self.code(mint(claims(self.clk, n=3), kid="k9", key=K)), "auth.signature")
        self.assertEqual(self.code(self.tok(n=4, iss="https://evil")), "auth.issuer")
        self.assertEqual(self.code(self.tok(n=5, aud="other")), "auth.audience")
        self.assertEqual(self.code(self.tok(n=6, iat=self.clk() - 7200, exp=self.clk() - 3600)), "auth.expired")
        self.assertEqual(self.code(self.tok(n=7, iat=self.clk() + 600, nbf=self.clk() + 600, exp=self.clk() + 900)), "auth.not_yet_valid")
        self.assertEqual(self.code(self.tok(n=8, exp=self.clk() + 86_400)), "auth.lifetime")
        self.assertEqual(self.code(self.tok(n=9, kind="root")), "auth.malformed")

    def test_replay_and_revocation(self):
        t = self.tok(n=10)
        self.a.authenticate(t)
        self.assertEqual(self.code(t), "auth.replay")
        a2 = Authenticator(lambda: trust_cfg(revoked_subjects=frozenset({"alice"})), clock=self.clk)
        with self.assertRaises(Inv64Error) as cm:
            a2.authenticate(self.tok(n=11))
        self.assertEqual(cm.exception.code, "auth.revoked")

    def test_channel_binding(self):
        t = self.tok(n=12, cnf="tls-exporter-abc")
        self.assertEqual(self.code(t, channel_binding="other"), "auth.signature")
        self.assertEqual(self.a.authenticate(self.tok(n=13, cnf="tls-exporter-abc"), channel_binding="tls-exporter-abc").subject, "alice")

    def test_failure_rate_limit_is_per_source(self):
        a = Authenticator(lambda: trust_cfg(), clock=self.clk, failure_limit=3)
        for _ in range(3):
            with self.assertRaises(Inv64Error):
                a.authenticate("bad", source="attacker")
        with self.assertRaises(Inv64Error) as cm:
            a.authenticate(self.tok(n=14), source="attacker")
        self.assertEqual(cm.exception.code, "auth.rate_limited")
        self.assertEqual(a.authenticate(self.tok(n=15), source="victim-tenant-host").tenant, "acme")

    def test_trust_outage_cached_then_closed(self):
        up = {"on": True}

        def src():
            if not up["on"]:
                raise TrustUnavailable()
            return trust_cfg()
        a = Authenticator(src, clock=self.clk, cache_ttl_s=60)
        a.authenticate(self.tok(n=16))
        up["on"] = False
        self.clk.t += 30
        a.authenticate(self.tok(n=17))
        self.clk.t += 60
        with self.assertRaises(Inv64Error) as cm:
            a.authenticate(self.tok(n=18))
        self.assertEqual(cm.exception.code, "auth.trust_unavailable")

    def test_breakglass_lifetime_is_shorter(self):
        self.assertEqual(self.code(self.tok(n=19, kind="breakglass", exp=self.clk() + 1800)), "auth.lifetime")
        self.assertTrue(self.a.authenticate(self.tok(n=20, kind="breakglass", exp=self.clk() + 600)).breakglass)

    def test_eddsa_when_backend_present(self):
        try:
            priv, pub = P.ed25519_keypair()
        except ImportError:
            self.skipTest("cryptography not installed (optional)")
        a = Authenticator(lambda: TrustConfig("t", "inv64", {"https://idp": {"e1": ("EdDSA", pub)}}), clock=self.clk)
        self.assertEqual(a.authenticate(mint(claims(self.clk, n=21), kid="e1", key=priv, alg="EdDSA")).subject, "alice")
        # algorithm confusion: HS256 token signed with the public key bytes must fail
        with self.assertRaises(Inv64Error):
            a.authenticate(mint(claims(self.clk, n=22), kid="e1", key=pub, alg="HS256"))


# --------------------------------------------------------------------------- MC-08
class AuthzTest(unittest.TestCase):
    def setUp(self):
        self.az = Authorizer(POLICY)
        self.dev = Principal("alice", "acme", "human", ("dev",), "i", "j", 0)
        self.cp = Principal("inv66", "platform", "service", ("control-plane",), "i", "j", 0)

    def d(self, p, cap, tenant="acme", env="prod", res="apps/shop"):
        return self.az.decide(p, cap, tenant=tenant, environment=env, site="s1", resource=res)

    def test_allow_and_deny_by_default(self):
        self.assertTrue(self.d(self.dev, "app.submit").allowed)
        self.assertEqual(self.d(self.dev, "config.activate").code, "authz.denied")  # vertical escalation
        self.assertEqual(self.d(self.dev, "made.up").code, "authz.denied")
        self.assertEqual(self.d(self.dev, "app.submit", env="staging").code, "authz.denied")
        self.assertEqual(self.d(self.dev, "app.submit", res="policies/x").code, "authz.denied")

    def test_cross_tenant(self):
        self.assertEqual(self.d(self.dev, "app.submit", tenant="globex").code, "tenant.mismatch")  # horizontal
        self.assertTrue(self.d(self.cp, "app.validate", tenant="globex").allowed)
        self.assertFalse(self.d(self.cp, "app.validate", tenant="initech").allowed)  # not named -> denied
        self.assertFalse(self.d(self.cp, "app.submit", tenant="acme").allowed)

    def test_policy_rules_fail_closed(self):
        bad = [dict(POLICY, grants=[dict(POLICY["grants"][0], tenants=["*"])]),
               dict(POLICY, grants=[dict(POLICY["grants"][0], capabilities=["root"])]),
               dict(POLICY, grants=[dict(POLICY["grants"][0], resources=["a*b"])]),
               dict(POLICY, format="v0"),
               dict(POLICY, separation_of_duties=[["app.submit", "app.validate"]])]
        for doc in bad:
            with self.assertRaises(PolicyError):
                load_policy(doc)
        before = self.az.policy.digest
        with self.assertRaises(PolicyError):
            self.az.activate(bad[0])
        self.assertEqual(self.az.policy.digest, before)  # failed activation leaves the old policy
        empty = Authorizer()
        self.assertEqual(empty.decide(self.dev, "app.submit", tenant="acme", environment="prod", site="s", resource="apps/x").code,
                         "authz.policy_invalid")

    def test_rollback_and_version_in_decision(self):
        self.az.activate(dict(POLICY, version="p2"))
        self.assertEqual(self.d(self.dev, "app.submit").policy_version, "p2")
        self.az.rollback()
        self.assertEqual(self.d(self.dev, "app.submit").policy_version, "p1")

    def test_breakglass_requires_breakglass_principal(self):
        pol = dict(POLICY, grants=POLICY["grants"] + [{"id": "bg", "roles": ["dev"], "capabilities": ["breakglass"],
                                                      "tenants": ["acme"], "environments": ["prod"], "sites": ["*"], "resources": ["*"]}])
        az = Authorizer(pol)
        self.assertFalse(az.decide(self.dev, "breakglass", tenant="acme", environment="prod", site="s", resource="x").allowed)
        bg = Principal("alice", "acme", "breakglass", ("dev",), "i", "j", 0, True)
        self.assertTrue(az.decide(bg, "breakglass", tenant="acme", environment="prod", site="s", resource="x").allowed)


# --------------------------------------------------------------------------- MC-09
class SemanticsTest(unittest.TestCase):
    def test_deadline_bounds_and_propagation(self):
        clk = Clock()
        with self.assertRaises(Inv64Error):
            Deadline.for_operation("submit", 0, clock=clk)
        with self.assertRaises(Inv64Error):
            Deadline.for_operation("submit", OPERATIONS["submit"]["max_ms"] + 1, clock=clk)
        d = Deadline.for_operation("submit", 5_000, clock=clk, inbound_expires_at_ms=clk() * 1000 + 100)
        self.assertLessEqual(d.remaining_ms(), 100)  # never extended past the inbound deadline
        clk.t += 1
        with self.assertRaises(Inv64Error) as cm:
            d.check()
        self.assertEqual(cm.exception.code, "deadline.exceeded")

    def test_retry_bounded_and_nonretryable_immediate(self):
        import random
        calls = []

        def flaky():
            calls.append(1)
            raise Inv64Error("admission.overloaded")
        rp = RetryPolicy(max_attempts=3)
        with self.assertRaises(Inv64Error):
            rp.run(flaky, operation="validate", sleep=lambda s: None, rng=random.Random(1))
        self.assertEqual(len(calls), 3)
        calls.clear()
        with self.assertRaises(Inv64Error):
            rp.run(lambda: (calls.append(1), (_ for _ in ()).throw(Inv64Error("auth.expired")))[1],
                   operation="validate", sleep=lambda s: None)
        self.assertEqual(len(calls), 1)
        with self.assertRaises(ValueError):
            rp.run(lambda: 1, operation="submit")  # state-changing: no automatic retry

    def test_retry_budget_prevents_storm(self):
        import random
        rp = RetryPolicy(max_attempts=10, budget_tokens=2)
        n = []

        def fail():
            n.append(1)
            raise Inv64Error("admission.overloaded")
        for _ in range(3):
            with self.assertRaises(Inv64Error):
                rp.run(fail, operation="validate", sleep=lambda s: None, rng=random.Random(2))
        self.assertLessEqual(len(n), 3 + 2)

    def test_cancellation(self):
        c = CancelToken()
        c.cancel("user")
        with self.assertRaises(Inv64Error) as cm:
            c.check()
        self.assertEqual(cm.exception.code, "request.cancelled")

    def test_idempotency(self):
        s = IdempotencyStore(clock=Clock())
        key = "k" * 20
        with s.claim("acme", key, "d1") as (rep, h):
            self.assertFalse(rep)
            h["response"] = {"ok": 1}
        with s.claim("acme", key, "d1") as (rep, h):
            self.assertTrue(rep)
            self.assertEqual(h["response"], {"ok": 1})
        with self.assertRaises(Inv64Error) as cm:
            with s.claim("acme", key, "d2"):
                pass
        self.assertEqual(cm.exception.code, "idempotency.conflict")
        with s.claim("globex", key, "d2") as (rep, _):  # tenant-scoped: no collision
            self.assertFalse(rep)
        with self.assertRaises(Inv64Error):
            with s.claim("acme", "short", "d"):
                pass

    def test_admission_bounded_per_tenant(self):
        adm = AdmissionController(max_inflight=2, per_tenant_max=1)
        with adm.admit("a"):
            with self.assertRaises(Inv64Error) as cm:
                with adm.admit("a"):
                    pass
            self.assertEqual(cm.exception.code, "admission.tenant_quota")
            with adm.admit("b"):
                with self.assertRaises(Inv64Error) as cm2:
                    with adm.admit("c"):
                        pass
                self.assertEqual(cm2.exception.code, "admission.overloaded")
        self.assertEqual(adm.inflight, 0)

    def test_version_negotiation(self):
        self.assertEqual(negotiate(["PK_APP_SUBMIT/1", "PK_APP_SUBMIT/2"]), "PK_APP_SUBMIT/2")
        with self.assertRaises(Inv64Error) as cm:
            negotiate(["PK_APP_SUBMIT/9"])
        self.assertEqual(cm.exception.code, "version.unsupported")
        with self.assertRaises(Inv64Error) as cm:
            negotiate(["PK_APP_SUBMIT/1"], required_features=frozenset({"channel-binding"}))
        self.assertEqual(cm.exception.code, "version.downgrade_refused")


# --------------------------------------------------------------------------- service boundary (MC-06/07/08/09/16/18/24/25)
class ServiceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.clk = Clock()
        self.audit = AuditLog(Path(self.tmp.name) / "audit.jsonl", clock=self.clk)
        self.svc = ApplicationModelService(authenticator=Authenticator(lambda: trust_cfg(), clock=self.clk),
                                           authorizer=Authorizer(POLICY), audit=self.audit, clock=self.clk)
        self.n = 0

    def tearDown(self):
        self.tmp.cleanup()

    def tok(self, **kw):
        self.n += 1
        return mint(claims(self.clk, n=self.n, **kw), kid="k1", key=K)

    def req(self, **kw):
        r = {"format": "PK_APP_SUBMIT_REQUEST/1", "version": "PK_APP_SUBMIT/2", "operation": "submit", "tenant": "acme",
             "environment": "prod", "site": "s1", "app": "shop", "manifest_json": json.dumps(GOOD),
             "idempotency_key": "idem-" + "a" * 16}
        r.update(kw)
        return r

    def test_accept_and_response_contract(self):
        r = self.svc.handle(self.req(), token=self.tok(), traceparent="00-" + "1" * 32 + "-" + "2" * 16 + "-01")
        self.assertEqual(r["outcome"], "success")
        self.assertEqual(r["result"]["canonical"]["digest"], M.canonical(GOOD))
        self.assertEqual(r["traceparent"].split("-")[1], "1" * 32)  # trace continued
        self.assertEqual(len(self.svc.registry.list("acme")), 1)
        self.assertGreaterEqual(self.audit.verify(), 3)  # authn + authz + submit

    def test_unauthenticated_request_gets_no_semantic_processing(self):
        bad_manifest = self.req(manifest_json='{"schema":"app/v1","components":[{"name":"a","x":"AKIAABCDEFGHIJKLMNOP"}]}')
        r = self.svc.handle(bad_manifest, token=None)
        self.assertEqual(r["error"]["code"], "auth.missing")
        self.assertIsNone(r["result"])
        self.assertFalse(self.svc.decisions.find(tenant="acme"))

    def test_rejections_are_typed(self):
        cases = [
            (self.req(format="x"), "request.invalid"),
            (self.req(extra_field=1), "request.invalid"),
            (self.req(version="PK_APP_SUBMIT/7"), "version.unsupported"),
            (self.req(tenant="globex"), "tenant.mismatch"),
            (self.req(operation="validate", manifest_json='{"schema":'), "manifest.parse"),
            (self.req(operation="validate", manifest_json='{"schema":"app/v1","schema":"app/v1"}'), "manifest.duplicate_key"),
            (self.req(operation="validate", manifest_json="[" * 100 + "]" * 100), "manifest.too_deep"),
            (self.req(operation="validate", manifest_json=json.dumps(dict(GOOD, links=[{"from": "api", "to": "ghost"}]))), "manifest.invalid"),
            (self.req(operation="validate", deadline_ms=10 ** 9), "deadline.invalid"),
            (self.req(operation="validate", manifest_json=json.dumps(dict(GOOD, tenant="globex"))), "tenant.mismatch"),
        ]
        for req, code in cases:
            with self.subTest(code):
                r = self.svc.handle(req, token=self.tok())
                self.assertEqual(r["error"]["code"], code)
                self.assertEqual(r["error"]["version"], "PK_APP_ERROR/1")
                self.assertIsNotNone(r["correlation_id"])

    def _schema_check(self, doc, schema_file):
        schema = json.loads((PKG / "schema" / schema_file).read_text())
        try:
            import jsonschema
            from referencing import Registry, Resource
            reg = Registry().with_resource("urn:inv64:error:v1", Resource.from_contents(
                json.loads((PKG / "schema" / "error-v1.schema.json").read_text())))
            jsonschema.Draft202012Validator(schema, registry=reg).validate(doc)
        except ImportError:  # structural fallback so the contract test never skips
            for k in schema.get("required", []):
                self.assertIn(k, doc)

    def test_responses_match_published_schemas(self):
        ok = self.svc.handle(self.req(), token=self.tok())
        self._schema_check(ok, "submit-response-v1.schema.json")
        bad = self.svc.handle(self.req(operation="validate", manifest_json=json.dumps(dict(GOOD, links=[{"from": "x", "to": "y"}]))),
                              token=self.tok())
        self._schema_check(bad, "submit-response-v1.schema.json")
        self._schema_check(bad["error"], "error-v1.schema.json")
        denied = self.svc.handle(self.req(), token=None)
        self._schema_check(denied, "submit-response-v1.schema.json")
        self._schema_check(self.svc.status(), "status-v1.schema.json")
        self._schema_check(self.req(), "submit-request-v1.schema.json")
        for rec in self.audit.records():
            self._schema_check(rec, "audit-v1.schema.json")
        for d in self.svc.decisions.find():
            self._schema_check(d, "decision-v1.schema.json")

    def test_invalid_manifest_issues_sorted_and_bounded(self):
        m = dict(GOOD, links=[{"from": f"g{i}", "to": "kv"} for i in range(1500)])
        r = self.svc.handle(self.req(operation="validate", manifest_json=json.dumps(m)), token=self.tok())
        self.assertEqual(r["result"]["issue_count"], 1500)
        self.assertEqual(len(r["result"]["issues"]), 1000)
        self.assertTrue(r["result"]["truncated"])
        paths = [(i["path"], i["code"]) for i in r["result"]["issues"]]
        self.assertEqual(paths, sorted(paths))

    def test_idempotent_duplicate_and_conflict(self):
        r1 = self.svc.handle(self.req(), token=self.tok())
        r2 = self.svc.handle(self.req(), token=self.tok())
        self.assertTrue(r2["replayed"])
        self.assertEqual(r1["result"], r2["result"])
        r3 = self.svc.handle(self.req(manifest_json=json.dumps(dict(GOOD, traits=[]))), token=self.tok())
        self.assertEqual(r3["error"]["code"], "idempotency.conflict")
        effects = [x for x in self.audit.records() if x["operation"] == "app.submit" and x["outcome"] == "accepted"]
        self.assertEqual(len(effects), 1)

    def test_submit_is_refused_when_audit_cannot_record(self):
        class Broken:
            def __call__(self, p):
                raise OSError("ro")
        svc = ApplicationModelService(authenticator=Authenticator(lambda: trust_cfg(), clock=self.clk),
                                      authorizer=Authorizer(POLICY),
                                      audit=AuditLog(Path(self.tmp.name) / "b.jsonl", opener=Broken(), buffer_limit=1000),
                                      clock=self.clk)
        r = svc.handle(self.req(), token=self.tok())
        self.assertEqual(r["error"]["code"], "internal")
        self.assertEqual(svc.registry.list("acme"), [])  # nothing registered without its audit record

    def test_telemetry_logs_and_explain_are_safe(self):
        self.svc.handle(self.req(operation="validate", manifest_json=json.dumps(
            dict(GOOD, components=[{"name": "api", "p": {"password": "hunter2"}}]))), token=self.tok())
        blob = json.dumps(self.svc.log.records()) + json.dumps(self.svc.decisions.find()) + self.svc.metrics.exposition()
        self.assertNotIn("hunter2", blob)
        self.assertIn('inv64_rejections_total{operation="validate",code="manifest.invalid"} 1', self.svc.metrics.exposition())
        ex = explain(self.svc.decisions.find(), viewer_tenant="globex")
        self.assertEqual(ex["decisions"], [])
        ex = explain(self.svc.decisions.find(), viewer_tenant="acme")
        self.assertEqual(ex["decisions"][0]["dominant_constraint"], "security")

    def test_emergency_disable(self):
        self.svc.emergency_disable(actor="oncall", reason="bad rollout")
        r = self.svc.handle(self.req(), token=self.tok())
        self.assertEqual(r["error"]["code"], "service.disabled")
        self.assertEqual(self.svc.status()["state"], "blocked")
        self.svc.emergency_enable(actor="oncall", reason="fixed")
        self.assertEqual(self.svc.handle(self.req(), token=self.tok())["outcome"], "success")
        ops = [x["operation"] for x in self.audit.records()]
        self.assertIn("service.emergency_disable", ops)

    def test_status_readiness(self):
        st = self.svc.status()
        self.assertEqual((st["live"], st["ready"], st["state"]), (True, True, "ready"))
        self.assertEqual(st["versions"]["component"], __version__)
        self.svc.register_dependency("pk_core", lambda: False)
        st = self.svc.status()
        self.assertEqual((st["ready"], st["state"]), (False, "blocked"))
        self.assertEqual(st["reasons"][0]["code"], "dependency.unhealthy")
        self.svc.register_dependency("pk_core", lambda: True)
        self.svc.register_dependency("telemetry-exporter", lambda: False, required=False)
        self.assertEqual(self.svc.status()["state"], "degraded")
        empty = ApplicationModelService(authenticator=self.svc.authn, authorizer=Authorizer(), audit=self.audit)
        self.assertEqual(empty.status()["reasons"][0]["code"], "policy.missing")


# --------------------------------------------------------------------------- MC-12/13
class OverlayActivationTest(unittest.TestCase):
    def ov(self, **kw):
        o = {"format": "PK_APP_OVERLAY/1", "id": "o1", "version": 1,
             "scope": {"tenant": "acme", "environment": "prod"}, "base_digest": M.canonical(GOOD),
             "author": "alice", "approval": {"approver": "bob", "ref": "CHG-1"},
             "set": [{"path": "components[api].properties.replicas", "value": 3}]}
        o.update(kw)
        return o

    def code(self, overlays, scope=Scope("acme", "prod", "eu1")):
        with self.assertRaises(Inv64Error) as cm:
            merge(GOOD, overlays, scope)
        return cm.exception.code

    def test_merge_deterministic_and_precedence(self):
        site = self.ov(id="o2", scope={"tenant": "acme", "environment": "prod", "site": "eu1"},
                       set=[{"path": "components[api].properties.replicas", "value": 6}])
        e1 = merge(GOOD, [self.ov(), site], Scope("acme", "prod", "eu1"))
        e2 = merge(GOOD, [site, self.ov()], Scope("acme", "prod", "eu1"))
        self.assertEqual(e1["digest"], e2["digest"])
        self.assertEqual(e1["manifest"]["components"][0]["properties"]["replicas"], 6)  # site beats environment
        self.assertEqual([o["id"] for o in e1["overlays"]], ["o1", "o2"])

    def test_negative_overlays(self):
        self.assertEqual(self.code([self.ov(set=[{"path": "schema", "value": "app/v2"}])]), "overlay.immutable")
        self.assertEqual(self.code([self.ov(set=[{"path": "components[api].name", "value": "x"}])]), "overlay.immutable")
        self.assertEqual(self.code([self.ov(scope={"tenant": "globex", "environment": "prod"})]), "overlay.scope")
        self.assertEqual(self.code([self.ov(base_digest="0" * 64)]), "overlay.stale_parent")
        self.assertEqual(self.code([self.ov(), self.ov(id="o3")]), "overlay.conflict")
        self.assertEqual(self.code([self.ov(approval={"approver": "alice"})]), "overlay.invalid")
        self.assertEqual(self.code([self.ov(set=[{"path": "components[ghost].properties.x", "value": 1}])]), "overlay.invalid")
        self.assertEqual(self.code([self.ov(set=[{"path": "components[api].properties.password", "value": "p"}])]), "manifest.invalid")
        with self.assertRaises(Inv64Error) as cm:
            merge(GOOD, [self.ov()], Scope("acme", "prod", "eu1"), authorize=lambda author, o: author == "carol")
        self.assertEqual(cm.exception.code, "authz.denied")
        replay = [merge(GOOD, [self.ov()], Scope("acme", "prod", "eu1"))["digest"] for _ in range(3)]
        self.assertEqual(len(set(replay)), 1)  # deterministic replay

    def eff(self, tag):
        m = dict(GOOD, **{"x-tag": tag})
        return {"scope": {"tenant": "acme"}, "manifest": m, "digest": M.canonical(m)}

    def test_activation_rollback_quarantine_and_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            audit = AuditLog(Path(d) / "a.jsonl")
            s = ConfigStore(Path(d) / "s", audit=audit)
            r1 = s.propose(self.eff("1"), actor="op", release=__version__, validator=M.validate)
            s.activate(r1, actor="op", expected_active=None)
            r2 = s.propose(self.eff("2"), actor="op", release=__version__, validator=M.validate)
            with self.assertRaises(Inv64Error) as cm:
                s.activate(r2, actor="op", expected_active="rev-999999")
            self.assertEqual(cm.exception.code, "activation.conflict")
            res = s.activate(r2, actor="op", expected_active=r1, health_probe=lambda e: False)
            self.assertEqual(res["result"], "rolled_back")
            self.assertEqual(s.state["active"], r1)
            self.assertEqual(s.state["revisions"][r2]["state"], "quarantined")
            with self.assertRaises(Inv64Error):
                s.propose(self.eff("2"), actor="op", release="x", validator=M.validate)
            with self.assertRaises(Inv64Error):
                s.reapprove(self.eff("2")["digest"], approver="op")  # same actor cannot lift
            s.reapprove(self.eff("2")["digest"], approver="lead")
            r3 = s.propose(self.eff("2"), actor="op", release="x", validator=M.validate)
            s.activate(r3, actor="op", expected_active=r1)
            self.assertEqual(s.rollback(actor="op", reason="manual")["active"], r1)
            self.assertEqual(s.rollback(actor="op", reason="again", to=r1)["result"], "noop")
            self.assertGreater(audit.verify(), 5)

    def test_crash_recovery_each_phase(self):
        for phase, expect_new in (("prepare", False), ("commit", True)):
            with self.subTest(phase), tempfile.TemporaryDirectory() as d:
                s = ConfigStore(d)
                r1 = s.propose(self.eff("1"), actor="op", release="x", validator=M.validate)
                s.activate(r1, actor="op", expected_active=None)
                r2 = s.propose(self.eff("2"), actor="op", release="x", validator=M.validate)
                s.crash_at = phase
                with self.assertRaises(SimulatedCrash):
                    s.activate(r2, actor="op", expected_active=r1)
                s2 = ConfigStore(d)
                self.assertEqual(s2.state["active"], r2 if expect_new else r1)
                self.assertIsNone(s2.state["pending"])
                self.assertIsNone(ConfigStore(d).recovery)  # converged: second restart is a no-op

    def test_lifecycle_table_has_no_path_out_of_rejected(self):
        self.assertEqual(TRANSITIONS["rejected"], frozenset())
        self.assertNotIn("active", TRANSITIONS["quarantined"])


# --------------------------------------------------------------------------- MC-15 / MC-39
class TrustTest(unittest.TestCase):
    def setUp(self):
        self.data = b"artifact-bytes"
        self.stmt = P.statement([{"name": "a.whl", "digest": {"sha256": hashlib.sha256(self.data).hexdigest()}}],
                                version="4.3.0", builder_id="ci://protected", invocation={"source": "repo@main"},
                                dependencies=[])
        self.key = b"s" * 32
        pol = TrustPolicy("tp1", {"sig1": {"alg": "hmac-sha256", "key": self.key, "not_after": None}},
                          {"wheel": {"signers": ["sig1"], "builders": ["ci://protected"], "sources": ["repo@main"],
                                     "min_version": "4.2.0", "allowed_versions": None}})
        self.store = TrustStore(root_keys={})
        self.store.active = pol

    def env(self, stmt=None, key=None, kid="sig1"):
        return P.sign(stmt or self.stmt, key=key or self.key, key_id=kid)

    def code(self, **kw):
        args = dict(data=self.data, artifact_class="wheel", version="4.3.0", envelope=self.env(), store=self.store)
        args.update(kw)
        with self.assertRaises(Inv64Error) as cm:
            verify_artifact(**args)
        return cm.exception.code

    def test_accept(self):
        r = verify_artifact(self.data, artifact_class="wheel", version="4.3.0", envelope=self.env(), store=self.store)
        self.assertEqual((r["result"], r["policy_version"]), ("PASS", "tp1"))

    def test_rejections(self):
        self.assertEqual(self.code(data=b"tampered"), "artifact.digest")
        self.assertEqual(self.code(envelope=self.env(key=b"x" * 32)), "artifact.signature")
        self.assertEqual(self.code(envelope=self.env(kid="unknown")), "artifact.signature")
        self.assertEqual(self.code(envelope={"payloadType": "x"}), "artifact.signature")
        bad_builder = json.loads(json.dumps(self.stmt))
        bad_builder["predicate"]["runDetails"]["builder"]["id"] = "laptop"
        self.assertEqual(self.code(envelope=self.env(stmt=bad_builder)), "artifact.provenance")
        old = json.loads(json.dumps(self.stmt))
        old["predicate"]["buildDefinition"]["externalParameters"]["version"] = "4.1.0"
        self.assertEqual(self.code(version="4.1.0", envelope=self.env(stmt=old)), "artifact.version")
        self.store.active.denied_digests = frozenset({hashlib.sha256(self.data).hexdigest()})
        self.assertEqual(self.code(), "artifact.revoked")

    def test_revoked_signer_and_downgrade(self):
        verify_artifact(self.data, artifact_class="wheel", version="4.3.0", envelope=self.env(), store=self.store)
        older = json.loads(json.dumps(self.stmt))
        older["predicate"]["buildDefinition"]["externalParameters"]["version"] = "4.2.5"
        self.assertEqual(self.code(version="4.2.5", envelope=self.env(stmt=older)), "artifact.version")  # below floor seen
        self.store.active.signers["sig1"]["revoked"] = True
        self.assertEqual(self.code(), "artifact.revoked")

    def test_policy_activation_requires_root_signature(self):
        body = b'{"policy": 2}'
        st = P.statement([{"name": "policy", "digest": {"sha256": hashlib.sha256(body).hexdigest()}}], version="2",
                         builder_id="sec", invocation={}, dependencies=[])
        store = TrustStore(root_keys={"root": ("hmac-sha256", b"r" * 32)})
        with self.assertRaises(Inv64Error):
            store.activate(TrustPolicy("tp2", {}, {}), P.sign(st, key=b"x" * 32, key_id="root"), body)
        store.activate(TrustPolicy("tp2", {}, {}), P.sign(st, key=b"r" * 32, key_id="root"), body)
        self.assertEqual(store.active.version, "tp2")


# --------------------------------------------------------------------------- MC-16
class TenancyTest(unittest.TestCase):
    def test_cross_tenant_refs(self):
        check_manifest_tenancy(GOOD, "acme", SharedResources())
        with self.assertRaises(Inv64Error):
            check_manifest_tenancy(dict(GOOD, providers=[{"name": "kv", "tenant": "globex"}]), "acme", SharedResources())
        check_manifest_tenancy(dict(GOOD, providers=[{"name": "kv", "tenant": "platform"}]), "acme",
                               SharedResources({"kv": frozenset({"acme"})}))

    def test_registry_partition_and_restore(self):
        r = TenantRegistry()
        r.put("acme", "prod", "../../etc/passwd", {"digest": "d"})
        self.assertEqual(r.list("globex"), [])
        with self.assertRaises(Inv64Error):
            r.restore("globex", r.list("acme"))


# --------------------------------------------------------------------------- MC-17
class CryptoTest(unittest.TestCase):
    def test_seal_rotate_retire(self):
        try:
            from inv64_application_model.crypto_policy import KeyProvider, KeyRing, open_sealed, rewrap, seal
            import cryptography  # noqa: F401
        except ImportError:
            self.skipTest("cryptography not installed (optional backend)")
        keys = {"k1": b"1" * 32, "k2": b"2" * 32}
        ring = KeyRing(KeyProvider(lambda kid: keys[kid]), {"k1": "active"})
        obj = seal(b"secret evidence", ring, aad=b"acme")
        self.assertNotIn(b"secret evidence", json.dumps(obj).encode())
        self.assertEqual(obj["kid"], "k1")
        ring.rotate("k2")
        self.assertEqual(open_sealed(obj, ring, aad=b"acme"), b"secret evidence")  # decrypt-only window
        new = rewrap(obj, ring, aad=b"acme")
        self.assertEqual(new["kid"], "k2")
        ring.retire("k1")
        with self.assertRaises(Inv64Error) as cm:
            open_sealed(obj, ring, aad=b"acme")
        self.assertEqual(cm.exception.code, "crypto.key_retired")
        with self.assertRaises(Inv64Error):
            open_sealed(new, ring, aad=b"globex")  # AAD binds tenant

    def test_tls_policy_and_outage_rules(self):
        import ssl
        from inv64_application_model.crypto_policy import OUTAGE_RULES, outage_decision, tls_context
        ctx = tls_context(server=False)
        self.assertGreaterEqual(ctx.minimum_version, ssl.TLSVersion.TLSv1_2)
        self.assertTrue(ctx.check_hostname)
        self.assertEqual(tls_context(server=True).verify_mode, ssl.CERT_REQUIRED)
        self.assertEqual(outage_decision("identity", cached_age_s=10, new_trust=False), "allow-cached")
        for svc in OUTAGE_RULES:
            with self.assertRaises(Inv64Error):
                outage_decision(svc, cached_age_s=10, new_trust=True)
        with self.assertRaises(Inv64Error):
            outage_decision("unknown-service", cached_age_s=0, new_trust=False)


# --------------------------------------------------------------------------- MC-18
class AuditTest(unittest.TestCase):
    def test_tamper_detection(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.jsonl"
            log = AuditLog(p, mac_key=b"m" * 32)
            for i in range(5):
                log.append("op", actor="a", outcome="ok", token="should-not-appear", n=i)
            self.assertNotIn("should-not-appear", p.read_text())
            anchor = Path(d) / "anchor.json"
            log.seal(anchor, key=b"z" * 32)
            self.assertEqual(log.verify(anchor_path=anchor, anchor_key=b"z" * 32), 5)
            lines = p.read_text().splitlines()
            mutations = {
                "mutate": lines[:2] + [lines[2].replace('"ok"', '"no"')] + lines[3:],
                "delete": lines[:2] + lines[3:],
                "reorder": [lines[1], lines[0]] + lines[2:],
                "duplicate": lines + [lines[-1]],
                "truncate": lines[:3],
            }
            for name, body in mutations.items():
                with self.subTest(name):
                    p.write_text("\n".join(body) + "\n")
                    with self.assertRaises(AuditChainBroken):
                        AuditLog(p, mac_key=b"m" * 32).verify(anchor_path=anchor, anchor_key=b"z" * 32)
            p.write_text("\n".join(lines) + "\n")
            forged = json.loads(anchor.read_text())
            forged["seq"] = 3
            anchor.write_text(json.dumps(forged))
            with self.assertRaises(AuditChainBroken):
                AuditLog(p, mac_key=b"m" * 32).verify(anchor_path=anchor, anchor_key=b"z" * 32)

    def test_restart_continuity_and_injection(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.jsonl"
            AuditLog(p).append("op", actor="evil\n{\"seq\":99}", outcome="ok")
            log = AuditLog(p)
            log.append("op", actor="b", outcome="ok")
            self.assertEqual(log.verify(), 2)

    def test_fail_closed_append(self):
        with tempfile.TemporaryDirectory() as d:
            class Broken:
                def __call__(self, p):
                    raise OSError("x")
            log = AuditLog(Path(d) / "a.jsonl", opener=Broken())
            head = log.head()
            with self.assertRaises(AuditUnavailable):
                log.append("activation.commit", actor="a", outcome="ok", fail_closed=True)
            self.assertEqual(log.head(), head)


# --------------------------------------------------------------------------- MC-24
class TelemetryTest(unittest.TestCase):
    def test_cardinality_bound(self):
        m = Metrics()
        for i in range(MAX_SERIES_PER_METRIC + 50):
            m.inc("inv64_rejections_total", operation="submit", code=f"evil-{i}")
        self.assertEqual(len(m.snapshot()["inv64_rejections_total"]), MAX_SERIES_PER_METRIC + 1)
        self.assertEqual(m.get("inv64_telemetry_label_overflow_total", metric="inv64_rejections_total"), 50)
        with self.assertRaises(KeyError):
            m.inc("inv64_requests_total", tenant="acme")  # tenant is not an allowed label
        with self.assertRaises(KeyError):
            m.inc("not_in_catalog")

    def test_log_ring_bounded_and_sink_failure_counted(self):
        met = Metrics()

        def sink(_):
            raise IOError("down")
        log = StructuredLog(capacity=3, sink=sink, metrics=met)
        for i in range(5):
            log.emit("INFO", "validate", outcome="success", password="x")
        self.assertEqual(len(log.records()), 3)
        self.assertEqual(log.dropped, 2)
        self.assertEqual(met.get("inv64_telemetry_sink_errors_total", sink="log"), 5)
        self.assertEqual(log.records()[0]["detail"]["password"], REDACTED)

    def test_traceparent(self):
        tp = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
        self.assertEqual(parse_traceparent(tp)[0], "a" * 32)
        for bad in ("", "00-" + "0" * 32 + "-" + "b" * 16 + "-01", "ff-" + "a" * 32 + "-" + "b" * 16 + "-01", "junk"):
            self.assertIsNone(parse_traceparent(bad))
        out, tid, span = child_traceparent(tp)
        self.assertEqual(tid, "a" * 32)
        self.assertNotEqual(span, "b" * 16)


# --------------------------------------------------------------------------- MC-25
class ExplainTest(unittest.TestCase):
    def test_precedence_and_determinism(self):
        self.assertEqual(dominant(["manifest.invalid", "authz.denied", "admission.overloaded"]), "security")
        self.assertEqual(dominant(["admission.overloaded", "deadline.exceeded"]), "capacity")
        self.assertEqual(dominant(["internal"]), "defect")
        a = DecisionLog(clock=Clock()).record("validation", "rejected", codes=["link.to.undeclared"], tenant="t", correlation_id="c")
        b = DecisionLog(clock=Clock()).record("validation", "rejected", codes=["link.to.undeclared"], tenant="t", correlation_id="c")
        self.assertEqual(a["decision_id"], b["decision_id"])
        ex = explain([a], viewer_tenant="t")["decisions"][0]
        self.assertIn("caveat", ex)
        self.assertNotIn("node", ex["infrastructure"])


# --------------------------------------------------------------------------- MC-10 / MC-11 / MC-40
class AdjacentOamRolloutTest(unittest.TestCase):
    def test_adjacent_happy_and_no_partial(self):
        adj = default_adjacent()
        out = adj.handoff(dict(GOOD, providers=[{"name": "kv"}]), tenant="acme", correlation_id="c", traceparent="t")
        self.assertTrue(out["deployment"].startswith("dep-"))
        adj = default_adjacent(inv63=Faults(unavailable=True))
        with self.assertRaises(Inv64Error):
            adj.handoff(GOOD, tenant="acme", correlation_id="c", traceparent="t")
        self.assertFalse(adj.inv65.bound.get("acme"))

    def test_oam_round_trip_and_unsupported(self):
        m = {"schema": "app/v1", "components": [{"name": "api", "type": "webservice", "properties": {"image": "x"}}],
             "providers": [{"name": "kv"}], "links": [{"from": "api", "to": "kv"}],
             "traits": [{"type": "scaler", "component": "api", "properties": {"replicas": 2}}]}
        doc = to_oam(m, name="shop")
        self.assertEqual(doc["apiVersion"], "core.oam.dev/v1beta1")
        self.assertEqual(M.canonical(from_oam(doc)), M.canonical(m))
        for mut in ({"scopes": []}, {"policies": []}, {"workflow": {}}):
            bad = copy.deepcopy(doc)
            bad["spec"].update(mut)
            with self.assertRaises(Inv64Error):
                from_oam(bad)
        dup = dict(m, traits=m["traits"] * 2)
        with self.assertRaises(Inv64Error):
            to_oam(dup, name="x")

    def test_rollout_stages_abort_and_emergency(self):
        applied, reverted = [], []
        targets = [f"n{i}" for i in range(100)]
        good = {k: (0.0 if op == "<=" else 1.0) for k, (op, _) in __import__("inv64_application_model.rollout", fromlist=["x"]).DEFAULT_GATES.items()}
        ro = Rollout("r1", {"artifact_digest": "a", "config_digest": "c"}, targets, applied.append, reverted.append)
        ro.promote(None, actor="op")
        ro.promote(good, actor="op")
        ro.promote(good, actor="op")
        self.assertEqual(len(ro.exposed), 5)
        res = ro.promote(dict(good, p99_latency_ms=50.0), actor="op")
        self.assertEqual(res["state"], "aborted")
        self.assertEqual(sorted(reverted), sorted(applied))
        ro2 = Rollout("r2", {"artifact_digest": "a", "config_digest": "c"}, targets, lambda t: None, lambda t: None)
        ro2.promote(None, actor="op")
        self.assertEqual(ro2.promote({}, actor="op")["state"], "aborted")  # missing signals block promotion
        with self.assertRaises(Inv64Error):
            Rollout("r3", {}, targets, lambda t: None, lambda t: None).emergency_full(actor="op", approver="op", reason="x")
        ro4 = Rollout("r4", {"a": 1}, targets, lambda t: None, lambda t: None)
        ro4.promote(None, actor="op")
        with self.assertRaises(Inv64Error):
            ro4.promote(good, actor="op", candidate={"a": 2})

    def test_rollback_drill(self):
        with tempfile.TemporaryDirectory() as d:
            mk = lambda tag: {"scope": {}, "manifest": dict(GOOD, **{"x": tag}), "digest": M.canonical(dict(GOOD, **{"x": tag}))}
            r = rollback_drill(lambda: ConfigStore(d), candidate_effective=mk("new"), known_good_effective=mk("old"),
                               validator=M.validate)
            self.assertEqual(r["result"], "PASS")


# --------------------------------------------------------------------------- MC-01/03/29/30/36 repository controls
class RepositoryControlsTest(unittest.TestCase):
    def test_version_single_source(self):
        self.assertEqual((PKG / "VERSION").read_text().strip(), __version__)
        py = (PKG / "pyproject.toml").read_text()
        self.assertIn('version = {file = "VERSION"}', py)

    def test_source_integrity_passes_and_detects_mutation(self):
        from inv64_application_model.tools import source_integrity as SI
        self.assertEqual(SI.check(), [])
        src = PKG / "source" / "INV64_v4.2.0_MISSING_COMPONENTS_CHECKLIST.md"
        orig = src.read_bytes()
        try:
            src.write_bytes(orig.replace(b"MC-40", b"MC-4O", 1))
            errs = SI.check()
            self.assertTrue(any("digest mismatch" in e for e in errs))
        finally:
            src.write_bytes(orig)
        self.assertEqual(SI.normalize(b"\xef\xbb\xbfa \r\nb\r\n\r\n"), b"a\nb\n")

    def test_gate_is_deterministic_and_fails_closed(self):
        from inv64_application_model.release_gate import evaluate
        policy = json.loads((PKG / "ops" / "GATE_POLICY.json").read_text())
        today = dt.date(2026, 9, 23)
        with tempfile.TemporaryDirectory() as d:
            ev = Path(d)
            for c in policy["evidence"]:
                (ev / c["file"]).write_text(json.dumps({"schema": c["schema"], "result": "PASS", "skipped": 0}))
            comps = {"components": [{"id": "MC-01", "severity": "High", "status": "COMPLETE"},
                                    {"id": "MC-38", "severity": "Medium", "status": "GOVERNANCE_PENDING"}]}
            matrix = {"requirements": [{"check_id": "INV-64-C001", "status": "verified"}]}
            waiver = {"id": "W1", "type": "waiver", "severity": "Medium", "affected": ["MC-38"], "status": "active",
                      "owner": "dana", "approvers": ["erin"], "compensating_controls": ["x"], "expires": "2026-12-01"}
            args = dict(policy=policy, components=comps, matrix=matrix, register={"entries": [waiver]}, evidence_dir=ev,
                        pk_gate={"element": "INV-64", "verdict": "PASS"},
                        approval={"decision": "APPROVE", "approver": "dana", "policy_administrator": "frank"}, today=today)
            r1, r2 = evaluate(**args), evaluate(**args)
            self.assertEqual(r1["verdict"], "CONDITIONAL_GO")
            self.assertEqual(r1["input_digest"], r2["input_digest"])
            self.assertEqual(evaluate(**dict(args, register={"entries": [dict(waiver, expires="2026-09-01")]}))["verdict"], "NO_GO")
            comps_ok = {"components": [{"id": "MC-01", "severity": "High", "status": "COMPLETE"}]}
            self.assertEqual(evaluate(**dict(args, components=comps_ok))["verdict"], "GO")
            for mutate in (dict(pk_gate=None), dict(approval={"decision": "APPROVE", "approver": "ci-bot"}),
                           dict(approval={"decision": "APPROVE", "approver": "frank", "policy_administrator": "frank"}),
                           dict(components={"components": [{"id": "MC-02", "severity": "Critical", "status": "PARTIAL"}]}),
                           dict(matrix={"requirements": [{"check_id": "INV-64-C009", "status": "missing"}]})):
                a2 = dict(args, components=comps_ok)
                a2.update(mutate)
                self.assertEqual(evaluate(**a2)["verdict"], "NO_GO", mutate)
            (ev / "FUZZ.json").write_text(json.dumps({"schema": "PK_APP_FUZZ/1", "result": "FAIL"}))
            self.assertEqual(evaluate(**dict(args, components=comps_ok))["verdict"], "NO_GO")
            (ev / "FUZZ.json").write_text("{forged")
            self.assertEqual(evaluate(**dict(args, components=comps_ok))["verdict"], "NO_GO")
            (ev / "FUZZ.json").unlink()
            self.assertEqual(evaluate(**dict(args, components=comps_ok))["verdict"], "NO_GO")
            (ev / "FUZZ.json").write_text(json.dumps({"schema": "PK_APP_FUZZ/1", "result": "PASS"}))
            (ev / "TESTS.json").write_text(json.dumps({"schema": "PK_APP_TESTS/1", "result": "PASS", "skipped": 2}))
            self.assertEqual(evaluate(**dict(args, components=comps_ok))["verdict"], "NO_GO")

    def test_register_and_components_are_well_formed(self):
        comp = json.loads((PKG / "COMPONENTS_STATUS.json").read_text())
        self.assertEqual([c["id"] for c in comp["components"]], [f"MC-{i:02d}" for i in range(1, 41)])
        allowed = {"COMPLETE", "IMPLEMENTED_LOCAL", "PARTIAL", "BLOCKED_EXTERNAL", "GOVERNANCE_PENDING"}
        for c in comp["components"]:
            self.assertIn(c["status"], allowed)
            for a in c["artifacts"]:
                self.assertTrue((PKG / a).exists(), f"{c['id']} references missing artifact {a}")
            if c["status"] != "COMPLETE":
                self.assertTrue(c["blockers"], f"{c['id']} not complete but lists no blocker")


# --------------------------------------------------------------------------- MC-32 / MC-39
class BackupReleaseTest(unittest.TestCase):
    def test_backup_restore_verifies_and_isolates(self):
        from inv64_application_model.tools.backup_restore import backup, restore
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            audit = AuditLog(d / "a.jsonl")
            s = ConfigStore(d / "store", audit=audit)
            m = dict(GOOD, **{"x": 1})
            r = s.propose({"scope": {"tenant": "acme"}, "manifest": m, "digest": M.canonical(m)}, actor="op",
                          release="x", validator=M.validate)
            s.activate(r, actor="op", expected_active=None)
            backup(d / "store", d / "a.jsonl", d / "b.tar")
            self.assertEqual(restore(d / "b.tar", d / "r1", tenant="acme")["result"], "PASS")
            self.assertEqual(restore(d / "b.tar", d / "r2", tenant="globex")["result"], "FAIL")   # wrong tenant scope
            self.assertEqual(restore(d / "b.tar", d / "r1")["result"], "FAIL")                    # never over existing state
            import tarfile, io
            with tarfile.open(d / "b.tar") as t:
                members = {m_.name: t.extractfile(m_).read() for m_ in t.getmembers()}
            members["audit/audit.jsonl"] = members["audit/audit.jsonl"].replace(b'"ok"', b'"xx"', 1) \
                if b'"ok"' in members["audit/audit.jsonl"] else members["audit/audit.jsonl"] + b" "
            with tarfile.open(d / "bad.tar", "w") as t:
                for n, data in members.items():
                    ti = tarfile.TarInfo(n)
                    ti.size = len(data)
                    t.addfile(ti, io.BytesIO(data))
            self.assertEqual(restore(d / "bad.tar", d / "r3")["result"], "FAIL")

    def test_release_signing_and_consumer_verification(self):
        try:
            import cryptography  # noqa: F401
        except ImportError:
            self.skipTest("cryptography not installed (optional)")
        from inv64_application_model.tools.release import build, verify
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "dist").mkdir()
            (d / "dist" / "pkg-1-py3-none-any.whl").write_bytes(b"wheel-bytes")
            (d / "ev").mkdir()
            (d / "ev" / "X.json").write_text("{}")
            info = build(d / "dist", d / "ev", d / "rel")
            self.assertEqual(info["signing_mode"], "ephemeral")
            v = verify(d / "rel", d / "dist", None)
            by = {c["check"]: c["result"] for c in v["checks"]}
            self.assertEqual(by["SHA256SUMS signature"], "PASS")
            self.assertEqual(by["digest pkg-1-py3-none-any.whl"], "PASS")
            self.assertEqual(by["signer identity"], "FAIL")      # ephemeral key never counts as production signing
            pub = json.loads((d / "rel" / "signing-key.pub.json").read_text())
            v2 = verify(d / "rel", d / "dist", {"kid": pub["kid"], "public_key_hex": pub["public_key_hex"]})
            self.assertEqual(v2["result"], "PASS")               # pinned key supplied out-of-band
            (d / "dist" / "pkg-1-py3-none-any.whl").write_bytes(b"tampered")
            self.assertEqual({c["check"]: c["result"] for c in verify(d / "rel", d / "dist", None)["checks"]}
                             ["digest pkg-1-py3-none-any.whl"], "FAIL")
            sums = (d / "rel" / "SHA256SUMS").read_text()
            (d / "rel" / "SHA256SUMS").write_text(sums.replace(sums[:4], "ffff", 1))
            self.assertEqual({c["check"]: c["result"] for c in verify(d / "rel", d / "dist", None)["checks"]}
                             ["SHA256SUMS signature"], "FAIL")
            other = "11" * 32
            self.assertEqual(verify(d / "rel", d / "dist", {"kid": pub["kid"], "public_key_hex": other})["result"], "FAIL")


# --------------------------------------------------------------------------- MC-02 preflight (with a stand-in pk_core)
class PreflightTest(unittest.TestCase):
    def test_pin_digest_version_and_location_checks(self):
        import os
        import stat
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            pk = d / "core" / "pk_core"
            pk.mkdir(parents=True)
            (pk / "__init__.py").write_text('__version__ = "9.9.9"\n')
            compat = json.loads((PKG / "compatibility.json").read_text())

            def run(comp, extra_env=None, cert=True):
                cp = d / "compat.json"
                cp.write_text(json.dumps(comp))
                code = ("import json,sys; from pathlib import Path; from inv64_application_model.tools import preflight as p;"
                        f"print(json.dumps(p.run({cert}, Path(sys.argv[1]))))")
                env = dict(os.environ, PK_CORE_PATH=str(d / "core"), **(extra_env or {}))
                out = subprocess.run([sys.executable, "-c", code, str(cp)], capture_output=True, text=True,
                                     cwd=str(PKG.parent), env=env, check=True).stdout
                r = json.loads(out)
                return r, {c["check"]: c["result"] for c in r["checks"]}
            r, by = run(compat)
            self.assertEqual(by["pk_core.import"], "PASS")
            self.assertEqual(by["pk_core.pin"], "BLOCKED")  # no pin recorded -> certification fails closed
            self.assertEqual(r["result"], "FAIL")
            digest = next(c for c in r["checks"] if c["check"] == "pk_core.import")["digest"]
            pinned = dict(compat, pk_core=dict(compat["pk_core"], pin_version="9.9.9", pin_sha256=digest))
            r, by = run(pinned)
            self.assertEqual(by["pk_core.pin"], "PASS")
            (pk / "evil.py").write_text("x = 1\n")  # tampered package
            r, by = run(pinned)
            self.assertEqual(by["pk_core.pin"], "FAIL")
            (pk / "evil.py").unlink()
            if os.name == "posix":
                pk.chmod(pk.stat().st_mode | stat.S_IWOTH)
                r, by = run(pinned)
                self.assertEqual(by["pk_core.location"], "FAIL")
                pk.chmod(pk.stat().st_mode & ~stat.S_IWOTH)
            old = dict(compat, python=dict(compat["python"], min="3.99", max="3.99"))
            r, by = run(old)
            self.assertEqual(by["python.version"], "FAIL")


class SecretScanTest(unittest.TestCase):
    def test_repository_clean_and_archives_scanned(self):
        import zipfile
        from inv64_application_model.tools.secret_scan import scan
        self.assertEqual(scan([PKG]), [])
        with tempfile.TemporaryDirectory() as d:
            w = Path(d) / "x-1-py3-none-any.whl"
            with zipfile.ZipFile(w, "w") as z:
                z.writestr("inv64_application_model/leak.py", 'K = "AKIA' + "ABCDEFGHIJKLMNOP" + '"\n')
                z.writestr("x.dist-info/RECORD", "a,sha256=Zm9vYmFyYmF6cXV4cXV1eHF1dXhxdXV4cXV1eA,1\n")
            hits = scan([Path(d)])
            self.assertEqual([(h["path"], h["class"]) for h in hits], [("leak.py", "aws-access-key-id")])


class PerfGateTest(unittest.TestCase):
    def test_absolute_relative_and_noise_rules(self):
        from inv64_application_model.bench.perf import THRESHOLDS, compare
        env = {"cpu_model": "x", "cpu_count": 4, "python": "3.11.15"}

        def doc(scale=1.0, **over):
            res = {}
            for key, limit in THRESHOLDS.items():
                scen, metric = key.rsplit(".", 1)
                res.setdefault(scen, {})[metric] = limit * 0.1 * scale
            for k, v in over.items():
                scen, metric = k.rsplit(".", 1)
                res[scen][metric] = v
            return {"environment": env, "results": res, "version": "t"}
        base = doc()
        self.assertEqual(compare(base, doc(1.2))["result"], "PASS")
        self.assertEqual(compare(base, doc(**{"validate@10.p99_ms": 0.7}))["result"], "PASS")    # +40% but only +0.2 ms: jitter
        self.assertEqual(compare(base, doc(**{"validate@10.p99_ms": 1.5}))["result"], "FAIL")    # +1 ms: real regression
        self.assertEqual(compare(None, doc(**{"validate@10.p99_ms": 6.0}))["result"], "FAIL")    # absolute SLO breach
        other = dict(doc(**{"validate@10.p99_ms": 1.5}), environment=dict(env, cpu_model="y"))
        self.assertEqual(compare(base, other)["result"], "PASS")                                  # not equivalent: absolute only
        waived = compare(None, doc(**{"validate@10.p99_ms": 6.0}), [{"type": "perf-waiver", "metric": "validate@10.p99_ms",
                                                                     "expires": "2999-01-01", "status": "active"}])
        self.assertEqual(waived["result"], "PASS")
