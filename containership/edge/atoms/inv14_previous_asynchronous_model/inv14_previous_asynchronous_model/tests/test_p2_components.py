"""P2-21..P2-35: contract fixtures, fuzz, concurrency, bench, soak, faults, CI,
SBOM/provenance, signing, config, redaction, dashboards/alerts, runbook, waivers, EOL."""
import datetime as dt, json, os, pathlib, re, shutil, subprocess, sys, tempfile, threading, unittest
from _support import PKG_DIR, KEY, tmpdir, make_service
import polling as P, schema_check, config, redaction, governance, telemetry
TOOLS = PKG_DIR / "tools"
sys.path.insert(0, str(TOOLS))


def tool(*args, env=None):
    return subprocess.run([sys.executable, "-B", *map(str, args)], cwd=PKG_DIR, capture_output=True, text=True, env=env)


class C21ContractFixtures(unittest.TestCase):
    def test_c21_golden_fixtures_validate(self):
        g = sorted((PKG_DIR / "tests" / "fixtures" / "golden").glob("*.json"))
        self.assertGreaterEqual(len(g), 8)
        for f in g:
            d = json.loads(f.read_text())
            self.assertEqual(schema_check.check(d["instance"], d["schema_file"]), [], f.name)

    def test_c21_negative_fixtures_are_rejected(self):
        n = sorted((PKG_DIR / "tests" / "fixtures" / "negative").glob("*.json"))
        self.assertGreaterEqual(len(n), 24)
        for f in n:
            d = json.loads(f.read_text())
            self.assertTrue(schema_check.check(d["instance"], d["schema_file"]), f"{f.name} was accepted")

    def test_c21_golden_matches_current_behaviour(self):
        import gen_fixtures
        live = gen_fixtures.golden()
        for sch, inst in live.items():
            if sch in ("pk_poll_audit.schema.json",):
                continue  # audit prev/mac depend on key+clock only, compared structurally
            stored = json.loads((PKG_DIR / "tests" / "fixtures" / "golden" / (sch.replace(".schema.json", "") + ".json")).read_text())
            self.assertEqual(stored["instance"], json.loads(json.dumps(inst)), sch)


class C22Fuzz(unittest.TestCase):
    def test_c22_seeded_fuzz_has_no_findings(self):
        import fuzz
        r = fuzz.run(3000, seed=5)
        self.assertEqual(r["findings"], [])
        self.assertTrue(all(v >= 700 for v in r["per_target"].values()))

    def test_c22_regression_D02_non_json_config_is_structured(self):
        d = json.loads(json.dumps(config.BASE_CONFIG)); d["limits"]["max_pollables"] = object()
        with self.assertRaises(config.ConfigError) as cm:
            config.validate_config(d)
        self.assertEqual(cm.exception.code, "PK_CONFIG_INVALID")

    def test_c22_regression_D03_unknown_provenance_key_refused(self):
        d = json.loads(json.dumps(config.BASE_CONFIG)); d["provenance"]["zz"] = "x"
        with self.assertRaises(config.ConfigError):
            config.validate_config(d)


class C23Concurrency(unittest.TestCase):
    def test_c23_exhaustive_model_check_and_mutant_detected(self):
        import interleave
        self.assertEqual(interleave.explore(n_pollables=2, signals=(0, 1, 1), clearer=True, canceller=True)["violations"], 0)
        self.assertGreater(interleave.explore(n_pollables=1, signals=(0,), mutant="check_before_register")["violations"], 0)

    def test_c23_thread_stress_clear_vs_signal_multi_set(self):
        for _ in range(150):
            p = P.Pollable("x", "o"); sets = [P.PollSet("o") for _ in range(3)]
            res, barrier = [], threading.Barrier(5)
            def poller(ps):
                barrier.wait(); res.append(ps.poll([p], timeout_ticks=500))
            ths = [threading.Thread(target=poller, args=(s,)) for s in sets]
            ths.append(threading.Thread(target=lambda: (barrier.wait(), p.signal())))
            ths.append(threading.Thread(target=lambda: (barrier.wait(), p.clear())))
            [t.start() for t in ths]; [t.join(5) for t in ths]
            self.assertFalse(any(t.is_alive() for t in ths))
            self.assertEqual(len(res), 3)
            self.assertEqual(len(p._waiters), 0)

    def test_c23_regression_D01_service_catches_mixin_errors(self):
        svc, iss, _, _ = make_service(); o = "a/b/c"
        svc.lifecycle.transition("DRAINING", actor="t", reason="t")
        with self.assertRaises(Exception) as cm:
            svc.poll(o, [P.Pollable("x", o)], timeout_ticks=1, token=iss.mint(o))
        self.assertEqual(getattr(cm.exception, "code", None), "PK_POLL_DRAINING")


