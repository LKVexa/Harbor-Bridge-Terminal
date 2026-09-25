"""Unit tests: config transactions (M10), lifecycle (M11), call control (M14),
admission/quotas/breaker (M15), health (M16), residency (M40), SLO (M39),
artifact trust/SBOM (M20), telemetry (M21)."""
import threading, time, unittest
from inv65_capability_providers.tests.helpers import World
from inv65_capability_providers.config.model import ConfigHistory
from inv65_capability_providers.errors.mapping import ProviderFault
from inv65_capability_providers.health.model import HealthModel
from inv65_capability_providers.lifecycle.state_machines import link_machine, provider_machine
from inv65_capability_providers.observability.telemetry import JsonLogger, MAX_SERIES, Metrics, parse_traceparent, redact
from inv65_capability_providers.residency.engine import ResidencyEngine
from inv65_capability_providers.runtime.admission import AdmissionController
from inv65_capability_providers.runtime.call_control import CancelToken, Deadline, Dispatcher, call_with_retry
from inv65_capability_providers.runtime.circuit_breaker import CircuitBreaker
from inv65_capability_providers.runtime.idempotency import IdempotencyCache
from inv65_capability_providers.secret_refs.resolver import SecretValue
from inv65_capability_providers.slo.error_budget import evaluate
from inv65_capability_providers.supply_chain.trust import ArtifactTrust, provenance, sbom


class Clock:
    t = 0.0
    def __call__(self):
        return self.t


def fault_code(fn):
    try:
        fn()
    except ProviderFault as e:
        return e.code
    return None


class ConfigTransactions(unittest.TestCase):
    def test_versioned_provenance_atomic_batch_and_rollback(self):
        h = ConfigHistory(); a, b = ("a",), ("b",)
        r1 = h.propose(a, {"x": 1}, author="alice", reason="init")
        h.activate_batch([(a, r1.version)])
        ra, rb = h.propose(a, {"x": 2}, author="bob", reason="bump"), h.propose(b, {"y": 1}, author="bob", reason="new")
        def veto(k, cfg):
            if k == b:
                raise ProviderFault("PK_PROVIDER_INVALID_LINK", "veto")
        with self.assertRaises(ProviderFault):
            h.activate_batch([(a, ra.version), (b, rb.version)], validator=veto)
        self.assertEqual(h.active(a).config, {"x": 1}); self.assertIsNone(h.active(b))  # nothing half-applied
        h.activate_batch([(a, ra.version), (b, rb.version)])
        rb2 = h.rollback(a, 1, author="carol", reason="bad deploy")
        self.assertEqual((rb2.version, rb2.config, rb2.parent), (3, {"x": 1}, 2))
        hist = h.history(a)
        self.assertEqual([x["state"] for x in hist], ["superseded", "superseded", "active"])
        self.assertTrue(all(x["author"] and x["digest"] for x in hist))

    def test_author_and_reason_required(self):
        with self.assertRaises(ProviderFault):
            ConfigHistory().propose(("a",), {}, author="", reason="x")


class Lifecycle(unittest.TestCase):
    def test_legal_and_illegal_transitions(self):
        p = provider_machine(); p.to("ready"); p.to("draining"); p.to("stopped")
        self.assertEqual(fault_code(lambda: p.to("ready")), "PK_PROVIDER_INVALID_LINK")
        l = link_machine(); l.to("active"); l.to("revoked")
        for s in ("active", "pending", "suspended"):
            self.assertIsNotNone(fault_code(lambda s=s: l.to(s)))

    def test_relink_after_revoke_is_new_generation_with_higher_version(self):
        w = World(); w.svc.start(); v1 = w.link()["config_version"]; w.unlink()
        v2 = w.link()["config_version"]
        self.assertGreater(v2, v1); self.assertEqual(w.call()["config_version"], v2)


