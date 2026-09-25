"""Standalone unit tests for the INV-40 runtime model (no pk_core required)."""
from __future__ import annotations

import pathlib
import subprocess
import sys
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

from runtime import (  # noqa: E402
    BOOT_BUDGET_MS,
    FOOTPRINT_CEILING_MIB,
    FULL_DEVICE_MODEL,
    DeviceConflict,
    DeviceLeaseRegistry,
    FootprintExceeded,
    FullVm,
    InvalidVmState,
    PrimitiveRequired,
    device_conflict,
)


def shared_device_map(prefix: str = "shared") -> dict[str, str]:
    return {kind: f"{prefix}:{kind}" for kind in FULL_DEVICE_MODEL}


class RuntimeValidationTest(unittest.TestCase):
    def test_identity_and_capacity_validation(self):
        for args in [
            ("", "tenant", 512),
            ("vm", "", 512),
            ("vm", "tenant", 0),
            ("vm", "tenant", -1),
        ]:
            with self.subTest(args=args), self.assertRaises((TypeError, ValueError)):
                FullVm(*args)
        with self.assertRaises(TypeError):
            FullVm("vm", "tenant", True)

    def test_complete_device_model_required(self):
        with self.assertRaises(ValueError):
            FullVm("vm", "tenant", 512, devices=frozenset({"virtio-net"}))

    def test_device_instance_mapping_must_be_complete_and_unique(self):
        mapping = shared_device_map()
        mapping.pop("tpm")
        with self.assertRaises(ValueError):
            FullVm("vm", "tenant", 512, device_instances=mapping)

        mapping = shared_device_map()
        first = next(iter(mapping.values()))
        keys = list(mapping)
        mapping[keys[1]] = first
        with self.assertRaises(ValueError):
            FullVm("vm", "tenant", 512, device_instances=mapping)


class RuntimeLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.registry = DeviceLeaseRegistry()
        self.vm = FullVm("vm-1", "tenant-a", 1024)

    def test_hardware_primitive_is_mandatory(self):
        with self.assertRaises(PrimitiveRequired):
            self.vm.start(
                primitive_usable=False,
                elapsed_ms=100,
                resident_mib=512,
                registry=self.registry,
            )
        self.assertEqual(self.vm.state, "created")
        self.assertEqual(self.registry.active_claim_count(), 0)

    def test_operational_errors_are_machine_readable(self):
        try:
            self.vm.start(
                primitive_usable=False,
                elapsed_ms=100,
                resident_mib=512,
                registry=self.registry,
            )
        except PrimitiveRequired as exc:
            payload = exc.as_dict()
        else:  # pragma: no cover
            self.fail("PrimitiveRequired not raised")
        self.assertEqual(payload["schema"], "PK_FULL_VM_ERROR/1")
        self.assertEqual(payload["code"], "PK_FULL_VM_PRIMITIVE_REQUIRED")

    def test_primitive_flag_is_strict_boolean(self):
        with self.assertRaises(TypeError):
            self.vm.start(
                primitive_usable=1,
                elapsed_ms=100,
                resident_mib=512,
                registry=self.registry,
            )

    def test_footprint_ceiling_fails_closed_before_leasing(self):
        with self.assertRaises(FootprintExceeded):
            self.vm.start(
                primitive_usable=True,
                elapsed_ms=100,
                resident_mib=FOOTPRINT_CEILING_MIB + 1,
                registry=self.registry,
            )
        self.assertEqual(self.vm.state, "created")
        self.assertEqual(self.registry.active_claim_count(), 0)

    def test_start_stop_restart_destroy_lifecycle(self):
        result = self.vm.start(
            primitive_usable=True,
            elapsed_ms=400,
            resident_mib=700,
            registry=self.registry,
        )
        self.assertEqual(result["state"], "running")
        self.assertEqual(self.vm.state, "running")
        self.assertEqual(self.registry.active_claim_count(), len(FULL_DEVICE_MODEL))

        with self.assertRaises(InvalidVmState):
            self.vm.start(
                primitive_usable=True,
                elapsed_ms=400,
                resident_mib=700,
                registry=self.registry,
            )

        stopped = self.vm.stop()
        self.assertFalse(stopped["destroyed"])
        self.assertEqual(self.registry.active_claim_count(), 0)

        self.vm.start(
            primitive_usable=True,
            elapsed_ms=450,
            resident_mib=710,
            registry=self.registry,
        )
        destroyed = self.vm.destroy()
        self.assertTrue(destroyed["destroyed"])
        self.assertEqual(self.registry.active_claim_count(), 0)
        self.assertTrue(self.vm.destroy()["idempotent"])
        with self.assertRaises(InvalidVmState):
            self.vm.start(
                primitive_usable=True,
                elapsed_ms=1,
                resident_mib=1,
                registry=self.registry,
            )

    def test_boot_budget_is_reported_as_degraded_not_hidden(self):
        result = self.vm.start(
            primitive_usable=True,
            elapsed_ms=BOOT_BUDGET_MS + 1,
            resident_mib=512,
            registry=self.registry,
        )
        self.assertFalse(result["within_budget"])
        self.assertEqual(result["status"], "degraded")
        self.vm.destroy()

    def test_stop_requires_running_state(self):
        with self.assertRaises(InvalidVmState):
            self.vm.stop()


