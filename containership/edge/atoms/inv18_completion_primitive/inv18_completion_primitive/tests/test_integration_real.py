"""Real-component integration tier (C030, C083).

Runs only when INV18_REAL_COMPONENTS points at a directory containing the real
INV-12/15/16/17/20 packages from the Post-Kubernetes estate.  Otherwise every test
SKIPS, and the release gate treats these mandatory skips as BLOCKED: contract
doubles never satisfy this tier.
"""
import importlib
import os
import sys
import unittest

REAL = os.environ.get("INV18_REAL_COMPONENTS")
LAYERS = {"INV-12": "inv12_", "INV-15": "inv15_", "INV-16": "inv16_", "INV-17": "inv17_", "INV-20": "inv20_"}


def _find(prefix):
    for name in sorted(os.listdir(REAL)):
        if name.startswith(prefix) and os.path.isdir(os.path.join(REAL, name)):
            return name
    return None


@unittest.skipUnless(REAL and os.path.isdir(REAL or ""), "INV18_REAL_COMPONENTS not set: real adjacent components unavailable")
class RealAdjacentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, REAL)

    def _layer(self, layer):
        name = _find(LAYERS[layer])
        if name is None:
            self.fail(f"{layer} package not found in {REAL}")
        return importlib.import_module(name)

    def test_inv12_real(self):
        """REQ: C030 C083"""
        self.assertTrue(hasattr(self._layer("INV-12"), "COMPONENT"))

    def test_inv15_real(self):
        """REQ: C030 C083"""
        self.assertTrue(hasattr(self._layer("INV-15"), "COMPONENT"))

    def test_inv16_real(self):
        """REQ: C030 C083"""
        self.assertTrue(hasattr(self._layer("INV-16"), "COMPONENT"))

    def test_inv17_real(self):
        """REQ: C030 C083"""
        self.assertTrue(hasattr(self._layer("INV-17"), "COMPONENT"))

    def test_inv20_real(self):
        """REQ: C030 C083"""
        self.assertTrue(hasattr(self._layer("INV-20"), "COMPONENT"))


if __name__ == "__main__":
    unittest.main()
