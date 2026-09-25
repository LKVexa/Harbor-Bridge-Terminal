"""Schema validation (23), fixtures (79), negotiation (25), error mapping (26),
authn (27), authz (28), admission (30), tenant isolation (31), quota (32),
secrets (43), transport (24)."""
from __future__ import annotations

import json
import pathlib
import time
import unittest

import _support  # noqa: F401
from _support import cluster
from inv04_current_orchestration.runtime import errors
from inv04_current_orchestration.runtime import objects as o
from inv04_current_orchestration.runtime.config import load_config
from inv04_current_orchestration.runtime.errors import (AdmissionDenied, Forbidden, IncompatibleProtocol,
                                                        QuotaExceeded, SchemaViolation, Unauthenticated)
from inv04_current_orchestration.runtime.security import (AdmissionPolicy, Authorizer, DEFAULT_RULES, FairQueue,
                                                          MaintenanceWindow, Principal, Secret, SecretRef,
                                                          SecretResolver, TokenAuthenticator, mint_token, scope_filter)
from inv04_current_orchestration.runtime.service import Orchestrator, Service, problem
from inv04_current_orchestration.runtime.validation import (SCHEMAS, advertise, errors_for, load_schema, negotiate,
                                                            parse_and_validate, validate)

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures"
KEY = Secret(b"0123456789abcdef0123456789abcdef")


def token(**claims):
    now = time.time()
    base = {"iss": "https://idp.example", "aud": "inv04", "sub": "alice", "tenant": "t1",
            "groups": ["inv04:operators", "inv04:site-operators"], "iat": now, "exp": now + 300}
    base.update(claims)
    return "Bearer " + mint_token(base, KEY, "k1")


def authn():
    return TokenAuthenticator({"k1": KEY}, issuer="https://idp.example", audience="inv04")


class SchemaFixtureTest(unittest.TestCase):
    def test_every_fixture_matches_its_expectation(self):
        index = json.loads((FIXTURES / "index.json").read_text())
        self.assertEqual(set(index["interfaces"]), set(SCHEMAS))
        n = 0
        for case in index["cases"]:
            payload = json.loads((FIXTURES / case["file"]).read_text())
            errs = errors_for(payload, load_schema(case["interface"]))
            self.assertEqual(not errs, case["valid"], f"{case['file']}: {errs}")
            n += 1
        for iface in SCHEMAS:
            kinds = {c["valid"] for c in index["cases"] if c["interface"] == iface}
            self.assertEqual(kinds, {True, False}, f"{iface} needs positive and negative fixtures")
        self.assertGreaterEqual(n, 16)

    def test_hostile_payloads_fail_closed(self):
        with self.assertRaises(SchemaViolation):
            parse_and_validate("PK_ORCH_DRAIN/1", b'{"node": NaN}')
        with self.assertRaises(SchemaViolation):
            parse_and_validate("PK_ORCH_DRAIN/1", b"\xff\xfe")
        with self.assertRaises(SchemaViolation):
            parse_and_validate("PK_ORCH_INVENTORY/1", ("[" * 5000 + "]" * 5000).encode())
        with self.assertRaises(SchemaViolation):
            validate("PK_ORCH_RECONCILE/1", {"nodes": ["a"], "pods": [], "desired": {"w": True}})

    def test_error_schema_covers_every_code(self):
        schema = load_schema("PK_ORCH_ERROR/1")
        self.assertEqual(sorted(schema["properties"]["code"]["enum"]), list(errors.ALL_CODES))
        for code in errors.ALL_CODES:
            validate("PK_ORCH_ERROR/1", {"code": code, "message": "m"})


