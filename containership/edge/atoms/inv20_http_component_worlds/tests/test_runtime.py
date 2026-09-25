"""Dependency-independent unit/security tests for INV-20 runtime primitives."""
import unittest

try:
    from . import _path  # noqa: F401
except ImportError:  # executed as a script
    import _path  # type: ignore # noqa: F401

from inv20_http_component_worlds.runtime import (  # noqa: E402
    BodyStream, BodyTooLarge, Completion, CompletionAlreadyResolved,
    EgressDenied, HttpMessage, HttpWorld, InvalidHost, NoOutgoingCapability,
    canonical_host,
)


class RuntimeTest(unittest.TestCase):
    def test_stream_is_bounded_and_copies_mutable_input(self):
        stream = BodyStream(limit=4)
        data = bytearray(b"ab")
        stream.write(data)
        data[:] = b"zz"
        self.assertEqual(stream.forward(), b"ab")
        with self.assertRaises(BodyTooLarge):
            stream.write(b"12345")

    def test_stream_limit_validation(self):
        for bad in (-1, True, 1.5):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                BodyStream(limit=bad)

    def test_trailers_are_single_resolution_completion(self):
        message = HttpMessage()
        with self.assertRaises(RuntimeError):
            message.trailers.result()
        message.trailers.resolve({"x-checksum": "ok"})
        self.assertEqual(message.trailers.result(), {"x-checksum": "ok"})
        with self.assertRaises(CompletionAlreadyResolved):
            message.trailers.resolve({})

    def test_world_requires_explicit_outgoing_capability(self):
        with self.assertRaises(ValueError):
            HttpWorld("bad", allowed_hosts=frozenset({"example.com"}))
        sealed = HttpWorld("sealed")
        with self.assertRaises(NoOutgoingCapability):
            sealed.fetch("example.com")

    def test_egress_is_exact_host_allowlist(self):
        world = HttpWorld("api", outgoing_granted=True, allowed_hosts=frozenset({"Example.COM."}))
        self.assertEqual(world.fetch("example.com"), ("ok", "example.com"))
        with self.assertRaises(EgressDenied):
            world.fetch("sub.example.com")
        with self.assertRaises(EgressDenied):
            world.fetch("169.254.169.254")
        self.assertEqual(world.egress_denials, 2)

    def test_rejects_url_and_authority_confusion(self):
        for target in ("https://example.com", "user@example.com", "example.com:443", " example.com",
                       "fe80::1%eth0", "exa%6dple.com", "a\\b"):
            with self.subTest(target=target), self.assertRaises(InvalidHost):
                canonical_host(target)

    def test_exactly_one_handler(self):
        world = HttpWorld("api")
        world.export_handler(lambda req: req["path"])
        self.assertEqual(world.handle({"path": "/"}), "/")
        with self.assertRaises(ValueError):
            world.export_handler(lambda req: req)
        with self.assertRaises(TypeError):
            HttpWorld("x").export_handler(None)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
