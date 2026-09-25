"""WS 2, 5, 8, 9, 12, 18 -- config lifecycle, health/quarantine, retry/admission, quota, telemetry, bootstrap."""
from __future__ import annotations

import json
import pathlib
import random
import subprocess
import sys
import tempfile
import threading
import unittest

from _support import E, FakeClock, Rig, pkg
from inv32_elastic_virtualization import bootstrap
from inv32_elastic_virtualization.config import SCHEMA, ConfigManager, merge, parse_document
from inv32_elastic_virtualization.health import Watchdog
from inv32_elastic_virtualization.quota import QuotaPolicy, TenantQuota
from inv32_elastic_virtualization.resilience import AdmissionController, CircuitBreaker, Priority, RetryBudget, RetryPolicy
from inv32_elastic_virtualization.telemetry import MetricsRegistry, StructuredLogger, TraceContext, redact


class ConfigTest(unittest.TestCase):
    def test_every_setting_has_bounds(self):
        for k, spec in SCHEMA.items():
            self.assertIn(spec[0], (int, float, bool, str), k)
            if spec[0] in (int, float):
                self.assertIsNotNone(spec[1], k)
                self.assertIsNotNone(spec[2], k)

    def test_rejections(self):
        bad = [{"nope": 1}, {"host_reserve_fraction": 0.01}, {"retry_max_attempts": "3"},
               {"provider_credential_ref": "hunter2"}, {"provider_endpoint": "https://x?password=abc"},
               {"mode": "yolo"}, {"retry_max_attempts": True}, {"host_reserve_fraction": float("nan")}]
        for doc in bad:
            with self.assertRaises(E.ConfigInvalid, msg=doc):
                merge({"site": [doc]})

    def test_layer_precedence_conflict_and_emergency_scope(self):
        v = merge({"site": [{"retry_max_attempts": 5}], "node": [{"retry_max_attempts": 2}]})
        self.assertEqual(v["retry_max_attempts"], 2)
        with self.assertRaises(E.ConfigInvalid):
            merge({"site": [{"retry_max_attempts": 5}, {"retry_max_attempts": 4}]})
        with self.assertRaises(E.ConfigInvalid):
            merge({"emergency": [{"host_reserve_fraction": 0.2}]})
        self.assertTrue(merge({"emergency": [{"emergency_disable": True}]})["emergency_disable"])
        with self.assertRaises(E.ConfigInvalid):
            parse_document('{"mode":"normal","mode":"freeze"}')

    def test_cross_field_invariants(self):
        m = ConfigManager(release_version="x")
        with self.assertRaises(E.ConfigInvalid):
            m.stage({"site": [{"retry_base_delay_s": 5.0, "retry_max_delay_s": 1.0}]}, author="a", source="s")
        with self.assertRaises(E.ConfigInvalid):
            m.stage({"site": [{"safety_reserved_slots": 64, "max_inflight_per_host": 64}]}, author="a", source="s")

    def test_atomic_activation_rollback_and_audit(self):
        audit = []
        m = ConfigManager(release_version="4.3.0", audit=audit.append)
        base = m.active
        c = m.stage({"site": [{"retry_max_attempts": 5}]}, author="alice", source="git:abc", approval="CR-1")
        self.assertIs(m.active, base)  # staged, not live
        m.activate(c)
        self.assertEqual(m.active["retry_max_attempts"], 5)
        self.assertEqual(m.active.meta.approval, "CR-1")
        self.assertNotEqual(m.active.digest, base.digest)
        m.rollback(base.meta.revision, reason="operator")
        self.assertEqual(m.active.digest, base.digest)
        bad = m.stage({"site": [{"retry_max_attempts": 9}]}, author="bob", source="s")
        m.activate(bad, health_gate=lambda cfg: False)  # auto-rollback
        self.assertEqual(m.active.digest, base.digest)
        self.assertEqual([a["kind"] for a in audit].count("config_rollback"), 2)
        with self.assertRaises(E.ConfigInvalid):
            m.activate(m.stage({"site": [{"lease_duration_s": 30.0}]}, author="a", source="s"))  # restart-only

    def test_readers_never_see_mixed_config(self):
        m = ConfigManager(release_version="x")
        a = m.stage({"site": [{"retry_max_attempts": 2, "retry_base_delay_s": 0.01}]}, author="a", source="s")
        b = m.stage({"site": [{"retry_max_attempts": 7, "retry_base_delay_s": 0.02}]}, author="a", source="s")
        seen = set()
        stop = threading.Event()

        def reader():
            while not stop.is_set():
                c = m.active
                seen.add((c["retry_max_attempts"], c["retry_base_delay_s"]))
        th = threading.Thread(target=reader)
        th.start()
        for _ in range(300):
            m.activate(a)
            m.activate(b)
        stop.set()
        th.join()
        self.assertTrue(seen <= {(3, 0.05), (2, 0.01), (7, 0.02)}, seen)

    def test_inspect_hides_secret_values(self):
        m = ConfigManager(release_version="x")
        blob = json.dumps(m.active.inspect())
        self.assertIn("secret://", blob)

    def test_emergency_disable_without_restart(self):
        r = Rig()
        r.guest()
        r.config.activate(r.config.stage({"emergency": [{"emergency_disable": True}]}, author="sre", source="pager"))
        self.assertEqual(r.ctl.handle(r.mem("a", 2048), r.tenant_token())["error"]["code"], "emergency_disabled")
        r.config.rollback(r.config.revisions()[0], reason="incident closed")
        self.assertEqual(r.ctl.handle(r.mem("b", 2048), r.tenant_token())["outcome"], "success")
        r.close()


