"""Threat-derived adversarial security tests (MC-040, MC-076).  Each test
names the THREAT_MODEL.md entry it exercises."""
from __future__ import annotations

import base64
import json
import unittest

from support import OTHER, TENANT, client, seeded, make_service

from inv62_edge_topology.production import audit, auth, errors, wire


def env(op="resolve", protocol="PK_TOPO_NEAREST/1", tenant=TENANT, cred="x" * 20, body=None, **kw):
    e = {"protocol": protocol, "op": op, "tenant": tenant, "request_id": "req-00000001", "credential": cred,
         "body": body if body is not None else {"origin": "s1-d1", "capability": "gpu"}}
    e.update(kw)
    return e


def call(svc, envelope) -> dict:
    return json.loads(svc.handle(wire.encode(envelope) if isinstance(envelope, dict) else envelope))


def code(resp) -> str | None:
    return resp.get("error", {}).get("code")


class SpoofingTest(unittest.TestCase):
    def setUp(self):
        self.svc, self.feed = seeded()

    def test_T01_forged_signature_rejected(self):
        tok = self.svc.authn.issue("s", "scheduler", [TENANT])
        head, kid, body, sig = tok.split(".")
        forged = f"{head}.{kid}.{body}.{sig[:-2]}AA"
        self.assertEqual(code(call(self.svc, env(cred=forged))), "TOPO.UNAUTHENTICATED")

    def test_T01_claims_tampering_rejected(self):
        tok = self.svc.authn.issue("s", "scheduler", [TENANT])
        head, kid, body, sig = tok.split(".")
        claims = json.loads(base64.urlsafe_b64decode(body + "=="))
        claims["role"] = "operator"
        body2 = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
        self.assertEqual(code(call(self.svc, env(cred=f"{head}.{kid}.{body2}.{sig}"))), "TOPO.UNAUTHENTICATED")

    def test_T01_unknown_or_revoked_key_rejected(self):
        tok = self.svc.authn.issue("s", "scheduler", [TENANT])
        self.assertEqual(code(call(self.svc, env(cred=tok.replace("PKT1.k1.", "PKT1.k9.")))), "TOPO.UNAUTHENTICATED")
        self.svc.keyring.revoke("k1")
        self.assertEqual(code(call(self.svc, env(cred=tok))), "TOPO.UNAUTHENTICATED")

    def test_T02_expired_and_future_credentials_rejected(self):
        tok = self.svc.authn.issue("s", "scheduler", [TENANT], lifetime_s=60)
        self.svc.clock.advance(60 + auth.CLOCK_SKEW_S + 1)
        self.assertEqual(code(call(self.svc, env(cred=tok))), "TOPO.UNAUTHENTICATED")
        self.svc.clock.advance(-10_000)
        self.assertEqual(code(call(self.svc, env(cred=self.svc.authn.issue("s", "scheduler", [TENANT])))), None)
        self.svc.clock.advance(10_000)
        self.assertEqual(code(call(self.svc, env(cred=tok))), "TOPO.UNAUTHENTICATED")

    def test_T02_wildcard_and_lifetime_refused_at_issue(self):
        with self.assertRaises(ValueError):
            self.svc.authn.issue("s", "scheduler", ["*"])
        with self.assertRaises(ValueError):
            self.svc.authn.issue("s", "scheduler", [TENANT], lifetime_s=auth.MAX_LIFETIME_S + 1)
        with self.assertRaises(ValueError):
            self.svc.authn.issue("s", "root", [TENANT])

    def test_T03_replay_of_mutating_credential_rejected(self):
        tok = self.svc.authn.issue("f", "topology-feed", [TENANT])
        e = env("apply", "PK_TOPO_GRAPH/1", cred=tok, body={"mutations": [
            {"kind": "add_node", "node": "s1-d9", "tier": "device", "site": "s1", "parent": "s1-gw"}]})
        self.assertEqual(code(call(self.svc, e)), None)
        e["request_id"] = "req-00000002"
        self.assertEqual(code(call(self.svc, e)), "TOPO.REPLAYED")

    def test_T03_replay_cache_fails_closed_when_full(self):
        self.svc.authn.replay.capacity = len(self.svc.authn.replay) + 1
        mk = lambda: self.svc.authn.issue("f", "topology-feed", [TENANT])  # noqa: E731
        b = lambda n: {"mutations": [{"kind": "add_node", "node": n, "tier": "device", "site": "s1", "parent": "s1-gw"}]}  # noqa: E731
        self.assertIsNone(code(call(self.svc, env("apply", "PK_TOPO_GRAPH/1", cred=mk(), body=b("x1")))))
        self.assertEqual(code(call(self.svc, env("apply", "PK_TOPO_GRAPH/1", cred=mk(), body=b("x2")))), "TOPO.OVERLOADED")


