"""MC-002 KVM preflight, MC-003 device specs/ownership, MC-006 datapath policy."""
import os
import pathlib
import unittest

from inv24_microvm_runtime.tests.helpers import FakeKvm, tmpdir

from inv24_microvm_runtime.devices import (BlockSpec, NetSpec, OwnershipRegistry, RtcSpec, SerialSpec,
                                           SPEC_TYPES, VsockSpec, order_and_check)
from inv24_microvm_runtime.errors import Inv24Error
from inv24_microvm_runtime.io import Region, negotiate, validate_descriptor, validate_regions
from inv24_microvm_runtime.runtime import MINIMAL_DEVICE_MODEL
from inv24_microvm_runtime.virtualization.kvm import KvmPreflight


class KvmTest(unittest.TestCase):
    def test_usable_host_profile_exposed(self):
        fk = FakeKvm()
        prof = fk.preflight().run()
        self.assertTrue(prof.usable)
        self.assertEqual(prof.api_version, 12)
        self.assertEqual(fk.closed, 1)
        self.assertEqual(prof.to_dict()["schema"], "PK_MICROVM_HOST/1")

    def test_failure_classification(self):
        cases = [("absent", {}, "HOST_KVM_UNAVAILABLE", False), ("denied", {}, "HOST_KVM_PERMISSION", False),
                 ("busy", {}, "HOST_KVM_TRANSIENT", True), ("revoked", {}, "HOST_KVM_UNAVAILABLE", False),
                 ("ok", {"api": 11}, "HOST_KVM_INCOMPATIBLE", False),
                 ("ok", {"missing": ("KVM_CAP_IRQFD",)}, "HOST_KVM_INCOMPATIBLE", False)]
        for scen, kw, code, retry in cases:
            with self.subTest(scen=scen, kw=kw), self.assertRaises(Inv24Error) as cm:
                FakeKvm(scen, **kw).preflight().run()
            self.assertEqual((cm.exception.code, cm.exception.retryable), (code, retry))

    def test_unsupported_arch_fails_closed(self):
        with self.assertRaises(Inv24Error) as cm:
            KvmPreflight(arch="riscv64").run()
        self.assertEqual(cm.exception.code, "HOST_KVM_INCOMPATIBLE")

    def test_real_host_probe_classifies_this_host(self):
        """Runs the real probe here; on a host without /dev/kvm it must classify, not crash."""
        try:
            KvmPreflight().run()
        except Inv24Error as exc:
            self.assertIn(exc.code, {"HOST_KVM_UNAVAILABLE", "HOST_KVM_PERMISSION", "HOST_KVM_INCOMPATIBLE"})


