"""Governance, documentation, supply-chain and gate tests (Sections 1, 2, 4, 7, 17, 23, 24)."""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
import unittest

from _common import PKG_DIR, ROOT

sys.path.insert(0, str(PKG_DIR / "tools"))
import governance_check  # noqa: E402

from inv41_capability_security import preflight  # noqa: E402

TODAY = dt.date(2026, 9, 22)


class GovernanceTest(unittest.TestCase):
    def test_GV001_owners_schema(self):
        owners = json.loads((PKG_DIR / "OWNERS.json").read_text())
        codeowners = (PKG_DIR / "CODEOWNERS").read_text()
        errs, warns = governance_check.check_owners(owners, codeowners, today=TODAY, production=False)
        self.assertEqual(errs, [])
        perrs, _ = governance_check.check_owners(owners, codeowners, today=TODAY, production=True)
        self.assertTrue(any("backup_owner" in e for e in perrs), "placeholders must fail production")
        broken = json.loads(json.dumps(owners))
        broken["roles"]["security_approver"]["kind"] = "service"
        del broken["escalation"][0]["ack_minutes"]
        e2, _ = governance_check.check_owners(broken, codeowners.replace("@SECURITY-APPROVER-UNASSIGNED", ""), today=TODAY,
                                              production=False)
        self.assertTrue(any("must be human" in e for e in e2))
        self.assertTrue(any("two reviewers" in e for e in e2))
        self.assertTrue(any("ack_minutes" in e for e in e2))
        e3, _ = governance_check.check_owners(owners, codeowners, today=TODAY + dt.timedelta(days=400), production=True)
        self.assertIn("owner review is stale", e3)

    def test_GV002_waiver_expiry_fails(self):
        exc = json.loads((PKG_DIR / "EXCEPTIONS.json").read_text())
        errs, _ = governance_check.check_waivers(exc, today=TODAY, production=False)
        self.assertEqual(errs, [])
        errs, _ = governance_check.check_waivers(exc, today=dt.date(2027, 1, 1), production=False)
        self.assertTrue(any("EXPIRED" in e for e in errs))
        long = {"entries": [dict(exc["entries"][0], expires="2027-09-22")]}
        errs, _ = governance_check.check_waivers(long, today=TODAY, production=False)
        self.assertTrue(any("exceeds 90 days" in e for e in errs))

    def test_GV003_stdlib_only(self):
        self.assertEqual(governance_check.check_imports(), [])

    def test_GV004_docs_present_and_cross_referenced(self):
        docs = ["README.md", "SECURITY.md", "docs/ADR-0001-explicit-capabilities.md", "docs/REQUIREMENTS.md",
                "docs/THREAT_MODEL.md", "docs/OPERATIONS.md", "docs/DATA_PROTECTION.md", "docs/COMPATIBILITY.md",
                "docs/OBSERVABILITY.md", "NOTICE", "OWNERS.md"]
        for d in docs:
            self.assertTrue((PKG_DIR / d).exists(), d)
        for d in ("README.md", "SECURITY.md", "docs/THREAT_MODEL.md", "docs/REQUIREMENTS.md"):
            self.assertIn("ADR-0001", (PKG_DIR / d).read_text(), d)
        req = (PKG_DIR / "docs" / "REQUIREMENTS.md").read_text().lower()
        self.assertIn("precedence", req)
        ops = (PKG_DIR / "docs" / "OPERATIONS.md").read_text().lower()
        for h in ("telemetry policy", "incident", "rollout", "vulnerability", "reconstruction", "day-0", "day-1",
                  "day-2", "recurring reviews", "support", "failure taxonomy"):
            self.assertIn(h, ops, h)

    def test_GV005_alerts_link_runbooks(self):
        alerts = json.loads((PKG_DIR / "ops" / "alerts.json").read_text())["alerts"]
        ops = (PKG_DIR / "docs" / "OPERATIONS.md").read_text()
        for a in alerts:
            for k in ("expr", "severity", "owner", "runbook"):
                self.assertTrue(a.get(k), (a["id"], k))
            anchor = a["runbook"].split("#")[1]
            self.assertIn(f'<a id="{anchor}"></a>', ops, anchor)

    def test_GV006_preflight_refuses_unsupported_runtime(self):
        self.assertTrue(preflight.run()["ok"])
        self.assertFalse(preflight.run(version_info=(3, 8, 0))["ok"])
        self.assertFalse(preflight.run(implementation="PyPy")["ok"])
        self.assertFalse(preflight.run(profile="mars")["ok"])

    def test_GV007_traceability_is_clean(self):
        p = subprocess.run([sys.executable, "-B", str(PKG_DIR / "tools" / "traceability.py")], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout[-3000:])
        body = json.loads((PKG_DIR / "evidence" / "TRACEABILITY.json").read_text())
        self.assertEqual(len(body["audit"]), 100)

    def test_GV008_release_gate_refuses_go_with_blockers(self):
        import release_gate
        r = release_gate.evaluate(today=TODAY)
        self.assertEqual(r["verdict"], "NO_GO")
        self.assertTrue(r["open_blockers"])
        states = {i["id"]: i["state"] for i in r["items"]}
        self.assertIn(states["EXIT-10"], ("BLOCKED", "FAIL"))

    def test_GV009_threat_model_mapping_complete(self):
        th = json.loads((PKG_DIR / "docs" / "threats.json").read_text())["threats"]
        reqs = {r["id"] for r in json.loads((PKG_DIR / "requirements" / "REQUIREMENTS.json").read_text())["requirements"]}
        mut = (PKG_DIR / "tools" / "mutation.py").read_text()
        for t in th:
            self.assertTrue(t["tests"], t["id"])
            self.assertTrue(set(t["requirements"]) <= reqs, t["id"])
            for m in t["mutants"]:
                self.assertIn(f'("{m}"', mut, (t["id"], m))
            if t["severity"] in ("critical", "high") and not t["requires_external_isolation"]:
                self.assertTrue(t["mutants"] or t["id"] == "T-SUPPLY", f"{t['id']} has no mutant")

    def test_GV010_perf_gate_trips_on_regression_and_slo_breach(self):
        import bench
        base = json.loads((PKG_DIR / "perf" / "baseline.json").read_text())
        slo = json.loads((PKG_DIR / "perf" / "slo.json").read_text())
        ops = {k: dict(v) for k, v in base["operations"].items()}
        fake = {"fingerprint": dict(base["fingerprint"]), "operations": ops, "selfcheck_ms": 1.0,
                "memory_per_object": {k: 1 for k in slo["memory_bytes_max"]}}
        self.assertTrue(bench.gate(fake)["pass"])
        ops["grant"]["best_round_p50_us"] = ops["grant"].get("best_round_p50_us", ops["grant"]["p50_us"]) * 2
        g = bench.gate(fake)
        self.assertFalse(g["pass"])
        self.assertTrue(g["blocking"])
        ops["grant"]["best_round_p50_us"] /= 2
        ops["use_allowed"]["p99_us"] = 10 ** 6
        self.assertTrue(bench.gate(fake)["slo_breaches"])
        fake["fingerprint"]["python"] = "0.0"
        self.assertFalse(bench.gate(fake)["blocking"], "off-reference runs are advisory")


if __name__ == "__main__":
    unittest.main()