class ElevationTest(unittest.TestCase):
    def setUp(self):
        self.svc, self.feed = seeded()

    def test_T04_role_cannot_exceed_matrix(self):
        sched = self.svc.authn.issue("s", "scheduler", [TENANT])
        e = env("apply", "PK_TOPO_GRAPH/1", cred=sched, body={"mutations": [{"kind": "remove_node", "node": "s1-d2"}]})
        self.assertEqual(code(call(self.svc, e)), "TOPO.FORBIDDEN")
        with self.assertRaises(errors.TopoError):
            self.svc.admin(sched, "freeze")

    def test_T04_no_role_holds_every_permission(self):
        every = set().union(*auth.ROLE_PERMISSIONS.values())
        for role, perms in auth.ROLE_PERMISSIONS.items():
            self.assertNotEqual(set(perms), every, role)

    def test_T05_node_agent_bound_to_own_node(self):
        agent = client(self.svc, "node-agent", node="s1-gw2")
        with self.assertRaises(errors.TopoError) as cm:
            agent.acquire("s1", "s1-gw")
        self.assertEqual(cm.exception.code, "TOPO.FORBIDDEN")

    def test_T06_cross_tenant_access_denied_and_isolated(self):
        other = client(self.svc, "scheduler", tenant=OTHER)
        with self.assertRaises(errors.TopoError) as cm:
            other.resolve("s1-d1", "gpu")
        self.assertEqual(cm.exception.code, "TOPO.UNKNOWN_NODE")  # other tenant has no graph; nothing leaks
        tok = self.svc.authn.issue("s", "scheduler", [OTHER])
        self.assertEqual(code(call(self.svc, env(tenant=TENANT, cred=tok))), "TOPO.FORBIDDEN")
        client(self.svc, "topology-feed", tenant=OTHER).apply([{"kind": "add_node", "node": "cloud", "tier": "cloud"}])
        self.assertEqual(len(self.svc.tenants[OTHER].topo.nodes), 1)
        self.assertEqual(len(self.svc.tenants[TENANT].topo.nodes), 6)


class InjectionAndExhaustionTest(unittest.TestCase):
    def setUp(self):
        self.svc, self.feed = seeded()
        self.cred = self.svc.authn.issue("s", "scheduler", [TENANT])

    def test_T07_hostile_payloads_rejected_without_internal_error(self):
        cases = [
            b"\xff\xfe", b"[]", b"null", b'{"a":NaN}', b'{"a":1,"a":2}', b"{" * 5000,
            wire.encode(env(cred=self.cred, body={"origin": "s1 d1", "capability": "gpu"})),
            wire.encode(env(cred=self.cred, body={"origin": "s1-d1", "capability": "gpu", "evil": True})),
            wire.encode(env(cred=self.cred, protocol="PK_TOPO_NEAREST/9")),
            wire.encode(env(cred=self.cred, required_features=["time-travel"])),
            b"{" + b'"x":' * 1 + b'"' + b"a" * (wire.MAX_PAYLOAD_BYTES) + b'"}',
        ]
        nested = {"x": 1}
        for _ in range(40):
            nested = {"x": nested}
        cases.append(json.dumps(nested).encode())
        for raw in cases:
            with self.subTest(raw=raw[:40]):
                resp = json.loads(self.svc.handle(raw))
                self.assertIn(code(resp), {"TOPO.INVALID_REQUEST", "TOPO.PAYLOAD_TOO_LARGE", "TOPO.UNSUPPORTED_VERSION"})

    def test_T08_graph_quota_and_batch_limits(self):
        svc, feed = seeded(limits={"max_nodes": 7})
        feed.apply([{"kind": "add_node", "node": "s1-d7", "tier": "device", "site": "s1", "parent": "s1-gw"}])
        with self.assertRaises(errors.TopoError) as cm:
            feed.apply([{"kind": "add_node", "node": "s1-d8", "tier": "device", "site": "s1", "parent": "s1-gw"}])
        self.assertEqual(cm.exception.code, "TOPO.QUOTA_EXCEEDED")
        big = [{"kind": "remove_node", "node": "x"}] * (wire.MAX_MUTATIONS_PER_APPLY + 1)
        with self.assertRaises(errors.TopoError) as cm:
            feed.apply(big)
        self.assertEqual(cm.exception.code, "TOPO.INVALID_REQUEST")

    def test_T09_rate_limit_sheds_per_tenant(self):
        svc, _ = seeded(admission={"rate_per_s": 1.0, "burst": 2, "max_in_flight": 10})
        sched = client(svc, "scheduler")
        sched.retry = __import__("inv62_edge_topology.production.resilience", fromlist=["RetryPolicy"]).RetryPolicy(max_attempts=1)
        sched.resolve("s1-d1", "gpu")
        with self.assertRaises(errors.TopoError) as cm:
            for _ in range(5):
                sched.resolve("s1-d1", "gpu")
        self.assertEqual(cm.exception.code, "TOPO.RATE_LIMITED")

    def test_T10_anonymous_flood_cannot_drain_victim_bucket(self):
        svc, _ = seeded(admission={"rate_per_s": 1.0, "burst": 2, "max_in_flight": 10})
        for i in range(50):
            call(svc, env(cred="PKT1.k1.bad.bad", request_id=f"req-{i:08d}"))
        self.assertIsNone(code(call(svc, env(cred=svc.authn.issue("s", "scheduler", [TENANT])))))


