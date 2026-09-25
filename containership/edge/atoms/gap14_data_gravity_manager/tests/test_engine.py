"""Standalone unit tests for the GAP-14 decision engine (stdlib only)."""
import math
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gap14_data_gravity_manager import (  # noqa: E402
    CostModelError,
    Dataset,
    GravityManager,
    NoLegalOption,
)


class DatasetValidationTest(unittest.TestCase):
    def test_rejects_invalid_dataset_fields(self):
        for bad in (-1, float("nan"), float("inf"), True, "1"):
            with self.subTest(size_gb=bad), self.assertRaises(ValueError):
                Dataset("d", "a", bad, "public")
        with self.assertRaises(ValueError):
            Dataset("", "a", 1, "public")
        with self.assertRaises(ValueError):
            Dataset("d", "", 1, "public")
        with self.assertRaises(ValueError):
            Dataset("d", "a", 1, "")
        with self.assertRaises(ValueError):
            Dataset("d", "a", 1, "public", converged=1)


class GravityManagerTest(unittest.TestCase):
    def manager(self, **overrides):
        config = dict(
            residency={"dub": {"public", "pii"}, "ams": {"public"}},
            distance={("dub", "ams"): 1.0, ("ams", "dub"): 1.0},
            compute_sites={"dub", "ams"},
        )
        config.update(overrides)
        return GravityManager(**config)

    def test_small_data_moves_data_large_data_moves_compute(self):
        g = self.manager()
        self.assertEqual(g.recommend(Dataset("small", "dub", 2, "public"), "ams")["direction"], "move-data")
        self.assertEqual(g.recommend(Dataset("large", "dub", 500, "public"), "ams")["direction"], "move-compute")

    def test_residency_filters_before_cost(self):
        g = self.manager()
        result = g.recommend(Dataset("customers", "dub", 1, "pii"), "ams")
        self.assertEqual(result["direction"], "move-compute")
        self.assertIn("move-data: ams may not hold pii", result["eliminated"])
        self.assertEqual(result["elimination_details"][0]["code"], "RESIDENCY_FORBIDDEN")

    def test_unconverged_data_is_not_moved(self):
        g = self.manager(compute_sites={"ams"})
        with self.assertRaises(NoLegalOption) as ctx:
            g.recommend(Dataset("live", "dub", 1, "public", converged=False), "ams")
        self.assertIn("unresolved replication conflicts", str(ctx.exception))
        self.assertEqual(ctx.exception.code, "PK_GRAVITY_NO_LEGAL_OPTION")

    def test_no_legal_option_is_machine_readable(self):
        g = GravityManager(
            residency={"dub": {"pii"}, "ams": {"public"}},
            distance={("dub", "ams"): 1.0, ("ams", "dub"): 1.0},
            compute_sites={"ams"},
        )
        with self.assertRaises(NoLegalOption) as ctx:
            g.recommend(Dataset("pinned", "dub", 1, "pii"), "ams")
        payload = ctx.exception.as_dict()
        self.assertEqual(payload["code"], "PK_GRAVITY_NO_LEGAL_OPTION")
        self.assertEqual(len(payload["details"]["eliminated"]), 2)

    def test_missing_route_cost_fails_closed(self):
        g = GravityManager(
            residency={"dub": {"public"}, "ams": {"public"}},
            distance={},
            compute_sites={"dub", "ams"},
        )
        with self.assertRaises(CostModelError) as ctx:
            g.recommend(Dataset("d", "dub", 1, "public"), "ams")
        self.assertEqual(ctx.exception.code, "PK_GRAVITY_COST_MODEL_ERROR")
        self.assertIn("missing locality multiplier", str(ctx.exception))

    def test_cost_breakdown_and_asymmetric_egress(self):
        g = self.manager(egress_per_gb={("dub", "ams"): 5.0})
        result = g.recommend(Dataset("d", "dub", 10, "public"), "ams")
        self.assertEqual(result["direction"], "move-compute")
        data = next(o for o in result["options"] if o["direction"] == "move-data")
        self.assertEqual(data["cost"], 50.0)
        self.assertEqual(data["cost_breakdown"]["egress_per_gb"], 5.0)
        self.assertEqual(result["cost_breakdown"]["total"], result["cost"])

    def test_exact_cost_tie_prefers_moving_compute(self):
        g = self.manager()
        result = g.recommend(Dataset("d", "dub", 25, "public"), "ams")
        self.assertEqual(result["cost"], 25.0)
        self.assertEqual(result["direction"], "move-compute")

    def test_colocated_is_noop_only_when_current_residency_is_legal(self):
        g = self.manager()
        result = g.recommend(Dataset("d", "ams", 1, "public"), "ams")
        self.assertEqual(result["direction"], "none")
        self.assertEqual(result["reason_code"], "ALREADY_COLOCATED")
        self.assertEqual(result["cost_breakdown"]["total"], 0.0)

        illegal = GravityManager(residency={"ams": {"public"}}, compute_sites={"ams"})
        with self.assertRaises(NoLegalOption):
            illegal.recommend(Dataset("d", "ams", 1, "pii"), "ams")

    def test_config_is_snapshotted(self):
        residency = {"dub": {"public"}, "ams": {"public"}}
        distance = {("dub", "ams"): 1.0, ("ams", "dub"): 1.0}
        sites = {"dub", "ams"}
        g = GravityManager(residency=residency, distance=distance, compute_sites=sites)
        residency["ams"].clear()
        distance[("dub", "ams")] = math.inf
        sites.clear()
        self.assertTrue(g.legal("ams", "public"))
        self.assertEqual(g.move_data_cost(Dataset("d", "dub", 1, "public"), "ams"), 1.0)
        self.assertIn("ams", g.compute_sites)

    def test_rejects_invalid_cost_configuration(self):
        for bad in (-1, float("nan"), float("inf"), True, "1"):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                GravityManager(distance={("a", "b"): bad})
        with self.assertRaises(ValueError):
            GravityManager(egress_per_gb={("a", "b"): -1})
        with self.assertRaises(ValueError):
            GravityManager(compute_relocation_cost=float("inf"))
        with self.assertRaises(ValueError):
            GravityManager(compute_sites="ams")
        with self.assertRaises(ValueError):
            GravityManager(residency={"ams": None})


if __name__ == "__main__":
    unittest.main()
