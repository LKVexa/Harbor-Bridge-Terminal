"""P1-22: property and fuzz tests (seeded, stdlib-only, reproducible).

Set GAP14_FUZZ_ITERS to raise the iteration count in CI soak jobs.
"""
import json
import math
import os
import pathlib
import random
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fixtures.estate import Estate  # noqa: E402

from gap14_data_gravity_manager.engine import Dataset, GravityDecisionError, GravityManager, NoLegalOption  # noqa: E402
from gap14_data_gravity_manager.planner import PlanInputs, Route, plan  # noqa: E402
from gap14_data_gravity_manager.schema_check import validate  # noqa: E402
from gap14_data_gravity_manager.trust import canonical_json  # noqa: E402

ITERS = int(os.environ.get("GAP14_FUZZ_ITERS", "400"))
SITES = ["a", "b", "c"]
CLASSES = ["public", "pii", "secret"]


def random_world(rng):
    residency = {s: set(rng.sample(CLASSES, rng.randint(0, 3))) for s in SITES}
    distance = {(x, y): rng.choice([0.0, 0.5, 1.0, 3.7, 1e3]) for x in SITES for y in SITES if x != y}
    egress = {(x, y): rng.choice([0.0, 0.01, 1.0, 9.5]) for x in SITES for y in SITES if x != y and rng.random() < 0.5}
    compute = set(rng.sample(SITES, rng.randint(0, 3)))
    return residency, distance, egress, compute


