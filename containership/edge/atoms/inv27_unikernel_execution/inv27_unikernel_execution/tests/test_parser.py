"""MC-001 adversarial parser fixtures + MC-050 fuzzing harness.

Fuzz iterations: INV27_FUZZ_ITERS (default 1500).  Seeded and reproducible (INV27_FUZZ_SEED).  The
invariant: the parser either returns an ElfImage or raises UkError with a UK_PARSE_* code - never
any other exception, never exceeds its work budget, never hangs.
"""
import os
import random
import struct
import time
import unittest

from harness import UkError, elf, facts, image

GOOD = image("uk_good.elf")


def patch(data: bytes, off: int, fmt: str, *vals) -> bytes:
    b = bytearray(data)
    struct.pack_into(fmt, b, off, *vals)
    return bytes(b)


def ehdr(data):
    return struct.unpack_from("<HHIQQQIHHHHHH", data, 16)


class Adversarial(unittest.TestCase):
    def code(self, data, limits=elf.Limits()):
        with self.assertRaises(UkError) as c:
            elf.parse(data, limits)
        return c.exception.code

    def test_bad_magic_class_endianness_machine(self):
        self.assertEqual(self.code(b"MZ" + GOOD[2:]), "UK_PARSE_BAD_MAGIC")
        self.assertEqual(self.code(GOOD[:4] + b"\x01" + GOOD[5:]), "UK_PARSE_UNSUPPORTED_FORMAT")
        self.assertEqual(self.code(GOOD[:5] + b"\x02" + GOOD[6:]), "UK_PARSE_UNSUPPORTED_FORMAT")
        self.assertEqual(self.code(patch(GOOD, 18, "<H", 40)), "UK_PARSE_UNSUPPORTED_FORMAT")
        self.assertEqual(self.code(patch(GOOD, 16, "<H", 1)), "UK_PARSE_UNSUPPORTED_FORMAT")   # ET_REL

    def test_truncation_everywhere_is_classified(self):
        for n in (0, 3, 15, 40, 63, 100, 400, len(GOOD) // 2, len(GOOD) - 1):
            with self.subTest(n=n):
                self.assertTrue(self.code(GOOD[:n]).startswith("UK_PARSE_"))

    def test_phdr_count_bomb_and_shdr_count_bomb(self):
        self.assertEqual(self.code(patch(GOOD, 56, "<H", 0xFFFF)), "UK_PARSE_LIMIT")
        self.assertEqual(self.code(patch(GOOD, 60, "<H", 0xFFFF)), "UK_PARSE_LIMIT")

    def test_integer_overflow_offsets(self):
        t = ehdr(GOOD)
        self.assertEqual(self.code(patch(GOOD, 32, "<Q", 2**64 - 8)), "UK_PARSE_TRUNCATED")
        self.assertEqual(self.code(patch(GOOD, 40, "<Q", 2**63)), "UK_PARSE_TRUNCATED")

    def test_overlapping_load_segments(self):
        e = elf.parse(GOOD)
        phoff = ehdr(GOOD)[4]
        loads = [i for i, s in enumerate(e.segments) if s.type == elf.PT_LOAD]
        a, b = loads[0], loads[1]
        vaddr_b = e.segments[b].vaddr
        data = patch(GOOD, phoff + a * 56 + 40, "<Q", vaddr_b - e.segments[a].vaddr + 0x100)  # memsz of a into b
        data = patch(data, phoff + a * 56 + 32, "<Q", min(e.segments[a].filesz, vaddr_b - e.segments[a].vaddr + 0x100))
        self.assertEqual(self.code(data), "UK_PARSE_OVERLAP")

    def test_duplicate_section_names(self):
        e = elf.parse(GOOD)
        shoff, shnum = ehdr(GOOD)[5], ehdr(GOOD)[10]
        names = [s.name for s in e.sections]
        i, j = names.index(".text"), names.index(".rodata") if ".rodata" in names else names.index(".symtab")
        name_off = struct.unpack_from("<I", GOOD, shoff + i * 64)[0]
        data = patch(GOOD, shoff + j * 64, "<I", name_off)
        self.assertEqual(self.code(data), "UK_PARSE_OVERLAP")

    def test_corrupt_symbol_table_and_string_index(self):
        e = elf.parse(GOOD)
        sym = e.section(".symtab")
        data = patch(GOOD, sym.offset + 24, "<I", 0x7FFFFFFF)       # name offset outside strtab
        self.assertEqual(self.code(data), "UK_PARSE_MALFORMED")
        shoff = ehdr(GOOD)[5]
        idx = [s.name for s in e.sections].index(".symtab")
        data = patch(GOOD, shoff + idx * 64 + 56, "<Q", 23)         # entsize != 24
        self.assertEqual(self.code(data), "UK_PARSE_MALFORMED")

    def test_symbol_bomb_limit(self):
        self.assertEqual(self.code(GOOD, elf.Limits(max_symbols=3)), "UK_PARSE_LIMIT")

    def test_work_budget(self):
        self.assertEqual(self.code(GOOD, elf.Limits(work_budget=500)), "UK_PARSE_BUDGET")

    def test_size_budget(self):
        self.assertEqual(self.code(GOOD, elf.Limits(max_bytes=1024)), "UK_PARSE_TOO_LARGE")

    def test_path_is_never_accepted(self):
        with self.assertRaises(TypeError):
            elf.parse("tests/fixtures/uk_good.elf")

    def test_matches_readelf_ground_truth(self):
        e = elf.parse(GOOD)
        self.assertEqual(e.machine, "x86_64")
        self.assertEqual(e.e_type, elf.ET_EXEC)
        self.assertIsNone(e.interp)
        self.assertTrue(any(s.name == "ukplat_entry" and s.value == e.entry for s in e.symbols))
        dyn = elf.parse(image("dyn_fork_dlopen.elf"))
        self.assertEqual(dyn.interp, "/lib64/ld-linux-x86-64.so.2")
        self.assertIn("libc.so.6", dyn.needed)


class Fuzz(unittest.TestCase):
    def test_mutation_fuzz(self):
        iters = int(os.environ.get("INV27_FUZZ_ITERS", "1500"))
        rng = random.Random(int(os.environ.get("INV27_FUZZ_SEED", "27")))
        seeds = [image(n) for n in ("uk_good.elf", "solo5_good.elf", "dyn_fork_dlopen.elf", "uk_stripped.elf")]
        outcomes = {"ok": 0}
        worst = 0.0
        for _ in range(iters):
            b = bytearray(rng.choice(seeds))
            for _ in range(rng.randint(1, 8)):
                op = rng.random()
                if op < 0.6:
                    b[rng.randrange(len(b))] = rng.randrange(256)
                elif op < 0.8:
                    off = rng.randrange(0, 64) if rng.random() < 0.5 else rng.randrange(max(1, len(b) - 8))
                    struct.pack_into("<Q", b, min(off, len(b) - 8), rng.choice([0, 1, 2**32 - 1, 2**63, 2**64 - 1, rng.getrandbits(64)]))
                else:
                    del b[rng.randrange(len(b)):]
                    if len(b) < 16:
                        b += b"\0" * (16 - len(b))
            t = time.perf_counter()
            try:
                e = elf.parse(bytes(b))
                try:
                    facts.derive(e)
                except UkError as err:
                    self.assertTrue(err.code.startswith("UK_SEAL_") or err.code.startswith("UK_PROVENANCE"), err.code)
                outcomes["ok"] += 1
            except UkError as err:
                self.assertTrue(err.code.startswith("UK_PARSE_"), err.code)
                outcomes[err.code] = outcomes.get(err.code, 0) + 1
            worst = max(worst, time.perf_counter() - t)
        self.assertLess(worst, 2.0, "a single parse took too long")
        self.assertGreater(len(outcomes), 3)


if __name__ == "__main__":
    unittest.main()
