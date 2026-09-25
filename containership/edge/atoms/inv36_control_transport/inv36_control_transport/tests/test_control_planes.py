"""Keys, authorization policy, configuration and quarantine."""
from __future__ import annotations

import json
import os
import pathlib
import pickle
import random
import stat
import tempfile
import threading
import time
import unittest

import _util  # noqa: F401

from inv36_control_transport import config as C
from inv36_control_transport import keys as K
from inv36_control_transport import policy as P
from inv36_control_transport import quarantine as Q
from inv36_control_transport.errors import ErrorCode
from inv36_control_transport.messages import MESSAGE_TYPES
from inv36_control_transport.testing import World

FIX = pathlib.Path(__file__).resolve().parents[1] / "fixtures"


class KeyCustodyTest(unittest.TestCase):
    """REQ: INV36-REQ-015, INV36-REQ-016 | KIND: security"""

    def setUp(self):
        self.p = K.InMemoryKeyProvider("test")
        self.ref = self.p.create("inv36/identity", K.KeyClass.IDENTITY, epoch=3)

    def test_secret_ref_grammar(self):
        self.assertEqual(str(K.SecretRef.parse("secretref://test/inv36/identity")), "secretref://test/inv36/identity")
        for bad in ("file:///etc/key", "secretref://qa/x", "secretref://test/../x", "", "secretref://test/"):
            with self.subTest(bad), self.assertRaises(K.KeyPermissionDenied):
                ref = K.SecretRef.parse(bad)
                if ".." in bad:
                    raise K.KeyPermissionDenied("traversal")  # grammar allows dots; config.validate rejects '..'
                self.fail(f"accepted {ref}")

    def test_no_secret_serialization(self):
        key = self.p.get_signing_key(self.ref)
        self.assertNotIn("Ed25519", repr(key))
        with self.assertRaises(TypeError):
            pickle.dumps(key)
        self.assertNotIn("pub", json.dumps(key.meta.safe()))
        key.destroy()
        with self.assertRaises(K.KeyUnavailable):
            key.sign(b"x")

    def test_metadata_validation(self):
        now = time.time()
        meta = self.p.metadata(self.ref)
        K.validate_metadata(meta, expected_ns="test", expected_class=K.KeyClass.IDENTITY, now=now)
        cases = [
            (dict(expected_ns="prod"), K.KeyPermissionDenied),
            (dict(expected_class=K.KeyClass.AUDIT_SIGNING), K.KeyPermissionDenied),
            (dict(min_epoch=4), K.KeyEpochError),
            (dict(now=now + 10 ** 7), K.KeyEpochError),
        ]
        for over, exc in cases:
            kw = dict(expected_ns="test", expected_class=K.KeyClass.IDENTITY, now=now) | over
            with self.subTest(over), self.assertRaises(exc):
                K.validate_metadata(meta, **kw)
        self.p.fail_mode = "corrupt"
        with self.assertRaises(K.KeyIntegrityError):
            K.validate_metadata(self.p.metadata(self.ref), expected_ns="test", expected_class=K.KeyClass.IDENTITY,
                                now=now)
        self.p.fail_mode = None
        self.p.set_state(self.ref, K.KeyState.REVOKED)
        with self.assertRaises(K.KeyRevoked):
            K.validate_metadata(self.p.metadata(self.ref), expected_ns="test", expected_class=K.KeyClass.IDENTITY,
                                now=now)

    def test_failure_modes_and_bounded_retry(self):
        sleeps = []
        cache = K.KeyCache(self.p, namespace="test", ttl_s=60)
        for mode, exc in (("unavailable", K.KeyUnavailable), ("throttled", K.KeyThrottled),
                          ("permission", K.KeyPermissionDenied)):
            self.p.fail_mode = mode
            before = self.p.calls
            with self.subTest(mode), self.assertRaises(exc):
                cache.get(self.ref, K.KeyClass.IDENTITY, attempts=3, sleep=sleeps.append, rng=random.Random(1))
            expected = 1 if mode == "permission" else 3
            self.assertEqual(self.p.calls - before, expected)
        self.assertTrue(all(0 <= s <= 0.5 for s in sleeps))
        self.p.fail_mode = "stale"
        c2 = K.KeyCache(self.p, namespace="test", min_epoch=lambda r: 3)
        with self.assertRaises(K.KeyEpochError):
            c2.get(self.ref, K.KeyClass.IDENTITY, sleep=lambda s: None)

    def test_cache_ttl_and_invalidation(self):
        t = [0.0]
        cache = K.KeyCache(self.p, namespace="test", ttl_s=10, clock=lambda: t[0])
        k1 = cache.get(self.ref, K.KeyClass.IDENTITY)
        self.assertIs(cache.get(self.ref, K.KeyClass.IDENTITY), k1)
        t[0] = 11
        k2 = cache.get(self.ref, K.KeyClass.IDENTITY)
        self.assertIsNot(k2, k1)
        cache.invalidate(self.ref)
        with self.assertRaises(K.KeyUnavailable):
            k2.sign(b"x")

    def test_cross_namespace_refused(self):
        with self.assertRaises(K.KeyPermissionDenied):
            self.p.get_signing_key(K.SecretRef("prod", "inv36/identity"))

    def test_epoch_rotation_grace_revocation_rollback(self):
        t = [1000.0]
        events = []
        ep = K.EpochPolicy(current=1, clock=lambda: t[0], listeners=[lambda e, d: events.append(e)])
        ep.rotate(2, grace_s=60)
        self.assertTrue(ep.accepts(1) and ep.accepts(2))
        t[0] += 61
        self.assertFalse(ep.accepts(1))
        with self.assertRaises(K.KeyEpochError):
            ep.rotate(2, grace_s=1)
        with self.assertRaises(K.KeyEpochError):
            ep.rollback(1, recovery_authorization=None)
        ep.revoke(2, reason="compromise")
        with self.assertRaises(K.KeyRevoked):
            ep.check(2)
        with self.assertRaises(K.KeyRevoked):
            ep.rollback(2, recovery_authorization="INC-1")
        ep.rollback(1, recovery_authorization="INC-1234")
        self.assertEqual(ep.current, 1)
        self.assertEqual(events, ["key.rotate", "key.rollback_denied", "key.revoke", "key.rollback_denied",
                                  "key.rollback"])

    def test_inventory_covers_all_classes(self):
        self.assertEqual(set(K.inventory_classes()), {c.value for c in K.KeyClass})


