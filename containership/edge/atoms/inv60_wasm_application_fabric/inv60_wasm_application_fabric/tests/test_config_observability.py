"""M27-M33 M52 M58-M66 M25(partial) - configuration, secrets, telemetry, execution backend."""
import io, json, shutil, unittest
from _harness import World, Clock
from inv60_wasm_application_fabric.fabric import config as cf, telemetry as tm
from inv60_wasm_application_fabric.fabric.errors import FabricError
from inv60_wasm_application_fabric.fabric.wasm_backend import NodeWasmBackend, WasmCloudBackend, build_module
from inv60_wasm_application_fabric.fabric.ledger import AuditLedger

COMMIT = "c" * 40


class Schema(unittest.TestCase):
    def test_defaults_valid_and_secure(self):
        d = cf.validate(cf.defaults())
        self.assertTrue(d["transport.require_tls"]); self.assertFalse(d["auth.allow_anonymous"])
        self.assertTrue(d["signing.require_signature"])

    def test_rejections(self):
        for patch in ({"nope": 1}, {"auth.token_ttl_s": 5000.0}, {"transport.nats_url": "nats://plain"},
                      {"transport.require_tls": False}, {"auth.allow_anonymous": True},
                      {"membership.suspect_after_s": 9.0, "membership.lost_after_s": 8.0},
                      {"secrets.nats_credentials": {"value": "hunter2"}},
                      {"secrets.nats_credentials": {"ref": "plaintext"}}, {"signing.min_slsa_level": "2"}):
            with self.assertRaises(FabricError, msg=str(patch)):
                cf.validate({**cf.defaults(), **patch})

    def test_int_float_normalization(self):
        self.assertEqual(cf.validate({**cf.defaults(), "auth.token_ttl_s": 60})["auth.token_ttl_s"], 60.0)


class Overlays(unittest.TestCase):
    def test_merge_and_delete(self):
        base = {**cf.defaults(), "placement.allowed_regions": ["eu", "us"]}
        r = cf.render(base, ("staging", {"telemetry.trace_sample_ratio": 1.0}), ("edge", {"telemetry.trace_sample_ratio": None,
                                                                                          "placement.allowed_regions": ["eu"]}))
        self.assertEqual(r["telemetry.trace_sample_ratio"], 0.1)
        self.assertEqual(r["placement.allowed_regions"], ["eu"])

    def test_lower_trust_cannot_weaken(self):
        base = {**cf.defaults(), "placement.allowed_regions": ["eu"]}
        for env, ov in (("development", {"transport.require_tls": False}), ("test", {"auth.allow_anonymous": True}),
                        ("edge", {"signing.min_slsa_level": 1}), ("edge", {"placement.allowed_regions": ["eu", "cn"]})):
            with self.assertRaises(FabricError):
                cf.render(base, (env, ov))

    def test_unknown_env_and_field(self):
        with self.assertRaises(FabricError):
            cf.render(cf.defaults(), ("mars", {}))
        with self.assertRaises(FabricError):
            cf.render(cf.defaults(), ("edge", {"x": 1}))

    def test_every_shipped_overlay_renders(self):
        import pathlib
        d = pathlib.Path(__file__).resolve().parents[1] / "config"
        base = json.loads((d / "base.json").read_text())
        envs = sorted(p.stem for p in (d / "overlays").glob("*.json"))
        self.assertGreaterEqual(len(envs), 6)
        for e in envs:
            cf.render(base, (e, json.loads((d / "overlays" / f"{e}.json").read_text())))

    def test_diff(self):
        a = cf.defaults(); b = {**a, "features.batching": True}
        self.assertEqual(cf.diff(a, b), [{"field": "features.batching", "from": False, "to": True}])


