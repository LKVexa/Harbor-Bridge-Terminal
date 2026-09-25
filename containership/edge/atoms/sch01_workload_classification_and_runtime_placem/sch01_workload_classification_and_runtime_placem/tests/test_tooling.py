"""MC-01/02/03/04/05/06/35/36/42/49/51/57/58/59/60: governance tooling and the exit gate."""
from __future__ import annotations

import json
import subprocess
import sys
import tomllib
import unittest

from _fx import PKG_DIR

sys.path.insert(0, str(PKG_DIR / "tools"))
import exit_gate  # noqa: E402
from registry import R  # noqa: E402
from sch01_workload_classification_and_runtime_placem import canary  # noqa: E402


def run(tool, *a):
    return subprocess.run([sys.executable, "-B", str(PKG_DIR / "tools" / tool), *a], capture_output=True, text=True, cwd=PKG_DIR)


class ProvenanceTest(unittest.TestCase):
    """MC-01 MASTER.md provenance: absence is an EVIDENCE_GAP, never reconstructed or passed."""

    def test_gap_reported_not_fabricated(self):
        r = run("verify_master_provenance.py")
        self.assertEqual(r.returncode, 3)
        self.assertFalse((PKG_DIR / "MASTER.md").exists())
        self.assertEqual(json.loads((PKG_DIR / "evidence/master_provenance.json").read_text())["status"], "EVIDENCE_GAP")


class PackagingTest(unittest.TestCase):
    """MC-02 reproducible package manifest; zero third-party runtime dependencies."""

    def test_pyproject(self):
        d = tomllib.loads((PKG_DIR / "pyproject.toml").read_text())
        self.assertEqual(d["project"]["version"], (PKG_DIR / "VERSION").read_text().strip())
        self.assertEqual(d["project"]["dependencies"], [])


class GovernanceTest(unittest.TestCase):
    """MC-03/04/42/50/52/54/55/56 governance artifacts exist and are honestly unapproved."""

    def test_owners_unassigned_and_adrs_proposed(self):
        o = json.loads((PKG_DIR / "governance/OWNERS.json").read_text())
        self.assertEqual(o["service_owner"], "UNASSIGNED")
        for p in (PKG_DIR / "docs/adr").glob("*.md"):
            self.assertIn("Status: PROPOSED", p.read_text())
        for comp, (state, arts, _, _) in R.items():
            for a in arts:
                self.assertTrue((PKG_DIR / a).exists(), f"{comp}: {a}")


class ShallTest(unittest.TestCase):
    """MC-05 SHALL spec: every requirement names checks and an existing test class."""

    def test_shall_traceable(self):
        d = json.loads((PKG_DIR / "governance/SHALL.json").read_text())
        for s in d["requirements"]:
            f, cls = s["verified_by"].split("::")
            self.assertIn(f"class {cls}", (PKG_DIR / "tests" / f).read_text(), s["id"])


class RtmTest(unittest.TestCase):
    """MC-06 RTM generation + validator."""

    def test_rtm(self):
        r = run("rtm.py"); self.assertEqual(r.returncode, 0, r.stdout)
        rows = json.loads((PKG_DIR / "evidence/RTM.json").read_text())["rows"]
        self.assertEqual(len(rows), 100); self.assertFalse(any(x["gate"] == "PASS" for x in rows))


class BenchTest(unittest.TestCase):
    """MC-35/36 bench harness + gate: thresholds PROPOSED, regression detected."""

    def test_gate_detects_regression(self):
        import tempfile, os
        base = {"results": [{"nodes": 1000, "p99_ms": 1.0, "p50_ms": 0.5}], "peak_kib_5000": 1,
                "service_results": [{"nodes": 1000, "p99_ms": 1.0}]}
        cur = json.loads(json.dumps(base)); cur["results"][0]["p99_ms"] = 2.0
        d = tempfile.mkdtemp(); bp, cp = os.path.join(d, "b.json"), os.path.join(d, "c.json")
        json.dump(base, open(bp, "w")); json.dump(cur, open(cp, "w"))
        r = run("bench.py", "--gate", cp, "--baseline", bp)
        self.assertEqual(r.returncode, 1); self.assertIn("regression@1000", r.stdout)
        r = run("bench.py", "--gate", bp)
        self.assertIn("met_under_proposed_thresholds", r.stdout)


