"""Component 5: DNS and destination-identity enforcement (adversarial suite)."""
import unittest

try:
    from . import _path  # noqa: F401
except ImportError:
    import _path  # type: ignore # noqa: F401

from inv20_http_component_worlds.egress import (
    Answer, DestinationPolicy, DnsDenied, DnsFailure, EgressPolicyDenied, RedirectLimit,
    check_identity_coherence, classify, proxy_environment_ignored,
)
import ipaddress


class FakeResolver:
    def __init__(self, table):
        self.table, self.calls = dict(table), 0

    def resolve(self, host):
        self.calls += 1
        v = self.table.get(host)
        if v is None:
            raise DnsFailure("nxdomain")
        if isinstance(v, Answer):
            return v
        return Answer(tuple(v), ttl=30)


class Clock:
    t = 0.0

    def __call__(self):
        return self.t


def policy(table, hosts=("api.example.com",), **kw):
    decisions = []
    p = DestinationPolicy.from_hosts(hosts, resolver=FakeResolver(table), on_decision=lambda r, d: decisions.append(r), **kw)
    return p, decisions


class EgressTest(unittest.TestCase):
    def test_allowed_pins_connect_ip(self):
        p, d = policy({"api.example.com": ["93.184.216.34"]})
        dest = p.authorize("https", "api.example.com")
        self.assertEqual((dest.connect_ip, dest.sni, dest.reason), ("93.184.216.34", "api.example.com", "allowed"))
        self.assertEqual(d, ["allowed"])

    def test_default_deny(self):
        p, d = policy({})
        with self.assertRaises(EgressPolicyDenied):
            p.authorize("https", "other.example.com")
        with self.assertRaises(EgressPolicyDenied):
            p.authorize("http", "api.example.com")         # scheme not allowed
        with self.assertRaises(EgressPolicyDenied):
            p.authorize("https", "api.example.com:8443")   # port not allowed
        self.assertEqual(d, ["not_allowlisted", "scheme", "not_allowlisted"])

    def test_rebinding_to_private_classes(self):
        cases = {"127.0.0.1": "loopback", "10.1.2.3": "private", "192.168.0.10": "private",
                 "169.254.169.254": "metadata", "169.254.1.1": "link_local", "0.0.0.0": "unspecified",
                 "224.0.0.1": "multicast", "::1": "loopback", "fd00::1": "private",
                 "::ffff:127.0.0.1": "mapped_denied", "64:ff9b::a00:1": "mapped_denied",
                 "100.100.100.200": "metadata", "198.18.0.1": "private"}
        for ip, why in cases.items():
            with self.subTest(ip=ip):
                p, d = policy({"api.example.com": [ip]})
                with self.assertRaises(DnsDenied):
                    p.authorize("https", "api.example.com")
                self.assertEqual(d[-1], why)

    def test_mixed_answer_rejected(self):
        p, d = policy({"api.example.com": ["93.184.216.34", "10.0.0.5"]})
        with self.assertRaises(DnsDenied):
            p.authorize("https", "api.example.com")
        self.assertEqual(d[-1], "mixed_answer")

    def test_cname_chain_denied(self):
        p, d = policy({"api.example.com": Answer(("93.184.216.34",), ("x.internal.corp.",))},
                      denied_cname_suffixes=(".internal.corp",))
        with self.assertRaises(DnsDenied):
            p.authorize("https", "api.example.com")

    def test_answer_change_between_checks_is_revalidated(self):
        clock = Clock()
        p, _ = policy({"api.example.com": ["93.184.216.34"]}, clock=clock)
        p.authorize("https", "api.example.com")
        p.resolver.table["api.example.com"] = ["127.0.0.1"]
        p.authorize("https", "api.example.com")          # cached within TTL: same validated IP
        clock.t = 31                                     # TTL expiry -> fresh answer, denied
        with self.assertRaises(DnsDenied):
            p.authorize("https", "api.example.com")
        p.resolver.table["api.example.com"] = ["93.184.216.34"]
        p.authorize("https", "api.example.com")
        p.resolver.table["api.example.com"] = ["10.0.0.1"]
        p.invalidate("api.example.com")                  # reconnect forces revalidation
        with self.assertRaises(DnsDenied):
            p.authorize("https", "api.example.com")

    def test_ip_literals(self):
        p, _ = policy({}, hosts=("93.184.216.34", "127.0.0.1"))
        with self.assertRaises(EgressPolicyDenied):
            p.authorize("https", "93.184.216.34")        # literals off by default
        p.allow_ip_literals = True
        self.assertEqual(p.authorize("https", "93.184.216.34").sni, None)
        with self.assertRaises(DnsDenied):
            p.authorize("https", "127.0.0.1")            # allow-listed but loopback class
        for enc in ("2130706433", "0x7f000001", "0177.0.0.1", "127.1"):
            with self.subTest(enc=enc), self.assertRaises(Exception):
                p.authorize("https", enc)

    def test_explicit_cidr_exception(self):
        p, _ = policy({"mesh.example.com": ["10.8.0.4"]}, hosts=("mesh.example.com",), allowed_cidrs=("10.8.0.0/24",))
        self.assertEqual(p.authorize("https", "mesh.example.com").connect_ip, "10.8.0.4")

    def test_redirects(self):
        p, _ = policy({"api.example.com": ["93.184.216.34"], "evil.example.com": ["93.184.216.35"]})
        hops = iter([("https", "evil.example.com")])
        with self.assertRaises(EgressPolicyDenied):
            p.follow_redirects("https", "api.example.com", lambda d: next(hops, None))
        with self.assertRaises(RedirectLimit):
            p.follow_redirects("https", "api.example.com", lambda d: ("https", "api.example.com"))
        p.max_redirects = 0
        self.assertEqual(p.follow_redirects("https", "api.example.com", lambda d: None).connect_ip, "93.184.216.34")

    def test_resolver_failure_fails_closed(self):
        p, _ = policy({})
        p.allowed_authorities = frozenset({("gone.example.com", 443)})
        with self.assertRaises(DnsFailure):
            p.authorize("https", "gone.example.com")

        class Broken:
            def resolve(self, h):
                raise RuntimeError("boom")
        p.resolver = Broken()
        with self.assertRaises(DnsFailure):
            p.authorize("https", "gone.example.com")

    def test_identity_coherence(self):
        p, _ = policy({"api.example.com": ["93.184.216.34"]})
        dest = p.authorize("https", "api.example.com")
        check_identity_coherence(dest, "api.example.com", ["api.example.com"])
        check_identity_coherence(dest, None, ["*.example.com"])
        with self.assertRaises(EgressPolicyDenied):
            check_identity_coherence(dest, "other.example.com", ["api.example.com"])
        with self.assertRaises(EgressPolicyDenied):
            check_identity_coherence(dest, None, ["evil.com"])

    def test_proxy_env_ignored(self):
        self.assertEqual(proxy_environment_ignored({"HTTPS_PROXY": "http://x", "PATH": "/"}), ["HTTPS_PROXY"])

    def test_classify_public(self):
        self.assertEqual(classify(ipaddress.ip_address("8.8.8.8")), "public")
        self.assertEqual(classify(ipaddress.ip_address("2606:4700::1111")), "public")


if __name__ == "__main__":
    unittest.main()
