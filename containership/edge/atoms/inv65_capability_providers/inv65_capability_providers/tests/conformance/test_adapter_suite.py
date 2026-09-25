"""M38: one contract suite run against three capability classes."""
import unittest
from inv65_capability_providers.tests.helpers import World
from inv65_capability_providers.errors.mapping import ProviderFault
from inv65_capability_providers.fixtures.providers.broker import BrokerBackend
from inv65_capability_providers.fixtures.providers.http import HttpBackend
from inv65_capability_providers.fixtures.providers.keyvalue import KeyValueBackend

CASES = [
    ("wasi:keyvalue", KeyValueBackend, "get", {"key": "k"}, {}),
    ("wasi:http", HttpBackend, "request", {"url": "https://api.example.com/x"}, {"allowed_hosts": ["api.example.com"]}),
    ("wasmcloud:messaging", BrokerBackend, "publish", {"subject": "s", "body": "b"}, {}),
]


class AdapterSuite(unittest.TestCase):
    def test_contract_invariants_hold_for_every_capability_class(self):
        for contract, B, op, payload, extra in CASES:
            with self.subTest(contract=contract):
                w = World(backend=B(), contract=contract); w.svc.start()
                w.link("a", {"bucket": "A", "user": "ua", **extra}); w.link("b", {"bucket": "B", "user": "ub", **extra})
                w.call("a", op, payload); w.call("b", op, payload)
                with self.assertRaises(ProviderFault) as c:
                    w.call("a", op, payload, tenant="globex")
                self.assertEqual(c.exception.code, "PK_PROVIDER_NO_LINK")
                w.unlink("a")
                w2 = World(backend=B(), contract=contract, state_dir=w.tmp); w2.svc.start()
                with self.assertRaises(ProviderFault):
                    w2.call("a", op, payload)
                w2.call("b", op, payload)
                w2.backend.up = False
                self.assertFalse(w2.svc.health()["ready"])

    def test_broker_links_cannot_read_each_others_messages(self):
        w = World(backend=BrokerBackend(), contract="wasmcloud:messaging"); w.svc.start()
        w.link("a", {"bucket": "A", "user": "u"}); w.link("b", {"bucket": "B", "user": "u"})
        w.call("a", "publish", {"subject": "s", "body": "secret-a"})
        self.assertIsNone(w.call("b", "pull", {"subject": "s"})["result"]["body"])
        self.assertEqual(w.call("a", "pull", {"subject": "s"})["result"]["body"], "secret-a")

    def test_http_destination_bound_to_link_config(self):
        w = World(backend=HttpBackend(), contract="wasi:http"); w.svc.start()
        w.link("a", {"bucket": "A", "user": "u", "allowed_hosts": ["api.example.com"]})
        with self.assertRaises(ProviderFault) as c:
            w.call("a", "request", {"url": "https://evil.example.net/"})
        self.assertEqual(c.exception.code, "PK_PROVIDER_FORBIDDEN")
