"""Real HashiCorp Vault integration (checklist #82, #83).

Runs only when INV55_VAULT_ADDR and INV55_VAULT_TOKEN point at a disposable Vault
(e.g. ``vault server -dev`` in CI, see .github/workflows/ci.yml job ``vault-real``).
When the variables are absent the tests SKIP -- and a skip is NOT a pass: the
release gate (tools/exit_gate.py) treats this suite as mandatory for production.
"""
from __future__ import annotations

import os
import unittest
import uuid

from helpers import Env
from inv55_secrets_integration.providers.vault import TokenAuth, VaultProvider
from inv55_secrets_integration.secretvalue import SecretValue

ADDR, TOKEN = os.environ.get("INV55_VAULT_ADDR"), os.environ.get("INV55_VAULT_TOKEN")


@unittest.skipUnless(ADDR and TOKEN, "MANDATORY-SKIP: INV55_VAULT_ADDR/INV55_VAULT_TOKEN not set")
class RealVault(unittest.TestCase):
    def setUp(self):
        self.p = VaultProvider(ADDR, TokenAuth(SecretValue(TOKEN)),
                               allow_insecure_http=ADDR.startswith("http://127.0.0.1"))
        self.name = f"inv55-it/{uuid.uuid4().hex}"

    def test_health_supported_version(self):
        h = self.p.health()
        self.assertTrue(h.reachable)
        self.assertEqual(h.detail, "", f"server {h.version} outside compatibility matrix")

    def test_kv2_roundtrip_cas_destroy(self):
        self.assertEqual(self.p.write(self.name, SecretValue("a")), 1)
        self.assertEqual(self.p.write(self.name, SecretValue("b"), cas=1), 2)
        self.assertEqual(self.p.read(self.name).value.reveal(), "b")
        self.p.destroy_version(self.name, 1)
        from inv55_secrets_integration.providers.base import ProviderNotFound
        with self.assertRaises(ProviderNotFound):
            self.p.read(self.name, 1)

    def test_service_end_to_end(self):
        e = Env(provider=self.p)
        e.seed(name="it-" + uuid.uuid4().hex[:8])
