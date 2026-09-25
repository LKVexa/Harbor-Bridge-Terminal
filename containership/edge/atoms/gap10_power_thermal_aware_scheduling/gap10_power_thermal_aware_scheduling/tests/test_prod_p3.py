"""P3 certification tests: components 29-38 (e2e, contracts/fuzz, concurrency,
fault injection, benchmark smoke, compatibility, SBOM, release, rollout, backup)."""
import json
import os
import random
import tempfile
import threading
import unittest

from harness import PKG_DIR, SCOPE, Stack
from gap10_power_thermal_aware_scheduling.model import PowerThermalPolicy
from gap10_power_thermal_aware_scheduling.production.errors import ErrorCode, Gap10Error
from gap10_power_thermal_aware_scheduling.production.policy_service import policy_to_dict, sign_bundle
from gap10_power_thermal_aware_scheduling.production.rollout import Guard, RolloutController
from gap10_power_thermal_aware_scheduling.production.schema_validate import load_schemas, validate
from gap10_power_thermal_aware_scheduling.production.store import FileStateStore

SCHEMAS = load_schemas(PKG_DIR / "schemas")


class C29EndToEnd(unittest.TestCase):
    """GAP-09 envelope -> GAP-10 -> scheduler + elasticity, per scenario."""

    def test_c29_success_stale_forged_emergency_recovery(self):
        s = Stack()
        # success
        s.send("edge-001", 40.0)
        s.adapter.admit("edge-001", "w1", 50, s.clock.now())
        # forged cool reading while hot: rejected, state unchanged
        s.mc.advance(1)
        s.send("edge-001", 96.0)
        with self.assertRaises(Gap10Error):
            s.ctl.ingest(s.envelope("edge-001", 96.0, tamper=True))
        self.assertEqual(s.ctl.nodes["edge-001"].last_decision["band"], "emergency")
        self.assertEqual(s.sched.allocated("edge-001"), 0)
        with self.assertRaises(Gap10Error):
            s.adapter.admit("edge-001", "w2", 1, s.clock.now())
        # stale: GAP-09 stops -> consumer decision ages out -> fail closed
        s.mc.advance(20)
        self.assertTrue(s.view.effective("edge-001", 100, s.clock.now())["fail_closed"])
        # recovery requires fresh trusted evidence and hysteresis
        s.send("edge-001", 92.0)  # inside the 5 C recovery margin: held
        self.assertEqual(s.ctl.nodes["edge-001"].last_decision["band"], "emergency")
        s.mc.advance(1)
        d = s.send("edge-001", 70.0)
        self.assertIn(d["band"], ("nominal", "elevated", "critical"))
        s.adapter.admit("edge-001", "w3", 1, s.clock.now())
        self.assertEqual(s.elastic_adapter.apply("pool", s.clock.now()) >= 0, True)

    def test_c29_every_published_decision_is_schema_valid(self):
        s = Stack()
        for t in (30, 80, 86, 96, 70, None):
            s.mc.advance(1)
            sensors = [{"sensor_id": "cpu0", "kind": "cpu", "temperature_c": t}]
            d = s.ctl.ingest(s.envelope(sensors=sensors))
            self.assertEqual(validate(d, SCHEMAS["PK_POWER_CEILING/1"]), [], d)


