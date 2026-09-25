"""INV-35-C085 / REPO-008: seeded property-based fuzzing of every untrusted input.

Deterministic by default (seeded); set INV35_FUZZ_ITERS / INV35_FUZZ_SEED to
run longer campaigns.  Seed corpus: fixtures/**.  Mutation strategy: structural
(links, indices, duplicates, types) and numeric (boundary values around the
registered regions, 2^63/2^64, negatives, bools, floats).
"""
from __future__ import annotations

import copy
import json
import os
import random
import unittest

from _support import PKG_DIR, Descriptor, Inv35Error, MemoryRegion, VirtQueue, errors, one, stack, wire, pkg

ITERS = int(os.environ.get("INV35_FUZZ_ITERS", "3000"))
SEED = int(os.environ.get("INV35_FUZZ_SEED", "35042"))
REGIONS = (MemoryRegion(0x1000, 0x1000), MemoryRegion(0x2000, 0x800), MemoryRegion(0x4000, 0x1000))
BOUNDARY = [0, 1, 0xFFF, 0x1000, 0x1FFF, 0x2000, 0x27FF, 0x2800, 0x3FFF, 0x4000, 0x4FFF, 0x5000,
            2**31, 2**32, 2**63 - 1, 2**63, 2**64, -1, True, False, 1.5, "0x1000", None]


def in_memory(addr, length):
    if length == 0:
        return any(r.base <= addr <= r.limit for r in REGIONS)
    covered = set()
    for r in REGIONS:
        lo, hi = max(addr, r.base), min(addr + length, r.limit)
        if lo < hi:
            covered.add((lo, hi))
    cursor = addr
    for lo, hi in sorted(covered):
        if lo > cursor:
            return False
        cursor = max(cursor, hi)
    return cursor >= addr + length


def value(rng):
    return rng.choice(BOUNDARY) if rng.random() < 0.4 else rng.randrange(0, 0x6000)


class RingFuzzTest(unittest.TestCase):
    def test_random_rings_accept_only_safe_chains(self):
        rng = random.Random(SEED)
        accepted = refused = 0
        for _ in range(ITERS):
            q = VirtQueue("fz", REGIONS)
            n = rng.randint(1, pkg.MAX_CHAIN + 3)
            ring = {}
            for i in range(n):
                slot = i if rng.random() > 0.05 else value(rng)
                nxt = (i + 1 if i + 1 < n else None) if rng.random() > 0.15 else rng.choice([None, 0, i, n + 5, -1, "1"])
                d = Descriptor(slot if rng.random() > 0.05 else value(rng), value(rng), rng.choice([0, 1, 16, 256, 4096]) if rng.random() > 0.2 else value(rng), nxt)
                try:
                    ring[slot] = d
                except TypeError:
                    pass
            head = 0 if rng.random() > 0.1 else value(rng)
            before = (q.in_flight, q.pending, q.in_flight_descriptors)
            try:
                res = q.submit(ring, head)
            except (pkg.DescriptorInvalid, pkg.QueueFull) as exc:
                refused += 1
                self.assertEqual((q.in_flight, q.pending, q.in_flight_descriptors), before)
                self.assertTrue(errors.classify_model_error(exc).startswith("INV35-E"))
                continue
            accepted += 1
            # Property: every walked descriptor is an int-typed, in-bounds, non-looping link.
            self.assertEqual(len(set(res["descriptors"])), len(res["descriptors"]))
            self.assertLessEqual(len(res["descriptors"]), pkg.MAX_CHAIN)
            total = 0
            for idx in res["descriptors"]:
                d = ring[idx]
                self.assertTrue(isinstance(d.address, int) and not isinstance(d.address, bool))
                self.assertTrue(in_memory(d.address, d.length), (hex(d.address), d.length))
                total += d.length
            self.assertEqual(total, res["bytes"])
        self.assertGreater(accepted, 0)
        self.assertGreater(refused, 0)


class WireFuzzTest(unittest.TestCase):
    def test_mutated_fixtures_never_crash_and_never_mutate_on_refusal(self):
        rng = random.Random(SEED + 1)
        corpus = [json.loads(p.read_text())["request"] for p in sorted((PKG_DIR / "fixtures").rglob("*.json"))]
        r, cp, dp, ctl, bulk = stack()
        for _ in range(ITERS):
            doc = copy.deepcopy(rng.choice(corpus))
            for _m in range(rng.randint(1, 4)):
                self._mutate(doc, rng)
            q = r.queues["q0"].vq
            before = q.in_flight_descriptors
            try:
                req = wire.decode_submit(doc)
                dp.submit(bulk, tenant="t1", queue="q0", chain=req["chain"], head=req["head"])
                dp.complete(bulk, tenant="t1", queue="q0", guest_wants_notification=True)
            except Inv35Error as exc:
                self.assertIn(exc.code, errors.REGISTRY)
                self.assertEqual(q.in_flight_descriptors, before)
            except Exception as exc:  # any uncoded exception is a finding
                self.fail(f"uncoded {type(exc).__name__}: {exc} for {doc!r}")

    @staticmethod
    def _mutate(doc, rng):
        choice = rng.randrange(7)
        descs = doc.get("descriptors")
        if choice == 0 and isinstance(descs, list) and descs:
            d = rng.choice(descs)
            if isinstance(d, dict):
                d[rng.choice(["index", "address", "length", "next_index", "flags"])] = rng.choice(BOUNDARY)
        elif choice == 1:
            doc["head"] = rng.choice(BOUNDARY)
        elif choice == 2 and isinstance(descs, list) and descs:
            descs.append(copy.deepcopy(rng.choice(descs)))
        elif choice == 3:
            doc[rng.choice(["descriptors", "queue", "tenant"])] = rng.choice([None, [], {}, "", 7, [None]])
        elif choice == 4 and isinstance(descs, list):
            rng.shuffle(descs)
        elif choice == 5:
            doc.pop(rng.choice(["head", "descriptors", "queue"]), None)
        else:
            doc["extra"] = "x"


class TokenFuzzTest(unittest.TestCase):
    @staticmethod
    def _decoded(tok):
        import base64
        parts = tok.split(".")
        dec = lambda t: base64.urlsafe_b64decode(t + "=" * (-len(t) % 4))  # noqa: E731
        return dec(parts[0]), parts[1], dec(parts[2])

    def test_bit_flipped_tokens_are_always_refused(self):
        rng = random.Random(SEED + 2)
        r, cp, dp, ctl, bulk = stack()
        for _ in range(ITERS // 3):
            chars = list(bulk)
            for _f in range(rng.randint(1, 3)):
                i = rng.randrange(len(chars))
                chars[i] = rng.choice("ABCDEFabcdef0123456789-_.=")
            tok = "".join(chars)
            if tok == bulk:
                continue
            try:
                dp.submit(tok, tenant="t1", queue="q0", chain=one(), head=0)
                dp.complete(bulk, tenant="t1", queue="q0", guest_wants_notification=True)
                # Only a flip in unused base64 tail bits (decoding to identical bytes) may pass.
                self.assertEqual(self._decoded(tok), self._decoded(bulk), tok)
            except Inv35Error as exc:
                self.assertIn(exc.code, {"INV35-E300", "INV35-E301", "INV35-E303", "INV35-E305", "INV35-E302"})


if __name__ == "__main__":
    unittest.main()
