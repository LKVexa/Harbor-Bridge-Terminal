"""Seeded property/fuzz tests for register inputs and selection constraints (MC-046).

stdlib-only (no Hypothesis): a seeded ``random.Random`` generates records and requests; every run is
reproducible from ``INV28_FUZZ_SEED`` (default 2826) and ``INV28_FUZZ_N`` (default 300).  Properties:

P1 soundness     - a selected toolchain satisfies every requested capability and the env's maturity floor
P2 completeness  - if an oracle finds an admissible candidate, selection does not refuse
P3 determinism   - shuffling registration order never changes the decision
P4 refusal shape - a refusal lists every registered candidate exactly once, each with >= 1 code
P5 no crash      - arbitrary junk into from_dict raises only ValidationError
"""
import os
import random
import string
import unittest

from harness import F, RefusalError, ValidationError
from inv28_unikernel_implementations.model import MATURITY, ToolchainRecord
from inv28_unikernel_implementations.selection import SelectionRequest

SEED = int(os.environ.get("INV28_FUZZ_SEED", "2826"))
N = int(os.environ.get("INV28_FUZZ_N", "300"))
LANGS = ("c", "rust", "go", "ocaml")
ARCHES = ("x86_64", "aarch64")
FEATS = ("smp", "tls", "net-stack", "posix-subset")
DEVS = ("virtio-net", "virtio-blk", "nvme")
FLOOR = {"production": 2, "staging": 1, "dev": 0}


def rand_world(rng):
    recs = []
    for i in range(rng.randint(1, 8)):
        recs.append(F.record(
            f"t{i}", languages=rng.sample(LANGS, rng.randint(1, 3)), architectures=rng.sample(ARCHES, rng.randint(1, 2)),
            features=rng.sample(FEATS, rng.randint(0, 3)), devices=rng.sample(DEVS, rng.randint(0, 2)),
            maturity=rng.choice(MATURITY), contact=rng.choice(["mailto:s@x.invalid", "mailto:s@x.invalid", ""])))
    return recs


def rand_request(rng):
    return F.request(environment=rng.choice(list(FLOOR)), language=rng.choice(LANGS), architecture=rng.choice(ARCHES),
                     features=frozenset(rng.sample(FEATS, rng.randint(0, 2))),
                     devices=frozenset(rng.sample(DEVS, rng.randint(0, 1))))


def admissible(r, req):
    if req.language not in r.languages or req.architecture not in r.architectures:
        return False
    if not req.features <= r.features or not req.devices <= r.devices:
        return False
    if MATURITY.index(r.maturity) < FLOOR[req.environment]:
        return False
    if req.environment in ("production", "staging") and not r.security.has_contact:
        return False
    return True


class Properties(unittest.TestCase):
    def test_properties(self):
        rng = random.Random(SEED)
        selected = refused = 0
        for i in range(N):
            recs = rand_world(rng)
            req = rand_request(rng)
            w = F.world(records=recs)
            oracle = [r for r in recs if admissible(r, req)]
            try:
                res = w["selector"].select(req, now=F.NOW)
            except RefusalError as exc:
                refused += 1
                self.assertEqual(oracle, [], f"seed={SEED} case={i}: refused but oracle admits {oracle}")  # P2
                elim = exc.refusal.eliminated
                self.assertEqual(sorted(e["toolchain"] for e in elim), sorted(r.ref for r in recs))       # P4
                self.assertTrue(all(e["codes"] for e in elim))
                continue
            selected += 1
            rec = next(r for r in recs if r.ref == res.ref)
            self.assertTrue(admissible(rec, req), f"seed={SEED} case={i}: unsound pick {res.ref}")        # P1
            best = max(MATURITY.index(r.maturity) for r in oracle)
            self.assertEqual(MATURITY.index(rec.maturity), best)
            shuffled = recs[:]
            rng.shuffle(shuffled)
            self.assertEqual(F.world(records=shuffled)["selector"].select(req, now=F.NOW).ref, res.ref)   # P3
        self.assertGreater(selected, N // 10)
        self.assertGreater(refused, N // 10)

    def test_junk_never_crashes_loaders(self):                                       # P5
        rng = random.Random(SEED + 1)
        template = F.record("x").to_dict()
        req_template = F.request().to_dict()

        def junk():
            return rng.choice([None, 0, -1, 2 ** 70, 1.5, True, "", " ", "x" * 1000, [], {}, ["a", 1], {"a": 1},
                               "".join(rng.choice(string.printable) for _ in range(rng.randint(0, 80)))])
        for _ in range(N * 3):
            for tpl, loader in ((template, ToolchainRecord.from_dict), (req_template, SelectionRequest.from_dict)):
                d = dict(tpl)
                for k in rng.sample(list(d), rng.randint(1, 3)):
                    d[k] = junk()
                if rng.random() < 0.2:
                    d["extra_%d" % rng.randint(0, 9)] = junk()
                try:
                    loader(d)
                except ValidationError:
                    pass


if __name__ == "__main__":
    unittest.main()
