"""Fuzz / property-based tests for the untrusted parsing boundary (item 51).

Seeded, stdlib-only generators (no Hypothesis dependency). Properties:
  P1 translate() either returns schema-valid output or raises TranslationError —
     never any other exception, never mutates input.
  P2 every unknown field injected anywhere is named in the refusal.
  P3 quantity() never accepts a string the Kubernetes grammar rejects and is
     monotone in the numeric value for same-suffix inputs.
"""
import copy
import json
import random
import string
import unittest

import _support as S

T, V = S.translator, S.mod("schema")
SCHEMA = json.loads((S.PKG_DIR / "schemas/PK_K8S_TRANSLATE_v1.schema.json").read_text())
N = 3000


def rand_value(r, depth=0):
    k = r.randrange(9 if depth < 3 else 6)
    return [lambda: r.randrange(-5, 10**6), lambda: r.random() * 1e9, lambda: "".join(r.choices(string.printable, k=r.randrange(12))),
            lambda: None, lambda: r.choice([True, False]), lambda: r.choice(["250m", "1Gi", "1e3", "-1", "NaN", "1KB", "", "9" * 70]),
            lambda: [rand_value(r, depth + 1) for _ in range(r.randrange(3))],
            lambda: {r.choice(["name", "image", "cpu", "memory", "requests", "x"]): rand_value(r, depth + 1) for _ in range(r.randrange(3))},
            lambda: {"cpu": r.choice(["1", "100m", "2Gi"]), "memory": "64Mi"}][k]()


def base():
    return {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "a", "labels": {"x": "y"}},
            "spec": {"containers": [{"name": "c", "image": "i", "resources": {"requests": {"cpu": "1"}, "limits": {"memory": "1Gi"}}}]}}


def paths(obj, prefix=()):
    yield prefix
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from paths(v, prefix + (k,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from paths(v, prefix + (i,))


def mutate(r, pod):
    ps = list(paths(pod))
    p = r.choice(ps)
    tgt = pod
    for k in p[:-1]:
        tgt = tgt[k]
    if p:
        if r.random() < 0.5:
            tgt[p[-1]] = rand_value(r)
        elif isinstance(tgt, dict):
            del tgt[p[-1]]
    return pod


class Fuzz(unittest.TestCase):
    def test_p1_total_and_non_mutating(self):
        r = random.Random(67)
        ok = refused = 0
        for _ in range(N):
            pod = mutate(r, mutate(r, base()))
            snap = copy.deepcopy(pod)
            try:
                out = T.translate(pod)
            except T.TranslationError as e:
                refused += 1
                d = e.to_dict()
                self.assertTrue(d["details"] or d["message"])
            else:
                ok += 1
                self.assertEqual(V.errors(SCHEMA, out), [], (pod, out))
            self.assertEqual(pod, snap)
        self.assertGreater(ok, 50)
        self.assertGreater(refused, 500)

    def test_p2_injected_unknown_fields_are_named(self):
        r = random.Random(68)
        sites = [((), ""), (("metadata",), "metadata."), (("spec",), "spec."), (("spec", "containers", 0), "spec.containers[0]."),
                 (("spec", "containers", 0, "resources"), "spec.containers[0].resources.")]
        for _ in range(500):
            pod = base()
            site, prefix = r.choice(sites)
            tgt = pod
            for k in site:
                tgt = tgt[k]
            name = "zz" + "".join(r.choices(string.ascii_lowercase, k=6))
            tgt[name] = rand_value(r)
            with self.assertRaises(T.Unsupported) as ctx:
                T.translate(pod)
            self.assertIn(prefix + name, {d.field for d in ctx.exception.details})

    def test_p3_quantity_grammar_and_monotonicity(self):
        r = random.Random(69)
        for _ in range(N):
            s = "".join(r.choices("0123456789.eE+-kMGTPEKimun ", k=r.randrange(1, 10)))
            try:
                v = T.quantity(s)
            except ValueError:
                continue
            self.assertGreaterEqual(v, 0)
            self.assertNotIn(" ", s)
        for suf in ["", "m", "k", "Mi", "Gi"]:
            xs = sorted(r.sample(range(0, 10**6), 50))
            vals = [T.quantity(f"{x}{suf}") for x in xs]
            self.assertEqual(vals, sorted(vals))


if __name__ == "__main__":
    unittest.main()
