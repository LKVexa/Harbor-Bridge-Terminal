"""MC-006/008/013/014/015/018/058/059/063/064 — control-plane behaviour, positive and negative."""
from __future__ import annotations

import threading
import time
import unittest
from importlib import import_module

from _support import PKG_DIR

ctl = import_module(PKG_DIR.name + ".control")
errors = import_module(PKG_DIR.name + ".errors")
lifecycle = import_module(PKG_DIR.name + ".lifecycle")
att = import_module(PKG_DIR.name + ".attestation")
K = b"k" * 32


class AuthTest(unittest.TestCase):
    def test_roundtrip(self):
        t = ctl.issue_token(K, "alice", "inv39.sandbox", 60)
        self.assertEqual(ctl.authenticate({"alice": K}, t, "inv39.sandbox"), "alice")

    def test_rejections(self):
        t = ctl.issue_token(K, "alice", "inv39.sandbox", 60, now=0)
        cases = {
            "expired": (t, {"alice": K}, "inv39.sandbox"),
            "wrong key": (ctl.issue_token(b"x" * 32, "alice", "inv39.sandbox", 60), {"alice": K}, "inv39.sandbox"),
            "wrong audience": (ctl.issue_token(K, "alice", "other", 60), {"alice": K}, "inv39.sandbox"),
            "unknown principal": (ctl.issue_token(K, "mallory", "inv39.sandbox", 60), {"alice": K}, "inv39.sandbox"),
            "garbage": ("zz.zz", {"alice": K}, "inv39.sandbox"),
            "oversize": ("a" * 5000, {"alice": K}, "inv39.sandbox"),
        }
        for name, (tok, keys, aud) in cases.items():
            with self.subTest(name), self.assertRaises(errors.SandboxError) as c:
                ctl.authenticate(keys, tok, aud)
            self.assertEqual(c.exception.code, "E_UNAUTHENTICATED")

    def test_ttl_is_capped(self):
        t = ctl.issue_token(K, "alice", "a", 10**9, now=0)
        with self.assertRaises(errors.SandboxError):
            ctl.authenticate({"alice": K}, t, "a", now=ctl.TOKEN_MAX_TTL_S + 1)


class AuthzTest(unittest.TestCase):
    def test_tenant_scoped_deny_by_default(self):
        a = ctl.Authorizer()
        a.grant("op", "tenant-operator", "t1")
        a.check("op", "launch", "t1")
        for op, tenant in (("launch", "t2"), ("config.activate", "t1"), ("quarantine", "t1"), ("bogus", "t1")):
            with self.subTest(op=op, tenant=tenant), self.assertRaises(errors.SandboxError):
                a.check("op", op, tenant)
        with self.assertRaises(errors.SandboxError):
            a.check("nobody", "inspect", "t1")


