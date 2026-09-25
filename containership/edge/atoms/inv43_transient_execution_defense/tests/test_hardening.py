"""Checklists 21, 25, 26, 27, 28-30, 33, 37-39, 44, 45: schema conformance,
adversarial, property/fuzz, concurrency, resilience, fault injection,
telemetry, soak/burst, rollout."""
from __future__ import annotations

import io
import json
import os
import pathlib
import random
import string
import threading
import time
import unittest

from _harness import (COSTS, FULL, Fleet, W, attestation, auditlog, collector, config, pkg, registry, resilience,
                      rollout, telemetry)

PKG = pathlib.Path(__file__).resolve().parents[1]
SEED = int(os.environ.get("INV43_FUZZ_SEED", "4343"))
FUZZ_N = int(os.environ.get("INV43_FUZZ_N", "400"))

try:
    import jsonschema  # optional dev dependency, declared in pyproject [dev]
except ImportError:  # pragma: no cover
    jsonschema = None


class SchemaConformanceTest(unittest.TestCase):
    """Checklist 21: full Draft 2020-12 validation with a standards validator."""

    def setUp(self):
        if jsonschema is None:
            if os.environ.get("INV43_REQUIRE_JSONSCHEMA") == "1":
                self.fail("jsonschema required (INV43_REQUIRE_JSONSCHEMA=1) but not installed")
            self.skipTest("jsonschema not installed; set INV43_REQUIRE_JSONSCHEMA=1 in release CI")

    def schema(self, name):
        s = json.loads((PKG / "schemas" / name).read_text())
        jsonschema.Draft202012Validator.check_schema(s)
        return jsonschema.Draft202012Validator(s)

    def test_all_schemas_are_valid_2020_12(self):
        for p in sorted((PKG / "schemas").glob("*.json")):
            jsonschema.Draft202012Validator.check_schema(json.loads(p.read_text()))

    def test_live_outputs_conform(self):
        f = Fleet()
        try:
            f.attest("node-a")
            v2 = self.schema("PK_MITIGATIONS_2.schema.json")
            rep = f.reg.status("obs", "node-a", version=2)
            rep.pop("freshness")
            v2.validate(rep)
            self.schema("PK_COTENANCY_1.schema.json").validate(
                {k: v for k, v in f.reg.decide("sched", "node-a", W("a"), W("b"), tier="microvm").items()
                 if k != "decision_id"})
            err = f.reg.decide("sched", "node-b", W("a"), W("b"), tier="microvm")
            err.pop("decision_id")
            self.schema("PK_ERROR_1.schema.json").validate(err)
            rb = collector.collect("node-a", root=f.roots["node-a"]).to_dict(include_monotonic=False)
            self.schema("PK_READBACK_1.schema.json").validate(rb)
            self.schema("INV43_CONFIG_1.schema.json").validate(config.merge())
            v1 = self.schema("PK_MITIGATIONS_1.schema.json")
            v1.validate(json.loads((PKG / "tests/fixtures/status.example.json").read_text()))
        finally:
            f.close()

    def test_schemas_reject_bad_instances(self):
        v2 = self.schema("PK_MITIGATIONS_2.schema.json")
        bad = json.loads((PKG / "tests/fixtures/status.example.json").read_text())
        self.assertTrue(list(v2.iter_errors(bad)))  # v1 document is not a v2 document
        cfg = self.schema("INV43_CONFIG_1.schema.json")
        self.assertTrue(list(cfg.iter_errors(dict(config.merge(), require_attestation=False))))