class C30Contracts(unittest.TestCase):
    def test_c30_fixtures_validate(self):
        mapping = {"thermal_state": "PK_THERMAL_STATE/1", "power_ceiling": "PK_POWER_CEILING/1",
                   "thermal_policy": "PK_THERMAL_POLICY/1", "telemetry_envelope": "PK_TELEMETRY_ENVELOPE/1"}
        seen = 0
        for p in sorted((PKG_DIR / "fixtures").glob("*.json")):
            key = next((k for k in mapping if p.name.startswith(k)), None)
            if key is None:
                continue
            seen += 1
            self.assertEqual(validate(json.loads(p.read_text()), SCHEMAS[mapping[key]]), [], p.name)
        self.assertGreaterEqual(seen, 6)

    def test_c30_policy_schema_accepts_default_and_envelope_schema_accepts_harness(self):
        self.assertEqual(validate(dict(policy_to_dict(PowerThermalPolicy()), schema="PK_THERMAL_POLICY/1"),
                                  SCHEMAS["PK_THERMAL_POLICY/1"]), [])
        self.assertEqual(validate(Stack().envelope(), SCHEMAS["PK_TELEMETRY_ENVELOPE/1"]), [])

    def test_c30_negative_instances_rejected(self):
        bad = [{"schema": "PK_POWER_CEILING/1"}, {"schema": "PK_POWER_CEILING/1", "node": "", "band": "hot", "ceiling": -1,
               "ceiling_fraction": 2, "excluded": "no", "reason": "", "reasons": [], "telemetry_status": "x"}]
        for b in bad:
            self.assertTrue(validate(b, SCHEMAS["PK_POWER_CEILING/1"]))

    def test_c30_fuzz_telemetry_boundary_never_crashes_or_relaxes(self):
        rng = random.Random(1234)
        s = Stack()
        s.send(temp=96.0)
        junk = [None, True, -1, 1e308, float("nan"), float("inf"), "", "x" * 300, [], {}, [1], {"a": 1}]
        for i in range(2000):
            env = s.envelope(temp=96.0)
            target = rng.choice(["top", "payload", "sensor"])
            key = rng.choice(["schema", "key_id", "signature", "attestation", "payload", "node", "seq",
                              "observed_at", "sensors", "temperature_c", "kind", "sensor_id", "battery_fraction"])
            val = rng.choice(junk)
            if target == "top":
                env[key] = val
            elif target == "payload":
                env["payload"][key] = val
            else:
                env["payload"]["sensors"][0][key] = val
            raw = json.dumps(env, allow_nan=True) if rng.random() < 0.5 else env
            try:
                s.ctl.ingest(raw)
            except Gap10Error:
                pass
            # nothing that fails signature can ever change the excluded state
            self.assertEqual(s.ctl.nodes["edge-001"].last_decision["band"], "emergency", i)

    def test_c30_fuzz_policy_boundary(self):
        rng = random.Random(99)
        s = Stack()
        base = policy_to_dict(PowerThermalPolicy())
        for _ in range(500):
            p = dict(base)
            k = rng.choice(list(p))
            p[k] = rng.choice([None, -1, 0, 0.5, 1, 1e9, float("nan"), "x", True])
            try:
                s.policies.submit(sign_bundle(s.kr, SCOPE, p, s.policies.active[SCOPE], "author-k1"), now=1)
            except Gap10Error as e:
                self.assertIn(e.code, (ErrorCode.POLICY_INVALID, ErrorCode.POLICY_UNAUTHORIZED))
            except (TypeError, ValueError):
                self.fail("policy boundary leaked a non-taxonomy exception")


