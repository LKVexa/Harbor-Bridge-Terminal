"""Standalone safety tests for the INV-32 resource model (stdlib only)."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import importlib.util
import pathlib
import sys
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
MODEL_PATH = PKG_DIR / "model.py"
spec = importlib.util.spec_from_file_location("inv32_elastic_virtualization_model_test", MODEL_PATH)
model = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = model
assert spec.loader is not None
spec.loader.exec_module(model)


class ModelTest(unittest.TestCase):
    def host(self, total=4096, **kwargs):
        host = model.ElasticHost("n1", total_mib=total, **kwargs)
        host.add(model.Guest("g1", "t1", memory_mib=1024, floor_mib=256, ceiling_mib=2048))
        return host

    def test_host_and_guest_validation(self):
        with self.assertRaises(ValueError):
            model.ElasticHost("", 1024)
        with self.assertRaises(ValueError):
            model.ElasticHost("n", 1024, reserve_fraction=0)
        with self.assertRaises(TypeError):
            model.ElasticHost("n", True)
        with self.assertRaises(TypeError):
            model.Guest("g", "t", True, 0, 10)
        with self.assertRaises(ValueError):
            model.Guest("g", "t", 100, 101, 200)
        with self.assertRaises(TypeError):
            model.Guest("g", "t", 100, 0, 200, cooperative=1)

    def test_guest_is_immutable(self):
        guest = model.Guest("g", "t", 100, 0, 200)
        with self.assertRaises(FrozenInstanceError):
            guest.memory_mib = 150

    def test_reserve_rounds_up(self):
        host = model.ElasticHost("n", 101, reserve_fraction=0.10)
        self.assertEqual(host.reserve_mib, 11)
        self.assertEqual(host.free_mib, 90)

    def test_duplicate_and_reserve_admission_are_refused(self):
        host = model.ElasticHost("n", 1024)
        guest = model.Guest("g", "t", 900, 100, 900)
        host.add(guest)
        with self.assertRaises(ValueError):
            host.add(guest)
        with self.assertRaises(model.ReserveBreach):
            host.add(model.Guest("g2", "t", 22, 0, 22))

    def test_memory_bounds_ceiling_clamp_and_original_request(self):
        host = self.host()
        with self.assertRaises(model.FloorBreach):
            host.adjust_memory("g1", 255)
        record = host.adjust_memory("g1", 9999, operation_id="clamp")
        self.assertEqual(record["requested_mib"], 9999)
        self.assertEqual(record["target_mib"], 2048)
        self.assertTrue(record["clamped_to_ceiling"])
        self.assertEqual(host.guests["g1"].memory_mib, 2048)

    def test_noncooperative_guest_blocks_reclaim_but_not_growth(self):
        host = model.ElasticHost("n", 4096)
        host.add(model.Guest("g", "t", 1024, 256, 2048, cooperative=False))
        shrink = host.adjust_memory("g", 512, honoured=True, operation_id="shrink")
        self.assertFalse(shrink["honoured"])
        self.assertEqual(host.guests["g"].memory_mib, 1024)
        grow = host.adjust_memory("g", 1536, honoured=True, operation_id="grow")
        self.assertTrue(grow["honoured"])
        self.assertEqual(host.guests["g"].memory_mib, 1536)

    def test_operation_id_is_idempotent_and_conflicts_are_rejected(self):
        host = self.host()
        first = host.adjust_memory("g1", 1536, operation_id="same")
        second = host.adjust_memory("g1", 1536, operation_id="same")
        self.assertEqual(first, second)
        with self.assertRaises(model.ReplayConflict):
            host.adjust_memory("g1", 1400, operation_id="same")

    def test_stale_memory_rollback_is_fenced(self):
        host = self.host()
        first = host.adjust_memory("g1", 1536, operation_id="first")
        later = host.adjust_memory("g1", 1400, operation_id="later")
        with self.assertRaises(model.StaleAdjustment):
            host.revert(first, operation_id="undo-first")
        self.assertEqual(host.revert(later, operation_id="undo-later"), 1536)

    def test_vcpu_adjustment_is_logged_and_reverts_vcpu_only(self):
        host = self.host()
        before_memory = host.guests["g1"].memory_mib
        record = host.adjust_vcpus("g1", 3, operation_id="cpu")
        self.assertEqual(record["kind"], "vcpu")
        self.assertEqual(host.revert(record, operation_id="undo-cpu"), 1)
        self.assertEqual(host.guests["g1"].memory_mib, before_memory)
        self.assertEqual(host.guests["g1"].vcpus, 1)

    def test_forged_v2_record_is_rejected(self):
        host = self.host()
        record = host.adjust_memory("g1", 1536, operation_id="grow")
        forged = dict(record)
        forged["reversible_to"] = 256
        with self.assertRaises(model.InvalidAdjustmentRecord):
            host.revert(forged)

    def test_legacy_record_cannot_escape_current_bounds(self):
        host = self.host()
        host.adjust_memory("g1", 1536, operation_id="grow")
        malicious = {
            "schema": model.LEGACY_RESOURCE_ADJUSTMENT_SCHEMA,
            "guest": "g1",
            "from_mib": 1024,
            "applied_mib": 1536,
            "reversible_to": 1,
        }
        with self.assertRaises(model.InvalidAdjustmentRecord):
            host.revert(malicious)

    def test_history_is_hash_chained_and_returned_record_is_detached(self):
        host = self.host()
        record = host.adjust_memory("g1", 1536, operation_id="grow")
        self.assertTrue(host.verify_history())
        record["applied_mib"] = 1
        self.assertTrue(host.verify_history())
        self.assertEqual(host.guests["g1"].memory_mib, 1536)

    def test_tampered_history_fails_closed(self):
        host = self.host()
        host.history[0]["applied_mib"] = 1
        self.assertFalse(host.verify_history())
        with self.assertRaises(model.AuditIntegrityError):
            host.adjust_memory("g1", 1200)

    def test_host_snapshot_matches_live_accounting(self):
        host = self.host()
        snapshot = host.host_snapshot()
        self.assertEqual(snapshot["total_mib"], 4096)
        self.assertEqual(snapshot["allocated_mib"], 1024)
        self.assertEqual(snapshot["free_mib"], host.free_mib)
        self.assertEqual(snapshot["audit_head"], host.audit_head)

    def test_free_page_reports_are_bounded(self):
        host = self.host()
        event = host.report_free_pages("g1", 128)
        self.assertEqual(event["free_pages_mib"], 128)
        with self.assertRaises(ValueError):
            host.report_free_pages("g1", 1025)
        self.assertEqual(host.guests["g1"].memory_mib, 1024)

    def test_registry_tampering_is_detected(self):
        host = self.host()
        host.guests["evil"] = host.guests["g1"]
        with self.assertRaises(model.StateIntegrityError):
            host.adjust_memory("g1", 1200)

    def test_structured_error_payload(self):
        host = self.host(total=1200)
        with self.assertRaises(model.ReserveBreach) as ctx:
            host.adjust_memory("g1", 1100)
        payload = ctx.exception.to_dict()
        self.assertEqual(payload["code"], "reserve_breach")
        self.assertIn("details", payload)

    def test_concurrent_mutations_serialize_and_preserve_audit_chain(self):
        host = self.host(total=8192)
        errors = []

        def worker(worker_id):
            try:
                for index in range(25):
                    target = 1200 if (worker_id + index) % 2 else 1300
                    host.adjust_memory(
                        "g1", target, operation_id=f"w{worker_id}-{index}"
                    )
            except Exception as exc:  # pragma: no cover - reported by assertion below
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertTrue(host.verify_history())
        self.assertIn(host.guests["g1"].memory_mib, {1200, 1300})


if __name__ == "__main__":
    unittest.main()
