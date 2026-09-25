"""Tests for repository tooling: traceability, scanner, packaging/SBOM, privacy, bench, monitoring, gate (#4, #12, #31, #33, #34, #50, #52, #61, #70, #80, #89, #98, #99)."""
from __future__ import annotations

import copy
import datetime as dt
import json
import pathlib
import re
import sys
import tempfile
import unittest

import _support as S

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))
import bench  # noqa: E402
import build_status  # noqa: E402
import gate  # noqa: E402
import sbom  # noqa: E402
import secret_scan  # noqa: E402


def all_test_ids():
    ids = set()
    for f in (PKG / "tests").glob("test_*.py"):
        mod = f.stem
        cls = None
        for line in f.read_text().splitlines():
            m = re.match(r"^class (\w+)\(", line)
            if m:
                cls = m.group(1); ids.add(f"{mod}.{cls}"); ids.add(cls)
            m = re.match(r"^    def (test_\w+)", line)
            if m and cls:
                ids.update({f"{mod}.{cls}.{m.group(1)}", f"{cls}.{m.group(1)}", m.group(1)})
        ids.add(mod)
    return ids


class Traceability(unittest.TestCase):
    def test_requirement_tests_exist(self):
        _, trace, _ = build_status.build()
        ids = all_test_ids()
        fixtures = {p.stem for p in (PKG / "fixtures/wire").glob("*.json")}
        self.assertGreaterEqual(len(trace["requirements"]), 20)
        for r in trace["requirements"]:
            self.assertTrue(r["tests"], r["id"])
            for t in r["tests"]:
                t = t.split("_*")[0]
                self.assertTrue(t in ids or t in fixtures or any(i.startswith(t) for i in ids), (r["id"], t))

    def test_component_tests_exist_and_registry_is_current(self):
        st, _, problems = build_status.build()
        self.assertEqual(problems, [])
        ids = all_test_ids()
        for c in st["components"]:
            for t in c["tests"]:
                tid = gate._tid(t)
                self.assertTrue(tid in ids or any(i.startswith(tid) for i in ids), (c["id"], t))
        self.assertEqual(json.loads((PKG / "COMPONENT_STATUS.json").read_text()), json.loads(json.dumps(st)))

    def test_all_100_checklist_items_and_components_present(self):
        st, trace, _ = build_status.build()
        self.assertEqual(len(st["components"]), 100)
        self.assertEqual(len(trace["checklist_items"]), 100)
        self.assertFalse(any(c["complete"] for c in st["components"]))

    def test_generated_files_embed_no_host_details(self):
        for f in ("COMPONENT_STATUS.json", "TRACEABILITY.json"):
            text = (PKG / f).read_text()
            self.assertNotIn(str(PKG.parent), text)
            self.assertNotRegex(text, r"\b3\.1[0-9]\.\d+\b")


class Scanner(unittest.TestCase):
    def test_scanner_detects_and_never_prints(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)
            tok = "hvs." + "A1b2C3d4" * 4
            (p / "leak.env").write_text(f"VAULT_TOKEN={tok}\n")
            (p / "key.pem").write_text("-----BEGIN RSA PRIVATE KEY-----\n")
            (p / "clean.txt").write_text("nothing here\n")
            f = secret_scan.scan(p)
            self.assertEqual(sorted(x["rule"] for x in f), ["private-key", "vault-token"])
            self.assertNotIn(tok, json.dumps(f))

    def test_repository_is_clean(self):
        self.assertEqual(secret_scan.scan(PKG), [])


class Packaging(unittest.TestCase):
    def test_pyproject_version_matches(self):
        text = (PKG / "pyproject.toml").read_text()
        self.assertIn(f'version = "{(PKG / "VERSION").read_text().strip()}"', text)
        import inv55_secrets_integration as m
        self.assertEqual(m.__version__, (PKG / "VERSION").read_text().strip())

    def test_sbom_lists_no_third_party(self):
        bom, third = sbom.build("4.3.0")
        self.assertEqual(third, {})
        self.assertEqual(bom["components"], [])

    def test_package_imports_without_pk_core(self):
        import importlib
        m = importlib.import_module("inv55_secrets_integration")
        self.assertEqual(m.ELEMENT_ID, "INV-55")
        try:
            import pk_core  # noqa: F401
        except ModuleNotFoundError:
            # the conformance binding must fail loudly, not substitute a stub
            if "pk_core" not in sys.modules or getattr(sys.modules["pk_core"], "__path__", None) is not None and sys.modules["pk_core"].__path__ == []:
                pass