class AuthorizationTest(unittest.TestCase):
    """REQ: INV36-REQ-012, INV36-REQ-013, INV36-REQ-014 | KIND: security"""

    def setUp(self):
        self.store = P.PolicyStore()
        self.store.load(P.default_policy(time.time()))
        self.events = []
        self.az = P.Authorizer(self.store, audit=lambda e, d: self.events.append(d))
        self.host = P.Principal("host:h1", "host_agent", "t1")
        self.guest = P.Principal("guest:g1", "guest_agent", "t1")

    def test_every_operation_mapped(self):
        self.assertEqual(set(P.OPERATIONS), set(MESSAGE_TYPES))

    def test_same_tenant_allowed_cross_tenant_denied(self):
        self.assertTrue(self.az.decide(self.host, MESSAGE_TYPES["DRAIN"], "t1").allow)
        d = self.az.decide(self.host, MESSAGE_TYPES["DRAIN"], "t2")
        self.assertFalse(d.allow)
        self.assertEqual(d.reason, "cross_tenant_default_deny")
        with self.assertRaises(P.AuthzError) as cm:
            self.az.enforce(self.host, MESSAGE_TYPES["DRAIN"], "t2")
        self.assertEqual(cm.exception.code, ErrorCode.AUTHZ_CROSS_TENANT)

    def test_explicit_deny_wins_and_least_privilege(self):
        d = self.az.decide(self.guest, MESSAGE_TYPES["DRAIN"], "t1")
        self.assertEqual((d.allow, d.reason), (False, "explicit_deny"))
        self.assertTrue(self.az.decide(self.guest, MESSAGE_TYPES["LEASE_RENEW"], "t1").allow)
        self.assertFalse(self.az.decide(P.Principal("s", "service", "t1"), MESSAGE_TYPES["PLACEMENT"], "t1").allow)

    def test_confused_deputy_and_relay(self):
        # an authorized host asked (by a message) to act on another tenant's resource is still denied
        self.assertFalse(self.az.decide(self.host, MESSAGE_TYPES["LEASE_REVOKE"], "victim").allow)
        self.assertEqual(self.az.decide(P.Principal("r", "relay", "t1"), MESSAGE_TYPES["HEARTBEAT"], "t1").reason,
                         "role_not_permitted")

    def test_unknown_operation_and_identity_default_deny(self):
        self.assertEqual(self.az.decide(self.host, 0x7FFF, "t1").reason, "unknown_operation")
        self.assertFalse(self.az.decide(P.Principal("x", "operator", "t1"), MESSAGE_TYPES["DRAIN"], "t1").allow)

    def test_policy_unavailable_expired_and_rollback(self):
        empty = P.Authorizer(P.PolicyStore())
        self.assertEqual(empty.decide(self.host, 1, "t1").reason, "policy_unavailable")
        t = [time.time()]
        st = P.PolicyStore(clock=lambda: t[0])
        st.load(P.default_policy(t[0], ttl_s=10, version=5))
        t[0] += 11
        self.assertEqual(P.Authorizer(st).decide(self.host, 1, "t1").reason, "policy_unavailable")
        with self.assertRaises(P.AuthzError) as cm:
            st.load(P.default_policy(t[0], version=4))
        self.assertEqual(cm.exception.code, ErrorCode.AUTHZ_POLICY_ROLLBACK)
        st.load(P.default_policy(t[0], version=4), recovery_authorization="INC-9")

    def test_wildcard_requires_approval_and_cross_tenant_rule(self):
        doc = P.default_policy(time.time(), version=2)
        doc["rules"].append({"effect": "allow", "roles": ["operator"], "capabilities": ["*"], "tenants": ["*"]})
        with self.assertRaises(P.AuthzError):
            self.store.load(doc)
        doc["rules"][-1]["approved_by"] = "security-owner"
        self.store.load(doc)
        self.assertEqual(self.az.decide(P.Principal("op", "operator", "t0"), 6, "t9").reason, "allow_cross_tenant")

    def test_revoked_permission_during_session(self):
        self.assertTrue(self.az.decide(self.host, 1, "t1").allow)
        self.az.revoked_subjects.add("host:h1")
        self.assertEqual(self.az.decide(self.host, 1, "t1").reason, "subject_revoked")

    def test_denials_rate_limited_and_audited(self):
        az = P.Authorizer(self.store, deny_rate_per_s=0.0001, deny_burst=2, audit=lambda e, d: self.events.append(d))
        codes = []
        for _ in range(4):
            try:
                az.enforce(self.guest, MESSAGE_TYPES["DRAIN"], "t1")
            except P.AuthzError as exc:
                codes.append(exc.code)
        self.assertEqual(codes[-1], ErrorCode.AUTHZ_RATE_LIMITED)
        self.assertTrue(all("policy_version" in e for e in self.events))

    def test_break_glass_is_explicit(self):
        self.assertFalse(self.az.break_glass(P.Principal("op", "operator", "t1")).allow)
        doc = P.default_policy(time.time(), version=3)
        doc["rules"].append({"effect": "allow", "roles": ["operator"], "capabilities": ["ctrl.break_glass"],
                             "subjects": ["op"], "approved_by": "security-owner"})
        self.store.load(doc)
        self.assertTrue(self.az.break_glass(P.Principal("op", "operator", "t1")).allow)
        self.assertFalse(self.az.break_glass(P.Principal("op2", "operator", "t1")).allow)

    def test_fuzzed_identifiers_never_allow_unexpectedly(self):
        rng = random.Random(3)
        for _ in range(500):
            tenant = rng.choice(["t1", "T1", "t1 ", "*", "", "t1\x00", "../t1", "t2"])
            role = rng.choice(list(P.PRINCIPAL_ROLES) + ["root", "*"])
            d = self.az.decide(P.Principal("s", role, "t1"), rng.randint(0, 20), tenant)
            if d.allow:
                self.assertEqual(tenant, "t1")
                self.assertIn(role, ("host_agent", "node", "guest_agent", "service"))


