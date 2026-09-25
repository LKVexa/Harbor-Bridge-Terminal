"""MC-006: INV-35 accelerated datapath on a real host."""
import unittest

try:
    import inv35_high_performance_vm_io  # noqa: F401
    HAVE = True
except ImportError:
    HAVE = False


@unittest.skipUnless(HAVE, "NOT_TESTED: INV-35 not installed")
class Inv35Test(unittest.TestCase):
    def test_accelerated_benefit(self):
        self.skipTest("NOT_TESTED: benchmark profile not approved")
