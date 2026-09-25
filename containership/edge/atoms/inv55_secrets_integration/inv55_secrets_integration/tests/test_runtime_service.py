"""End-to-end tests through the public boundary (checklist #24, #25, #48, #57, #58, #71, #77, #81, #82, #84-#88)."""
from __future__ import annotations

import json
import random
import string
import threading
import unittest

import _support as S
from _support import PLAINTEXT, req, seeded, token
from fake_vault import FakeVault
from inv55_secrets_integration.runtime import audit as A
from inv55_secrets_integration.runtime.errors import INV55Error
from inv55_secrets_integration.runtime.health import status
from inv55_secrets_integration.runtime.vault import AppRoleAuth, StaticTokenAuth, VaultKV2Provider
from inv55_secrets_integration.runtime.wire import SCHEMAS, validate


def everything_observable(svc) -> str:
    return "\n".join([json.dumps(svc.audit.memory, default=str), svc.metrics.prometheus(),
                      "\n".join(svc.log.ring), json.dumps(list(svc.tracer.spans), default=str),
                      json.dumps(svc.state_snapshot())])


class HappyPath(unittest.TestCase):
    def test_resolve_then_use(self):
        svc, prov, ver, clock, wall = seeded()
        tok = token(ver, wall)
        r = svc.handle("RESOLVE", req(), tok)
        self.assertEqual(r["outcome"], "SUCCESS", r)
        self.assertEqual(validate(r, SCHEMAS["PK_SECRET_RESOLVE/1.response"]), [])
        self.assertNotIn(PLAINTEXT, json.dumps(r))
        self.assertEqual(svc.use(r["lease"]["lease_id"], tok), PLAINTEXT)
        self.assertNotIn(PLAINTEXT, everything_observable(svc))
        self.assertTrue(A.verify_records(svc.audit.memory)[0])

    def test_rotation_keeps_old_lease_on_old_version(self):
        svc, prov, ver, clock, wall = seeded()
        tok = token(ver, wall)
        rot = token(ver, wall, roles=("secret-rotator",))
        svc.policy.set_scope("acme/db-password", [("acme", "orders")])
        old = svc.handle("RESOLVE", req(), tok)["lease"]
        r = svc.handle("ROTATE", req(op="ROTATE", idempotency_key="idem-00000001", expected_version=1,
                                     ext={"value_ref": "v2-value"}), rot)
        self.assertEqual(r["lease"]["version"], 2, r)
        new = svc.handle("RESOLVE", req(), tok)["lease"]
        self.assertEqual((old["version"], new["version"]), (1, 2))
        self.assertEqual(svc.use(old["lease_id"], tok), PLAINTEXT)
        self.assertEqual(svc.use(new["lease_id"], tok), "v2-value")

    def test_rotate_idempotency(self):
        svc, prov, ver, clock, wall = seeded()
        rot = token(ver, wall, roles=("secret-rotator",))
        body = req(op="ROTATE", idempotency_key="idem-00000002", ext={"value_ref": "v2"})
        a = svc.handle("ROTATE", body, rot)
        b = svc.handle("ROTATE", body, rot)
        self.assertEqual(a["lease"]["version"], b["lease"]["version"])
        self.assertEqual(prov.metadata("acme/db-password", timeout_s=1)["current_version"], 2)
        c = svc.handle("ROTATE", req(op="ROTATE", idempotency_key="idem-00000002", expected_version=5, ext={"value_ref": "v3"}), rot)
        self.assertEqual(c["error"]["code"], "INV55-E-CONFLICT")

    def test_explain_view(self):
        svc, prov, ver, clock, wall = seeded()
        svc.handle("RESOLVE", req(), token(ver, wall, app="intruder"))
        rows = svc.explain("req-00000001")
        self.assertEqual(rows[-1]["reason"], "not_in_scope")
        self.assertIn("policy_digest", rows[-1])


