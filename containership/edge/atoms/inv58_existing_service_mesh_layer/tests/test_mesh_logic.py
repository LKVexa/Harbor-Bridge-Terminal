"""Dependency-free tests for INV-58 retry, identity, migration, and bypass logic."""
from __future__ import annotations

import importlib.util
import pathlib
import threading
import unittest
import sys

MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "mesh_logic.py"
SPEC = importlib.util.spec_from_file_location("inv58_mesh_logic_under_test", MODULE_PATH)
mesh = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = mesh
SPEC.loader.exec_module(mesh)


class RetryReconciliationTest(unittest.TestCase):
    def test_multiplication_is_removed_even_when_product_fits_budget(self):
        r = mesh.reconcile("a->b", 2, 2, budget=4)
        self.assertEqual(r["owner"], "app")
        self.assertEqual((r["app"], r["mesh"]), (2, 1))
        self.assertEqual(r["effective_attempts"], 2)

    def test_mesh_keeps_ownership_when_only_mesh_retries(self):
        r = mesh.reconcile("a->b", 1, 9, budget=3)
        self.assertEqual(r["owner"], "mesh")
        self.assertEqual((r["app"], r["mesh"]), (1, 3))
        self.assertLessEqual(r["effective_attempts"], r["budget"])

    def test_budget_one_disables_all_retries(self):
        r = mesh.reconcile("a->b", 5, 5, budget=1)
        self.assertEqual((r["owner"], r["app"], r["mesh"]), ("none", 1, 1))

    def test_invalid_inputs_fail_closed(self):
        for bad in (0, -1, True, 1.5, "3"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    mesh.reconcile("a->b", bad, 1, 3)
        for route in ("", " a->b", "a->b\n"):
            with self.subTest(route=route):
                with self.assertRaises(ValueError):
                    mesh.reconcile(route, 1, 1, 3)


class IdentityTest(unittest.TestCase):
    def test_valid_spiffe_identity(self):
        self.assertEqual(
            mesh.map_identity("spiffe://estate.local/ns/shop/sa/orders", "estate.local"),
            "runtime:ns/shop/sa/orders",
        )

    def test_ambiguous_or_foreign_identities_fail_closed(self):
        bad = [
            "spiffe://evil.local/ns/shop/sa/orders",
            "spiffe://estate.local/",
            "spiffe://estate.local/ns//orders",
            "spiffe://estate.local/ns/../admin",
            "spiffe://estate.local/ns/%2e%2e/admin",
            "spiffe://estate.local/ns/orders?role=admin",
            "https://estate.local/ns/orders",
        ]
        for san in bad:
            with self.subTest(san=san):
                with self.assertRaises(mesh.Unmappable):
                    mesh.map_identity(san, "estate.local")


class BypassDetectorTest(unittest.TestCase):
    def test_evidence_is_bounded(self):
        det = mesh.BypassDetector({"payments"}, max_flags=2)
        for i in range(4):
            self.assertTrue(det.observe(f"src-{i}", "payments", False))
        self.assertEqual(det.snapshot(), (("src-2", "payments"), ("src-3", "payments")))

    def test_meshed_destination_set_is_bounded(self):
        with self.assertRaises(ValueError):
            mesh.BypassDetector({"a", "b"}, max_destinations=1)

    def test_mtls_must_be_boolean(self):
        det = mesh.BypassDetector({"payments"})
        with self.assertRaises(ValueError):
            det.observe("orders", "payments", "false")

    def test_concurrent_observation_remains_bounded(self):
        det = mesh.BypassDetector({"payments"}, max_flags=64)
        threads = [threading.Thread(target=det.observe, args=(f"src-{i}", "payments", False)) for i in range(250)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(det.snapshot()), 64)


class MigrationRegistryTest(unittest.TestCase):
    def test_route_capacity_is_bounded(self):
        reg = mesh.RoutePolicyRegistry(max_routes=1)
        reg.migrate_route("a->b", 2, 1, 2)
        with self.assertRaises(OverflowError):
            reg.migrate_route("c->d", 2, 1, 2)
        self.assertEqual(reg.revision, 1)

    def test_copy_on_write_migration_and_revision(self):
        reg = mesh.RoutePolicyRegistry()
        first = reg.migrate_route("orders->payments", 3, 3, 3)
        second = reg.migrate_route("catalog->search", 1, 2, 2)
        self.assertEqual((first["revision"], second["revision"], reg.revision), (1, 2, 2))
        rev, snapshot = reg.snapshot()
        self.assertEqual(rev, 2)
        self.assertEqual(snapshot["orders->payments"]["mesh"], 1)
        snapshot["orders->payments"]["mesh"] = 99
        self.assertEqual(reg.get("orders->payments")["mesh"], 1)


if __name__ == "__main__":
    unittest.main()
