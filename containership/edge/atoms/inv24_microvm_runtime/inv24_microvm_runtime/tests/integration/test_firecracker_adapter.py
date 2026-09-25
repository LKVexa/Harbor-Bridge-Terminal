"""MC-001-A01/A02 on a real KVM host."""
import glob
import os
import unittest

from ._realhost import adapter, env, need_real_host
from inv24_microvm_runtime import MicroVM
from inv24_microvm_runtime.devices import BlockSpec, SerialSpec


@need_real_host
class RealFirecrackerTest(unittest.TestCase):
    def test_create_boot_query_destroy_no_orphans(self):
        ad = adapter()
        vm = MicroVM("it-vm1", "it-tenant", vcpus=1, memory_mib=128, devices={"virtio-block", "serial"})
        res = ad.launch(vm, [BlockSpec("rootfs", env("INV24_ROOTFS"), is_root=True), SerialSpec()])
        self.assertEqual(vm.state, "running")
        self.assertLessEqual(res.boot["boot_ms"], res.boot["budget_ms"])
        ad.destroy(vm)
        self.assertEqual(ad.registry.owned_by("it-tenant"), [])
        self.assertFalse(glob.glob(os.path.join(ad.run_dir, "it-tenant-*.sock")))
