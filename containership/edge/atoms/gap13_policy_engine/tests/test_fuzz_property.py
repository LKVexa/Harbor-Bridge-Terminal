"""G13-MC-035 fuzz and property-based tests (stdlib random, fixed seeds, time-bounded).

Set G13_FUZZ_ITERATIONS to raise the budget in CI nightly runs.
"""
import json
import os
import random
import string
import time
import unittest

import testkit as k
from gap13_policy_engine import bundle as B, errors as E
from gap13_policy_engine.canonical import canonical_bytes
from gap13_policy_engine.attributes import AttributeSchema, build_request

N = int(os.environ.get("G13_FUZZ_ITERATIONS", "3000"))
g = k.g


def rand_json(rng, depth=0):
    t = rng.randint(0, 7 if depth < 4 else 4)
    if t == 0: return None
    if t == 1: return rng.choice([True, False])
    if t == 2: return rng.randint(-2**70, 2**70)
    if t == 3: return "".join(rng.choice(string.printable + "é‮\u0000퟿") for _ in range(rng.randint(0, 20)))
    if t == 4: return rng.random()
    if t in (5, 6): return [rand_json(rng, depth + 1) for _ in range(rng.randint(0, 4))]
    return {rand_json(rng, 9) if False else "".join(rng.choice("abcxyz_.") for _ in range(rng.randint(0, 6))): rand_json(rng, depth + 1)
            for _ in range(rng.randint(0, 4))}


class ParserFuzz(unittest.TestCase):
    def test_parser_never_crashes(self):
        rng = random.Random(0xC0FFEE)
        base = canonical_bytes(k.bundle_doc())
        deadline = time.time() + 20
        for i in range(N):
            if time.time() > deadline:
                break
            mode = i % 4
            if mode == 0:
                data = bytearray(base)
                for _ in range(rng.randint(1, 8)):
                    data[rng.randrange(len(data))] = rng.randrange(256)
                data = bytes(data)
            elif mode == 1:
                data = base[: rng.randrange(len(base))]
            elif mode == 2:
                data = json.dumps(rand_json(rng)).encode()
            else:
                doc = k.bundle_doc()
                key = rng.choice(list(doc))
                doc[key] = rand_json(rng)
                try:
                    data = canonical_bytes(doc)
                except ValueError:
                    continue
            try:
                b = B.parse_bundle(data)
                self.assertIsInstance(b, B.PolicyBundle)
            except E.BundleRejected:
                pass                       # the only acceptable failure type

    def test_verifier_never_crashes(self):
        rng = random.Random(7)
        env = bytearray(k.envelope())
        v = k.verifier()
        for _ in range(min(N, 1500)):
            d = bytearray(env)
            for _ in range(rng.randint(1, 4)):
                d[rng.randrange(len(d))] = rng.randrange(256)
            r = v.verify(bytes(d), now=k.T0)
            self.assertIn(r.state.value, {s.value for s in g.VerificationState})
            if r.verified:
                self.assertEqual(r.digest, k.verifier().verify(bytes(env), now=k.T0).digest)


class RequestFuzz(unittest.TestCase):
    def test_build_request_only_raises_policy_errors(self):
        rng = random.Random(99)
        schema, lim = AttributeSchema(), g.Limits()
        names = list(schema.specs) + ["x", "Bad", "a.b.c.d.e", "", "identity.z"]
        for _ in range(N):
            attrs = {rng.choice(names): rand_json(rng, 3) for _ in range(rng.randint(0, 6))}
            try:
                build_request(attrs, {}, schema, lim)
            except E.RequestRejected:
                pass


class Properties(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(4242)

    def random_rules(self, n):
        rules = []
        for i in range(n):
            m = {a: self.rng.choice(["read", "write", "t1", "t2"]) for a in
                 self.rng.sample(["action", "resource_type", "site"], self.rng.randint(0, 3))}
            rules.append({"name": f"r{i:03}", "effect": self.rng.choice(["allow", "deny"]), "scope": "estate", "match": m})
        return rules

    def test_order_independence_and_determinism(self):
        for trial in range(30):
            rules = self.random_rules(25)
            shuffled = rules[:]
            self.rng.shuffle(shuffled)
            e1, e2 = g.PolicyEngine("prod"), g.PolicyEngine("prod")
            e1.activate(k.verified(1, rules))
            e2.activate(k.verified(1, shuffled))
            for _ in range(50):
                req = {a: self.rng.choice(["read", "write", "t1", "t2"]) for a in
                       self.rng.sample(["action", "resource_type", "site"], self.rng.randint(0, 3))}
                v1, v2 = e1.evaluate(req), e2.evaluate(req)
                for f in ("effect", "rule", "tie_break", "considered"):
                    self.assertEqual(v1[f], v2[f])
                self.assertEqual(v1, e1.evaluate(req))

    def test_deny_by_default_property(self):
        for _ in range(30):
            rules = [r for r in self.random_rules(20) if r["effect"] == "deny"]
            e = g.PolicyEngine("prod")
            e.activate(k.verified(1, rules))
            req = {"action": self.rng.choice(["read", "write"])}
            self.assertEqual(e.evaluate(req)["effect"], "deny")

    def test_allow_implies_matching_allow_rule_and_no_more_specific_deny(self):
        for _ in range(30):
            rules = self.random_rules(30)
            e = g.PolicyEngine("prod")
            e.activate(k.verified(1, rules))
            req = {"action": "read", "resource_type": "t1", "site": "t2"}
            v = e.evaluate(req)
            if v["effect"] == "allow":
                win = next(r for r in e.rules if r.name == v["rule"])
                self.assertTrue(win.matches(req) and win.effect == "allow")
                for r in e.rules:
                    if r.matches(req) and r.effect == "deny":
                        self.assertLess(r.specificity, win.specificity)


if __name__ == "__main__":
    unittest.main()