class CanaryTest(unittest.TestCase):
    """MC-51 staged rollout: breach and insufficient samples both roll back."""

    def arms(self, cand_ref, n=500):
        return lambda f: ({"n": n, "refusals": 5, "p99": 10}, {"n": n, "refusals": cand_ref, "p99": 10})

    def test_rollout(self):
        done = []
        self.assertEqual(canary.Rollout().run(self.arms(5), lambda: done.append("p"), lambda: done.append("r")), "PROMOTED")
        self.assertEqual(canary.Rollout().run(self.arms(100), lambda: None, lambda: done.append("r")), "ROLLED_BACK")
        ro = canary.Rollout()
        self.assertEqual(ro.run(self.arms(5, n=10), lambda: None, lambda: None), "ROLLED_BACK")
        self.assertEqual(ro.history[0].verdict, "INSUFFICIENT")


class ExitGateTest(unittest.TestCase):
    """MC-57/58 exit gate: NO_GO as delivered; GO reachable only with every input real (falsifier)."""

    def good(self):
        reg = {k: ("IMPLEMENTED_TESTED", [], [], "") for k in R}
        return {"owners": {"service_owner": "Jane Doe", "backup_owner": "Raj Patel", "approver": "Ana Lima"},
                "shall": {"status": "APPROVED", "approver": "Ana Lima"}, "provenance": {"status": "VERIFIED"},
                "ci": {"verdict": "PASS"}, "bench_gate": {"verdict": "PASS", "thresholds": {"status": "APPROVED"}},
                "release_approval": {"approver": "Ana Lima"}, "registry": reg, "waivers": {"waivers": []}}

    def test_delivered_is_no_go(self):
        self.assertEqual(exit_gate.evaluate()["verdict"], "NO_GO")

    def test_gate_is_a_gate_not_a_wall(self):
        """Synthetic, non-delivered inputs: all real -> GO; each single omission -> NO_GO."""
        self.assertEqual(exit_gate.evaluate(inputs=self.good())["verdict"], "GO")
        breaks = {"owners": {"service_owner": "UNASSIGNED", "backup_owner": "x y", "approver": "a b"},
                  "shall": {"status": "PROPOSED"}, "provenance": {"status": "EVIDENCE_GAP"}, "ci": {"verdict": "FAIL"},
                  "bench_gate": {"verdict": "PASS", "thresholds": {"status": "PROPOSED"}},
                  "release_approval": {"approver": "Claude"}}
        for k, v in breaks.items():
            inp = self.good(); inp[k] = v
            self.assertEqual(exit_gate.evaluate(inputs=inp)["verdict"], "NO_GO", k)
        inp = self.good(); inp["registry"] = dict(inp["registry"], **{"MC-32": ("BLOCKED_EXTERNAL", [], [], "x")})
        self.assertEqual(exit_gate.evaluate(inputs=inp)["verdict"], "NO_GO")

    def test_waiver_rules(self):
        w = {"id": "W1", "item": "MC-32", "owner": "Jane", "scope": "s", "risk": "r", "compensating_control": "c",
             "approver": "Ana", "expires": "2026-12-31"}
        ok, errs = exit_gate.validate_waivers({"waivers": [w]}, "2026-09-23"); self.assertEqual(len(ok), 1)
        for bad in ({"expires": "2026-01-01"}, {"approver": "Jane"}, {"approver": "automation-bot"}, {"risk": ""}):
            ok, errs = exit_gate.validate_waivers({"waivers": [dict(w, **bad)]}, "2026-09-23"); self.assertFalse(ok, bad)


class SbomTest(unittest.TestCase):
    """MC-60 SBOM + checksums; licence NOASSERTION, never invented."""

    def test_sbom(self):
        r = run("sbom.py"); self.assertEqual(r.returncode, 0, r.stdout)
        d = json.loads((PKG_DIR / "sbom/sbom.cdx.json").read_text())
        self.assertEqual(d["metadata"]["component"]["licenses"][0]["expression"], "NOASSERTION")
        self.assertFalse((PKG_DIR / "LICENSE").exists())


class CiTest(unittest.TestCase):
    """MC-59/45 CI definitions present; matrix declared; only one platform executed here."""

    def test_ci_files(self):
        self.assertIn("matrix", (PKG_DIR / "ci/github-workflow.yml").read_text())
        self.assertIn("unittest discover", (PKG_DIR / "ci/ci.sh").read_text())


class EvidenceTest(unittest.TestCase):
    """MC-49 evidence bundle is generated and states it is unsigned."""

    def test_bundle(self):
        subprocess.run([sys.executable, "-B", str(PKG_DIR / "tools/evidence_bundle.py")], capture_output=True, cwd=PKG_DIR)
        d = json.loads((PKG_DIR / "evidence/RELEASE_EVIDENCE.json").read_text())
        self.assertIsNone(d["signature"]); self.assertGreater(len(d["artifacts"]), 40)


if __name__ == "__main__":
    unittest.main()
