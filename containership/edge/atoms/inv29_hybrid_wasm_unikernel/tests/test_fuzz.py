"""Fuzzing harness (MC032): mutation fuzzing of the untrusted-input surfaces
(record parser, schema validator, interface records, model inputs).

The unit run is short and seeded; tools/fuzz.py runs the same targets for a
wall-clock budget and saves crashing inputs to fuzz/crashes/.  The oracle: the
only allowed exceptions are the documented refusal types - anything else
(KeyError, RecursionError, AttributeError ...) is a finding.
"""
import os
import random
import unittest

import _fixtures as F
from inv29_hybrid_wasm_unikernel import fuzz_targets as T

ITER = int(os.environ.get("INV29_FUZZ_ITER", "1500"))


class FuzzTest(unittest.TestCase):
    def test_targets_only_raise_documented_errors(self):
        r = random.Random(int(os.environ.get("INV29_FUZZ_SEED", "7")))
        for name, target in T.TARGETS.items():
            with self.subTest(target=name):
                for i in range(ITER):
                    data = T.mutate(r, r.choice(T.SEEDS[name]))
                    try:
                        target(data)
                    except T.ALLOWED:
                        pass
                    except Exception as exc:  # pragma: no cover - a finding
                        self.fail(f"{name} iteration {i}: {type(exc).__name__}: {exc!r} on {data[:120]!r}")


if __name__ == "__main__":
    unittest.main()
