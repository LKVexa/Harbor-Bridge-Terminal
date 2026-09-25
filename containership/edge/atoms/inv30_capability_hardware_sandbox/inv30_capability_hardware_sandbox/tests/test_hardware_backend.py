# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Real-backend conformance (GAP-004, GAP-058). Runs ONLY against a real CHERI backend.

Separated from model tests so model success can never be mistaken for hardware
enforcement. Skips when no backend is available; the release gate reports a
skipped run as "hardware tier NO_GO", never as a pass.

Differential test: the same operation sequence is run on the semantic model and
on the hardware backend; any divergence fails.
"""
import unittest

from ..backend import CheriHardwareBackend, SemanticModelBackend

HW = CheriHardwareBackend()
AVAILABLE = HW.available()


@unittest.skipUnless(AVAILABLE["available"], f"no CHERI backend: {AVAILABLE['reason']}")
class HardwareConformanceTest(unittest.TestCase):
    def test_differential_against_model(self):  # pragma: no cover - requires CHERI hardware
        model = SemanticModelBackend()
        for base, length, perms in [(0x1000, 0x1000, {"read"}), (0, 16, {"read", "write"})]:
            m = model.mint(base, length, perms)
            h = HW.mint(base, length, perms)
            for addr, size, op in [(base, 1, "read"), (base + length, 1, "read"), (base, 1, "write")]:
                def outcome(c):
                    try:
                        c.check(address=addr, size=size, operation=op)
                        return "ok"
                    except Exception as e:  # noqa: BLE001
                        return getattr(e, "code", type(e).__name__)
                self.assertEqual(outcome(m), outcome(h))

    def test_tag_cleared_on_forgery(self):  # pragma: no cover
        self.fail("implement with the native helper: write capability bytes as data, reload, expect tag=0")


if __name__ == "__main__":
    unittest.main()
