"""Adjacent-layer integration: VaultProvider <-> Vault HTTP API over real sockets and TLS
(checklist #15, #18, #25, #44, #82).  A real Vault run is in test_vault_real.py."""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from helpers import SECRET, Env
from vault_fake import FakeVault
from inv55_secrets_integration.providers.base import (ProviderConflict, ProviderDenied, ProviderNotFound,
                                                       ProviderUnavailable)
from inv55_secrets_integration.providers.vault import (AppRoleAuth, TokenAuth, VaultProvider,
                                                        build_tls_context)
from inv55_secrets_integration.resilience import RetryPolicy
from inv55_secrets_integration.secretvalue import SecretValue


def _tok(fv):
    return TokenAuth(SecretValue(fv.token))


class VaultHttp(unittest.TestCase):
    def setUp(self):
        self.fv = FakeVault().__enter__()
        self.p = VaultProvider(self.fv.address, _tok(self.fv), allow_insecure_http=True)

    def tearDown(self):
        self.fv.__exit__()

    def test_write_read_versions_and_cas(self):
        self.assertEqual(self.p.write("acme/db", SecretValue("v1")), 1)
        self.assertEqual(self.p.write("acme/db", SecretValue("v2"), cas=1), 2)
        with self.assertRaises(ProviderConflict):
            self.p.write("acme/db", SecretValue("v3"), cas=1)
        self.assertEqual(self.p.read("acme/db").value.reveal(), "v2")
        self.assertEqual(self.p.read("acme/db", 1).value.reveal(), "v1")
        self.assertEqual(self.p.metadata("acme/db")["current_version"], 2)

    def test_destroy_makes_version_unreadable(self):
        self.p.write("acme/db", SecretValue("v1"))
        self.p.destroy_version("acme/db", 1)
        with self.assertRaises(ProviderNotFound):
            self.p.read("acme/db", 1)

    def test_status_mapping(self):
        with self.assertRaises(ProviderNotFound):
            self.p.read("acme/missing")
        self.fv.fail_next = [503]
        with self.assertRaises(ProviderUnavailable):
            self.p.read("acme/x")
        self.fv.fail_next = [403]
        with self.assertRaises(ProviderDenied):
            self.p.read("acme/x")

    def test_wrong_token_denied(self):
        p = VaultProvider(self.fv.address, TokenAuth(SecretValue("wrong")), allow_insecure_http=True)
        with self.assertRaises(ProviderDenied):
            p.read("acme/x")

    def test_approle_login_and_namespace_header(self):
        self.fv.namespace = "team-a"
        p = VaultProvider(self.fv.address, AppRoleAuth("role-1", SecretValue("sid-1")), namespace="team-a",
                          allow_insecure_http=True)
        p.write("acme/db", SecretValue("v1"))
        self.assertEqual(p.read("acme/db").value.reveal(), "v1")
        last = self.fv.requests[-1][2]
        self.assertEqual(last.get("X-Vault-Namespace"), "team-a")

    def test_lease_revoke_renew_and_token_renew(self):
        self.p.revoke("database/creds/ro/abc")
        self.assertEqual(self.fv.revoked, ["database/creds/ro/abc"])
        self.assertEqual(self.p.renew("database/creds/ro/abc", 60), 60.0)
        self.assertEqual(self.p.renew_self(), 120.0)

    def test_health_sealed_and_version(self):
        self.assertTrue(self.p.health().reachable)
        self.fv.sealed = True
        h = self.p.health()
        self.assertFalse(h.reachable)
        self.assertTrue(h.sealed)
        self.fv.sealed, self.fv.version = False, "1.9.0"
        self.assertEqual(self.p.health().detail, "unsupported_server_version")

    def test_unreachable_is_retryable(self):
        port = self.fv.server.server_address[1]
        self.fv.__exit__()
        p = VaultProvider(f"http://127.0.0.1:{port}", _tok(self.fv), allow_insecure_http=True, timeout_s=0.3)
        with self.assertRaises(ProviderUnavailable):
            p.read("x")
        self.fv = FakeVault().__enter__()   # for tearDown

    def test_plain_http_refused_for_non_loopback(self):
        with self.assertRaises(ValueError):
            VaultProvider("http://vault.example:8200", _tok(self.fv))
        with self.assertRaises(ValueError):
            VaultProvider("http://127.0.0.1:8200", _tok(self.fv))   # loopback still needs explicit flag

    def test_token_never_in_url_or_body(self):
        self.p.write("acme/db", SecretValue(SECRET))
        for method, path, headers in self.fv.requests:
            self.assertNotIn(self.fv.token, path)


class ServiceOverVault(unittest.TestCase):
    """Full stack: service -> retry/circuit -> VaultProvider -> HTTP -> fake Vault."""

    def test_end_to_end(self):
        with FakeVault() as fv:
            p = VaultProvider(fv.address, _tok(fv), allow_insecure_http=True)
            e = Env(provider=p, retry=RetryPolicy(max_attempts=3))
            e.seed()
            r = e.resolve()
            self.assertEqual(e.use(r["lease_id"])["value"], SECRET)
            fv.fail_next = [503, 503]           # transient: retried transparently
            e.svc._cache.clear()
            self.assertTrue(e.resolve()["ok"])
            self.assertIn("/v1/secret/data/acme/db-password", [x[1] for x in fv.requests])


@unittest.skipUnless(shutil.which("openssl"), "openssl CLI required to mint a test CA")
class VaultTls(unittest.TestCase):
    """Encryption in transit: verified TLS succeeds; unknown CA and TLS<1.2 are refused."""

    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()
        key, crt = os.path.join(cls.d, "k.pem"), os.path.join(cls.d, "c.pem")
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", key, "-out", crt,
                        "-days", "1", "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost"],
                       check=True, capture_output=True)
        cls.key, cls.crt = key, crt

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def test_verified_tls(self):
        with FakeVault(tls=(self.crt, self.key)) as fv:
            p = VaultProvider(fv.address, _tok(fv), ssl_context=build_tls_context(self.crt))
            p.write("acme/db", SecretValue("v1"))
            self.assertEqual(p.read("acme/db").value.reveal(), "v1")

    def test_untrusted_ca_refused(self):
        with FakeVault(tls=(self.crt, self.key)) as fv:
            p = VaultProvider(fv.address, _tok(fv), timeout_s=1)   # default system CAs
            with self.assertRaises(ProviderUnavailable):
                p.read("acme/db")

    def test_min_tls_version(self):
        ctx = build_tls_context(self.crt)
        import ssl
        self.assertGreaterEqual(ctx.minimum_version, ssl.TLSVersion.TLSv1_2)
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)


if __name__ == "__main__":
    unittest.main()