class AdversarialTest(unittest.TestCase):
    """Checklist 25: escalation, injection, replay, spoofing, escape, exhaustion."""

    def setUp(self):
        self.f = Fleet()

    def tearDown(self):
        self.f.close()

    def test_privilege_escalation_collector_cannot_decide_or_control(self):
        for fn in (lambda: self.f.reg.decide("collector-node-a", "node-a", W("a"), W("b"), tier="microvm"),):
            self.assertEqual(fn()["code"], "authz_denied")
        with self.assertRaises(pkg.MitigationMissing):
            self.f.reg.quarantine("collector-node-a", "node-b", "x")
        with self.assertRaises(pkg.MitigationMissing):
            self.f.reg.freeze("collector-node-a")

    def test_spoofed_node_identity(self):
        env = self.f.envelope("node-a")
        env["header"]["node"] = "node-b"
        with self.assertRaises(pkg.MitigationMissing) as cm:
            self.f.reg.submit("collector-node-b", env)
        self.assertIn(cm.exception.code, {"attestation_bad_mac", "attestation_node_mismatch"})

    def test_replay_of_old_good_posture_after_regression(self):
        good = self.f.envelope("node-a")
        self.f.reg.submit("collector-node-a", good)
        (self.f.roots["node-a"] / collector.SYSFS_VULN_DIR / "mds").write_text("Vulnerable\n")
        self.f.attest("node-a")  # node regressed and honestly reported it
        with self.assertRaises(pkg.MitigationMissing) as cm:
            self.f.reg.submit("collector-node-a", good)  # attacker replays the old good one
        self.assertEqual(cm.exception.code, "attestation_replay")
        self.assertEqual(self.f.reg.decide("sched", "node-a", W("a"), W("b"), tier="microvm")["code"],
                         "required_mitigation_missing")

    def test_injection_in_identifiers(self):
        for evil in ("t\n{\"permitted\":true}", "t\x00", "", "   ", 7, None, ["t"]):
            out = self.f.reg.decide("sched", "node-a", W(evil) if isinstance(evil, str) else {"tenant": evil,
                                    "trust_class": "tenant-standard"}, W("b"), tier="microvm")
            self.assertFalse(out.get("permitted", False), evil)

    def test_tenant_escape_by_case_or_whitespace_is_cross_tenant(self):
        self.f.attest("node-a")
        (self.f.roots["node-a"] / collector.SYSFS_VULN_DIR / "mds").write_text("Vulnerable\n")
        self.f.attest("node-a")
        for other in ("T1", "t1 ", " t1"):
            out = self.f.reg.decide("sched", "node-a", W("t1"), W(other), tier="microvm")
            self.assertFalse(out.get("permitted", False), repr(other))

    def test_cost_poisoning_cannot_create_active(self):
        env = self.f.envelope("node-a", costs={"spectre_v2": float("nan"), "retbleed": -1, "mmio_stale_data": True})
        self.f.reg.submit("collector-node-a", env)
        rep = self.f.reg.status("obs", "node-a", version=2)
        for m in ("spectre_v2", "retbleed", "mmio_stale_data"):
            self.assertEqual(rep["mitigations"][m]["status"], "unknown")

    def test_exhaustion_bounds(self):
        rb = collector.collect("node-a", root=self.f.roots["node-a"]).to_dict(include_monotonic=False)
        rb["observations"] = rb["observations"] * 50
        env = self.f.envelope("node-a", readback=registry.readback_from_dict(rb) if False else None)
        big = attestation.seal({"node": "node-a", "readback": rb, "epoch": 1}, node="node-a",
                               key_id=self.f.creds["node-a"][0], secret=self.f.creds["node-a"][1], seq=999,
                               now=self.f.clock.time())
        with self.assertRaises(pkg.MitigationMissing) as cm:
            self.f.reg.submit("collector-node-a", big)
        self.assertIn(cm.exception.code, {"bad_request", "attestation_oversize"})
        m = telemetry.Metrics()
        for i in range(telemetry.MAX_SERIES + 50):
            m.inc("x_total", tenant=f"t{i}")
        self.assertGreater(m.value("inv43_metric_series_overflow_total"), 0)

    def test_side_channel_misuse_explain_does_not_leak_other_tenant_to_scheduler(self):
        self.f.attest("node-a")
        out = self.f.reg.decide("sched", "node-a", W("a"), W("b"), tier="microvm")
        with self.assertRaises(pkg.MitigationMissing):
            self.f.reg.explain("sched", out["decision_id"])


class SecretLeakageTest(unittest.TestCase):
    def test_secrets_never_in_logs_errors_audit_or_explain(self):
        buf = io.StringIO()
        f = Fleet()
        try:
            f.reg.log = telemetry.StructuredLogger(stream=buf)
            f.attest("node-a")
            out = f.reg.decide("sched", "node-a", W("tenant-alpha"), W("tenant-beta"), tier="microvm")
            ex = json.dumps(f.reg.explain("obs", out["decision_id"]))
            audit = json.dumps(f.audit.entries())
            sec = f.creds["node-a"][1]
            for blob in (buf.getvalue(), ex, audit, repr(f.keys._get(f.creds["node-a"][0]))):
                self.assertNotIn(sec.hex(), blob)
                self.assertNotIn(sec.decode("latin-1"), blob)
            self.assertNotIn("tenant-alpha", buf.getvalue())  # pseudonymised in logs
            rec = telemetry.StructuredLogger(stream=io.StringIO()).log("info", "x", token="abc", nested={"password": "p"})
            self.assertEqual((rec["token"], rec["nested"]["password"]), ("[REDACTED]", "[REDACTED]"))
        finally:
            f.close()