class Activation(unittest.TestCase):
    def ctl(self, n=3, **kw):
        L = AuditLedger(None)
        return cf.ConfigController([cf.Target(f"t{i}") for i in range(n)], ledger=L), L

    def prop(self, c, **kw):
        return c.propose({**cf.defaults(), **kw}, source_commit=COMMIT, author="ci", approver="alice",
                         change_ref="CHG-1", environment="production")

    def test_provenance_and_approval(self):
        c, L = self.ctl()
        r = self.prop(c)
        self.assertTrue(r.digest.startswith("sha256:")); self.assertEqual(r.schema, cf.CONFIG_SCHEMA_VERSION)
        self.assertIn("secrets.nats_credentials", r.secret_refs)
        with self.assertRaises(FabricError):
            c.propose(cf.defaults(), source_commit="main", author="ci", approver="a", change_ref="x", environment="production")
        with self.assertRaises(FabricError):
            c.propose(cf.defaults(), source_commit=COMMIT, author="ci", approver="ci", change_ref="x", environment="production")

    def test_two_phase_commit_and_stale_generation(self):
        c, L = self.ctl()
        g1 = self.prop(c).generation
        self.assertEqual(c.activate(g1)["code"], "OK")
        with self.assertRaises(FabricError) as cm:
            c.activate(g1)
        self.assertEqual(cm.exception.code, "STALE_GENERATION")
        self.assertEqual(c.status()["drift"], [])

    def test_offline_target_aborts_then_reconciles(self):
        c, L = self.ctl()
        g1 = self.prop(c).generation; c.activate(g1)
        c.targets["t1"].online = False
        g2 = self.prop(c, **{"features.batching": True}).generation
        r = c.activate(g2)
        self.assertFalse(r["committed"]); self.assertEqual(c.active, g1)
        r = c.activate(g2, min_success_ratio=0.6)
        self.assertTrue(r["committed"]); self.assertEqual(r["per_target"]["t1"], "unreachable")
        self.assertEqual(c.status()["drift"], ["t1"])
        self.assertEqual(c.reconcile_offline("t1"), "converged")
        self.assertEqual(c.status()["drift"], [])

    def test_commit_failure_rolls_back_compensating(self):
        c, L = self.ctl()
        g1 = self.prop(c).generation; c.activate(g1)
        c.targets["t2"].fail_on_commit = True
        g2 = self.prop(c, **{"features.batching": True}).generation
        r = c.activate(g2)
        self.assertEqual(r["code"], "PARTIAL"); self.assertEqual(r["rolled_back_to"], g1)
        self.assertTrue(all(t.active_generation == g1 for t in c.targets.values()))

    def test_unhealthy_after_commit_auto_rollback(self):
        c, L = self.ctl()
        g1 = self.prop(c).generation; c.activate(g1)
        c.targets["t0"].healthy_after = False
        r = c.activate(self.prop(c, **{"features.batching": True}).generation)
        self.assertFalse(r["committed"]); self.assertEqual(c.active, g1)

    def test_explicit_rollback_idempotent(self):
        c, L = self.ctl()
        g1 = self.prop(c).generation; c.activate(g1)
        g2 = self.prop(c, **{"features.batching": True}).generation; c.activate(g2)
        r = c.rollback("bob")
        self.assertTrue(r["committed"]); self.assertEqual(r["rolled_back_from"], g1)
        self.assertEqual(c.revisions[c.active].digest, c.revisions[g1].digest)
        self.assertGreaterEqual(len([x for x in L.records if x["kind"].startswith("config.")]), 5)
        L.verify()


class Secrets(unittest.TestCase):
    def setUp(self):
        self.w = World(); self.calls = {"n": 0}
        def vault(ref):
            self.calls["n"] += 1
            if self.calls.get("fail"):
                raise ConnectionError("down")
            return b"s3cr3t-v%d" % self.calls["n"]
        self.ref = "secret://vault/inv60/nats-creds#v1"
        self.r = cf.SecretResolver({"vault": vault}, {self.ref: {self.w.p["api"].id}}, ttl_s=10, clock=self.w.mono)

    def test_acl_cache_rotate(self):
        v = self.r.resolve(self.ref, principal=self.w.p["api"])
        self.assertEqual(v.reveal(), b"s3cr3t-v1")
        self.assertNotIn("s3cr3t", repr(v) + str(v))
        self.r.resolve(self.ref, principal=self.w.p["api"]); self.assertEqual(self.calls["n"], 1)
        self.r.rotate(self.ref)
        self.assertEqual(v.reveal(), b"")                      # zeroized
        self.assertEqual(self.r.resolve(self.ref, principal=self.w.p["api"]).reveal(), b"s3cr3t-v2")
        with self.assertRaises(FabricError):
            self.r.resolve(self.ref, principal=self.w.p["evil"])

    def test_refresh_failure_no_stale_fallback(self):
        self.r.resolve(self.ref, principal=self.w.p["api"])
        self.w.mono.advance(11); self.calls["fail"] = True
        with self.assertRaises(FabricError) as cm:
            self.r.resolve(self.ref, principal=self.w.p["api"])
        self.assertEqual(cm.exception.code, "UNAVAILABLE")

    def test_malformed_and_unconfigured(self):
        with self.assertRaises(FabricError):
            self.r.resolve("vault:inv60", principal=self.w.p["api"])
        r = cf.SecretResolver({}, {"secret://kms/x": {self.w.p["api"].id}})
        with self.assertRaises(FabricError) as cm:
            r.resolve("secret://kms/x", principal=self.w.p["api"])
        self.assertEqual(cm.exception.code, "BACKEND_NOT_CONFIGURED")

    def test_scanner(self):
        self.assertTrue(cf.scan_text_for_secrets('password = "hunter22"'))
        self.assertTrue(cf.scan_text_for_secrets("-----BEGIN RSA PRIVATE KEY-----"))
        self.assertFalse(cf.scan_text_for_secrets('{"ref": "secret://vault/x#v1"}'))


