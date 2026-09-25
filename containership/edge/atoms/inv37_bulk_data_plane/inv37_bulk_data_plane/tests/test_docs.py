"""Documentation and traceability are machine-checked (C011, C020, C021, C043)."""
from __future__ import annotations

import ast
import importlib.util
import json
import re
import subprocess
import sys
import unittest

from _support import PKG_DIR, pkg


def tool(name):
    spec = importlib.util.spec_from_file_location(name, PKG_DIR / "tools" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class DocsTest(unittest.TestCase):
    def test_requirements_rule(self):
        self.assertEqual(tool("check_requirements").check(), [])

    def test_semantics_generated_tables_current(self):
        r = subprocess.run([sys.executable, str(PKG_DIR / "tools" / "render_semantics.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_interfaces_inventory_complete(self):
        text = (PKG_DIR / "INTERFACES.md").read_text()
        public = [n for n in dir(pkg.BulkDataPlane) if not n.startswith("_") and callable(getattr(pkg.BulkDataPlane, n))]
        missing = [n for n in public if f"`{n}(" not in text]
        self.assertEqual(missing, [])
        self.assertEqual([c for c in pkg.ERROR_CODES if f"`{c}`" not in text], [])

    def test_no_ambient_authority_in_runtime_modules(self):
        forbidden = {"socket", "subprocess", "ctypes", "urllib", "http", "ssl", "pickle", "marshal"}
        for p in PKG_DIR.glob("*.py"):
            tree = ast.parse(p.read_text())
            for node in ast.walk(tree):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    mods = [node.module.split(".")[0]]
                self.assertFalse(set(mods) & forbidden, f"{p.name} imports {set(mods) & forbidden}")
            envs = set(re.findall(r'os\.environ(?:\.get)?\(\s*"([A-Z0-9_]+)"', p.read_text()))
            self.assertTrue(envs <= {"INV37_BUILD_COMMIT", "INV37_NODE_ID"}, (p.name, envs))
            self.assertNotIn("eval(", p.read_text().replace("# eval(", ""))

    def test_traceability_covers_all_100(self):
        status = json.loads((PKG_DIR / "REMEDIATION_STATUS.json").read_text())
        audit = json.loads((PKG_DIR / "SELF_AUDIT.json").read_text())
        ids = {i["check_id"] for i in json.loads((PKG_DIR / "CHECKLIST.json").read_text())["items"]}
        self.assertEqual({r["check_id"] for r in audit["requirements"]}, ids)
        self.assertEqual(len(status["items"]), 85)
        self.assertFalse([r for r in status["items"] if r["status"] == "PASS"])  # PASS needs accountable review
        self.assertEqual(audit["gate"], "NO_GO")
        for r in status["items"]:
            for p in r["evidence"]:
                self.assertTrue((PKG_DIR / p).exists(), f"{r['check_id']}: {p}")
        tr = (PKG_DIR / "TRACEABILITY.md").read_text()
        self.assertEqual([i for i in ids if i not in tr], [])


if __name__ == "__main__":
    unittest.main()
