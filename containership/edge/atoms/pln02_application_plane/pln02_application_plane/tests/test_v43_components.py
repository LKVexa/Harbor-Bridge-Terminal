"""Unit + negative tests for v4.3 components. Each class names its MC id."""
from __future__ import annotations

import datetime as dt
import pathlib
import json
import tempfile
import time
import unittest

from helpers import APP, CONFIG, KEY, catalogue_doc, provider, ring, token

from pln02_application_plane import admission, audit, config, context, errors, oam, policy, secret_refs, versioning, wit
from pln02_application_plane.errors import PlaneError
from pln02_application_plane.resolver import resolve_document
from pln02_application_plane.trust import KeyRing, TrustKey, authenticate, issue_token, verify_artifact


def code_of(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except Exception as exc:  # noqa: BLE001
        return getattr(exc, "code", type(exc).__name__)
    return None


class MC04Versioning(unittest.TestCase):
    def test_current_accepted(self):
        self.assertEqual(versioning.check("PK_APPLICATION/1")["status"], "current")

    def test_unknown_major_and_malformed(self):
        self.assertEqual(code_of(versioning.check, "PK_APPLICATION/2"), "UNSUPPORTED_VERSION")
        self.assertEqual(code_of(versioning.check, "pk_application/1"), "UNSUPPORTED_VERSION")
        self.assertEqual(code_of(versioning.check, 7), "UNSUPPORTED_VERSION")

    def test_negotiate_and_removal_window(self):
        self.assertEqual(versioning.negotiate("PK_APPLICATION", [3, 1, 2]), 1)
        self.assertEqual(code_of(versioning.negotiate, "PK_APPLICATION", [9]), "UNSUPPORTED_VERSION")
        old = versioning.POLICY["PK_ERROR"]
        versioning.POLICY["PK_ERROR"] = (versioning.MajorPolicy(1, "deprecated", "2026-01-01"),)
        try:
            self.assertEqual(code_of(versioning.check, "PK_ERROR/1", today=dt.date(2026, 9, 23)), "UNSUPPORTED_VERSION")
            self.assertEqual(versioning.check("PK_ERROR/1", today=dt.date(2025, 1, 1))["status"], "deprecated")
        finally:
            versioning.POLICY["PK_ERROR"] = old


class MC05Admission(unittest.TestCase):
    def test_payload_limit(self):
        a = admission.AdmissionController(admission.AdmissionPolicy(max_payload_bytes=1024))
        self.assertEqual(code_of(a.check_payload, 2048), "PAYLOAD_TOO_LARGE")

    def test_rate_quota_and_refill(self):
        now = [0.0]
        a = admission.AdmissionController(admission.AdmissionPolicy(tenant_rate_per_second=1, tenant_burst=2), clock=lambda: now[0])
        for _ in range(2):
            with a.admit("t"):
                pass
        with self.assertRaises(PlaneError) as cm:
            with a.admit("t"):
                pass
        self.assertEqual(cm.exception.code, "QUOTA_EXCEEDED")
        now[0] = 1.5
        with a.admit("t"):
            pass

    def test_tenant_fairness_and_shedding(self):
        a = admission.AdmissionController(admission.AdmissionPolicy(tenant_max_concurrency=1, global_max_concurrency=4, shed_threshold=0.5))
        with a.admit("t1"):
            self.assertEqual(code_of(lambda: a.admit("t1").__enter__()), "QUOTA_EXCEEDED")
            with a.admit("t2"):
                self.assertEqual(code_of(lambda: a.admit("t3").__enter__()), "OVERLOADED")
                with a.admit("t3", priority=True):
                    pass
        self.assertEqual(a.saturation(), 0)

    def test_circuit_breaker(self):
        now = [0.0]
        b = admission.CircuitBreaker("x", failure_threshold=2, reset_after=5, clock=lambda: now[0])
        for _ in range(2):
            self.assertEqual(code_of(b.call, lambda: 1 / 0), "ZeroDivisionError")
        self.assertEqual(b.state, "open")
        self.assertEqual(code_of(b.call, lambda: 1), "CIRCUIT_OPEN")
        now[0] = 6
        self.assertEqual(b.state, "half_open")
        self.assertEqual(b.call(lambda: 1), 1)
        self.assertEqual(b.state, "closed")


class MC07MC28Policy(unittest.TestCase):
    def test_precedence_hard_before_soft(self):
        k = policy.Constraints(min_tier="hardened", prefer_region="us")
        pid, ex = policy.select("state", [provider("cheap-us", region="us", tier="standard", cost=0),
                                          provider("eu-hard", cost=9)], k)
        self.assertEqual(pid, "eu-hard")  # locality/cost can never admit a security-rejected provider
        self.assertEqual(ex["rejected"], [{"id": "cheap-us", "reason": "security"}])

    def test_deterministic_tiebreak(self):
        cands = [provider("b"), provider("a")]
        self.assertEqual(policy.select("s", cands, policy.Constraints())[0], "a")
        self.assertEqual(policy.select("s", list(reversed(cands)), policy.Constraints())[0], "a")

    def test_residency_conflict_refused(self):
        with self.assertRaises(PlaneError) as cm:
            policy.merge(policy.Constraints(residency=frozenset({"eu"})), policy.Constraints(),
                         policy.Constraints(residency=frozenset({"us"})))
        self.assertEqual(cm.exception.code, "POLICY_CONFLICT")

    def test_lower_source_cannot_weaken(self):
        m = policy.merge(policy.Constraints(min_tier="hardened"), policy.Constraints(min_tier="standard"), policy.Constraints())
        self.assertEqual(m.min_tier, "hardened")

    def test_no_eligible_explains(self):
        with self.assertRaises(PlaneError) as cm:
            policy.select("s", [provider("x", healthy=False)], policy.Constraints())
        self.assertEqual(cm.exception.code, "NO_ELIGIBLE_PROVIDER")
        self.assertIn("x:unhealthy", cm.exception.details["rejected"])

    def test_unknown_constraint(self):
        self.assertEqual(code_of(policy.Constraints.from_doc, {"magic": 1}), "POLICY_CONFLICT")


class MC11Authentication(unittest.TestCase):
    def test_roundtrip_and_tamper(self):
        r = ring()
        t = token(r)
        self.assertEqual(authenticate(r, t, audience="pln-02").tenant, "acme")
        body, sig = t.split(".")
        self.assertEqual(code_of(authenticate, r, body + "x." + sig, audience="pln-02"), "UNAUTHENTICATED")
        self.assertEqual(code_of(authenticate, r, t, audience="other"), "UNAUTHENTICATED")
        self.assertEqual(code_of(authenticate, r, None, audience="pln-02"), "UNAUTHENTICATED")
        self.assertEqual(code_of(authenticate, r, "a" * 5000, audience="pln-02"), "UNAUTHENTICATED")

    def test_expiry_and_revocation(self):
        r = ring()
        t = issue_token(r, "tok-1", subject="a", tenant="acme", audience="pln-02", roles=[], ttl=10, now=1000)
        self.assertEqual(code_of(authenticate, r, t, audience="pln-02", now=2000), "UNAUTHENTICATED")
        t2 = token(r)
        r.revoke("tok-1")
        self.assertEqual(code_of(authenticate, r, t2, audience="pln-02"), "UNAUTHENTICATED")

    def test_short_key_refused(self):
        self.assertEqual(code_of(TrustKey, "k", "hmac-sha256", "token", b"short"), "CONFIG_INVALID")

    def test_rotation_overlap(self):
        now = [1000.0]
        r = KeyRing(clock=lambda: now[0])
        r.add(TrustKey("old", "hmac-sha256", "token", KEY))
        sig = r.sign("old", "token", {"a": 1})
        r.rotate("old", TrustKey("new", "hmac-sha256", "token", b"n" * 32), overlap_seconds=60)
        self.assertTrue(r.verify("old", "token", {"a": 1}, sig))
        self.assertEqual(code_of(r.sign, "old", "token", {}), "CATALOGUE_UNTRUSTED")
        now[0] += 61
        self.assertEqual(code_of(r.verify, "old", "token", {"a": 1}, sig), "CATALOGUE_UNTRUSTED")


class MC12Entitlement(unittest.TestCase):
    def setUp(self):
        self.p = policy.EntitlementPolicy({"acme": frozenset({"state"})})
        self.r = ring()

    def test_denials(self):
        who = authenticate(self.r, token(self.r), audience="pln-02")
        self.assertIsNone(code_of(self.p.authorize_resolve, who, "acme", [{"requires": {"state": True}}]))
        self.assertEqual(code_of(self.p.authorize_resolve, who, "acme", [{"requires": {"gpu": True}}]), "PERMISSION_DENIED")
        self.assertEqual(code_of(self.p.authorize_resolve, who, "other", []), "PERMISSION_DENIED")
        viewer = authenticate(self.r, token(self.r, roles=("viewer",)), audience="pln-02")
        self.assertEqual(code_of(self.p.authorize_resolve, viewer, "acme", []), "PERMISSION_DENIED")
        self.assertEqual(code_of(self.p.authorize_admin, who), "PERMISSION_DENIED")


class MC13Context(unittest.TestCase):
    def test_deadline_cancel(self):
        c = context.RequestContext.create("acme", "prod", "eu-1", timeout=0.0)
        self.assertEqual(code_of(c.checkpoint), "DEADLINE_EXCEEDED")
        c2 = context.RequestContext.create("acme", "prod", "eu-1")
        c2.cancellation.cancel()
        self.assertEqual(code_of(c2.checkpoint), "CANCELLED")
        self.assertEqual(code_of(context.RequestContext.create, "acme", "prod", "eu-1", timeout=600), "INVALID_APPLICATION")
        self.assertEqual(code_of(context.RequestContext.create, "ACME!", "prod", "eu-1"), "INVALID_APPLICATION")

    def test_idempotency(self):
        cache = context.IdempotencyCache(capacity=2)
        c = context.RequestContext.create("acme", "prod", "eu-1", idempotency_key="key-12345")
        calls = []
        self.assertEqual(cache.run(c, "d1", lambda: calls.append(1) or "r"), "r")
        self.assertEqual(cache.run(c, "d1", lambda: calls.append(1) or "x"), "r")
        self.assertEqual(len(calls), 1)
        self.assertEqual(code_of(cache.run, c, "d2", lambda: 1), "IDEMPOTENCY_CONFLICT")

    def test_bounded_retry_only_retryable(self):
        c = context.RequestContext.create("acme", "prod", "eu-1")
        n = []

        def flaky():
            n.append(1)
            if len(n) < 3:
                raise PlaneError("x", code="CATALOGUE_UNAVAILABLE")
            return "ok"
        self.assertEqual(context.retry_safe(flaky, c, base_delay=0), "ok")
        self.assertEqual(code_of(context.retry_safe, lambda: (_ for _ in ()).throw(PlaneError("x", code="PERMISSION_DENIED")), c), "PERMISSION_DENIED")


class MC14Errors(unittest.TestCase):
    def test_public_document_redacts(self):
        try:
            resolve_document({"schema": "PK_APPLICATION/1", "components": [], "edges": [], "evil": 1},
                             {"schema": "PK_PROVIDER_CATALOGUE/1", "providers": {}})
        except Exception as exc:
            doc = errors.to_public(exc, correlation_id="c1")
        self.assertEqual(doc["code"], "INVALID_APPLICATION")
        self.assertEqual(doc["schema"], "PK_ERROR/1")
        self.assertEqual(doc["retryable"], "never")
        self.assertEqual(doc["correlation_id"], "c1")
        internal = errors.to_public(RuntimeError("secret path /etc/x"))
        self.assertEqual(internal["code"], "INTERNAL")
        self.assertNotIn("/etc", json.dumps(internal))

    def test_registry_complete_for_resolver_codes(self):
        for c in ("INVALID_APPLICATION", "UNSATISFIED_CAPABILITY", "INCOMPATIBLE_INTERFACE", "REVISION_INTEGRITY_ERROR"):
            self.assertIn(c, errors.REGISTRY)

    def test_error_schema_matches_registry(self):
        import pathlib
        schema = json.loads((pathlib.Path(__file__).parents[1] / "schemas" / "PK_ERROR-1.schema.json").read_text())
        self.assertEqual(sorted(schema["properties"]["code"]["enum"]), sorted(errors.REGISTRY))


class MC17Config(unittest.TestCase):
    def test_defaults_and_overlays(self):
        cfg = config.compose(CONFIG, {"admission": {"tenant_burst": 5}}, {"catalogue": {"max_age_seconds": 60}})
        self.assertEqual(cfg["admission"]["tenant_burst"], 5)
        self.assertEqual(cfg["catalogue"]["max_age_seconds"], 60)

    def test_invalid_refused(self):
        self.assertEqual(code_of(config.validate, {"bogus": 1}), "CONFIG_INVALID")
        self.assertEqual(code_of(config.validate, {"admission": {"tenant_burst": 0}}), "CONFIG_INVALID")
        self.assertEqual(code_of(config.validate, {"admission": {"tenant_max_concurrency": 100, "global_max_concurrency": 10}}), "CONFIG_INVALID")
        self.assertEqual(code_of(config.validate, {"provenance": {"author": "", "source": "s", "version": "v"}}), "CONFIG_INVALID")

    def test_activate_and_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            m = config.ConfigManager(d)
            a = m.activate(CONFIG)
            b = m.activate({**CONFIG, "provenance": {**CONFIG["provenance"], "version": "t2"}})
            self.assertNotEqual(a["digest"], b["digest"])
            self.assertEqual(code_of(m.activate, {"bogus": 1}), "CONFIG_INVALID")
            self.assertEqual(m.active()["digest"], b["digest"])  # failed activation changed nothing
            self.assertEqual(m.rollback()["digest"], a["digest"])
            m2 = config.ConfigManager(d)  # restart
            self.assertEqual(m2.active()["digest"], a["digest"])


class MC18Secrets(unittest.TestCase):
    def test_inline_refused_ref_allowed(self):
        self.assertEqual(code_of(secret_refs.check_no_inline_secrets, {"db": {"password": "hunter2"}}), "SECRET_INLINE")
        secret_refs.check_no_inline_secrets({"db": {"password": "secret://vault/db/pw#3"}})

    def test_store_fail_closed_and_redaction(self):
        s = secret_refs.InMemorySecretStore({("vault", "db/pw", "3"): b"x"})
        self.assertEqual(secret_refs.resolve_ref(s, "secret://vault/db/pw#3"), b"x")
        s.available = False
        self.assertEqual(code_of(secret_refs.resolve_ref, s, "secret://vault/db/pw#3"), "SECRET_UNAVAILABLE")
        self.assertEqual(secret_refs.redact({"api_key": "abc", "n": 1})["api_key"], secret_refs.REDACTED)
        self.assertEqual(code_of(config.validate, {"provenance": {"author": "a", "source": "s", "version": "v"},
                                                   "entitlements": {"token": ["x"]}}), None)


class MC21SupplyChain(unittest.TestCase):
    def setUp(self):
        self.r = ring()
        body = {"artifact": "redis-provider", "version": "7.2.0", "digest": "a" * 64, "sbom_digest": "b" * 64, "builder": "ci"}
        self.att = {**body, "key_id": "art-1", "signature": self.r.sign("art-1", "artifact", body)}

    def test_accept_and_reject(self):
        ok = verify_artifact(self.r, self.att, approved={"redis-provider": {"7.2.0"}})
        self.assertEqual(ok["digest"], "a" * 64)
        self.assertEqual(code_of(verify_artifact, self.r, self.att, approved={}), "ARTIFACT_UNTRUSTED")
        self.assertEqual(code_of(verify_artifact, self.r, {**self.att, "version": "7.2.1"},
                                 approved={"redis-provider": {"7.2.1"}}), "ARTIFACT_UNTRUSTED")
        self.assertEqual(code_of(verify_artifact, self.r, self.att, approved={"redis-provider": {"7.2.0"}},
                                 revoked_digests={"a" * 64}), "ARTIFACT_UNTRUSTED")
        self.r.revoke("art-1")
        self.assertEqual(code_of(verify_artifact, self.r, self.att, approved={"redis-provider": {"7.2.0"}}), "ARTIFACT_UNTRUSTED")


class MC22Audit(unittest.TestCase):
    def test_chain_tamper_truncate_restart(self):
        r = ring()
        with tempfile.TemporaryDirectory() as d:
            p = f"{d}/audit.jsonl"
            led = audit.AuditLedger(p, r, "aud-1")
            for i in range(5):
                led.append({"action": "publish", "outcome": "ok", "actor": "a", "tenant": "acme", "resource": str(i)})
            seq, head = led.head
            self.assertEqual(audit.verify(p, r, expected_head=head, expected_seq=seq)["seq"], 5)
            led2 = audit.AuditLedger(p, r, "aud-1")  # restart resumes chain
            led2.append({"action": "freeze", "outcome": "ok"})
            self.assertEqual(audit.verify(p, r)["seq"], 6)
            P = pathlib.Path(p)
            lines = P.read_bytes().splitlines()
            P.write_bytes(b"\n".join(lines[:3]) + b"\n")
            self.assertEqual(code_of(audit.verify, p, r, expected_seq=6), "AUDIT_CHAIN_BROKEN")
            tampered = lines[1].replace(b'"resource":"1"', b'"resource":"X"')
            P.write_bytes(b"\n".join([lines[0], tampered] + lines[2:]) + b"\n")
            self.assertEqual(code_of(audit.verify, p, r), "AUDIT_CHAIN_BROKEN")

    def test_event_validation_and_redaction(self):
        r = ring()
        with tempfile.TemporaryDirectory() as d:
            led = audit.AuditLedger(f"{d}/a.jsonl", r, "aud-1")
            self.assertEqual(code_of(led.append, {"action": "nope"}), "INVALID_APPLICATION")
            self.assertEqual(code_of(led.append, {"action": "publish", "password": "x"}), "INVALID_APPLICATION")


class MC09OAM(unittest.TestCase):
    DOC = {"apiVersion": "core.oam.dev/v1beta1", "kind": "Application", "metadata": {"name": "shop"},
           "spec": {"components": [
               {"name": "api", "type": "webservice", "traits": [
                   {"type": "pk.capabilities", "properties": {"requires": {"state": True}}},
                   {"type": "pk.interfaces", "properties": {"imports": {"store": "1.2"}}},
                   {"type": "pk.bindings", "properties": {"imports": {"store": "store"}}}]},
               {"name": "store", "type": "worker", "traits": [
                   {"type": "pk.capabilities", "properties": {"requires": {"state": True}}},
                   {"type": "pk.interfaces", "properties": {"exports": {"store": "1.2"}}}]}],
               "policies": [{"name": "r", "type": "pk.constraints", "properties": {"residency": ["eu"]}}]}}

    def test_translate_resolves(self):
        app, cons = oam.translate(self.DOC)
        rev = resolve_document(app, {"schema": "PK_PROVIDER_CATALOGUE/1", "providers": {"state": "p"}})
        self.assertEqual(rev["edges"], [["store", "api", "store"]])
        self.assertEqual(cons, {"residency": ["eu"]})

    def test_unsupported_refused(self):
        import copy
        for mutate in (lambda d: d.update(apiVersion="core.oam.dev/v1alpha2"),
                       lambda d: d["spec"].update(workflow={}),
                       lambda d: d["spec"]["components"][0]["traits"].append({"type": "scaler"}),
                       lambda d: d["spec"]["policies"].append({"type": "topology"}),
                       lambda d: d["metadata"].update(name="Bad_Name")):
            d = copy.deepcopy(self.DOC)
            mutate(d)
            self.assertEqual(code_of(oam.translate, d), "OAM_INVALID")


class MC10WIT(unittest.TestCase):
    V1 = """package pk:store@1.2.0;
    // key-value store
    interface kv {
      record entry { key: string, value: list<u8> }
      enum mode { strict, lax }
      type key = string;
      get: func(k: key) -> option<entry>;
      put: func(e: entry, m: mode) -> result<_, string>;
    }
    world store-world { export kv; }
    """

    def test_parse(self):
        p = wit.parse(self.V1)
        self.assertEqual(p.version, (1, 2, 0))
        self.assertEqual(sorted(p.interfaces["kv"].funcs), ["get", "put"])
        self.assertEqual(wit.interface_version(p, "kv"), "pk:store@1.2.0")

    def test_additive_compatible_and_breaks(self):
        consumer = wit.parse(self.V1)
        newer = wit.parse(self.V1.replace("1.2.0", "1.3.0").replace("put:", "del: func(k: key);\n put:"))
        wit.check_compatible(newer, consumer, "kv")
        self.assertEqual(code_of(wit.check_compatible, consumer, newer, "kv"), "INCOMPATIBLE_INTERFACE")  # older producer
        changed = wit.parse(self.V1.replace("value: list<u8>", "value: string"))
        self.assertEqual(code_of(wit.check_compatible, changed, consumer, "kv"), "INCOMPATIBLE_INTERFACE")
        major = wit.parse(self.V1.replace("1.2.0", "2.0.0"))
        self.assertEqual(code_of(wit.check_compatible, major, consumer, "kv"), "INCOMPATIBLE_INTERFACE")

    def test_alias_is_structural(self):
        a = wit.parse(self.V1)
        b = wit.parse(self.V1.replace("get: func(k: key)", "get: func(k: string)"))
        wit.check_compatible(b, a, "kv")

    def test_rejects(self):
        for src in ("package a:b@1.0.0; interface i { resource r {} }",
                    "package a:b@1.0.0; interface i { f: func(x: nope); }",
                    "package a:b@1.0.0; interface i { type a = b; type b = a; }",
                    "package a:b@1.0; interface i {}",
                    "package a:b@1.0.0; world w { import missing; }",
                    "package a:b@1.0.0; interface i { f: func() -> " + "list<" * 40 + "u8" + ">" * 40 + "; }",
                    "package a:b@1.0.0; interface i { f: func(); f: func(); }",
                    "package a:b@1.0.0; interface i { $ }"):
            self.assertEqual(code_of(wit.parse, src), "WIT_INVALID", src[:60])



try:
    import jsonschema
except ModuleNotFoundError:  # optional
    jsonschema = None


@unittest.skipIf(jsonschema is None, "jsonschema not installed")
class SchemaConformance(unittest.TestCase):
    """Generated documents validate against the published v4.3 JSON Schemas."""

    def _schema(self, name):
        return json.loads((pathlib.Path(__file__).parents[1] / "schemas" / name).read_text())

    def test_signed_catalogue_and_error_and_config(self):
        jsonschema.validate(catalogue_doc(ring()), self._schema("PK_SIGNED_CATALOGUE-1.schema.json"))
        jsonschema.validate(errors.to_public(PlaneError("x", code="QUOTA_EXCEEDED"), correlation_id="c"),
                            self._schema("PK_ERROR-1.schema.json"))
        jsonschema.validate(config.validate(CONFIG), self._schema("PK_PLANE_CONFIG-1.schema.json"))
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate({**catalogue_doc(ring()), "extra": 1}, self._schema("PK_SIGNED_CATALOGUE-1.schema.json"))


if __name__ == "__main__":
    unittest.main()