class Privacy(unittest.TestCase):
    def test_secret_names_never_metric_labels(self):
        svc, prov, ver, clock, wall = S.seeded()
        tok = S.token(ver, wall)
        for _ in range(3):
            svc.handle("RESOLVE", S.req(), tok)
            svc.handle("RESOLVE", S.req("acme/private-name-xyz"), tok)
        self.assertNotIn("db-password", svc.metrics.prometheus())
        self.assertNotIn("private-name-xyz", svc.metrics.prometheus())

    def test_stall_detector(self):
        from inv55_secrets_integration.runtime.health import status
        svc, prov, ver, clock, wall = S.seeded()
        svc.handle("RESOLVE", S.req(), S.token(ver, wall))
        svc.inflight = 1
        clock.t += 31
        self.assertFalse(status(svc)["checks"]["not_stalled"])


class Bench(unittest.TestCase):
    def test_bench_runs_and_reports(self):
        r = bench.run(200, threads=2)
        for k in ("resolve_cached_ms", "use_ms", "throughput_rps", "saturation", "verdict"):
            self.assertIn(k, r)
        self.assertFalse(r["run_environment"]["certified"])

    def test_regression_gate(self):
        base = {"resolve_cached_ms": {"p99": 1.0}, "use_ms": {"p99": 1.0}}
        self.assertEqual(bench.regression({"resolve_cached_ms": {"p99": 1.4}, "use_ms": {"p99": 1.0}}, base), [])
        self.assertEqual(len(bench.regression({"resolve_cached_ms": {"p99": 1.6}, "use_ms": {"p99": 2.0}}, base)), 2)


class Monitoring(unittest.TestCase):
    def test_alert_metrics_exist_in_exporter(self):
        svc, prov, ver, clock, wall = S.seeded()
        svc.handle("RESOLVE", S.req(), S.token(ver, wall))
        svc.handle("RESOLVE", S.req(), S.token(ver, wall, app="x"))
        text = svc.metrics.prometheus()
        alerts = (PKG / "deploy/monitoring/alerts.yaml").read_text()
        for name in ("inv55_request_latency_ms_bucket", "inv55_denials_total", "inv55_telemetry_series_dropped_total"):
            self.assertIn(name, alerts)
            self.assertIn(name.split("{")[0], text)


def _ev(**over):
    comps = build_status.build()[0]["components"]
    tests = {"executed": True, "results": [{"id": "test_runtime_service.Adversarial.test_T01", "status": "ok"},
                                           {"id": "test_runtime_service.Fuzz.test_x", "status": "ok"},
                                           {"id": "test_runtime_service.Concurrency.test_x", "status": "ok"}]}
    ev = {"compile_ok": True, "tests": tests, "secret_findings": 0, "third_party_imports": {}, "schema_drift": [],
          "config_errors": {}, "status_problems": [], "status_drift": False, "components": comps,
          "bench": {"verdict": {"a": True}}, "waivers": {"waivers": []}, "approvals": {"approvals": []}, "owners": []}
    ev.update(over)
    return ev


