"""Governance artefact checks: components 24, 34, 38, 39, 40 and the component registry."""
import importlib.util
import json
import re
import unittest

from harness import PKG_DIR


def registry():
    spec = importlib.util.spec_from_file_location("reg", PKG_DIR / "tools" / "component_registry.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.C


class GovernanceDocs(unittest.TestCase):
    def test_c39_every_alert_severity_defined_with_paging(self):
        text = (PKG_DIR / "docs" / "INCIDENT_SEVERITY.md").read_text()
        rules = json.loads((PKG_DIR / "ops" / "alerts.json").read_text())["rules"]
        for sev in ("SEV1", "SEV2", "SEV3", "SEV4"):
            self.assertIn(f"**{sev}**", text)
        for r in rules:
            self.assertIn(r["name"], text, r["name"])

    def test_c40_adrs_and_exception_register_well_formed(self):
        adr = (PKG_DIR / "docs" / "ADR.md").read_text()
        self.assertGreaterEqual(len(re.findall(r"^## ADR-\d{4}", adr, re.M)), 5)
        reg = (PKG_DIR / "docs" / "EXCEPTION_REGISTER.md").read_text()
        rows = [l for l in reg.splitlines() if l.startswith("| EX-")]
        self.assertGreaterEqual(len(rows), 5)
        for row in rows:
            cells = [c.strip() for c in row.strip("|").split("|")]
            self.assertEqual(len(cells), 7, row)
            self.assertRegex(cells[6], r"^\d{4}-\d{2}-\d{2}$")  # every exception is time-bounded

    def test_c38_runbook_has_backup_restore_and_alert_anchors(self):
        rb = (PKG_DIR / "docs" / "RUNBOOK.md").read_text()
        self.assertIn("{#backup}", rb)
        for r in json.loads((PKG_DIR / "ops" / "alerts.json").read_text())["rules"]:
            anchor = r["runbook"].split("#", 1)[1]
            self.assertIn("{#" + anchor + "}", rb, anchor)

    def test_c40_registry_covers_all_components_with_existing_modules(self):
        C = registry()
        self.assertEqual(sorted(C), list(range(1, 41)))
        for i, comp in C.items():
            for m in comp["modules"] + comp["docs"]:
                if "*" in m:
                    self.assertTrue(list(PKG_DIR.glob(m)), m)
                else:
                    self.assertTrue((PKG_DIR / m).exists(), f"C{i:02d}: {m}")
            for k in ("scope", "non_goals", "fail_closed", "permissions", "limits", "signals", "restart"):
                self.assertTrue(comp[k], f"C{i:02d} missing {k}")


if __name__ == "__main__":
    unittest.main()
