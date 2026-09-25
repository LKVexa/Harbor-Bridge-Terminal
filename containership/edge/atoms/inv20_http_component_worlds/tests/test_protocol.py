"""Component 4: typed HTTP protocol model and error model."""
import unittest

try:
    from . import _path  # noqa: F401
except ImportError:
    import _path  # type: ignore # noqa: F401

from inv20_http_component_worlds.errors import REGISTRY, Inv20Error, error_from_dict, safe_detail
from inv20_http_component_worlds.protocol import (
    Fields, FieldLimits, ForbiddenField, FieldLimit, InvalidAuthority, InvalidField, InvalidMethod,
    InvalidPath, InvalidScheme, InvalidStatus, Request, Response, parse_authority, validate_trailers,
)


class AuthorityTest(unittest.TestCase):
    def test_golden(self):
        a = parse_authority("API.Example.com")
        self.assertEqual((a.host, a.port, a.is_ip), ("api.example.com", 443, False))
        self.assertEqual(parse_authority("example.com:80", "http").port, 80)
        self.assertEqual(parse_authority("[2001:DB8::1]:8443").host, "2001:db8::1")
        self.assertTrue(parse_authority("10.0.0.1").is_ip)

    def test_rejects(self):
        for bad in ("user@h.com", "h.com:0", "h.com:65536", "h.com:080", "h.com:", "[fe80::1%eth0]",
                    "2001:db8::1", "h.com/x", " h.com", "", "[::1", "h..com", "h.com:44a", "h_com"):
            with self.subTest(bad=bad), self.assertRaises(InvalidAuthority):
                parse_authority(bad)
        with self.assertRaises(InvalidScheme):
            parse_authority("h.com", "ftp")
        with self.assertRaises(InvalidAuthority):
            parse_authority("h.com:8080", allowed_ports=[443])

    def test_normalization_differential(self):
        # Equivalent spellings must canonicalise identically (policy and transport share this).
        self.assertEqual(parse_authority("EXAMPLE.com."), parse_authority("example.com:443"))
        self.assertEqual(parse_authority("[::ffff:127.0.0.1]").host, "::ffff:127.0.0.1")

    def test_idna_unicode_rejected(self):
        for bad in ("bücher.de", "exa​mple.com", "ｅxample.com"):
            with self.subTest(bad=bad), self.assertRaises(InvalidAuthority):
                parse_authority(bad)


class FieldsTest(unittest.TestCase):
    def test_names_values(self):
        f = Fields([("Content-Type", "text/plain"), ("X-A", "1"), ("x-a", "2")])
        self.assertEqual(f.get_all("x-a"), ["1", "2"])
        with self.assertRaises(InvalidField):
            f.get("X-A")  # duplicate singleton is ambiguous
        for name in ("bad name", "", "x:y", "x\r\n"):
            with self.subTest(name=name), self.assertRaises(InvalidField):
                Fields([(name, "v")])
        for val in ("a\r\nInjected: 1", "a\nb", "a\x00", " lead", "trail ", "café"):
            with self.subTest(val=val), self.assertRaises(InvalidField):
                Fields([("x", val)])

    def test_forbidden(self):
        for name in ("connection", "transfer-encoding", "te", "upgrade", ":path"):
            with self.subTest(name=name), self.assertRaises(ForbiddenField):
                Fields([(name, "x")])

    def test_limits(self):
        lim = FieldLimits(max_fields=2, max_total_bytes=20, max_name_bytes=5, max_value_bytes=5)
        with self.assertRaises(FieldLimit):
            Fields([("a", "1"), ("b", "1"), ("c", "1")], limits=lim)
        with self.assertRaises(FieldLimit):
            Fields([("abcdef", "1")], limits=lim)
        with self.assertRaises(FieldLimit):
            Fields([("a", "123456")], limits=lim)
        with self.assertRaises(FieldLimit):
            Fields([("abcde", "12345"), ("abcde", "12345"), ], limits=FieldLimits(max_total_bytes=15))

    def test_boundary_exact_limit_accepted(self):
        lim = FieldLimits(max_fields=1, max_total_bytes=10, max_name_bytes=5, max_value_bytes=5)
        self.assertEqual(len(Fields([("abcde", "12345")], limits=lim)), 1)

    def test_trailer_smuggling(self):
        hdr = Fields([("x-reviewed", "1")])
        for name in ("authorization", "host", "content-length", "set-cookie", "location"):
            with self.subTest(name=name), self.assertRaises(ForbiddenField):
                Fields([(name, "x")], trailers=True)
        with self.assertRaises(ForbiddenField):
            validate_trailers(Fields([("x-reviewed", "2")], trailers=True), hdr)
        with self.assertRaises(ForbiddenField):
            validate_trailers(Fields([("x-digest", "2")]), hdr)
        ok = validate_trailers(Fields([("x-digest", "sha-256=:a:")], trailers=True), hdr)
        self.assertEqual(ok.names(), ["x-digest"])
        with self.assertRaises(FieldLimit):
            Fields([(f"x-{i}", "v") for i in range(17)], trailers=True)


class MessageTest(unittest.TestCase):
    def test_request(self):
        r = Request.build("GET", "https", "api.example.com", "/v1/items?q=a%20b", [("host", "api.example.com:443")])
        self.assertTrue(r.idempotent)
        self.assertEqual(r.path_with_query, "/v1/items?q=a%20b")  # preserved, not re-encoded
        self.assertFalse(Request.build("POST", "https", "h.com").idempotent)

    def test_request_rejects(self):
        with self.assertRaises(InvalidMethod):
            Request.build("get", "https", "h.com")
        with self.assertRaises(InvalidMethod):
            Request.build("G ET", "https", "h.com")
        for p in ("v1", "//evil.com/x", "/a%zz", "/a b", "/x#frag"):
            with self.subTest(p=p), self.assertRaises(InvalidPath):
                Request.build("GET", "https", "h.com", p)
        with self.assertRaises(InvalidAuthority):
            Request.build("GET", "https", "h.com", "/", [("host", "other.com")])
        with self.assertRaises(InvalidAuthority):
            Request("GET", "https", "h.com", "/")  # raw string authority refused

    def test_extension_method_allowed(self):
        self.assertEqual(Request.build("PROPFIND", "https", "h.com").method, "PROPFIND")

    def test_status(self):
        self.assertEqual(Response(204).status_class, "2xx")
        for bad in (99, 600, True, "200"):
            with self.subTest(bad=bad), self.assertRaises(InvalidStatus):
                Response(bad)


class ErrorModelTest(unittest.TestCase):
    def test_registry_complete_and_stable(self):
        cats = {s.category.value for s in REGISTRY.values()}
        for c in ("caller_error", "policy_denial", "resource_exhaustion", "timeout", "cancellation",
                  "upstream_error", "protocol_violation", "internal_defect"):
            self.assertIn(c, cats)
        with self.assertRaises(KeyError):
            Inv20Error("x", code="E_NOT_REAL")

    def test_roundtrip_and_bounded_detail(self):
        e = InvalidField("A" * 1000 + "\r\n")
        self.assertLessEqual(len(e.detail), 160)
        self.assertNotIn("\r", e.detail)
        self.assertEqual(error_from_dict(e.to_dict()).code, "E_INVALID_FIELD")
        self.assertEqual(error_from_dict({"code": "E_X"}).code, "E_ILLEGAL_STATE")
        self.assertEqual(safe_detail("\x1b[31m"), "\\x1b[31m")


if __name__ == "__main__":
    unittest.main()
