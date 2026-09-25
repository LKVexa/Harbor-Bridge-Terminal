"""Repository integrity: version, MASTER provenance, checklist, packaging data, matrix, waivers."""

import hashlib
import json
import re
import subprocess
import sys
import unittest

from tests._boot import PKG_DIR, mod

schema = mod("schema")


@unittest.skipUnless((PKG_DIR / "tools").is_dir(), "source-checkout checks (installed wheel carries no tools/)")
class RepositoryTest(unittest.TestCase):
    def test_version_consistency(self):
        out = subprocess.run([sys.executable, str(PKG_DIR / "tools" / "check_version.py")], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout)

    def test_master_restored_with_matching_provenance(self):
        prov = json.loads((PKG_DIR / "MASTER_PROVENANCE.json").read_text())
        raw = (PKG_DIR / "MASTER.md").read_bytes()
        self.assertEqual(prov["status"], "restored")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), prov["sha256"])
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\r\n", raw)
        text = raw.decode("utf-8")
        self.assertTrue(text.startswith("# INV-23 "))
        ids = re.findall(r"^# (INV-23-C\d{3}) — Master Prompt & Workflow$", text, re.M)
        items = json.loads((PKG_DIR / "CHECKLIST.json").read_text())["items"]
        self.assertEqual(ids, [i["check_id"] for i in items])  # 1:1, ordered, no dupes/truncation
        for it in items:
            self.assertIn(f"**Checklist requirement:** {it['requirement']}", text)

    def test_checklist_integrity(self):
        d = json.loads((PKG_DIR / "CHECKLIST.json").read_text())
        self.assertEqual((d["element"], d["item_count"], len(d["items"])), ("INV-23", 100, 100))
        self.assertEqual([i["ordinal"] for i in d["items"]], list(range(1, 101)))
        self.assertEqual(len({i["check_id"] for i in d["items"]}), 100)

    def test_vendored_pk_core_is_pinned(self):
        compat = mod("pkcore_compat")
        self.assertEqual(compat.verify_vendored(PKG_DIR / "vendor"), [])

    def test_compatibility_doc_fresh_and_readme_not_overclaiming(self):
        out = subprocess.run([sys.executable, str(PKG_DIR / "tools" / "gen_compat.py"), "--check"])
        self.assertEqual(out.returncode, 0, "COMPATIBILITY.md stale; run tools/gen_compat.py")
        rows = json.loads((PKG_DIR / "compatibility.json").read_text())["rows"]
        self.assertEqual(len({r["id"] for r in rows}), len(rows))
        for r in rows:
            if r["status"] == "verified":
                self.assertTrue(r["last_verified"], r["id"])
        readme = (PKG_DIR / "README.md").read_text().lower()
        for claim in ("production-ready on windows", "production-ready on macos", "supports all platforms"):
            self.assertNotIn(claim, readme)

    def test_waivers_valid(self):
        sys.path.insert(0, str(PKG_DIR / "tools"))
        import waivers

        ws = waivers.load()
        self.assertTrue(all(w["id"].startswith("WVR-") for w in ws))

    def test_governance_artifacts_present(self):
        for f in (
            "SECURITY.md",
            "SUPPORT.md",
            "THREAT_MODEL.md",
            "CODEOWNERS",
            "LICENSE-STATUS.md",
            "THIRD-PARTY-NOTICES.md",
            "security/incident-runbook.md",
            "security/waivers.json",
        ):
            self.assertTrue((PKG_DIR / f).is_file(), f)
        tm = (PKG_DIR / "THREAT_MODEL.md").read_text()
        self.assertEqual(len(re.findall(r"^\| T\d\d \|", tm, re.M)), 20)


if __name__ == "__main__":
    unittest.main()