class C24Bench(unittest.TestCase):
    def test_c24_bench_runs_and_meets_proposed_thresholds(self):
        import bench
        r = bench.run(300)
        th = json.loads((PKG_DIR / "ops" / "perf_thresholds.json").read_text())
        self.assertEqual(th["status"], "PROPOSED")
        cmp_ = bench.compare(r, th)
        self.assertTrue(all(c["result"] == "met_under_proposed_threshold" for c in cmp_), cmp_)
        self.assertEqual(r["power"], "NOT_MEASURED")


class C25Soak(unittest.TestCase):
    def test_c25_soak_burst_recovery_invariants(self):
        import soak
        r = soak.run(seconds=1.5, workers=12, tenants=300)
        self.assertTrue(r["ok"], r["invariants"])
        self.assertGreater(sum(r["shed"].values()), 0)  # overload really happened


class C26Faults(unittest.TestCase):
    def test_c26_fault_scenarios(self):
        import faults
        r = faults.run(["F1_clock_backward_jump", "F2_clock_forward_jump", "F3_audit_sink_loss", "F4_signaller_stall",
                        "F6_process_kill", "F7_corrupt_checkpoint", "F8_control_plane_degraded"])
        bad = {k: v for k, v in r.items() if isinstance(v, dict) and v.get("ok") is False}
        self.assertEqual(bad, {})
        self.assertEqual(r["network_partition"]["status"], "NOT_APPLICABLE")


