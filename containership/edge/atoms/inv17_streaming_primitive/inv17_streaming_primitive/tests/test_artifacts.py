"""Machine checks over the documentation/governance artifacts so no item is closed by prose:
state machine replayed against the runtime, requirement/threat/alert/dashboard references
resolved, policy files equal to code defaults, and every ``module::symbol`` cited in the
Markdown resolves to a real attribute (doc-drift guard)."""
import dataclasses
import importlib
import json
import re
import sys
import unittest

from _pkg import PKG_DIR, control as C, observability as O, stream as S

J = lambda rel: json.loads((PKG_DIR / rel).read_text())


def reach(state):
    s = S.Stream(int, config=S.StreamConfig(max_credit=4, max_buffer=4))
    for step in J("spec/stream-state-machine.json")["setup"][state]:
        getattr(s, step[0])(*step[1:])
    assert s.state == state, (state, s.state)
    return s


class StateMachineTest(unittest.TestCase):
    def test_every_documented_transition_matches_runtime(self):
        sm = J("spec/stream-state-machine.json")
        self.assertEqual(len(sm["transitions"]), 42)
        for t in sm["transitions"]:
            s = reach(t["from"])
            args = {"grant": (1,), "write": (1,), "freeze": ("x",)}.get(t["op"], ())
            try:
                r = getattr(s, t["op"])(*args)
                got = "EOF" if (t["op"] == "read" and r is None) else ("NOT_READY" if r is S.NOT_READY else s.state)
            except S.StreamError as e:
                got = type(e).__name__
            self.assertEqual(got, t["expect"], t)

    def test_state_precedence_matches_property(self):
        s = S.Stream(int); s.grant(1); s.freeze("x"); s.end(); s.drop_writer(); s.drop_reader()
        self.assertEqual(s.state, J("spec/stream-state-machine.json")["state_precedence"][0])


class PolicyEqualsCodeTest(unittest.TestCase):
    def test_health_policy_json_equals_code_defaults(self):
        doc = J("operations/health-policy.json")
        for f in dataclasses.fields(C.HealthPolicy):
            self.assertEqual(doc[f.name], f.default, f.name)

    def test_config_defaults_equal_runtime_defaults(self):
        d = J("config/defaults.json")["stream"]
        cfg = S.StreamConfig()
        self.assertEqual((d["max_credit"], d["max_buffer"], d["idempotency_window"]),
                         (cfg.max_credit, cfg.max_buffer, cfg.idempotency_window))

    def test_capability_policy_equals_code(self):
        from _pkg import security as X
        pol = J("security/capability-policy.json")
        self.assertEqual(set(pol["rights"]), set(X.RIGHTS))
        self.assertEqual(pol["max_ttl_seconds"], X.CapabilityAuthority().max_ttl)


class ReferenceTest(unittest.TestCase):
    def test_requirements_cite_existing_tests(self):
        reqs = J("spec/requirements.json")["requirements"]
        self.assertGreaterEqual(len(reqs), 19)
        for r in reqs:
            for v in r["verification"]:
                self.assertTrue((PKG_DIR / v).exists(), (r["id"], v))

    def test_threat_model_tests_exist(self):
        for t in J("security/threat-model.json")["threats"]:
            for ref in t["tests"]:
                path, _, name = ref.partition("::")
                self.assertTrue((PKG_DIR / path).exists(), ref)
                if name:
                    self.assertIn(name.split(".")[-1], (PKG_DIR / path).read_text(), ref)

    def test_alerts_and_dashboards_use_exported_metrics(self):
        exported = set(O.MetricsExporter.HELP)
        exprs = [r["expr"] for g in J("observability/alert-rules.json")["groups"] for r in g["rules"]]
        exprs += [t["expr"] for p in J("observability/dashboards/inv17-overview.json")["panels"] for t in p["targets"]]
        for e in exprs:
            names = set(re.findall(r"\binv17_[a-z_]+", e))
            self.assertTrue(names, e)
            self.assertLessEqual(names, exported, e)
        classes = {r["labels"]["class"] for g in J("observability/alert-rules.json")["groups"] for r in g["rules"]}
        for needed in ("load", "overload", "dependency-failure", "attack"):
            self.assertIn(needed, classes)

    def test_closure_register_covers_all_64_components(self):
        comps = J("conformance/closure-status.json")["components"]
        self.assertEqual([c["n"] for c in comps], list(range(1, 65)))
        allowed = set(J("conformance/closure-status.json")["statuses"])
        for c in comps:
            self.assertIn(c["status"], allowed)
            if c["status"] != "IMPLEMENTED_VERIFIED":
                self.assertTrue(c["open_item"], c["n"])

    def test_governance_records_shape(self):
        o = J("governance/OWNERS.json")
        for k in ("primary_owner", "deputy", "paging_target", "authorities", "review", "status"):
            self.assertIn(k, o)
        for w in J("governance/waivers.json")["waivers"]:
            for k in ("id", "control", "rationale", "owner", "approver", "scope", "expires", "status"):
                self.assertIn(k, w)

    def test_rollout_controller_rolls_back(self):
        sys.path.insert(0, str(PKG_DIR / "tools"))
        ro = importlib.import_module("rollout")
        self.assertEqual(ro.run(fleet=10)["outcome"], "completed")
        bad = ro.run(fleet=10, fail_at="canary")
        self.assertEqual(bad["outcome"], "rolled_back")


SYMBOL = re.compile(r"`?([a-z_]+)(?:\.py)?::([A-Za-z_][A-Za-z0-9_.]*)`?")
MODULES = {"stream", "control", "security", "configuration", "observability", "adapters", "wire", "contract", "component"}


class DocDriftTest(unittest.TestCase):
    def test_every_cited_symbol_exists(self):
        bad, seen = [], 0
        for md in PKG_DIR.rglob("*.md"):
            if "vendor" in md.parts or md.name in ("MASTER.md",):
                continue
            for mod, sym in SYMBOL.findall(md.read_text(encoding="utf-8")):
                if mod not in MODULES or mod in ("contract", "component"):
                    continue
                seen += 1
                module = importlib.import_module(f"{PKG_DIR.name}.{mod}")
                src = (PKG_DIR / f"{mod}.py").read_text()
                obj = module
                for part in sym.split("."):
                    if sym.endswith("drop_") and part == "drop_":
                        break  # "drop_*" wildcard in prose
                    if hasattr(obj, part):
                        obj = getattr(obj, part)
                        continue
                    if re.search(rf"self\.{re.escape(part)}\b", src):
                        break  # instance attribute assigned in __init__
                    bad.append(f"{md.relative_to(PKG_DIR)}: {mod}::{sym}")
                    break
        self.assertGreater(seen, 50)
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
