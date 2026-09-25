"""P2-28..39: partial movement, amortisation, replication, DAG, carbon/power/thermal, transfer time,
storage/IOPS, architecture compatibility, quota, calibration/drift, canary/shadow, simulation."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fixtures.estate import Estate  # noqa: E402

from gap14_data_gravity_manager.engine import GravityDecisionError, NoLegalOption  # noqa: E402
from gap14_data_gravity_manager.errors import G14Error  # noqa: E402
from gap14_data_gravity_manager.modeling import CalibrationTracker, CanaryRouter, PageHinkley  # noqa: E402
from gap14_data_gravity_manager.planner import PlanInputs, Route, SiteEconomics, Stage, WorkloadProfile, optimize_dag, plan  # noqa: E402
from gap14_data_gravity_manager.schema_check import validate  # noqa: E402


def inputs(**kw):
    base = dict(dataset="d", data_site="a", compute_site="b", size_gb=100.0, classification="public", converged=True,
                legal=lambda s: (True, "ok"), routes={("a", "b"): Route(1.0, 1.0, bandwidth_gbps=1.0),
                                                    ("b", "a"): Route(1.0, 1.0, bandwidth_gbps=1.0)},
                compute_ok=lambda s: (True, "ok"), quota_ok=lambda s, gb: (True, "ok"), compute_relocation_cost=25.0)
    base.update(kw)
    return PlanInputs(**base)


class PartialMovementTest(unittest.TestCase):  # P2-28
    def test_only_needed_shards_move(self):
        p = WorkloadProfile.parse({"shards": [{"name": "hot", "size_gb": 5, "needed": True},
                                              {"name": "cold", "size_gb": 95, "needed": False}]})
        r = plan(inputs(profile=p))
        self.assertEqual(r["best"]["direction"], "move-data-partial")
        self.assertEqual(r["best"]["cost_breakdown"]["shards"], ["hot"])
        self.assertAlmostEqual(r["best"]["cost"], 5.0)

    def test_all_shards_needed_equals_full_move(self):
        p = WorkloadProfile.parse({"shards": [{"name": "a", "size_gb": 60, "needed": True},
                                              {"name": "b", "size_gb": 40, "needed": True}]})
        r = plan(inputs(profile=p))
        costs = {o["direction"]: o["cost"] for o in r["options"]}
        self.assertAlmostEqual(costs["move-data-partial"], costs["move-data"])

    def test_unconverged_needed_shard_blocks_partial(self):
        p = WorkloadProfile.parse({"shards": [{"name": "hot", "size_gb": 5, "needed": True, "converged": False}]})
        r = plan(inputs(profile=p))
        self.assertIn("DATASET_NOT_CONVERGED", [e["code"] for e in r["eliminated"] if e["direction"] == "move-data-partial"])

    def test_inconsistent_shard_model_rejected(self):
        p = WorkloadProfile.parse({"shards": [{"name": "x", "size_gb": 500, "needed": True}]})
        r = plan(inputs(profile=p))
        self.assertIn("SHARD_MODEL_INCONSISTENT", [e["code"] for e in r["eliminated"]])

    def test_partial_respects_residency(self):
        p = WorkloadProfile.parse({"shards": [{"name": "hot", "size_gb": 1, "needed": True}]})
        r = plan(inputs(profile=p, legal=lambda s: (s == "a", "no")))
        self.assertEqual(r["best"]["direction"], "move-compute")


class AmortisationTest(unittest.TestCase):  # P2-29
    def test_warmup_amortised_and_repeated_transfer_counted(self):
        one = plan(inputs(size_gb=40, profile=WorkloadProfile(runs=1, compute_warmup_cost=100)))
        self.assertEqual(one["best"]["direction"], "move-data")          # 40 < 125
        many = plan(inputs(size_gb=40, profile=WorkloadProfile(runs=50, compute_warmup_cost=100)))
        self.assertEqual(many["best"]["direction"], "move-compute")      # (125)/50=2.5 << 40/run
        cached = plan(inputs(size_gb=40, profile=WorkloadProfile(runs=50, compute_warmup_cost=100, cache_reuse_fraction=1.0)))
        self.assertAlmostEqual([o for o in cached["options"] if o["direction"] == "move-data"][0]["cost"], 0.8)


class ReplicationOptionTest(unittest.TestCase):  # P2-30
    def test_replicate_wins_for_long_lived_repeated_reads(self):
        econ = {"b": SiteEconomics(storage_per_gb_month=0.01)}
        prof = WorkloadProfile(runs=100, replica_months=1, replica_sync_gb_per_run=0.1, compute_warmup_cost=5000)
        r = plan(inputs(size_gb=10, profile=prof, economics=econ))
        dirs = {o["direction"] for o in r["options"]}
        self.assertIn("replicate", dirs)
        rep = [o for o in r["options"] if o["direction"] == "replicate"][0]
        self.assertAlmostEqual(rep["cost_breakdown"]["replica_storage"], 0.1)
        self.assertIn("consistency", rep["cost_breakdown"])

    def test_replicate_requires_convergence(self):
        r = plan(inputs(converged=False, profile=WorkloadProfile(replica_months=1)))
        self.assertIn(("replicate", "DATASET_NOT_CONVERGED"), [(e["direction"], e["code"]) for e in r["eliminated"]])


class DagTest(unittest.TestCase):  # P2-31
    def setUp(self):
        self.ds = {"big": {"site": "a", "size_gb": 1000, "classification": "public"},
                   "small": {"site": "b", "size_gb": 1, "classification": "public"},
                   "pii": {"site": "a", "size_gb": 1, "classification": "pii"}}

    def cost(self, name, gb, cls, a, b):
        if "pii" in cls.split("+") and b != "a":
            return None
        return 0.0 if a == b else gb

    def test_exact_optimum_colocates_with_big_input(self):
        stages = [Stage("join", ("big", "small"), output_gb=10), Stage("report", ("join",))]
        r = optimize_dag(stages, self.ds, ["a", "b"], self.cost, lambda s: 0.0)
        self.assertEqual(r["method"], "exhaustive")
        self.assertEqual(r["assignment"], {"join": "a", "report": "a"})
        self.assertEqual(r["total_cost"], 1.0)

    def test_derived_outputs_inherit_classification(self):
        stages = [Stage("mask", ("pii",), output_gb=1), Stage("out", ("mask", "small"))]
        r = optimize_dag(stages, self.ds, ["a", "b"], self.cost, lambda s: 0.0)
        self.assertEqual(r["assignment"]["out"], "a")

    def test_cycle_and_unknown_rejected(self):
        with self.assertRaises(G14Error):
            optimize_dag([Stage("x", ("y",)), Stage("y", ("x",))], self.ds, ["a"], self.cost, lambda s: 0.0)
        with self.assertRaises(G14Error):
            optimize_dag([Stage("x", ("nope",))], self.ds, ["a"], self.cost, lambda s: 0.0)

    def test_greedy_fallback_reported(self):
        stages = [Stage(f"s{i}", ("small",)) for i in range(12)]
        r = optimize_dag(stages, self.ds, ["a", "b", "c"], self.cost, lambda s: 0.0, max_assignments=1000)
        self.assertEqual(r["method"], "greedy-topological")

    def test_service_dag_uses_verified_inputs_and_is_not_executable(self):
        e = Estate()
        raw = {"workload": {"tenant_id": "t-acme", "workload_id": "wl"},
               "datasets": [{"name": "lake", "tenant_id": "t-acme", "site": "dub", "size_gb": 800, "classification": "public"},
                            {"name": "cust", "tenant_id": "t-acme", "site": "dub", "size_gb": 1, "classification": "pii"}],
               "stages": [{"name": "join", "inputs": ["lake", "cust"], "output_gb": 5}], "candidate_sites": ["dub", "ams"]}
        r = e.service.plan_dag(raw, e.token())
        self.assertFalse(r["executable"])
        self.assertEqual(r["assignment"], {"join": "dub"})  # ams may not hold pii


class CarbonThermalTransferStorageTest(unittest.TestCase):  # P2-32, 33, 34
    def test_carbon_price_shifts_choice(self):
        econ = {"a": SiteEconomics(carbon_g_per_kwh=900), "b": SiteEconomics(carbon_g_per_kwh=20)}
        prof = WorkloadProfile(compute_kwh_per_run=1000, carbon_price_per_kg=0.1)
        r = plan(inputs(size_gb=30, economics=econ, profile=prof))
        self.assertEqual(r["best"]["direction"], "move-data")  # 30 + 2 < 25 + 90
        self.assertAlmostEqual(r["best"]["cost_breakdown"]["per_run_kg_co2"], 20.0)

    def test_thermal_headroom_is_hard_constraint(self):
        econ = {"a": SiteEconomics(thermal_headroom_kw=5)}
        r = plan(inputs(size_gb=1e6, economics=econ, profile=WorkloadProfile(compute_kw=10)))
        self.assertEqual(r["best"]["direction"], "move-data")
        self.assertIn("THERMAL_LIMIT", [e["code"] for e in r["eliminated"]])

    def test_transfer_time_with_congestion(self):
        r = Route(1, 1, bandwidth_gbps=10, congestion=0.5)
        self.assertAlmostEqual(r.transfer_hours(4500), 4500 * 8 / 5 / 3600)
        prof = WorkloadProfile(time_value_per_hour=1000)
        res = plan(inputs(size_gb=10, routes={("a", "b"): Route(1, 1, bandwidth_gbps=0.01), ("b", "a"): Route(1, 1)}, profile=prof))
        self.assertEqual(res["best"]["direction"], "move-compute")

    def test_storage_iops_min_charge_and_rounding(self):
        econ = {"b": SiteEconomics(read_per_gb=0.1, per_million_iops=2, min_charge=5, rounding_gb=10)}
        prof = WorkloadProfile(read_gb_per_run=1, iops_per_run=1000)
        r = plan(inputs(size_gb=1, economics=econ, profile=prof))
        md = [o for o in r["options"] if o["direction"] == "move-data"][0]
        self.assertEqual(md["cost_breakdown"]["storage_io_per_run"], 5.0)   # min charge
        self.assertEqual(md["cost_breakdown"]["one_time_money"], 10.0)     # rounded to 10 GB increments


class CompatQuotaTest(unittest.TestCase):  # P2-35, P2-36 (service-level in test_p0_security_adapters too)
    def test_arch_and_quota_eliminate_before_cost(self):
        r = plan(inputs(size_gb=10, compute_ok=lambda s: (False, f"{s} lacks architecture riscv64"),
                        quota_ok=lambda s, gb: (gb < 50, "quota")))
        self.assertIn("COMPUTE_INCOMPATIBLE", [e["code"] for e in r["eliminated"]])
        with self.assertRaises(NoLegalOption):
            plan(inputs(size_gb=100, compute_ok=lambda s: (False, "no compute capacity"), quota_ok=lambda s, gb: (False, "q")))


class CalibrationTest(unittest.TestCase):  # P2-37
    def test_page_hinkley_detects_shift(self):
        ph = PageHinkley(delta=0.01, threshold=1.0)
        self.assertFalse(any(ph.update(0.02) for _ in range(100)))
        self.assertTrue(any(ph.update(0.8) for _ in range(20)))

    def test_service_drift_alarm_is_telemetry_only(self):
        e = Estate()
        d = e.decide(size=2)
        tok = e.token()
        for _ in range(3):
            rep = e.service.record_outcome(d["provenance"]["decision_id"], {"money": 2.0}, tok)
        self.assertTrue(rep["calibrated"])
        for _ in range(30):
            rep = e.service.record_outcome(d["provenance"]["decision_id"], {"money": 0.5}, tok)
        self.assertFalse(rep["calibrated"])
        self.assertIn("gap14_calibration_drift_alarms_total", e.service.registry.exposition())
        self.assertEqual(e.decide(size=2)["recommendation"]["direction"], "move-data")  # unchanged behaviour


class ShadowCanaryTest(unittest.TestCase):  # P2-38
    def test_shadow_recorded_not_returned(self):
        e = Estate(config_extra={"shadow_model": {"revision": "m2", "compute_relocation_cost": 0.5}})
        d = e.decide(size=2)
        self.assertEqual(d["recommendation"]["direction"], "move-data")
        ex = e.service.explain(d["provenance"]["decision_id"], e.token())
        self.assertEqual(ex["shadow"]["direction"], "move-compute")
        self.assertTrue(ex["shadow"]["diverged"])
        self.assertIn('gap14_shadow_divergence_total{model="shadow"} 1.0', e.service.registry.exposition())

    def test_canary_cohort_deterministic(self):
        r = CanaryRouter(20, b"salt")
        picks = [r.in_canary(f"k{i}") for i in range(5000)]
        self.assertAlmostEqual(sum(picks) / 5000, 0.2, delta=0.03)
        self.assertEqual(picks, [r.in_canary(f"k{i}") for i in range(5000)])

    def test_full_canary_uses_candidate_and_marks_revision(self):
        e = Estate(config_extra={"shadow_model": {"revision": "m2", "compute_relocation_cost": 0.5}, "canary_percent": 100})
        d = e.decide(size=2)
        self.assertEqual(d["recommendation"]["direction"], "move-compute")
        self.assertEqual(d["provenance"]["engine"]["model_revision"], "m2")

    def test_candidate_model_cannot_bypass_residency(self):
        e = Estate(config_extra={"shadow_model": {"revision": "m2", "compute_relocation_cost": 1e6}, "canary_percent": 100})
        d = e.decide(name="c", cls="pii", size=1)
        self.assertEqual(d["recommendation"]["direction"], "move-compute")


class SideEffectTest(unittest.TestCase):
    def test_amortisation_inputs_are_in_signed_decision(self):  # P2-29 A09
        e = Estate()
        d = e.decide(size=40, profile={"runs": 20, "compute_warmup_cost": 100, "cache_reuse_fraction": 0.5})
        bd = d["recommendation"]["cost_breakdown"]
        self.assertEqual(bd["runs"], 20)
        body = {k: v for k, v in d.items() if k not in ("sig", "audit")}
        e.keys.verify(body, d["sig"], expected_issuer="gap14-data-gravity", now=e.clock.now())

    def test_explain_has_no_execution_side_effects(self):  # P1-20 G02
        e = Estate()
        d = e.decide(size=2)
        calls = sum(getattr(e, n).calls for n in ("policy", "topology", "replication", "placement", "dataplane"))
        e.service.explain(d["provenance"]["decision_id"], e.token())
        self.assertEqual(sum(getattr(e, n).calls for n in ("policy", "topology", "replication", "placement", "dataplane")), calls)
        self.assertEqual(e.dataplane.received, [])

    def test_simulation_does_not_mutate_live_config(self):  # P2-39 B05
        e = Estate()
        before = e.config.active.digest
        e.service.simulate({"request": e.request(size=2), "residency": {"dub": ["public"], "ams": ["public"]},
                            "routes": [{"from": "dub", "to": "ams", "locality_multiplier": 1, "egress_per_gb": 1}],
                            "compute_sites": ["ams"], "compute_relocation_cost": 1e6}, e.token())
        self.assertEqual(e.config.active.digest, before)
        self.assertEqual(e.decide(size=500)["recommendation"]["direction"], "move-compute")

    def test_replicate_elimination_is_metered(self):  # P2-30 D01
        e = Estate()
        e.replication.unconverged.add("lake")
        e.decide(size=2, profile={"replica_months": 1})
        self.assertIn('gap14_illegal_options_eliminated_total{direction="replicate",code="DATASET_NOT_CONVERGED"}',
                      e.service.registry.exposition())


class SimulationTest(unittest.TestCase):  # P2-39
    def scenario(self, e, **kw):
        s = {"request": e.request(size=2), "residency": {"dub": ["public"], "ams": ["public"]},
             "routes": [{"from": "dub", "to": "ams", "locality_multiplier": 1, "egress_per_gb": 50},
                        {"from": "ams", "to": "dub", "locality_multiplier": 1, "egress_per_gb": 1}],
             "compute_sites": ["dub", "ams"]}
        s.update(kw)
        return s

    def test_what_if_is_non_executable_and_makes_no_dependency_calls(self):
        e = Estate()
        calls = e.policy.calls + e.topology.calls
        sim = e.service.simulate(self.scenario(e), e.token())
        validate(sim, "PK_GRAVITY_SIMULATION/1")
        self.assertFalse(sim["executable"])
        self.assertEqual(sim["result"]["direction"], "move-compute")
        self.assertEqual(e.policy.calls + e.topology.calls, calls)
        self.assertEqual(e.audit.records[-1]["event"], "simulation.run")

    def test_simulation_cannot_be_executed(self):
        e = Estate()
        sim = e.service.simulate(self.scenario(e), e.token())
        with self.assertRaises(G14Error) as ctx:
            e.service.handoff({**sim, "provenance": {"identity": {"tenant_id": "t-acme"}}}, e.token())
        self.assertEqual(ctx.exception.code, "G14_NOT_EXECUTABLE")

    def test_forged_executable_flag_rejected(self):
        e = Estate(mode="staging")
        d = e.decide(size=2)
        d["executable"] = True
        with self.assertRaises(G14Error) as ctx:
            e.service.handoff(d, e.token())
        self.assertEqual(ctx.exception.code, "G14_NOT_EXECUTABLE")

    def test_simulate_scope_required(self):
        e = Estate()
        with self.assertRaises(G14Error) as ctx:
            e.service.simulate(self.scenario(e), e.token(scopes=("gravity:recommend",)))
        self.assertEqual(ctx.exception.code, "G14_FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
