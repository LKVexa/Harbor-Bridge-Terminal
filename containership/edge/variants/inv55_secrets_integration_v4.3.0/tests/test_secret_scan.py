"""The secret-scan gate itself must catch planted credentials (checklist #31)."""
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

from helpers import ROOT

sys.path.insert(0, str(ROOT / "tools"))
import secret_scan  # noqa: E402


class ScanGate(unittest.TestCase):
    def test_repository_is_clean(self):
        self.assertEqual(secret_scan.scan(ROOT), [])

    def test_detects_planted_credentials(self):
        planted = {
            "a.py": "tok = 'hvs." + "A" * 24 + "'\n",
            "b.json": '{"password": "' + "Z" * 12 + '"}\n',
            "c.md": "-----BEGIN " + "PRIVATE KEY-----\n",
        }
        with tempfile.TemporaryDirectory() as d:
            for n, c in planted.items():
                (pathlib.Path(d) / n).write_text(c)
            rules = {r for _, _, r in secret_scan.scan(pathlib.Path(d))}
        self.assertEqual(rules, {"vault-token", "generic-assignment", "private-key"})


if __name__ == "__main__":
    unittest.main()