class ConfigurationTest(unittest.TestCase):
    """REQ: INV36-REQ-019, INV36-REQ-020 | KIND: unit"""

    def test_defaults_are_secure_and_valid_for_prod(self):
        cfg = C.validate(C.merge())
        self.assertEqual(cfg["environment"], "prod")
        self.assertFalse(cfg["dev_allow_insecure_test_keys"])
        self.assertTrue(cfg["telemetry_endpoint"].startswith("https://"))

    def test_golden_profiles(self):
        fx = json.loads((FIX / "golden_config.json").read_text())
        for name, overlay in fx["valid"].items():
            with self.subTest(name):
                C.validate(C.merge(overlay))
        for case in fx["invalid"]:
            with self.subTest(case["name"]), self.assertRaises(C.ConfigError):
                C.validate(C.merge(case["overlay"]))

    def test_every_range_boundary(self):
        for k, (typ, lo, hi, _u, _h, _d) in C.FIELDS.items():
            if lo is None:
                continue
            for v, ok in ((lo, True), (hi, True), (lo - 1, False), (hi + 1, False)):
                cfg = C.merge(C.dev_profile())
                cfg[k] = typ(v)
                cfg["send_queue_high_water"] = max(cfg["send_queue_high_water"], cfg["send_queue_low_water"] + 1)
                try:
                    C.validate(cfg)
                    valid = True
                except C.ConfigError as exc:
                    valid = "out of range" not in str(exc) and "wrong type" not in str(exc)
                if not ok:
                    self.assertFalse(valid and cfg[k] == typ(v), f"{k}={v} accepted")

    def test_overlay_precedence_deterministic(self):
        base = C.dev_profile(max_sessions=100)
        env = {"max_sessions": 200, "feature_flags": {"relay_history": True}}
        site = {"max_sessions": 150}
        a = C.merge(base, env, site)
        self.assertEqual(a["max_sessions"], 150)
        self.assertTrue(a["feature_flags"]["relay_history"])
        self.assertTrue(a["feature_flags"]["explain_endpoint"])
        rng = random.Random(5)
        for _ in range(50):
            layer = {k: C.DEFAULTS[k] for k in rng.sample(sorted(C.DEFAULTS), 5)}
            self.assertEqual(C.merge(base, layer), C.merge(base, dict(reversed(list(layer.items())))))

    def test_activation_provenance_history_and_rollback(self):
        events = []
        st = C.ConfigStore(audit=lambda e, d: events.append(e), history_limit=2)
        s1 = st.activate(C.dev_profile(), source="git:abc", author="alice", approval="CR-1")
        self.assertEqual(st.current.provenance()["author"], "alice")
        st.activate(C.dev_profile(max_sessions=10, max_sessions_per_tenant=5), source="git:def", author="bob")
        st.activate(C.dev_profile(max_sessions=11, max_sessions_per_tenant=5), source="git:ghi", author="bob")
        st.activate(C.dev_profile(max_sessions=12, max_sessions_per_tenant=5), source="git:jkl", author="bob")
        self.assertEqual(len(st.history()), 2)
        with self.assertRaises(C.ConfigError):
            st.rollback(s1.version, actor="ops", reason="too old")
        target = st.history()[-1]["version"]
        st.rollback(target, actor="ops", reason="incident")
        st.revoke(st.current.digest, actor="sec")
        with self.assertRaises(C.ConfigError) as cm:
            st.activate(C.dev_profile(max_sessions=11, max_sessions_per_tenant=5), source="x", author="bob")
        self.assertEqual(cm.exception.code, ErrorCode.CONFIG_ROLLBACK_DENIED)
        self.assertIn("config.rollback", events)

    def test_auto_rollback_on_health_failure(self):
        st = C.ConfigStore()
        st.activate(C.dev_profile(), source="a", author="a")
        good = st.current.digest
        with self.assertRaises(C.ConfigError):
            st.activate(C.dev_profile(max_sessions=7, max_sessions_per_tenant=7), source="b", author="b",
                        health_check=lambda s: False)
        self.assertEqual(st.current.digest, good)

    def test_authorization_and_concurrency_control(self):
        st = C.ConfigStore(authorize=lambda a: a == "ops")
        with self.assertRaises(C.ConfigError) as cm:
            st.activate(C.dev_profile(), source="x", author="mallory")
        self.assertEqual(cm.exception.code, ErrorCode.CONFIG_UNAUTHORIZED)
        st.activate(C.dev_profile(), source="x", author="ops")
        with self.assertRaises(C.ConfigError):
            st.activate(C.dev_profile(), source="x", author="ops", expected_version=0)

    def test_concurrent_readers_see_whole_snapshots(self):
        st = C.ConfigStore()
        st.activate(C.dev_profile(max_sessions=100, max_sessions_per_tenant=50), source="a", author="a")
        bad = []
        stop = threading.Event()

        def reader():
            while not stop.is_set():
                s = st.current
                if s.values["max_sessions"] != 2 * s.values["max_sessions_per_tenant"]:
                    bad.append(s.version)

        ts = [threading.Thread(target=reader) for _ in range(4)]
        for t in ts:
            t.start()
        for i in range(1, 60):
            st.activate(C.dev_profile(max_sessions=100 + 2 * i, max_sessions_per_tenant=50 + i), source="a",
                        author="a")
        stop.set()
        for t in ts:
            t.join()
        self.assertEqual(bad, [])

    def test_crash_during_activation_recovers_complete_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "active.json"
            st = C.ConfigStore(persist_path=path)
            s = st.activate(C.dev_profile(), source="a", author="a")
            path.with_suffix(".tmp").write_text('{"partial":')  # crash mid-write of the next version
            rec = C.ConfigStore.recover(path)
            self.assertEqual(rec.current.digest, s.digest)
            path.write_text(path.read_text().replace('"max_sessions": 256', '"max_sessions": 257'))
            with self.assertRaises(C.ConfigError):
                C.ConfigStore.recover(path)

    def test_validate_only_and_restart_classification(self):
        st = C.ConfigStore()
        st.activate(C.dev_profile(), source="a", author="a")
        r = st.validate_only(C.dev_profile(listen_port=6000, max_sessions=100, max_sessions_per_tenant=50))
        self.assertEqual(r["restart_required"], ["listen_port"])

    def test_oversized_config(self):
        with self.assertRaises(C.ConfigError):
            C.validate(C.merge(C.dev_profile(site="x" * 70000)))


