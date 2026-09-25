"""Deterministic, stdlib-only fuzzing of every untrusted parser (C085).
Invariant: arbitrary input produces either success or a BulkDataPlaneError with
a registered code - never an unclassified exception.  Seeds are fixed so
results are reproducible; set INV37_FUZZ_ITERS to extend in CI."""
from __future__ import annotations

import json
import os
import random
import unittest

from _support import C, Env, S, pkg

ITERS = int(os.environ.get("INV37_FUZZ_ITERS", "1500"))


def rand_json(rng, depth=0):
    r = rng.random()
    if depth > 3 or r < 0.3:
        return rng.choice([None, True, False, -1, 0, 1, 2 ** 70, 1.5, float("inf"), "", "x" * rng.randint(0, 80),
                           "a" * 64, "0" * 64, "ü", [], {}])
    if r < 0.6:
        return [rand_json(rng, depth + 1) for _ in range(rng.randint(0, 5))]
    keys = ["schema", "chunk", "size", "chunks", "object", "chunk_count", "algorithm", "limits", "security", "x"]
    return {rng.choice(keys): rand_json(rng, depth + 1) for _ in range(rng.randint(0, 6))}


def mutate(rng, obj):
    o = json.loads(json.dumps(obj))
    for _ in range(rng.randint(1, 3)):
        k = rng.choice(list(o))
        o[k] = rand_json(rng)
    return o


class FuzzTest(unittest.TestCase):
    def assert_classified(self, fn, *a, **k):
        try:
            fn(*a, **k)
        except pkg.BulkDataPlaneError as exc:
            self.assertIn(exc.code, pkg.ERROR_CODES, exc.code)
        except (TypeError, ValueError) as exc:  # documented argument-type contract errors
            self.assertNotIsInstance(exc, (KeyError, AttributeError, IndexError))

    def test_manifest(self):
        rng = random.Random(1)
        good = pkg.manifest(os.urandom(9000), 4096)
        for _ in range(ITERS):
            cand = mutate(rng, good) if rng.random() < 0.7 else rand_json(rng)
            try:
                pkg.validate_manifest(cand)
            except pkg.InvalidManifest:
                pass

    def test_chunk_accept(self):
        rng = random.Random(2)
        data = os.urandom(9000)
        m = pkg.manifest(data, 4096)
        r = pkg.Receiver(m)
        for _ in range(ITERS):
            idx = rng.choice([rng.randint(-3, 5), "1", None, 1.0, True])
            payload = rng.choice([os.urandom(rng.randint(0, 5000)), data[:4096], b"", bytearray(4096)])
            self.assert_classified(r.accept, idx, payload)

    def test_tokens(self):
        rng = random.Random(3)
        env = Env()
        try:
            an = S.Authenticator(env.ring)
            good = env.token()
            for _ in range(ITERS):
                t = list(good)
                for _ in range(rng.randint(1, 4)):
                    i = rng.randrange(len(t))
                    t[i] = rng.choice("abcXYZ019.-_=")
                cand = "".join(t) if rng.random() < 0.8 else rand_json(rng)
                try:
                    an.verify(cand)
                except pkg.SecurityRejected as exc:
                    self.assertIn(exc.code, ("authentication_failed", "replay_detected"))
        finally:
            env.close()

    def test_config_layers(self):
        rng = random.Random(4)
        for _ in range(ITERS):
            cand = rand_json(rng)
            try:
                C.merge(("f", C.load_layer(cand, layer="f")))
            except pkg.ConfigError:
                pass

    def test_resume_tokens(self):
        rng = random.Random(5)
        env = Env()
        try:
            dp = env.plane()
            tok = env.token()
            m = pkg.manifest(os.urandom(9000), 4096)
            dp.create_transfer(tok, m, transfer_id="fz", transport="copy")
            good = dp.resume_token(tok, "fz")
            for _ in range(ITERS // 3):
                cand = mutate(rng, good) if rng.random() < 0.7 else rand_json(rng)
                if not isinstance(cand, dict):
                    continue
                self.assert_classified(dp.reconcile, tok, "fz", cand)
        finally:
            env.close()


if __name__ == "__main__":
    unittest.main()