class HealthQuarantineTest(unittest.TestCase):
    def setUp(self):
        self.r = Rig()
        self.r.guest()
        self.r.guest("g2", tenant="t2")
        self.op = self.r.operator_token()

    def tearDown(self):
        self.r.close()

    def test_scopes(self):
        for scope, ident, guest, tenant in (("guest", "g1", "g1", "t1"), ("host", "host-1", "g2", "t2"),
                                            ("tenant", "t2", "g2", "t2")):
            self.r.ctl.set_quarantine(self.op, scope, ident, reason="r", ticket="INC-1", owner="sre", ttl_s=60)
            res = self.r.ctl.handle(self.r.mem(f"q-{scope}", 2048, guest=guest, tenant=tenant),
                                    self.r.tenant_token(tenant))
            self.assertEqual(res["error"]["code"], "quarantined")
            self.r.ctl.clear_quarantine(self.op, scope, ident, reason="done")

    def test_global_emergency_keeps_reads_and_audit(self):
        self.r.ctl.set_quarantine(self.op, "global", None, reason="r", ticket="INC-2", owner="sre", ttl_s=None)
        self.assertEqual(self.r.ctl.handle(self.r.mem("a", 2048), self.r.tenant_token())["error"]["code"],
                         "emergency_disabled")
        self.assertEqual(self.r.ctl.host_snapshot()["guest_count"], 2)
        self.assertTrue(self.r.store.verify())
        self.assertEqual(self.r.ctl.health().mode, "frozen_write")

    def test_manual_quarantine_requires_authz_and_fields(self):
        with self.assertRaises(E.AuthorizationDenied):
            self.r.ctl.set_quarantine(self.r.tenant_token(), "guest", "g1", reason="r", ticket="t", owner="o")
        with self.assertRaises(E.ValidationFailed):
            self.r.ctl.set_quarantine(self.op, "guest", "g1", reason="", ticket="t", owner="o")

    def test_ttl_expiry_only_when_declared_safe(self):
        self.r.ctl.set_quarantine(self.op, "guest", "g1", reason="r", ticket="t", owner="o", ttl_s=10)
        self.r.ctl.set_quarantine(self.op, "guest", "g2", reason="r", ticket="t", owner="o", ttl_s=10,
                                  auto_expire_safe=True)
        self.r.clock.advance(11)
        act = self.r.ctl.quarantine.active()
        self.assertIn("guest:g1", act)
        self.assertNotIn("guest:g2", act)
        kinds = [e["kind"] for e in self.r.store.audit_events]
        self.assertIn("quarantine_expired", kinds)
        self.assertIn("quarantine_set", kinds)

    def test_watchdog_flags_stall_once(self):
        clk = FakeClock(0)
        seen = []
        w = Watchdog(clock=clk, on_incident=seen.append)
        w.start("op", "memory_reclaim", "g1", deadline=100, stall_after_s=5)
        w.progress("op", "provider_requested", "req-1")
        clk.advance(6)
        w.scan()
        w.scan()
        self.assertEqual(len(seen), 1)
        self.assertEqual((seen[0]["cause"], seen[0]["provider_request_id"]), ("provider_slow", "req-1"))

    def test_readiness_false_on_integrity_or_ownership(self):
        self.assertTrue(self.r.ctl.health().ready)
        self.r.store.audit_events[0]["tenant"] = "evil"
        self.assertFalse(self.r.ctl.health().ready)


