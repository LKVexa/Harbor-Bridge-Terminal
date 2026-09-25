"""Property-based tests (MC033).  Stdlib only: seeded random generation, so
failures reproduce exactly (INV29_PROP_SEED / INV29_PROP_CASES override)."""
import os
import random
import unittest

import _fixtures as F
from inv29_hybrid_wasm_unikernel import admission as adm
from inv29_hybrid_wasm_unikernel.model import (HostImage, ImportUnsatisfied, LayerMissing, WasmModule,
                                               compose, verify)

SEED = int(os.environ.get("INV29_PROP_SEED", "20260923"))
CASES = int(os.environ.get("INV29_PROP_CASES", "400"))
CAPS = [f"cap-{i}" for i in range(24)]
ARCH_H = ["x86_64", "aarch64", "riscv64", "mips"]
ARCH_W = ["wasm32", "wasm64", "x86_64"]


def gen(r):
    exposes = frozenset(r.sample(CAPS, r.randint(0, 12)))
    imports = frozenset(r.sample(CAPS, r.randint(0, 8)))
    return (WasmModule("m", imports, hardened=r.random() < 0.8, architecture=r.choice(ARCH_W)),
            HostImage("h", exposes, sealed=r.random() < 0.8, architecture=r.choice(ARCH_H)),
            r.choice([2, 2, 2, 3]))


class PropertyTest(unittest.TestCase):
    def test_admit_iff_all_invariants_hold(self):
        r = random.Random(SEED)
        for i in range(CASES):
            m, h, req = gen(r)
            v = verify(m, h)
            expect_ok = (h.sealed and h.architecture in ("x86_64", "aarch64") and m.hardened
                         and m.architecture in ("wasm32", "wasm64") and m.imports <= h.exposes and req == 2)
            try:
                rec = compose(m, h, required_layers=req)
            except (LayerMissing, ImportUnsatisfied):
                self.assertFalse(expect_ok, f"case {i}: valid composition refused")
                continue
            self.assertTrue(expect_ok, f"case {i}: invalid composition admitted")
            # properties of every admitted record
            self.assertEqual(rec["layer_count"], 2)
            self.assertTrue(rec["defence_in_depth"])
            self.assertTrue(set(rec["imports"]) <= h.exposes)
            self.assertTrue(v["verified"])
            self.assertEqual(v["import_closure"]["unsatisfied"], ())

    def test_verify_is_pure_and_deterministic(self):
        r = random.Random(SEED + 1)
        for _ in range(CASES // 4):
            m, h, _ = gen(r)
            self.assertEqual(verify(m, h), verify(m, h))

    def test_monotonic_exposure(self):
        """Exposing more capabilities can never turn an admitted import set into a refusal."""
        r = random.Random(SEED + 2)
        for _ in range(CASES // 4):
            m, h, _ = gen(r)
            m = WasmModule("m", m.imports)
            h = HostImage("h", h.exposes | m.imports)
            compose(m, h)
            compose(m, HostImage("h", h.exposes | frozenset(r.sample(CAPS, 3))))

    def test_admission_signatures_bind_every_field(self):
        kr = F.keyring()
        a = F.admitter(kr)
        rec = a.admit(F.request(kr))
        r = random.Random(SEED + 3)
        for key in ("module", "host", "imports", "layer_count", "admission"):
            mutated = dict(rec)
            mutated[key] = {"module": "x", "host": "y", "imports": ["clock"],
                            "layer_count": 3, "admission": dict(rec["admission"], tenant="evil")}[key]
            with self.subTest(key=key), self.assertRaises((adm.AttestationInvalid, ValueError)):
                adm.verify_record(kr, mutated, expected_key_id=F.SIGN_KEY, now=F.NOW)


if __name__ == "__main__":
    unittest.main()
