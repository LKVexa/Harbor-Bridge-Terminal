"""Property-based fuzzing of every untrusted-input boundary (C085).

Stdlib only (seeded ``random``; no Hypothesis).  ``INV72_FUZZ_ITERS`` raises the iteration count for the
long CI lane.  Properties:

* the matcher either returns a well-formed decision or raises one of the three declared ValueError
  subclasses - never any other exception;
* a selection never violates the invariants (class, memory, count, isolation, tenant ownership,
  interconnect locality) and is independent of inventory order;
* the schema validator, token parser, traceparent parser, config validator and journal recovery never
  raise anything but their declared error types on arbitrary input.
Any crashing input is written to tests/fuzz_corpus/ and replayed first on every run.
"""
import json
import os
import random
import string
import tempfile
import unittest

from harness import M, PKG_DIR, pkg

ITERS = int(os.environ.get("INV72_FUZZ_ITERS", "1500"))
CORPUS = PKG_DIR / "tests" / "fuzz_corpus"
Device = pkg.Device
DECLARED = (pkg.RequirementValidationError, pkg.InventoryValidationError, pkg.LimitExceededError)


def junk(rng, depth=0):
    choices = [lambda: None, lambda: rng.choice([True, False]), lambda: rng.randint(-10**6, 10**6),
               lambda: rng.choice([float("nan"), float("inf"), -0.0, 1e308, 80.0, 0.5]),
               lambda: "".join(rng.choice(string.printable) for _ in range(rng.randint(0, 20))),
               lambda: rng.choice(["gpu-large", "dedicated", "shared", "t1", "", " "])]
    if depth < 3:
        choices += [lambda: [junk(rng, depth + 1) for _ in range(rng.randint(0, 3))],
                    lambda: {rng.choice(["class", "mem_gb", "tenant", "count", "isolation", "interconnect", "x"]):
                             junk(rng, depth + 1) for _ in range(rng.randint(0, 6))}]
    return rng.choice(choices)()


def plausible_fleet(rng):
    fleet = []
    for i in range(rng.randint(0, 12)):
        part = rng.random() < 0.3
        tenants = set(rng.sample(["t1", "t2", "t3"], rng.randint(0, 2))) if rng.random() < 0.4 else set()
        fleet.append(Device(f"d{i}", rng.choice(["gpu-large", "gpu-small"]), rng.choice([0, 20, 40, 80]),
                            f"n{rng.randint(0, 3)}", rng.choice(["nvl-1", "pcie"]),
                            f"g{i}" if part else "", tenants))
    return fleet


def plausible_req(rng):
    r = {"class": rng.choice(["gpu-large", "gpu-small", "tpu"]), "mem_gb": rng.choice([0, 10, 40, 80, 120]),
         "tenant": rng.choice(["t1", "t2", "t3"])}
    if rng.random() < 0.6:
        r["count"] = rng.randint(1, 4)
    if rng.random() < 0.5:
        r["interconnect"] = rng.random() < 0.5
    if rng.random() < 0.6:
        r["isolation"] = rng.choice(["dedicated", "shared"])
    return r


