"""Public-interface unit/contract suite (checklist #81, #6, #7, #22, #23)."""
from __future__ import annotations

import os
import tempfile
import unittest

from helpers import SECRET, Env
from inv55_secrets_integration.errors import ErrorCode
from inv55_secrets_integration.service import ServiceLimits, State


def code(r: dict) -> str:
    return r["error"]["code"]


class ResolveUseContract(unittest.TestCase):
    def setUp(self):
        self.e = Env()
        self.e.seed()

    def test_success_path(self):
        r = self.e.resolve()
        self.assertTrue(r["ok"])
        self.assertEqual(r["version"], 1)
        u = self.e.use(r["lease_id"])
        self.assertEqual(u["value"], SECRET)

    def test_boundary_ttl_is_capped(self):
        r = self.e.resolve(ttl_s=10**9)
        self.assertEqual(r["expires_in_s"], ServiceLimits().max_lease_ttl_s)

    def test_expiry_exact_boundary_is_expired(self):
        r = self.e.resolve(ttl_s=10)
        self.e.clock.advance(10)
        self.assertEqual(code(self.e.use(r["lease_id"])), ErrorCode.LEASE_EXPIRED.value.code)

    def test_malformed_inputs(self):
        for bad in ["", " x", "a\nb", "x" * 300, None, 5]:
            r = self.e.resolve(name=bad)
            self.assertEqual(code(r), ErrorCode.INVALID_REFERENCE.value.code, bad)
        for ttl in [0, -1, float("nan"), float("inf"), "10", True]:
            self.assertFalse(self.e.resolve(ttl_s=ttl)["ok"], ttl)

    def test_unsupported_and_mismatched_protocol(self):
        for proto in ["PK_SECRET_RESOLVE/2", "PK_SECRET_ROTATE/1", "", None, "junk"]:
            r = self.e.svc.resolve({"protocol": proto, "credential": self.e.cred(), "name": "db-password"})
            self.assertEqual(code(r), ErrorCode.UNSUPPORTED_VERSION.value.code, proto)

    def test_tolerant_reader_ignores_unknown_fields(self):
        r = self.e.resolve(future_field={"x": 1})
        self.assertTrue(r["ok"])

    def test_unauthorized_and_missing_are_indistinguishable(self):
        a = self.e.resolve(sub="marketing")
        b = self.e.resolve(name="does-not-exist")
        self.assertEqual(a["error"]["code"], b["error"]["code"])
        self.assertEqual(a["error"]["message"], b["error"]["message"])

    def test_revoke_then_use_fails(self):
        r = self.e.resolve()
        rv = self.e.svc.revoke({"protocol": "PK_SECRET_RESOLVE/1", "credential": self.e.cred("admin"),
                                "name": "db-password", "lease_id": r["lease_id"]})
        self.assertTrue(rv["ok"], rv)
        self.assertEqual(code(self.e.use(r["lease_id"])), ErrorCode.LEASE_REVOKED.value.code)

    def test_stale_lease_after_retire(self):
        r = self.e.resolve()
        rt = self.e.svc.retire({"protocol": "PK_SECRET_ROTATE/1", "credential": self.e.cred("admin"),
                                "name": "db-password", "version": 1})
        self.assertTrue(rt["ok"])
        self.assertEqual(code(self.e.use(r["lease_id"])), ErrorCode.VERSION_RETIRED.value.code)
        self.assertEqual(code(self.e.resolve()), ErrorCode.VERSION_RETIRED.value.code)

    def test_scope_narrowing_revokes_existing_leases(self):
        r = self.e.resolve()
        self.e.svc.set_scope({"protocol": "PK_SECRET_SCOPE/1", "credential": self.e.cred("admin"),
                              "name": "db-password", "apps": ["billing"]})
        self.assertEqual(code(self.e.use(r["lease_id"])), ErrorCode.LEASE_REVOKED.value.code)

    def test_per_subject_lease_limit(self):
        e = Env(limits=ServiceLimits(max_leases_per_subject=2))
        e.seed()
        self.assertTrue(e.resolve()["ok"])
        self.assertTrue(e.resolve()["ok"])
        self.assertEqual(code(e.resolve()), ErrorCode.QUOTA_EXCEEDED.value.code)