class SecurityDependencyOutageTest(unittest.TestCase):
    """MC-038: identity/policy/key/time outages fail closed."""

    def setUp(self):
        self.svc, self.feed = seeded()

    def _resolve_code(self):
        return code(call(self.svc, env(cred=self.svc.authn.issue("s", "scheduler", [TENANT]))))

    def test_policy_outage(self):
        self.svc.authz.available = False
        self.assertEqual(self._resolve_code(), "TOPO.DEPENDENCY_UNAVAILABLE")

    def test_key_outage(self):
        tok = self.svc.authn.issue("s", "scheduler", [TENANT])
        self.svc.keyring.available = False
        self.assertEqual(code(call(self.svc, env(cred=tok))), "TOPO.DEPENDENCY_UNAVAILABLE")

    def test_time_outage(self):
        tok = self.svc.authn.issue("s", "scheduler", [TENANT])
        self.svc.clock_source.healthy = False
        self.assertEqual(code(call(self.svc, env(cred=tok))), "TOPO.DEPENDENCY_UNAVAILABLE")
        self.assertFalse(self.svc.health()["ready"])


class KeyRotationTest(unittest.TestCase):
    def test_overlap_then_retire(self):
        svc = make_service(secrets={"token_keys": {"k1": "secret://keys/k1", "k2": "secret://keys/k2"},
                                    "active_token_key": "k1"})
        old = svc.authn.issue("s", "scheduler", [TENANT])
        svc.keyring.rotate_to("k2")
        new = svc.authn.issue("s", "scheduler", [TENANT])
        self.assertIn(".k2.", new)
        for tok in (old, new):
            self.assertNotEqual(code(call(svc, env(cred=tok))), "TOPO.UNAUTHENTICATED")
        self.assertEqual(svc.keyring.retire_verify_only(), ["k1"])
        self.assertEqual(code(call(svc, env(cred=old))), "TOPO.UNAUTHENTICATED")
        with self.assertRaises(ValueError):
            svc.keyring.add("k2", b"z" * 40)  # keys are never overwritten


class AuditAndLeakageTest(unittest.TestCase):
    def test_audit_chain_detects_tampering(self):
        svc, feed = seeded()
        call(svc, env(cred="PKT1.k1.xxxxxxxx.yyyyyyyy"))
        recs = [dict(r) for r in svc.audit.records]
        key = b"au" * 20
        self.assertEqual(audit.verify(recs, key, expected_head=svc.audit.head()), (True, "ok"))
        for mutate in (lambda r: r[1].__setitem__("tenant", "evil"), lambda r: r.pop(1),
                       lambda r: r.reverse(), lambda r: r.pop()):
            copy = [dict(x) for x in recs]
            mutate(copy)
            self.assertFalse(audit.verify(copy, key, expected_head=svc.audit.head())[0])
        self.assertTrue(any(r["event"] == "security.denied" for r in recs))

    def test_credentials_and_secrets_never_logged(self):
        sink: list = []
        svc, feed = seeded()
        svc.logger.sink = sink
        tok = svc.authn.issue("s", "scheduler", [TENANT])
        call(svc, env(cred=tok))
        call(svc, env(cred=tok[:-3] + "AAA"))
        svc.logger.log("info", "t", detail={"api_key": "hunter2", "nested": {"password": "p"}, "c": tok})
        blob = json.dumps(sink) + json.dumps(svc.audit.records)
        for secret in (tok, "hunter2", "\"p\"", (b"k1" * 20).decode()):
            self.assertNotIn(secret, blob)

    def test_errors_do_not_leak_internals(self):
        svc, feed = seeded()
        svc._dispatch = lambda *a, **k: 1 / 0  # simulated defect
        resp = call(svc, env(cred=svc.authn.issue("s", "scheduler", [TENANT])))
        self.assertEqual(code(resp), "TOPO.INTERNAL")
        self.assertNotIn("ZeroDivision", json.dumps(resp))


if __name__ == "__main__":
    unittest.main()
