"""INV-08 conformance and dependency-free model tests.

Run from the folder that contains this package::

    python inv08_dynamic_infrastructure_model/tests/test_component.py

The model/version tests always run.  ``pk_core`` integration tests run only when
``pk_core`` is importable; use ``preflight.py`` for an explicit dependency gate.
"""
from __future__ import annotations

import importlib
import math
import os
import pathlib
import subprocess
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
for path in filter(None, [os.environ.get("PK_CORE_PATH"), str(ROOT.parent), str(ROOT)]):
    if path not in sys.path:
        sys.path.insert(0, path)

PKG_NAME = PKG_DIR.name if ROOT.name != "pk_components" else "pk_components." + PKG_DIR.name
pkg = importlib.import_module(PKG_NAME)
Pool = pkg.Pool
PoolInvariantError = pkg.PoolInvariantError

try:
    import pk_core  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - environment dependent
    pk_core = None

KNOWN_PARTIAL: list[str] = []


class StandaloneModelTest(unittest.TestCase):
    def test_version_files_agree(self):
        self.assertEqual(pkg.__version__, "4.2.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text(encoding="utf-8").strip(), "4.2.0")

    def test_hard_bounds_and_safe_busy_reclaim(self):
        pool = Pool(min_nodes=1, max_nodes=5)
        self.assertEqual(pool.tick(0, 10**100)["size"], 5)
        busy = sorted(pool.nodes)[:2]
        for node_id in busy:
            pool.set_busy(node_id)
        result = pool.tick(20, 0)
        self.assertEqual(result["size"], 2)
        self.assertTrue(all(node_id in pool.nodes for node_id in busy))
        self.assertEqual(sorted(result["renewed"]), busy)

    def test_expired_pool_is_topped_back_to_minimum(self):
        pool = Pool(min_nodes=3, max_nodes=5, lease_ttl=1)
        pool.tick(0, 0)
        result = pool.tick(2, 0)
        self.assertEqual(result["size"], 3)
        self.assertEqual(result["added"], 3)
        self.assertEqual(len(result["reclaimed"]), 3)

    def test_non_finite_and_boolean_inputs_are_rejected(self):
        pool = Pool(0, 2)
        for demand in [math.nan, math.inf, -math.inf, True, -1]:
            with self.subTest(demand=demand), self.assertRaises(ValueError):
                pool.tick(0, demand)
        for now in [math.nan, math.inf, True]:
            with self.subTest(now=now), self.assertRaises(ValueError):
                pool.tick(now, 0)

    def test_time_cannot_move_backwards(self):
        pool = Pool(1, 2)
        pool.tick(10, 1)
        before = pool.snapshot()
        with self.assertRaises(ValueError):
            pool.tick(9, 1)
        self.assertEqual(pool.snapshot(), before)

    def test_invalid_restored_state_fails_closed_without_mutation(self):
        pool = Pool(0, 2)
        pool.nodes["poison"] = {"expires": math.nan, "busy": False}
        before_hours = pool.node_hours
        with self.assertRaises(PoolInvariantError):
            pool.tick(1, 0)
        self.assertEqual(pool.node_hours, before_hours)
        self.assertIn("poison", pool.nodes)

    def test_restored_generated_ids_do_not_collide(self):
        pool = Pool(
            0,
            4,
            nodes={"node-9": {"expires": 100, "busy": False}},
        )
        result = pool.tick(0, 8)
        self.assertEqual(result["size"], 2)
        self.assertIn("node-9", pool.nodes)
        self.assertIn("node-10", pool.nodes)

    def test_node_hour_accounting_accepts_explicit_interval(self):
        pool = Pool(2, 2)
        pool.tick(0, 1, elapsed_hours=0)
        pool.tick(1, 1, elapsed_hours=0.5)
        self.assertEqual(pool.node_hours, 1.0)

    def test_constructor_rejects_invalid_bounds(self):
        for args in [(True, 2), (0, True), (-1, 2), (3, 2)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                Pool(*args)
        with self.assertRaises(ValueError):
            Pool(0, 2, per_node=0)
        with self.assertRaises(ValueError):
            Pool(0, 2, lease_ttl=0)


@unittest.skipIf(pk_core is None, "pk_core not importable; strict preflight will flag this")
class PkCoreConformanceTest(unittest.TestCase):
    def _load_component(self):
        return importlib.import_module(PKG_NAME).COMPONENT()

    def test_all_100_requirements_answered_by_framework(self):
        comp = self._load_component()
        findings = [finding for band in comp.assess_all().values() for finding in band]
        self.assertEqual(len(findings), 100)
        self.assertEqual(len({finding.check_id for finding in findings}), 100)
        unexpected = sorted(
            finding.check_id
            for finding in findings
            if not finding.status.passing
            and finding.check_id not in KNOWN_PARTIAL
            and "not installed" not in finding.note
        )
        self.assertEqual(unexpected, [])
        self.assertFalse([finding for finding in findings if finding.status.value == "blocked"])

    def test_checks_survive_optimised_mode(self):
        code = (
            "import sys; sys.path[:0]=%r; import importlib; "
            "m=importlib.import_module(%r); c=m.COMPONENT(); "
            "print(sum(len(v) for v in c.assess_all().values()))"
        ) % ([path for path in sys.path[:3]], PKG_NAME)
        out = subprocess.run(
            [sys.executable, "-O", "-c", code],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            check=False,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "100")


if __name__ == "__main__":
    unittest.main(verbosity=2)
