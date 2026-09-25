"""Standalone safety and lifecycle tests for INV-24; no pk_core dependency."""
from __future__ import annotations

import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import inv24_microvm_runtime as pkg


class RuntimeTest(unittest.TestCase):
    def test_package_import_and_version_without_pk_core(self):
        self.assertEqual(pkg.__version__, "4.3.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text().strip(), "4.3.0")

    def test_create_record_is_bounded_and_stable(self):
        vm = pkg.MicroVM(" vm-1 ", " tenant-a ", vcpus=2, memory_mib=256,
                         devices={"virtio-net", "serial"})
        self.assertEqual(vm.name, "vm-1")
        self.assertEqual(vm.tenant, "tenant-a")
        self.assertEqual(vm.create_record(), {
            "schema": "PK_MICROVM/1", "instance": "vm-1", "tenant": "tenant-a",
            "vcpus": 2, "memory_mib": 256, "devices": ["serial", "virtio-net"],
            "state": "created",
        })

    def test_rejects_out_of_model_device(self):
        with self.assertRaises(pkg.DeviceOutsideModel):
            pkg.MicroVM("vm", "tenant", devices={"pci-passthrough"})

    def test_rejects_ambiguous_or_invalid_scalar_types(self):
        bad = [
            dict(name="", tenant="t"),
            dict(name="x\n", tenant="t"),
            dict(name="x", tenant=" "),
            dict(name="x", tenant="t", vcpus=True),
            dict(name="x", tenant="t", vcpus=1.5),
            dict(name="x", tenant="t", memory_mib=False),
            dict(name="x", tenant="t", devices="virtio-net"),
            dict(name="x", tenant="t", devices={1}),
        ]
        for kwargs in bad:
            with self.subTest(kwargs=kwargs), self.assertRaises((TypeError, ValueError)):
                pkg.MicroVM(**kwargs)

    def test_enforces_upper_and_lower_resource_bounds(self):
        for kwargs in [
            dict(vcpus=0), dict(vcpus=pkg.MAX_VCPUS + 1),
            dict(memory_mib=pkg.MIN_MEMORY_MIB - 1),
            dict(memory_mib=pkg.MAX_MEMORY_MIB + 1),
        ]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                pkg.MicroVM("vm", "tenant", **kwargs)

    def test_boot_budget_cannot_be_widened_or_type_confused(self):
        for budget in [0, pkg.BOOT_BUDGET_MS + 1, True, 12.5]:
            vm = pkg.MicroVM("vm", "tenant")
            with self.subTest(budget=budget), self.assertRaises((TypeError, ValueError)):
                vm.boot(elapsed_ms=10, budget_ms=budget)
        for elapsed in [-1, True, 1.5]:
            vm = pkg.MicroVM("vm", "tenant")
            with self.subTest(elapsed=elapsed), self.assertRaises((TypeError, ValueError)):
                vm.boot(elapsed_ms=elapsed)

    def test_budget_breach_is_explicit_failed_state_then_destroyable(self):
        vm = pkg.MicroVM("vm", "tenant")
        with self.assertRaises(pkg.BootBudgetExceeded):
            vm.boot(elapsed_ms=pkg.BOOT_BUDGET_MS + 1)
        self.assertEqual(vm.state, "failed")
        self.assertTrue(vm.stop()["destroyed"])

    def test_lifecycle_and_terminal_destruction(self):
        vm = pkg.MicroVM("vm", "tenant")
        vm.boot(elapsed_ms=10)
        self.assertEqual(vm.pause(), "paused")
        self.assertEqual(vm.resume(), "running")
        self.assertTrue(vm.stop()["destroyed"])
        for op in (lambda: vm.stop(), lambda: vm.boot(elapsed_ms=1), vm.pause, vm.resume):
            with self.assertRaises(RuntimeError):
                op()


    def test_runtime_managed_fields_cannot_be_mutated_externally(self):
        vm = pkg.MicroVM("vm", "tenant", devices={"serial"})
        for field_name, value in [
            ("tenant", "other"), ("devices", frozenset({"pci-passthrough"})),
            ("vcpus", 99), ("state", "running"), ("destroyed", True),
            ("boot_ms", 0),
        ]:
            with self.subTest(field=field_name), self.assertRaises(AttributeError):
                setattr(vm, field_name, value)
        self.assertEqual(vm.tenant, "tenant")
        self.assertEqual(vm.state, "created")

    def test_status_is_snapshot_not_internal_mutable_object(self):
        vm = pkg.MicroVM("vm", "tenant", devices={"serial"})
        status = vm.status()
        status["devices"].append("evil")
        self.assertEqual(vm.status()["devices"], ["serial"])


if __name__ == "__main__":
    unittest.main()