class Adversarial(unittest.TestCase):
    """Threat-model-derived (THREAT_MODEL.md T-01..T-12)."""

    def code(self, r):
        return r.get("error", {}).get("code")

    def test_T01_no_existence_oracle(self):
        svc, prov, ver, clock, wall = seeded()
        intruder = token(ver, wall, app="intruder")
        a = svc.handle("RESOLVE", req("acme/db-password"), intruder)
        b = svc.handle("RESOLVE", req("acme/does-not-exist"), intruder)
        self.assertEqual(a, b)
        svc.policy.set_scope("acme/ghost", [("acme", "orders")])
        c = svc.handle("RESOLVE", req("acme/ghost"), token(ver, wall))
        self.assertEqual({k: v for k, v in c["error"].items() if k != "reason"},
                         {k: v for k, v in a["error"].items() if k != "reason"})

    def test_T02_cross_tenant(self):
        svc, prov, ver, clock, wall = seeded()
        r = svc.handle("RESOLVE", req("acme/db-password"), token(ver, wall, tenant="evilcorp", app="orders"))
        self.assertEqual(self.code(r), "INV55-E-DENIED")
        self.assertEqual(svc.audit.memory[-1]["reason"], "cross_tenant")

    def test_T03_lease_replay_by_other_workload(self):
        svc, prov, ver, clock, wall = seeded()
        lid = svc.handle("RESOLVE", req(), token(ver, wall))["lease"]["lease_id"]
        svc.policy.set_scope("acme/db-password", [("acme", "orders"), ("acme", "billing")])
        with self.assertRaises(INV55Error) as c:
            svc.use(lid, token(ver, wall, app="billing"))
        self.assertEqual(c.exception.code, "INV55-E-LEASE-CONTEXT")

    def test_T04_expiry_revocation_retirement_scope_removal(self):
        svc, prov, ver, clock, wall = seeded()
        tok = token(ver, wall)
        lid = lambda: svc.handle("RESOLVE", req(), tok)["lease"]["lease_id"]
        l1 = lid(); clock.t += 61
        with self.assertRaises(INV55Error) as c: svc.use(l1, tok)
        self.assertEqual(c.exception.code, "INV55-E-LEASE-EXPIRED")
        l2 = lid(); svc.revoke(l2, actor="op")
        with self.assertRaises(INV55Error) as c: svc.use(l2, tok)
        self.assertEqual(c.exception.code, "INV55-E-LEASE-REVOKED")
        l3 = lid(); svc.retire("acme/db-password", 1, actor="op")
        with self.assertRaises(INV55Error) as c: svc.use(l3, tok)
        self.assertEqual(c.exception.code, "INV55-E-VERSION-RETIRED")
        self.assertEqual(self.code(svc.handle("RESOLVE", req(), tok)), "INV55-E-VERSION-RETIRED")

    def test_T04b_scope_removed_after_resolve_denies_use(self):
        svc, prov, ver, clock, wall = seeded()
        tok = token(ver, wall)
        l = svc.handle("RESOLVE", req(), tok)["lease"]["lease_id"]
        svc.policy.set_scope("acme/db-password", [("acme", "someone-else")])
        with self.assertRaises(INV55Error) as c:
            svc.use(l, tok)
        self.assertEqual(c.exception.code, "INV55-E-DENIED")

    def test_T05_forged_and_expired_tokens(self):
        svc, prov, ver, clock, wall = seeded()
        good = token(ver, wall)
        forged = good[:-3] + ("AAA" if not good.endswith("AAA") else "BBB")
        self.assertEqual(self.code(svc.handle("RESOLVE", req(), forged)), "INV55-E-UNAUTHENTICATED")
        wall.t += 10_000
        self.assertEqual(self.code(svc.handle("RESOLVE", req(), good)), "INV55-E-UNAUTHENTICATED")

    def test_T06_schema_smuggling_and_oversize(self):
        svc, prov, ver, clock, wall = seeded()
        tok = token(ver, wall)
        self.assertEqual(self.code(svc.handle("RESOLVE", req(value="x"), tok)), "INV55-E-INVALID-REQUEST")
        self.assertEqual(self.code(svc.handle("RESOLVE", "x" * 10000, tok)), "INV55-E-INVALID-REQUEST")
        self.assertEqual(self.code(svc.handle("RESOLVE", "[1]", tok)), "INV55-E-INVALID-REQUEST")
        self.assertEqual(self.code(svc.handle("RESOLVE", json.dumps({"versions": ["PK_SECRET_RESOLVE/7"], "request_id": "req-00000001", "name": "acme/x"}), tok)),
                         "INV55-E-UNSUPPORTED-VERSION")

    def test_T07_log_injection_identifiers(self):
        svc, prov, ver, clock, wall = seeded()
        r = svc.handle("RESOLVE", req("acme/x\n{\"allowed\":true}"), token(ver, wall))
        self.assertEqual(self.code(r), "INV55-E-INVALID-REQUEST")

    def test_T08_consumer_cannot_rotate_or_rescope(self):
        svc, prov, ver, clock, wall = seeded()
        tok = token(ver, wall)
        self.assertEqual(self.code(svc.handle("ROTATE", req(op="ROTATE", idempotency_key="idem-00000009", ext={"value_ref": "x"}), tok)), "INV55-E-DENIED")
        self.assertEqual(self.code(svc.handle("SCOPE", req(op="SCOPE", members=["acme/intruder"]), tok)), "INV55-E-DENIED")
        adm = token(ver, wall, roles=("scope-admin",))
        self.assertEqual(self.code(svc.handle("SCOPE", req(op="SCOPE", members=["evil/orders"]), adm)), "INV55-E-DENIED")

    def test_T09_freeze_blocks_resolve_and_use(self):
        svc, prov, ver, clock, wall = seeded()
        tok = token(ver, wall)
        l = svc.handle("RESOLVE", req(), tok)["lease"]["lease_id"]
        svc.freeze("tenant:acme", "incident-42", actor="op")
        self.assertEqual(self.code(svc.handle("RESOLVE", req(), tok)), "INV55-E-FROZEN")
        with self.assertRaises(INV55Error):
            svc.use(l, tok)
        svc.unfreeze("tenant:acme", actor="op")
        self.assertEqual(svc.use(l, tok), PLAINTEXT)

    def test_T10_clock_rollback(self):
        svc, prov, ver, clock, wall = seeded()
        tok = token(ver, wall)
        svc.handle("RESOLVE", req(), tok)
        clock.t -= 5
        self.assertEqual(self.code(svc.handle("RESOLVE", req(), tok)), "INV55-E-CLOCK")

    def test_T11_no_plaintext_in_any_channel_after_mixed_traffic(self):
        svc, prov, ver, clock, wall = seeded()
        tok = token(ver, wall)
        for i in range(30):
            svc.handle("RESOLVE", req(), tok if i % 3 else token(ver, wall, app="x"))
        lid = svc.handle("RESOLVE", req(), tok)["lease"]["lease_id"]
        svc.use(lid, tok)
        try:
            svc.use("bogus", tok)
        except INV55Error as e:
            self.assertNotIn(PLAINTEXT, str(e) + json.dumps(e.to_wire()))
        self.assertNotIn(PLAINTEXT, everything_observable(svc))

    def test_T12_quota_and_overload(self):
        svc, prov, ver, clock, wall = seeded(config=S.cfg(limits={"rate_per_s": 0.001, "burst": 2}))
        tok = token(ver, wall)
        codes = [self.code(svc.handle("RESOLVE", req(), tok)) for _ in range(4)]
        self.assertEqual(codes, [None, None, "INV55-E-QUOTA", "INV55-E-QUOTA"])
        other = token(ver, wall, app="other")   # fairness: another workload is unaffected
        svc.policy.set_scope("acme/db-password", [("acme", "orders"), ("acme", "other")])
        self.assertIsNone(self.code(svc.handle("RESOLVE", req(), other)))


