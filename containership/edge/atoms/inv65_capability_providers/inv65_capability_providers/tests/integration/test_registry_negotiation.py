import unittest
from inv65_capability_providers.errors.mapping import ProviderFault
from inv65_capability_providers.registry.model import ProviderRegistry
from inv65_capability_providers.supply_chain.trust import ArtifactTrust

D1, D2 = "a" * 64, "b" * 64


def reg(inst="i1", epoch=1, digest=D1, versions=("1.0", "1.1")):
    return {"instance_id": inst, "contract_id": "wasi:keyvalue", "versions": list(versions), "site": "sfo1",
            "environment": "prod", "implementation_digest": digest, "lease_epoch": epoch}


class Registry(unittest.TestCase):
    def setUp(self):
        self.r = ProviderRegistry(ArtifactTrust({"contracts": {"wasi:keyvalue": [{"sha256": D1}, {"sha256": D2, "revoked": True}]}}))

    def test_register_discover_negotiate(self):
        self.r.register(reg())
        cur, v = self.r.discover("wasi:keyvalue", site="sfo1", environment="prod", versions=["1.0", "1.1"])
        self.assertEqual((cur["instance_id"], v), ("i1", "1.1"))
        with self.assertRaises(ProviderFault) as c:
            self.r.discover("wasi:keyvalue", site="sfo1", environment="prod", versions=["2.0"])
        self.assertEqual(c.exception.code, "PK_PROVIDER_INCOMPATIBLE")

    def test_duplicate_owner_refused_higher_epoch_takes_over(self):
        self.r.register(reg())
        with self.assertRaises(ProviderFault):
            self.r.register(reg("i2", 1))
        self.r.register(reg("i2", 2))
        self.assertFalse(self.r.deregister("wasi:keyvalue", "sfo1", "prod", "i1", 1))

    def test_untrusted_or_revoked_artifact_refused(self):
        for d in ("c" * 64, D2):
            with self.assertRaises(ProviderFault) as c:
                self.r.register(reg(digest=d))
            self.assertEqual(c.exception.code, "PK_PROVIDER_UNTRUSTED_ARTIFACT")

    def test_malformed_registration(self):
        with self.assertRaises(ProviderFault):
            self.r.register({"instance_id": "x"})
