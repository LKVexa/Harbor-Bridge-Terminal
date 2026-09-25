"""Authentication, secrets, redaction, TLS configuration (MC-022, MC-024, MC-025)."""
from __future__ import annotations

import os
import ssl
import time
import unittest

from _util import NS_A, FakeClock, tmpdir
from inv05_current_control_state_system.errors import InvalidArgument, Unauthenticated
from inv05_current_control_state_system.security import (
    MTLSAuthenticator, SecretProvider, TokenAuthenticator, check_tls_context, client_tls_context, derive_key,
    redact,
)

URI = "spiffe://inv05.local/tenant/acme/env/prod/site/site-a/wl/ctrl/svc"


def cert(uri=URI, nb="Jan  1 00:00:00 2020 GMT", na="Jan  1 00:00:00 2099 GMT", serial="0A"):
    return {"subjectAltName": (("URI", uri),), "notBefore": nb, "notAfter": na, "serialNumber": serial}


class MTLSTest(unittest.TestCase):
    def setUp(self):
        self.a = MTLSAuthenticator("inv05.local", role_map={"client": {"writer"}, "admin": {"operator"}})

    def test_valid_identity_binds_namespace(self):
        p = self.a.authenticate(cert())
        self.assertEqual(p.namespace, NS_A)
        self.assertEqual(p.roles, frozenset({"writer"}))

    def test_rejections(self):
        cases = {
            "no cert": None,
            "expired": cert(na="Jan  1 00:00:00 2021 GMT"),
            "not yet valid": cert(nb="Jan  1 00:00:00 2098 GMT"),
            "foreign trust domain": cert(uri=URI.replace("inv05.local", "evil.local")),
            "malformed spiffe": cert(uri="spiffe://inv05.local/tenant/acme"),
            "wrong purpose": cert(uri=URI.replace("/svc", "/peer-1")),
            "two SANs": {**cert(), "subjectAltName": (("URI", URI), ("URI", URI))},
        }
        for name, c in cases.items():
            with self.subTest(name), self.assertRaises(Unauthenticated):
                self.a.authenticate(c)
        self.a.revoke("0a")
        with self.assertRaises(Unauthenticated):
            self.a.authenticate(cert())


class TokenTest(unittest.TestCase):
    def test_issue_verify_rotate_expire(self):
        clock = FakeClock(1_000_000)
        t = TokenAuthenticator({"k1": b"a" * 32}, "k1", clock=clock)
        tok = t.issue("svc", NS_A, ["writer"], ttl_s=60)
        self.assertEqual(t.authenticate(tok).namespace, NS_A)
        t.keys["k2"] = b"b" * 32
        t.active = "k2"
        self.assertEqual(t.authenticate(tok).subject, "svc")  # old kid still accepted until removed
        del t.keys["k1"]
        with self.assertRaises(Unauthenticated):
            t.authenticate(tok)
        tok2 = t.issue("svc", NS_A, ["writer"], ttl_s=60)
        clock.advance(61)
        with self.assertRaises(Unauthenticated):
            t.authenticate(tok2)

    def test_forgery_and_replay_to_other_audience(self):
        t = TokenAuthenticator({"k": b"a" * 32}, "k")
        tok = t.issue("svc", NS_A, ["reader"])
        raw, sig = tok.split(".")
        import base64, json
        body = json.loads(base64.urlsafe_b64decode(raw))
        body["roles"] = ["security-admin"]
        forged = base64.urlsafe_b64encode(json.dumps(body, sort_keys=True).encode()).decode() + "." + sig
        for bad in (forged, tok + "x", "", "a.b.c", None):
            with self.assertRaises(Unauthenticated):
                t.authenticate(bad)
        other = TokenAuthenticator({"k": b"a" * 32}, "k", audience="other")
        with self.assertRaises(Unauthenticated):
            other.authenticate(tok)


class SecretsTest(unittest.TestCase):
    def test_secret_file_permissions_and_env(self):
        d = tmpdir()
        p = os.path.join(d, "data-key")
        with open(p, "w") as fh:
            fh.write("s3cr3t\n")
        os.chmod(p, 0o644)
        sp = SecretProvider(d)
        with self.assertRaises(InvalidArgument):
            sp.get("secret://data-key")
        os.chmod(p, 0o600)
        self.assertEqual(sp.get("secret://data-key"), b"s3cr3t")
        os.environ["INV05_SECRET_AUDIT_KEY"] = "from-env"
        self.assertEqual(sp.get("secret://audit-key"), b"from-env")
        for bad in ("plain", "secret://../etc/passwd", "secret://missing"):
            with self.assertRaises(InvalidArgument):
                sp.get(bad)

    def test_error_messages_never_carry_secret_values(self):
        sp = SecretProvider(None)
        try:
            sp.get("secret://nope")
        except InvalidArgument as e:
            self.assertNotIn("nope", str(e.to_wire()["details"]))

    def test_redaction(self):
        r = redact({"password": "p", "nested": {"api_key": "k", "ok": 1}, "list": [{"token": "t"}],
                    "authorization": "Bearer x", "value": "x" * 90 + "." + "y" * 10})
        self.assertEqual(r["password"], "[REDACTED]")
        self.assertEqual(r["nested"], {"api_key": "[REDACTED]", "ok": 1})
        self.assertEqual(r["list"][0]["token"], "[REDACTED]")
        self.assertEqual(r["value"], "[REDACTED]")

    def test_key_derivation_separates_purposes(self):
        self.assertNotEqual(derive_key(b"m", "wal"), derive_key(b"m", "audit"))
        self.assertEqual(len(derive_key(b"m", "wal")), 32)


class TLSConfigTest(unittest.TestCase):
    def test_client_context_policy(self):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20")
        self.assertEqual(check_tls_context(ctx, server=False), [])
        ctx.check_hostname = False
        self.assertTrue(check_tls_context(ctx, server=False))
        weak = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        weak.minimum_version = ssl.TLSVersion.TLSv1_2
        weak.set_ciphers("AES128-SHA")
        self.assertTrue(any("non-AEAD" in p for p in check_tls_context(weak, server=False)))


if __name__ == "__main__":
    unittest.main()