class Resilience(unittest.TestCase):
    def test_outage_offline_deny_then_recovery(self):
        svc, prov, ver, clock, wall = seeded()
        tok = token(ver, wall)
        prov.available = False
        r = svc.handle("RESOLVE", req(), tok)
        self.assertEqual(r["error"]["code"], "INV55-E-PROVIDER-UNAVAILABLE")
        self.assertEqual(r["error"]["outcome"], "RETRYABLE")
        prov.available = True
        self.assertEqual(svc.handle("RESOLVE", req(), tok)["error"]["code"], "INV55-E-CIRCUIT-OPEN")
        clock.t += 11                                           # breaker cooldown
        self.assertEqual(svc.handle("RESOLVE", req(), tok)["outcome"], "SUCCESS")

    def test_degraded_stale_serving_when_configured(self):
        svc, prov, ver, clock, wall = seeded(config=S.cfg(cache={"allow_stale": True}))
        tok = token(ver, wall)
        svc.handle("RESOLVE", req(), tok)
        clock.t += 10
        prov.available = False
        r = svc.handle("RESOLVE", req(), tok)
        self.assertEqual(r["outcome"], "DEGRADED")
        self.assertEqual(svc.audit.memory[-1]["reason"], "granted_degraded")
        clock.t += 100
        self.assertEqual(svc.handle("RESOLVE", req(), tok)["error"]["outcome"], "RETRYABLE")   # stale window over

    def test_transient_fault_retried(self):
        svc, prov, ver, clock, wall = seeded()
        prov.fail_next = ["INV55-E-PROVIDER-UNAVAILABLE"]
        self.assertEqual(svc.handle("RESOLVE", req(), token(ver, wall))["outcome"], "SUCCESS")
        self.assertEqual(svc.metrics.get("provider_retries", reason="INV55-E-PROVIDER-UNAVAILABLE"), 1)

    def test_breaker_opens_and_health_reports_not_ready(self):
        svc, prov, ver, clock, wall = seeded()
        tok = token(ver, wall)
        prov.available = False
        for _ in range(2):
            svc.handle("RESOLVE", req(), tok)
        self.assertEqual(svc.breaker.state, "open")
        st = status(svc)
        self.assertFalse(st["ready"])
        self.assertFalse(st["checks"]["circuit_closed"])
        self.assertEqual(svc.handle("RESOLVE", req(), tok)["error"]["code"], "INV55-E-CIRCUIT-OPEN")

    def test_restart_invalidates_leases_keeps_scopes_and_retirements(self):
        svc, prov, ver, clock, wall = seeded()
        tok = token(ver, wall)
        l = svc.handle("RESOLVE", req(), tok)["lease"]["lease_id"]
        svc.retire("acme/db-password", 1, actor="op")
        snap = json.loads(json.dumps(svc.state_snapshot()))
        svc2, _, _, _, _ = S.make(provider=prov)
        svc2.verifier = svc.verifier
        svc2.restore(snap)
        with self.assertRaises(INV55Error):
            svc2.use(l, tok)                                  # fail closed after restart
        self.assertEqual(svc2.handle("RESOLVE", req(), tok)["error"]["code"], "INV55-E-VERSION-RETIRED")

    def test_health_ready_when_all_good(self):
        svc, *_ = seeded()
        st = status(svc)
        self.assertTrue(st["ready"], st)
        self.assertEqual(st["version"], "4.3.0")


