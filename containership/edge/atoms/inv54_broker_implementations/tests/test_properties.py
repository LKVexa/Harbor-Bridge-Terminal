"""Seeded property/fuzz-style tests (component 85). Deterministic: fixed seeds, bounded runs."""
from __future__ import annotations

import importlib
import pathlib
import random
import string
import sys
import tempfile
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG_DIR.parent))
P = PKG_DIR.name
security = importlib.import_module(f"{P}.security")
config = importlib.import_module(f"{P}.config")
storage = importlib.import_module(f"{P}.storage")
brokers = importlib.import_module(f"{P}.brokers")
errors = importlib.import_module(f"{P}.errors")

ALPH = string.printable + "é☃\x00\x7f"


class Properties(unittest.TestCase):
    def test_c85_name_grammar_accepts_iff_regex(self):
        import re
        rx = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")
        rng = random.Random(85)
        for _ in range(3000):
            s = "".join(rng.choice(ALPH) for _ in range(rng.randint(0, 140)))
            ok = bool(rx.fullmatch(s))
            try:
                security.check_name(s, "n")
                self.assertTrue(ok, repr(s))
            except errors.BrokerError:
                self.assertFalse(ok, repr(s))

    def test_c85_validator_never_crashes_on_random_configs(self):
        rng = random.Random(851)
        vals = [None, 0, -1, 1, True, 10 ** 12, "x", "secret://env/X", [], {}, 1.5]
        keys = list(config.DEFAULTS)
        for _ in range(1500):
            cfg = config.apply_overlays({})
            for _ in range(rng.randint(1, 5)):
                k = rng.choice(keys)
                if isinstance(cfg[k], dict) and cfg[k] and rng.random() < .7:
                    sk = rng.choice(list(cfg[k]))
                    cfg[k][sk] = rng.choice(vals)
                else:
                    cfg[k] = rng.choice(vals)
            try:
                probs = config.validate(cfg)
            except Exception as exc:  # validator must return problems, never raise
                raise AssertionError(f"validator raised {type(exc).__name__} on {cfg}") from exc
            self.assertIsInstance(probs, list)

    def test_c85_c57_recovery_on_random_truncation_is_a_prefix(self):
        rng = random.Random(857)
        for trial in range(40):
            d = tempfile.mkdtemp()
            log = storage.DurableLog(d, 1, fsync="never")
            n = rng.randint(1, 30)
            for i in range(n):
                log.append("k", {"i": i, "pad": "x" * rng.randint(0, 50)})
            log.close()
            p = pathlib.Path(d) / "p0.log"
            data = p.read_bytes()
            p.write_bytes(data[: rng.randint(0, len(data))])
            got = [r.value["i"] for r in storage.DurableLog(d, 1).read(0, 0, 10 ** 6)]
            self.assertEqual(got, list(range(len(got))))

    def test_c85_log_model_equivalence(self):
        """Random op sequences on PartitionedLog match a trivial reference model."""
        rng = random.Random(8585)
        for _ in range(200):
            log = brokers.PartitionedLog(3)
            model = {p: [] for p in range(3)}
            offs = {}
            for _ in range(60):
                op = rng.random()
                if op < .5:
                    k = rng.choice("abcde")
                    p, o = log.append(k, rng.random())
                    model[p].append(k)
                    self.assertEqual(o, len(model[p]) - 1)
                elif op < .8:
                    c, p = rng.choice("xy"), rng.randrange(3)
                    got = log.poll(c, p, rng.randint(0, 5))
                    start = offs.get((c, p), 0)
                    self.assertEqual([k for k, _ in got], model[p][start:start + len(got)])
                    offs[(c, p)] = start + len(got)
                else:
                    c, p = rng.choice("xy"), rng.randrange(3)
                    o = rng.randint(0, len(model[p]))
                    log.seek(c, p, o)
                    offs[(c, p)] = o


if __name__ == "__main__":
    unittest.main()
