"""Repository production gates (MC-011, MC-079, MC-088, MC-091..094): these
fail if traceability, schemas, versions, registers or release integrity
tooling are removed, stale or bypassed."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
import zipfile

import support  # noqa: F401 - puts the package root on sys.path

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, cwd=str(PKG))


class TraceabilityTest(unittest.TestCase):
    def test_rtm_in_sync_and_complete(self):
        r = run(PKG / "tools" / "rtm.py", "--check")
        self.assertEqual(r.returncode, 0, r.stdout)
        rtm = json.loads((PKG / "conformance" / "RTM.json").read_text())
        self.assertEqual(rtm["uncovered_checklist_items"], [])
        self.assertEqual(len(rtm["missing_components"]), 94)
        self.assertEqual(len(rtm["checklist_coverage"]), 100)

    def test_mc_status_is_honest(self):
        mc = json.loads((PKG / "conformance" / "mc_status.json").read_text())
        vocab = set(mc["status_vocabulary"])
        self.assertEqual(len(mc["items"]), 94)
        self.assertEqual({i["id"] for i in mc["items"]}, {f"MC-{n:03d}" for n in range(1, 95)})
        for i in mc["items"]:
            self.assertIn(i["status"], vocab)
            self.assertTrue(i["evidence"])
        # nothing may claim 'implemented' until a human review record exists
        self.assertFalse([i for i in mc["items"] if i["status"] == "implemented"])

    def test_versions_consistent(self):
        import inv62_edge_topology as pkg  # noqa: F401 - path set by support in other tests
        v = (PKG / "VERSION").read_text().strip()
        self.assertEqual(v, "4.3.0")
        self.assertIn(f'version = "{v}"', (PKG / "pyproject.toml").read_text())
        self.assertIn(f"## {v}", (PKG / "CHANGELOG.md").read_text())
        from inv62_edge_topology.production.service import VERSION
        self.assertEqual(VERSION, v)

    def test_registers_well_formed(self):
        w = json.loads((PKG / "governance" / "waivers.json").read_text())["waivers"]
        for x in w:
            for k in ("id", "requirements", "scope", "risk", "compensating_controls", "owner", "approver", "created", "expires", "remediation", "status"):
                self.assertIn(k, x)
        alerts = json.loads((PKG / "ops" / "alerts.json").read_text())
        self.assertEqual(set(alerts["taxonomy"]), {a["class"] for a in alerts["alerts"]})


class ReleaseIntegrityTest(unittest.TestCase):
    def test_reproducible_build_verify_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            r1 = run(PKG / "tools" / "release.py", "build", "--out", d1)
            r2 = run(PKG / "tools" / "release.py", "build", "--out", d2)
            self.assertEqual(r1.returncode, 0, r1.stderr)
            b1, b2 = json.loads(r1.stdout), json.loads(r2.stdout)
            self.assertEqual(b1["tree_digest"], b2["tree_digest"])
            z = pathlib.Path(b1["zip"])
            self.assertEqual(run(PKG / "tools" / "release.py", "verify-zip", "--zip", z, "--sums", pathlib.Path(d1) / "SHA256SUMS").returncode, 0)
            sbom = json.loads((pathlib.Path(d1) / "sbom.cdx.json").read_text())
            self.assertEqual(sbom["bomFormat"], "CycloneDX")
            prov = json.loads((pathlib.Path(d1) / "provenance.intoto.json").read_text())
            self.assertEqual(prov["subject"][0]["digest"]["sha256"], b1["sha256"])
            with tempfile.TemporaryDirectory() as x:
                zipfile.ZipFile(z).extractall(x)
                root = pathlib.Path(x) / "inv62_edge_topology"
                ok = run(PKG / "tools" / "release.py", "verify", "--dir", root)
                self.assertEqual(ok.returncode, 0, ok.stdout)
                self.assertIn("NONPRODUCTION-EPHEMERAL", ok.stdout)
                (root / "topology.py").write_text((root / "topology.py").read_text() + "\n# tampered\n")
                bad = run(PKG / "tools" / "release.py", "verify", "--dir", root)
                self.assertNotEqual(bad.returncode, 0)
                self.assertIn("digest mismatch topology.py", bad.stdout)

    def test_zip_bytes_are_reproducible(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            # signatures differ (ephemeral key) so compare the member payloads except the signature
            z1 = json.loads(run(PKG / "tools" / "release.py", "build", "--out", d1).stdout)["zip"]
            z2 = json.loads(run(PKG / "tools" / "release.py", "build", "--out", d2).stdout)["zip"]
            with zipfile.ZipFile(z1) as a, zipfile.ZipFile(z2) as b:
                names = [n for n in a.namelist() if not n.endswith("RELEASE_MANIFEST.sig.json")]
                self.assertEqual(names, [n for n in b.namelist() if not n.endswith("RELEASE_MANIFEST.sig.json")])
                for n in names:
                    self.assertEqual(a.read(n), b.read(n), n)
                    self.assertEqual(a.getinfo(n).date_time, b.getinfo(n).date_time)


if __name__ == "__main__":
    sys.path.insert(0, str(PKG.parent))
    unittest.main()