class Fuzz(unittest.TestCase):
    def test_random_requests_never_crash_or_leak(self):
        svc, prov, ver, clock, wall = seeded()
        tok = token(ver, wall)
        rng = random.Random(55)
        alphabet = string.printable + "\u0000‮퟿"
        for i in range(1500):
            kind = rng.random()
            if kind < 0.3:
                body = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 200)))
            elif kind < 0.7:
                d = json.loads(req())
                k = rng.choice(list(d) + ["x", "ext", "version", "ttl_s"])
                d[k] = rng.choice([None, 0, -1, 1e308, "", "a" * 300, [], {}, True, "acme/" + "b" * rng.randint(0, 300)])
                body = json.dumps(d)
            else:
                body = req(rng.choice(["acme/db-password", "acme/x", "evil/x", "acme/../x", "acme/%00"]))
            op = rng.choice(["RESOLVE", "ROTATE", "SCOPE"])
            r = svc.handle(op, body, rng.choice([tok, "", "garbage", tok[:-1]]))
            self.assertTrue("error" in r or r.get("outcome") in ("SUCCESS", "DEGRADED"))
            if "error" in r:
                self.assertEqual(validate(r, SCHEMAS["error"]), [], r)
        self.assertNotIn(PLAINTEXT, everything_observable(svc))
        self.assertTrue(A.verify_records(svc.audit.memory)[0])
        self.assertNotIn("internal_errors", svc.metrics.prometheus())   # no crash was masked

    def test_property_scope_decision_matches_model(self):
        rng = random.Random(9)
        svc, prov, ver, clock, wall = seeded(config=S.cfg(limits={"burst": 100000, "rate_per_s": 100000}))
        apps = ["a1", "a2", "a3"]
        for i in range(300):
            members = [("acme", a) for a in apps if rng.random() < 0.5] or [("acme", "nobody")]
            svc.policy.set_scope("acme/db-password", members)
            app = rng.choice(apps)
            r = svc.handle("RESOLVE", req(), token(ver, wall, app=app))
            self.assertEqual("error" not in r, ("acme", app) in members)


