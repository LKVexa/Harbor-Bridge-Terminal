"""P0-09 attestation, P0-10 authn, P0-11 authz, P1-30 secrets — 'security template' .01-.10."""
from __future__ import annotations

import json
import secrets
import unittest

from support import Stack, covers, operator_token, workload_token
from gap11_control.common import ControlError, ManualClock
from gap11_control.hardware import normalize
from gap11_control.security import (AttestationVerifier, Authenticator, Keyring, Policy, Principal, SCOPES,
                                    SecretProvider, redact, sign)
from test_hardware import NV

ALL_TEMPLATE = lambda c, *n: tuple(f"GAP11-{c}.{i:02d}" for i in n)


def alloc_body(tenant="t1", rid="req-sec-0001"):
    return json.dumps({"schema": "PK_ACCELERATOR_ALLOCATION_REQUEST/1", "request_id": rid, "tenant": tenant, "workload": "w"}).encode()


class AuthnTests(unittest.TestCase):
    @covers(*ALL_TEMPLATE("P0-10", 2, 3, 6, 10), *ALL_TEMPLATE("P0-11", 3), "GAP11-P2-37.03")
    def test_forged_expired_replayed_and_wrong_audience_credentials_refused(self):
        clock = ManualClock()
        kr = Keyring(); kr.add("k1", secrets.token_bytes(32))
        a = Authenticator(kr, clock=clock)
        tok = a.issue("spiffe://t1/w", "t1", "workload", {"lease:allocate"})
        self.assertEqual(a.authenticate(tok).tenant, "t1")
        with self.assertRaises(ControlError) as cm:
            a.authenticate(tok)
        self.assertEqual(cm.exception.code, "REPLAY_DETECTED")
        forged = a.issue("spiffe://t1/w", "t1", "workload", {"lease:allocate"})
        forged["claims"]["ten"] = "t2"                                                # tenant swap
        with self.assertRaises(ControlError):
            a.authenticate(forged)
        other = Keyring(); other.add("k1", secrets.token_bytes(32))
        with self.assertRaises(ControlError):
            a.authenticate(Authenticator(other, clock=clock).issue("x", "t1", "workload", set()))   # foreign issuer
        expired = a.issue("x", "t1", "workload", set(), ttl_s=5)
        clock.advance(40)
        with self.assertRaises(ControlError):
            a.authenticate(expired)
        aud = Authenticator(kr, clock=clock, audience="other").issue("x", "t1", "workload", set())
        with self.assertRaises(ControlError):
            a.authenticate(aud)
        for junk in (None, "Bearer abc", {"kid": "k1"}, {"kid": "k1", "claims": [], "mac": "x"}):
            with self.assertRaises(ControlError):
                a.authenticate(junk)

    @covers(*ALL_TEMPLATE("P0-10", 7), *ALL_TEMPLATE("P1-30", 7))
    def test_live_key_rotation_with_overlap_and_emergency_revocation(self):
        clock = ManualClock()
        kr = Keyring(); kr.add("k1", secrets.token_bytes(32))
        a = Authenticator(kr, clock=clock)
        old = a.issue("x", "t1", "workload", set())
        old_unused = a.issue("x", "t1", "workload", set())
        kr.add("k2", secrets.token_bytes(32), activate=True)                          # overlap window
        new = a.issue("x", "t1", "workload", set())
        self.assertEqual(new["kid"], "k2")
        a.authenticate(old); a.authenticate(new)
        kr.retire("k1")                                                               # emergency revoke
        with self.assertRaises(ControlError) as cm:
            a.authenticate(old_unused)
        self.assertEqual(cm.exception.code, "UNAUTHENTICATED")          # revoked, not merely replayed
        a.authenticate(a.issue("x", "t1", "workload", set()))             # k2 still valid, no restart
        with self.assertRaises(ControlError):
            kr.add("weak", b"short")

    @covers(*ALL_TEMPLATE("P0-10", 9), *ALL_TEMPLATE("P0-11", 9), *ALL_TEMPLATE("P1-30", 9))
    def test_identity_policy_and_kms_outages_fail_closed(self):
        st = Stack()
        svc, authn = st.service()
        authn.available = False
        s, r = svc.handle("/v1/allocate", alloc_body(), workload_token(authn))
        self.assertEqual((s, r["code"]), (503, "DEPENDENCY_UNAVAILABLE"))
        authn.available = True
        svc.policy.available = False
        s, r = svc.handle("/v1/allocate", alloc_body(rid="req-sec-0002"), workload_token(authn))
        self.assertEqual(r["code"], "DEPENDENCY_UNAVAILABLE")
        self.assertEqual(len(st.ctl.leases()), 0)
        sp = SecretProvider(backend=lambda n: (_ for _ in ()).throw(TimeoutError()))
        with self.assertRaises(ControlError) as cm:
            sp.resolve("secretref://gap11-audit")
        self.assertEqual(cm.exception.code, "DEPENDENCY_UNAVAILABLE")
        with self.assertRaises(ControlError):
            SecretProvider().resolve("hunter2")                                       # inline secret refused