class PropertyFuzzTest(unittest.TestCase):
    """Checklist 26: seeded property tests; seed/iterations via env for CI fuzz runs."""

    def rand_text(self, rng):
        alphabet = string.printable + "\x00\x01é‮"
        return "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 40)))

    def test_classifier_total_and_never_satisfying_on_garbage(self):
        rng = random.Random(SEED)
        for _ in range(FUZZ_N * 5):
            s = self.rand_text(rng)
            st, _ = collector.classify(s)
            self.assertIn(st, pkg.VALID_STATUSES)
            if st in pkg.SATISFYING_STATUSES:
                t = s.strip()
                t = t[5:] if t.startswith("KVM: ") else t
                self.assertTrue(t == "Not affected" or t.startswith("Mitigation:"), s)

    def test_decision_invariant(self):
        """For random postures and required sets: permitted <=> every required
        mitigation satisfied and (SMT off or core scheduling)."""
        rng = random.Random(SEED + 1)
        names = ["m%d" % i for i in range(8)]
        for _ in range(FUZZ_N):
            smt, core = rng.random() < 0.5, rng.random() < 0.5
            st = pkg.MitigationState("n", smt_enabled=smt, core_scheduling=core)
            for n in names:
                s = rng.choice(sorted(pkg.VALID_STATUSES))
                if rng.random() < 0.8:
                    st.record(n, s, round(rng.uniform(0.1, 5), 2) if s == pkg.ACTIVE else 0.0)
            req = rng.sample(names + ["future"], rng.randint(1, 5))
            ok = all(st.status(r) in pkg.SATISFYING_STATUSES for r in req) and (not smt or core)
            try:
                permitted = st.may_cotenant("a", "b", req)["permitted"]
            except pkg.MitigationMissing:
                permitted = False
            self.assertEqual(permitted, ok)

    def test_untrusted_readback_dicts_never_crash_unstructured(self):
        rng = random.Random(SEED + 2)
        f = Fleet()
        try:
            base = collector.collect("node-a", root=f.roots["node-a"]).to_dict(include_monotonic=False)
            for i in range(FUZZ_N):
                d = json.loads(json.dumps(base))
                k = rng.choice(list(d))
                d[k] = rng.choice([None, 1, "x", [], {}, True, -1.0, "\x00"])
                if d["observations"] and rng.random() < 0.5 and isinstance(d["observations"], list):
                    o = d["observations"][0]
                    o[rng.choice(list(o))] = rng.choice([None, 1, "x", [], {}, "\x00", float("inf")])
                try:
                    rb = registry.readback_from_dict(d)
                    rb.to_state(COSTS)
                except (pkg.MitigationMissing, ValueError, TypeError):
                    pass  # structured refusal or validation error - never a crash of another kind
        finally:
            f.close()

    def test_identifier_fuzz(self):
        rng = random.Random(SEED + 3)
        for _ in range(FUZZ_N):
            s = self.rand_text(rng)
            try:
                pkg.MitigationState(s)
                self.assertTrue(s.strip() and all(ord(c) >= 32 for c in s))
            except ValueError:
                self.assertTrue(not s.strip() or any(ord(c) < 32 for c in s))


