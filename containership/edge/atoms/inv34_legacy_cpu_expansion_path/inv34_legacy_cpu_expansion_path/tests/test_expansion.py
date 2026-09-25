"""Standalone stdlib tests for the INV-34 CPU expansion state machine."""
from __future__ import annotations

import pathlib
import sys
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inv34_legacy_cpu_expansion_path.expansion import (  # noqa: E402
    CpuExpansionController,
    ExpansionDisabled,
    GuestLimitExceeded,
    HostCapacityExceeded,
    HotplugUnsupported,
    IdempotencyConflict,
    InvalidRequest,
    ObservationAheadOfDesired,
    ObservationRegression,
    REQUEST_SCHEMA,
    RESULT_SCHEMA,
    STATUS_SCHEMA,
    ShrinkNotSupported,
    StaleGeneration,
    VmCpuState,
)


class StateValidationTest(unittest.TestCase):
    def test_valid_state_and_status_schema(self):
        state = VmCpuState("vm-1", 2, 2, 8, 16)
        self.assertTrue(state.converged)
        self.assertEqual(state.pending_vcpus, 0)
        status = state.as_dict()
        self.assertEqual(status["schema"], STATUS_SCHEMA)
        self.assertEqual(status["observed_vcpus"], 2)

    def test_rejects_malformed_identifiers_and_boolean_counts(self):
        for vm_id in ("", " vm", "vm id", "vm\n1"):
            with self.subTest(vm_id=repr(vm_id)), self.assertRaises(InvalidRequest):
                VmCpuState(vm_id, 1, 1, 2, 2)
        with self.assertRaises(InvalidRequest):
            VmCpuState("vm", True, 1, 2, 2)

    def test_rejects_impossible_initial_state(self):
        with self.assertRaises(InvalidRequest):
            VmCpuState("vm", 4, 2, 8, 8)
        with self.assertRaises(InvalidRequest):
            VmCpuState("vm", 2, 9, 8, 16)
        # Desired may temporarily exceed newly discovered host capacity; that represents
        # a degraded pending request rather than an impossible state.
        degraded = VmCpuState("vm", 2, 9, 16, 8)
        self.assertEqual(degraded.desired_vcpus, 9)


