"""MC-32 - Seeded property/fuzz tests. Deterministic seeds so failures reproduce.

Set PLN02_FUZZ_ITERATIONS to raise the campaign size in CI nightly tiers.
Any crash input is to be added to tests/corpus/ as a regression fixture.
"""
from __future__ import annotations

import copy
import json
import os
import pathlib
import random
import string
import unittest

from helpers import APP

from pln02_application_plane import oam, wit
from pln02_application_plane.errors import to_public
from pln02_application_plane.resolver import ResolutionError, resolve, resolve_document, verify_revision
from pln02_application_plane.errors import PlaneError

N = int(os.environ.get("PLN02_FUZZ_ITERATIONS", "400"))
SEED = int(os.environ.get("PLN02_FUZZ_SEED", "0"))
CORPUS = pathlib.Path(__file__).parent / "corpus"
ALLOWED = (ResolutionError, PlaneError)


def rand_value(rng: random.Random, depth: int = 0):
    choices = [lambda: rng.randint(-5, 5), lambda: "".join(rng.choice(string.printable) for _ in range(rng.randint(0, 8))),
               lambda: None, lambda: rng.random() < 0.5, lambda: float("nan"), lambda: rng.choice(["api", "store", "1.2", "state"])]
    if depth < 3:
        choices += [lambda: [rand_value(rng, depth + 1) for _ in range(rng.randint(0, 3))],
                    lambda: {rand_value(rng, 9) if rng.random() < .2 else rng.choice(["name", "requires", "imports", "exports", "x"]):
                             rand_value(rng, depth + 1) for _ in range(rng.randint(0, 3))}]
    return rng.choice(choices)()


def mutate(rng: random.Random, doc):
    doc = copy.deepcopy(doc)
    target = doc
    path = []
    for _ in range(rng.randint(1, 4)):
        if isinstance(target, dict) and target:
            k = rng.choice(list(target))
            path.append(k)
            if rng.random() < 0.4 or not isinstance(target[k], (dict, list)):
                target[k] = rand_value(rng)
                break
            target = target[k]
        elif isinstance(target, list) and target:
            i = rng.randrange(len(target))
            if rng.random() < 0.4 or not isinstance(target[i], (dict, list)):
                target[i] = rand_value(rng)
                break
            target = target[i]
        else:
            break
    return doc


class ResolverProperties(unittest.TestCase):
    CAT = {"schema": "PK_PROVIDER_CATALOGUE/1", "providers": {"state": "p1"}}

    def test_mutations_only_raise_typed_errors(self):
        rng = random.Random(0xC0FFEE + SEED)
        for i in range(N):
            doc = mutate(rng, APP)
            try:
                rev = resolve_document(doc, self.CAT)
            except ALLOWED as exc:
                self.assertIn(to_public(exc)["code"], {"INVALID_APPLICATION", "UNSATISFIED_CAPABILITY",
                                                       "INCOMPATIBLE_INTERFACE", "RESOLUTION_ERROR"})
                continue
            self.assertTrue(verify_revision(rev), i)

    def test_determinism_under_permutation(self):
        rng = random.Random(7)
        base = resolve_document(APP, self.CAT)["revision"]
        for _ in range(50):
            comps = copy.deepcopy(APP["components"])
            rng.shuffle(comps)
            for c in comps:
                c["requires"] = dict(rng.sample(list(c["requires"].items()), len(c["requires"])))
            self.assertEqual(resolve(comps, list(APP["edges"]), self.CAT["providers"])["revision"], base)

    def test_semantic_change_changes_identity(self):
        base = resolve_document(APP, self.CAT)["revision"]
        doc = copy.deepcopy(APP)
        doc["components"][0]["imports"]["store"] = doc["components"][1]["exports"]["store"] = "1.3"
        self.assertNotEqual(resolve_document(doc, self.CAT)["revision"], base)

    def test_committed_corpus(self):
        for f in sorted(CORPUS.glob("resolver-*.json")):
            case = json.loads(f.read_text())
            try:
                resolve_document(case["input"], self.CAT)
                got = "OK"
            except ALLOWED as exc:
                got = exc.code
            self.assertEqual(got, case["expect"], f.name)


class ParserFuzz(unittest.TestCase):
    SRC = "package pk:s@1.0.0; interface kv { record e { k: string } get: func(k: string) -> option<e>; } world w { export kv; }"

    def test_wit_byte_mutations(self):
        rng = random.Random(1234 + SEED)
        alphabet = "abc{}()<>,:;=@._-> \n0123456789%/"
        for _ in range(N):
            s = list(self.SRC)
            for _ in range(rng.randint(1, 5)):
                op = rng.random()
                pos = rng.randrange(len(s) + 1)
                if op < 0.4 and s:
                    s.pop(min(pos, len(s) - 1))
                elif op < 0.8:
                    s.insert(pos, rng.choice(alphabet))
                else:
                    s[pos:pos] = list(rng.choice(["list<", "result<", "tuple<", "}", "func(", "resource"]))
            try:
                wit.parse("".join(s))
            except PlaneError as exc:
                self.assertEqual(exc.code, "WIT_INVALID")

    def test_oam_mutations(self):
        from test_v43_components import MC09OAM
        rng = random.Random(99 + SEED)
        for _ in range(N):
            try:
                oam.translate(mutate(rng, MC09OAM.DOC))
            except PlaneError as exc:
                self.assertEqual(exc.code, "OAM_INVALID")
            except ResolutionError:
                self.fail("OAM adapter leaked a resolver error")




class FuzzRegressions(unittest.TestCase):
    """Defects found by this campaign during the v4.3.0 build (see CHANGELOG)."""

    def test_r001_non_string_component_key(self):
        with self.assertRaises(ResolutionError) as cm:
            resolve([{"name": "a", True: 1}], [], {})
        self.assertEqual(cm.exception.code, "INVALID_APPLICATION")

    def test_r002_oam_non_list_traits_and_unhashable_type(self):
        from test_v43_components import MC09OAM
        for bad in (5, [{"type": ["x"]}]):
            d = copy.deepcopy(MC09OAM.DOC)
            d["spec"]["components"][0]["traits"] = bad
            with self.assertRaises(PlaneError) as cm:
                oam.translate(d)
            self.assertEqual(cm.exception.code, "OAM_INVALID")


if __name__ == "__main__":
    unittest.main()
