# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Property-based / fuzz tests (GAP-031). Seeded stdlib RNG => reproducible; seed printed on failure.

Properties checked over tens of thousands of random cases:
P1 access succeeds  <=>  valid ∧ op∈perms ∧ size>0 ∧ base<=addr ∧ addr+size<=limit
P2 derive succeeds  =>   child ⊆ parent in bounds and permissions
P3 derive fails     <=>  it would widen (or parent invalid / depth limit)
P4 after invalidate, every access/derive raises Invalidated
P5 malformed inputs raise TypeError/ValueError/CapabilityError — never succeed, never other exceptions
P6 schema validator never raises anything but SchemaInvalid on arbitrary JSON-ish input
"""
import os
import random
import unittest

from ..core import Amplification, BoundsViolation, Capability, CapabilityError, Invalidated, PermissionViolation
from ..errors import SchemaInvalid
from .. import schema

SEED = int(os.environ.get("INV30_FUZZ_SEED", "20260923"))
N = int(os.environ.get("INV30_FUZZ_N", "20000"))
PERMS = ["read", "write", "execute"]


def rperms(rng):
    return {p for p in PERMS if rng.random() < 0.5}


class PropertyTest(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(SEED)

    def test_p1_access_oracle(self):
        rng = self.rng
        for i in range(N):
            base, length = rng.randrange(0, 1 << 20), rng.randrange(0, 1 << 12)
            perms = rperms(rng)
            cap = Capability(base, length, perms)
            addr = base + rng.randrange(-64, length + 64)
            size = rng.randrange(-2, 80)
            op = rng.choice(PERMS)
            expect = op in perms and size > 0 and addr >= base and addr + size <= base + length
            try:
                ok = cap.check(address=addr, size=size, operation=op)["permitted"]
            except (BoundsViolation, PermissionViolation):
                ok = False
            self.assertEqual(ok, expect, f"seed={SEED} case={i}")

    def test_p2_p3_derive_monotonic(self):
        rng = self.rng
        for i in range(N):
            parent = Capability(rng.randrange(0, 1 << 20), rng.randrange(0, 1 << 12), rperms(rng))
            b = parent.base + rng.randrange(-32, parent.length + 32)
            ln = rng.randrange(-4, parent.length + 32)
            p = rperms(rng)
            widens = ln < 0 or b < parent.base or b + ln > parent.limit or not p <= parent.permissions
            try:
                c = parent.derive(base=b, length=ln, permissions=p)
            except Amplification:
                self.assertTrue(widens, f"seed={SEED} case={i}: refused a narrowing")
                continue
            self.assertFalse(widens, f"seed={SEED} case={i}: allowed a widening")
            self.assertTrue(parent.base <= c.base and c.limit <= parent.limit and c.permissions <= parent.permissions)

    def test_chains_never_amplify(self):
        rng = self.rng
        for _ in range(N // 20):
            root = Capability(0, 1 << 16, set(PERMS))
            cur = root
            for _ in range(rng.randrange(1, 40)):
                b = cur.base + rng.randrange(0, max(1, cur.length))
                ln = rng.randrange(0, max(1, cur.limit - b + 1))
                try:
                    cur = cur.derive(base=b, length=ln, permissions={p for p in cur.permissions if rng.random() < .8})
                except Amplification:
                    break
                self.assertTrue(root.base <= cur.base <= cur.limit <= root.limit)

    def test_p4_invalidation_absorbing(self):
        rng = self.rng
        for _ in range(N // 10):
            cap = Capability(0, 1 << 12, set(PERMS))
            cap.invalidate()
            with self.assertRaises(Invalidated):
                cap.check(address=rng.randrange(0, 1 << 12), size=1, operation=rng.choice(PERMS))
            with self.assertRaises(Invalidated):
                cap.derive(base=0, length=1)

    def test_p5_malformed_constructor_inputs(self):
        rng = self.rng
        junk = [None, True, False, 1.5, -1, "1", b"1", [], {}, {"read"}, 2 ** 70, float("nan"), object()]
        for _ in range(N // 10):
            args = [rng.choice(junk + [0, 16]), rng.choice(junk + [0, 16]),
                    rng.choice(junk + [{"read"}, ["write"], frozenset()])]
            try:
                Capability(*args)
            except (TypeError, ValueError, CapabilityError):
                continue
            self.assertTrue(type(args[0]) is int and type(args[1]) is int and args[0] >= 0 and args[1] >= 0)

    def test_p6_schema_fuzz(self):
        rng = self.rng
        atoms = [None, True, 0, -1, 2 ** 64, 1.0, "", "x" * 600, "cap_" + "0" * 32, "read", [], {}]

        def val(d=0):
            r = rng.random()
            if d > 3 or r < .5:
                return rng.choice(atoms)
            if r < .75:
                return [val(d + 1) for _ in range(rng.randrange(0, 4))]
            keys = ["schema", "handle", "address", "size", "operation", "op", "base", "length", "permissions",
                    "tenant", "zzz"]
            return {rng.choice(keys): val(d + 1) for _ in range(rng.randrange(0, 7))}
        for _ in range(N // 4):
            for name in ("access", "capability", "failure", "config"):
                try:
                    schema.validate(name, val())
                except SchemaInvalid:
                    pass


if __name__ == "__main__":
    unittest.main()