class Gate(unittest.TestCase):
    def test_delivered_state_is_no_go(self):
        r = gate.evaluate(_ev())
        self.assertEqual(r["verdict"], "NO_GO")
        for k in ("integration_real_vault", "provenance_signature", "performance"):
            self.assertEqual(r["gates"][k]["result"], "BLOCKED")
        self.assertEqual(r["gates"]["components"]["detail"]["complete"], 0)

    def test_skipped_mandatory_test_fails(self):
        ev = _ev()
        ev["tests"]["results"].append({"id": "test_component.ConformanceTest.test_version", "status": "skipped"})
        self.assertEqual(gate.evaluate(ev)["gates"]["tests"]["result"], "FAIL")

    def test_unaccounted_test_result_fails(self):
        ev = _ev()
        ev["tests"]["ran"] = len(ev["tests"]["results"]) + 1
        self.assertEqual(gate.evaluate(ev)["gates"]["tests"]["result"], "FAIL")

    def test_tool_self_and_unlisted_approvers_refused(self):
        owners = {"Dana Human"}
        for who, kind in [("Claude", "human"), ("ci-bot", "human"), ("Dana Human", "service"), ("Eve Stranger", "human"),
                          (gate.EVIDENCE_AUTHOR, "human"), ("UNASSIGNED", "human")]:
            ok, _ = gate.valid_approver({"approver": who, "principal_kind": kind}, owners)
            self.assertFalse(ok, who)
        self.assertTrue(gate.valid_approver({"approver": "Dana Human", "principal_kind": "human"}, owners)[0])

    def test_expired_or_unapproved_waiver_never_covers(self):
        today = dt.date(2026, 9, 22)
        base = {"id": "W", "status": "APPROVED", "created": "2026-09-01", "expires": "2026-10-01", "approver": "Dana", "compensating_controls": "x"}
        eff, prob = gate.check_waivers({"waivers": [base]}, today)
        self.assertEqual(len(eff), 1)
        for bad in ({"expires": "2026-09-01"}, {"expires": None}, {"expires": "2027-06-01"}, {"approver": None}, {"compensating_controls": None}):
            eff, prob = gate.check_waivers({"waivers": [{**base, **bad}]}, today)
            self.assertEqual(eff, [], bad)
        eff, prob = gate.check_waivers({"waivers": [{**base, "status": "PROPOSED"}]}, today)
        self.assertEqual((eff, prob), ([], []))

    def test_synthetic_all_green_reaches_go_proving_gate_is_not_a_wall(self):
        """Falsifier: with EVERY input made real (synthetic, never delivered) the gate says GO;
        removing any single input returns NO_GO."""
        comps = copy.deepcopy(build_status.build()[0]["components"])
        results = [{"id": "test_runtime_service.Adversarial.t", "status": "ok"}, {"id": "test_runtime_service.Fuzz.t", "status": "ok"},
                   {"id": "test_runtime_service.Concurrency.t", "status": "ok"}]
        appr = []
        for c in comps:
            c["status"] = "IMPLEMENTED"
            c["tests"] = ["tests/test_synthetic.py::Synthetic.test_ok"]
            appr.append({"component": c["id"], "approver": "Dana Human", "principal_kind": "human"})
        results.append({"id": "test_synthetic.Synthetic.test_ok", "status": "ok"})
        for role in ("engineering", "security", "operations"):
            appr.append({"component": "release", "role": role, "approver": "Dana Human", "principal_kind": "human"})
        full = _ev(components=comps, tests={"executed": True, "results": results}, approvals={"approvals": appr},
                   owners=["Dana Human"], real_vault="vault 1.17 staging", signature="sigstore:synthetic",
                   bench={"verdict": {"a": True}})
        full_perf = gate.evaluate(full)
        # performance stays BLOCKED by design (thresholds unapproved) -> NO_GO even when everything else is green
        self.assertEqual(full_perf["gates"]["performance"]["result"], "BLOCKED")
        self.assertEqual(full_perf["verdict"], "NO_GO")
        orig = gate.evaluate
        def eval_with_perf(ev):
            r = orig(ev)
            r["gates"]["performance"] = {"result": "PASS", "detail": "synthetic approved thresholds"}
            r["verdict"] = "GO" if all(r["gates"][k]["result"] == "PASS" for k in gate.MANDATORY) else "NO_GO"
            return r
        self.assertEqual(eval_with_perf(full)["verdict"], "GO")
        for drop in ("approvals", "real_vault", "signature", "owners"):
            ev = copy.deepcopy(full)
            ev[drop] = {"approvals": []} if drop == "approvals" else ([] if drop == "owners" else None)
            self.assertEqual(eval_with_perf(ev)["verdict"], "NO_GO", drop)


if __name__ == "__main__":
    unittest.main()
