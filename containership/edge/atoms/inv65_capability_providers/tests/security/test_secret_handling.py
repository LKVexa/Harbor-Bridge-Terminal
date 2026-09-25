import json, unittest
from inv65_capability_providers.tests.helpers import World
from inv65_capability_providers.errors.mapping import ProviderFault
from inv65_capability_providers.secret_refs.resolver import SecretValue


class Secrets(unittest.TestCase):
    def setUp(self):
        self.w = World(); self.w.svc.start()
        self.scope = ("acme", "prod", "sfo1", "shop", "orders")
        self.w.inv55.put("secret://kv/orders", self.scope, b"S3CR3T-v1")
        self.w.link(secret_ref="secret://kv/orders")

    def test_secret_resolved_in_scope_and_never_persisted_or_logged(self):
        self.w.call()
        self.assertEqual(self.w.backend.seen_secret_versions, [1])
        blob = open(self.w.tmp + "/wal.jsonl").read() + json.dumps(self.w.svc.audit.events()) + "\n".join(self.w.svc.log.sink)
        self.assertNotIn("S3CR3T", blob)
        self.assertIn("secret://kv/orders", open(self.w.tmp + "/wal.jsonl").read())

    def test_other_scope_cannot_resolve(self):
        self.w.link(tenant="globex", secret_ref="secret://kv/orders", cfg={"bucket": "g", "user": "g"})
        with self.assertRaises(ProviderFault) as c:
            self.w.call(tenant="globex")
        self.assertEqual(c.exception.code, "PK_PROVIDER_SECRET_UNAVAILABLE")

    def test_rotation_picks_up_new_version_after_invalidate(self):
        self.w.call()
        self.w.inv55.put("secret://kv/orders", self.scope, b"S3CR3T-v2")
        self.w.svc.secrets.invalidate("secret://kv/orders")
        self.w.call()
        self.assertEqual(self.w.backend.seen_secret_versions, [1, 2])

    def test_revoked_secret_fails_closed_even_if_cached_expired(self):
        self.w.svc.secrets.ttl_s = 0
        self.w.inv55.revoke("secret://kv/orders", self.scope)
        with self.assertRaises(ProviderFault) as c:
            self.w.call()
        self.assertEqual(c.exception.code, "PK_PROVIDER_SECRET_UNAVAILABLE")

    def test_backend_outage_fails_closed(self):
        self.w.svc.secrets.ttl_s = 0
        self.w.inv55.available = False
        with self.assertRaises(ProviderFault):
            self.w.call()

    def test_secret_value_redacts_and_zeroizes(self):
        v = SecretValue(b"abc", 1)
        self.assertNotIn("abc", repr(v) + str(v))
        v.zeroize()
        with self.assertRaises(ProviderFault):
            v.reveal()

    def test_bad_refs_and_inline_secrets_rejected(self):
        for ref in ("http://x", "secret://../etc", "secret://A", "secret://" + "a" * 300):
            with self.subTest(ref=ref), self.assertRaises(ProviderFault):
                self.w.link(name="n2", secret_ref=ref)
        with self.assertRaises(ProviderFault):
            self.w.link(name="n3", cfg={"bucket": "b", "user": "u", "apiKey": "x"})