class RotateContract(unittest.TestCase):
    def setUp(self):
        self.e = Env()
        self.e.seed()

    def _rot(self, value, idem, expected=None):
        req = {"protocol": "PK_SECRET_ROTATE/1", "credential": self.e.cred("admin"), "name": "db-password",
               "value": value, "idempotency_key": idem}
        if expected is not None:
            req["expected_version"] = expected
        return self.e.svc.rotate(req)

    def test_rotation_adds_version_old_lease_still_bound(self):
        old = self.e.resolve()
        r = self._rot("v2-value", "idem-000002")
        self.assertEqual(r["version"], 2)
        new = self.e.resolve()
        self.assertEqual(self.e.use(old["lease_id"])["value"], SECRET)
        self.assertEqual(self.e.use(new["lease_id"])["value"], "v2-value")

    def test_idempotent_replay(self):
        a = self._rot("v2-value", "idem-000003")
        b = self._rot("v2-value", "idem-000003")
        self.assertEqual(a["version"], b["version"])
        self.assertTrue(b["replayed"])

    def test_cas_conflict(self):
        r = self._rot("v2-value", "idem-000004", expected=0)
        self.assertEqual(code(r), ErrorCode.CONFLICT.value.code)

    def test_requires_idempotency_key(self):
        r = self._rot("x", "short")
        self.assertEqual(code(r), ErrorCode.INVALID_REFERENCE.value.code)

    def test_value_size_limit(self):
        r = self._rot("x" * 65_537, "idem-000005")
        self.assertEqual(code(r), ErrorCode.LIMIT_EXCEEDED.value.code)


class LifecycleContract(unittest.TestCase):
    def test_frozen_denies_everything(self):
        e = Env()
        e.seed()
        op = e.cred("ops", tenant="platform", roles=("operator",))
        e.svc.freeze(op, "incident-123")
        self.assertEqual(code(e.resolve()), ErrorCode.FROZEN.value.code)
        e.svc.unfreeze(op)
        self.assertTrue(e.resolve()["ok"])

    def test_non_operator_cannot_freeze(self):
        e = Env()
        with self.assertRaises(Exception):
            e.svc.freeze(e.cred(), "x")
        self.assertEqual(e.svc.state, State.READY)

    def test_tenant_operator_cannot_freeze_platform(self):
        e = Env()
        with self.assertRaises(Exception):
            e.svc.freeze(e.cred("ops", tenant="acme", roles=("operator",)), "x")
        self.assertEqual(e.svc.state, State.READY)
        import json as _j
        self.assertEqual(_j.loads(e.sink.lines[-1])["reason"], "not_platform_operator")

    def test_stall_detector(self):
        e = Env()
        e.svc.admission.admit()                  # a request is in flight and never finishes
        e.clock.advance(e.svc.limits.stall_after_s + 1)
        h = e.svc.health()
        self.assertTrue(h["stalled"])
        self.assertFalse(h["ready"])
        e.svc.admission.release()
        self.assertFalse(e.svc.health()["stalled"])

    def test_illegal_transition_rejected(self):
        e = Env()
        e.svc.drain()
        with self.assertRaises(ValueError):
            e.svc.transition(State.READY, "x")

    def test_drain_wipes_leased_values(self):
        e = Env()
        e.seed()
        r = e.resolve()
        lease = e.svc._leases[r["lease_id"]]
        e.svc.drain()
        self.assertTrue(lease.value.wiped)

    def test_no_active_config_quarantines(self):
        from inv55_secrets_integration.config import ConfigController
        e = Env()
        from inv55_secrets_integration.service import SecretsService
        s = SecretsService(provider=e.provider, authenticator=e.authn, policy=e.policy, audit=e.audit,
                           clock=e.clock, config=ConfigController())
        self.assertEqual(s.start(), State.QUARANTINED)

    def test_health_endpoint_shape(self):
        e = Env()
        h = e.svc.health()
        for k in ("live", "ready", "state", "version", "config", "policy_digest", "dependencies", "protocols"):
            self.assertIn(k, h)
        self.assertTrue(h["ready"])
        self.assertTrue(h["config"]["digest"].startswith("sha256:"))

    def test_scopes_and_retirements_survive_restart(self):
        with tempfile.TemporaryDirectory() as d:
            sp = os.path.join(d, "state.json")
            e = Env(state_path=sp)
            e.seed()
            e.svc.retire({"protocol": "PK_SECRET_ROTATE/1", "credential": e.cred("admin"),
                          "name": "db-password", "version": 1})
            e2 = Env(provider=e.provider, state_path=sp)
            self.assertEqual(code(e2.resolve()), ErrorCode.VERSION_RETIRED.value.code)
            self.assertEqual(e2.svc._scopes[("acme", "db-password")], frozenset({"orders"}))

    def test_state_write_failure_leaves_memory_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            e = Env(state_path=os.path.join(d, "missing-dir", "state.json"))
            r = e.svc.set_scope({"protocol": "PK_SECRET_SCOPE/1", "credential": e.cred("admin"),
                                 "name": "db-password", "apps": ["orders"]})
            self.assertEqual(code(r), ErrorCode.INTERNAL.value.code)
            self.assertNotIn(("acme", "db-password"), e.svc._scopes, "write-ahead: nothing applied")


if __name__ == "__main__":
    unittest.main()
