"""P2 verification/release/governance: fixtures (34), benchmark (39), release bundle (40), RTM (41), ADR (42),
owners (43), bootstrap (44), supply chain (45), rollout (46), runbooks (48), exit gate (50), MASTER.md (51)."""
import io
import contextlib
import json
import os
import re
import statistics
import tempfile
import time
import unittest

from fixtures import ENV, PART, T0, World, art
from gap15_runtime_compatibility_certification.production import (config, fixtures_matrix, ops, release, serve,
                                                                   signing)
from gap15_runtime_compatibility_certification.production.state import CertKey

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EVIDENCE = os.path.join(PKG, "evidence")


class FixtureMatrixTest(unittest.TestCase):
    def test_inventory_risk_based_matrix_and_gaps(self):
        """controls: 34-01 34-02 34-06 34-09"""
        m = fixtures_matrix.load_manifest(os.path.join(PKG, "deploy", "supported-versions.json"))
        cells = fixtures_matrix.generate(m)
        high = [k for k, v in m["matrix_dimensions"].items() if v["criticality"] == "high"]
        n_high = 1
        for k in high:
            n_high *= len(m["matrix_dimensions"][k]["values"])
        self.assertGreaterEqual(len(cells), n_high)  # full coverage of high-criticality dims
        combos = {tuple(c[k] for k in sorted(high)) for c in cells}
        self.assertEqual(len(combos), n_high)
        cov = fixtures_matrix.coverage(cells, set())
        self.assertEqual((cov["tested"], cov["ratio"]), (0, 0.0))  # new cells are visible gaps by default

    def test_results_carry_harness_identity(self):
        """controls: 34-03 34-05 34-08"""
        w = World()
        w.svc.ingest(w.producer(), w.evidence())
        ts = w.store.events()[-1]["test_suite"]
        self.assertTrue({"id", "version", "harness_digest"} <= set(ts))
        self.assertTrue(ts["harness_digest"].startswith("sha256:"))

    def test_fixture_categories_present(self):
        """controls: 34-04"""
        w = World()
        w.svc.ingest(w.producer(), w.evidence(digest=art(1)))
        w.svc.ingest(w.producer(), w.evidence(digest=art(2), result="incompatible", failure_class="deterministic"))
        w.svc.ingest(w.producer(), w.evidence(digest=art(3), features=[{"feature": "wasi:io/streams", "result": "passed"}]))
        results = sorted(e["result"] for e in w.store.events())
        self.assertEqual(results, ["compatible", "compatible", "incompatible"])

    def test_retired_runtime_history_preserved(self):
        """controls: 34-10"""
        w = World()
        r = w.svc.ingest(w.producer(), w.evidence())
        w.svc.lifecycle(w.operator(), partition=PART, runtime="wasmtime@21.0.0", state="end-of-life", effective_at=T0,
                        reason="retired", source="lab")
        rows = w.store.lookup(PART, runtime="wasmtime@21.0.0")
        self.assertEqual([e["event_type"] for e in rows], ["evidence", "lifecycle"])


class BenchmarkTest(unittest.TestCase):
    def test_latency_throughput_envelope_recorded(self):
        """controls: 39-01 39-02 39-03 39-04 39-05 39-09 39-10 26-03"""
        import platform
        import resource
        import sqlite3
        w = World(ttl_s=10**6)
        ingest, cert = [], []
        keys = []
        n = 60
        for i in range(n):
            raw = w.evidence(digest=art(i))
            tok = w.producer()
            t0 = time.perf_counter()
            r = w.svc.ingest(tok, raw)
            ingest.append(time.perf_counter() - t0)
            keys.append(w.key_for(r, digest=art(i)))
        for i in range(300):
            tok = w.reader()
            t0 = time.perf_counter()
            w.svc.certify(tok, keys[i % n])
            cert.append(time.perf_counter() - t0)

        def pct(xs, p):
            xs = sorted(xs)
            return round(xs[min(len(xs) - 1, int(p / 100 * len(xs)))] * 1000, 3)
        rep = {"schema": "GAP15_BENCHMARK/1", "measured_at": int(time.time()),
               "environment": {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
                               "platform": platform.platform(), "cpu_count": os.cpu_count()},
               "workload": {"ingest_ops": n, "certify_ops": len(cert), "path": "full: authn+authz+schema+ed25519 x3+provenance+attestation+commit"},
               "ingest_ms": {"p50": pct(ingest, 50), "p95": pct(ingest, 95), "p99": pct(ingest, 99), "max": round(max(ingest) * 1000, 3)},
               "certify_ms": {"p50": pct(cert, 50), "p95": pct(cert, 95), "p99": pct(cert, 99), "max": round(max(cert) * 1000, 3)},
               "ingest_ops_per_s": round(n / sum(ingest), 1), "certify_ops_per_s": round(len(cert) / sum(cert), 1),
               "max_rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               "db_bytes": os.path.getsize(w.db_path),
               "note": "single process, local SSD, cloud container; not a fleet-scale or soak result"}
        os.makedirs(EVIDENCE, exist_ok=True)
        json.dump(rep, open(os.path.join(EVIDENCE, "BENCHMARK.json"), "w"), indent=2)
        self.assertLess(rep["certify_ms"]["p99"], 250)
        self.assertLess(rep["ingest_ms"]["p99"], 2000)