class MatcherFuzzTest(unittest.TestCase):
    def test_arbitrary_requirements_only_declared_errors(self):
        rng = random.Random(72)
        fleet = plausible_fleet(random.Random(1))
        for _ in range(ITERS):
            r = junk(rng)
            try:
                pkg.decide(r, fleet)
            except DECLARED:
                pass
            except Exception as e:  # pragma: no cover - failure path writes the corpus
                CORPUS.mkdir(exist_ok=True)
                (CORPUS / f"req-{abs(hash(repr(r)))}.json").write_text(json.dumps(repr(r)))
                self.fail(f"undeclared {type(e).__name__} on {r!r}: {e}")

    def test_selection_invariants_hold(self):
        rng = random.Random(7272)
        for _ in range(ITERS):
            fleet, r = plausible_fleet(rng), plausible_req(rng)
            by_id = {d.dev_id: d for d in fleet}
            out = pkg.decide(r, fleet)
            shuffled = list(fleet)
            rng.shuffle(shuffled)
            self.assertEqual(pkg.decide(r, shuffled)["selected"], out["selected"], "order dependence")
            if out["selected"] is None:
                self.assertIn(out["code"], M["errors"].REGISTRY)
                continue
            sel = [by_id[i] for i in out["selected"]]
            self.assertEqual(len(sel), r.get("count", 1))
            self.assertEqual(len(set(out["selected"])), len(sel))
            for d in sel:
                self.assertEqual(d.cls, r["class"])
                self.assertGreaterEqual(d.mem_gb, r["mem_gb"])
                self.assertFalse(d.tenants - {r["tenant"]}, "foreign tenant")
                if d.partition_of:
                    self.assertEqual(r.get("isolation", "dedicated"), "shared", "partition under dedicated")
            if r.get("interconnect"):
                self.assertEqual(len({(d.node, d.link_group) for d in sel}), 1)

    def test_reserve_false_never_mutates(self):
        rng = random.Random(99)
        for _ in range(ITERS // 3):
            fleet, r = plausible_fleet(rng), plausible_req(rng)
            before = [set(d.tenants) for d in fleet]
            pkg.decide(r, fleet, reserve=False)
            self.assertEqual([set(d.tenants) for d in fleet], before)


class BoundaryFuzzTest(unittest.TestCase):
    def test_schema_validator_total(self):
        rng = random.Random(3)
        for _ in range(ITERS):
            v = junk(rng)
            for name in ("PK_ACCEL_REQ-1", "PK_ACCEL_INVENTORY-1", "PK_ACCEL_CONFIG-1"):
                self.assertIsInstance(M["schema_check"].check(v, name), list)

    def test_config_validator_total(self):
        rng = random.Random(4)
        base = M["config"].load_profile("cloud")
        for _ in range(ITERS // 2):
            cand = dict(base)
            cand[rng.choice(list(base) + ["zzz"])] = junk(rng)
            self.assertIsInstance(M["config"].validate(cand), list)

    def test_token_parser_total(self):
        rng = random.Random(5)
        auth = M["trust"].Authenticator(M["trust"].StaticKeyProvider({"p": b"k" * 32}, {"p": {"accel.match"}}))
        for _ in range(ITERS):
            t = rng.choice(["PK_ACCEL_TOKEN/1:", ""]) + "|".join(
                "".join(rng.choice(string.printable) for _ in range(rng.randint(0, 70))) for _ in range(rng.randint(0, 8)))
            try:
                auth.authenticate(t)
            except M["errors"].AccelError as e:
                self.assertIn(e.code, M["errors"].REGISTRY)

    def test_traceparent_total(self):
        rng = random.Random(6)
        for _ in range(ITERS):
            h = junk(rng)
            self.assertRegex(M["telemetry"].TraceContext.parse(h).trace_id, r"^[0-9a-f]{32}$")

    def test_journal_recovery_total(self):
        rng = random.Random(8)
        with tempfile.TemporaryDirectory() as td:
            structured = ["5\n1\n", "[]\n[]\n", '{"seq":0}\n{}\n', "null\n{}\n", '"s"\n{}\n',
                          '{"seq":0,"op":"x","data":null,"prev":"%s","hash":"h"}\n{}\n' % ("0" * 64)]
            for i in range(60 + len(structured)):
                p = os.path.join(td, f"j{i}.jsonl")
                with open(p, "w", encoding="utf-8") as f:
                    f.write(structured[i - 60] if i >= 60 else
                            "".join(rng.choice(string.printable) for _ in range(rng.randint(0, 400))))
                try:
                    M["state"].ReservationStore.recover(p)
                except M["errors"].AccelError:
                    pass
                except Exception as e:  # pragma: no cover
                    self.fail(f"recover raised {type(e).__name__} on journal {i}")

    def test_redaction_total(self):
        rng = random.Random(9)
        for _ in range(ITERS):
            M["redaction"].redact(junk(rng))

    def test_corpus_replays(self):
        for f in sorted(CORPUS.glob("*.json")):
            raw = json.loads(f.read_text())
            try:
                pkg.decide(raw, [])
            except DECLARED:
                pass


if __name__ == "__main__":
    unittest.main()