class ExpansionControllerTest(unittest.TestCase):
    def make_controller(self, **overrides):
        params = dict(
            vm_id="vm-1",
            observed_vcpus=2,
            desired_vcpus=2,
            max_vcpus=8,
            host_capacity_vcpus=8,
            acpi_hotplug_supported=True,
            guest_hotplug_supported=True,
            expansion_enabled=True,
            generation=0,
        )
        params.update(overrides)
        return CpuExpansionController(VmCpuState(**params), replay_cache_size=8)

    def test_accept_then_observe_progress_without_false_completion(self):
        controller = self.make_controller()
        result = controller.request_expansion("req-1", 4, expected_generation=0)
        self.assertEqual(result.as_dict()["schema"], RESULT_SCHEMA)
        self.assertEqual(result.status, "accepted")
        self.assertEqual(result.added_vcpus, 2)
        self.assertEqual(controller.snapshot().observed_vcpus, 2)
        self.assertEqual(controller.snapshot().desired_vcpus, 4)
        self.assertFalse(controller.snapshot().converged)
        self.assertEqual(controller.record_observation(3).pending_vcpus, 1)
        self.assertTrue(controller.record_observation(4).converged)

    def test_noop_is_safe_when_already_at_target(self):
        controller = self.make_controller(acpi_hotplug_supported=False, guest_hotplug_supported=False)
        result = controller.request_expansion("req-noop", 2)
        self.assertEqual(result.status, "noop")
        self.assertEqual(result.added_vcpus, 0)
        self.assertEqual(result.generation, 0)

    def test_rejects_shrink(self):
        with self.assertRaises(ShrinkNotSupported):
            self.make_controller().request_expansion("req-shrink", 1)

    def test_rejects_guest_limit(self):
        with self.assertRaises(GuestLimitExceeded):
            self.make_controller(max_vcpus=4, host_capacity_vcpus=8).request_expansion("req-max", 5)

    def test_rejects_host_capacity_as_retryable(self):
        with self.assertRaises(HostCapacityExceeded) as ctx:
            self.make_controller(max_vcpus=8, host_capacity_vcpus=4).request_expansion("req-host", 5)
        self.assertTrue(ctx.exception.retryable)
        self.assertEqual(ctx.exception.as_dict()["code"], "HOST_CAPACITY_EXCEEDED")

    def test_rejects_disabled_or_unsupported_expansion(self):
        with self.assertRaises(ExpansionDisabled):
            self.make_controller(expansion_enabled=False).request_expansion("req-off", 3)
        with self.assertRaises(HotplugUnsupported):
            self.make_controller(acpi_hotplug_supported=False).request_expansion("req-no-acpi", 3)
        with self.assertRaises(HotplugUnsupported):
            self.make_controller(guest_hotplug_supported=False).request_expansion("req-no-guest", 3)

    def test_generation_guard(self):
        with self.assertRaises(StaleGeneration):
            self.make_controller(generation=3).request_expansion("req-stale", 3, expected_generation=2)

    def test_idempotent_replay_and_conflict(self):
        controller = self.make_controller()
        first = controller.request_expansion("req-idem", 4, expected_generation=0)
        replay = controller.request_expansion("req-idem", 4, expected_generation=0)
        self.assertIs(first, replay)
        with self.assertRaises(IdempotencyConflict):
            controller.request_expansion("req-idem", 5, expected_generation=0)

    def test_observation_guards(self):
        controller = self.make_controller()
        controller.request_expansion("req-obs", 4)
        controller.record_observation(3)
        with self.assertRaises(ObservationRegression):
            controller.record_observation(2)
        with self.assertRaises(ObservationAheadOfDesired):
            controller.record_observation(5)

    def test_capacity_update_refuses_invalidation(self):
        controller = self.make_controller()
        controller.request_expansion("req-cap", 6)
        degraded = controller.update_host_capacity(5)
        self.assertEqual(degraded.host_capacity_vcpus, 5)
        self.assertEqual(degraded.desired_vcpus, 6)
        with self.assertRaises(InvalidRequest):
            controller.update_host_capacity(1)
        updated = controller.update_host_capacity(10)
        self.assertEqual(updated.host_capacity_vcpus, 10)

    def test_request_schema_constant(self):
        self.assertEqual(REQUEST_SCHEMA, "PK_CPU_EXPANSION_REQUEST/1")

    def test_generation_is_not_artificially_bounded_by_vcpu_limit(self):
        controller = self.make_controller(generation=100_000)
        result = controller.request_expansion("req-old-controller", 3, expected_generation=100_000)
        self.assertEqual(result.generation, 100_001)

    def test_threaded_duplicate_request_is_single_state_change(self):
        controller = self.make_controller()
        results = []
        errors = []
        barrier = threading.Barrier(8)

        def worker():
            try:
                barrier.wait()
                results.append(controller.request_expansion("req-thread", 4))
            except Exception as exc:  # pragma: no cover - diagnostic collection
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 8)
        self.assertTrue(all(result is results[0] for result in results))
        self.assertEqual(controller.snapshot().generation, 1)
        self.assertEqual(controller.snapshot().desired_vcpus, 4)

    def test_replay_cache_is_bounded(self):
        controller = CpuExpansionController(VmCpuState("vm", 2, 2, 8, 8), replay_cache_size=2)
        controller.request_expansion("a", 2)
        controller.request_expansion("b", 2)
        controller.request_expansion("c", 2)
        # 'a' was evicted, so reusing it now is a fresh no-op rather than an unbounded retained replay.
        again = controller.request_expansion("a", 2)
        self.assertEqual(again.status, "noop")


if __name__ == "__main__":
    unittest.main()
