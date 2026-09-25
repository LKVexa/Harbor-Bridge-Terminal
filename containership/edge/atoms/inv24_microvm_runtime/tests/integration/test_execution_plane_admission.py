"""MC-005 / MC-048: admission against the real PLN-04 contract."""
import os
import unittest


@unittest.skipUnless(os.environ.get("INV24_PLN04_ENDPOINT"), "NOT_TESTED: PLN-04 execution plane not available")
class RealPln04Test(unittest.TestCase):
    def test_pln04_roundtrip(self):
        self.skipTest("NOT_TESTED: PLN-04 client binding not supplied in this archive")