class Telemetry(unittest.TestCase):
    def test_metrics_cardinality_guard(self):
        m = tm.Metrics()
        for i in range(tm.MAX_SERIES_PER_METRIC + 10):
            m.inc("calls", host=f"h{i}")
        self.assertEqual(m.dropped_series, 10)
        with self.assertRaises(ValueError):
            m.inc("calls", component="api")
        self.assertIn('inv60_calls_total{overflow="true"} 10', m.exposition())

    def test_histogram_exposition(self):
        m = tm.Metrics(); m.observe("lat", 0.002); m.observe("lat", 9.0)
        e = m.exposition()
        self.assertIn('inv60_lat_bucket{le="0.002"} 1', e); self.assertIn('inv60_lat_bucket{le="+Inf"} 2', e)

    def test_traceparent(self):
        t = tm.TraceContext.parse("00-" + "a" * 32 + "-" + "b" * 16 + "-01")
        self.assertEqual(t.trace_id, "a" * 32); self.assertEqual(t.parent, "b" * 16)
        c = t.child(); self.assertEqual(c.trace_id, t.trace_id); self.assertEqual(c.parent, t.span_id)
        for bad in (None, "junk", "00-" + "0" * 32 + "-" + "b" * 16 + "-01"):
            self.assertNotEqual(tm.TraceContext.parse(bad).trace_id, "0" * 32)
        self.assertRegex(t.header(), r"^00-a{32}-[0-9a-f]{16}-01$")

    def test_trace_propagates_through_fabric(self):
        w = World(); tp = "00-" + "d" * 32 + "-" + "e" * 16 + "-01"
        ref = w.fabric.push(w.tok("deployer-a"), "tenant-a/api", b"\x00asm-component-v1", w.artifact(), tenant="tenant-a").value
        r = w.fabric.start(w.tok("deployer-a"), "api", ref, tenant="tenant-a", traceparent=tp)
        self.assertEqual(r.detail["trace_id"], "d" * 32)
        self.assertEqual(w.fabric.decisions.query(kind="placement")[0]["trace_id"], "d" * 32)

    def test_logger_bounded_redacted(self):
        buf = io.StringIO(); L = tm.Logger(buf, config_digest="sha256:x")
        L.log("info", "e", secret="x", note="y" * 5000)
        rec = json.loads(buf.getvalue())
        self.assertLessEqual(len(buf.getvalue()), tm.Logger.MAX_LINE + 1)
        self.assertEqual(rec["config_digest"], "sha256:x")

    def test_decision_query_bounded(self):
        d = tm.DecisionLog(max_records=10)
        for i in range(30):
            d.record("placement", f"c{i}", "placed", ["r"])
        self.assertEqual(len(d.records), 10)
        self.assertEqual(len(d.query(limit=10**6)), 10)

    def test_status_endpoint_fields(self):
        w = World(); s = w.fabric.status()
        for k in ("version", "ready", "live", "mode", "partition", "hosts", "dependencies", "config_schema", "ledger_head"):
            self.assertIn(k, s)
        self.assertTrue(s["ready"])

    def test_dashboards_and_alerts_reference_real_metrics(self):
        import pathlib
        ops = pathlib.Path(__file__).resolve().parents[1] / "ops"
        alerts = json.loads((ops / "alerts.json").read_text())
        dash = json.loads((ops / "dashboard.json").read_text())
        emitted = {"operations_total", "operation_seconds", "call_seconds", "failovers_total", "hosts", "instances"}
        for a in alerts["alerts"]:
            self.assertTrue(any(m in a["expr"] for m in emitted), a["name"])
            self.assertIn("runbook", a)
        self.assertTrue(dash["panels"])


class WasmExecution(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_real_wasm_executes(self):
        self.assertEqual(NodeWasmBackend().invoke(build_module("add"), "run", [20, 22]), 42)

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_sandbox_refusals(self):
        b = NodeWasmBackend()
        for mod, code in ((build_module("trap"), "PROVIDER_ERROR"), (build_module("add", with_import=True), "PERMISSION_DENIED"),
                          (build_module("add", memory_pages=64), "QUOTA_EXCEEDED"), (b"\x00asmjunk", "INVALID_ARGUMENT")):
            with self.assertRaises(FabricError) as cm:
                b.invoke(mod, "run", [1, 2] if mod[:4] == b"\x00asm" else [])
            self.assertEqual(cm.exception.code, code)

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_timeout_kills_runaway(self):
        with self.assertRaises(FabricError) as cm:
            NodeWasmBackend().invoke(build_module("spin"), "run", [], timeout_s=0.4)
        self.assertEqual(cm.exception.code, "DEADLINE_EXCEEDED")

    def test_abi_validation_and_wasmcloud_fails_closed(self):
        with self.assertRaises(FabricError):
            NodeWasmBackend(node="/nonexistent").invoke(build_module("add"), "run", [2**40, 1])
        with self.assertRaises(FabricError) as cm:
            WasmCloudBackend().invoke(b"", "run", [])
        self.assertEqual(cm.exception.code, "BACKEND_NOT_CONFIGURED")


if __name__ == "__main__":
    unittest.main()
