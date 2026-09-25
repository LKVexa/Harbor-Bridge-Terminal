"""MC-002-A01/A02 on a real KVM host."""
import unittest

from ._realhost import need_real_host
from inv24_microvm_runtime.virtualization.kvm import KvmPreflight


@need_real_host
class RealKvmTest(unittest.TestCase):
    def test_real_ioctl_profile(self):
        p = KvmPreflight().run()
        self.assertTrue(p.usable)
        self.assertEqual(p.api_version, 12)
        self.assertTrue(all(p.capabilities.values()))
