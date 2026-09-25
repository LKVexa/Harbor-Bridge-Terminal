"""Dependency-free runtime and repository tests for PLN-06."""
from __future__ import annotations

import concurrent.futures
import json
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pln06_data_plane as pkg


class RuntimeTest(unittest.TestCase):
    def setUp(self):
        self.plane = pkg.DataPlane({"s": {"public", "pii"}}, inflight_limit=2)

    def test_version_files_agree(self):
        self.assertEqual(pkg.__version__, "4.3.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text(encoding="utf-8").strip(), pkg.__version__)

    def test_checklist_has_100_unique_ordered_requirements(self):
        data = json.loads((PKG_DIR / "CHECKLIST.json").read_text(encoding="utf-8"))
        self.assertEqual(data["item_count"], 100)
        self.assertEqual(len(data["items"]), 100)
        self.assertEqual([i["ordinal"] for i in data["items"]], list(range(1, 101)))
        ids = [i["check_id"] for i in data["items"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_legacy_size_bands_and_locality_floor(self):
        self.assertEqual(pkg.DataPlane.tier_for(0), "inline")
        self.assertEqual(pkg.DataPlane.tier_for(64 * 1024), "inline")
        self.assertEqual(pkg.DataPlane.tier_for(64 * 1024 + 1), "local")
        self.assertEqual(pkg.DataPlane.tier_for(64 * 1024 * 1024), "local")
        self.assertEqual(pkg.DataPlane.tier_for(64 * 1024 * 1024 + 1), "bulk")
        self.assertEqual(pkg.DataPlane.tier_for(1, "same_node"), "local")
        self.assertEqual(pkg.DataPlane.tier_for(1, "remote"), "bulk")

    def test_invalid_configuration_and_request_types_fail_closed(self):
        for bad in (True, False, 0, -1, 1.5, "4"):
            with self.subTest(inflight_limit=bad):
                with self.assertRaises(pkg.InvalidRequest):
                    pkg.DataPlane({"s": {"public"}}, inflight_limit=bad)
        for bad in (True, -1, 1.25, "1"):
            with self.subTest(size=bad):
                with self.assertRaises(pkg.InvalidRequest):
                    pkg.DataPlane.tier_for(bad)
        with self.assertRaises(pkg.InvalidRequest):
            pkg.DataPlane({"s": "public"})
        with self.assertRaises(pkg.InvalidRequest):
            self.plane.admit(tenant="", workload="w", size=1, classification="public", destination="s")
        with self.assertRaises(pkg.InvalidRequest):
            self.plane.admit(tenant="t", workload="w", size=1, classification="public", destination="s", locality="moon")

    def test_residency_is_copied_and_refusal_is_structured(self):
        policy = {"s": {"public"}}
        plane = pkg.DataPlane(policy)
        policy["s"].add("pii")
        self.assertFalse(plane.permitted("s", "pii"))
        with self.assertRaises(pkg.ResidencyViolation) as ctx:
            plane.admit(tenant="t", workload="w", size=1, classification="pii", destination="s")
        detail = ctx.exception.as_dict()
        self.assertEqual(detail["code"], "PK_RESIDENCY_VIOLATION")
        self.assertFalse(detail["retryable"])

    def test_digest_validation_and_normalization(self):
        decision = self.plane.admit(
            tenant="t", workload="w", size=1, classification="public", destination="s",
            digest="A" * 64,
        )
        self.assertEqual(decision["digest"], "a" * 64)
        with self.assertRaises(pkg.InvalidRequest):
            self.plane.admit(
                tenant="t", workload="w", size=1, classification="public", destination="s",
                digest="not-a-digest",
            )

    def test_backpressure_completion_idempotency_and_tamper_rejection(self):
        args = dict(tenant="t", workload="w", size=1024 * 1024,
                    classification="public", destination="s")
        first = self.plane.admit(**args)
        second = self.plane.admit(**args)
        with self.assertRaises(pkg.Backpressure) as ctx:
            self.plane.admit(**args)
        self.assertTrue(ctx.exception.as_dict()["retryable"])
        forged = dict(first)
        forged["tenant"] = "other"
        with self.assertRaises(pkg.InvalidCompletion):
            self.plane.complete(forged)
        self.assertEqual(self.plane.inflight, 2)
        self.assertTrue(self.plane.complete(first))
        self.assertFalse(self.plane.complete(first))
        self.assertTrue(self.plane.cancel(second))
        self.assertEqual(self.plane.inflight, 0)
        metrics = self.plane.metrics()
        self.assertEqual(metrics["backpressure_events"], 1)
        self.assertEqual(metrics["completed"], 1)
        self.assertEqual(metrics["cancelled"], 1)

    def test_concurrent_admission_never_oversubscribes_limit(self):
        plane = pkg.DataPlane({"s": {"public"}}, inflight_limit=4)
        args = dict(tenant="t", workload="w", size=1024 * 1024,
                    classification="public", destination="s")

        def attempt(_):
            try:
                return plane.admit(**args)
            except pkg.Backpressure:
                return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            results = list(pool.map(attempt, range(64)))
        admitted = [r for r in results if r is not None]
        self.assertEqual(len(admitted), 4)
        self.assertEqual(plane.inflight, 4)


    def test_per_tenant_quota_prevents_single_tenant_monopoly(self):
        plane = pkg.DataPlane(
            {"s": {"public"}}, inflight_limit=4, per_tenant_inflight_limit=2
        )
        args = dict(workload="w", size=1024 * 1024, classification="public", destination="s")
        plane.admit(tenant="a", **args)
        plane.admit(tenant="a", **args)
        with self.assertRaises(pkg.Backpressure) as ctx:
            plane.admit(tenant="a", **args)
        self.assertEqual(ctx.exception.details["scope"], "tenant")
        # Another tenant can still use remaining global capacity.
        plane.admit(tenant="b", **args)
        self.assertEqual(plane.inflight, 3)

    def test_residency_update_is_atomic_and_tracks_provenance(self):
        plane = pkg.DataPlane(
            {"s": {"public"}},
            config_revision="r1",
            config_author="bootstrapper",
        )
        live = plane.admit(
            tenant="t", workload="w", size=1024 * 1024,
            classification="public", destination="s",
        )
        with self.assertRaises(pkg.InvalidRequest):
            plane.replace_residency({"s": {"pii"}}, revision="r2", author="operator")
        self.assertTrue(plane.permitted("s", "public"))
        self.assertEqual(plane.config_snapshot()["revision"], "r1")
        plane.complete(live)
        plane.replace_residency({"s": {"pii"}}, revision="r2", author="operator")
        config = plane.config_snapshot()
        self.assertEqual(config["revision"], "r2")
        self.assertEqual(config["author"], "operator")
        self.assertFalse(plane.permitted("s", "public"))
        self.assertTrue(plane.permitted("s", "pii"))

    def test_health_exposes_version_readiness_and_active_revision(self):
        plane = pkg.DataPlane({"s": {"public"}}, config_revision="policy-7")
        health = plane.health()
        self.assertEqual(health["schema"], "PK_DATA_PLANE_HEALTH/1")
        self.assertEqual(health["element"], "PLN-06")
        self.assertEqual(health["version"], pkg.__version__)
        self.assertTrue(health["healthy"])
        self.assertTrue(health["ready"])
        self.assertEqual(health["config_revision"], "policy-7")

    def test_public_schema_artifacts_exist_and_are_versioned(self):
        schema_ids = {
            "pk_transfer_v1.schema.json": "PK_TRANSFER/1",
            "pk_residency_v1.schema.json": "PK_RESIDENCY/1",
            "pk_transport_tier_v1.schema.json": "PK_TRANSPORT_TIER/1",
            "pk_data_plane_metrics_v1.schema.json": "PK_DATA_PLANE_METRICS/1",
            "pk_data_plane_health_v1.schema.json": "PK_DATA_PLANE_HEALTH/1",
        }
        for name, schema_id in schema_ids.items():
            with self.subTest(schema=name):
                data = json.loads((PKG_DIR / "schemas" / name).read_text(encoding="utf-8"))
                self.assertEqual(data["$id"], schema_id)
                self.assertEqual(data["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_metrics_snapshot_is_detached(self):
        self.plane.admit(tenant="t", workload="w", size=1, classification="public", destination="s")
        snap = self.plane.metrics()
        snap["bytes_by_tier"]["inline"] = 999
        self.assertEqual(self.plane.control_bytes, 1)


if __name__ == "__main__":
    unittest.main()