class EngineProperties(unittest.TestCase):
    def test_legality_is_never_violated_and_choice_is_minimal(self):
        rng = random.Random(1414)
        for _ in range(ITERS):
            residency, distance, egress, compute = random_world(rng)
            g = GravityManager(residency=residency, distance=distance, egress_per_gb=egress, compute_sites=compute,
                               compute_relocation_cost=rng.choice([0.0, 1.0, 25.0, 1e4]))
            ds = Dataset("d", rng.choice(SITES), rng.choice([0, 0.5, 2, 500, 1e6]), rng.choice(CLASSES),
                         converged=rng.random() < 0.8)
            cs = rng.choice(SITES)
            try:
                r = g.recommend(ds, cs)
            except NoLegalOption:
                continue
            if r["direction"] == "none":
                self.assertIn(ds.classification, residency[ds.site])
                continue
            # legality: the chosen destination may hold the data class
            holder = r["to"] if r["direction"] == "move-data" else ds.site
            self.assertIn(ds.classification, residency[holder])
            if r["direction"] == "move-data":
                self.assertTrue(ds.converged)
            else:
                self.assertIn(ds.site, compute)
            # minimality + tie-break
            self.assertEqual(r["cost"], min(o["cost"] for o in r["options"]))
            if len(r["options"]) == 2 and r["options"][0]["cost"] == r["options"][1]["cost"]:
                self.assertEqual(r["direction"], "move-compute")
            validate(r, "PK_GRAVITY_RECOMMENDATION/1")

    def test_planner_reduces_exactly_to_engine_without_profile(self):
        rng = random.Random(2024)
        compared = 0
        for _ in range(ITERS):
            residency, distance, egress, compute = random_world(rng)
            rc = rng.choice([0.0, 1.0, 25.0])
            g = GravityManager(residency=residency, distance=distance, egress_per_gb=egress, compute_sites=compute,
                               compute_relocation_cost=rc)
            ds = Dataset("d", rng.choice(SITES), rng.choice([0, 2, 500]), rng.choice(CLASSES), converged=rng.random() < 0.8)
            cs = rng.choice([s for s in SITES if s != ds.site])
            routes = {k: Route(v, egress.get(k, 1.0)) for k, v in distance.items()}
            inp = PlanInputs(ds.name, ds.site, cs, ds.size_gb, ds.classification, ds.converged,
                             lambda s: (ds.classification in residency[s], "x"), routes,
                             lambda s: (s in compute, "no compute capacity"), lambda s, gb: (True, "ok"), rc)
            try:
                a = g.recommend(ds, cs)
            except NoLegalOption:
                with self.assertRaises(NoLegalOption):
                    plan(inp)
                continue
            b = plan(inp)["best"]
            self.assertEqual((a["direction"], a["to"]), (b["direction"], b["to"]))
            self.assertTrue(math.isclose(a["cost"], b["cost"], rel_tol=1e-12, abs_tol=1e-12))
            compared += 1
        self.assertGreater(compared, ITERS // 5)


def _mutations(rng, req):
    """Yield malformed variants of a valid request."""
    bad_values = [None, True, -1, float("inf"), float("nan"), "", " ", "x" * 500, "é́", "a b", {}, [], 1e300, "../x",
                  "\x00", "DROP TABLE",
                  5e-324, 1.7976931348623157e308, -0.0, 0.1 + 0.2, 2**63, -2**63]
    paths = [("request_id",), ("compute_site",), ("dataset", "name"), ("dataset", "site"), ("dataset", "size_gb"),
             ("dataset", "classification"), ("dataset", "tenant_id"), ("workload", "tenant_id"), ("workload", "workload_id"),
             ("workload", "environment"), ("schema",)]
    for _ in range(ITERS):
        r = json.loads(json.dumps(req))
        op = rng.random()
        path = rng.choice(paths)
        tgt = r
        for p in path[:-1]:
            tgt = tgt[p]
        if op < 0.6:
            tgt[path[-1]] = rng.choice(bad_values)
        elif op < 0.8:
            tgt.pop(path[-1], None)
        else:
            tgt["unexpected_" + str(rng.randint(0, 9))] = 1
        yield r


class RequestFuzz(unittest.TestCase):
    def test_malformed_requests_always_refused_with_registered_code(self):
        e = Estate()
        rng = random.Random(77)
        tok = e.token(ttl=3600)
        base = e.request()
        refused = 0
        for r in _mutations(rng, base):
            r["request_id"] = r.get("request_id") if not isinstance(r.get("request_id"), str) else f"{r['request_id']}-{refused}"
            try:
                e.service.decide(r, tok)
            except GravityDecisionError as exc:
                self.assertTrue(exc.code.startswith(("G14_", "PK_GRAVITY_")), exc.code)
                self.assertNotEqual(exc.code, "G14_INTERNAL", f"internal fault on malformed input {r}")
                refused += 1
            except Exception as exc:  # pragma: no cover - any other exception type is a defect
                self.fail(f"unclassified exception {type(exc).__name__}: {exc} for {r}")
        self.assertGreater(refused, ITERS * 0.8)

    def test_canonical_json_rejects_non_finite(self):
        for v in (float("nan"), float("inf")):
            with self.assertRaises(GravityDecisionError):
                canonical_json({"x": [v]})

    def test_config_fuzz_never_activates_invalid(self):
        e = Estate()
        rng = random.Random(9)
        knobs = ["decision_deadline_s", "dependency_timeout_s", "max_batch", "retry_max_attempts", "bogus"]
        activated = 0
        for i in range(ITERS // 4):
            body = {"schema": "PK_GAP14_CONFIG/1", "revision": 100 + i, "mode": rng.choice(["production", "test", "prod"]),
                    "knobs": {rng.choice(knobs): rng.choice([-1, 0, 0.001, 0.05, 1e9, "1", None, True])}}
            try:
                cfg = e.config.activate(e.signed_config(body), e.clock.now())
                activated += 1
                self.assertLessEqual(cfg.knobs["dependency_timeout_s"], cfg.knobs["decision_deadline_s"])
            except GravityDecisionError as exc:
                self.assertIn(exc.code, ("G14_CONFIG_INVALID", "G14_CONFIG_FORBIDDEN_IN_PRODUCTION"))
        self.assertGreater(activated, 0)


if __name__ == "__main__":
    unittest.main()