class DeviceTest(unittest.TestCase):
    def setUp(self):
        self.d = tmpdir()
        self.img = os.path.join(self.d, "disk.img")
        pathlib.Path(self.img).write_bytes(b"\0" * 1024)

    def test_spec_set_equals_minimal_model(self):
        self.assertEqual(set(SPEC_TYPES), set(MINIMAL_DEVICE_MODEL))

    def test_every_permitted_device_validates(self):
        all_dev = frozenset(MINIMAL_DEVICE_MODEL)
        specs = [BlockSpec("root", self.img, is_root=True), NetSpec("eth0", "tap0", "02:00:00:00:00:01"),
                 VsockSpec("v0", 3, "/run/v.sock"), SerialSpec(), RtcSpec()]
        ordered = order_and_check(specs, declared=all_dev)
        self.assertEqual([s.kind for s in ordered], ["virtio-block", "virtio-net", "virtio-vsock", "serial", "rtc"])

    def test_malformed_duplicate_and_unsafe_specs(self):
        link = os.path.join(self.d, "link.img")
        os.symlink(self.img, link)
        odd = os.path.join(self.d, "odd.img")
        pathlib.Path(odd).write_bytes(b"\0" * 100)
        bad = [
            [BlockSpec("root", "rel/path")], [BlockSpec("root", link)], [BlockSpec("root", odd)],
            [BlockSpec("root", "/nonexistent/x")], [NetSpec("eth0", "tap0", "03:00:00:00:00:01")],
            [NetSpec("eth0", "tap-name-far-too-long", "02:00:00:00:00:01")], [VsockSpec("v", 2, "/run/v")],
            [VsockSpec("v", True, "/run/v")], [SerialSpec("a"), SerialSpec("b")],
            [BlockSpec("root", self.img), BlockSpec("root", self.img)],
            [BlockSpec("a", self.img, is_root=True), BlockSpec("b", self.img, is_root=True)],
            [BlockSpec("BAD ID", self.img)],
        ]
        for specs in bad:
            with self.subTest(specs=specs), self.assertRaises(Inv24Error):
                order_and_check(specs, declared=frozenset(MINIMAL_DEVICE_MODEL))

    def test_tenant_root_confinement(self):
        with self.assertRaises(Inv24Error) as cm:
            order_and_check([BlockSpec("r", self.img)], declared=frozenset({"virtio-block"}), tenant_root="/srv/other")
        self.assertEqual(cm.exception.code, "TENANT_MISMATCH")

    def test_cross_tenant_reuse_blocked_and_teardown_frees(self):
        reg = OwnershipRegistry()
        nic = NetSpec("eth0", "tap0", "02:00:00:00:00:01")
        reg.claim_specs([nic], "t1", "vm1")
        with self.assertRaises(Inv24Error) as cm:
            reg.claim_specs([nic], "t2", "vm9")
        self.assertEqual(cm.exception.code, "TENANT_MISMATCH")
        self.assertEqual(reg.release_instance("t1", "vm1"), 2)
        reg.claim_specs([nic], "t2", "vm9")
        self.assertEqual(reg.owned_by("t1"), [])

    def test_partial_claim_rolls_back(self):
        reg = OwnershipRegistry()
        reg.claim("mac", "02:00:00:00:00:02", "t2", "vmx")
        with self.assertRaises(Inv24Error):
            reg.claim_specs([NetSpec("a", "tapA", "02:00:00:00:00:01"), NetSpec("b", "tapB", "02:00:00:00:00:02")], "t1", "vm1")
        self.assertEqual(reg.owned_by("t1"), [])

    def test_cid_allocation_unique_and_reconciled(self):
        reg = OwnershipRegistry()
        cids = {reg.allocate_cid("t", f"vm{i}") for i in range(200)}
        self.assertEqual(len(cids), 200)
        self.assertTrue(all(c >= 3 for c in cids))
        self.assertEqual(reg.reconcile({("t", "vm0")}), 199)


class DatapathTest(unittest.TestCase):
    class P:
        name, version = "inv35", "1"

        def __init__(self, ok):
            self.ok = ok

        def healthy(self):
            return self.ok

    def test_policy_matrix(self):
        self.assertEqual(negotiate("disabled", self.P(True)).mode, "standard")
        self.assertEqual(negotiate("prefer", self.P(True)).mode, "accelerated")
        d = negotiate("prefer", None)
        self.assertEqual(d.mode, "standard")
        self.assertIn("fell back", d.reason)
        for prov in (None, self.P(False)):
            with self.assertRaises(Inv24Error) as cm:
                negotiate("require", prov)
            self.assertEqual(cm.exception.code, "DATAPATH_UNAVAILABLE")
        with self.assertRaises(Inv24Error):
            negotiate("turbo", None)

    def test_region_and_descriptor_bounds(self):
        regs = [Region(0x1000, 0x1000, "t1"), Region(0x4000, 0x1000, "t1")]
        validate_regions(regs, guest_memory_bytes=1 << 20)
        validate_descriptor(0x1000, 4096, regs, queue_size=256)
        for bad in [dict(addr=0x1800, length=4096), dict(addr=0x3000, length=16), dict(addr=0x1000, length=0)]:
            with self.subTest(bad=bad), self.assertRaises(Inv24Error):
                validate_descriptor(bad["addr"], bad["length"], regs, queue_size=256)
        for bad in [[Region(0, 0x2000, "t"), Region(0x1000, 0x1000, "t")], [Region(0, 1 << 21, "t")],
                    [Region(0, 16, "a"), Region(32, 16, "b")]]:
            with self.subTest(bad=bad), self.assertRaises(Inv24Error):
                validate_regions(bad, guest_memory_bytes=1 << 20)
        with self.assertRaises(Inv24Error):
            validate_descriptor(0x1000, 16, regs, queue_size=300)


if __name__ == "__main__":
    unittest.main()