class ConcurrencyTest(unittest.TestCase):
    """Checklist 27."""

    def test_no_torn_reads_during_concurrent_record(self):
        st = pkg.MitigationState("n", smt_enabled=False)
        stop = threading.Event()
        bad = []

        def writer():
            i = 0
            while not stop.is_set():
                for m in pkg.REQUIRED_FOR_COTENANCY:
                    st.record(m, pkg.ACTIVE, 1.0 + (i % 3))
                i += 1

        def reader():
            while not stop.is_set():
                rep = st.report()
                if abs(rep["total_cost_percent"] - sum(v["cost_percent"] for v in rep["mitigations"].values()
                                                       if v["status"] == "active")) > 1e-6:
                    bad.append(rep)

        ts = [threading.Thread(target=writer) for _ in range(3)] + [threading.Thread(target=reader) for _ in range(3)]
        for t in ts:
            t.start()
        time.sleep(0.4)
        stop.set()
        for t in ts:
            t.join()
        self.assertEqual(bad, [])

    def test_concurrent_submissions_and_decisions(self):
        f = Fleet(nodes=tuple(f"n{i}" for i in range(8)))
        try:
            envs = {n: [f.envelope(n) for _ in range(20)] for n in f.roots}
            errors = []

            def sub(n):
                for e in envs[n]:
                    try:
                        f.reg.submit(f"collector-{n}", e)
                    except pkg.MitigationMissing as exc:
                        if exc.code != "attestation_replay":
                            errors.append(exc.code)

            def dec():
                for _ in range(100):
                    out = f.reg.decide("sched", "n0", W("a"), W("b"), tier="microvm")
                    if not out.get("permitted") and out["code"] not in {"posture_absent"}:
                        errors.append(out["code"])

            ts = [threading.Thread(target=sub, args=(n,)) for n in f.roots] + [threading.Thread(target=dec) for _ in range(4)]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
            self.assertEqual(errors, [])
            auditlog.verify_entries(f.audit.entries(), key=b"k" * 32)  # chain stayed linear under contention
        finally:
            f.close()


class ResilienceTest(unittest.TestCase):
    """Checklists 28, 29, 30."""

    def test_taxonomy_covers_every_emitted_code(self):
        import re
        codes = set()
        for p in PKG.glob("*.py"):
            codes |= set(re.findall(r'code="([a-z0-9_]+)"', p.read_text()))
            codes |= set(re.findall(r'AttestationError\([^)]*?"(attestation_[a-z_]+)"', p.read_text()))
        missing = sorted(c for c in codes if c not in resilience.CODE_CLASS)
        self.assertEqual(missing, [])
        self.assertEqual(resilience.classify_code("never_seen"), resilience.FailureClass.SOFTWARE_DEFECT)

    def test_health_state_machine_and_stall(self):
        now = [0.0]
        h = resilience.HealthMonitor(stall_after_s=10, clock=lambda: now[0])
        self.assertEqual(h.state(), resilience.Health.STARTING)
        h.mark_ready()
        h.beat("collector:n1")
        self.assertEqual(h.state(), resilience.Health.READY)
        self.assertEqual(h.state(degraded_nodes=1), resilience.Health.DEGRADED)
        now[0] = 11
        self.assertEqual(h.stalled(), ["collector:n1"])
        self.assertEqual(h.state(), resilience.Health.STALLED)
        h.set_frozen(True)
        self.assertEqual(h.state(), resilience.Health.FROZEN)

    def test_retry_only_retryable_with_jitter_and_deadline(self):
        calls, slept = [0], []

        def flaky():
            calls[0] += 1
            if calls[0] < 3:
                raise pkg.MitigationMissing("down", code="dependency_unavailable")
            return "ok"

        pol = resilience.RetryPolicy(max_attempts=4, base_s=0.1, cap_s=1.0, deadline_s=10)
        self.assertEqual(pol.run(flaky, rng=random.Random(1), sleep=slept.append, clock=lambda: 0.0), "ok")
        self.assertEqual(len(slept), 2)
        self.assertTrue(all(0 <= d <= 1.0 for d in slept))

        def refuse():
            calls[0] += 1
            raise pkg.MitigationMissing("no", code="required_mitigation_missing")

        calls[0] = 0
        with self.assertRaises(pkg.MitigationMissing):
            pol.run(refuse, sleep=slept.append)
        self.assertEqual(calls[0], 1)  # policy rejections are never retried

        def always():
            raise pkg.MitigationMissing("down", code="dependency_unavailable")
        t = [0.0]

        def clock():
            t[0] += 5
            return t[0]
        with self.assertRaises(pkg.MitigationMissing) as cm:
            pol.run(always, rng=random.Random(2), sleep=lambda d: None, clock=clock)
        self.assertEqual(cm.exception.code, "deadline_exceeded")

    def test_admission_control(self):
        now = [0.0]
        b = resilience.TokenBucket(rate_per_s=2, burst=2, clock=lambda: now[0])
        self.assertEqual([b.take() for _ in range(3)], [True, True, False])
        now[0] = 0.5
        self.assertTrue(b.take())
        lim = resilience.ConcurrencyLimiter(1)
        with lim:
            with self.assertRaises(pkg.MitigationMissing) as cm:
                with lim:
                    pass
            self.assertEqual(cm.exception.code, "overloaded")

    def test_circuit_breaker(self):
        now = [0.0]
        cb = resilience.CircuitBreaker(threshold=2, reset_s=5, clock=lambda: now[0])

        def boom():
            raise OSError("down")
        for _ in range(2):
            with self.assertRaises(OSError):
                cb.call(boom)
        self.assertEqual(cb.state, "open")
        with self.assertRaises(pkg.MitigationMissing):
            cb.call(lambda: 1)
        now[0] = 6
        self.assertEqual(cb.state, "half_open")
        with self.assertRaises(OSError):
            cb.call(boom)  # failed trial re-opens
        self.assertEqual(cb.state, "open")
        now[0] = 12
        self.assertEqual(cb.call(lambda: 1), 1)
        self.assertEqual(cb.state, "closed")


