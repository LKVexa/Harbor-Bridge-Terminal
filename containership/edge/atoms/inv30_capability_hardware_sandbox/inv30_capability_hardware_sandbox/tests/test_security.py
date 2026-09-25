# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Adversarial security suite derived from docs/THREAT_MODEL.md (GAP-030, GAP-016, GAP-017, GAP-028, GAP-029).

Each test names the threat id it exercises (T-xx).
"""
import io
import json
import time
import unittest

from ..audit import AuditLedger
from ..authz import Authenticator, MintingAuthority, sign, verify_attestation
from ..errors import Unauthenticated, Unauthorized
from ._util import KEY_A, KEY_B, access, derive, invalidate, make_service, mint, signed


class SecurityTest(unittest.TestCase):
    def setUp(self):
        self.svc = make_service()
        self.root = mint(self.svc)["handle"]

    # T-01 pointer forgery / out-of-bounds
    def test_t01_forged_handle_and_oob(self):
        self.assertEqual(access(self.svc, "cap_" + "f" * 32, 0x1000)["code"], "NOT_FOUND")
        self.assertEqual(access(self.svc, self.root, 0x0FFF)["code"], "BOUNDS_VIOLATION")
        self.assertEqual(access(self.svc, self.root, 0x1FFC, size=8)["code"], "BOUNDS_VIOLATION")
        self.assertEqual(access(self.svc, self.root, 2 ** 64 - 8, size=8)["code"], "BOUNDS_VIOLATION")

    # T-02 permission amplification
    def test_t02_amplification(self):
        ro = derive(self.svc, self.root, 0x1000, 0x10, ["read"])["handle"]
        self.assertEqual(derive(self.svc, ro, 0x1000, 0x10, ["read", "write"])["code"], "AMPLIFICATION")
        self.assertEqual(derive(self.svc, ro, 0x1000, 0x11)["code"], "AMPLIFICATION")

    # T-03 use after invalidate / resurrection
    def test_t03_use_after_invalidate(self):
        child = derive(self.svc, self.root, 0x1000, 0x10)["handle"]
        invalidate(self.svc, self.root)
        for h in (self.root, child):
            self.assertEqual(access(self.svc, h, 0x1000)["code"], "INVALIDATED")
            self.assertEqual(derive(self.svc, h, 0x1000, 1)["code"], "INVALIDATED")

    # T-04 false hardware claim
    def test_t04_hardware_required_is_refused_on_model(self):
        r = mint(self.svc, require_hardware=True)
        self.assertEqual(r["code"], "HARDWARE_REQUIRED")
        with self.assertRaises(Exception) as cm:
            make_service(require_hardware=True)
        self.assertEqual(getattr(cm.exception, "code", None), "HARDWARE_REQUIRED")

    # T-05 malicious tenant: cross-tenant handle use
    def test_t05_cross_tenant(self):
        r = access(self.svc, self.root, 0x1000, tenant="tenant-b", principal="ctl-b", key=KEY_B)
        self.assertEqual(r["code"], "TENANT_MISMATCH")
        r = access(self.svc, self.root, 0x1000, tenant="tenant-a", principal="ctl-b", key=KEY_B)
        self.assertEqual(r["code"], "UNAUTHORIZED")

    # T-06 spoofing: bad MAC, unknown principal, skewed timestamp
    def test_t06_spoofing(self):
        b = {"schema": "PK_CAPABILITY_ACCESS/1", "handle": self.root, "tenant": "tenant-a", "address": 0x1000,
             "size": 8, "operation": "read"}
        a = signed("access", b)
        self.assertEqual(self.svc.access(b, dict(a, mac="0" * 64))["code"], "UNAUTHENTICATED")
        self.assertEqual(self.svc.access(b, signed("access", b, principal="ghost", key=b"G" * 32))["code"],
                         "UNAUTHENTICATED")
        self.assertEqual(self.svc.access(b, signed("access", b, ts=time.time() - 3600))["code"], "UNAUTHENTICATED")
        # body tampering after signing
        self.assertEqual(self.svc.access(dict(b, address=0x1008), a)["code"], "UNAUTHENTICATED")
        # action confusion: a signature for 'access' replayed as 'invalidate'
        ib = {"schema": "PK_CAPABILITY/1", "op": "invalidate", "tenant": "tenant-a", "handle": self.root}
        self.assertEqual(self.svc.invalidate(ib, signed("access", ib))["code"], "UNAUTHENTICATED")
        self.assertEqual(self.svc.access(b, signed("access", b))["permitted"], True)  # root still alive

    # T-07 replay
    def test_t07_replay(self):
        b = {"schema": "PK_CAPABILITY_ACCESS/1", "handle": self.root, "tenant": "tenant-a", "address": 0x1000,
             "size": 8, "operation": "read"}
        a = signed("access", b)
        self.assertTrue(self.svc.access(b, a)["permitted"])
        self.assertEqual(self.svc.access(b, a)["code"], "REPLAY")

    # T-08 escalation: principal without mint cannot mint
    def test_t08_privilege_escalation(self):
        b = {"schema": "PK_CAPABILITY/1", "op": "mint", "tenant": "tenant-b", "base": 0, "length": 16,
             "permissions": ["read"]}
        self.assertEqual(self.svc.mint(b, signed("mint", b, "ctl-b", KEY_B))["code"], "UNAUTHORIZED")

    # T-09 injection / hostile input
    def test_t09_injection(self):
        for bad in [{"schema": "PK_CAPABILITY_ACCESS/1", "handle": self.root + "'; DROP", "tenant": "tenant-a",
                     "address": 0, "size": 1, "operation": "read"},
                    {"schema": "PK_CAPABILITY_ACCESS/1", "handle": self.root, "tenant": "../../etc",
                     "address": 0, "size": 1, "operation": "read"},
                    {"schema": "PK_CAPABILITY_ACCESS/1", "handle": self.root, "tenant": "tenant-a",
                     "address": "0x1000", "size": 1, "operation": "read"}]:
            self.assertIn(self.svc.access(bad, signed("access", bad))["code"], ("SCHEMA_INVALID", "UNAUTHORIZED"))

    # T-10 forged provenance: tamper the grant in the table
    def test_t10_forged_grant(self):
        ent = self.svc._table[self.root]
        ent.grant = dict(ent.grant, length=2 ** 40)
        self.assertEqual(access(self.svc, self.root, 0x1000)["code"], "PROVENANCE_INVALID")

    # T-11 resource exhaustion
    def test_t11_exhaustion(self):
        svc = make_service(limits={"max_capabilities_per_tenant": 3, "max_derivation_depth": 64})
        r = mint(svc)["handle"]
        codes = [derive(svc, r, 0x1000, 1).get("code", "OK") for _ in range(5)]
        self.assertEqual(codes, ["OK", "OK", "LIMIT_EXCEEDED", "LIMIT_EXCEEDED", "LIMIT_EXCEEDED"])
        big = {"schema": "PK_CAPABILITY_ACCESS/1", "handle": r, "tenant": "tenant-a", "address": 0x1000,
               "size": 2 ** 31, "operation": "read"}
        self.assertEqual(svc.access(big, signed("access", big))["code"], "SCHEMA_INVALID")

    def test_t11_derivation_depth_limit(self):
        from ..core import Amplification, Capability
        c = Capability(0, 1 << 10, {"read"})
        with self.assertRaises(Amplification):
            for _ in range(100):
                c = c.derive(base=c.base, length=c.length)

    # T-12 diagnostics leak
    def test_t12_no_secret_or_raw_authority_in_diagnostics(self):
        buf = io.StringIO()
        self.svc.log.stream = buf
        access(self.svc, self.root, 0x9999)
        text = buf.getvalue() + json.dumps(self.svc.decisions.records) + self.svc.metrics.prometheus()
        self.assertNotIn(KEY_A.decode(), text)
        self.assertNotIn("tenant-a", text)  # tenants appear only as hashed buckets
        self.assertNotIn(self.root, text)
        self.assertNotIn("base", repr(self.svc._table[self.root].cap))

    # T-13 audit tampering
    def test_t13_audit_tamper_evident(self):
        led = AuditLedger(key=b"K" * 32)
        for i in range(5):
            led.append("x", "ok", i=i)
        self.assertEqual(led.verify(), [])
        led.events[2]["fields"]["i"] = 99
        self.assertTrue(led.verify())
        led2 = AuditLedger(key=b"K" * 32)
        for i in range(3):
            led2.append("x", "ok", i=i)
        head = led2.head
        led2.events.pop()
        self.assertTrue(led2.verify(expected_head=head))

    # T-14 peer/node attestation
    def test_t14_attestation(self):
        anchor = b"T" * 32
        doc = {"anchor": "estate-ca", "subject": "node-7", "measurement": "sha256:abc", "issued_at": 1000.0}
        doc["sig"] = sign(anchor, doc)
        ok = verify_attestation(doc, anchors={"estate-ca": anchor}, allowed_measurements={"sha256:abc"},
                                max_age_s=60, now=1010)
        self.assertEqual(ok["subject"], "node-7")
        for bad, exc in [(dict(doc, measurement="sha256:evil"), Unauthenticated),
                         (dict(doc, anchor="other"), Unauthenticated)]:
            with self.assertRaises(exc):
                verify_attestation(bad, anchors={"estate-ca": anchor}, allowed_measurements={"sha256:abc"},
                                   max_age_s=60, now=1010)
        with self.assertRaises(Unauthenticated):
            verify_attestation(doc, anchors={"estate-ca": anchor}, allowed_measurements={"sha256:abc"},
                               max_age_s=60, now=5000)
        d2 = {k: v for k, v in doc.items() if k != "sig"}
        d2["measurement"] = "sha256:evil"
        d2["sig"] = sign(anchor, d2)
        with self.assertRaises(Unauthorized):
            verify_attestation(d2, anchors={"estate-ca": anchor}, allowed_measurements={"sha256:abc"},
                               max_age_s=60, now=1010)

    # T-15 short keys refused
    def test_t15_weak_keys(self):
        with self.assertRaises(ValueError):
            MintingAuthority(b"short")
        with self.assertRaises(ValueError):
            Authenticator().register("x", b"short", {"access"}, {"t"})

    # T-16 side channel: MAC comparison uses constant-time primitive (static check)
    def test_t16_constant_time_compare_used(self):
        import inspect
        from .. import authz
        src = inspect.getsource(authz)
        self.assertIn("hmac.compare_digest", src)
        self.assertNotRegex(src, r"mac\s*==|sig\s*==")


if __name__ == "__main__":
    unittest.main()