class NegotiationAndMappingTest(unittest.TestCase):
    def test_negotiation_picks_highest_common_and_refuses_incompatible(self):
        self.assertEqual(negotiate("PK_ORCH_DRAIN", ["1.0", "1.1", "2.0"]), "1.1")
        self.assertEqual(negotiate("PK_ORCH_DRAIN", ["1.0"]), "1.0")
        with self.assertRaises(IncompatibleProtocol):
            negotiate("PK_ORCH_DRAIN", ["2.0"])
        self.assertIn("PK_ORCH_RECONCILE", advertise())

    def test_every_code_maps_and_internal_errors_do_not_leak(self):
        for code in errors.ALL_CODES:
            self.assertIn(code, errors.TRANSPORT_MAP)
        status, body = problem(RuntimeError("secret path /etc/x"))
        self.assertEqual((status, body["code"], body["detail"]), (500, "ORCH_RUNTIME_ERROR", "internal error"))
        status, body = problem(errors.Forbidden("no"))
        self.assertEqual((status, body["grpc_status"], body["k8s_reason"]), (403, "PERMISSION_DENIED", "Forbidden"))


class SecurityTest(unittest.TestCase):
    def test_token_validation_matrix(self):
        a = authn()
        self.assertEqual(a.authenticate(token()).subject, "alice")
        bad = {"expired": token(exp=time.time() - 120), "issuer": token(iss="evil"), "audience": token(aud="x"),
               "future": token(nbf=time.time() + 600), "ttl": token(exp=time.time() + 99999),
               "tenantless": token(tenant="")}
        for name, t in bad.items():
            with self.assertRaises(Unauthenticated, msg=name):
                a.authenticate(t)
        forged = token()[:-4] + "AAAA"
        for t in (None, "Basic x", "Bearer a.b", forged):
            with self.assertRaises(Unauthenticated):
                a.authenticate(t)

    def test_rbac_deny_by_default_and_tenant_scope(self):
        z = Authorizer(list(DEFAULT_RULES))
        op = Principal("alice", "t1", ("inv04:operators",))
        z.authorize(op, "reconcile", tenant="t1")
        with self.assertRaises(Forbidden):
            z.authorize(op, "reconcile", tenant="t2")
        with self.assertRaises(Forbidden):
            z.authorize(op, "drain", tenant="t1")  # tenant operators cannot drain shared nodes
        z.authorize(Principal("sre", "ops", ("inv04:site-operators",)), "drain", tenant="t1")
        with self.assertRaises(Forbidden):
            z.authorize(Principal("r", "t1", ("inv04:readers",)), "drain", tenant="t1")
        with self.assertRaises(Forbidden):
            z.authorize(Principal("n", "t1", ()), "read", tenant="t1")
        z.authorize(Principal("root", "ops", ("inv04:platform-admins",)), "drain", tenant="t9")

    def test_admission_windows_frozen_and_concurrency(self):
        p = Principal("a", "t1", ())
        adm = AdmissionPolicy(windows=[MaintenanceWindow(0, 10)], frozen_tenants={"frozen"}, clock=lambda: 50)
        with self.assertRaises(AdmissionDenied):
            adm.admit("drain", p, tenant="t1")
        adm.admit("drain", p, tenant="t1", emergency_reason="INC-1")
        with self.assertRaises(AdmissionDenied):
            adm.admit("reconcile", p, tenant="frozen")
        adm2 = AdmissionPolicy(max_concurrent_drains=1)
        adm2.begin("s")
        with self.assertRaises(AdmissionDenied):
            adm2.admit("drain", p, tenant="t1", site="s")

    def test_tenant_filter_hides_unmapped_and_foreign_namespaces(self):
        pods = [o.make_pod("a", "w", "n", ns="ns1"), o.make_pod("b", "w", "n", ns="ns2"), o.make_pod("c", "w", "n", ns="x")]
        got = scope_filter(pods, "t1", {"ns1": "t1", "ns2": "t2"})
        self.assertEqual([p.meta.name for p in got], ["a"])
        self.assertEqual(scope_filter(pods, "", {"x": ""}), [])

    def test_fair_queue_prevents_starvation_and_enforces_quota(self):
        fq = FairQueue(per_tenant_inflight=1, per_tenant_queued=3)
        for i in range(3):
            fq.submit("big", i)
        fq.submit("small", "s")
        with self.assertRaises(QuotaExceeded):
            fq.submit("big", 99)
        first, second = fq.next(), fq.next()
        self.assertEqual({first[0], second[0]}, {"big", "small"})
        self.assertIsNone(fq.next())  # both at in-flight limit

    def test_secrets_never_render(self):
        s = Secret(b"hunter2")
        self.assertNotIn("hunter2", repr(s) + str(s) + json.dumps({"s": str(s)}))
        with self.assertRaises(TypeError):
            import pickle
            pickle.dumps(s)
        r = SecretResolver(env={"INV04_KEY": "abc"})
        self.assertEqual(r.resolve(SecretRef("env", "INV04_KEY")).reveal(), b"abc")
        with self.assertRaises(Unauthenticated):
            r.resolve(SecretRef("env", "MISSING"))


