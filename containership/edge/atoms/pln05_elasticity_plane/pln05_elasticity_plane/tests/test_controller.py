"""Standalone unit tests for the PLN-05 elasticity algorithm.

These tests intentionally avoid importing the package ``__init__`` so they run
without the external ``pk_core`` framework.
"""
from __future__ import annotations

import importlib.util
import math
import pathlib
import subprocess
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
CONTROLLER_PATH = PKG_DIR / "controller.py"


def _load_controller_module():
    spec = importlib.util.spec_from_file_location("pln05_controller_standalone", CONTROLLER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {CONTROLLER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


m = _load_controller_module()
ElasticityController = m.ElasticityController
Limits = m.Limits


class LimitsTest(unittest.TestCase):
    def test_defaults_are_valid(self):
        lim = Limits()
        self.assertEqual((lim.floor, lim.ceiling, lim.grace_samples), (0, 10, 3))

    def test_rejects_invalid_integer_fields(self):
        for kwargs in (
            {"floor": True}, {"floor": -1}, {"floor": 1.5},
            {"ceiling": True}, {"ceiling": -1}, {"ceiling": 4.5},
            {"grace_samples": True}, {"grace_samples": 0}, {"grace_samples": 2.5},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Limits(**kwargs)

    def test_rejects_inconsistent_envelope(self):
        with self.assertRaises(ValueError):
            Limits(floor=5, ceiling=4)

    def test_rejects_invalid_thresholds(self):
        bad = [math.nan, math.inf, -math.inf, True, "0.5"]
        for value in bad:
            with self.subTest(scale_up_at=value), self.assertRaises(ValueError):
                Limits(scale_up_at=value)
        for value in bad:
            with self.subTest(scale_down_at=value), self.assertRaises(ValueError):
                Limits(scale_down_at=value)
        with self.assertRaises(ValueError):
            Limits(scale_down_at=0.8, scale_up_at=0.7)


class ControllerTest(unittest.TestCase):
    def test_initial_current_is_clamped(self):
        self.assertEqual(ElasticityController(Limits(floor=2, ceiling=8), current=100).current, 8)
        self.assertEqual(ElasticityController(Limits(floor=2, ceiling=8), current=0).current, 2)

    def test_current_rejects_non_integer(self):
        for value in (True, 2.5, "2"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ElasticityController(Limits(), current=value)

    def test_scale_up_and_ceiling_reason(self):
        c = ElasticityController(Limits(floor=0, ceiling=8), current=2)
        self.assertEqual(c.observe(0.9), (4, "scale-up"))
        self.assertEqual(c.observe(0.9), (8, "scale-up"))
        self.assertEqual(c.observe(0.9), (8, "hold: at ceiling"))

    def test_scale_down_requires_consecutive_grace_samples(self):
        c = ElasticityController(Limits(floor=0, ceiling=8, grace_samples=3), current=8)
        self.assertEqual(c.observe(0.0)[0], 8)
        self.assertEqual(c.observe(0.0)[0], 8)
        self.assertEqual(c.observe(0.0), (4, "scale-down"))
        self.assertEqual(c.suppressed, 2)

    def test_mid_band_breaks_scale_down_streak(self):
        c = ElasticityController(Limits(grace_samples=2), current=4)
        c.observe(0.0)
        self.assertEqual(c.observe(0.5), (4, "hold: within band"))
        self.assertEqual(c.observe(0.0)[0], 4)

    def test_scale_to_zero_and_floor_hold(self):
        c = ElasticityController(Limits(floor=0, ceiling=4, grace_samples=1), current=1)
        self.assertEqual(c.observe(0.0), (0, "scale-down"))
        self.assertEqual(c.observe(0.0), (0, "hold: at floor"))

    def test_non_finite_or_negative_utilisation_is_rejected(self):
        c = ElasticityController(Limits())
        for value in (True, "0.5", math.nan, math.inf, -math.inf, -0.01):
            with self.subTest(value=value), self.assertRaises(ValueError):
                c.observe(value)

    def test_oversubscription_value_is_allowed(self):
        c = ElasticityController(Limits(ceiling=4), current=1)
        self.assertEqual(c.observe(2.0), (2, "scale-up"))

    def test_lower_ceiling_is_monotonic_and_cannot_cross_floor(self):
        c = ElasticityController(Limits(floor=2, ceiling=10), current=9)
        c.lower_ceiling(4)
        self.assertEqual((c.current, c.limits.floor, c.limits.ceiling), (4, 2, 4))
        with self.assertRaises(ValueError):
            c.lower_ceiling(5)
        with self.assertRaises(ValueError):
            c.lower_ceiling(1)
        with self.assertRaises(ValueError):
            c.lower_ceiling(True)

    def test_lower_ceiling_resets_pending_low_water_streak(self):
        c = ElasticityController(Limits(floor=0, ceiling=10, grace_samples=2), current=8)
        c.observe(0.0)
        c.lower_ceiling(6)
        self.assertEqual(c.observe(0.0)[0], 6)
        self.assertEqual(c.observe(0.0)[0], 3)

    def test_target_never_escapes_active_envelope(self):
        c = ElasticityController(Limits(floor=1, ceiling=9, grace_samples=2), current=4)
        for value in [0.0, 0.0, 0.5, 0.9, 3.0, 0.0, 0.0] * 20:
            target, _ = c.observe(value)
            self.assertGreaterEqual(target, c.limits.floor)
            self.assertLessEqual(target, c.limits.ceiling)

    def test_standalone_tests_survive_optimised_mode(self):
        code = (
            "import importlib.util,sys; p=%r; "
            "s=importlib.util.spec_from_file_location('ctrl_o',p); "
            "m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m); "
            "c=m.ElasticityController(m.Limits(floor=0,ceiling=4,grace_samples=1),current=1); "
            "print(c.observe(0.0))"
        ) % str(CONTROLLER_PATH)
        out = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "(0, 'scale-down')")


if __name__ == "__main__":
    unittest.main()
