"""MC-003-A01/A02: every permitted device booted end-to-end on a real host."""
import unittest

from ._realhost import need_real_host


@need_real_host
class RealDeviceTest(unittest.TestCase):
    def test_every_device_combination_boots(self):
        self.skipTest("NOT_TESTED: TAP/netns provisioning fixture for the approved host profile not yet supplied")
