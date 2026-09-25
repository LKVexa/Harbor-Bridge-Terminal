"""MC-001/004/010/017/027/032/035/040/041: governance, release and packaging artifacts."""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import re
import subprocess
import sys
import unittest

from _support import CTRL_A, PKG_DIR, make_service


def _load(name):
    spec = importlib.util.spec_from_file_location(f"inv58_tool_{name}", PKG_DIR / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rtm = _load("rtm")
gate = _load("release_gate")


class ReleaseArtifactTest(unittest.TestCase):
    def test_rtm_complete_and_resolvable(self):
        data, problems = rtm.build()
        self.assertEqual(problems, [])
        self.assertEqual(data["row_count"], 100)
        ids = [r["check_id"] for r in data["rows"]]
        self.assertEqual(ids, [f"INV-58-C{i:03d}" for i in range(1, 101)])
        for r in data["rows"]:
            self.assertTrue(all(x["resolved"] for x in r["implementation"] + r["docs"]), r["check_id"])

    def test_rtm_rejects_dangling_references(self):
        probs = []
        rtm.resolve_ref("service.py::NoSuchThing", probs, "X")
        rtm.resolve_ref("docs/NOPE.md", probs, "Y")
        rtm.resolve_ref("docs/REQUIREMENTS.md#no-such-anchor", probs, "Z")
        self.assertEqual(len(probs), 3)

    def test_bom_and_compat_matrix(self):
        bom = json.loads((PKG_DIR / "governance/bom.json").read_text())
        self.assertEqual(bom["runtime"]["third_party_runtime_dependencies"], [])
        self.assertIn(bom["framework"]["status"], ("BLOCKED", "PINNED"))
        compat = json.loads((PKG_DIR / "governance/compatibility_matrix.json").read_text())
        version = (PKG_DIR / "VERSION").read_text().strip()
        self.assertEqual(compat["component"][version], "supported")
        states = set(compat["states"])
        for section in ("component", "python", "platforms", "pk_core", "istio", "adjacent"):
            for k, v in compat[section].items():
                self.assertIn(v.split(" ")[0], states, f"{section}.{k}")
        self.assertIn(f"{sys.version_info.major}.{sys.version_info.minor}", compat["python"])

    def test_bootstrap_preflight_runs(self):
        r = subprocess.run([sys.executable, "-B", str(PKG_DIR / "tools/bootstrap.py"), "--dev-keys", "--json"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        out = json.loads(r.stdout)
        by = {c["check"]: c["status"] for c in out["checks"]}
        self.assertEqual(by["bootstrap -> ready"], "PASS")
        self.assertIn(by["pk_core framework"], ("PASS", "BLOCKED"))

    def test_stall_detection(self):
        svc, clock, _ = make_service()
        self.assertFalse(svc.health()["stalled"])
        svc._admission.try_acquire("alpha")  # an in-flight request that never completes
        clock.advance(31)
        h = svc.health()
        self.assertTrue(h["stalled"])
        self.assertFalse(h["live"])
        svc._admission.release("alpha")
        svc.reconcile(CTRL_A, "alpha", "a", 2, 1)
        self.assertFalse(svc.health()["stalled"])
        for _ in range(25):
            try:
                svc.reconcile(CTRL_A, "alpha", "a", 0, 1)
            except Exception:
                pass
        self.assertTrue(svc.health()["error_burst"])

    def test_alerts_cover_required_classes(self):
        alerts = json.loads((PKG_DIR / "ops/alerts.json").read_text())
        classes = {a["class"] for a in alerts["alerts"]}
        self.assertEqual(classes, set(alerts["classes"]))
        catalog = importlib.import_module(PKG_DIR.name + ".telemetry").METRIC_CATALOG
        for a in alerts["alerts"]:
            for m in re.findall(r"inv58_[a-z_]+", a["expr"]):
                self.assertIn(m, catalog, a["id"])
            self.assertTrue((PKG_DIR / a["runbook"].split("#")[0]).exists(), a["id"])
        for d in json.loads((PKG_DIR / "ops/dashboards.json").read_text())["dashboards"]:
            for p in d["panels"]:
                if "metric" in p:
                    self.assertIn(p["metric"], catalog)

    def test_waiver_register_rules(self):
        today = dt.date(2026, 9, 22)
        self.assertEqual(gate.check_waivers(json.loads((PKG_DIR / "governance/waivers.json").read_text()), today), [])
        bad = {"waivers": [
            {"id": "W1", "owner": "UNASSIGNED", "created": "2026-09-01", "expires": "2026-10-01", "rationale": "r", "risk": "r", "compensating_controls": "c", "requirement": "C1"},
            {"id": "W2", "owner": "Pat", "created": "2026-01-01", "expires": "2026-02-01", "rationale": "r", "risk": "r", "compensating_controls": "c", "requirement": "C1"},
            {"id": "W3", "owner": "Pat", "created": "2026-09-01", "expires": "2027-09-01", "rationale": "r", "risk": "r", "compensating_controls": "c", "requirement": "C1"},
            {"id": "W4", "owner": "Pat", "created": "2026-09-01", "expires": "2026-10-01"}]}
        probs = gate.check_waivers(bad, today)
        for w in ("W1", "W2", "W3", "W4"):
            self.assertTrue(any(w in p for p in probs), w)

    def test_release_gate_is_fail_closed(self):
        self.assertEqual(gate.verdict(["x"], []), ("ENGINEERING_FAIL", 1))
        self.assertEqual(gate.verdict([], ["owner missing"]), ("NO_GO", 3))
        self.assertEqual(gate.verdict([], []), ("GO", 0))  # falsifier: GO is reachable once blockers are closed
        self.assertIn("pk_core", gate.EXPECTED_SKIP_MARKERS)

    def test_readme_declared_artifacts_exist_or_are_tracked(self):
        readme = (PKG_DIR / "README.md").read_text()
        missing_tracked = {"MASTER.md"}
        generated = {"release/ACCEPTANCE_RECORD.json", "perf/results.json"}  # produced by tools, verified by the gate
        for ref in set(re.findall(r"`([A-Za-z0-9_./-]+\.(?:md|json|py|toml|yml))`", readme)):
            if ref in generated:
                continue
            if ref in missing_tracked:
                self.assertIn(ref, (PKG_DIR / "POST_AUDIT_MISSING_COMPONENTS.md").read_text())
                continue
            self.assertTrue((PKG_DIR / ref).exists() or (PKG_DIR.parent / ref).exists(), ref)

    def test_changelog_and_package_metadata_agree(self):
        version = (PKG_DIR / "VERSION").read_text().strip()
        self.assertIn(f'version = "{version}"', (PKG_DIR / "pyproject.toml").read_text())
        self.assertIn(f"## {version} -", (PKG_DIR / "CHANGELOG.md").read_text())
        self.assertIn(f'"version": "{version}"', (PKG_DIR / "governance/bom.json").read_text())


import importlib  # noqa: E402

if __name__ == "__main__":
    unittest.main()