class Concurrency(unittest.TestCase):
    def test_parallel_resolve_rotate_revoke(self):
        svc, prov, ver, clock, wall = seeded(config=S.cfg(limits={"burst": 100000, "rate_per_s": 100000, "max_inflight": 1000}))
        tok = token(ver, wall)
        rot = token(ver, wall, roles=("secret-rotator",))
        errors, leases = [], []
        lock = threading.Lock()

        def reader():
            for _ in range(200):
                r = svc.handle("RESOLVE", req(), tok)
                if "error" in r:
                    errors.append(r)
                else:
                    with lock:
                        leases.append(r["lease"])

        def rotator(n):
            for i in range(20):
                svc.handle("ROTATE", req(op="ROTATE", idempotency_key=f"idem-{n:03d}-{i:04d}", ext={"value_ref": f"v-{n}-{i}"}), rot)

        ts = [threading.Thread(target=reader) for _ in range(8)] + [threading.Thread(target=rotator, args=(n,)) for n in range(3)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(errors, [])
        self.assertEqual(prov.metadata("acme/db-password", timeout_s=1)["current_version"], 61)
        ok, info = A.verify_records(svc.audit.memory)
        self.assertTrue(ok, info)
        self.assertEqual(len({l["lease_id"] for l in leases}), len(leases))
        for l in leases[::97]:
            v = svc.use(l["lease_id"], tok)
            self.assertEqual(v, PLAINTEXT if l["version"] == 1 else v)


class VaultIntegration(unittest.TestCase):
    """Adapter against the KV v2 wire double - NOT a real-Vault certification."""

    def adapter(self, fv, **kw):
        return VaultKV2Provider(fv.address, auth=StaticTokenAuth("root-test-token"), allow_insecure_loopback=True, **kw)

    def test_kv2_roundtrip_versions_destroy_health(self):
        with FakeVault() as fv:
            a = self.adapter(fv, namespace="team-a")
            self.assertEqual(a.write("acme/db", "v1", cas=0, timeout_s=2), 1)
            self.assertEqual(a.write("acme/db", "v2", cas=None, timeout_s=2), 2)
            self.assertEqual(a.read("acme/db", timeout_s=2).value._reveal(), "v2")
            self.assertEqual(a.read("acme/db", 1, timeout_s=2).value._reveal(), "v1")
            a.destroy_version("acme/db", 1, timeout_s=2)
            with self.assertRaises(INV55Error) as c:
                a.read("acme/db", 1, timeout_s=2)
            self.assertEqual(c.exception.code, "INV55-E-VERSION-RETIRED")
            self.assertEqual(a.metadata("acme/db", timeout_s=2), {"current_version": 2, "destroyed": [1]})
            self.assertTrue(a.health(timeout_s=2).healthy)
            self.assertIn("team-a", fv.namespace_seen)
            with self.assertRaises(INV55Error) as c:
                a.write("acme/db", "v3", cas=0, timeout_s=2)
            self.assertEqual(c.exception.code, "INV55-E-INVALID-REQUEST")

    def test_error_mapping_and_sealed(self):
        with FakeVault() as fv:
            a = self.adapter(fv)
            with self.assertRaises(INV55Error) as c:
                a.read("acme/missing", timeout_s=2)
            self.assertEqual(c.exception.code, "INV55-E-DENIED")
            fv.fail_status = [500]
            with self.assertRaises(INV55Error) as c:
                a.read("acme/missing", timeout_s=2)
            self.assertEqual(c.exception.code, "INV55-E-PROVIDER-UNAVAILABLE")
            fv.sealed = True
            h = a.health(timeout_s=2)
            self.assertFalse(h.healthy); self.assertTrue(h.sealed)
            bad = VaultKV2Provider(fv.address, auth=StaticTokenAuth("wrong"), allow_insecure_loopback=True)
            fv.sealed = False
            with self.assertRaises(INV55Error) as c:
                bad.read("acme/x", timeout_s=2)
            self.assertEqual(c.exception.code, "INV55-E-DENIED")

    def test_timeout_maps_to_deadline(self):
        with FakeVault() as fv:
            a = self.adapter(fv)
            fv.delay_s = 0.5
            with self.assertRaises(INV55Error) as c:
                a.read("acme/x", timeout_s=0.1)
            self.assertEqual(c.exception.code, "INV55-E-DEADLINE")
            fv.delay_s = 0

    def test_approle_login_and_token_never_in_repr(self):
        with FakeVault() as fv:
            a = VaultKV2Provider(fv.address, auth=AppRoleAuth("role-1", "sid-1"), allow_insecure_loopback=True)
            a.write("acme/x", "v", cas=None, timeout_s=2)
            self.assertNotIn("approle-token", repr(a.__dict__))
            self.assertNotIn("sid-1", repr(a.__dict__))
            bad = VaultKV2Provider(fv.address, auth=AppRoleAuth("role-1", "wrong"), allow_insecure_loopback=True)
            with self.assertRaises(INV55Error):
                bad.read("acme/x", timeout_s=2)

    def test_transport_policy_fail_closed(self):
        for addr, kw in [("http://example.com", {}), ("http://127.0.0.1:1", {}), ("ftp://127.0.0.1", {"allow_insecure_loopback": True}),
                         ("http://10.0.0.1:8200", {"allow_insecure_loopback": True})]:
            with self.assertRaises(INV55Error, msg=addr):
                VaultKV2Provider(addr, auth=StaticTokenAuth("t"), **kw)
        VaultKV2Provider("https://vault.example.com", auth=StaticTokenAuth("t"))   # https accepted

    def test_https_to_plain_listener_fails_closed(self):
        with FakeVault() as fv:
            a = VaultKV2Provider(fv.address.replace("http://", "https://"), auth=StaticTokenAuth("root-test-token"))
            with self.assertRaises(INV55Error) as c:
                a.read("acme/x", timeout_s=2)
            self.assertEqual(c.exception.code, "INV55-E-PROVIDER-UNAVAILABLE")

    def test_service_over_vault_end_to_end(self):
        with FakeVault() as fv:
            prov = self.adapter(fv)
            prov.write("acme/db-password", PLAINTEXT, cas=None, timeout_s=2)
            svc, _, ver, clock, wall = S.make(provider=prov)
            svc.policy.set_scope("acme/db-password", [("acme", "orders")])
            tok = token(ver, wall)
            r = svc.handle("RESOLVE", req(), tok)
            self.assertEqual(svc.use(r["lease"]["lease_id"], tok), PLAINTEXT)
            fv.sealed = True
            self.assertEqual(svc.handle("RESOLVE", req(), tok)["outcome"], "SUCCESS")  # fresh cache within fresh_s
            clock.t += 6
            self.assertEqual(svc.handle("RESOLVE", req(), tok)["error"]["outcome"], "RETRYABLE")
            self.assertNotIn(PLAINTEXT, everything_observable(svc))


if __name__ == "__main__":
    unittest.main()
