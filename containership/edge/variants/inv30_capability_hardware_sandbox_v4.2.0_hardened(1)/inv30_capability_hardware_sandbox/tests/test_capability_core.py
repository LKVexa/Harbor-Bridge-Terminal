"""Dependency-free security and edge-case tests for INV-30 capability semantics."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inv30_capability_hardware_sandbox import (  # noqa: E402
    Amplification,
    BoundsViolation,
    Capability,
    Invalidated,
    PermissionViolation,
)


class CapabilityCoreTest(unittest.TestCase):
    def setUp(self):
        self.root = Capability(0x1000, 0x1000, {"read", "write"})

    def test_exact_in_bounds_access(self):
        self.assertTrue(self.root.check(address=0x1000, size=1, operation="read")["permitted"])
        self.assertTrue(self.root.check(address=0x1FFF, size=1, operation="write")["permitted"])

    def test_rejects_zero_negative_and_cross_boundary_access(self):
        for address, size in [(0x1000, 0), (0x1000, -1), (0x0FFF, 1), (0x1FFF, 2), (0x2000, 1)]:
            with self.subTest(address=address, size=size), self.assertRaises(BoundsViolation):
                self.root.check(address=address, size=size, operation="read")

    def test_rejects_missing_permission(self):
        with self.assertRaises(PermissionViolation):
            self.root.check(address=0x1000, size=1, operation="execute")

    def test_derive_can_only_attenuate(self):
        child = self.root.derive(base=0x1400, length=0x100, permissions={"read"})
        self.assertEqual((child.base, child.limit, child.permissions), (0x1400, 0x1500, frozenset({"read"})))
        cases = [
            dict(base=0x0FFF, length=1),
            dict(base=0x1000, length=0x1001),
            dict(base=0x1000, length=-1),
            dict(base=0x1000, length=1, permissions={"execute"}),
        ]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs), self.assertRaises(Amplification):
                self.root.derive(**kwargs)

    def test_permissions_are_defensively_frozen(self):
        source = {"read"}
        cap = Capability(0, 4, source)
        source.add("write")
        self.assertEqual(cap.permissions, frozenset({"read"}))
        with self.assertRaises(Amplification):
            cap.permissions = frozenset({"read", "write"})

    def test_bounds_are_immutable(self):
        with self.assertRaises(Amplification):
            self.root.base = 0
        with self.assertRaises(Amplification):
            self.root.length = 0x10000

    def test_invalidation_is_permanent(self):
        self.root.invalidate()
        with self.assertRaises(Invalidated):
            self.root.check(address=0x1000, size=1, operation="read")
        with self.assertRaises(Invalidated):
            self.root.derive(base=0x1000, length=1)
        with self.assertRaises(Invalidated):
            self.root.valid = True
        self.assertFalse(self.root.valid)

    def test_malformed_types_are_rejected(self):
        bad_constructors = [
            (True, 1, {"read"}),
            (0, False, {"read"}),
            (0, 1, "read"),
            (0, 1, {1}),
        ]
        for args in bad_constructors:
            with self.subTest(args=args), self.assertRaises(TypeError):
                Capability(*args)
        with self.assertRaises(TypeError):
            self.root.check(address=True, size=1, operation="read")
        with self.assertRaises(TypeError):
            self.root.check(address=0x1000, size=True, operation="read")
        with self.assertRaises(TypeError):
            self.root.derive(base=0x1000, length=True)
        with self.assertRaises(TypeError):
            self.root.derive(base=0x1000, length=1, permissions="read")

    def test_unknown_permission_is_rejected(self):
        with self.assertRaises(ValueError):
            Capability(0, 1, {"admin"})

    def test_refusals_have_machine_readable_codes(self):
        try:
            self.root.check(address=0x2000, size=1, operation="read")
        except BoundsViolation as exc:
            self.assertEqual(exc.as_dict()["code"], "BOUNDS_VIOLATION")
        else:
            self.fail("expected BoundsViolation")


if __name__ == "__main__":
    unittest.main()