class CallControl(unittest.TestCase):
    def test_deadline_validation(self):
        for ms in (0, -1, 700000, 1.5):
            self.assertIsNotNone(fault_code(lambda ms=ms: Deadline(ms)))

    def test_cancellation(self):
        d = Dispatcher(1, 1); tok = CancelToken()
        threading.Timer(0.05, tok.cancel).start()
        self.assertEqual(fault_code(lambda: d.run(lambda: time.sleep(0.5), deadline=Deadline(2000), cancel=tok)), "PK_PROVIDER_CANCELLED")
        d.close()

    def test_backpressure_sheds_when_queue_full(self):
        d = Dispatcher(1, 0); ev = threading.Event()
        t = threading.Thread(target=lambda: d.run(ev.wait, deadline=Deadline(2000))); t.start(); time.sleep(0.05)
        self.assertEqual(fault_code(lambda: d.run(lambda: 1, deadline=Deadline(1000))), "PK_PROVIDER_OVERLOADED")
        ev.set(); t.join(); d.close()

    def test_retry_bounded_and_respects_deadline(self):
        n = []
        def f(a):
            n.append(a); raise ProviderFault("PK_PROVIDER_UNAVAILABLE", "x")
        with self.assertRaises(ProviderFault):
            call_with_retry(f, op="get", deadline=Deadline(5000), max_attempts=3, sleep=lambda s: None)
        self.assertEqual(n, [1, 2, 3]); n.clear()
        with self.assertRaises(ProviderFault):
            call_with_retry(f, op="set", deadline=Deadline(5000), sleep=lambda s: None)
        self.assertEqual(n, [1])

    def test_idempotency_conflict_and_scope(self):
        c = IdempotencyCache(); c.store(("s1",), "k", {"a": 1}, "r")
        self.assertEqual(c.lookup(("s1",), "k", {"a": 1}), "r")
        self.assertIsNone(c.lookup(("s2",), "k", {"a": 1}))
        self.assertEqual(fault_code(lambda: c.lookup(("s1",), "k", {"a": 2})), "PK_PROVIDER_IDEMPOTENCY_CONFLICT")

    def test_service_idempotent_replay(self):
        w = World(); w.svc.start(); w.link()
        m = {"correlation_id": "ab" * 8, "deadline_ms": 1000, "idempotency_key": "order-123456"}
        a = w.call(op="set", payload={"key": "k", "value": 1}, meta=m)
        b = w.call(op="set", payload={"key": "k", "value": 1}, meta=m)
        self.assertTrue(b.get("idempotent_replay")); self.assertEqual(a["result"], b["result"])


class Admission(unittest.TestCase):
    def test_noisy_tenant_does_not_starve_quiet_tenant(self):
        clk = Clock(); a = AdmissionController(tenant_rate=10, tenant_burst=10, link_rate=100, link_burst=100, clock=clk)
        ok = 0
        for _ in range(50):
            try:
                with a.admit("noisy", ("l",)):
                    ok += 1
            except ProviderFault as e:
                self.assertEqual(e.code, "PK_PROVIDER_OVERLOADED"); self.assertGreater(e.retry_after_ms, 0)
        self.assertEqual(ok, 10)
        with a.admit("quiet", ("q",)):
            pass
        clk.t = 1.0
        with a.admit("noisy", ("l",)):
            pass

    def test_concurrency_and_global_caps(self):
        a = AdmissionController(tenant_concurrency=2, global_inflight=3)
        t1, t2 = a.admit("x", ("1",)), a.admit("x", ("2",))
        self.assertEqual(fault_code(lambda: a.admit("x", ("3",))), "PK_PROVIDER_OVERLOADED")
        t3 = a.admit("y", ("1",))
        self.assertEqual(fault_code(lambda: a.admit("z", ("1",))), "PK_PROVIDER_OVERLOADED")
        for t in (t1, t2, t3):
            t.__exit__(None, None, None)
        with a.admit("z", ("1",)):
            pass

    def test_link_quota(self):
        from inv65_capability_providers.runtime.quotas import LinkQuotas
        w = World(); w.svc.quotas = LinkQuotas(max_links_per_workload=2); w.svc.start()
        w.link("a"); w.link("b")
        self.assertEqual(fault_code(lambda: w.link("c")), "PK_PROVIDER_OVERLOADED")
        w.link("a")  # update is not a new link
        self.assertEqual(fault_code(lambda: w.link("d", cfg={"bucket": "b", "user": "u", "blob": "x" * 20000})), "PK_PROVIDER_INVALID_LINK")

    def test_circuit_breaker(self):
        clk = Clock(); b = CircuitBreaker(2, 5, clock=clk)
        b.failure(); b.before(); b.failure()
        self.assertEqual(fault_code(b.before), "PK_PROVIDER_CIRCUIT_OPEN")
        clk.t = 6; b.before()
        self.assertEqual(fault_code(b.before), "PK_PROVIDER_CIRCUIT_OPEN")  # only one probe
        b.success(); b.before(); self.assertEqual(b.state, "closed")


class Health(unittest.TestCase):
    def test_states_reasons_and_stall(self):
        clk = Clock(); h = HealthModel("c", stall_after_s=5, clock=clk)
        h.set_dependency("backend", "ok"); self.assertTrue(h.report("ready")["ready"])
        h.set_dependency("cache", "down", required=False)
        r = h.report("ready"); self.assertEqual((r["state"], r["ready"]), ("degraded", True))
        h.set_dependency("backend", "weird")
        r = h.report("ready"); self.assertFalse(r["ready"]); self.assertIn("DEP_BACKEND_UNKNOWN", r["reasons"])
        clk.t = 10; r = h.report("ready")
        self.assertEqual((r["live"], r["state"]), (False, "failed")); self.assertIn("DISPATCH_STALLED", r["reasons"])
        self.assertFalse(h.report("draining")["ready"])


