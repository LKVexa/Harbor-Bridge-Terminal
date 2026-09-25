"""Mutation fuzzing of the untrusted-input parsers (C085, C050).

Invariants, for every mutated input:

1. ``wasm.parse`` / ``sfi.verify`` / ``config.load_json_strict`` / descriptor opening
   raise nothing but ``SfiError`` (no crash, no raw exception escapes);
2. each input finishes within a bounded time (no hang);
3. **differential**: any input our verifier ACCEPTS is also valid to V8
   (``WebAssembly.validate``) - a parser differential in the permissive direction
   is the dangerous one;
4. regression corpus in ``tests/fuzz/corpus/`` always stays green.

Smoke budget in CI: ``INV45_FUZZ_SECONDS`` (default 3 s per target).  Scheduled campaigns
run ``tools/fuzz_campaign.py`` for hours; crashers are minimised into the corpus.
"""
from __future__ import annotations

import json
import os
import random
import time
import unittest
from pathlib import Path

from inv45_sfi_mechanisms.tests.support import Harness, node_available
from inv45_sfi_mechanisms.production import builder, config, engine, sfi, trust, wasm
from inv45_sfi_mechanisms.production.errors import SfiError

BUDGET = float(os.environ.get("INV45_FUZZ_SECONDS", "3"))
SEED = int(os.environ.get("INV45_FUZZ_SEED", "4545"))
CORPUS = Path(__file__).with_name("corpus")
P = sfi.Profile(65536, 16)
PER_INPUT_S = 2.0


def seeds() -> list[bytes]:
    out = [builder.rw_module(), sfi.rewrite(builder.rw_module(), P).artifact]
    fx = Path(__file__).resolve().parents[2] / "fixtures"
    out += [p.read_bytes() for p in sorted((fx / "wasm").glob("*.wasm"))]
    out += [p.read_bytes() for p in sorted(CORPUS.glob("*.wasm"))]
    return out


def mutate(rng: random.Random, data: bytes) -> bytes:
    b = bytearray(data)
    for _ in range(rng.randint(1, 4)):
        k = rng.randrange(7)
        if not b:
            b = bytearray(rng.randbytes(rng.randint(1, 16)))
        i = rng.randrange(len(b))
        if k == 0:
            b[i] ^= 1 << rng.randrange(8)
        elif k == 1:
            b[i] = rng.choice([0x00, 0x7F, 0x80, 0xFF, 0x41, 0x0B, 0x28, 0x36, 0x71, 0x6A, 0xFC, 0xFD])
        elif k == 2:
            del b[i:i + rng.randint(1, 8)]
        elif k == 3:
            b[i:i] = rng.randbytes(rng.randint(1, 8))
        elif k == 4:
            j = rng.randrange(len(b))
            b[i:i] = b[j:j + rng.randint(1, 32)]
        elif k == 5:
            b[i:i] = wasm.uleb(rng.choice([0, 1, 127, 128, 2**32 - 1, 2**31]))
        else:
            b = b[:i]
    return bytes(b)


class ParserFuzz(unittest.TestCase):
    def test_wasm_parse_and_verify_never_crash_and_accepts_are_engine_valid(self):
        rng = random.Random(SEED)
        pool = seeds()
        accepted: list[bytes] = []
        n = 0
        end = time.monotonic() + BUDGET
        while time.monotonic() < end:
            data = mutate(rng, rng.choice(pool))
            t0 = time.monotonic()
            try:
                sfi.verify(data, P, wasm.Limits(deadline_seconds=PER_INPUT_S))
                accepted.append(data)
            except SfiError:
                pass
            except Exception as exc:  # invariant 1
                (CORPUS / f"crash-{SEED}-{n}.wasm").write_bytes(data)
                self.fail(f"non-SfiError escaped: {type(exc).__name__}: {exc}")
            self.assertLess(time.monotonic() - t0, PER_INPUT_S + 0.5)  # invariant 2
            n += 1
        self.assertGreater(n, 50)
        if accepted and node_available():  # invariant 3
            verdicts = engine.validate_with_engine(accepted[:500])
            bad = [i for i, ok in enumerate(verdicts) if not ok]
            for i in bad:
                (CORPUS / f"differential-{SEED}-{i}.wasm").write_bytes(accepted[i])
            self.assertEqual(bad, [], "verifier accepted modules V8 rejects (parser differential)")

    def test_regression_corpus(self):
        for p in sorted(CORPUS.glob("*.wasm")):
            with self.subTest(p.name):
                try:
                    sfi.verify(p.read_bytes(), P)
                except SfiError:
                    pass


class ConfigAndDescriptorFuzz(unittest.TestCase):
    def test_config_json_fuzz(self):
        rng = random.Random(SEED + 1)
        base = json.dumps(config.DEFAULTS)
        end = time.monotonic() + BUDGET / 2
        while time.monotonic() < end:
            s = bytearray(base.encode())
            for _ in range(rng.randint(1, 5)):
                i = rng.randrange(len(s))
                s[i:i + 1] = rng.choice([b"", b"{", b"}", b'"', b"1e999", b"NaN", b"-", b"0", b",", b"true"])
            try:
                config.validate(config.load_json_strict(s.decode("utf-8", "replace")))
            except SfiError:
                pass

    def test_descriptor_fuzz(self):
        h = Harness()
        try:
            r = h.submit()
            rng = random.Random(SEED + 2)
            keys = list(r["descriptor"])
            end = time.monotonic() + BUDGET / 2
            while time.monotonic() < end:
                d = dict(r["descriptor"])
                k = rng.choice(keys)
                d[k] = rng.choice([None, 0, -1, 1e308, "", "x" * 5000, [], {}, True, d[k]])
                try:
                    trust.open_descriptor(h.keyring, d)
                except SfiError:
                    pass
                except Exception as exc:
                    self.fail(f"descriptor fuzz escaped {type(exc).__name__} on field {k}")
            art = builder.rw_module()
            good = h.sign(art)
            for _ in range(400):
                env = {k: dict(v) if isinstance(v, dict) else v for k, v in good.items()}
                target = env if rng.random() < 0.5 else env["statement"]
                k = rng.choice(list(target))
                target[k] = rng.choice([None, 0, [], {}, "x", 1e308, True])
                try:
                    h.trust_store.verify_statement(art, env)
                except SfiError:
                    pass
                except Exception as exc:
                    self.fail(f"statement fuzz escaped {type(exc).__name__} on field {k}")
        finally:
            h.close()


if __name__ == "__main__":
    unittest.main()