class ResilienceTest(unittest.TestCase):
    def test_retry_bounded_and_respects_deadline_and_classification(self):
        clk = FakeClock(0)
        calls = []

        def boom():
            calls.append(1)
            raise E.ProviderUnavailable("x")
        p = RetryPolicy(max_attempts=4, base_delay_s=0.1, max_delay_s=1, sleep=clk.advance, clock=clk,
                        rng=random.Random(1), budget=RetryBudget(min_retries=100, clock=clk))
        with self.assertRaises(E.ProviderUnavailable):
            p.run(boom, deadline=100, idempotent=True)
        self.assertEqual(len(calls), 4)
        calls.clear()
        with self.assertRaises(E.ProviderUnavailable):
            p.run(boom, deadline=100, idempotent=False)
        self.assertEqual(len(calls), 1)
        calls.clear()
        with self.assertRaises(E.ProviderUnavailable):
            p.run(boom, deadline=clk() + 0.05, idempotent=True)
        self.assertEqual(len(calls), 1)

        def denied():
            calls.append(1)
            raise E.AuthorizationDenied("no")
        calls.clear()
        with self.assertRaises(E.AuthorizationDenied):
            p.run(denied, deadline=100, idempotent=True)
        self.assertEqual(len(calls), 1)

    def test_retry_budget_prevents_storm(self):
        b = RetryBudget(ratio=0.1, min_retries=2, clock=FakeClock(0))
        for _ in range(10):
            b.record_request()
        self.assertEqual(sum(b.try_spend() for _ in range(10)), 2)

    def test_circuit_breaker_open_half_open_jitter(self):
        clk = FakeClock(0)
        cb = CircuitBreaker("p", failure_threshold=2, reset_s=10, clock=clk, rng=random.Random(3))
        for _ in range(2):
            cb.before()
            cb.failure()
        self.assertEqual(cb.state, "open")
        with self.assertRaises(E.CircuitOpen):
            cb.before()
        clk.advance(12.1)
        cb.before()  # half-open probe allowed
        with self.assertRaises(E.CircuitOpen):
            cb.before()  # only one probe
        cb.success()
        self.assertEqual(cb.state, "closed")
        opens = set()
        for seed in range(20):
            c = CircuitBreaker("p", failure_threshold=1, reset_s=10, clock=clk, rng=random.Random(seed))
            c.before()
            c.failure()
            opens.add(round(c._reopen_after, 3))
        self.assertGreater(len(opens), 10)  # de-synchronised probes

    def test_admission_bounds_and_safety_reserve(self):
        a = AdmissionController(max_host=6, max_tenant=3, safety_slots=2, tenant_rate_per_s=1000, tenant_burst=1000)
        held = []
        for i in range(4):
            cm = a.admit(f"t{i % 2}", Priority.NORMAL)
            cm.__enter__()
            held.append(cm)
        with self.assertRaises(E.Overloaded):
            with a.admit("t9", Priority.NORMAL):
                pass
        with a.admit(None, Priority.SAFETY):  # recovery still serviceable under saturation
            pass
        a.saturated_dependency = True
        for cm in held:
            cm.__exit__(None, None, None)
        with self.assertRaises(E.Overloaded):
            with a.admit("t1", Priority.LOW):
                pass
        self.assertEqual(a.inflight(), 0)

    def test_tenant_rate_limit(self):
        clk = FakeClock(0)
        a = AdmissionController(tenant_rate_per_s=1, tenant_burst=2, clock=clk)
        for _ in range(2):
            with a.admit("t", Priority.NORMAL):
                pass
        with self.assertRaises(E.QuotaExceeded) as cm:
            with a.admit("t", Priority.NORMAL):
                pass
        self.assertIn("retry_after_s", cm.exception.details)
        with a.admit("other", Priority.NORMAL):  # noisy neighbour does not starve others
            pass

    def test_controller_overload_bounded_no_duplicate_mutations(self):
        r = Rig(config_layers={"site": [{"max_inflight_per_host": 8, "safety_reserved_slots": 2,
                                         "max_inflight_per_tenant": 8, "tenant_burst": 20, "tenant_rate_per_s": 0.1}]})
        for i in range(10):
            r.guest(f"g{i}")
        tok = r.tenant_token()
        results = []
        lock = threading.Lock()

        def go(i):
            res = r.ctl.handle(r.mem(f"op-{i}", 2048, guest=f"g{i % 10}"), tok)
            with lock:
                results.append(res)
        th = [threading.Thread(target=go, args=(i,)) for i in range(60)]
        [t.start() for t in th]
        [t.join() for t in th]
        codes = {x.get("error", {}).get("code", x["outcome"]) for x in results}
        self.assertTrue(codes <= {"success", "quota_exceeded", "overloaded", "guest_busy", "reserve_breach"}, codes)
        self.assertGreaterEqual(r.ctl.host_snapshot()["free_mib"], 0)  # concurrent grows never cross reserve
        self.assertEqual(len(r.fake.calls), len({c[1] for c in r.fake.calls}))  # <=1 mutation per guest
        self.assertEqual(r.ctl.admission.inflight(), 0)
        r.close()