class Residency(unittest.TestCase):
    def test_constraints(self):
        e = ResidencyEngine(); e.set_policy({"tenant": "t", "allowed_regions": ["eu"], "failover_regions": ["eu2"], "allowed_environments": ["prod"]})
        e.check_placement("t", region="eu", environment="prod")
        for kw in ({"region": "us", "environment": "prod"}, {"region": "eu", "environment": "dev"}):
            self.assertEqual(fault_code(lambda kw=kw: e.check_placement("t", **kw)), "PK_PROVIDER_RESIDENCY")
        self.assertEqual(fault_code(lambda: e.check_placement("t", region="eu", environment="prod", failover=True)), "PK_PROVIDER_RESIDENCY")
        e.check_placement("t", region="eu2", environment="prod", failover=True)
        self.assertEqual(fault_code(lambda: e.check_placement("nobody", region="eu", environment="prod")), "PK_PROVIDER_RESIDENCY")

    def test_service_refuses_link_outside_residency(self):
        w = World(region="eu-central"); w.svc.start()
        self.assertEqual(fault_code(lambda: w.link()), "PK_PROVIDER_RESIDENCY")


class Slo(unittest.TestCase):
    def test_budget_verdicts(self):
        good = {"isolation": {"bad": 0, "total": 100}, "restart_continuity": {"bad": 0, "total": 5},
                "revocation_durability": {"bad": 0, "total": 5}, "call_overhead": {"bad": 1, "total": 1000}}
        self.assertEqual(evaluate(good)["verdict"], "PASS")
        self.assertEqual(evaluate({**good, "isolation": {"bad": 1, "total": 10**6}})["verdict"], "BLOCK")
        self.assertEqual(evaluate({**good, "call_overhead": {"bad": 20, "total": 1000}})["verdict"], "BLOCK")
        self.assertEqual(evaluate({k: v for k, v in good.items() if k != "isolation"})["verdict"], "INSUFFICIENT_DATA")


class SupplyChain(unittest.TestCase):
    def test_sbom_and_provenance_cover_files(self):
        s = sbom("4.3.0"); p = provenance("4.3.0", s)
        names = {c["name"] for c in s["components"]}
        self.assertIn("provider.py", names); self.assertIn("service.py", names)
        self.assertEqual(len(p["subject"]), len(s["components"]))

    def test_catalog_pinning(self):
        t = ArtifactTrust({"contracts": {"c": [{"sha256": "a" * 64}]}})
        t.require("c", "a" * 64)
        self.assertEqual(fault_code(lambda: t.require("c", "b" * 64)), "PK_PROVIDER_UNTRUSTED_ARTIFACT")
        self.assertEqual(fault_code(lambda: t.require("other", "a" * 64)), "PK_PROVIDER_UNTRUSTED_ARTIFACT")


class Telemetry(unittest.TestCase):
    def test_cardinality_guard_and_label_allowlist(self):
        m = Metrics()
        for i in range(MAX_SERIES + 50):
            m.inc("x", {"op": f"o{i}", "tenant": "t"})
        series = [k for k in m._c if k[0] == "x"]
        self.assertLessEqual(len(series), MAX_SERIES + 1); self.assertGreater(m.dropped_labels, 0)
        self.assertNotIn("tenant=", m.exposition())

    def test_redaction(self):
        log = JsonLogger()
        log.log("info", "e", password="p", nested={"apiKey": "k", "ok": 1}, hdr="Bearer abc.def", sv=SecretValue(b"zz", 1))
        line = log.sink[0]
        for bad in ('"p"', '"k"', "abc.def", "zz"):
            self.assertNotIn(bad, line)
        self.assertEqual(redact({"secret_ref": "secret://x"}), {"secret_ref": "secret://x"})

    def test_traceparent(self):
        t, p = parse_traceparent("00-" + "a" * 32 + "-" + "b" * 16 + "-01"); self.assertEqual((t, p), ("a" * 32, "b" * 16))
        t, p = parse_traceparent("garbage"); self.assertEqual((len(t), p), (32, ""))

    def test_service_emits_metrics_traces_and_explanations(self):
        w = World(); w.svc.start(); w.link(); w.call()
        try:
            w.call(tenant="globex")
        except ProviderFault:
            pass
        self.assertEqual(w.svc.metrics.counter("pk_calls", {"contract": "wasi:keyvalue", "op": "get", "outcome": "ok"}), 1)
        self.assertEqual(len(w.svc.tracer.spans), 1)
        self.assertIn('"explain"', w.svc.log.sink[-1]); self.assertIn("PK_PROVIDER_NO_LINK", w.svc.log.sink[-1])
