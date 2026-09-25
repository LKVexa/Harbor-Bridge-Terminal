import unittest
from inv65_capability_providers.tests.helpers import World, ident
from inv65_capability_providers.errors.mapping import ProviderFault
from inv65_capability_providers.identity.context import IdentityContext


class IdentityBinding(unittest.TestCase):
    def setUp(self):
        self.w = World(); self.w.svc.start(); self.w.link()

    def test_same_names_other_tenant_is_a_different_link(self):
        for ov in ({"tenant": "globex"}, {"env": "staging"}, {"site": "nyc1"}, {"workload": "other"}, {"component": "billing"}):
            with self.subTest(ov=ov), self.assertRaises(ProviderFault) as c:
                self.w.call(**ov)
            self.assertEqual(c.exception.code, "PK_PROVIDER_NO_LINK")

    def test_two_tenants_same_link_name_are_isolated(self):
        self.w.link(tenant="globex", cfg={"bucket": "globex-b", "user": "g"})
        self.assertEqual(self.w.call()["result"]["bucket"], "acme-primary")
        self.assertEqual(self.w.call(tenant="globex")["result"]["bucket"], "globex-b")

    def test_unauthenticated_context_cannot_be_constructed_as_trusted(self):
        c = IdentityContext(**{k if k != "env" else "environment": v for k, v in ident().items()})
        self.assertFalse(c.authenticated)

    def test_link_names_listing_is_scope_bound(self):
        self.w.link(name="archive")
        self.w.link(tenant="globex", name="secret-plan", cfg={"bucket": "g", "user": "g"})
        self.assertEqual(self.w.svc.link_names(self.w.token()), ["archive", "primary"])