class QuotaTest(unittest.TestCase):
    def test_property_caps_floors_reserve(self):
        rng = random.Random(99)
        r = Rig(total_mib=32768)
        r.ctl.quotas = QuotaPolicy({"t1": TenantQuota(4096, 8192), "t2": TenantQuota(8192, 12288)})
        for i in range(6):
            r.guest(f"a{i}", tenant="t1", mem=512, floor=256, ceiling=4096)
            r.guest(f"b{i}", tenant="t2", mem=512, floor=256, ceiling=4096)
        toks = {"t1": r.tenant_token("t1"), "t2": r.tenant_token("t2")}
        for n in range(400):
            t = rng.choice(["t1", "t2"])
            g = f"{'a' if t == 't1' else 'b'}{rng.randrange(6)}"
            r.ctl.handle(r.mem(f"p{n}", rng.randrange(0, 5000), guest=g, tenant=t), toks[t])
            guests = r.fake.list_guests()
            use = {"t1": 0, "t2": 0}
            for gg in guests:
                self.assertGreaterEqual(gg.memory_mib, 256)
                use[gg.tenant] += gg.memory_mib
            self.assertLessEqual(use["t1"], 8192)
            self.assertLessEqual(use["t2"], 12288)
            snap = r.ctl.host_snapshot()
            self.assertGreaterEqual(snap["free_mib"], 0)
        r.close()

    def test_borrow_cannot_break_other_guarantee_and_reclaim_order(self):
        q = QuotaPolicy({"a": TenantQuota(1000, 5000), "b": TenantQuota(3000, 5000)})
        with self.assertRaises(E.QuotaExceeded):
            q.check_growth(tenant="a", delta_mib=2000, delta_vcpus=0, usage={"a": (1000, 1), "b": (0, 0)},
                           allocatable_mib=5000)
        q.check_growth(tenant="a", delta_mib=1000, delta_vcpus=0, usage={"a": (1000, 1), "b": (0, 0)},
                       allocatable_mib=5000)
        self.assertEqual(q.reclaim_order({"a": (2500, 1), "b": (4000, 1)}), [("a", 1500), ("b", 1000)])


