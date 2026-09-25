"""Standalone evaluator tests (core semantics, index equivalence, G13-MC-029)."""
import random
import unittest

import testkit as k

g = k.g
Rule, PolicyEngine = g.Rule, g.PolicyEngine


def engine_with(rules_json, gen=1):
    e = PolicyEngine("prod")
    e.activate(k.verified(gen, rules_json))
    return e


def R(name, effect, match, scope="estate"):
    return {"name": name, "effect": effect, "scope": scope, "match": match}


class RuleTests(unittest.TestCase):
    def test_normalises_and_validates_match(self):
        rule = Rule(" r ", "allow", (("z", 1), ("a", 2)))
        self.assertEqual(rule.name, "r")
        self.assertEqual(rule.match, (("a", 2), ("z", 1)))
        for bad in [lambda: Rule("dup", "allow", (("a", 1), ("a", 2))), lambda: Rule("bad", "maybe", ()),
                    lambda: Rule("bad", "allow", (("", 1),))]:
            with self.assertRaises(ValueError):
                bad()

    def test_unhashable_values_are_supported(self):
        self.assertTrue(Rule("l", "deny", (("labels", ["s"]),)).matches({"labels": ["s"]}))

    def test_type_strict_matching(self):
        r = Rule("t", "allow", (("flag", True),))
        self.assertFalse(r.matches({"flag": 1}))
        self.assertFalse(Rule("n", "allow", (("n", 1),)).matches({"n": "1"}))


class EngineTests(unittest.TestCase):
    def test_deny_by_default(self):
        v = PolicyEngine("prod").evaluate({"action": "read"})
        self.assertEqual((v["effect"], v["rule"], v["bundle"]), ("deny", None, None))

    def test_specificity_and_deny_first_tie_break(self):
        e = engine_with([R("allow-read", "allow", {"action": "read"}),
                         R("deny-pii", "deny", {"action": "read", "classification": "pii"}),
                         R("z-allow-pii", "allow", {"action": "read", "classification": "pii"})])
        v = e.evaluate({"action": "read", "classification": "pii"})
        self.assertEqual(v["rule"], "deny-pii")
        self.assertTrue(v["tie_break"])

    def test_rule_name_tie_break_is_deterministic(self):
        e = engine_with([R("z-deny", "deny", {"action": "read"}), R("a-deny", "deny", {"action": "read"})])
        a, b = e.evaluate({"action": "read"}), e.evaluate({"action": "read"})
        self.assertEqual(a, b)
        self.assertEqual(a["rule"], "a-deny")

    def test_caller_asserted_verification_is_refused(self):
        """G13-MC-001 DoD: no API path activates on caller assertion."""
        e = PolicyEngine("prod")
        rules = [Rule("r", "allow", (("action", "read"),))]
        for fake in ({"verified": True}, True, None, "VERIFIED"):
            with self.assertRaises(g.BundleRejected):
                e.load(rules, "v1", fake)
        with self.assertRaises(Exception):
            g.VerificationResult(g.VerificationState.VERIFIED, "forged", None, None, None, None, None, None)
        with self.assertRaises(g.BundleRejected):
            PolicyEngine("prod", rules=tuple(rules))
        self.assertEqual(e.rules, ())

    def test_load_rejects_substituted_rules(self):
        r = k.verified(1)
        e = PolicyEngine("prod")
        with self.assertRaises(g.BundleRejected):
            e.load([Rule("evil", "allow", ())], r.bundle.version, r)
        self.assertEqual(e.load(list(r.bundle.rules), r.bundle.version, r), "v1")

    def test_tenant_rules(self):
        with self.assertRaises(g.BundleRejected):
            engine_with([R("tg", "allow", {"action": "read"}, "tenant")])
        with self.assertRaises(g.ScopeEscalation):
            engine_with([R("ed", "deny", {"labels": ["secret"]}),
                         R("ta", "allow", {"labels": ["secret"], "tenant": "t1"}, "tenant")])

    def test_activation_is_atomic(self):
        e = engine_with([R("old", "deny", {"a": 1})])
        with self.assertRaises(g.ScopeEscalation):
            e.activate(k.verified(2, [R("ed", "deny", {"action": "w"}),
                                      R("ta", "allow", {"action": "w", "tenant": "t"}, "tenant")]))
        self.assertEqual([r.name for r in e.rules], ["old"])

    def test_staleness_boundary(self):
        e = engine_with([])
        e.loaded_at = 100
        self.assertFalse(e.evaluate({}, now=100 + g.BUNDLE_STALENESS_BOUND)["stale"])
        self.assertTrue(e.evaluate({}, now=101 + g.BUNDLE_STALENESS_BOUND)["stale"])
        with self.assertRaises(ValueError):
            e.evaluate({}, now=99)

    def test_explain_redacts_values(self):
        e = engine_with([R("allow", "allow", {"action": "read"}), R("deny", "deny", {"action": "read"})])
        x = e.explain({"action": "read", "resource": "secret-doc-42"})
        self.assertEqual(x["winner"], "deny")
        self.assertEqual([m["rule"] for m in x["matched"]], ["deny", "allow"])
        self.assertNotIn("secret-doc-42", repr(x))
        self.assertFalse(x["truncated"])
        self.assertTrue(e.explain({"action": "read"}, max_matches=1)["truncated"])


class IndexEquivalenceTests(unittest.TestCase):
    """G13-MC-029: compiled index gives identical verdicts to a linear scan."""

    def test_random_equivalence(self):
        rng = random.Random(1307)
        attrs = ["action", "resource_type", "tenant", "classification", "site"]
        vals = ["a", "b", "c", 1, True, ["x"]]
        rules = []
        for i in range(300):
            m = {a: rng.choice(vals) for a in rng.sample(attrs, rng.randint(0, 3))}
            rules.append(Rule(f"r{i:03}", rng.choice(["allow", "deny"]), tuple(m.items())))
        idx = g.CompiledIndex(tuple(rules))
        for _ in range(2000):
            req = {a: rng.choice(vals) for a in rng.sample(attrs, rng.randint(0, 5))}
            linear = sorted((r for r in rules if r.matches(req)), key=lambda r: r.name)
            viaidx = sorted((r for r in idx.candidates(req) if r.matches(req)), key=lambda r: r.name)
            self.assertEqual(linear, viaidx)

    def test_index_visits_fewer_rules(self):
        rules = tuple(Rule(f"r{i}", "allow", (("resource", f"res-{i}"),)) for i in range(5000))
        idx = g.CompiledIndex(rules)
        self.assertEqual(len(idx.candidates({"resource": "res-7"})), 1)


if __name__ == "__main__":
    unittest.main()
