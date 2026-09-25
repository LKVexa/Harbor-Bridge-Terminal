"""M06/M07/M09/M13/M23 - authentication, authorization, replay/spoofing,
audit chain and the adversarial abuse-case suite against the service pipeline."""
import json
import secrets
import time
import unittest

from _harness import KV, Fixture, codec, key, security


class PipelineHappyPath(unittest.TestCase):
    def test_get_put_scan(self):
        fx = Fixture()
        r = fx.call(fx.envelope("put", [{"key": "a", "value": 7, "tags": []}, "strong"]))
        self.assertEqual(r["status"], "ok")
        r = fx.call(fx.envelope("get", ["a"]))
        self.assertEqual(codec.decode(("option", "u64"), r["result"]), 7)
        self.assertIn("inv61_requests_total", fx.svc.metrics.render())


class AuthnTest(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()

    def test_tampered_payload_rejected(self):
        env = self.fx.envelope("get", ["a"])
        env["function"] = "put"
        self.assertEqual(self.fx.call(env)["status"], "unauthenticated")

    def test_unknown_key(self):
        self.assertEqual(self.fx.call(self.fx.envelope("get", ["a"], key_=key("ghost")))["status"], "unauthenticated")

    def test_spoofed_sender(self):
        env = self.fx.envelope("get", ["a"])
        env["sender"] = "admin"
        self.assertEqual(self.fx.call(env)["status"], "unauthenticated")

    def test_revoked_and_expired_keys(self):
        self.fx.ring.revoke(self.fx.ckey.key_id)
        self.assertEqual(self.fx.call(self.fx.envelope("get", ["a"]))["status"], "unauthenticated")
        fx = Fixture()
        new = security.Key("client-a-k2", "client-a", secrets.token_bytes(32))
        fx.ring.rotate("client-a", new, overlap_s=-1, now=time.time())  # old key ended immediately
        self.assertEqual(fx.call(fx.envelope("get", ["a"]))["status"], "unauthenticated")
        self.assertEqual(fx.call(fx.envelope("get", ["a"], key_=new))["status"], "ok")

    def test_tls_peer_binding(self):
        env = self.fx.envelope("get", ["a"])
        self.assertEqual(self.fx.call(env, tls_peer="mallory")["status"], "unauthenticated")

    def test_weak_key_refused(self):
        with self.assertRaises(security.SecurityError):
            security.KeyRing().add(security.Key("k", "p", b"short"))

    def test_unauthenticated_peer_never_reaches_lookup(self):
        env = self.fx.envelope("get", ["a"], key_=key("ghost"))
        env["interface"] = "does/not-exist"
        self.assertEqual(self.fx.call(env)["status"], "unauthenticated")  # not unknown-interface


class ReplayTest(unittest.TestCase):
    def test_replay_and_window(self):
        fx = Fixture()
        env = fx.envelope("get", ["a"])
        self.assertEqual(fx.call(env)["status"], "ok")
        self.assertEqual(fx.call(env)["status"], "replay")
        old = fx.envelope("get", ["a"], issued_ms=int(time.time() * 1000) - 120_000)
        self.assertEqual(fx.call(old)["status"], "replay")
        self.assertEqual(fx.call(fx.envelope("get", ["a"], nonce="short"))["status"], "replay")

    def test_replay_across_restart_refused(self):
        d = __import__("tempfile").mkdtemp()
        fx = Fixture(d)
        env = fx.envelope("get", ["a"], issued_ms=int(time.time() * 1000) - 50)
        self.assertEqual(fx.call(env)["status"], "replay")  # issued before this process booted
        time.sleep(0.01)
        env = fx.envelope("get", ["a"])
        self.assertEqual(fx.call(env)["status"], "ok")
        fx2 = Fixture(d)  # restart (possibly within the same millisecond): empty replay cache
        fx2.ring = fx.ring
        fx2.svc.keyring = fx.ring
        self.assertEqual(fx2.call(env)["status"], "replay")

    def test_full_replay_cache_sheds_as_retryable_overload(self):
        fx = Fixture()
        fx.svc.replay.capacity = 1
        self.assertEqual(fx.call(fx.envelope("get", ["a"]))["status"], "ok")
        r = fx.call(fx.envelope("get", ["a"]))
        self.assertEqual((r["status"], r["detail"], r["retryable"]), ("overloaded", "replay-cache-full", True))

    def test_future_skew_bounded(self):
        g = security.ReplayGuard(window_ms=30_000, future_skew_ms=5_000)
        with self.assertRaises(security.SecurityError):
            g.check("p", "f" * 16, 10_000, 0)
        g.check("p", "g" * 16, 4_000, 0)

    def test_bounded_cache_fails_closed(self):
        g = security.ReplayGuard(window_ms=10_000, capacity=3)
        for i in range(3):
            g.check("p", f"{i:016d}", 0, 0)
        with self.assertRaises(security.SecurityError) as cm:
            g.check("p", "x" * 16, 0, 0)
        self.assertEqual(cm.exception.code, "replay-cache-full")
        g.check("p", "y" * 16, 30_000, 30_000)  # old entries evicted after 2 windows


class AuthzTest(unittest.TestCase):
    def test_default_deny_and_explicit_deny(self):
        fx = Fixture(grants=[security.Grant("client-a", "default", KV.qualified, "get")])
        self.assertEqual(fx.call(fx.envelope("get", ["a"]))["status"], "ok")
        self.assertEqual(fx.call(fx.envelope("put", [{"key": "a", "value": 1, "tags": []}, "strong"]))["status"],
                         "permission-denied")
        self.assertEqual(fx.call(fx.envelope("get", ["a"], tenant="other"))["status"], "permission-denied")
        p = security.Policy([security.Grant("u", "t", "*", "*")], [security.Grant("u", "t", "*", "boom")])
        self.assertFalse(p.decide("u", "t", "x", "boom", 0).allowed)
        self.assertTrue(p.decide("u", "t", "x", "get", 0).allowed)
        p2 = security.Policy([security.Grant("u", "t", "*", "*", expires=10)])
        self.assertEqual(p2.decide("u", "t", "x", "get", 11).reason, "grant-expired")


class AuditTest(unittest.TestCase):
    def test_chain_detects_tampering(self):
        fx = Fixture()
        fx.call(fx.envelope("get", ["a"], key_=key("ghost")))
        fx.call(fx.envelope("get", ["a"], version="9.9.9"))
        path = fx.tmp / "audit.jsonl"
        ok, n, head = security.AuditLog.verify(path, fx.audit_key)
        self.assertTrue(ok)
        self.assertEqual(n, 2)
        events = [json.loads(json.loads(l)["body"])["event"] for l in path.read_text().splitlines()]
        self.assertEqual(events, ["authn-failure", "version-drift"])
        lines = path.read_text().splitlines()
        # edit
        row = json.loads(lines[0]); row["body"] = row["body"].replace("authn", "authz")
        path.write_text(json.dumps(row) + "\n" + lines[1] + "\n")
        self.assertFalse(security.AuditLog.verify(path, fx.audit_key)[0])
        # delete first record
        path.write_text(lines[1] + "\n")
        self.assertFalse(security.AuditLog.verify(path, fx.audit_key)[0])
        # truncate tail against an anchored head
        path.write_text(lines[0] + "\n")
        self.assertFalse(security.AuditLog.verify(path, fx.audit_key, expected_head=head)[0])
        # reopening a broken log is refused
        path.write_text(lines[1] + "\n")
        with self.assertRaises(security.SecurityError):
            security.AuditLog(path, fx.audit_key)


class AdversarialSuite(unittest.TestCase):
    """M23 abuse cases (see docs/THREAT_MODEL.md, AC-01..AC-14)."""

    def setUp(self):
        self.fx = Fixture()

    def test_ac01_signature_drift(self):
        self.assertEqual(self.fx.call(self.fx.envelope("get", ["a"], fp="0" * 16))["status"], "signature-mismatch")

    def test_ac02_version_drift(self):
        self.assertEqual(self.fx.call(self.fx.envelope("get", ["a"], version="2.0.0"))["status"], "version-mismatch")

    def test_ac03_type_confusion_args(self):
        env = self.fx.envelope("get", ["a"])
        env["args"] = codec.encode(("tuple", ("u64",)), [5])
        env = security.sign(env, self.fx.ckey)
        self.assertEqual(self.fx.call(env)["status"], "invalid-args")

    def test_ac04_garbage_body(self):
        out = codec.decode(codec.RESPONSE_ENVELOPE, self.fx.svc.handle(b"\x00" * 7))
        self.assertEqual(out["status"], "malformed-frame")

    def test_ac05_expired_deadline(self):
        now = int(time.time() * 1000)
        self.assertEqual(self.fx.call(self.fx.envelope("get", ["a"], deadline_ms=now - 1))["status"],
                         "deadline-exceeded")

    def test_ac06_callee_trap_no_leak(self):
        r = self.fx.call(self.fx.envelope("boom", []))
        self.assertEqual(r["status"], "callee-trap")
        self.assertIsNone(r["detail"])
        self.assertNotIn("ZeroDivision", " ".join(self.fx.logs))

    def test_ac07_circuit_opens_after_traps(self):
        for _ in range(5):
            self.fx.call(self.fx.envelope("boom", []))
        self.assertEqual(self.fx.call(self.fx.envelope("boom", []))["status"], "circuit-open")

    def test_ac08_emergency_disable(self):
        self.fx.svc.set_disabled(True, actor="oncall")
        self.assertEqual(self.fx.call(self.fx.envelope("get", ["a"]))["status"], "disabled")
        self.assertEqual(self.fx.svc.health.readiness()["status"], "fail")

    def test_ac09_unowned_mutation_fenced(self):
        self.fx.svc.owner_epoch = None
        r = self.fx.call(self.fx.envelope("put", [{"key": "a", "value": 1, "tags": []}, "strong"]))
        self.assertEqual(r["status"], "fenced")

    def test_ac10_idempotency_key_reuse_with_other_args(self):
        e1 = self.fx.envelope("put", [{"key": "a", "value": 1, "tags": []}, "strong"], idem="op-1")
        e2 = self.fx.envelope("put", [{"key": "a", "value": 2, "tags": []}, "strong"], idem="op-1")
        self.assertEqual(self.fx.call(e1)["status"], "ok")
        self.assertEqual(self.fx.call(e2)["status"], "idempotency-conflict")

    def test_ac11_duplicate_execution_suppressed(self):
        for _ in range(3):
            e = self.fx.envelope("put", [{"key": "a", "value": 1, "tags": []}, "strong"], idem="op-2")
            self.assertEqual(self.fx.call(e)["status"], "ok")
        self.assertEqual(self.fx.calls["put"], 1)

    def test_ac12_secrets_not_logged(self):
        self.fx.call(self.fx.envelope("get", ["a"], key_=key("ghost")))
        blob = " ".join(self.fx.logs)
        self.assertNotIn(self.fx.ckey.secret.hex(), blob)
        self.assertNotIn("secret", repr(self.fx.ckey).lower().replace("secret=", "x"))

    def test_ac13_oversize_string_arg(self):
        lim = codec.Limits(max_string_bytes=4)
        fx = Fixture(limits=lim)
        env = fx.envelope("get", ["abc"])
        env["args"] = codec.encode(("tuple", ("string",)), ["x" * 100])
        env = security.sign(env, fx.ckey)
        r = codec.decode(codec.RESPONSE_ENVELOPE, fx.svc.handle(codec.encode(codec.REQUEST_ENVELOPE, env)))
        self.assertEqual((r["status"], r["detail"]), ("invalid-args", "string-limit"))

    def test_ac14_bad_traceparent_ignored_safely(self):
        r = self.fx.call(self.fx.envelope("get", ["a"], trace="00-zz-bad-01"))
        self.assertEqual(r["status"], "ok")


if __name__ == "__main__":
    unittest.main()
