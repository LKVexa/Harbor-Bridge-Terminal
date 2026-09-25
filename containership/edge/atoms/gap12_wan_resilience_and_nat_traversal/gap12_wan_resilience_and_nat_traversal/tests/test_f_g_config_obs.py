"""Groups F and G — configuration/policy plane and observability; plus the
integrated controller (policy inputs, reason codes, explain view)."""
import http.client
import json
import os
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from gap12_wan_resilience_and_nat_traversal.tests._covers import covers  # noqa: E402
from gap12_wan_resilience_and_nat_traversal.wan import config as cfgm, obs, reasons, rollout, security as sec  # noqa: E402
from gap12_wan_resilience_and_nat_traversal.wan.controller import Adapter, Controller  # noqa: E402


class SchemaTest(unittest.TestCase):
    @covers("G12-F067:spec1,spec2,unit,impl-doc,schema,config-tests", "G12-F068:schema", "G12-H086:unit")
    def test_generated_fixtures_docs_and_version_rules(self):
        for name, (cfg, ok) in cfgm.fixtures().items():
            self.assertEqual(not cfgm.validate(cfg), ok, name)
        doc = cfgm.render_markdown()
        for field in cfgm.SCHEMA:
            self.assertIn(f"`{field}`", doc)
        self.assertIn("DEPRECATED", doc)
        docs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "CONFIG_SCHEMA.md")
        if os.path.exists(docs_path):
            with open(docs_path) as fh:
                self.assertEqual(fh.read(), doc, "committed schema doc drifted from the schema")

    @covers("G12-F068:unit,impl-doc,semantic", "G12-F067:semantic", "G12-D052:config")
    def test_semantic_fail_closed_rules(self):
        base = cfgm.defaults()
        probs = cfgm.validate({**base, "require_attestation": False})
        self.assertTrue(any("trust-sensitive" in p for p in probs))
        self.assertTrue(cfgm.validate({**base, "turn_servers": ["turn.example:3478"], "turn_credential": "hunter2"}))
        self.assertTrue(cfgm.validate({**base, "environment": "lab", "strategies": ["relay", "direct"]}))
        self.assertTrue(cfgm.validate({**base, "environment": "lab", "attempt_timeout_s": 10.0, "overall_timeout_s": 5.0}))
        self.assertTrue(cfgm.validate({**base, "environment": "lab", "egress_allow": ["10.0.0.0/8:0-99999"]}))
        self.assertTrue(cfgm.validate({**base, "stun_servers": ["only-one.example:3478"]}))
        self.assertFalse(cfgm.validate({**base, "environment": "lab"}))