class DeviceIsolationTest(unittest.TestCase):
    def test_conflict_uses_concrete_instance_ids_not_guest_names(self):
        mapping = shared_device_map()
        a = FullVm("guest-a", "tenant-a", 512, device_instances=mapping)
        b = FullVm("guest-b", "tenant-b", 512, device_instances=mapping)
        self.assertTrue(device_conflict(a, b))

    def test_registry_rejects_cross_guest_sharing_and_releases_on_stop(self):
        registry = DeviceLeaseRegistry()
        mapping = shared_device_map()
        a = FullVm("guest-a", "tenant-a", 512, device_instances=mapping)
        b = FullVm("guest-b", "tenant-b", 512, device_instances=mapping)
        a.start(primitive_usable=True, elapsed_ms=100, resident_mib=300, registry=registry)
        with self.assertRaises(DeviceConflict):
            b.start(primitive_usable=True, elapsed_ms=100, resident_mib=300, registry=registry)
        a.stop()
        b.start(primitive_usable=True, elapsed_ms=100, resident_mib=300, registry=registry)
        b.destroy()

    def test_concurrent_claim_has_single_winner(self):
        registry = DeviceLeaseRegistry()
        mapping = shared_device_map("race")
        vms = [
            FullVm("guest-a", "tenant-a", 512, device_instances=mapping),
            FullVm("guest-b", "tenant-b", 512, device_instances=mapping),
        ]
        barrier = threading.Barrier(2)
        outcomes: list[str] = []
        lock = threading.Lock()

        def worker(vm: FullVm) -> None:
            barrier.wait()
            try:
                vm.start(
                    primitive_usable=True,
                    elapsed_ms=100,
                    resident_mib=300,
                    registry=registry,
                )
                outcome = "started"
            except DeviceConflict:
                outcome = "conflict"
            with lock:
                outcomes.append(outcome)

        threads = [threading.Thread(target=worker, args=(vm,)) for vm in vms]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertCountEqual(outcomes, ["started", "conflict"])
        self.assertEqual(registry.active_claim_count(), len(FULL_DEVICE_MODEL))
        for vm in vms:
            if vm.state == "running":
                vm.destroy()


class RepositoryMetadataTest(unittest.TestCase):
    def test_version_files_are_consistent(self):
        # v4.3.0: literal bumped; pyproject.toml now also has to agree
        self.assertEqual((PKG_DIR / "VERSION").read_text().strip(), "4.3.0")
        init_text = (PKG_DIR / "__init__.py").read_text()
        self.assertIn('__version__ = "4.3.0"', init_text)
        self.assertIn('version = "4.3.0"', (PKG_DIR / "pyproject.toml").read_text())

    def test_package_runtime_import_does_not_require_pk_core(self):
        code = (
            "import sys; sys.path.insert(0, %r); "
            "import %s as p; "
            "print(p.__version__, p.FullVm.__name__)"
        ) % (str(PKG_DIR.parent), PKG_DIR.name)
        out = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=str(PKG_DIR.parent),
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "4.3.0 FullVm")


if __name__ == "__main__":
    unittest.main()