class ReleaseBundleTest(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.w.trust.add(signing.TrustedKey("release-key", "release-bot", self.w.kp.generate("release-key"),
                                            scopes=frozenset({"gate:sign"})))
        self.w.trust.add(signing.TrustedKey("reviewer-key", "human-reviewer", self.w.kp.generate("reviewer-key"),
                                            scopes=frozenset({"gate:review", "gate:approval"})))
        self.build = release.tree_digest(PKG)["root"]

    def inputs(self, **over):
        out = []
        for kind in release.MANDATORY_INPUTS:
            key = "reviewer-key" if kind in ("review", "approval") else "release-key"
            body = over.get(kind, {"status": "pass"})
            inp = release.GateInput(kind, over.get(f"{kind}_build", self.build), over.get(f"{kind}_at", T0), body)
            out.append(release.sign_input(self.w.kp, key, inp))
        return out

    def test_gate_go_only_with_complete_signed_bound_evidence(self):
        """controls: 50-01 50-02 50-03 50-04 50-05 40-01 40-02 40-08"""
        d = release.exit_gate(self.inputs(), build_digest=self.build, trust=self.w.trust, now=T0 + 10)
        self.assertEqual(d["decision"], "GO")
        self.assertEqual(d["gate_policy_revision"], release.GATE_POLICY_REVISION)

    def test_gate_rejects_missing_stale_mismatched_unsigned_selfreview(self):
        """controls: 50-03 50-10 40-10"""
        ins = self.inputs()
        d = release.exit_gate(ins[:-1], build_digest=self.build, trust=self.w.trust, now=T0 + 10)
        self.assertEqual((d["decision"], d["inputs"]["approval"]), ("NO_GO", "MISSING"))
        d = release.exit_gate(self.inputs(tests_at=T0 - 30 * 86400), build_digest=self.build, trust=self.w.trust, now=T0)
        self.assertEqual(d["inputs"]["tests"], "STALE")
        d = release.exit_gate(self.inputs(sbom_build="sha256:" + "0" * 64), build_digest=self.build, trust=self.w.trust, now=T0)
        self.assertEqual(d["inputs"]["sbom"], "MISMATCHED_BUILD")
        ins = self.inputs()
        ins[0].body = {"status": "pass", "tampered": True}  # evidence substitution after signing
        d = release.exit_gate(ins, build_digest=self.build, trust=self.w.trust, now=T0)
        self.assertTrue(d["inputs"]["tests"].startswith("UNVERIFIABLE"))
        d = release.exit_gate(self.inputs(), build_digest=self.build, trust=self.w.trust, now=T0,
                              reviewer_denylist=frozenset({"human-reviewer"}))
        self.assertEqual(d["inputs"]["review"], "SELF_REVIEW")
        d = release.exit_gate(self.inputs(security={"status": "fail"}), build_digest=self.build, trust=self.w.trust, now=T0)
        self.assertEqual(d["inputs"]["security"], "FAILED")
        # a manually typed 'pass' with no signature is not evidence
        manual = [release.GateInput(k, self.build, T0, {"status": "pass"}) for k in release.MANDATORY_INPUTS]
        self.assertEqual(release.exit_gate(manual, build_digest=self.build, trust=self.w.trust, now=T0)["decision"], "NO_GO")

    def test_release_key_cannot_sign_review(self):
        """controls: 50-06 36-04"""
        ins = self.inputs()
        ins[-1] = release.sign_input(self.w.kp, "release-key", release.GateInput("approval", self.build, T0, {"status": "pass"}))
        d = release.exit_gate(ins, build_digest=self.build, trust=self.w.trust, now=T0)
        self.assertTrue(d["inputs"]["approval"].startswith("UNVERIFIABLE"))

    def test_gate_explain_lists_every_input(self):
        """controls: 50-09 40-07"""
        d = release.exit_gate(self.inputs()[:5], build_digest=self.build, trust=self.w.trust, now=T0)
        self.assertEqual(set(d["inputs"]), set(release.MANDATORY_INPUTS))
        self.assertEqual(len(d["blockers"]), 5)


class RtmTest(unittest.TestCase):
    def test_rtm_problem_detection(self):
        """controls: 41-06 41-07"""
        rows = [release.RtmRow("A", "t", "01", "P0", "LOCALLY_VERIFIED"),
                release.RtmRow("B", "t", "01", "P0", "NOT_APPLICABLE"),
                release.RtmRow("C", "t", "01", "P0", "BLOCKED"),
                release.RtmRow("D", "t", "01", "P0", "NOT_IMPLEMENTED", implementation=["x.py"])]
        self.assertEqual(len(release.rtm_problems(rows)), 4)
        ok = release.RtmRow("E", "t", "01", "P0", "LOCALLY_VERIFIED", tests=["t"], evidence=["e"])
        self.assertEqual(release.rtm_problems([ok]), [])


class AdrOwnersRunbooksTest(unittest.TestCase):
    def test_adr_structure_and_links(self):
        """controls: 42-01 42-02 42-03 42-04 42-05 42-08"""
        adr = open(os.path.join(PKG, "docs", "ADR.md")).read()
        for n in range(1, 10):
            self.assertIn(f"## ADR-00{n}", adr)
        for mod in set(re.findall(r"`production/([a-z_0-9]+\.py)`", adr)):
            self.assertTrue(os.path.exists(os.path.join(PKG, "production", mod)), mod)
        for word in ("Decision", "Consequences", "Alternatives considered"):
            self.assertIn(word, adr)

    def test_owner_validation_reports_placeholders(self):
        """controls: 43-07 43-09"""
        doc = json.load(open(os.path.join(PKG, "docs", "OWNERS.json")))
        problems = ops.validate_owners(doc)
        self.assertEqual(len(problems), len(ops.ROLES))  # every role unassigned -> reported, never accepted
        good = {r: {"name": "Real Person", "contact": "rp@example.org"} for r in ops.ROLES}
        self.assertEqual(ops.validate_owners(good), [])

    def test_runbooks_cover_required_sections(self):
        """controls: 48-01 48-02 48-03 48-04 48-05 48-06 48-07 48-08 47-08"""
        rb = open(os.path.join(PKG, "docs", "RUNBOOKS.md")).read()
        for anchor in ("rb-day0", "rb-day1", "rb-day2", "rb-incident", "rb-disconnected", "rb-audit-chain", "rb-backup"):
            self.assertIn(f'id="{anchor}"', rb)
        self.assertIn("Preserve evidence first", rb)
        self.assertIn("admissions stop", rb)


class BootstrapSupplyChainTest(unittest.TestCase):
    def test_config_schema_secure_defaults_and_secrets(self):
        """controls: 44-03 44-05 44-06"""
        cfg = json.load(open(os.path.join(PKG, "deploy", "config.example.json")))
        self.assertEqual(config.validate_config(cfg), [])
        bad = dict(cfg, **{"signing.key_ref": "plaintext-key", "store.synchronous": "OFF"})
        bad["api_password"] = "x"
        probs = config.validate_config(bad)
        self.assertTrue(any("secret reference" in p for p in probs))
        self.assertTrue(any("not in" in p for p in probs))
        self.assertTrue(any("unknown key" in p for p in probs))
        self.assertTrue(any("development" in p for p in config.validate_config(dict(cfg, **{"signing.key_provider": "development"}))))

    def test_preflight_and_production_start_refusal(self):
        """controls: 44-04 44-08 44-10"""
        w = World()
        cfg = json.load(open(os.path.join(PKG, "deploy", "config.example.json")))
        d = tempfile.mkdtemp()
        os.chmod(d, 0o700)
        rep = release.preflight(data_dir=d, config=cfg, trust=w.trust, clock_ok=True)
        self.assertTrue(rep["ok"], rep)
        rep = release.preflight(data_dir=d, config={}, trust=signing.TrustStore(), clock_ok=False)
        self.assertFalse(rep["ok"])
        path = os.path.join(d, "cfg.json")
        json.dump(cfg, open(path, "w"))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(serve.main(["--config", path]), 3)
        self.assertIn("E_KEY_PROVIDER_UNAVAILABLE", buf.getvalue())

    def test_deployment_manifests_least_privilege(self):
        """controls: 44-02 14-10"""
        unit = open(os.path.join(PKG, "deploy", "gap15.service")).read()
        for d in ("NoNewPrivileges=yes", "ProtectSystem=strict", "MemoryMax=", "LimitNOFILE=", "User=gap15"):
            self.assertIn(d, unit)
        df = open(os.path.join(PKG, "deploy", "Dockerfile")).read()
        self.assertIn("USER 10015", df)
        self.assertIn("@sha256:", df)

    def test_sbom_provenance_and_manifest(self):
        """controls: 45-01 45-02 45-04 44-01 44-07 45-09"""
        sb = release.sbom(PKG, "gap15_runtime_compatibility_certification", "4.3.0")
        prov = release.build_provenance(PKG, builder="local:cowork-build", source_revision="archive:v4.2.0+overlay",
                                        invocation=["python", "tools/run_checklist.py"])
        self.assertEqual(sb["metadata"]["subject"][7:], prov["subject"][0]["digest"]["sha256"])
        self.assertTrue(any(c["name"] == "production/store.py" for c in sb["components"]))
        self.assertEqual(json.load(open(os.path.join(PKG, "deploy", "supported-versions.json")))["service"]["version"], "4.3.0")

    def test_signed_provenance_verifies_and_tamper_detected(self):
        """controls: 45-03 45-10"""
        w = World()
        prov = release.build_provenance(PKG, builder="local", source_revision="x", invocation=[])
        sig = signing.sign_payload(w.kp, "svc-key", message_type="release-provenance", environment="release", payload=prov, signed_at=T0)
        self.assertTrue(signing.verify_payload(w.trust, sig, message_type="release-provenance", environment="release", payload=prov).ok)
        prov["subject"][0]["digest"]["sha256"] = "0" * 64
        self.assertFalse(signing.verify_payload(w.trust, sig, message_type="release-provenance", environment="release", payload=prov).ok)


class RolloutTest(unittest.TestCase):
    def test_staged_promotion_and_auto_rollback(self):
        """controls: 46-01 46-02 46-03"""
        rc = release.RolloutController()
        healthy = {"error_rate": 0.0, "incorrect_verdicts": 0, "sig_failures": 0, "replication_lag_s": 1, "saturation": 0.3, "audit_gaps": 0}
        self.assertEqual(rc.evaluate(healthy, observation_s=10)["action"], "hold")
        self.assertEqual(rc.evaluate(healthy, observation_s=900)["to"], "test")
        rc.evaluate(healthy, observation_s=900)
        self.assertEqual(rc.stage, "canary")
        bad = dict(healthy, incorrect_verdicts=1)
        r = rc.evaluate(bad, observation_s=900)
        self.assertEqual((r["action"], r["to"], r["breaches"]), ("rollback", "test", ["incorrect_verdicts"]))
        missing = {k: v for k, v in healthy.items() if k != "audit_gaps"}
        self.assertEqual(rc.evaluate(missing, observation_s=900)["action"], "rollback")  # missing signal is not healthy

    def test_rollback_schema_compat_and_canary_isolation(self):
        """controls: 46-06 46-08"""
        w = World()
        w.svc.ingest(w.producer(), w.evidence())
        from gap15_runtime_compatibility_certification.production import store as store_mod
        self.assertEqual(store_mod.Store(w.db_path).schema_version(), store_mod.SCHEMA_VERSION)
        cfg = json.load(open(os.path.join(PKG, "deploy", "config.example.json")))
        self.assertEqual(len(cfg["partitions"]), 1)


class MasterDocTest(unittest.TestCase):
    def test_master_md_absence_is_reported_not_invented(self):
        """controls: 51-07 51-08 51-09 51-10"""
        readme = open(os.path.join(PKG, "README.md")).read()
        present = os.path.exists(os.path.join(PKG, "MASTER.md"))
        self.assertFalse(present)
        claims_bundled = re.search(r"MASTER\.md[^.\n]*\b(is bundled|included in this archive)", readme)
        self.assertIsNone(claims_bundled)
        self.assertIn("MASTER.md", open(os.path.join(PKG, "MISSING_COMPONENTS.md")).read())


if __name__ == "__main__":
    unittest.main()
