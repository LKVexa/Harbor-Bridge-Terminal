"""Direct domain tests for the deprecated v1 API (kept for backward compatibility, MC-039/MC-091)."""
import unittest

import harness  # noqa: F401
from inv28_unikernel_implementations.component import (
    REVIEW_INTERVAL,
    NoSuitableToolchain,
    Toolchain,
    ToolchainRegister,
)


def make_toolchain(name="unikraft", *, maturity="beta", security_contact=True, reviewed_at=0):
    return Toolchain(
        name,
        frozenset({"c", "rust"}),
        frozenset({"x86_64"}),
        maturity,
        security_contact,
        reviewed_at,
    )


class ToolchainDomainTest(unittest.TestCase):
    def test_normalizes_identifiers(self):
        item = Toolchain(" Unikraft ", frozenset({" C "}), frozenset({" X86_64 "}), " BETA ", True)
        self.assertEqual(item.name, "Unikraft")
        self.assertEqual(item.languages, frozenset({"c"}))
        self.assertEqual(item.architectures, frozenset({"x86_64"}))
        self.assertEqual(item.maturity, "beta")

    def test_duplicate_names_are_case_insensitive(self):
        reg = ToolchainRegister()
        reg.register(make_toolchain("Unikraft"))
        with self.assertRaises(ValueError):
            reg.register(make_toolchain("unikraft"))

    def test_registry_snapshot_is_immutable(self):
        reg = ToolchainRegister()
        reg.register(make_toolchain())
        self.assertIsInstance(reg.toolchains, tuple)

    def test_production_rejects_unsafe_candidate(self):
        reg = ToolchainRegister()
        reg.register(make_toolchain("nanos", maturity="experimental", security_contact=False))
        with self.assertRaises(NoSuitableToolchain):
            reg.select(language="C", architecture="X86_64", environment=" Production ", now=1)

    def test_production_rejects_stale_review(self):
        reg = ToolchainRegister()
        reg.register(make_toolchain("old", maturity="mature", reviewed_at=0))
        with self.assertRaises(NoSuitableToolchain):
            reg.select(language="c", architecture="x86_64", environment="production", now=REVIEW_INTERVAL + 1)

    def test_production_rejects_beta_per_mc094(self):
        reg = ToolchainRegister()
        reg.register(make_toolchain("unikraft", maturity="beta"))
        with self.assertRaises(NoSuitableToolchain):
            reg.select(language="c", architecture="x86_64", environment="production", now=1)
        self.assertEqual(reg.select(language="c", architecture="x86_64", environment="staging", now=1)["toolchain"],
                         "unikraft")

    def test_string_language_set_rejected(self):
        with self.assertRaises(TypeError):
            Toolchain("x", "ocaml", frozenset({"x86_64"}), "mature", True)

    def test_tie_break_is_registration_order_independent(self):
        for names in (("zeta", "alpha"), ("alpha", "zeta")):
            reg = ToolchainRegister()
            for name in names:
                reg.register(make_toolchain(name, maturity="mature"))
            selected = reg.select(language="c", architecture="x86_64", environment="dev")
            self.assertEqual(selected["toolchain"], "alpha")


if __name__ == "__main__":
    unittest.main()
