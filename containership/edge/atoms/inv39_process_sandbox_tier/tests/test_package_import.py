"""The hardened policy model remains importable when optional pk_core is absent."""
from __future__ import annotations

import pathlib
import subprocess
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent


class PackageImportTest(unittest.TestCase):
    def test_package_import_and_version_without_pk_core(self):
        code = (
            "import sys; sys.path.insert(0, %r); import %s as m; "
            "print(m.__version__); print(m.SandboxProfile('svc', {'read'}).name)"
        ) % (str(ROOT), PKG_DIR.name)
        out = subprocess.run(
            [sys.executable, "-I", "-c", code], capture_output=True, text=True, cwd=str(ROOT)
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.splitlines(), ["5.1.0", "svc"])


if __name__ == "__main__":
    unittest.main()
