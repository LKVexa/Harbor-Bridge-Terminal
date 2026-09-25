"""Production rewriter + independent verifier (C031, C046, A3)."""
from __future__ import annotations

import random
import unittest

from inv45_sfi_mechanisms.tests import support  # noqa: F401
from inv45_sfi_mechanisms.production import builder, sfi, wasm
from inv45_sfi_mechanisms.production.builder import F32, F64, I32, I64, Func, ModuleBuilder
from inv45_sfi_mechanisms.production.errors import SfiError
from inv45_sfi_mechanisms.sfi_core import SandboxRegion

P = sfi.Profile(region_base=65536, region_log2=16)


def code(fn, *a, **k):
    try:
        fn(*a, **k)
    except SfiError as e:
        return e.code
    return "OK"


class RewriteVerifyTest(unittest.TestCase):
    def test_rewrite_then_verify(self):
        r = sfi.rewrite(builder.rw_module(), P)
        proof = sfi.verify(r.artifact, P)
        self.assertEqual(proof["result"], "VERIFIED")
        self.assertEqual(proof["memory_accesses"], {"loads": 4, "stores": 4, "confined": 8})
        self.assertEqual(r.rewritten_accesses, 8)
        self.assertEqual(proof["artifact_sha256"], r.output_sha256)

    def test_unrewritten_rejected_with_offsets(self):
        try:
            sfi.verify(builder.rw_module(), P)
        except SfiError as e:
            self.assertEqual(e.code, "SFI_UNMASKED_ACCESS")
            self.assertEqual(e.details["unmasked_count"], 8)
            self.assertEqual(len(e.details["sample_offsets"]), 5)
        else:
            self.fail("unmasked module verified")

    def test_every_memory_opcode_rewritten_and_verified(self):
        b = ModuleBuilder(memory=(4, None))
        vals = {I32: (0x41, 1), I64: (0x42, 1), F32: (0x43, b"\0" * 4), F64: (0x44, b"\0" * 8)}
        for op, (vt, width, is_store) in wasm.MEMORY_OPS.items():
            align = {1: 0, 2: 1, 4: 2, 8: 3}[width]
            if is_store:
                body = [(0x20, 0), vals[vt], (op, (align, 12)), (0x0B, None)]
                b.add(Func((I32,), (), body))
            else:
                b.add(Func((I32,), (vt,), [(0x20, 0), (op, (align, 3)), (0x0B, None)]))
        r = sfi.rewrite(b.build(), P)
        proof = sfi.verify(r.artifact, P)
        self.assertEqual(proof["memory_accesses"]["confined"], len(wasm.MEMORY_OPS))

    def test_verifier_independent_of_rewriter(self):
        """Tamper each field of the canonical sequence in a rewritten module: all refused."""
        good = sfi.rewrite(builder.rw_module(), P).artifact
        mask = wasm.sleb(P.mask)
        base = wasm.sleb(P.region_base)
        seq = b"\x41" + mask + b"\x71\x41" + base + b"\x6a"
        self.assertIn(seq, good)
        for bad in (b"\x41" + wasm.sleb(P.mask * 2 + 1) + b"\x71\x41" + base + b"\x6a",   # wider mask
                    b"\x41" + mask + b"\x72\x41" + base + b"\x6a",                         # i32.or
                    b"\x41" + mask + b"\x71\x41" + wasm.sleb(0) + b"\x6a",                 # base 0
                    b"\x41" + mask + b"\x71\x41" + base + b"\x6b"):                        # i32.sub
            with self.subTest(bad=bad.hex()):
                tampered = good.replace(seq, bad, 1)
                self.assertNotEqual(tampered, good)
                c = code(sfi.verify, tampered, P)
                self.assertIn(c, ("SFI_UNMASKED_ACCESS", "SFI_MALFORMED_ARTIFACT", "SFI_INVALID_MODULE"))

    def test_double_rewrite_still_verifies(self):
        once = sfi.rewrite(builder.rw_module(), P).artifact
        twice = sfi.rewrite(once, P).artifact
        sfi.verify(twice, P)

    def test_proof_is_deterministic(self):
        a = sfi.rewrite(builder.rw_module(), P).artifact
        self.assertEqual(sfi.proof_digest(sfi.verify(a, P)), sfi.proof_digest(sfi.verify(a, P)))

    def test_custom_sections_other_than_name_stripped(self):
        b = ModuleBuilder(memory=(4, None), customs=[("name", b"\x00"), (".debug_info", b"xx"), ("sourceMappingURL", b"")])
        b.add(Func((), (), [(0x0B, None)]))
        r = sfi.rewrite(b.build(), P)
        self.assertEqual(sorted(r.stripped_custom_sections), [".debug_info", "sourceMappingURL"])
        self.assertEqual([n for n, _ in wasm.parse(r.artifact).customs], ["name"])

    def test_formula_matches_reference_model(self):
        proof = sfi.verify(sfi.rewrite(builder.rw_module(), P).artifact, P)
        rng = random.Random(45)
        samples = [rng.randrange(0, 1 << 32) for _ in range(2000)] + [0, P.mask, P.size, (1 << 32) - 1]
        ref = SandboxRegion(P.region_base, P.size)
        for addr, confined in sfi.reference_crosscheck(proof, samples):
            self.assertEqual(confined, ((addr & P.mask) + P.region_base))
            self.assertTrue(ref.contains(confined))