class ServiceTest(unittest.TestCase):
    def setUp(self):
        api = cluster(workloads={"web": 3}, min_available={"web": 2}, heartbeat=time.time())
        cfg = load_config({"namespace_tenants": {"default": "t1"}})
        self.orch = Orchestrator(api, config=cfg)
        self.orch.start()
        self.svc = Service(self.orch, authn())

    def call(self, method, path, body=b"", **headers):
        h = {"Authorization": token(), **{k.replace("_", "-"): v for k, v in headers.items()}}
        status, hdrs, out = self.svc.handle(method, path, h, body)
        return status, json.loads(out) if hdrs["content-type"].startswith("application") else out.decode()

    def test_drain_end_to_end_with_idempotent_replay(self):
        body = json.dumps({"node": "n0", "idempotency_key": "req-000001"}).encode()
        s1, r1 = self.call("POST", "/v1/drain", body, X_PK_Accept_Revision="1.1")
        s2, r2 = self.call("POST", "/v1/drain", body, X_PK_Accept_Revision="1.1")
        self.assertEqual((s1, r1["phase"], r1["replayed"]), (200, "completed", False))
        self.assertEqual((s2, r2["replayed"]), (200, True))
        self.assertEqual(len(self.orch.audit.query(action="drain")), 1)

    def test_rejections_carry_stable_codes(self):
        s, r = self.call("POST", "/v1/drain", b'{"node": "n0"}')
        self.assertEqual((s, r["code"]), (400, "ORCH_SCHEMA_INVALID"))  # idempotency key required
        s, r = self.call("POST", "/v1/drain", b'{"node": "n0", "idempotency_key": "req-000002"}')
        self.assertEqual((s, r["code"]), (426, "ORCH_PROTOCOL_INCOMPATIBLE"))  # 1.0 client sent 1.1 fields
        s, r = self.call("POST", "/v1/drain", b'{"node": "nope", "idempotency_key": "req-000003"}',
                         X_PK_Accept_Revision="1.1")
        self.assertEqual((s, r["code"]), (404, "ORCH_UNKNOWN_NODE"))
        s, r = self.call("POST", "/v1/drain", b'{"node": "n0", "extra": 1}')
        self.assertEqual(r["code"], "ORCH_SCHEMA_INVALID")
        status, _, out = self.svc.handle("GET", "/v1/inventory", {"Authorization": token(groups=[])})
        self.assertEqual((status, json.loads(out)["code"]), (403, "ORCH_FORBIDDEN"))
        status, _, out = self.svc.handle("GET", "/v1/inventory", {"Authorization": token(), "X-PK-Tenant": "t2"})
        self.assertEqual(status, 403)

    def test_inventory_health_metrics(self):
        s, inv = self.call("GET", "/v1/inventory")
        self.assertEqual((s, sorted(inv["workloads"])), (200, ["web"]))
        self.assertEqual(len(inv["digest"]), 64)
        s, ready = self.call("GET", "/readyz")
        self.assertEqual((s, ready["ready"]), (200, True))
        s, text = self.call("GET", "/metrics")
        self.assertIn("inv04_replicas_desired", text)
        self.assertNotIn("uid-", text)  # no high-cardinality identifiers

    def test_rate_limit_sheds_load(self):
        self.svc.limiter.tokens = 0
        self.svc.limiter.qps = 1e-9
        s, r = self.call("GET", "/v1/inventory")
        self.assertEqual((s, r["code"]), (429, "ORCH_THROTTLED"))

    def test_standby_replica_refuses_mutation(self):
        self.orch.elector.token = 0
        s, r = self.call("POST", "/v1/reconcile")
        self.assertEqual((s, r["code"]), (503, "ORCH_NOT_LEADER"))


if __name__ == "__main__":
    unittest.main()
