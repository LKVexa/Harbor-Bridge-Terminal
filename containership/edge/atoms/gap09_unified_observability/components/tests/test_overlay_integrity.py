"""The v5.0.0 package files are byte-identical to their MANIFEST.sha256."""
import hashlib
import os
import unittest

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestIntegrity(unittest.TestCase):
    def test_v5_files_unchanged(self):
        n = 0
        for line in open(os.path.join(PKG, "MANIFEST.sha256"), encoding="utf-8"):
            digest, name = line.split(maxsplit=1)
            name = name.strip().lstrip("*")
            with open(os.path.join(PKG, name), "rb") as fh:
                self.assertEqual(hashlib.sha256(fh.read()).hexdigest(), digest, name)
            n += 1
        self.assertGreaterEqual(n, 20)


if __name__ == "__main__":
    unittest.main()