class ConstantFoldTest(unittest.TestCase):
    """C066 optimisation must never weaken confinement."""

    def test_constant_addresses_folded_and_verified(self):
        b = ModuleBuilder(memory=(4, None))
        b.add(Func((), (I32,), [(0x41, -5), (0x28, (2, 0xFFFFFF)), (0x0B, None)]))
        b.add(Func((), (), [(0x41, 0x7FFFFFFF), (0x42, 9), (0x37, (3, 17)), (0x0B, None)]))
        b.add(Func((I64,), (), [(0x41, 3), (0x20, 0), (0x37, (3, 0)), (0x0B, None)]))
        r = sfi.rewrite(b.build(), P)
        self.assertEqual(r.constant_folded_accesses, 3)
        sfi.verify(r.artifact, P)
        for fn in wasm.parse(r.artifact).functions:
            for i, ins in enumerate(fn.body):
                if ins.op in wasm.MEMORY_OPS:
                    k = i - (2 if wasm.MEMORY_OPS[ins.op][2] else 1)
                    e = fn.body[k].imm & 0xFFFFFFFF
                    self.assertTrue(P.region_base <= e <= P.region_base + P.mask)

    def test_constant_outside_partition_rejected(self):
        for e in (0, P.region_base - 1, P.region_base + P.size, 0xFFFFFFFF):
            b = ModuleBuilder(memory=(4, None))
            b.add(Func((), (I32,), [(0x41, e - (1 << 32) if e >= 1 << 31 else e), (0x28, (2, 0)), (0x0B, None)]))
            self.assertEqual(code(sfi.verify, b.build(), P), "SFI_UNMASKED_ACCESS", e)

    def test_store_value_push_must_match_type(self):
        b = ModuleBuilder(memory=(4, None))
        b.add(Func((), (), [(0x41, P.region_base), (0x42, 1), (0x36, (2, 0)), (0x0B, None)]))
        self.assertIn(code(sfi.verify, b.build(), P), ("SFI_INVALID_MODULE", "SFI_UNMASKED_ACCESS"))


class ProfileAndPolicyTest(unittest.TestCase):
    def test_profile_validation(self):
        for kw in ({"region_base": 65536, "region_log2": 11}, {"region_base": 65536, "region_log2": 32},
                   {"region_base": 3, "region_log2": 16}, {"region_base": (1 << 32) - 8, "region_log2": 12},
                   {"region_base": True, "region_log2": 16}, {"region_base": 0, "region_log2": 16, "profile_id": "X"}):
            with self.subTest(kw=kw):
                self.assertIn(code(sfi.Profile, **kw), ("SFI_CONFIG_INVALID", "SFI_UNSUPPORTED_VERSION"))

    def test_profile_digest_binds_every_field(self):
        base = sfi.Profile(65536, 16)
        for other in (sfi.Profile(65536 * 2, 16), sfi.Profile(65536, 17), sfi.Profile(65536, 16, ("a.b",)),
                      sfi.Profile(65536, 16, allow_memory_grow=True), sfi.Profile(65536, 16, allow_memory_export=True),
                      sfi.Profile(65536, 16, require_imported_memory=True)):
            self.assertNotEqual(base.digest(), other.digest())

    def test_policy_rejections(self):
        def mod(**kw):
            b = ModuleBuilder(**kw)
            b.add(Func((), (), [(0x0B, None)]))
            return b.build()
        cases = {
            "import": mod(memory=(4, None), func_imports=[("env", "evil", (), ())]),
            "memory export": mod(memory=(4, None), export_memory="mem"),
            "too small": mod(memory=(1, None)),
            "data outside": mod(memory=(4, None), data=[(65536 * 2, b"x")]),
            "data straddles": mod(memory=(4, None), data=[(65536 * 2 - 2, b"xyz")]),
            "growable table": mod(memory=None, table=(1, None), elements=[(0, [0])]),
            "table max>min": mod(memory=None, table=(1, 2), elements=[(0, [0])]),
        }
        for name, blob in cases.items():
            with self.subTest(name):
                self.assertEqual(code(sfi.verify, blob, P), "SFI_POLICY_REJECTED")
        # imported memory required by profile
        self.assertEqual(code(sfi.verify, mod(memory=(4, None)), sfi.Profile(65536, 16, require_imported_memory=True)),
                         "SFI_POLICY_REJECTED")
        # allowlisted import passes
        sfi.verify(mod(memory=(4, None), func_imports=[("env", "trace_i32", (I32,), ())]),
                   sfi.Profile(65536, 16, ("env.trace_i32",)))

    def test_mutable_global_import_and_table_import_rejected(self):
        hdr = b"\x00asm\x01\x00\x00\x00"
        mut_global = hdr + b"\x02\x0a\x01\x03env\x01g\x03\x7f\x01"
        table_imp = hdr + b"\x02\x0b\x01\x03env\x01t\x01\x70\x00\x01"
        self.assertEqual(code(sfi.verify, mut_global, P), "SFI_POLICY_REJECTED")
        self.assertEqual(code(sfi.verify, table_imp, P), "SFI_POLICY_REJECTED")

    def test_memory_grow_policy(self):
        b = ModuleBuilder(memory=(4, None))
        b.add(Func((I32,), (I32,), [(0x20, 0), (0x40, None), (0x0B, None)]))
        self.assertEqual(code(sfi.verify, b.build(), P), "SFI_POLICY_REJECTED")
        sfi.verify(b.build(), sfi.Profile(65536, 16, allow_memory_grow=True))

    def test_permitted_indirect_targets(self):
        b = ModuleBuilder(memory=None, table=(3, 3), elements=[(0, [0, 2]), (2, [1])])
        for v in (1, 2, 3):
            b.add(Func((), (I32,), [(0x41, v), (0x0B, None)]))
        proof = sfi.verify(b.build(), P)
        self.assertEqual(proof["permitted_indirect_targets"], [0, 1, 2])


if __name__ == "__main__":
    unittest.main()