class C27ReleasePipeline(unittest.TestCase):
    def test_c27_missing_pk_core_blocks_release_exit_2(self):
        import faults
        self.assertTrue(faults.f5()["ok"])

    def test_c27_ci_workflow_runs_gate_in_release_mode_across_matrix(self):
        y = (PKG_DIR / "ci" / "release.yml").read_text()
        self.assertIn('INV14_RELEASE: "1"', y); self.assertIn("verify_release.py", y)
        for v in ("3.10", "3.11", "3.12", "3.13"):
            self.assertIn(f'"{v}"', y)

    def test_c27_release_mode_turns_absent_layers_into_failures(self):
        env = dict(os.environ, INV14_RELEASE="1"); env.pop("PK_ADJACENT_PATH", None)
        r = tool("tests/test_integration_adjacent.py", env=env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("FAIL", r.stderr)
        env.pop("INV14_RELEASE")
        r2 = tool("tests/test_integration_adjacent.py", env=env)
        self.assertEqual(r2.returncode, 0); self.assertIn("skipped=3", r2.stderr)


class C28Sbom(unittest.TestCase):
    def test_c28_sbom_provenance_scan(self):
        self.assertEqual(tool(TOOLS / "sbom.py").returncode, 0)
        sb = json.loads((PKG_DIR / "sbom" / "inv14.cdx.json").read_text())
        self.assertEqual((sb["bomFormat"], sb["specVersion"]), ("CycloneDX", "1.5"))
        names = {c["name"] for c in sb["components"]}
        self.assertIn("polling.py", names); self.assertIn("pk_core", names)
        scan = json.loads((PKG_DIR / "sbom" / "dependency_scan.json").read_text())
        self.assertTrue(scan["stdlib_only_runtime"]); self.assertIn("INDETERMINATE", scan["pk_core"])
        prov = json.loads((PKG_DIR / "sbom" / "provenance.intoto.json").read_text())
        self.assertTrue(prov["predicate"]["runDetails"]["builder"]["id"].startswith("UNSIGNED"))


class C29Signing(unittest.TestCase):
    def test_c29_sign_verify_tamper_and_trust_policy(self):
        import sign
        if sign.backend() is None:
            self.fail("no crypto backend: signing gate cannot pass (fail, not skip)")
        work = pathlib.Path(tmpdir()) / PKG_DIR.name
        shutil.copytree(PKG_DIR, work, ignore=shutil.ignore_patterns("__pycache__", "evidence"))
        kd = tmpdir()
        pub = subprocess.run([sys.executable, "-B", str(work / "tools/sign.py"), "keygen", "--out", kd, "--key-id", "t1"],
                             capture_output=True, text=True).stdout.strip()
        keys = {"schema": "PK_POLL_TRUSTED_KEYS/1", "keys": [{"key_id": "t1", "alg": "Ed25519", "status": "TRUSTED", "public_key": pub}]}
        (work / "governance" / "TRUSTED_KEYS.json").write_text(json.dumps(keys))
        run = lambda *a: subprocess.run([sys.executable, "-B", str(work / "tools/sign.py"), *a], capture_output=True, text=True)
        subprocess.run([sys.executable, "-B", str(work / "tools/manifest.py")], check=True, capture_output=True)
        self.assertEqual(run("sign", "--key", os.path.join(kd, "t1.pem"), "--key-id", "t1").returncode, 0)
        self.assertEqual(run("verify", "--require-trusted").stdout.strip(), "OK:TRUSTED")
        m = work / "MANIFEST.sha256"; m.write_text(m.read_text() + "tampered\n")
        self.assertEqual(run("verify").stdout.strip(), "MANIFEST_CHANGED")
        keys["keys"][0]["status"] = "UNTRUSTED_DEV"; (work / "governance" / "TRUSTED_KEYS.json").write_text(json.dumps(keys))
        subprocess.run([sys.executable, "-B", str(work / "tools/manifest.py")], check=True, capture_output=True)
        run("sign", "--key", os.path.join(kd, "t1.pem"), "--key-id", "t1")
        r = run("verify", "--require-trusted")
        self.assertEqual((r.returncode, r.stdout.strip()), (7, "SIGNER_NOT_TRUSTED:UNTRUSTED_DEV"))
        keys["keys"][0]["status"] = "REVOKED"; (work / "governance" / "TRUSTED_KEYS.json").write_text(json.dumps(keys))
        subprocess.run([sys.executable, "-B", str(work / "tools/manifest.py")], check=True, capture_output=True)
        run("sign", "--key", os.path.join(kd, "t1.pem"), "--key-id", "t1")
        self.assertEqual(run("verify").stdout.strip(), "REVOKED_KEY")

    def test_c29_openssl_only_backend_signs_and_verifies(self):
        import sign, shutil as sh
        if not sh.which("openssl"):
            self.skipTest("openssl CLI absent")
        kd = tmpdir()
        pub = __import__("base64").b64decode(sign._openssl_keygen(kd, "o1"))
        sig = sign._openssl_sign(os.path.join(kd, "o1.pem"), b"inv14")
        self.assertTrue(sign._openssl_verify(pub, sig, b"inv14"))
        self.assertFalse(sign._openssl_verify(pub, sig, b"inv15"))

    def test_c29_openssl_backend_agrees_when_present(self):
        import sign, base64, shutil as sh
        if not sh.which("openssl") or not sign._has_crypto():
            self.skipTest("differential check needs both backends; the required signing test covers whichever exists")
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization as s
        k = Ed25519PrivateKey.generate(); data = b"inv14"
        pub = k.public_key().public_bytes(s.Encoding.Raw, s.PublicFormat.Raw)
        self.assertTrue(sign._openssl_verify(pub, k.sign(data), data))
        self.assertFalse(sign._openssl_verify(pub, k.sign(data), data + b"x"))


class C30Config(unittest.TestCase):
    def test_c30_overlays_atomic_update_history(self):
        env = {"limits": {"max_concurrent_polls": 256}, "provenance": {"version": "4.3.0-prod", "reason": "prod overlay"}}
        site = {"limits": {"tenant_max_concurrent_polls": 16}, "provenance": {"version": "4.3.0-prod-eu1"}}
        merged = config.merge(config.BASE_CONFIG, env, site)
        self.assertEqual((merged["limits"]["max_concurrent_polls"], merged["limits"]["tenant_max_concurrent_polls"]), (256, 16))
        self.assertEqual(merged["provenance"]["author"], "inv14-release-build")
        store = config.ConfigStore(config.BASE_CONFIG)
        store.update(merged)
        bad = config.merge(merged, {"limits": {"tenant_max_concurrent_polls": 999}, "provenance": {"version": "x2"}})
        with self.assertRaises(config.ConfigError):
            store.update(bad)
        self.assertEqual(store.active, merged)
        reuse = config.merge(merged, {"limits": {"queue_depth": 3}})
        with self.assertRaises(config.ConfigError) as cm:
            store.update(reuse)
        self.assertEqual(cm.exception.code, "PK_CONFIG_VERSION_REUSE")
        self.assertEqual([h["version"] for h in store.history()], ["4.3.0-base", "4.3.0-prod-eu1"])
        self.assertEqual(schema_check.check(merged, "pk_poll_config.schema.json"), [])

    def test_c30_missing_provenance_and_unknown_keys_refused(self):
        for mut in (lambda d: d.pop("provenance"), lambda d: d.__setitem__("zz", 1), lambda d: d["limits"].pop("queue_depth"),
                    lambda d: d.__setitem__("legacy_polls_enabled", "yes")):
            d = json.loads(json.dumps(config.BASE_CONFIG)); mut(d)
            with self.assertRaises(config.ConfigError):
                config.validate_config(d)
        with self.assertRaises(config.ConfigError):
            config.merge(config.BASE_CONFIG, ["not", "a", "dict"])


class C31Redaction(unittest.TestCase):
    def test_c31_secret_keys_and_shapes_redacted(self):
        src = {"password": "p", "Authorization": "x", "api_key": "k", "note": "Bearer abcdefghijklmno", "pem": "-----BEGIN PRIVATE KEY-----",
               "aws": "AKIAABCDEFGHIJKLMNOP", "kv": "token=abc123", "ok": "hello", "n": 5,
               "nested": {"deep": {"secret": "s"}}, "b": b"raw", "lst": list(range(100))}
        r = redaction.redact(src)
        for k in ("password", "Authorization", "api_key", "note", "pem", "aws", "kv"):
            self.assertEqual(r[k], "[REDACTED]", k)
        self.assertEqual((r["ok"], r["n"], r["nested"]["deep"]["secret"], r["b"]), ("hello", 5, "[REDACTED]", "[bytes:3]"))
        self.assertEqual(len(r["lst"]), redaction.MAX_ITEMS + 1)

    def test_c31_bounds_and_totality(self):
        deep = {}; cur = deep
        for _ in range(10):
            cur["a"] = {}; cur = cur["a"]
        self.assertIn("[DEPTH_LIMIT]", json.dumps(redaction.redact(deep)))
        self.assertEqual(len(redaction.redact("x" * 5000)), redaction.MAX_VALUE_CHARS)
        self.assertEqual(redaction.redact(object()), "[object]")
        self.assertEqual(redaction.redact(float("nan")), "nan")

    def test_c31_error_details_and_diagnostics_carry_no_secrets(self):
        svc, iss, buf, _ = make_service()
        o = "a/b/c"; tok = iss.mint(o)
        with self.assertRaises(Exception):
            svc.poll("x/y/z", [P.Pollable("x", "x/y/z")], timeout_ticks=1, token=tok)
        blob = buf.getvalue() + json.dumps(svc.diagnostics()) + open(svc.audit.path).read()
        self.assertNotIn(tok, blob); self.assertNotIn(KEY.decode(), blob)


class C32DashboardAlerts(unittest.TestCase):
    def test_c32_alerts_reference_exported_metrics_and_distinguish_classes(self):
        y = (PKG_DIR / "ops" / "alerts.yml").read_text()
        t = telemetry.Telemetry(); t.record("a", "ready", latency_ms=1)
        exported = {n for n, _, _ in telemetry.parse_prometheus(t.prometheus_text())} | {"inv14_polls_total"}
        used = set(re.findall(r"(inv14_[a-z_]+)", y))
        self.assertTrue(used <= exported | {"inv14_poll_latency_ms_bucket"}, used - exported)
        classes = set(re.findall(r"class: ([a-z-]+)", y))
        self.assertTrue({"security", "saturation", "caller-defect", "timeout-load", "migration", "software-defect"} <= classes)
        for reason in re.findall(r'reason="([a-z_]+)"', y):
            self.assertIn(reason, telemetry.REASONS)
        for anchor in re.findall(r"RUNBOOK.md#([a-z0-9-]+)", y):
            heads = [re.sub(r"[^a-z0-9 -]", "", h.lower()).replace(" ", "-") for h in re.findall(r"^## (.+)$", (PKG_DIR / "docs" / "RUNBOOK.md").read_text(), re.M)]
            self.assertIn(anchor, heads)

    def test_c32_dashboard_panels_cover_classes(self):
        d = json.loads((PKG_DIR / "ops" / "dashboard.json").read_text())
        self.assertGreaterEqual(len(d["panels"]), 8)
        self.assertTrue(all("inv14_" in p["expr"] for p in d["panels"]))


class C33Runbook(unittest.TestCase):
    def test_c33_runbook_commands_execute(self):
        st = tmpdir(); env = dict(os.environ, INV14_AUDIT_KEY_HEX=KEY.hex())
        rb = lambda *a: subprocess.run([sys.executable, "-B", str(TOOLS / "runbook.py"), "--state", st, *a], capture_output=True, text=True, env=env)
        s = json.loads(rb("status").stdout); self.assertEqual((s["lifecycle"], s["pk_core"]), ("DEPRECATED", "PK_CORE_UNPINNED"))
        self.assertEqual(json.loads(rb("disable", "--actor", "oncall", "--reason", "drill").stdout)["state"], "DISABLED")
        self.assertEqual(json.loads(rb("rollback", "--actor", "oncall", "--reason", "drill over").stdout)["state"], "DEPRECATED")
        r = rb("transition", "ENABLED", "--actor", "x", "--reason", "y"); self.assertEqual(r.returncode, 2)
        self.assertEqual(json.loads(rb("verify-audit").stdout)["count"], 2)
        bad = subprocess.run([sys.executable, "-B", str(TOOLS / "runbook.py"), "--state", st, "verify-audit"], capture_output=True, text=True,
                             env={k: v for k, v in os.environ.items() if k != "INV14_AUDIT_KEY_HEX"})
        self.assertEqual(bad.returncode, 2)


class C34Waivers(unittest.TestCase):
    def test_c34_waiver_rules(self):
        base = {"waiver_id": "W", "component_id": "c", "owner": "a", "approved_by": "b", "granted": "2026-10-01", "expires": "2026-12-01", "retirement_commitment": "x"}
        governance.validate_waivers({"schema": "PK_POLL_WAIVERS/1", "waivers": [base]})
        for patch, code in (({"approved_by": "a"}, "PK_GOVERNANCE_SELF_APPROVAL"), ({"expires": "2027-12-01"}, "PK_GOVERNANCE_WAIVER_TOO_LONG"),
                            ({"retirement_commitment": ""}, "PK_GOVERNANCE_INVALID"), ({"expires": "12/01/2026"}, "PK_GOVERNANCE_INVALID")):
            with self.assertRaises(governance.GovernanceError) as cm:
                governance.validate_waivers({"schema": "PK_POLL_WAIVERS/1", "waivers": [dict(base, **patch)]})
            self.assertEqual(cm.exception.code, code)
        governance.validate_waivers(governance.load("WAIVERS.json"))


class C35Eol(unittest.TestCase):
    def test_c35_eol_phases_enforced(self):
        eol = governance.load("EOL_POLICY.json")
        self.assertEqual(eol["status"], "PROPOSED")
        c = {"component_id": "svc", "owner": "o", "stage": "LEGACY", "registered": "2026-09-01", "deadline": "2027-11-30"}
        w = {"waiver_id": "W", "component_id": "svc", "owner": "o", "approved_by": "g", "granted": "2027-07-01", "expires": "2027-12-01", "retirement_commitment": "x"}
        mk = lambda ws=(): governance.ConsumerGate({"schema": "PK_POLL_MIGRATION_REGISTRY/1", "consumers": [c]}, {"schema": "PK_POLL_WAIVERS/1", "waivers": list(ws)}, eol)
        self.assertEqual(governance.eol_phase(eol, dt.date(2026, 10, 1)), "DEPRECATED")
        self.assertEqual(mk().check("svc", dt.date(2027, 3, 1))["basis"], "deadline")
        with self.assertRaises(governance.GovernanceError):
            mk().check("svc", dt.date(2027, 7, 15))  # WAIVER_ONLY: deadline no longer admits
        self.assertTrue(mk([w]).check("svc", dt.date(2027, 7, 15))["allowed"])
        with self.assertRaises(governance.GovernanceError) as cm:
            mk([w]).check("svc", dt.date(2028, 1, 1))
        self.assertEqual(cm.exception.code, "PK_POLL_EOL_REMOVED")
        g = mk()
        with self.assertRaises(governance.GovernanceError) as cm:
            g.register(dict(c, component_id="late"), dt.date(2027, 2, 1))
        self.assertEqual(cm.exception.code, "PK_POLL_REGISTRY_CLOSED")
        g.register(dict(c, component_id="early"), dt.date(2026, 10, 1))

    def test_c35_eol_validation(self):
        for ms in ([], [{"phase": "REMOVED", "date": "2027-01-01"}, {"phase": "REMOVED", "date": "2026-01-01"}], [{"phase": "DEPRECATED", "date": "2026-01-01"}]):
            with self.assertRaises(governance.GovernanceError):
                governance.validate_eol({"schema": "PK_POLL_EOL/1", "milestones": ms})


class C00Diagnostics(unittest.TestCase):
    def test_c00_diagnostics_report_versions_and_safe_status_only(self):
        svc, iss, _, _ = make_service()
        o = "a/b/c"; svc.poll(o, [P.Pollable("x", o)], timeout_ticks=1, token=iss.mint(o))
        d = svc.diagnostics()
        for k in ("version", "process_epoch", "schema_digests", "lifecycle_model", "tick_seconds", "pk_core", "admission", "audit_head"):
            self.assertIn(k, d)
        self.assertEqual(d["pk_core"]["code"], "PK_CORE_UNPINNED")
        blob = json.dumps(d)
        self.assertNotIn(o, blob); self.assertNotIn(str(PKG_DIR), blob)

    def test_c00_error_registry_has_retry_class_and_action_for_every_code(self):
        reg = json.loads((PKG_DIR / "schemas" / "error_codes.json").read_text())
        for c in reg["codes"]:
            self.assertIn(c["retry_class"], {"transient", "quota", "caller", "policy", "dependency", "security", "governance", "permanent"})
            self.assertTrue(c["caller_action"])


if __name__ == "__main__":
    unittest.main()