class ApplyTest(unittest.TestCase):
    @covers("G12-F069:unit,impl-doc,overlays", "G12-F070:unit,impl-doc,atomic-apply,config-tests",
            "G12-F071:unit,impl-doc,provenance", "G12-F067:overlays,atomic-apply,provenance")
    def test_overlays_atomic_apply_rollback_and_provenance(self):
        health = {"ok": True}
        m = cfgm.ConfigManager(health_check=lambda eff: health["ok"], clock=lambda: 1234.5)
        a1 = m.apply({"environment": "lab"}, {"backoff_ceiling_s": 30}, source="git:abc", author="ci-bot",
                     approvals=["CR-1"])
        self.assertEqual((a1.generation, a1.outcome, a1.source, a1.author), (1, "active", "git:abc", "ci-bot"))
        self.assertEqual(a1.digest, cfgm.fingerprint(m.active))
        self.assertEqual(m.active["backoff_ceiling_s"], 30)                        # site overlay wins
        self.assertEqual(m.artifact_defaults["backoff_ceiling_s"], 60)              # artifact untouched
        with self.assertRaises(cfgm.ConfigError):
            m.apply({"environment": "lab"}, {"backoff_ceiling_s": -5}, source="x", author="y")
        self.assertEqual(m.active["backoff_ceiling_s"], 30)                        # preflight failure changes nothing
        health["ok"] = False
        with self.assertRaises(cfgm.ConfigError):
            m.apply({"environment": "lab"}, {"backoff_ceiling_s": 45}, source="x", author="y")
        self.assertEqual(m.active["backoff_ceiling_s"], 30)                        # health failure -> auto rollback
        health["ok"] = True
        m.apply({"environment": "lab"}, {"backoff_ceiling_s": 45}, source="x", author="y")
        back = m.rollback(author="oncall")
        self.assertEqual(m.active["backoff_ceiling_s"], 30)
        self.assertIn("rollback", back.outcome)
        outcomes = [h.outcome.split(":")[0] for h in m.history]
        self.assertEqual(outcomes, ["active", "rejected", "rolled_back", "active", "active (rollback to generation 1)"])

    @covers("G12-F070:config-tests", "G12-F067:config-tests")
    def test_concurrent_reloads_serialise(self):
        m = cfgm.ConfigManager()
        errs = []

        def go(i):
            try:
                m.apply({"environment": "lab"}, {"backoff_ceiling_s": 10 + i}, source=f"s{i}", author="a")
            except Exception as exc:  # pragma: no cover
                errs.append(exc)
        ts = [threading.Thread(target=go, args=(i,)) for i in range(20)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(errs, [])
        self.assertEqual(sorted(h.generation for h in m.history), list(range(1, 21)))

    @covers("G12-F072:unit,impl-doc", "G12-F073:unit,impl-doc", "G12-F074:unit,impl-doc")
    def test_mechanism_policy_relay_cost_and_flag_expiry(self):
        cfg = cfgm.defaults()
        self.assertFalse(cfgm.mechanism_enabled(cfg, "upnp"))
        self.assertTrue(cfgm.mechanism_enabled(cfg, "relay"))
        self.assertFalse(cfgm.mechanism_enabled(cfg, "hole-punch", zone="dmz", zone_policy={"dmz": {"hole-punch": False}}))
        bad = {**cfg, "environment": "lab", "relay_regions": [{"name": "eu"}]}
        self.assertTrue(cfgm.validate(bad))
        good = {**cfg, "environment": "lab", "relay_regions": [{"name": "eu", "jurisdiction": "EU", "cost_per_gb": 0.02}]}
        self.assertFalse(cfgm.validate(good))
        flags = {"new-punch": {"owner": "team-net", "expires": 100, "value": True, "safe_default": False}}
        c = {**cfg, "feature_flags": flags}
        self.assertTrue(cfgm.flag(c, "new-punch", 50))
        self.assertFalse(cfgm.flag(c, "new-punch", 150))                             # expired -> safe default
        self.assertTrue(cfgm.validate({**cfg, "environment": "lab", "feature_flags": {"x": {"value": True}}}))


class MetricsTest(unittest.TestCase):
    @covers("G12-G075:spec1,spec2,unit,impl-doc,vocabulary,cardinality", "G12-G083:cardinality")
    def test_catalog_cardinality_and_exposition(self):
        m = obs.Metrics(cardinality_budget=3)
        for s in ("direct", "hole-punch", "relay", "extra1", "extra2"):
            m.inc("g12_attempts_total", {"strategy": s, "outcome": "ok"})
        self.assertEqual(m.overflowed["g12_attempts_total"], 2)
        for bad in ("198.51.100.7", "https://x", "ValueError: boom", "a b"):
            with self.assertRaises(ValueError):
                m.inc("g12_policy_rejections_total", {"reason": bad})
        with self.assertRaises(ValueError):
            m.inc("g12_attempts_total", {"strategy": "direct"})                      # wrong label set
        m.observe("g12_establish_seconds", {"strategy": "direct"}, 0.07)
        text = m.expose()
        self.assertIn('g12_attempts_total{strategy="__overflow__",outcome="__overflow__"} 2.0', text)
        self.assertIn('g12_establish_seconds_bucket{strategy="direct",le="0.1"} 1', text)
        for name in ("g12_attempts_total", "g12_relay_bytes_total", "g12_dependency_up", "g12_partitions_total",
                     "g12_retries_total", "g12_relay_cost_usd_total", "g12_policy_rejections_total", "g12_active_paths"):
            self.assertIn(f"# TYPE {name}", text)


class LogTest(unittest.TestCase):
    @covers("G12-G076:spec1,spec2,unit,impl-doc,redaction,vocabulary")
    def test_structured_events_suppression_and_redaction(self):
        clk = [0.0]
        lines = []
        log = obs.EventLog(lines.append, suppress_window=60, clock=lambda: clk[0], lineage={"release": "4.3.0"})
        r = log.emit("G12-E002", "NET_TIMEOUT", peer_token="ep-1", detail="to 198.51.100.7:3478 password=pw1")
        self.assertEqual((r["event_id"], r["reason_class"], r["release"]), ("G12-E002", "network", "4.3.0"))
        self.assertNotIn("198.51.100.7", lines[0])
        self.assertNotIn("pw1", lines[0])
        for _ in range(50):
            clk[0] += 1
            self.assertIsNone(log.emit("G12-E002", "NET_TIMEOUT", peer_token="ep-1"))
        clk[0] = 61
        r = log.emit("G12-E002", "NET_TIMEOUT", peer_token="ep-1")
        self.assertEqual(r["suppressed_repeats"], 50)
        self.assertIn("first_seen", r)
        with self.assertRaises(KeyError):
            log.emit("G12-E002", "NOT_A_REASON")
        r = log.emit("G12-E004", "POLICY_EGRESS_DENIED", obj=object())
        self.assertEqual(r["obj"], "object")                                          # no free-form object dumps


class TraceTest(unittest.TestCase):
    @covers("G12-G077:spec1,spec2,unit,impl-doc,correlation")
    def test_spans_and_untrusted_traceparent(self):
        t = obs.Tracer()
        inbound = "00-" + "ab" * 16 + "-" + "cd" * 8 + "-01"
        root = t.start("request", inbound=inbound, trusted=False)
        self.assertNotEqual(root.trace_id, "ab" * 16)                                # not adopted
        self.assertEqual(root.links, [inbound])
        child = t.start("attempt", parent=root)
        self.assertEqual((child.trace_id, child.parent), (root.trace_id, root.span_id))
        trusted = t.start("request", inbound=inbound, trusted=True)
        self.assertEqual(trusted.trace_id, "ab" * 16)
        self.assertTrue(obs.TP.match(obs.Tracer.header(child)))
        with self.assertRaises(ValueError):
            t.start("arbitrary")


class HealthTest(unittest.TestCase):
    @covers("G12-G078:unit,impl-doc,integration")
    def test_live_ready_metrics_endpoints(self):
        view = {"dns": "up", "identity": "down", "keys": "up"}
        m = obs.Metrics()
        m.set("g12_dependency_up", {"dependency": "dns"}, 1)
        with obs.HealthServer(lambda: obs.readiness_from(view), m) as hs:
            def get(p):
                c = http.client.HTTPConnection(*hs.address, timeout=2)
                c.request("GET", p)
                r = c.getresponse()
                return r.status, r.read()
            self.assertEqual(get("/livez")[0], 200)
            code, body = get("/readyz")
            self.assertEqual(code, 503)
            self.assertEqual(json.loads(body)["detail"]["blocking"], {"identity": "down"})
            view["identity"] = "up"
            self.assertEqual(get("/readyz")[0], 200)
            self.assertIn(b"g12_dependency_up", get("/metrics")[1])
            self.assertEqual(hs.address[0], "127.0.0.1")


class ReasonTest(unittest.TestCase):
    @covers("G12-G079:unit,impl-doc,reason-codes", "G12-G075:reason-codes")
    def test_reason_codes_cover_every_class(self):
        classes = {v[0] for v in reasons.REASONS.values()}
        for need in ("network", "dependency", "policy", "auth", "budget", "defect", "cancelled", "operator"):
            self.assertIn(need, classes)
        with self.assertRaises(KeyError):
            reasons.check("MADE_UP")
        import re
        for code in reasons.REASONS:
            self.assertRegex(code, r"^[A-Z][A-Z0-9_]+$")


class DashAlertTest(unittest.TestCase):
    @covers("G12-G081:unit,impl-doc,alert-validation", "G12-G082:unit,impl-doc,alert-validation",
            "G12-G075:alert-validation")
    def test_generated_dashboard_alerts_and_synthetic_injection(self):
        d = obs.dashboard()
        self.assertEqual(len(d["panels"]), len(obs.CATALOG))
        rules = obs.alert_rules()
        names = {r["alert"] for r in rules}
        self.assertTrue({"G12RetryStorm", "G12RelaySaturation", "G12DnsFailure", "G12TraversalRegression",
                         "G12SecurityEvent", "G12EstablishBurn1h"} <= names)
        cases = {
            "ordinary_load": {"attempts": 100, "retries": 20, "relay_attempts": 10, "holepunch_attempts": 30, "holepunch_ok": 25},
            "retry_storm": {"attempts": 100, "retries": 450},
            "relay_saturation": {"attempts": 100, "retries": 10, "relay_attempts": 70},
            "dns_failure": {"attempts": 100, "dns_failures": 5},
            "traversal_regression": {"attempts": 100, "holepunch_attempts": 40, "holepunch_ok": 5},
            "security_event": {"attempts": 100, "auth_failures": 1},
        }
        for want, rates in cases.items():
            self.assertEqual(obs.classify_incident(rates), want)

    @covers("G12-G083:unit,impl-doc", "G12-G084:unit,impl-doc,correlation")
    def test_retention_policy_and_lineage(self):
        self.assertFalse(obs.RETENTION["metrics"]["contains_endpoints"])
        self.assertEqual(obs.RETENTION["security_audit"]["sampling"], "none (complete)")
        lin = obs.lineage(release="4.3.0", artifact_digest="a" * 64, config_generation=7, config_digest="b" * 64,
                          topology="two_nat")
        self.assertEqual(lin["config_gen"], 7)
        log = obs.EventLog(lineage=lin)
        self.assertEqual(log.emit("G12-E001", "OK")["artifact"], "a" * 16)


class _A(Adapter):
    def __init__(self, name, ok=False, eps=(("198.51.100.1", 3478),), evidence=b"good", hang=0.0):
        super().__init__(name)
        self.ok, self.eps, self.ev, self.hang = ok, list(eps), evidence, hang

    def endpoints(self):
        return self.eps

    def attempt(self, cancel):
        if self.hang:
            time.sleep(self.hang)
        return self.ok

    def evidence(self):
        return self.ev


class ControllerTest(unittest.TestCase):
    def _ctl(self, **kw):
        cfg = {**cfgm.defaults(), "environment": "lab", "attempt_timeout_s": 0.3}
        cfg.update(kw.pop("cfg", {}))

        def verifier(peer, ev):
            if ev != b"good":
                raise ValueError
            return sec.Attestation(peer, time.time() - 1, time.time() + 60, "x")
        return Controller(cfg, sec.TrustGate(verifier), sec.EgressPolicy(allow=[("198.51.100.0/24", (1, 65535))]),
                          sec.RateLimiter({"global": (1000, 1000), "peer": (1000, 1000)}), **kw)

    @covers("G12-C028:selection-inputs,telemetry", "G12-C033:selection-inputs", "G12-A001:fallback-policy",
            "G12-A004:fallback-policy", "G12-A002:fallback-policy", "G12-A005:fallback-policy",
            "G12-G079:telemetry", "G12-G080:unit,impl-doc", "G12-H100:unit")
    def test_policy_gates_are_inputs_and_failures_never_bypass_them(self):
        ctl = self._ctl()
        adapters = {"direct": _A("direct"), "hole-punch": _A("hole-punch", ok=True, evidence=b"forged"),
                    "relay": _A("relay", ok=True, eps=[("203.0.113.9", 3478)])}
        res = ctl.connect("site-b", adapters)
        self.assertFalse(res["ok"])
        trail = {t["strategy"]: t["reason"] for t in res["trail"]}
        self.assertEqual(trail["relay"], "POLICY_EGRESS_DENIED")              # never contacted
        self.assertEqual(trail["hole-punch"], "AUTH_FAILED")                  # reachable but untrusted -> refused
        self.assertIn("g12_policy_rejections_total", ctl.metrics.expose())
        ex = ctl.explain("site-b")
        self.assertTrue(ex["peer"].startswith("ep-"))
        self.assertTrue(all("class" in s for s in ex["decision_trail"]))
        adapters["hole-punch"].ev = b"good"
        res = ctl.connect("site-b", adapters)
        self.assertEqual(res["reason"], "BUDGET_BACKOFF_ACTIVE")              # inside the retry window: no probe
        ctl.store.clock.monotonic = lambda: time.monotonic() + 3600
        res = ctl.connect("site-b", adapters)
        self.assertEqual((res["ok"], res["strategy"], res["trusted"]), (True, "hole-punch", True))

    @covers("G12-C028:unit,telemetry", "G12-I108:unit", "G12-A014:fallback-policy")
    def test_kill_switch_and_mechanism_policy_skip_strategies(self):
        ks = rollout.KillSwitch(b"k", node_scope={"env": "lab"})
        ks.apply(rollout.sign_control(b"k", {"version": 1, "expires": time.time() + 60, "disable": ["hole-punch"]}), actor="op")
        ctl = self._ctl(killswitch=ks)
        adapters = {"direct": _A("direct"), "hole-punch": _A("hole-punch", ok=True), "relay": _A("relay", ok=True)}
        res = ctl.connect("p", adapters)
        self.assertEqual(res["strategy"], "relay")
        self.assertEqual(res["trail"][0], {"strategy": "hole-punch", "outcome": "skipped", "reason": "POLICY_MECHANISM_DISABLED"})

    @covers("G12-D049:telemetry", "G12-D050:unit,telemetry", "G12-E064:telemetry", "G12-H098:unit")
    def test_rate_limit_breaker_quarantine_reason_codes(self):
        ctl = self._ctl()
        ctl.limiter = sec.RateLimiter({"peer": (0.0001, 1)})
        a = {"direct": _A("direct", ok=True)}
        self.assertTrue(ctl.connect("p", a)["ok"])
        self.assertEqual(ctl.connect("p", a)["reason"], "BUDGET_RATE_LIMITED")
        ctl = self._ctl()
        dead = {"direct": _A("direct"), "hole-punch": _A("hole-punch"), "relay": _A("relay")}
        reasons_seen = []
        for i in range(8):
            ctl.store.clock.monotonic = (lambda v=1000.0 + i * 3600: v)
            reasons_seen.append(ctl.connect("p", dead)["reason"])
        self.assertIn("BUDGET_BREAKER_OPEN", reasons_seen)                    # fleet protection above per-path backoff
        ctl.quarantine.add("q", reason="abuse", actor="op")
        self.assertEqual(ctl.connect("q", dead)["reason"], "POLICY_QUARANTINED")

    @covers("G12-C028:fault", "G12-C029:fault")
    def test_hung_adapter_inside_controller(self):
        ctl = self._ctl()
        t0 = time.monotonic()
        res = ctl.connect("p", {"direct": _A("direct", ok=True, hang=2.0), "relay": _A("relay", ok=True)})
        self.assertLess(time.monotonic() - t0, 1.5)
        self.assertEqual(res["strategy"], "relay")
        self.assertEqual(res["trail"][0]["reason"], "CANCELLED_DEADLINE")


if __name__ == "__main__":
    unittest.main()