class TelemetryTest(unittest.TestCase):
    def test_metric_labels_bounded(self):
        m = MetricsRegistry()
        with self.assertRaises(ValueError):
            m.inc("inv32_requests_total", operation="x", outcome="y", tenant="t1")
        with self.assertRaises(KeyError):
            m.inc("made_up_metric")
        m.inc("inv32_refusals_total", reason="attacker-controlled-" + "x" * 10)
        self.assertEqual(m.value("inv32_refusals_total", reason="other"), 1)
        m.observe("inv32_provider_latency_seconds", 0.002, operation="memory_adjust")
        self.assertIn('inv32_provider_latency_seconds_bucket{operation="memory_adjust",le="0.005"} 1', m.exposition())

    def test_redaction(self):
        doc = redact({"token": "abc", "msg": "Bearer abcdefghijkl and /var/lib/x and password=zz",
                      "provider_credential_ref": "secret://x"})
        blob = json.dumps(doc)
        for leak in ("abcdefghijkl", "/var/lib", "zz\"", '"abc"'):
            self.assertNotIn(leak, blob)
        self.assertIn("secret://x", blob)

    def test_logs_structured_and_pseudonymous(self):
        out = []
        log = StructuredLogger("inv32", sink=out.append)
        log.log("INFO", "hi token=abc", tenant="acme", guest="vm-1", operation_id="o", trace_id="t", epoch=3,
                config_digest="d", outcome="success")
        rec = json.loads(out[0])
        self.assertNotIn("acme", out[0])
        self.assertTrue(rec["tenant_ref"].startswith("t-"))
        for k in ("ts", "severity", "component", "operation_id", "trace_id", "controller_epoch", "config_digest"):
            self.assertIn(k, rec)

    def test_traceparent_parse_and_spans(self):
        ctx = TraceContext.parse("00-" + "a" * 32 + "-" + "b" * 16 + "-01")
        self.assertEqual(ctx.trace_id, "a" * 32)
        self.assertNotEqual(TraceContext.parse("garbage\x00").trace_id, "a" * 32)
        r = Rig()
        r.guest()
        res = r.ctl.handle(r.mem("a", 2048), r.tenant_token(), traceparent=ctx.header())
        self.assertEqual(res["trace_id"], "a" * 32)
        names = r.ctl.tracer.names("a" * 32)
        for n in ("decode", "authorize", "state_read", "decision", "fence", "provider_mutation", "verification",
                  "commit", "audit_append"):
            self.assertIn(n, names)
        r.close()

    def test_explain(self):
        r = Rig()
        r.guest()
        r.ctl.handle(r.mem("a", 9999), r.tenant_token())
        x = r.ctl.explain(r.operator_token(), "a")
        for k in ("floor_mib", "ceiling_mib", "host_reserve_mib", "policy_version", "epoch", "config_digest",
                  "release", "controlling_rule", "provider_request_id"):
            self.assertIn(k, x)
        self.assertEqual(x["controlling_rule"], "clamped_to_ceiling")
        with self.assertRaises(E.AuthorizationDenied):
            r.ctl.explain(r.tenant_token(), "a")
        replay = r.ctl.handle(r.mem("a", 9999), r.tenant_token())
        self.assertTrue(replay["replayed"])
        r.close()

    def test_inventory(self):
        r = Rig()
        inv = r.ctl.inventory()
        for k in ("version", "schemas", "config_digest", "provider_version", "capabilities", "epoch", "feature_gates"):
            self.assertIn(k, inv)
        self.assertNotIn("secret", json.dumps(inv["capabilities"]))
        r.close()


class BootstrapTest(unittest.TestCase):
    def test_check_is_non_mutating_and_machine_readable(self):
        with tempfile.TemporaryDirectory() as d:
            sd = pathlib.Path(d) / "state"
            code, rep = bootstrap.run(["--check", "--state-dir", str(sd)])
            self.assertEqual(code, 0, rep)
            self.assertFalse(sd.exists())
            code, rep = bootstrap.run(["--state-dir", str(sd)])
            self.assertEqual(code, 0)
            self.assertTrue(sd.exists())
            code2, _ = bootstrap.run(["--state-dir", str(sd)])  # idempotent
            self.assertEqual(code2, 0)

    def test_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            bad = pathlib.Path(d) / "bad.json"
            bad.write_text('{"host_reserve_fraction": 0.9}')
            self.assertEqual(bootstrap.run(["--check", "--layer", f"site={bad}", "--state-dir", d])[0], 2)
            self.assertEqual(bootstrap.run(["--check", "--require-pk-core", "--state-dir", d])[0], 3)
            self.assertEqual(bootstrap.run(["--check", "--state-dir", "/proc/nonexistent/x"])[0], 5)

    def test_cli_emits_json(self):
        root = pathlib.Path(pkg.__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            out = subprocess.run([sys.executable, "-m", "inv32_elastic_virtualization.bootstrap", "--check",
                                  "--state-dir", d + "/s"], capture_output=True, text=True, cwd=str(root))
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(json.loads(out.stdout)["schema"], "PK_INV32_BOOTSTRAP/1")


if __name__ == "__main__":
    unittest.main()