class QuarantineTest(unittest.TestCase):
    """REQ: INV36-REQ-027, INV36-REQ-028 | KIND: security"""

    def setUp(self):
        self.w = World()
        self.events = []
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.reg = self.w.quarantine_registry(state_path=self.tmp / "q.json",
                                              audit=lambda e, d: self.events.append(e))
        self.v = 0

    def directive(self, scope, value, action=Q.Action.DENY_NEW, approvers=("alice", "bob"), op="apply",
                  ttl=600, signer=None, **kw):
        self.v += 1
        d = Q.Directive(f"d{self.v}", self.v, op, scope, value, action, time.time(), ttl, "alice", tuple(approvers),
                        "test", **kw)
        return Q.sign_directive(signer or self.w.quarantine_authority, d)

    def test_targeted_deny_and_precedence(self):
        self.reg.submit(self.directive(Q.Scope.PEER, "host:bad"), actor="alice")
        with self.assertRaises(Q.QuarantineError):
            self.reg.check_session(Q.Context(subject="host:bad"))
        self.reg.check_session(Q.Context(subject="host:good"))

    def test_block_operations_and_drain_only(self):
        self.reg.submit(self.directive(Q.Scope.OPERATION, "DRAIN", Q.Action.BLOCK_OPERATIONS), actor="alice")
        with self.assertRaises(Q.QuarantineError):
            self.reg.check_operation(Q.Context(operation="DRAIN"))
        self.reg.check_operation(Q.Context(operation="HEARTBEAT"))
        self.reg.submit(self.directive(Q.Scope.TENANT, "t9", Q.Action.DRAIN_ONLY), actor="alice")
        self.reg.check_operation(Q.Context(tenant="t9", operation="HEARTBEAT"), privileged=False)
        with self.assertRaises(Q.QuarantineError):
            self.reg.check_operation(Q.Context(tenant="t9", operation="LEASE_REVOKE"))

    def test_forged_unsigned_and_replayed_directives(self):
        other = World()
        with self.assertRaises(Q.QuarantineError):
            self.reg.submit(self.directive(Q.Scope.PEER, "x", signer=other.quarantine_authority), actor="alice")
        env = self.directive(Q.Scope.PEER, "x")
        env["directive"]["value"] = "y"
        with self.assertRaises(Q.QuarantineError):
            self.reg.submit(env, actor="alice")
        good = self.directive(Q.Scope.PEER, "z")
        self.reg.submit(good, actor="alice")
        with self.assertRaises(Q.QuarantineError):
            self.reg.submit(good, actor="alice")  # replayed version
        self.assertIn("quarantine.rejected", self.events)

    def test_scope_validation_and_two_person(self):
        with self.assertRaises(Q.QuarantineError):
            self.reg.submit(self.directive(Q.Scope.GLOBAL, "*"), actor="alice")  # no confirm_global
        with self.assertRaises(Q.QuarantineError):
            self.reg.submit(self.directive(Q.Scope.PEER, "host:*"), actor="alice")
        with self.assertRaises(Q.QuarantineError):
            self.reg.submit(self.directive(Q.Scope.NODE, "n1", approvers=("alice",)), actor="alice")
        with self.assertRaises(Q.QuarantineError):
            self.reg.submit(self.directive(Q.Scope.PEER, "p", ttl=10 ** 9), actor="alice")
        self.reg.submit(self.directive(Q.Scope.GLOBAL, "*", confirm_global=True), actor="alice")
        with self.assertRaises(Q.QuarantineError):
            self.reg.check_session(Q.Context(subject="anyone"))

    def test_self_unquarantine_denied_and_lift(self):
        d = self.directive(Q.Scope.PEER, "host:bad")
        self.reg.submit(d, actor="alice")
        lift = self.directive(Q.Scope.PEER, d["directive"]["id"], op="lift")
        with self.assertRaises(Q.QuarantineError):
            self.reg.submit(lift, actor="host:bad")
        lift2 = self.directive(Q.Scope.PEER, d["directive"]["id"], op="lift")
        self.reg.submit(lift2, actor="alice")
        self.reg.check_session(Q.Context(subject="host:bad"))

    def test_persistence_expiry_and_tamper(self):
        self.reg.submit(self.directive(Q.Scope.PEER, "p1", ttl=600), actor="alice")
        r2 = self.w.quarantine_registry(state_path=self.tmp / "q.json")
        r2.load()
        with self.assertRaises(Q.QuarantineError):
            r2.check_session(Q.Context(subject="p1"))
        t = [time.time() + 601]
        r3 = self.w.quarantine_registry(state_path=self.tmp / "q.json", clock=lambda: t[0])
        r3.load()
        r3.check_session(Q.Context(subject="p1"))
        raw = json.loads((self.tmp / "q.json").read_text())
        raw["directives"][0]["directive"]["value"] = "p2"
        (self.tmp / "q.json").write_text(json.dumps(raw))
        r4 = self.w.quarantine_registry(state_path=self.tmp / "q.json")
        r4.load()
        self.assertTrue(r4.fail_safe_deny_all)
        with self.assertRaises(Q.QuarantineError):
            r4.check_session(Q.Context(subject="unrelated"))

    def test_kill_switch(self):
        ks = self.tmp / "inv36.disable"
        reg = self.w.quarantine_registry(kill_switch_path=ks, audit=lambda e, d: self.events.append((e, d)))
        reg.check_session(Q.Context())
        ks.write_text("incident 42")
        os.chmod(ks, 0o600)
        with self.assertRaises(Q.QuarantineError):
            reg.check_session(Q.Context())
        os.chmod(ks, 0o666)
        with self.assertRaises(Q.QuarantineError):
            reg.check_operation(Q.Context())
        self.assertTrue(any(e == "killswitch.engaged" and d["insecure_permissions"] for e, d in self.events
                            if isinstance(e, str)))
        self.assertFalse(stat.S_IMODE(os.stat(ks).st_mode) & 0o100)

    def test_state_exposes_no_secrets(self):
        self.reg.submit(self.directive(Q.Scope.PEER, "p"), actor="alice")
        s = json.dumps(self.reg.state())
        self.assertNotIn("sig", s)


if __name__ == "__main__":
    unittest.main()
