import unittest
from inv65_capability_providers.errors.mapping import CATALOG, ProviderFault, from_envelope, http_status, to_envelope
from inv65_capability_providers.provider import InvalidLink, NoLink, ProviderUnavailable
from inv65_capability_providers.schemas import SchemaError


class ErrorCompat(unittest.TestCase):
    def test_every_code_round_trips(self):
        for code, spec in CATALOG.items():
            env = to_envelope(ProviderFault(code, "m", retry_after_ms=5), "ab" * 8)
            self.assertEqual(env["retryable"], spec.retryable)
            self.assertEqual(from_envelope(env).code, code)
            self.assertGreaterEqual(http_status(code), 400)

    def test_legacy_42_exceptions_map_to_same_codes(self):
        for exc, code in ((NoLink("x"), "PK_PROVIDER_NO_LINK"), (InvalidLink("x"), "PK_PROVIDER_INVALID_LINK"),
                          (ProviderUnavailable("x"), "PK_PROVIDER_UNAVAILABLE")):
            self.assertEqual(to_envelope(exc)["code"], code)

    def test_unknown_internal_errors_do_not_leak_messages(self):
        env = to_envelope(RuntimeError("password=hunter2 at /etc/x"))
        self.assertEqual(env["code"], "PK_PROVIDER_ERROR"); self.assertNotIn("hunter2", env["message"])

    def test_newer_peer_unknown_code_degrades(self):
        env = {"schema": "PK_PROVIDER_ERROR/1", "code": "PK_PROVIDER_FUTURE_THING", "message": "x", "retryable": True, "correlation_id": "ab" * 8}
        self.assertEqual(from_envelope(env).code, "PK_PROVIDER_ERROR")

    def test_malformed_envelope_rejected(self):
        with self.assertRaises(SchemaError):
            from_envelope({"code": "PK_PROVIDER_NO_LINK"})

    def test_uncatalogued_code_cannot_be_raised(self):
        with self.assertRaises(ValueError):
            ProviderFault("PK_PROVIDER_MADE_UP", "x")
