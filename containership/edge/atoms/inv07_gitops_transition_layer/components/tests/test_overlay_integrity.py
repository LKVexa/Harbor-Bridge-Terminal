"""The v4.2.0 reference model, contract, conformance adapter, their tests and
CHECKLIST.json are left byte-identical; only the documented files changed."""
from __future__ import annotations

import hashlib
import os
import unittest

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

UNCHANGED = {  # sha256 of the v4.2.0 files as received
    "gitops_model.py": "ccc039014bcda14e771e4e215b17404abd74c3be5173f7ef8197273705eac03f", "contract.py": "ec3d20760ee134076a046e0fade16762bfaeee808644335fda475daffdd854e5", "component.py": "04f872850e63cde1eeb7ea8629fe891ce8af9ac783e877f80f9eda8825db9b9b", "CHECKLIST.json": "873e6f1404133e240b112c24cd2199afb768db1bbfdcf986f52287bad13369aa",
    "tests/test_gitops_model.py": "dcda234e3c7f09f49c7615028ff70487440c4843cbd815f3d5e99d98e98f8ad7", "tests/test_component.py": "2ebf3ce976801c70d2195b11f896db1ed9fb73a3451af520901630a64290086f", "AUDIT_REPORT.md": "8ac16753f0e1a0b435d351776c196ebf1a5a2c548802138ab5fb2669230f3b0c",
}
CHANGED_BY_DESIGN = ("__init__.py", "VERSION", "README.md", "CHANGELOG.md", "MISSING_COMPONENTS.md")


def _sha(rel):
    with open(os.path.join(PKG, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class TestOverlayIntegrity(unittest.TestCase):
    def test_reference_files_unchanged(self):
        for rel, want in UNCHANGED.items():
            self.assertEqual(_sha(rel), want, rel)

    def test_reference_model_tests_still_pass(self):
        import subprocess
        import sys
        for opt in ([], ["-O"]):
            p = subprocess.run([sys.executable, "-B", *opt, os.path.join(PKG, "tests", "test_gitops_model.py")],
                               capture_output=True, text=True, timeout=120)
            self.assertEqual(p.returncode, 0, p.stderr[-500:])


if __name__ == "__main__":
    unittest.main()
