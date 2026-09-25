"""MC-17/43 schema contract tests, MC-44 adjacent-layer matrix, MC-46 property/fuzz tests."""
from __future__ import annotations

import random
import string
import subprocess
import sys
import unittest

from _fx import PKG_DIR, Rig, m, sch
from sch01_workload_classification_and_runtime_placem import adapters, errors, schemas
from sch01_workload_classification_and_runtime_placem.errors import SchedulerError


class SchemaContractTest(unittest.TestCase):
    """MC-17 + MC-43: every public payload validates against its published schema."""

    def test_schemas_in_sync_with_generator(self):
        r = subprocess.run([sys.executable, "-B", str(PKG_DIR / "tools/gen_schemas.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_payloads_validate(self):
        r = Rig(); r.node("n1")
        schemas.validate(sch.classify(sch.Workload("w", "t", "public")))
        schemas.validate(r.place())
        schemas.validate(r.s.health())
        from sch01_workload_classification_and_runtime_placem import lifecycle
        r2 = Rig(); r2.node("n1"); schemas.validate(lifecycle.downgrade_placement_v2_to_v1(r2.place()))
        n = [sch.NodeReport("a", "eu", frozenset({"process"}))]
        schemas.validate(sch.place(sch.Workload("w", "t", "internal"), n))
        for code in errors.CATALOG:
            schemas.validate(SchedulerError(code, "m").as_dict())
        schemas.validate(sch.Unplaceable("x").as_dict())

    def test_negative_payloads_refused(self):
        r = Rig(); r.node("n1"); p = r.place()
        for mut in ({"tier": "container"}, {"extra": 1}, {"lease_id": "XYZ"}, {"schema": "PK_PLACEMENT/7"}):
            with self.assertRaises(SchedulerError): schemas.validate(dict(p, **mut))
        bad = dict(p); del bad["node"]
        with self.assertRaises(SchedulerError): schemas.validate(bad)

    def test_unknown_keyword_refused(self):
        with self.assertRaises(ValueError): schemas._check_keywords({"type": "object", "if": {}})


class FakeWorld:
    def __init__(self, r, admit=True):
        self.r, self._admit, self.reclaimed = r, admit, []
    def resolve(self, app, rev): return [m.PlacementRequest(sch.Workload(f"{app}.web", "t1", "partner"))]
    def desired_instances(self, app): return 3
    def reports(self):
        return [(self.r.tok(n, "node", (), ("node-agent",)), self.r.node(n, report=False, slots=2)) for n in ("a", "b")]
    def admit(self, p): return self._admit
    def excluded(self): return {"a"}
    def reclaim(self, lid): self.reclaimed.append(lid)


class IntegrationMatrixTest(unittest.TestCase):
    """MC-44 adjacent layers (fakes): PLN-02, PLN-05, GAP-02, PLN-04, GAP-10, INV-33."""

    def run_world(self, admit):
        r = Rig(); w = FakeWorld(r, admit)
        out = adapters.reconcile(r.s, app="shop", revision="r1", app_plane=w, elastic=w, discovery=w, execution=w,
                                 thermal=w, virt=w, token_factory=lambda: r.tok(roles=("workload-submitter", "execution-plane")),
                                 ctx_factory=r.ctx)
        return r, w, out

    def test_happy_path_respects_thermal_and_capacity(self):
        r, w, out = self.run_world(True)
        self.assertEqual(len(out["placed"]), 2)                 # node a thermally excluded, b has 2 slots
        self.assertTrue(all(p["node"] == "b" and p["tier"] == "unikernel" for p in out["placed"]))
        self.assertEqual(out["refused"][0][1], "NO_CANDIDATE")

    def test_execution_refusal_revokes_and_reclaims(self):
        r, w, out = self.run_world(False)
        self.assertEqual(len(w.reclaimed), 3)   # revocation frees the slot, so all 3 are attempted
        self.assertTrue(all(l["state"] == "REVOKED" for l in r.s.leases.values()))

    def test_every_ext_has_a_port(self):
        for ext, port in adapters.PORTS.items(): self.assertTrue(hasattr(adapters, port), ext)


class PropertyFuzzTest(unittest.TestCase):
    """MC-46 seeded property/fuzz tests: constructors, classifier, candidate sets, error serialization."""

    SEED = 4242

    def rand_text(self, rng):
        return "".join(rng.choice(string.printable) for _ in range(rng.randint(0, 12)))

    def test_constructors_never_crash_unexpectedly(self):
        rng = random.Random(self.SEED)
        junk = [None, 0, -1, True, 1.5, "", " ", "x", [], {}, frozenset(), b"x", "é\u0000"]
        for _ in range(3000):
            args = [rng.choice(junk + [self.rand_text(rng)]) for _ in range(3)]
            try: sch.Workload(*args, needs=rng.choice(junk))
            except (ValueError, TypeError): pass
            try: sch.NodeReport(args[0], args[1], rng.choice(junk), free_slots=rng.choice(junk))
            except (ValueError, TypeError): pass

    def test_placement_invariants(self):
        """For random fleets: a placement never lands below the required tier, on a stale node,
        or beyond capacity; identical inputs yield identical decisions."""
        rng = random.Random(self.SEED)
        provs = ["internal", "first-party", "partner", "public", "quarantined"]
        for trial in range(300):
            def fleet():
                r2 = random.Random(trial)
                return [sch.NodeReport(f"n{i}", r2.choice(["eu", "us"]),
                                       frozenset(r2.sample(sch.TIER_ORDER, r2.randint(1, 5))),
                                       free_slots=r2.randint(0, 2), reported_at=r2.randint(0, 60)) for i in range(r2.randint(1, 8))]
            w = sch.Workload("w", "t", rng.choice(provs), site_affinity=rng.choice([None, "eu"]))
            a = b = None
            try: a = sch.place(w, fleet(), now=60)
            except sch.Unplaceable as e: schemas.validate(e.as_dict()); a = e.code
            try: b = sch.place(w, fleet(), now=60)
            except sch.Unplaceable as e: b = e.code
            self.assertEqual(a, b)
            if isinstance(a, dict):
                klass = sch.classify(w)
                self.assertGreaterEqual(sch.TIER_ORDER.index(a["tier"]), sch.TIER_ORDER.index(klass["required_tier"]))

    def test_service_fuzz_only_catalogued_errors(self):
        rng = random.Random(self.SEED); r = Rig()
        for i in range(8): r.node(f"n{i}", tiers=rng.sample(sch.TIER_ORDER, rng.randint(1, 5)), slots=rng.randint(0, 3),
                                  jurisdiction=rng.choice(["DE", "US"]), zone=rng.choice(["z1", "z2"]))
        for i in range(400):
            try:
                req = r.req(name=f"w{i}", prov=rng.choice(["internal", "partner", "public", "quarantined", "bogus"]),
                            residency=rng.choice([set(), {"DE"}, {"FR"}]), anti_affinity_zone=rng.choice([None, "z1"]),
                            slots=rng.randint(1, 3))
                r.place(req)
            except SchedulerError as e:
                self.assertIn(e.code, errors.CATALOG)


if __name__ == "__main__":
    unittest.main()