class FaultInjectionTest(unittest.TestCase):
    """Checklist 33: partition, collector loss, clock faults, audit-sink failure, reconnect."""

    def test_partition_then_reconnect(self):
        f = Fleet()
        try:
            f.attest("node-a")
            f.clock.advance(400)  # collector partitioned: no posture for 400 s
            self.assertEqual(f.reg.decide("sched", "node-a", W("a"), W("b"), tier="microvm")["code"], "posture_stale")
            self.assertIn("node-a", f.reg.degraded_nodes())
            self.assertEqual(f.reg.health.state(degraded_nodes=1).value, "degraded")
            f.attest("node-a")  # reconnect
            self.assertTrue(f.reg.decide("sched", "node-a", W("a"), W("b"), tier="microvm")["permitted"])
        finally:
            f.close()

    def test_collector_clock_far_behind_is_stale(self):
        f = Fleet()
        try:
            env = f.envelope("node-a")
            env_payload_rb = env["payload"]["readback"]
            env_payload_rb["observed_at_unix"] -= 10_000  # observation claims to be old
            kid, sec = f.creds["node-a"]
            f.seq["node-a"] += 1
            env = attestation.seal(env["payload"], node="node-a", key_id=kid, secret=sec, seq=f.seq["node-a"],
                                   now=f.clock.time())
            f.reg.submit("collector-node-a", env)
            self.assertEqual(f.reg.decide("sched", "node-a", W("a"), W("b"), tier="microvm")["code"], "posture_stale")
        finally:
            f.close()

    def test_audit_sink_failure_fails_closed(self):
        f = Fleet()
        try:
            f.attest("node-a")

            def broken(*a, **k):
                raise OSError("disk full")
            f.reg.audit.append = broken
            with self.assertRaises(OSError):
                f.reg.decide("sched", "node-a", W("a"), W("b"), tier="microvm")
            # an unaudited decision is never returned to the caller as a permit
        finally:
            f.close()

    def test_restart_loses_posture_not_controls(self):
        with self.subTest("covered in test_decision_plane.RegistryTest.test_controls_survive_restart_via_audit_chain"):
            pass

    def test_sysfs_disappears(self):
        f = Fleet()
        try:
            import shutil
            shutil.rmtree(f.roots["node-a"] / "sys")
            f.attest("node-a")
            self.assertEqual(f.reg.decide("sched", "node-a", W("a"), W("b"), tier="microvm")["code"],
                             "required_mitigation_missing")
        finally:
            f.close()


class TelemetryTest(unittest.TestCase):
    def test_prometheus_exposition(self):
        m = telemetry.Metrics()
        m.inc("inv43_decisions_total", verdict="permit", code="ok")
        m.observe("inv43_decision_seconds", 0.0003)
        m.set("inv43_smt_unsafe_nodes", 2)
        text = m.render()
        self.assertIn('inv43_decisions_total{code="ok",verdict="permit"} 1.0', text)
        self.assertIn('inv43_decision_seconds_bucket{le="0.0005"} 1', text)
        self.assertIn("inv43_smt_unsafe_nodes 2.0", text)

    def test_traceparent(self):
        tid, span, ok = telemetry.parse_traceparent("00-" + "1" * 32 + "-" + "2" * 16 + "-01")
        self.assertEqual((tid, ok), ("1" * 32, True))
        for bad in (None, "", "00-" + "0" * 32 + "-" + "2" * 16 + "-01", "garbage", "01-xyz"):
            tid, span, ok = telemetry.parse_traceparent(bad)
            self.assertFalse(ok)
            self.assertEqual(len(tid), 32)
        self.assertTrue(telemetry.child_traceparent("a" * 32).startswith("00-" + "a" * 32))

    def test_log_fields_stable(self):
        buf = io.StringIO()
        rec = telemetry.StructuredLogger(stream=buf, pseudonym_key=b"p" * 32).log(
            "info", "e", node="n", tenants=["t"], workload="w", op_id="o", trace_id="x")
        for k in ("ts", "level", "event", "component", "node", "tenants", "workload", "op_id", "trace_id"):
            self.assertIn(k, rec)
        self.assertEqual(json.loads(buf.getvalue())["tenants"], [rec["tenants"][0]])
        self.assertTrue(rec["tenants"][0].startswith("t_"))


