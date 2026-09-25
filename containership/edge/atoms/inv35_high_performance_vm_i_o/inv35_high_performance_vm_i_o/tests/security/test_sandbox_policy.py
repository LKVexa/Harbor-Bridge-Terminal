"""INV-35-C043: the datapath modules have no ambient OS authority (no fs/net/subprocess/env)."""
from __future__ import annotations

import ast
import unittest

from _support import PKG_DIR

DATAPATH_MODULES = ["io_model.py", "runtime/datapath.py", "runtime/security.py", "runtime/policy.py",
                    "runtime/lifecycle.py", "runtime/telemetry.py", "runtime/health.py", "runtime/errors.py",
                    "runtime/wire.py", "runtime/schema_check.py"]
FORBIDDEN_IMPORTS = {"socket", "subprocess", "urllib", "http", "ssl", "ctypes", "shutil", "pickle", "marshal"}
FORBIDDEN_BUILTINS = {"eval", "exec", "compile", "__import__", "open"}
FORBIDDEN_ATTRS = {"system", "popen", "getenv", "spawn", "fork", "execv"}


class SandboxPolicyTest(unittest.TestCase):
    def test_no_forbidden_imports_or_calls(self):
        for rel in DATAPATH_MODULES:
            tree = ast.parse((PKG_DIR / rel).read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for a in node.names:
                        self.assertNotIn(a.name.split(".")[0], FORBIDDEN_IMPORTS, rel)
                if isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotIn(node.module.split(".")[0], FORBIDDEN_IMPORTS, rel)
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        self.assertNotIn(node.func.id, FORBIDDEN_BUILTINS, f"{rel}:{node.lineno}")
                    elif isinstance(node.func, ast.Attribute):
                        self.assertNotIn(node.func.attr, FORBIDDEN_ATTRS, f"{rel}:{node.lineno}")
                if isinstance(node, ast.Attribute) and node.attr == "environ":
                    self.fail(f"{rel}:{node.lineno} reads os.environ")

    def test_only_wire_reads_files_and_only_its_own_schema(self):
        for rel in DATAPATH_MODULES:
            src = (PKG_DIR / rel).read_text()
            if rel != "runtime/wire.py":
                self.assertNotIn("read_text(", src, rel)


if __name__ == "__main__":
    unittest.main()