class AuthzTests(unittest.TestCase):
    @covers(*ALL_TEMPLATE("P0-11", 4, 5, 10), *ALL_TEMPLATE("P0-10", 4, 5))
    def test_deny_by_default_scopes_operator_only_and_cross_tenant(self):
        p = Policy([{"id": "a", "action": "lease:allocate", "kind": "workload"}])
        w = Principal("w", "t1", "workload", frozenset({"lease:allocate", "device:scrub"}))
        self.assertTrue(p.decide(w, "lease:allocate", {"tenant": "t1", "kind": "gpu"})["allow"])
        self.assertFalse(p.decide(w, "lease:release", {"tenant": "t1"})["allow"])    # no rule: deny
        self.assertEqual(p.decide(w, "device:scrub", {})["reason"], "operator-only action")   # escalation
        self.assertEqual(p.decide(w, "lease:allocate", {"tenant": "t2", "kind": "gpu"})["reason"], "cross-tenant resource")
        self.assertEqual(p.decide(w, "root:everything", {})["reason"], "unknown action")
        nos = Principal("w", "t1", "workload", frozenset())
        self.assertEqual(p.decide(nos, "lease:allocate", {"tenant": "t1"})["reason"], "scope not held")
        self.assertEqual(len({"read", "allocate", "release", "scrub", "quarantine", "unquarantine", "drain"} -
                             {s.split(":")[1].split("_")[0] for s in SCOPES}), 0)
        with self.assertRaises(ControlError):
            Policy([{"action": "lease:*"}])

    @covers(*ALL_TEMPLATE("P0-11", 2, 6, 10), *ALL_TEMPLATE("P0-10", 10), "GAP11-P2-37.04")
    def test_confused_deputy_and_cross_tenant_release_through_the_service(self):
        st = Stack()
        svc, authn = st.service()
        s, a = svc.handle("/v1/allocate", alloc_body("t1", "req-cd-00001"), workload_token(authn, "t1"))
        self.assertEqual(s, 200)
        # t2 claims to act for t1 in the body
        s, r = svc.handle("/v1/allocate", alloc_body("t1", "req-cd-00002"), workload_token(authn, "t2"))
        self.assertEqual(r["code"], "POLICY_DENIED")
        # t2 tries to release t1's lease by id
        rel = json.dumps({"schema": "PK_ACCELERATOR_RELEASE_REQUEST/1", "request_id": "req-cd-00003", "lease_id": a["lease_id"]}).encode()
        s, r = svc.handle("/v1/release", rel, workload_token(authn, "t2"))
        self.assertEqual((s, r["code"]), (403, "POLICY_DENIED"))
        # workload tries an operator action
        sc = json.dumps({"schema": "PK_SCRUB_REQUEST/1", "request_id": "req-cd-00004", "device": a["device"]}).encode()
        s, r = svc.handle("/v1/scrub", sc, workload_token(authn, "t1", scopes=("device:scrub",)))
        self.assertEqual(r["code"], "POLICY_DENIED")
        self.assertIn(a["lease_id"], st.ctl.leases())

    @covers(*ALL_TEMPLATE("P0-10", 8), *ALL_TEMPLATE("P0-11", 8), *ALL_TEMPLATE("P1-30", 8), *ALL_TEMPLATE("P0-09", 8))
    def test_sensitive_inventory_and_redaction(self):
        st = Stack()
        svc, authn = st.service()
        svc.handle("/v1/allocate", alloc_body("t1", "req-red-0001"), workload_token(authn, "t1"))
        s, inv = svc.handle("/v1/inventory", b"", workload_token(authn, "t2"))
        self.assertEqual(s, 200)
        self.assertTrue(all("security_tenant" not in d for d in inv["devices"]))
        s, inv = svc.handle("/v1/inventory", b"", operator_token(authn))
        self.assertTrue(any(d.get("security_tenant") == "t1" for d in inv["devices"]))
        red = redact({"token": "abc", "msg": "Authorization: Bearer eyJhbGciOi.x.y", "nested": [{"mac": "ff"}],
                      "k": "a" * 64, "security_tenant": "t1"})
        self.assertNotIn("eyJ", json.dumps(red))
        self.assertEqual(red["token"], "[REDACTED]")
        self.assertEqual(red["nested"][0]["mac"], "[REDACTED]")
        self.assertEqual(red["k"], "[REDACTED]")
        self.assertEqual(red["security_tenant"], "[REDACTED]")


