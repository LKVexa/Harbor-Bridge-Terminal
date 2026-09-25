"""CI/release tooling: traceability, MASTER.md policy, exceptions, supply chain, release gate (MC-002, MC-003, MC-048, MC-049, MC-052)."""
from __future__ import annotations

import copy
import datetime as dt
import json
import os
import subprocess
import sys
import unittest

from _util import PKG_DIR
from inv05_current_control_state_system import tools_check as tc


class TraceabilityTest(unittest.TestCase):
    def test_matrix_is_complete_and_consistent(self):
        m = tc.load_json("traceability/trace_matrix.json")
        self.assertEqual(len(m["rows"]), 100)
        self.assertEqual(tc.check_trace(m), [])

    def test_checker_detects_gaps(self):
        m = copy.deepcopy(tc.load_json("traceability/trace_matrix.json"))
        m["rows"][0]["tests"] = ["test_nope.X.test_y"]
        m["rows"][1]["implementation"] = ["store.py::NoSuchThing"]
        m["rows"][2]["status"] = "done-ish"
        m["rows"][3]["last_verified"] = "0.0.1"
        m["rows"][4]["evidence"] = ["docs/MISSING.md"]
        m["rows"][5]["exception"] = "EX-999"
        m["rows"][8]["exception"] = ""  # partial without exception
        del m["rows"][99]
        p = tc.check_trace(m)
        for needle in ("unknown test id", "broken implementation ref", "invalid status", "stale evidence",
                       "missing evidence path", "unknown exception", "requires an exception", "differ from CHECKLIST"):
            self.assertTrue(any(needle in x for x in p), needle)

    def test_markdown_render(self):
        md = tc.render_trace_md(tc.load_json("traceability/trace_matrix.json"))
        self.assertIn("| INV-05-C001 |", md)
        self.assertIn("Status totals", md)


class MasterMdTest(unittest.TestCase):
    def test_current_tree_is_clean(self):
        self.assertEqual(tc.check_master_md(), [])

    def test_detects_false_presence_claim(self):
        p = os.path.join(PKG_DIR, "docs", "_tmp_claim.md")
        with open(p, "w") as fh:
            fh.write("The workflow is bundled: see MASTER.md included in the archive.\n")
        try:
            self.assertTrue(tc.check_master_md())
        finally:
            os.remove(p)


class ExceptionsTest(unittest.TestCase):
    def test_register_valid_today_and_expiry_enforced(self):
        self.assertEqual(tc.check_exceptions(dt.date(2026, 9, 22)), [])
        self.assertTrue(tc.check_exceptions(dt.date(2027, 6, 1)))


class SupplyChainTest(unittest.TestCase):
    def test_manifest_sbom_provenance(self):
        m = tc.manifest()
        self.assertIn("store.py", m)
        self.assertFalse(any(k.startswith("evidence/") for k in m))
        self.assertEqual(len(tc.tree_digest(m)), 64)
        s = tc.sbom()
        self.assertEqual((s["bomFormat"], s["specVersion"]), ("CycloneDX", "1.5"))
        self.assertIn("pk_core", [c["name"] for c in s["components"]])
        p = tc.provenance({"tests": True})
        self.assertEqual(p["subject"][0]["digest"]["sha256"], tc.tree_digest())
        self.assertEqual(tc.sign({"a": 1}, b"k" * 32), tc.sign({"a": 1}, b"k" * 32))

    def test_compat_tool_passes(self):
        r = subprocess.run([sys.executable, os.path.join(PKG_DIR, "tools", "check_compat.py")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class ReleaseGateTest(unittest.TestCase):
    def test_release_gate_blocks_on_open_p0(self):
        r = subprocess.run([sys.executable, os.path.join(PKG_DIR, "tools", "release_gate.py"), "--topology", "ha",
                            "--allow-unsigned"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        out = json.loads(r.stdout)
        self.assertEqual(out["decision"], "BLOCK")
        self.assertTrue(any("MC-004" in x for x in out["reasons"]))

    def test_ci_gate_skip_policy_only_allows_framework_tests(self):
        sys.path.insert(0, os.path.join(PKG_DIR, "tools"))
        try:
            import ci_gate
        finally:
            sys.path.pop(0)
        self.assertEqual(set(ci_gate.APPROVED_SKIPS.values()), {"EX-003"})
        self.assertEqual(list(ci_gate.APPROVED_SKIPS), ["test_component."])


if __name__ == "__main__":
    unittest.main()