class SoakBurstTest(unittest.TestCase):
    """Checklist 44 (scaled to CI): fleet of N nodes, burst of decisions,
    memory/latency bounded.  Fleet-scale lab runs remain BLOCKED."""

    N_NODES = int(os.environ.get("INV43_SOAK_NODES", "200"))
    N_DECISIONS = int(os.environ.get("INV43_SOAK_DECISIONS", "3000"))

    def test_fleet_burst(self):
        f = Fleet(nodes=tuple(f"n{i:04d}" for i in range(self.N_NODES)))
        try:
            for n in f.roots:
                f.attest(n)
            nodes = sorted(f.roots)
            t0 = time.perf_counter()
            permits = 0
            for i in range(self.N_DECISIONS):
                out = f.reg.decide("sched", nodes[i % len(nodes)], W(f"a{i % 7}"), W(f"b{i % 11}"), tier="microvm")
                permits += bool(out.get("permitted"))
            dt = time.perf_counter() - t0
            self.assertEqual(permits, self.N_DECISIONS)
            self.assertLessEqual(len(f.reg._explain), registry.MAX_EXPLAIN)
            self.assertLess(dt / self.N_DECISIONS, 0.01, "mean decision latency regressed past 10 ms")
        finally:
            f.close()

    def test_explain_store_is_bounded(self):
        old = registry.MAX_EXPLAIN
        registry.MAX_EXPLAIN = 50
        f = Fleet()
        try:
            for _ in range(120):
                f.reg.decide("sched", "node-a", W("a"), W("b"), tier="microvm")
            self.assertEqual(len(f.reg._explain), 50)
        finally:
            registry.MAX_EXPLAIN = old
            f.close()


class RolloutTest(unittest.TestCase):
    """Checklist 45."""

    def test_cohorts(self):
        c = rollout.cohorts([f"n{i}" for i in range(200)])
        self.assertEqual([len(x) for x in c], [2, 18, 80, 100])
        self.assertEqual(sum(len(x) for x in c), 200)

    def test_completes_when_healthy_and_rolls_back_on_breach(self):
        nodes = [f"n{i}" for i in range(100)]
        store, audit = config.ConfigStore(), auditlog.AuditLog()
        d0 = store.provenance["digest"]
        ok = rollout.run(store, audit, nodes, environment={"max_inflight": 32}, probe=lambda c: {"refusal_rate": 0.01},
                         baseline={"refusal_rate": 0.01}, approved_by="alice")
        self.assertEqual(ok["result"], "completed")
        self.assertEqual(store.active["max_inflight"], 32)
        d1 = store.provenance["digest"]
        stage = [0]

        def probe(cohort):
            stage[0] += 1
            return {"refusal_rate": 0.01 if stage[0] < 3 else 0.40}
        bad = rollout.run(store, audit, nodes, environment={"max_inflight": 16}, probe=probe,
                          baseline={"refusal_rate": 0.01}, approved_by="bob")
        self.assertEqual(bad["result"], "rolled_back")
        self.assertEqual(bad["stages"][-1]["breaches"], ["refusal_rate_jump"])
        self.assertEqual(store.provenance["digest"], d1)
        self.assertNotEqual(d0, d1)
        self.assertIn("rollout_aborted", [e["body"]["kind"] for e in audit.entries()])
        with self.assertRaises(ValueError):
            rollout.run(store, audit, nodes, environment={}, probe=probe, baseline={}, approved_by="")


if __name__ == "__main__":
    unittest.main()
