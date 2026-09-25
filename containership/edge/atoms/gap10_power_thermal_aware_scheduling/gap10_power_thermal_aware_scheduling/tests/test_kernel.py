"""Standalone unit tests for the stdlib-only GAP-10 constraint kernel."""
import importlib.util
import json
import math
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
MODEL_PATH = PKG_DIR / "model.py"
SPEC = importlib.util.spec_from_file_location("gap10_model_test_target", MODEL_PATH)
model = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = model
SPEC.loader.exec_module(model)


class PolicyTests(unittest.TestCase):
    def test_invalid_temperature_order_is_rejected(self):
        with self.assertRaises(model.PolicyError):
            model.PowerThermalPolicy(elevated_c=90, critical_c=80)

    def test_invalid_ceiling_is_rejected(self):
        with self.assertRaises(model.PolicyError):
            model.PowerThermalPolicy(emergency_ceiling=0.1)


class ThermalStateTests(unittest.TestCase):
    def test_unobserved_startup_is_constrained(self):
        state = model.ThermalState("n1")
        self.assertEqual(state.band, "critical")
        self.assertEqual(state.ceiling(8)["ceiling"], 2)
        self.assertEqual(state.telemetry_status, "unobserved")

    def test_temperature_bands_and_hysteresis(self):
        state = model.ThermalState("n1")
        self.assertEqual(state.update(temperature=40.0), "nominal")
        self.assertEqual(state.update(temperature=80.0), "elevated")
        self.assertEqual(state.update(temperature=86.0), "critical")
        self.assertEqual(state.update(temperature=84.0), "critical")
        self.assertEqual(state.update(temperature=79.9), "elevated")

    def test_missing_nan_and_infinite_temperature_fail_closed(self):
        for value in (None, math.nan, math.inf, -math.inf, -1000.0, 1000.0, "hot", True):
            with self.subTest(value=value):
                state = model.ThermalState("n1")
                self.assertEqual(state.update(temperature=value), "critical")
                self.assertIn("temperature", state.ceiling(8)["reason"])

    def test_power_budget_is_enforced(self):
        state = model.ThermalState("n1")
        self.assertEqual(
            state.update(temperature=40.0, power_draw_watts=190.0, power_budget_watts=200.0),
            "critical",
        )
        self.assertEqual(state.ceiling(20)["ceiling"], 5)
        self.assertIn("power ratio", state.ceiling(20)["reason"])

    def test_power_budget_breach_excludes(self):
        state = model.ThermalState("n1")
        self.assertEqual(
            state.update(temperature=40.0, power_draw_watts=200.0, power_budget_watts=200.0),
            "emergency",
        )
        self.assertTrue(state.ceiling(20)["excluded"])
        self.assertEqual(state.ceiling(20)["ceiling"], 0)

    def test_incomplete_power_evidence_fails_closed(self):
        state = model.ThermalState("n1")
        self.assertEqual(state.update(temperature=40.0, power_budget_watts=200.0), "critical")

    def test_battery_reserve_and_recovery_margin(self):
        state = model.ThermalState("n1")
        self.assertEqual(state.update(temperature=30.0, battery=0.10), "critical")
        self.assertEqual(state.update(temperature=30.0, battery=0.16), "critical")
        self.assertEqual(state.update(temperature=30.0, battery=0.18), "nominal")

    def test_stale_and_future_readings_fail_closed(self):
        stale = model.ThermalState("n1")
        self.assertEqual(stale.update(temperature=30.0, observed_at=0.0, now=31.0), "critical")
        self.assertEqual(stale.telemetry_status, "stale")
        future = model.ThermalState("n2")
        self.assertEqual(future.update(temperature=30.0, observed_at=10.0, now=0.0), "critical")

    def test_replayed_timestamp_fails_closed(self):
        state = model.ThermalState("n1")
        self.assertEqual(state.update(temperature=30.0, observed_at=100.0, now=100.0), "nominal")
        self.assertEqual(state.update(temperature=30.0, observed_at=99.0, now=101.0), "critical")
        self.assertEqual(state.telemetry_status, "replayed")
        self.assertEqual(state.last_observed_at, 100.0)

    def test_freshness_arguments_are_atomic(self):
        state = model.ThermalState("n1")
        with self.assertRaises(ValueError):
            state.update(temperature=30.0, observed_at=1.0)

    def test_invalid_initial_state_is_rejected(self):
        with self.assertRaises(ValueError):
            model.ThermalState("")
        with self.assertRaises(ValueError):
            model.ThermalState("n1", band="unknown")
        with self.assertRaises(ValueError):
            model.ThermalState("bad\nnode")
        with self.assertRaises(ValueError):
            model.ThermalState("n" * 257)

    def test_capacity_validation(self):
        state = model.ThermalState("n1")
        state.update(temperature=30.0)
        for bad in (-1, 1.5, True):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                state.ceiling(bad)

    def test_schema_and_fixture_json_are_well_formed(self):
        for path in sorted((PKG_DIR / "schemas").glob("*.json")) + sorted((PKG_DIR / "fixtures").glob("*.json")):
            with self.subTest(path=path.name):
                self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), dict)


if __name__ == "__main__":
    unittest.main()