class AttestationTests(unittest.TestCase):
    def setUp(self):
        self.clock = ManualClock()
        self.kr = Keyring(); self.kr.add("node-ak", secrets.token_bytes(32))
        self.v = AttestationVerifier(self.kr, clock=self.clock, allowed_firmware={"simnv": {"96.00.61"}})
        self.rec = normalize("simnv", NV, "node-1")

    @covers(*ALL_TEMPLATE("P0-09", 1, 2, 3, 6, 10))
    def test_quote_binds_node_device_capability_and_firmware(self):
        q = self.v.quote(self.rec, "node-1")
        self.assertTrue(self.v.verify(self.rec, "node-1", q)["attested"])
        cases = {
            "node": (self.rec, "node-2", q),
            "capability": ({**self.rec, "memory_gb": 160}, "node-1", q),                  # inflated capability
            "stable_id": ({**self.rec, "stable_id": "GPU-other"}, "node-1", q),
            "driver_firmware": ({**self.rec, "firmware": "96.00.00"}, "node-1", q),
        }
        for name, (rec, node, quote) in cases.items():
            with self.assertRaises(ControlError, msg=name) as cm:
                self.v.verify(rec, node, quote)
            self.assertEqual(cm.exception.code, "ATTESTATION_INVALID")
        tampered = json.loads(json.dumps(q)); tampered["claims"]["cap"] = "0" * 64
        with self.assertRaises(ControlError):
            self.v.verify(self.rec, "node-1", tampered)
        self.clock.advance(3601)
        with self.assertRaises(ControlError):                                         # stale quote
            self.v.verify(self.rec, "node-1", q)

    @covers(*ALL_TEMPLATE("P0-09", 7, 9))
    def test_firmware_allowlist_and_verifier_key_rotation(self):
        bad = {**self.rec, "firmware": "00.00.01"}
        with self.assertRaises(ControlError):
            self.v.verify(bad, "node-1", self.v.quote(bad, "node-1"))
        q_old = self.v.quote(self.rec, "node-1")
        self.kr.add("node-ak-2", secrets.token_bytes(32), activate=True)
        self.v.verify(self.rec, "node-1", q_old)
        self.kr.retire("node-ak")
        with self.assertRaises(ControlError):
            self.v.verify(self.rec, "node-1", q_old)


class SecretsTests(unittest.TestCase):
    @covers("GAP11-P1-29.08")
    def test_secret_references_resolve_through_backend_only(self):
        sp = SecretProvider()
        ref = sp.put_local("gap11-audit", b"x" * 32)
        self.assertEqual(sp.resolve(ref), b"x" * 32)
        kms = SecretProvider(backend=lambda name: {"gap11-audit": b"k" * 32}[name])
        self.assertEqual(kms.resolve("secretref://gap11-audit"), b"k" * 32)
        with self.assertRaises(ControlError):
            kms.resolve("secretref://missing")
        # a signed token never carries the key
        kr = Keyring(); kr.add("k", b"s" * 32)
        self.assertNotIn("sss", json.dumps(sign(kr, {"a": 1})))


if __name__ == "__main__":
    unittest.main()