class C31Concurrency(unittest.TestCase):
    def test_c31_parallel_admission_never_exceeds_ceiling_during_transition(self):
        s = Stack()
        s.send(temp=40.0)
        errors = []

        def worker(i):
            for j in range(20):
                try:
                    s.adapter.admit("edge-001", f"w{i}-{j}", 1, s.clock.now())
                except Gap10Error:
                    pass
                except Exception as e:  # noqa: BLE001
                    errors.append(e)
        ts = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        for t in ts:
            t.start()
        s.mc.advance(1)
        s.send(temp=86.0)  # simultaneous nominal -> critical
        for t in ts:
            t.join()
        s.adapter.apply("edge-001", s.clock.now())
        self.assertEqual(errors, [])
        self.assertLessEqual(s.sched.allocated("edge-001"), 25)

    def test_c31_parallel_policy_swaps_single_winner(self):
        s = Stack()
        parent = s.policies.active[SCOPE]
        results = []

        def submit(e):
            try:
                r = s.policies.submit(sign_bundle(s.kr, SCOPE, dict(policy_to_dict(PowerThermalPolicy()), elevated_c=e),
                                                  parent, "author-k1"), now=1)
                s.policies.activate(SCOPE, r.revision_id, actor="alice", now=2)
                results.append(r.revision_id)
            except Gap10Error:
                pass
        ts = [threading.Thread(target=submit, args=(70.0 - i,)) for i in range(6)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(results), 1)  # compare-and-swap: exactly one concurrent activation wins
        self.assertEqual(s.policies.active[SCOPE], results[0])

    def test_c31_duplicate_samples_and_node_recreation(self):
        s = Stack()
        env = s.envelope(temp=40.0)
        s.ctl.ingest(env)
        for _ in range(5):
            with self.assertRaises(Gap10Error):
                s.ctl.ingest(env)
        s.store.delete("edge-001")
        del s.ctl.nodes["edge-001"]
        ctx = s.ctl.register("edge-001", scope=SCOPE)
        self.assertEqual(ctx.state.band, "critical")

    def test_c31_concurrent_store_writes_are_atomic(self):
        st = FileStateStore(tempfile.mkdtemp())
        from gap10_power_thermal_aware_scheduling.production.store import NodeRecord

        def w(i):
            for _ in range(20):
                try:
                    st.save(NodeRecord("n", "critical", None, None, "r", "critical", fencing_token=1 + (i % 2)))
                except Gap10Error:
                    pass
        ts = [threading.Thread(target=w, args=(i,)) for i in range(6)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertIsNotNone(st.load("n"))


class C32FaultInjection(unittest.TestCase):
    def test_c32_sensor_dropout_and_stuck_values(self):
        s = Stack()
        s.send(temp=40.0)
        s.mc.advance(1)
        d = s.send(sensors=[])
        self.assertEqual(d["band"], "critical")
        # stuck-low sensor while the domain overheats
        s.ctl.cooling.membership = {"edge-001": "rack", "edge-002": "rack", "edge-003": "rack"}
        s.ctl.cooling.inlet_limits_c = {"rack": 35.0}
        s.ctl.cooling.report_inlet("rack", 40.0)
        s.mc.advance(1)
        self.assertEqual(s.send(temp=20.0)["band"], "critical")

    def test_c32_delay_store_scheduler_outage_crash_restart(self):
        s = Stack()
        s.send(temp=40.0)
        s.mc.advance(31)  # telemetry delayed beyond freshness (and lease lapsed) -> health unsafe
        self.assertFalse(s.ctl.health()["safe_to_enforce"])
        s.ctl.acquire()  # same controller re-acquires with a new fencing token
        s.store.available = False
        d = s.ctl.ingest(s.envelope(temp=40.0))
        self.assertLessEqual(d["ceiling_fraction"], 0.25)
        s.store.available = True
        s.sched.available = False
        with self.assertRaises(Gap10Error):
            s.adapter.apply("edge-001", s.clock.now())
        s.sched.available = True
        # crash: new process with the same store, lease expired
        s.mc.advance(31)
        c2 = s.controller("ctl-b")
        c2.acquire()
        self.assertEqual(c2.register("edge-001", scope=SCOPE).state.band, "critical")

    def test_c32_partition(self):
        s = Stack()
        s.send(temp=30.0)
        s.ctl.partition.confirm("edge-001", 1.0)
        s.ctl.partition.on_disconnect(s.clock.now())
        s.mc.advance(1)
        self.assertLessEqual(s.send(temp=30.0)["ceiling_fraction"], 0.6)


class C33BenchmarkSmoke(unittest.TestCase):
    def test_c33_bench_harness_runs_and_bounds_memory(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("bench", PKG_DIR / "tools" / "bench.py")
        bench = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bench)
        r = bench.run(nodes=50, rounds=4)
        self.assertEqual(r["decisions"], 200)
        self.assertLess(r["latency_s"]["p99"], 0.05)
        self.assertIn("peak_kib", r["memory"])


class C34C35C36Release(unittest.TestCase):
    def test_c34_compat_matrix_well_formed(self):
        m = json.loads((PKG_DIR / "ops" / "compatibility_matrix.json").read_text())
        for k in ("python", "architectures", "operating_systems", "sensor_providers", "peer_schemas", "schedulers"):
            self.assertIn(k, m)
        for row in m["peer_schemas"]:
            self.assertIn(row["status"], ("supported", "rejected", "unverified"))

    def test_c35_sbom_lists_no_undeclared_imports(self):
        import ast
        sbom = json.loads((PKG_DIR / "SBOM.cdx.json").read_text())
        declared = {c["name"] for c in sbom["components"]}
        import sys
        stdlib = set(sys.stdlib_module_names)
        for py in PKG_DIR.rglob("*.py"):
            for node in ast.walk(ast.parse(py.read_text())):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    mods = [node.module.split(".")[0]]
                for m in mods:
                    if m in stdlib or m in ("gap10_power_thermal_aware_scheduling", "harness", "gen_golden", "__future__"):
                        continue
                    self.assertIn(m, declared, f"{py.name} imports undeclared {m}")

    def test_c36_reproducible_release_and_signature(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("rel", PKG_DIR / "tools" / "build_release.py")
        rel = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rel)
        out = tempfile.mkdtemp()
        key = b"k" * 32
        a = rel.build(PKG_DIR, os.path.join(out, "a"), signing_key=key, source_revision="test")
        b = rel.build(PKG_DIR, os.path.join(out, "b"), signing_key=key, source_revision="test")
        self.assertEqual(a["sha256"], b["sha256"])
        self.assertTrue(rel.verify(a["zip"], a["provenance"], key))
        with open(a["zip"], "ab") as fh:
            fh.write(b"tamper")
        self.assertFalse(rel.verify(a["zip"], a["provenance"], key))


class C37Rollout(unittest.TestCase):
    def test_c37_staged_promotion_and_auto_rollback(self):
        s = Stack(nodes=tuple(f"edge-{i:03d}" for i in range(20)))
        rev = s.policies.submit(sign_bundle(s.kr, SCOPE, dict(policy_to_dict(PowerThermalPolicy()), elevated_c=70.0),
                                            s.policies.active[SCOPE], "author-k1"), now=1)
        cohorts = {("dub", "x86"): [f"edge-{i:03d}" for i in range(15)], ("dub", "arm"): [f"edge-{i:03d}" for i in range(15, 20)]}
        healthy = {"ok": True}
        rc = RolloutController(s.policies, SCOPE, rev.revision_id, cohorts, [Guard("exclusions", lambda c: healthy["ok"])], soak_s=10)
        rc.start(0)
        staged = s.policies.staged[SCOPE][1]
        self.assertTrue(any(n in staged for n in cohorts[("dub", "arm")]))  # every hw cohort represented
        for t in (10, 20, 30):
            rc.tick(t)
        self.assertEqual(rc.state, "complete")
        self.assertEqual(s.policies.active[SCOPE], rev.revision_id)
        rev2 = s.policies.submit(sign_bundle(s.kr, SCOPE, dict(policy_to_dict(PowerThermalPolicy()), elevated_c=69.0),
                                             s.policies.active[SCOPE], "author-k1"), now=2)
        rc2 = RolloutController(s.policies, SCOPE, rev2.revision_id, cohorts, [Guard("exclusions", lambda c: healthy["ok"])], soak_s=10)
        rc2.start(40)
        healthy["ok"] = False
        self.assertEqual(rc2.tick(45), "rolled-back")
        self.assertNotIn(SCOPE, s.policies.staged)
        self.assertEqual(s.policies.active[SCOPE], rev.revision_id)
        self.assertIn("rollout.rolled_back", [e["type"] for e in s.audit.entries])


class C38BackupRestore(unittest.TestCase):
    def test_c38_backup_restore_verify_before_reopen(self):
        s = Stack()
        s.send("edge-001", 96.0)
        s.send("edge-002", 40.0)
        arc = os.path.join(s.tmp, "state.tgz")
        digest = s.store.backup(arc)
        restored = FileStateStore.restore(arc, os.path.join(s.tmp, "restored"), digest)
        self.assertEqual(sorted(restored.nodes()), ["edge-001", "edge-002"])
        self.assertEqual(restored.load("edge-001").band, "emergency")
        with self.assertRaises(Gap10Error):
            FileStateStore.restore(arc, os.path.join(s.tmp, "r2"), "0" * 64)
        # ownership recovered safely: new leader token is strictly greater
        s.mc.advance(31)
        s.store = restored
        c2 = s.controller("ctl-restore")
        tok = c2.acquire()
        self.assertGreater(tok, 1)
        self.assertEqual(c2.register("edge-001", scope=SCOPE).state.band, "emergency")
        self.assertEqual(c2.register("edge-002", scope=SCOPE).state.band, "critical")  # not reopened until fresh telemetry


if __name__ == "__main__":
    unittest.main()