class AdmissionTest(unittest.TestCase):
    def test_quota_concurrency_breaker(self):
        now = [0.0]
        adm = ctl.Admission(ctl.Limits(max_concurrent=3, max_per_tenant=2, breaker_failures=2, breaker_reset_s=10),
                            clock=lambda: now[0])
        adm.acquire("a"); adm.acquire("a")
        with self.assertRaises(errors.SandboxError) as c:
            adm.acquire("a")
        self.assertEqual(c.exception.code, "E_QUOTA_EXCEEDED")
        adm.acquire("b")
        with self.assertRaises(errors.SandboxError) as c:
            adm.acquire("c")
        self.assertEqual(c.exception.code, "E_OVERLOADED")
        adm.release("a", False); adm.release("a", False)
        with self.assertRaises(errors.SandboxError) as c:
            adm.acquire("z")
        self.assertEqual(c.exception.code, "E_CIRCUIT_OPEN")
        now[0] = 11
        adm.acquire("z")  # half-open probe admitted
        with self.assertRaises(errors.SandboxError):
            adm.check_payload(b"x" * (adm.limits.max_payload_bytes + 1))

    def test_concurrent_acquire_never_exceeds_ceiling(self):
        adm = ctl.Admission(ctl.Limits(max_concurrent=10, max_per_tenant=10))
        got, lock = [], threading.Lock()

        def worker():
            try:
                adm.acquire("t")
                with lock:
                    got.append(1)
            except errors.SandboxError:
                pass
        ts = [threading.Thread(target=worker) for _ in range(200)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(len(got), 10)
        self.assertEqual(adm.total, 10)


class RetryIdempotencyTest(unittest.TestCase):
    def test_only_retryable_codes_retry_and_bounded(self):
        calls = []

        def flaky():
            calls.append(1)
            raise errors.SandboxError("E_OVERLOADED", "busy")
        with self.assertRaises(errors.SandboxError):
            ctl.retry(flaky, attempts=3, sleep=lambda s: None)
        self.assertEqual(len(calls), 3)
        calls.clear()

        def terminal():
            calls.append(1)
            raise errors.SandboxError("E_PROFILE_INVALID", "no")
        with self.assertRaises(errors.SandboxError):
            ctl.retry(terminal, attempts=5, sleep=lambda s: None)
        self.assertEqual(len(calls), 1)

    def test_idempotency(self):
        c = ctl.IdempotencyCache()
        n = []
        self.assertEqual(c.run("k", {"a": 1}, lambda: n.append(1) or "r"), "r")
        self.assertEqual(c.run("k", {"a": 1}, lambda: n.append(1) or "r2"), "r")
        self.assertEqual(len(n), 1)
        with self.assertRaises(errors.SandboxError) as e:
            c.run("k", {"a": 2}, lambda: "x")
        self.assertEqual(e.exception.code, "E_CONFLICT")


class LeaseQuarantineLifecycleTest(unittest.TestCase):
    def test_fenced_leases(self):
        now = [0.0]
        lt = ctl.LeaseTable(ttl_s=5, clock=lambda: now[0])
        f1 = lt.acquire("sb", "ctl-a")
        with self.assertRaises(errors.SandboxError):
            lt.acquire("sb", "ctl-b")
        now[0] = 6
        f2 = lt.acquire("sb", "ctl-b")
        self.assertGreater(f2, f1)
        with self.assertRaises(errors.SandboxError) as c:
            lt.check("sb", "ctl-a", f1)  # stale controller
        self.assertEqual(c.exception.code, "E_OWNERSHIP_LOST")

    def test_quarantine_authorized_and_audited(self):
        a = ctl.Authorizer(); a.grant("sec", "security-responder", "*"); a.grant("op", "tenant-operator", "t1")
        audit = att.AuditChain()
        q = ctl.Quarantine(a, audit)
        with self.assertRaises(errors.SandboxError):
            q.set("op", "t1", "t1/w", "no")
        q.set("sec", "t1", "t1/w", "suspected escape")
        with self.assertRaises(errors.SandboxError) as c:
            q.check("t1/w")
        self.assertEqual(c.exception.code, "E_QUARANTINED")
        q.lift("sec", "t1", "t1/w")
        q.check("t1/w")
        self.assertEqual([e["kind"] for e in audit.entries], ["quarantine", "quarantine.lift"])

    def test_lifecycle_forbids_exec_before_verify(self):
        lc = lifecycle.Lifecycle("s")
        for bad in ("RUNNING", "READY", "VERIFYING", "CLEANED"):
            with self.subTest(bad), self.assertRaises(errors.SandboxError):
                lifecycle.Lifecycle("s").to(bad, "x")
        for st in ("APPLYING", "VERIFYING", "READY", "RUNNING", "TERMINATING", "CLEANED"):
            lc.to(st, "ok")
        self.assertTrue(lc.terminal)
        with self.assertRaises(errors.SandboxError):
            lc.to("RUNNING", "resurrect")

    def test_lifecycle_graph_properties(self):
        T = lifecycle.TRANSITIONS
        preds = {s for s, nxt in T.items() if "RUNNING" in nxt}
        self.assertEqual(preds, {"READY"})
        self.assertEqual({s for s, nxt in T.items() if "READY" in nxt}, {"VERIFYING"})
        for s in lifecycle.STATES:  # every state can reach CLEANED
            seen, todo = set(), [s]
            while todo:
                x = todo.pop()
                if x not in seen:
                    seen.add(x); todo += list(T[x])
            self.assertIn("CLEANED", seen, s)


if __name__ == "__main__":
    unittest.main()
