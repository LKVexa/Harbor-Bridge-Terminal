"""INV-69 v4.3.0 remediation tests. Each class names the controls it proves (stable IDs for the RTM).

Deterministic, stdlib-only, no network. Run: python -B tests/run_all.py  (also under python -O).
"""
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import json
import random
import threading
import time
import unittest

from harness import M, TOOL_IMPLS, PKG_DIR, build, ctx

cfg, E, lc, ctxm, retry, sb, tr, tel = (M["config"], M["errors"], M["lifecycle"], M["context"], M["retry"],
                                        M["sandbox"], M["trust"], M["telemetry"])
ALL = frozenset(TOOL_IMPLS)
SECRET = "sk-live-9f8e7d6c5b4a39281706"


def base(**extra):
    d = {"schema_version": cfg.SCHEMA_VERSION, "residency": {"zone": "eu-1", "allowed_failover_zones": ["eu-2"]}}
    d.update(extra)
    return d


class ErrorTaxonomyTest(unittest.TestCase):
    """INV-69-C026"""

    def test_registry_codes_unique_categorised_and_complete(self):
        self.assertEqual(len(E.REGISTRY), len({c.code for c in E._CODES}))
        for c in E.REGISTRY.values():
            self.assertIn(c.category, E.CATEGORIES)
            self.assertIn(c.severity, {"info", "warning", "error", "critical"})
        needed = {"validation", "authorization", "approval", "policy", "lifecycle", "dependency", "sandbox", "timeout",
                  "cancellation", "capacity", "integrity", "configuration", "internal"}
        self.assertTrue(needed <= {c.category for c in E.REGISTRY.values()})

    def test_unknown_exception_maps_to_internal_without_message(self):
        err = E.translate(RuntimeError(f"db password={SECRET}"))
        d = err.to_dict()
        self.assertEqual(d["code"], "AGT-INTERNAL-001")
        self.assertNotIn(SECRET, json.dumps(d))
        self.assertTrue(d["correlation_id"].startswith("corr-"))

    def test_unregistered_and_retired_codes_refused(self):
        with self.assertRaises(ValueError):
            E.AgentError("AGT-NOPE-999")

    def test_details_are_redacted(self):
        d = E.AgentError("AGT-VAL-001", details={"api_key": SECRET, "note": f"Bearer {SECRET}"}).to_dict()
        self.assertNotIn(SECRET, json.dumps(d))

    def test_kernel_reasons_all_map_to_codes(self):
        a = M["runtime"].Agent("a", frozenset({"send_email", "search_docs"}), max_steps=2)
        codes = [a.step("send_email", 1)["code"], a.step("nope", 1)["code"], a.step("search_docs", 1)["code"]]
        self.assertEqual(codes, ["AGT-APR-001", "AGT-AUTHZ-001", "AGT-CAP-001"])


class LifecycleTest(unittest.TestCase):
    """INV-69-C015"""

    def test_legal_path_and_terminal(self):
        r = lc.Lifecycle("run", "r")
        for i, s in enumerate(["admitted", "running", "succeeded"]):
            r.transition(s, actor="x", reason="t", request_id=str(i))
        self.assertTrue(r.terminal)
        with self.assertRaises(E.AgentError) as cm:
            r.transition("running", actor="x", reason="t", request_id="z")
        self.assertEqual(cm.exception.code, "AGT-LCY-001")

    def test_illegal_transition_records_nothing(self):
        r = lc.Lifecycle("run", "r")
        with self.assertRaises(E.AgentError):
            r.transition("succeeded", actor="x", reason="t", request_id="1")
        self.assertEqual(r.history, ())

    def test_duplicate_request_is_idempotent_and_reuse_rejected(self):
        r = lc.Lifecycle("run", "r")
        t1 = r.transition("admitted", actor="x", reason="t", request_id="a")
        self.assertIs(r.transition("admitted", actor="x", reason="t", request_id="a"), t1)
        with self.assertRaises(E.AgentError):
            r.transition("rejected", actor="x", reason="t", request_id="a")

    def test_side_effect_dispatch_requires_approval_and_authorization(self):
        inv = lc.Lifecycle("invocation", "i", side_effect=True)
        inv.transition("authorized", actor="az", reason="ok", request_id="1")
        with self.assertRaises(E.AgentError):
            inv.transition("dispatched", actor="x", reason="go", request_id="2")
        inv.transition("pending_approval", actor="k", reason="w", request_id="3")
        inv.transition("authorized", actor="k", reason="ok", request_id="4")
        inv.transition("dispatched", actor="x", reason="go", request_id="5")

    def test_state_not_assignable_and_restore_replays_guards(self):
        r = lc.Lifecycle("approval", "p", policy_version="pv1")
        with self.assertRaises(AttributeError):
            r.state = lc.ApprovalState.CONSUMED
        r.transition("granted", actor="u", reason="ok", request_id="1")
        snap = r.snapshot()
        self.assertEqual(lc.Lifecycle.restore(snap).state, lc.ApprovalState.GRANTED)
        bad = copy.deepcopy(snap)
        bad["history"][0]["to_state"] = "consumed"
        with self.assertRaises(E.AgentError):
            lc.Lifecycle.restore(bad)
        self.assertTrue(all(t.policy_version == "pv1" and t.actor and t.at for t in r.history))

    def test_concurrent_transitions_single_winner(self):
        r = lc.Lifecycle("run", "r")
        r.transition("admitted", actor="x", reason="t", request_id="0")
        r.transition("running", actor="x", reason="t", request_id="1")
        results = []

        def go(i):
            try:
                r.transition("succeeded" if i % 2 else "failed", actor="x", reason="t", request_id=f"c{i}")
                results.append(i)
            except E.AgentError:
                pass
        with ThreadPoolExecutor(8) as p:
            list(p.map(go, range(32)))
        self.assertEqual(len(results), 1)


class ContextTest(unittest.TestCase):
    """INV-69-C025, INV-69-C074"""

    def test_child_deadline_never_exceeds_parent(self):
        c = ctxm.CallContext.new(timeout=0.5)
        ch = c.child("tool_execution", 60)
        self.assertLessEqual(ch.deadline, c.deadline)

    def test_cancellation_propagates_parent_to_child_only(self):
        c = ctxm.CallContext.new()
        ch = c.child("policy")
        ch.cancel.cancel()
        self.assertFalse(c.cancel.cancelled)
        c.cancel.cancel()
        with self.assertRaises(E.AgentError) as cm:
            c.child("policy").check()
        self.assertEqual(cm.exception.code, "AGT-CAN-001")

    def test_deadline_expiry_is_structured_timeout(self):
        c = ctxm.CallContext.new(timeout=0.001)
        time.sleep(0.005)
        with self.assertRaises(E.AgentError) as cm:
            c.check()
        self.assertEqual(cm.exception.code, "AGT-TMO-001")
        self.assertTrue(cm.exception.retryable)

    def test_backpressure_sheds_beyond_waiting_limit(self):
        adm = ctxm.Admission(max_active=3, max_waiting=0, reserved_critical=1)
        c = ctxm.CallContext.new(timeout=1)
        adm.acquire(c)
        adm.acquire(c)
        with self.assertRaises(E.AgentError) as cm:
            adm.acquire(c)
        self.assertEqual(cm.exception.code, "AGT-CAP-003")
        adm.acquire(c, "critical")   # reserved slot
        self.assertEqual(adm.stats()["shed"], 1)

    def test_waiters_bounded_by_own_deadline(self):
        adm = ctxm.Admission(max_active=2, max_waiting=4, reserved_critical=1)
        adm.acquire(ctxm.CallContext.new())
        t0 = time.monotonic()
        with self.assertRaises(E.AgentError) as cm:
            adm.acquire(ctxm.CallContext.new(timeout=0.05))
        self.assertEqual(cm.exception.code, "AGT-TMO-001")
        self.assertLess(time.monotonic() - t0, 1.0)

    def test_traceparent_parse_roundtrip_and_malformed(self):
        t = ctxm.TraceContext.new_root()
        self.assertEqual(ctxm.TraceContext.parse(t.traceparent()), t)
        for bad in ("", "00-xyz", None, 5, "00-" + "0" * 32 + "-" + "1" * 16 + "-01", "x" * 1000):
            p = ctxm.TraceContext.parse(bad)
            self.assertEqual(len(p.trace_id), 32)

    def test_baggage_allowlist_refuses_secrets(self):
        with self.assertRaises(E.AgentError):
            ctxm.CallContext.new(baggage={"api_token": "x"})
        with self.assertRaises(E.AgentError):
            ctxm.CallContext.new(baggage={"user_prompt": "x"})
        self.assertEqual(ctxm.CallContext.new(baggage={"site": "a"}).baggage, (("site", "a"),))

    def test_resume_uses_span_link_not_parentage(self):
        t = ctxm.TraceContext.new_root()
        r = t.linked_root()
        self.assertNotEqual(r.trace_id, t.trace_id)
        self.assertEqual(r.links, (f"{t.trace_id}:{t.span_id}",))


class RetryTest(unittest.TestCase):
    """INV-69-C053, INV-69-C025"""

    def _flaky(self, n, code="AGT-DEP-001"):
        state = {"n": 0}

        def fn(c):
            state["n"] += 1
            if state["n"] <= n:
                raise E.AgentError(code)
            return "ok"
        return fn, state

    def test_idempotent_op_retries_until_success_with_bounded_full_jitter(self):
        fn, st = self._flaky(2)
        sleeps = []
        res = retry.call_with_retry("authorization.check", fn, ctxm.CallContext.new(), rng=random.Random(1),
                                    sleep=sleeps.append, budget=retry.RetryBudget())
        self.assertEqual(res.value, "ok")
        self.assertEqual(st["n"], 3)
        self.assertEqual([a.outcome for a in res.attempts], ["retry", "retry", "ok"])
        pol = retry.RetryPolicy()
        for i, s in enumerate(sleeps):
            self.assertLessEqual(s, min(pol.max_delay, pol.base_delay * 2 ** i))

    def test_side_effect_without_key_is_never_retried(self):
        fn, st = self._flaky(1)
        with self.assertRaises(E.AgentError):
            retry.call_with_retry("tool.execute.side_effect", fn, ctxm.CallContext.new(), sleep=lambda s: None,
                                  budget=retry.RetryBudget())
        self.assertEqual(st["n"], 1)
        fn2, st2 = self._flaky(1)
        retry.call_with_retry("tool.execute.side_effect", fn2, ctxm.CallContext.new(), idempotency_key="k",
                              sleep=lambda s: None, budget=retry.RetryBudget())
        self.assertEqual(st2["n"], 2)

    def test_non_retryable_code_stops_immediately(self):
        fn, st = self._flaky(5, "AGT-AUTHZ-002")
        with self.assertRaises(E.AgentError):
            retry.call_with_retry("authorization.check", fn, ctxm.CallContext.new(), sleep=lambda s: None)
        self.assertEqual(st["n"], 1)

    def test_never_sleeps_past_deadline(self):
        fn, _ = self._flaky(10)
        pol = retry.RetryPolicy(max_attempts=10, base_delay=5, max_delay=5)
        with self.assertRaises(E.AgentError) as cm:
            retry.call_with_retry("authorization.check", fn, ctxm.CallContext.new(timeout=0.5), policy=pol,
                                  rng=random.Random(3), sleep=lambda s: self.fail("slept"),
                                  budget=retry.RetryBudget())
        self.assertIn(cm.exception.code, {"AGT-TMO-001"})

    def test_cancellation_honoured_before_attempt(self):
        c = ctxm.CallContext.new()
        c.cancel.cancel()
        with self.assertRaises(E.AgentError) as cm:
            retry.call_with_retry("authorization.check", lambda x: 1, c)
        self.assertEqual(cm.exception.code, "AGT-CAN-001")

    def test_retry_budget_prevents_storms(self):
        b = retry.RetryBudget(ratio=0.0, floor=2)
        spent = 0
        for _ in range(5):
            fn, _ = self._flaky(1)
            try:
                retry.call_with_retry("authorization.check", fn, ctxm.CallContext.new(), sleep=lambda s: None, budget=b)
                spent += 1
            except E.AgentError as e:
                self.assertEqual(e.code, "AGT-DEP-002")
        self.assertEqual(spent, 2)

    def test_unclassified_operation_refused(self):
        with self.assertRaises(E.AgentError):
            retry.call_with_retry("mystery.op", lambda c: 1, ctxm.CallContext.new())


class ConfigTest(unittest.TestCase):
    """INV-69-C033, INV-69-C035, INV-69-C036, INV-69-C037, INV-69-C012"""

    def test_secure_defaults_resolve_and_are_safe(self):
        e = cfg.resolve([("base", base())])
        self.assertTrue(e.get("approval.required_for_side_effects"))
        self.assertEqual(e.get("sandbox.high_risk_tier"), "heavy")
        self.assertFalse(e.get("approval.allow_cached_offline"))
        self.assertIn("approval_gate", e.capabilities())

    def test_strict_parser_rejects(self):
        cases = ['{"a":1,"a":2}', '[]', '{"x": NaN}', '\xff', '{"schema_version": 1']
        for c in cases:
            with self.assertRaises(E.AgentError):
                cfg.loads_strict(c.encode("latin-1") if c == '\xff' else c)
        for doc in (base(unknown=1), base(budgets={"max_steps": "10"}), base(budgets={"max_steps": 0}),
                    base(budgets={"max_steps": True}), {"schema_version": "PK_AGENT_CONFIG/9"},
                    base(audit={"export_endpoint": "https://x?token=" + SECRET}), base(budgets=None)):
            with self.assertRaises(E.AgentError, msg=str(doc)):
                cfg.resolve([("base", doc)])

    def test_locked_fields_refused_at_lower_scope_and_emergency_tighten_only(self):
        with self.assertRaises(E.AgentError) as cm:
            cfg.resolve([("base", base()), ("site", {"sandbox": {"high_risk_tier": "heavy"}})])
        self.assertEqual(cm.exception.code, "AGT-CFG-002")
        with self.assertRaises(E.AgentError):
            cfg.resolve([("base", base()), ("instance", {"approval": {"required_for_side_effects": False}})])
        e = cfg.resolve([("base", base()), ("emergency", {"budgets": {"max_steps": 1}})])
        self.assertEqual(e.get("budgets.max_steps"), 1)
        with self.assertRaises(E.AgentError):
            cfg.resolve([("base", base()), ("emergency", {"budgets": {"max_steps": 500}})])

    def test_overlay_explain_digest_and_layer_order(self):
        e = cfg.resolve([("base", base()), ("environment", {"approval": {"ttl_s": 60}}),
                         ("site", {"offline": {"max_queue": 0}}), ("instance", {"budgets": {"max_steps": 7}})])
        src = {x["field"]: x["source"] for x in e.explain()}
        self.assertEqual(src["approval.ttl_s"], "environment")
        self.assertEqual(src["budgets.max_steps"], "instance")
        self.assertEqual(src["sandbox.high_risk_tier"], "default")
        self.assertEqual([l[0] for l in e.layers], ["default", "profile", "base", "environment", "site", "instance"])
        self.assertTrue(all(x["value"] == "<redacted>" for x in e.explain() if x["field"] == "audit.export_endpoint"))
        with self.assertRaises(E.AgentError):
            cfg.resolve([("site", {}), ("base", base())])

    def test_same_code_bytes_across_sites(self):
        code_digest = hashlib.sha256(b"".join(p.read_bytes() for p in sorted(PKG_DIR.glob("*.py")))).hexdigest()
        a = cfg.resolve([("base", base()), ("site", {"offline": {"max_queue": 0}})])
        b = cfg.resolve([("base", base()), ("site", {"budgets": {"max_transcript_events": 512}})])
        self.assertNotEqual(a.digest, b.digest)
        self.assertEqual(code_digest, hashlib.sha256(b"".join(p.read_bytes() for p in sorted(PKG_DIR.glob("*.py")))).hexdigest())

    def test_profiles_enforce_mandatory_and_prohibited_capabilities(self):
        profs = cfg.load_profiles()
        self.assertEqual(set(profs), {"cloud", "datacenter", "near_edge", "far_edge"})
        with self.assertRaises(E.AgentError):   # far_edge prohibits cross-zone failover configured in base()
            cfg.resolve([("base", base()), ("environment", {"profile": "far_edge"})])
        far = cfg.resolve([("base", {"schema_version": cfg.SCHEMA_VERSION}), ("environment", {"profile": "far_edge"})])
        self.assertEqual(far.get("sandbox.low_risk_tier"), "heavy")
        self.assertNotIn("fast_sandbox", far.capabilities())
        with self.assertRaises(E.AgentError):   # cloud prohibits offline queue
            cfg.resolve([("base", base()), ("site", {"offline": {"queue_enabled": True, "max_queue": 5}})])
        with self.assertRaises(E.AgentError):
            cfg.resolve([("base", base()), ("environment", {"profile": "moon_base"})])

    def test_atomic_generations_cas_provenance_and_rollback(self):
        store = cfg.ConfigStore(cfg.resolve([("base", base())]), author="boot")
        g1 = store.activate([("base", base()), ("instance", {"budgets": {"max_steps": 5}})],
                            expected_generation=0, author="alice", reviewer="bob")
        self.assertEqual(g1.number, 1)
        with self.assertRaises(E.AgentError) as cm:
            store.activate([("base", base())], expected_generation=0, author="carol")
        self.assertEqual(cm.exception.code, "AGT-CFG-003")
        with self.assertRaises(E.AgentError):   # invalid candidate leaves generation 1 active
            store.activate([("base", base(budgets={"max_steps": -1}))], expected_generation=1, author="d")
        self.assertEqual(store.active.number, 1)
        store.rollback(0, expected_generation=1, author="alice")
        self.assertEqual(store.active.config.digest, store.provenance[0]["config_digest"])
        self.assertTrue(store.verify_provenance())
        rec = store.provenance[1]
        for k in ("config_digest", "author", "reviewer", "activated_at", "supersedes", "layers", "time_trusted"):
            self.assertIn(k, rec)
        store._provenance[1]["author"] = "mallory"
        self.assertFalse(store.verify_provenance())

    def test_untrusted_time_can_block_activation(self):
        store = cfg.ConfigStore(cfg.resolve([("base", base())]), trusted_time=lambda: (time.time(), False))
        with self.assertRaises(E.AgentError) as cm:
            store.activate([("base", base())], expected_generation=0, author="a", require_trusted_time=True)
        self.assertEqual(cm.exception.code, "AGT-TRU-001")

    def test_concurrent_writers_exactly_one_wins(self):
        store = cfg.ConfigStore(cfg.resolve([("base", base())]))
        profiles = cfg.load_profiles()
        wins = []

        def w(i):
            try:
                store.activate([("base", base()), ("instance", {"budgets": {"max_steps": 1 + i}})],
                               expected_generation=0, author=f"w{i}", profiles=profiles)
                wins.append(i)
            except E.AgentError as e:
                assert e.code == "AGT-CFG-003"
        with ThreadPoolExecutor(8) as p:
            list(p.map(w, range(16)))
        self.assertEqual(len(wins), 1)
        self.assertEqual(len(store.provenance), 2)


class PrecedenceTest(unittest.TestCase):
    """INV-69-C019"""
    P = M["precedence"]

    def test_security_beats_cost_and_trace_names_winner(self):
        cons = [self.P.Constraint("cheap", "cost", lambda c: c["tier"] == "fast"),
                self.P.Constraint("isolation", "security", lambda c: c["tier"] == "heavy")]
        # cost is waivable but unwaived -> no candidate satisfies both
        with self.assertRaises(E.AgentError) as cm:
            self.P.resolve([{"tier": "fast"}, {"tier": "heavy"}], cons)
        dec = cm.exception.details["decision"]
        self.assertEqual(dec["winning_constraint"], "isolation")
        self.assertEqual(dec["policy_version"], self.P.PRECEDENCE_POLICY["version"])

    def test_waiver_only_for_waivable_in_scope_unexpired(self):
        cons = [self.P.Constraint("cheap", "cost", lambda c: c["tier"] == "fast"),
                self.P.Constraint("isolation", "security", lambda c: c["tier"] == "heavy")]
        w = self.P.Waiver("W-9", "cost", "tenant:a", "owner", "budget exception", time.time() + 3600, "audit#1")
        d = self.P.resolve([{"tier": "fast"}, {"tier": "heavy"}], cons, scope="tenant:a", waivers=[w])
        self.assertEqual(d.chosen, {"tier": "heavy"})
        self.assertEqual(d.waivers_used, ["W-9"])
        for bad in (self.P.Waiver("W-8", "security", "*", "o", "j", time.time() + 60, "a"),
                    self.P.Waiver("W-7", "cost", "tenant:b", "o", "j", time.time() + 60, "a"),
                    self.P.Waiver("W-6", "cost", "*", "o", "j", time.time() - 1, "a"),
                    self.P.Waiver("W-5", "cost", "*", "o", "j", time.time() + 400 * 86400, "a")):
            with self.assertRaises(E.AgentError):
                self.P.resolve([{"tier": "fast"}, {"tier": "heavy"}], cons, scope="tenant:a", waivers=[bad])

    def test_deterministic(self):
        cons = [self.P.Constraint("iso", "security", lambda c: c["t"] >= 2), self.P.Constraint("c", "cost", lambda c: True)]
        a = self.P.resolve([{"t": 1}, {"t": 2}], cons).to_dict()
        b = self.P.resolve([{"t": 1}, {"t": 2}], cons).to_dict()
        self.assertEqual(a, b)

    def test_runtime_cannot_downgrade_high_risk_even_when_forced_cheap(self):
        rt = build()
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        self.assertEqual(rt.invoke("r", "run_python", "x", c)["tier"], "heavy")
        self.assertEqual(rt.decisions[-1]["policy_version"], self.P.PRECEDENCE_POLICY["version"])


class TrustTest(unittest.TestCase):
    """INV-69-C048, INV-69-C018, INV-69-C056"""

    def _mon(self, clock):
        m = tr.TrustMonitor(clock=clock, max_queue=2)
        for d in tr.DEPENDENCY_MATRIX:
            m.report(d, tr.Health.UP, version="v1")
        return m

    def test_keys_or_time_down_blocks_approval_and_is_evented(self):
        now = [1000.0]
        m = self._mon(lambda: now[0])
        m.report("keys", tr.Health.DOWN, reason="kms timeout")
        with self.assertRaises(E.AgentError) as cm:
            m.gate("approval")
        self.assertEqual(cm.exception.code, "AGT-TRU-001")
        self.assertTrue(any(e["kind"] == "fail_closed" for e in m.events))
        m.report("keys", tr.Health.UP)
        m.report("time", tr.Health.DOWN)
        with self.assertRaises(E.AgentError):
            m.gate("approval")
        m.gate("in_flight")  # time loss does not stop in-flight bookkeeping

    def test_policy_cache_allowed_only_within_freshness(self):
        now = [1000.0]
        m = self._mon(lambda: now[0])
        m.report("policy", tr.Health.DOWN)
        d = m.gate("admission", ("policy",))
        self.assertEqual(d["checks"][0]["result"], "cache")
        now[0] += 301
        with self.assertRaises(E.AgentError):
            m.gate("admission", ("policy",))

    def test_noncritical_loss_degrades_not_fails(self):
        m = self._mon(time.time)
        m.report("fast_sandbox", tr.Health.DOWN)
        m.report("telemetry", tr.Health.DOWN)
        d = m.gate("tool_execution")
        self.assertIn("fast_sandbox", d["degraded"])
        self.assertIn("fast_sandbox", m.blocked_capabilities())
        self.assertIn("telemetry_export", m.blocked_capabilities())

    def test_offline_classification_queue_bound_and_reconcile(self):
        m = self._mon(time.time)
        m.set_connectivity(tr.Connectivity.OFFLINE)
        with self.assertRaises(E.AgentError):
            m.network_op("tool.side_effect")
        with self.assertRaises(E.AgentError):
            m.network_op("artifact.fetch")
        self.assertEqual(m.network_op("identity.verify"), "cache")
        self.assertEqual(m.network_op("tool.readonly_local"), "local")
        self.assertEqual(m.network_op("audit.export", payload_ref="e1", assumptions={"policy": "v1"}), "queued")
        self.assertEqual(m.network_op("audit.export", payload_ref="e1", assumptions={"policy": "v1"}), "queued")
        with self.assertRaises(E.AgentError) as cm:
            m.network_op("audit.export", payload_ref="e3")
        self.assertEqual(cm.exception.code, "AGT-CAP-003")
        drained = m.set_connectivity(tr.Connectivity.ONLINE)
        keep, drop = tr.reconcile(drained, {"policy": "v1"})
        self.assertEqual([o.local_seq for o in keep], [1])
        self.assertEqual(len(drop), 1)   # duplicate suppressed
        keep2, drop2 = tr.reconcile(drained[:1], {"policy": "v2"})
        self.assertEqual((keep2, len(drop2)), ([], 1))   # assumptions changed -> discarded

    def test_never_verified_dependency_fails_closed_at_startup(self):
        m = tr.TrustMonitor()
        with self.assertRaises(E.AgentError):
            m.gate("startup")

    def test_runtime_offline_blocks_side_effects_allows_readonly(self):
        rt = build()
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        rt.set_offline(True)
        with self.assertRaises(E.AgentError) as cm:
            rt.invoke("r", "send_email", 1, c)
        self.assertEqual(cm.exception.code, "AGT-DEP-002")
        self.assertEqual(rt.invoke("r", "search_docs", 1, c)["outcome"], "ran")
        st = rt.status()
        self.assertIn("HLT-OFFLINE", st["reasons"])
        self.assertFalse(st["ready"]["side_effect_tools"])
        self.assertIn("tool.side_effect", st["blocked_capabilities"])


class ArtifactTest(unittest.TestCase):
    """INV-69-C045"""
    A = M["artifacts"]

    def setUp(self):
        self.signer = self.A.HmacSigner({"k1": b"trust-root-1"})
        self.policy = {"schema": self.A.TRUST_POLICY_SCHEMA, "version": "tp-1", "revoked_digests": [],
                       "classes": {"tool_plugin": {"allowed_sources": ["registry.internal"], "signers": ["k1"],
                                                   "approved_versions": {"mail": ["1.2.0"]}, "execution_tier": "fast"},
                                   "generated_code": {"allowed_sources": ["model-gateway"], "signers": ["k1"],
                                                      "execution_tier": "heavy"}}}
        self.v = self.A.ArtifactVerifier(self.policy, pinned_policy_digest=self.A.policy_digest(self.policy),
                                         signer=self.signer)

    def art(self, content=b"code", name="mail", klass="tool_plugin", version="1.2.0", source="registry.internal",
            key="k1", sign=True, prov=None, digest=None):
        d = digest or hashlib.sha256(content).hexdigest()
        sig = self.signer.sign("k1", f"{klass}\n{name}\n{version}\n{hashlib.sha256(content).hexdigest()}".encode()) if sign else "00"
        return self.A.Artifact(name, klass, version, source, content, d, sig, key, prov)

    def test_accept_then_cache_by_digest(self):
        r = self.v.verify(self.art())
        self.assertEqual((r["decision"], r["cached"], r["execution_tier"]), ("accepted", False, "fast"))
        self.assertTrue(self.v.verify(self.art())["cached"])
        self.assertEqual(self.v.audit[-1]["policy_version"], "tp-1")

    def test_each_failure_class_rejects(self):
        bad = [self.art(digest="0" * 64), self.art(source="evil.example"), self.art(version="9.9.9"),
               self.art(sign=False), self.art(key="k2"), self.art(klass="dependency_package"),
               self.art(klass="generated_code", source="model-gateway", name="gen")]
        for a in bad:
            with self.assertRaises(E.AgentError) as cm:
                self.v.verify(a)
            self.assertEqual(cm.exception.code, "AGT-INT-002")
        self.assertTrue(all(x["decision"] == "rejected" for x in self.v.audit))

    def test_generated_code_bound_to_provenance_and_forced_heavy(self):
        prov = {"request_id": "req-1", "model": "m", "toolchain": "t", "input_digest": "d"}
        r = self.v.verify(self.art(b"print(1)", name="gen", klass="generated_code", source="model-gateway", prov=prov))
        self.assertEqual(r["execution_tier"], "heavy")
        self.assertEqual(r["provenance_ref"], "req-1")

    def test_tampered_policy_and_revocation(self):
        p2 = copy.deepcopy(self.policy)
        p2["classes"]["tool_plugin"]["allowed_sources"].append("evil")
        with self.assertRaises(E.AgentError):
            self.A.ArtifactVerifier(p2, pinned_policy_digest=self.A.policy_digest(self.policy), signer=self.signer)
        a = self.art()
        p3 = copy.deepcopy(self.policy)
        p3["revoked_digests"] = [a.expected_digest]
        v3 = self.A.ArtifactVerifier(p3, pinned_policy_digest=self.A.policy_digest(p3), signer=self.signer)
        with self.assertRaises(E.AgentError):
            v3.verify(a)

    def test_generated_code_routes_heavy_in_runtime(self):
        rt = build()
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        self.assertEqual(rt.invoke("r", "search_docs", "gen", c, generated=True)["tier"], "heavy")


class CompatTest(unittest.TestCase):
    """INV-69-C016, INV-69-C027, INV-69-C093"""
    C = M["compat"]

    def test_handshake_accepts_agrees_and_disables(self):
        h = self.C.handshake({"component": "INV-59", "version": "4.3.1", "protocol": "PK_AGENT_PEER/1",
                              "capabilities": ["step.v1"]})
        self.assertEqual(h["agreed_capabilities"], ["step.v1"])
        self.assertIn("fencing_tokens", h["disabled_features"])

    def test_rejections_before_side_effects(self):
        for peer, req in (({"component": "INV-59", "version": "4.3.0", "protocol": "PK_AGENT_PEER/2"}, frozenset()),
                          ({"component": "INV-57", "version": "4.3.0", "protocol": "PK_AGENT_PEER/1", "capabilities": []},
                           frozenset({"fencing_tokens"})),
                          ({"component": "INV-57", "version": "4.1.0", "protocol": "PK_AGENT_PEER/1",
                            "capabilities": ["fencing_tokens"]}, frozenset()),
                          ({"protocol": 7}, frozenset()), ({"protocol": "junk"}, frozenset())):
            with self.assertRaises(E.AgentError) as cm:
                self.C.handshake(peer, required=req)
            self.assertEqual(cm.exception.code, "AGT-CMP-001")

    def test_runtime_refuses_skewed_peer_at_construction(self):
        class Old(sb.DurableExecutionAdapter):
            version = "4.1.0"
        with self.assertRaises(E.AgentError):
            build(durable=Old())

    def test_migrate_reader_window(self):
        doc = {"schema": "PK_AGENT_STEP/1", "x": 1}
        self.assertEqual(self.C.migrate(doc), doc)
        with self.assertRaises(E.AgentError):
            self.C.migrate({"schema": "PK_AGENT_STEP/2"})
        with self.assertRaises(E.AgentError):
            self.C.migrate({"schema": "PK_OTHER/1"})
        self.C.MIGRATORS[("PK_AGENT_ERROR", 0)] = lambda d: dict(d, schema="PK_AGENT_ERROR/1", migrated=True)
        try:
            self.assertTrue(self.C.migrate({"schema": "PK_AGENT_ERROR/0"})["migrated"])
        finally:
            del self.C.MIGRATORS[("PK_AGENT_ERROR", 0)]

    def test_deprecation_warning_structured(self):
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.C.deprecated("Agent.approvals direct mutation")
        self.assertTrue(issubclass(w[0].category, self.C.AgentDeprecationWarning))
        self.assertIn("5.0.0", str(w[0].message))

    def test_matrix_consistent_with_code_and_lock(self):
        m = self.C.load_matrix()
        self.assertEqual(m["version"], self.C.COMPONENT_VERSION)
        self.assertEqual(self.C.support_state("INV-69", self.C.COMPONENT_VERSION, m), "fully_supported")
        self.assertEqual({k: int(v) for k, v in m["schemas"].items() if k in self.C.SCHEMAS}, self.C.SCHEMAS)
        self.assertEqual(pkg_version(), self.C.COMPONENT_VERSION)


def pkg_version():
    import importlib
    return importlib.import_module(PKG_DIR.name).__version__


class IntegrationTest(unittest.TestCase):
    """INV-69-C030, INV-69-C083 (adapter tier; certification tier against real peers is W-002)"""

    def test_happy_path_authorize_approve_execute_audit(self):
        rt = build()
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        self.assertEqual(rt.invoke("r", "send_email", {"to": "a"}, c)["outcome"], "pending")
        rt.approve("r", "send_email", {"to": "a"}, "reviewer", c)
        out = rt.invoke("r", "send_email", {"to": "a"}, c)
        self.assertEqual((out["outcome"], out["tier"]), ("ran", "fast"))
        rt.finish_run("r")
        self.assertTrue(rt.verify_events())
        self.assertTrue(rt.runs["r"].agent.verify_transcript())
        kinds = [e["kind"] for e in rt.events]
        self.assertEqual(kinds, ["run_started", "invocation", "approval_recorded", "invocation", "run_ended"])
        self.assertEqual(len({e["correlation_id"] for e in rt.events}), 1)

    def test_fast_and_heavy_routing_matches_policy(self):
        rt = build()
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        self.assertEqual(rt.invoke("r", "search_docs", 1, c)["tier"], "fast")
        self.assertEqual(rt.invoke("r", "run_python", 1, c)["tier"], "heavy")
        self.assertEqual(len(rt.fast.executions), 1)
        self.assertEqual(len(rt.heavy.executions), 1)

    def test_inv59_deny_timeout_malformed(self):
        rt = build(faults={"authz": sb.FaultPlan({"authorize": ["timeout", "ok"]})})
        c = ctx()
        rt.start_run("r", principal="bob", allow=ALL, ctx=c)
        with self.assertRaises(E.AgentError) as cm:
            rt.invoke("r", "run_python", 1, c)            # timeout retried, then policy deny
        self.assertEqual(cm.exception.code, "AGT-AUTHZ-002")
        self.assertEqual(rt.authz.calls, 2)
        rt.authz.faults.add("authorize", "malformed")
        with self.assertRaises(E.AgentError) as cm:
            rt.invoke("r", "search_docs", 1, c)
        self.assertEqual(cm.exception.code, "AGT-DEP-002")
        self.assertEqual(len(rt.heavy.executions) + len(rt.fast.executions), 0)

    def test_sandbox_failure_malformed_and_fast_unavailable_falls_to_heavy(self):
        rt = build(faults={"fast": sb.FaultPlan({"execute": ["malformed"]})})
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        with self.assertRaises(E.AgentError) as cm:
            rt.invoke("r", "search_docs", 1, c)
        self.assertEqual(cm.exception.code, "AGT-DEP-002")
        rt.trust.report("fast_sandbox", tr.Health.DOWN)
        self.assertEqual(rt.invoke("r", "search_docs", 2, c)["tier"], "heavy")

    def test_cancellation_and_timeout_are_structured(self):
        rt = build()
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        c.cancel.cancel()
        with self.assertRaises(E.AgentError) as cm:
            rt.invoke("r", "search_docs", 1, c)
        self.assertEqual(cm.exception.code, "AGT-CAN-001")
        self.assertEqual(rt.cancel_run("r")["state"], "cancelled")
        c2 = ctx(timeout=0.001)
        rt.start_run("r2", principal="alice", allow=ALL, ctx=ctx())
        time.sleep(0.01)
        with self.assertRaises(E.AgentError) as cm:
            rt.invoke("r2", "search_docs", 1, c2)
        self.assertEqual(cm.exception.code, "AGT-TMO-001")

    def test_restart_resume_does_not_replay_committed_side_effect(self):
        durable = sb.DurableExecutionAdapter()
        rt1 = build(durable=durable, executor_id="ex-1")
        c = ctx()
        rt1.start_run("r", principal="alice", allow=ALL, ctx=c)
        rt1.invoke("r", "send_email", {"to": "z"}, c)
        rt1.approve("r", "send_email", {"to": "z"}, "reviewer", c)
        rt1.invoke("r", "send_email", {"to": "z"}, c)
        durable.leases["r"] = ("ex-1", durable.leases["r"][1], 0.0, "eu-1")   # lease expired (executor died)
        rt2 = build(durable=durable, executor_id="ex-2", node="node-1")
        rt2.fast = rt1.fast
        info = rt2.adopt("r", principal="alice", allow=ALL, ctx=c, source_executor="ex-1")
        self.assertEqual(info["fence"], 2)
        self.assertEqual(info["restored_attempts"], 2)
        # approvals are not carried over: the same side effect needs re-approval
        self.assertEqual(rt2.invoke("r", "send_email", {"to": "z"}, c)["outcome"], "pending")
        # old executor is fenced out before any side effect
        with self.assertRaises(E.AgentError) as cm:
            rt1.invoke("r", "search_docs", 9, c)
        self.assertEqual(cm.exception.code, "AGT-INT-003")
        self.assertEqual(sum(1 for x in rt1.fast.executions if x["tool"] == "send_email"), 1)

    def test_finish_with_pending_approval_is_illegal_cancel_releases_slot(self):
        rt = build()
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        rt.invoke("r", "delete_records", 1, c)
        with self.assertRaises(E.AgentError) as cm:
            rt.finish_run("r")
        self.assertEqual(cm.exception.code, "AGT-LCY-001")
        self.assertEqual(rt.admission.stats()["active"], 1)
        self.assertEqual(rt.cancel_run("r")["state"], "cancelled")
        self.assertEqual(rt.admission.stats()["active"], 0)

    def test_overload_sheds(self):
        rt = build(layers=[("base", base(concurrency={"max_active": 3, "max_waiting": 0, "reserved_critical": 1}))])
        rt.start_run("a", principal="alice", allow=ALL, ctx=ctx())
        rt.start_run("b", principal="alice", allow=ALL, ctx=ctx())
        with self.assertRaises(E.AgentError) as cm:
            rt.start_run("c", principal="alice", allow=ALL, ctx=ctx())
        self.assertEqual(cm.exception.code, "AGT-CAP-003")
        rt.finish_run("a")
        rt.start_run("c", principal="alice", allow=ALL, ctx=ctx())


class TelemetryTest(unittest.TestCase):
    """INV-69-C074, INV-69-C078, INV-69-C079"""

    def test_audit_unsampled_even_at_zero_trace_rate(self):
        t = tel.Telemetry(sample_rate=0.0)
        t.end_span(t.start_span("x", ctxm.TraceContext.new_root()))
        self.assertEqual(t.buffers["trace"], [])
        rt = build(layers=[("base", base(telemetry={"trace_sample_rate": 0.0}))])
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        rt.invoke("r", "search_docs", 1, c)
        self.assertEqual(len(rt.telemetry.buffers["audit"]), len(rt.events))

    def test_mandatory_buffer_overflow_is_loud(self):
        t = tel.Telemetry(buffer_limit=1)
        t.record("audit", {"a": 1})
        with self.assertRaises(OverflowError):
            t.record("audit", {"a": 2})
        t.record("log", {"message": "x"})
        t.record("log", {"message": "y"})
        self.assertEqual(t.overflow["log"], 1)

    def test_field_allowlist_redaction_and_residency_routing(self):
        t = tel.Telemetry(zone="eu-1")
        t.record("log", {"message": f"Bearer {SECRET}", "raw_prompt": "p", "code": "AGT-VAL-001"})
        self.assertNotIn("raw_prompt", t.buffers["log"][0])
        self.assertNotIn(SECRET, json.dumps(t.buffers["log"]))
        us, eu = [], []
        t.add_exporter("us-1", lambda k, r: us.append(r))
        t.add_exporter("eu-1", lambda k, r: eu.append(r))
        t.flush()
        self.assertEqual((len(us), len(eu)), (0, 1))

    def test_span_attributes_allowlisted(self):
        t = tel.Telemetry(sample_rate=1.0)
        s = t.start_span("tool", ctxm.TraceContext.new_root(), tool="x", prompt="secret prompt", arg=SECRET)
        self.assertEqual(set(s.attributes), {"tool"})

    def test_trace_and_lineage_in_every_event_unknown_not_dropped(self):
        rt = build()
        rt.topology = tel.TopologyAdapter(None)
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        rt.invoke("r", "search_docs", 1, c)
        for e in rt.events:
            self.assertEqual(e["trace_id"], c.trace.trace_id)
            self.assertEqual(e["lineage"]["site"], "unknown")
            self.assertEqual(e["lineage"]["release_id"], "rel-2026-09-22")
        rt2 = build()
        c2 = ctx()
        rt2.start_run("r", principal="alice", allow=ALL, ctx=c2)
        self.assertEqual(rt2.events[0]["lineage"]["site"], "site-a")
        self.assertEqual(rt2.events[0]["lineage"]["topology_snapshot"], "topo-7")

    def test_stale_topology_marked(self):
        a = tel.TopologyAdapter({"version": "t1", "taken_at": 0.0, "nodes": {}}, max_age_s=10)
        self.assertEqual(a.lineage("n").topology_snapshot, "stale:t1")


class StatusTest(unittest.TestCase):
    """INV-69-C071, INV-69-C052"""

    def test_status_schema_and_public_view(self):
        rt = build()
        st = rt.status()
        for k in ("live", "ready", "version", "build_id", "profile", "config", "capabilities", "dependencies",
                  "reasons", "lineage", "telemetry"):
            self.assertIn(k, st)
        pub = rt.status("public")
        self.assertEqual(set(pub), {"schema", "live", "ready", "version", "reasons"})

    def test_status_has_no_secrets_and_capabilities_follow_state(self):
        rt = build(layers=[("base", base(audit={"export_endpoint": "secretref://vault/inv69/export"}))])
        self.assertIn("remote_audit_export", rt.status()["capabilities"])
        rt.trust.report("fast_sandbox", tr.Health.DOWN)
        st = rt.status()
        self.assertNotIn("fast_sandbox", st["capabilities"])
        self.assertNotIn("vault/inv69", json.dumps(st))

    def test_readiness_per_work_class(self):
        rt = build()
        rt.trust.report("keys", tr.Health.DOWN)
        st = rt.status()
        self.assertFalse(st["ready"]["approvals"])
        self.assertFalse(st["ready"]["side_effect_tools"])
        self.assertIn("HLT-DEP-DOWN", st["reasons"])

    def test_watchdog_stall_vs_long_tool_and_queue_age(self):
        now = [0.0]
        w = M["health"].Watchdog(warning_s=5, critical_s=10, queue_warn_s=1, queue_crit_s=3, clock=lambda: now[0])
        w.heartbeat("short")
        w.heartbeat("long", expected_max_s=100)
        now[0] = 11
        codes = {(f.get("run_id"), f["code"]) for f in w.evaluate(queue_age_s=4)}
        self.assertIn(("short", "HLT-STALL-CRIT"), codes)
        self.assertNotIn(("long", "HLT-STALL-CRIT"), codes)
        self.assertIn((None, "HLT-QUEUE-CRIT"), codes)
        now[0] = 150
        self.assertIn(("long", "HLT-STALL-CRIT"), {(f.get("run_id"), f["code"]) for f in w.evaluate()})

    def test_thresholds_are_from_configuration(self):
        rt = build(layers=[("base", base(health={"stall_warning_s": 7.0, "stall_critical_s": 70.0}))])
        self.assertEqual(rt.watchdog.thresholds()["stall_warning_s"], 7.0)


class ExplainTest(unittest.TestCase):
    """INV-69-C077"""

    def test_explain_links_decisions_and_marks_unknowns(self):
        rt = build()
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        rt.invoke("r", "run_python", 1, c)
        x = M["explain"].explain_run(rt.events, rt.decisions, "r", caller_tenants={"acme"})
        txt = M["explain"].render_text(x)
        self.assertIn("sandbox_selection", txt)
        self.assertIn("HARD security", txt)
        self.assertIn("<unavailable>", txt)
        self.assertEqual(x["timeline"][1]["event_hash"], rt.events[1]["event_hash"])
        self.assertEqual(M["explain"].explain_run(rt.events, rt.decisions, "r", caller_tenants={"acme"}), x)

    def test_explain_tenant_scoped(self):
        rt = build()
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        with self.assertRaises(E.AgentError) as cm:
            M["explain"].explain_run(rt.events, rt.decisions, "r", caller_tenants={"other"})
        self.assertEqual(cm.exception.code, "AGT-AUTHZ-002")


class BackupTest(unittest.TestCase):
    """INV-69-C095"""
    B = M["backup"]
    KEY = b"backup-key"

    def _rt(self):
        rt = build()
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        rt.invoke("r", "send_email", 1, c)
        rt.approve("r", "send_email", 1, "reviewer", c)
        rt.invoke("r", "send_email", 1, c)
        rt.approve("r", "send_email", 2, "reviewer", c)   # live approval at backup time
        return rt

    def test_roundtrip_restores_replay_guard_not_approvals(self):
        rt = self._rt()
        bundle = json.loads(json.dumps(self.B.create_backup(rt, key=self.KEY, actor="op")))
        st = self.B.restore_to_staging(bundle, key=self.KEY, actor="op")
        self.assertEqual(st["record"]["approvals_restored"], 0)
        fresh = sb.DurableExecutionAdapter()
        rec = self.B.activate_restore(st, fresh)
        self.assertEqual(set(fresh.effects), set(rt.durable.effects))
        self.assertIsNotNone(rec["activated_at"])

    def test_tamper_detection(self):
        rt = self._rt()
        b = json.loads(json.dumps(self.B.create_backup(rt, key=self.KEY, actor="op")))
        for mutate in (lambda d: d["body"]["run_events"]["events"][1].__setitem__("outcome", "x"),
                       lambda d: d.__setitem__("mac", "0" * 64),
                       lambda d: d["body"]["transcripts"]["r"]["events"][0].__setitem__("reason", "x")):
            d = copy.deepcopy(b)
            mutate(d)
            with self.assertRaises(E.AgentError):
                self.B.restore_to_staging(d, key=self.KEY, actor="op")
        with self.assertRaises(E.AgentError):
            self.B.restore_to_staging(b, key=b"wrong", actor="op")
        d = copy.deepcopy(b)   # attacker recomputes manifest but not MAC
        d["body"]["effects"] = {}
        d["manifest"]["effects"] = hashlib.sha256(b"{}").hexdigest()
        with self.assertRaises(E.AgentError):
            self.B.restore_to_staging(d, key=self.KEY, actor="op")


class FaultInjectionTest(unittest.TestCase):
    """INV-69-C060 — objectives: 0 duplicate side effects; 0 unaudited executions; recovery bounded by retry policy."""

    def test_transient_dependency_faults_recover_within_retry_policy(self):
        rt = build(faults={"authz": sb.FaultPlan({"authorize": ["unavailable", "unavailable"]}),
                           "heavy": sb.FaultPlan({"launch": ["sandbox_unavailable"]})})
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        self.assertEqual(rt.invoke("r", "run_python", 1, c)["outcome"], "ran")
        self.assertEqual(rt.authz.calls, 3)

    def test_persistent_fault_exhausts_and_reports(self):
        rt = build(faults={"authz": sb.FaultPlan({"authorize": ["unavailable"] * 10})})
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        with self.assertRaises(E.AgentError) as cm:
            rt.invoke("r", "search_docs", 1, c)
        self.assertEqual(cm.exception.code, "AGT-DEP-001")
        self.assertTrue(cm.exception.details["exhausted"])
        self.assertEqual(rt.events[-1]["kind"], "invocation_failed")

    def test_crash_after_effect_keyed_retry_is_deduplicated(self):
        rt = build(faults={"fast": sb.FaultPlan({"execute": ["crash_after_effect"]})})
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        rt.invoke("r", "send_email", 5, c)
        rt.approve("r", "send_email", 5, "reviewer", c)
        out = rt.invoke("r", "send_email", 5, c)
        self.assertEqual((out["outcome"], out["deduplicated"]), ("ran", True))
        self.assertEqual(len(rt.fast.executions), 1)

    def test_crash_after_effect_without_retry_is_indeterminate(self):
        rt = build(layers=[("base", base(retry={"max_attempts": 1}))],
                   faults={"fast": sb.FaultPlan({"execute": ["crash_after_effect"]})})
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        rt.invoke("r", "send_email", 5, c)
        rt.approve("r", "send_email", 5, "reviewer", c)
        with self.assertRaises(E.AgentError):
            rt.invoke("r", "send_email", 5, c)
        inv = list(rt.runs["r"].invocations.values())[-1]
        self.assertEqual(inv.state, lc.InvocationState.INDETERMINATE)
        self.assertEqual(len(rt.fast.executions), 1)

    def test_retry_of_keyed_side_effect_is_deduplicated_by_sandbox(self):
        rt = build(faults={"fast": sb.FaultPlan({"execute": ["timeout"]})})
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        rt.invoke("r", "send_email", 6, c)
        rt.approve("r", "send_email", 6, "reviewer", c)
        self.assertEqual(rt.invoke("r", "send_email", 6, c)["outcome"], "ran")
        self.assertEqual(len(rt.fast.executions), 1)

    def test_every_execution_is_audited(self):
        rt = build(faults={"authz": sb.FaultPlan({"authorize": ["unavailable", "ok", "timeout"] * 5})})
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        for i in range(8):
            try:
                rt.invoke("r", "search_docs", i, c)
            except E.AgentError:
                pass
        ran = sum(1 for e in rt.events if e["kind"] == "invocation" and e["outcome"] == "ran")
        self.assertEqual(ran, len(rt.fast.executions))
        self.assertTrue(rt.verify_events())


class DisasterTest(unittest.TestCase):
    """INV-69-C089, INV-69-C055"""

    def test_failover_target_respects_residency_trust_and_capability(self):
        rt = build()
        cands = [{"id": "us", "zone": "us-1", "trust_domain": "td-default", "max_tier": "heavy", "healthy": True},
                 {"id": "eu2-fast", "zone": "eu-2", "trust_domain": "td-default", "max_tier": "fast", "healthy": True},
                 {"id": "eu2-other", "zone": "eu-2", "trust_domain": "td-x", "max_tier": "heavy", "healthy": True},
                 {"id": "eu2-ok", "zone": "eu-2", "trust_domain": "td-default", "max_tier": "heavy", "healthy": True}]
        self.assertEqual(rt.plan_failover(cands)["id"], "eu2-ok")
        with self.assertRaises(E.AgentError) as cm:
            rt.plan_failover(cands[:3])
        whys = {r["why"] for r in cm.exception.details["rejected"]}
        self.assertEqual(whys, {"residency", "sandbox_capability", "trust_domain"})

    def test_split_brain_second_live_executor_refused(self):
        durable = sb.DurableExecutionAdapter()
        rt1 = build(durable=durable, executor_id="ex-1")
        rt1.start_run("r", principal="alice", allow=ALL, ctx=ctx())
        rt2 = build(durable=durable, executor_id="ex-2")
        with self.assertRaises(E.AgentError) as cm:
            rt2.adopt("r", principal="alice", allow=ALL, ctx=ctx(), source_executor="ex-1")
        self.assertEqual(cm.exception.code, "AGT-INT-003")

    def test_control_plane_outage_refuses_new_runs_and_recovers(self):
        rt = build()
        rt.trust.report("identity", tr.Health.DOWN)
        with self.assertRaises(E.AgentError) as cm:
            rt.start_run("r", principal="alice", allow=ALL, ctx=ctx())
        self.assertEqual(cm.exception.code, "AGT-TRU-001")
        self.assertFalse(rt.status()["ready"]["new_runs"])
        rt.trust.report("identity", tr.Health.UP)
        rt.start_run("r", principal="alice", allow=ALL, ctx=ctx())

    def test_long_partition_exceeds_freshness_then_reconnect(self):
        now = [5000.0]
        m = tr.TrustMonitor(clock=lambda: now[0], max_queue=10)
        for d in tr.DEPENDENCY_MATRIX:
            m.report(d, tr.Health.UP, version="v1")
        m.set_connectivity(tr.Connectivity.OFFLINE)
        m.report("policy", tr.Health.DOWN)
        m.gate("admission", ("policy",))
        m.network_op("audit.export", payload_ref="e", assumptions={"policy": "v1"})
        now[0] += 3600
        with self.assertRaises(E.AgentError):
            m.gate("admission", ("policy",))
        m.report("policy", tr.Health.UP, version="v2")
        keep, drop = tr.reconcile(m.set_connectivity(tr.Connectivity.ONLINE), {"policy": "v2"})
        self.assertEqual((len(keep), len(drop)), (0, 1))

    def test_storage_corruption_detected(self):
        B = M["backup"]
        rt = build()
        rt.start_run("r", principal="alice", allow=ALL, ctx=ctx())
        b = B.create_backup(rt, key=b"k", actor="op")
        b["body"]["config_provenance"]["records"][0]["author"] = "x"
        with self.assertRaises(E.AgentError):
            B.restore_to_staging(b, key=b"k", actor="op")


class OpsTest(unittest.TestCase):
    """INV-69-C097 containment; INV-69-C080 alerts"""

    def test_containment_actions_are_effective_and_audited(self):
        rt = build()
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        rt.contain("force_heavy_sandbox", operator="oncall", reason="drill")
        self.assertEqual(rt.invoke("r", "search_docs", 1, c)["tier"], "heavy")
        rt.contain("disable_new_runs", operator="oncall", reason="drill")
        with self.assertRaises(E.AgentError):
            rt.start_run("r2", principal="alice", allow=ALL, ctx=ctx())
        self.assertIn("HLT-CONTAINED", rt.status()["reasons"])
        rt.contain("release_containment", operator="oncall", reason="drill over")
        rt.start_run("r2", principal="alice", allow=ALL, ctx=ctx())
        self.assertEqual([e["action"] for e in rt.events if e["kind"] == "containment"],
                         ["force_heavy_sandbox", "disable_new_runs", "release_containment"])

    def test_alert_classes_are_distinguished(self):
        import importlib
        ae = importlib.import_module(PKG_DIR.name + ".tools.alert_eval")
        rt = build()
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        for i in range(3):
            try:
                rt.approve("r", "send_email", i, "r", c)   # self-approval: agent name == run id
            except E.AgentError:
                pass
        fired = {f["class"] for f in ae.evaluate(rt.telemetry.metrics_snapshot(), rt.status())}
        self.assertIn("attack", fired)
        self.assertNotIn("dependency_failure", fired)
        rt2 = build(faults={"authz": sb.FaultPlan({"authorize": ["unavailable"] * 40})})
        c2 = ctx()
        rt2.start_run("r", principal="alice", allow=ALL, ctx=c2)
        for i in range(3):
            try:
                rt2.invoke("r", "search_docs", i, c2)
            except E.AgentError:
                pass
        fired2 = {f["class"] for f in ae.evaluate(rt2.telemetry.metrics_snapshot(), rt2.status())}
        self.assertIn("dependency_failure", fired2)
        self.assertNotIn("attack", fired2)
        rules = json.loads((PKG_DIR / "ops" / "alerts.json").read_text())
        for r in rules["rules"]:
            self.assertTrue(r["runbook"] and r["owner"])
            anchor = r["runbook"].split("#")[1]
            self.assertIn(f'id="{anchor}"', (PKG_DIR / "ops" / "RUNBOOK.md").read_text())


class SchemaConformanceTest(unittest.TestCase):
    """INV-69-C082 (and C022/C016): every public record variant validates against its versioned JSON Schema."""

    @classmethod
    def setUpClass(cls):
        try:
            import jsonschema  # test-only pin in requirements.lock
        except ImportError:
            raise unittest.SkipTest("jsonschema not installed — VISIBLE SKIP; release profile requires it")
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
        docs = {p.name: json.loads(p.read_text()) for p in (PKG_DIR / "schemas").glob("*.json")}
        reg = Registry().with_resources([(n, Resource.from_contents(d)) for n, d in docs.items()])
        cls.v = {d["title"].split(" ")[0]: Draft202012Validator(d, registry=reg) for d in docs.values()}

    def _ok(self, schema, doc):
        errs = sorted(self.v[schema].iter_errors(doc), key=str)
        self.assertEqual(errs, [], f"{schema}: {errs[:1]}")

    def test_all_runtime_record_variants(self):
        rt = build()
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        rt.invoke("r", "send_email", 1, c)
        rt.approve("r", "send_email", 1, "reviewer", c)
        rt.invoke("r", "send_email", 1, c)
        with self.assertRaises(E.AgentError):
            rt.invoke("r", "nope", 1, c)
        try:
            rt.approve("r", "send_email", 2, "r", c)
        except E.AgentError as e:
            self._ok("PK_AGENT_ERROR/1", e.to_dict())
        rt.contain("force_heavy_sandbox", operator="op", reason="t")
        rt.finish_run("r")
        for ev in rt.events:
            self._ok("PK_AGENT_RUN_EVENT/1", ev)
        self._ok("PK_AGENT_TRANSCRIPT/1", rt.runs["r"].agent.export_transcript())
        self._ok("PK_AGENT_STATUS/1", rt.status())
        self._ok("PK_AGENT_STATUS/1", rt.status("public"))
        kinds = {e["kind"] for e in rt.events}
        self.assertTrue({"run_started", "invocation", "approval_recorded", "approval_refused", "containment",
                         "run_ended"} <= kinds)

    def test_config_documents_and_examples(self):
        for p in [PKG_DIR / "config" / "example.base.json", *sorted((PKG_DIR / "config" / "overlays").glob("*.json"))]:
            self._ok("PK_AGENT_CONFIG/1", json.loads(p.read_text()))
        bad = {"schema_version": "PK_AGENT_CONFIG/1", "budgets": {"max_steps": 0}}
        self.assertTrue(list(self.v["PK_AGENT_CONFIG/1"].iter_errors(bad)))
        with self.assertRaises(E.AgentError):
            cfg.resolve([("base", bad)])   # schema and runtime parser agree


class RetentionTest(unittest.TestCase):
    """INV-69-C088 soak finding: bounded retention via GovernedRuntime.archive (C067 support)"""

    def test_archive_bounds_memory_and_keeps_chain_continuity(self):
        rt = build()
        sink = []
        for i in range(30):
            c = ctx()
            rt.start_run(f"r{i}", principal="alice", allow=ALL, ctx=c)
            rt.invoke(f"r{i}", "search_docs", i, c)
            rt.finish_run(f"r{i}")
        rt.start_run("live", principal="alice", allow=ALL, ctx=ctx())
        info = rt.archive(lambda k, r: sink.append((k, r)))
        self.assertEqual(info["archived_runs"], 30)
        self.assertEqual(list(rt.runs), ["live"])
        self.assertEqual(rt.events, [])
        rt.invoke("live", "search_docs", 1, ctx())
        self.assertTrue(rt.verify_events())
        self.assertEqual(rt.events[0]["prev_hash"], sink[-1][1]["event_hash"])

    def test_audit_export_backlog_refuses_new_work_before_execution(self):
        rt = build()
        rt.telemetry.buffer_limit = 3
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        rt.invoke("r", "search_docs", 1, c)
        rt.invoke("r", "search_docs", 2, c)          # export copy now full (3 records)
        self.assertEqual(rt.audit_export_overflow, 0)
        n_exec = len(rt.fast.executions)
        with self.assertRaises(E.AgentError) as cm:
            rt.invoke("r", "search_docs", 3, c)
        self.assertEqual(cm.exception.code, "AGT-CAP-003")
        self.assertEqual(len(rt.fast.executions), n_exec)
        self.assertEqual(rt.audit_export_overflow, 1)   # the refusal itself is in the chain, not the full copy
        self.assertEqual(rt.events[-1]["kind"], "invocation_failed")
        self.assertIn("HLT-AUDIT-STALL", rt.status()["reasons"])
        rt.archive(lambda k, r: None)
        self.assertEqual(rt.invoke("r", "search_docs", 3, c)["outcome"], "ran")
        self.assertTrue(rt.verify_events())

    def test_failing_sink_drops_nothing(self):
        rt = build()
        c = ctx()
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        rt.finish_run("r")
        n = len(rt.events)

        def bad(k, r):
            raise OSError("store down")
        with self.assertRaises(OSError):
            rt.archive(bad)
        self.assertEqual((len(rt.events), list(rt.runs)), (n, ["r"]))


class GovernanceToolTest(unittest.TestCase):
    """INV-69-C009, C020, C031, C062, C069, C070, C090, C094, C098, C099, C100 — the governance tools fail closed."""

    @classmethod
    def setUpClass(cls):
        import importlib
        cls.T = {n: importlib.import_module(f"{PKG_DIR.name}.tools.{n}")
                 for n in ("governance_check", "rtm", "deps_check", "perf_gate", "release_gate", "capacity_model")}

    def test_owner_placeholders_and_expired_waivers_fail(self):
        import datetime as dt
        g = self.T["governance_check"]
        res = g.run(dt.date(2026, 9, 23))
        self.assertFalse(res["pass"])
        self.assertTrue(any("placeholder" in m for m in res["owners"]))
        late = g.run(dt.date(2027, 6, 1))
        self.assertTrue(any("EXPIRED" in m for m in late["waivers"]))
        self.assertTrue(any("overdue" in m for m in late["reviews"]))

    def test_rtm_validator_catches_broken_refs_and_false_present(self):
        rtm = self.T["rtm"]
        src = json.loads((PKG_DIR / "ops" / "RTM_SOURCE.json").read_text())
        chk = json.loads((PKG_DIR / "CHECKLIST.json").read_text())
        self.assertEqual([e for e in rtm.validate(src, chk) if "missing evidence" not in e], [])
        bad = copy.deepcopy(src)
        bad["controls"]["INV-69-C015"]["implementation"] = ["lifecycle.py::NoSuchThing"]
        bad["controls"]["INV-69-C030"]["status"] = "present"
        errs = rtm.validate(bad, chk)
        self.assertTrue(any("NoSuchThing" in e for e in errs))
        self.assertTrue(any("INV-69-C030" in e for e in errs))
        del bad["controls"]["INV-69-C001"]
        self.assertTrue(any("control set mismatch" in e for e in rtm.validate(bad, chk)))

    def test_deps_runtime_is_stdlib_only(self):
        self.assertEqual(self.T["deps_check"].runtime_imports(), {})

    def _perf(self, p50=300.0):
        lat = {"p50_us": p50, "p95_us": p50 * 2, "p99_us": p50 * 3, "max_us": p50 * 10}
        return {"fingerprint": {"machine": "x86_64", "python": "3.11.15", "optimized_mode": False},
                "latency": {"governed_invoke_fast": lat, "governed_invoke_heavy": lat, "kernel_step": lat},
                "startup": {"import_governed": {"p50_us": 1e5}, "construct_runtime": {"p50_us": 800}},
                "throughput": {"single_thread_ops_s": 3000}, "memory": {"bytes_per_completed_run": 17000},
                "load_shapes": {"steady": {"p99_us": 3000}, "recovery_after_overload": {"p99_us": 3000},
                                "scale_out_in": {"duplicate_side_effects": 0}, "burst_overload": {"timeout": 0}},
                "soak_with_archive": {"leak_verdict": "FLAT (<1 KiB retained per run)"}}

    def test_perf_gate_blocks_regressions_and_threshold_breaches(self):
        th = json.loads((PKG_DIR / "ops" / "PERF_THRESHOLDS.json").read_text())
        pg = self.T["perf_gate"]
        self.assertEqual(pg.evaluate(self._perf(), th, None)["verdict"], "PASS")
        self.assertEqual(pg.evaluate(self._perf(2000), th, None)["verdict"], "FAIL")
        self.assertEqual(pg.evaluate(self._perf(450), th, self._perf(200))["verdict"], "FAIL")   # x2.25 regression
        self.assertEqual(pg.evaluate(self._perf(250), th, self._perf(200))["verdict"], "PASS")

    def test_release_gate_no_go_now_and_falsifier_go_reachable(self):
        import datetime as dt
        rg = self.T["release_gate"]
        lanes = {"tests_normal": {"pass": True}, "tests_optimized": {"pass": True}}
        rtm = {"rows": [{"check_id": "INV-69-C001", "status": "present"}, {"check_id": "INV-69-C030", "status": "partial"}]}
        waivers = {"entries": [{"id": "W-002", "status": "pending_approval", "approver": None, "expires": "2026-10-22",
                                "controls": ["INV-69-C030"]}]}
        owners = {"roles": [{"alias": "inv69-security-owner", "holder": "Sam Security"}]}
        perf = {"verdict": "PASS", "quick": False, "failures": []}
        today = dt.date(2026, 9, 23)
        r = rg.evaluate(lanes, rtm, waivers, {"pass": False, "owners": ["x"], "waivers": [], "reviews": [], "versions": []},
                        perf, None, None, owners, today)
        self.assertEqual(r["verdict"], "NO_GO")
        self.assertEqual(len(r["blockers"]), 4)
        for bad in ({"decision": "APPROVE", "approver": "release-bot"}, {"decision": "APPROVE", "approver": "Sam Security"}):
            waivers["entries"][0].update(status="approved", approver="Ann Owner")
            r = rg.evaluate(lanes, rtm, waivers, {"pass": True}, perf, {"verdict": "PASS"}, bad, owners, today)
            self.assertEqual(r["verdict"], "NO_GO")
        r = rg.evaluate(lanes, rtm, waivers, {"pass": True}, perf, {"verdict": "PASS"},
                        {"decision": "APPROVE", "approver": "Rae Releaser"}, owners, today)
        self.assertEqual((r["verdict"], r["blockers"]), ("GO", []))
        r = rg.evaluate(lanes, rtm, waivers, {"pass": True}, perf, {"verdict": "PASS"},
                        {"decision": "APPROVE", "approver": "Rae Releaser"}, owners, dt.date(2026, 11, 1))
        self.assertEqual(r["verdict"], "NO_GO")   # waiver expired

    def test_capacity_model_binds_on_tightest_limit(self):
        perf = self._perf()
        perf["throughput"]["cpu_s_per_op"] = 300.0
        m = self.T["capacity_model"].model(4, 2048, {"readonly": 0.8, "high_risk": 0.2},
                                           {"readonly": 20, "high_risk": 900}, perf, {"sandbox_heavy_concurrency": 4})
        self.assertEqual(m["derived"]["binding_limit"], "quota:sandbox_heavy")
        self.assertEqual(m["recommendation"]["concurrency.max_active"], 20)


class LeakTest(unittest.TestCase):
    """Global gate: security-sensitive logs/errors/status outputs do not leak secrets or tenant data."""

    def test_no_secret_in_events_status_telemetry_errors(self):
        rt = build()
        c = ctx(tenant="tenant-secret-co")
        rt.start_run("r", principal="alice", allow=ALL, ctx=c)
        payload = {"authorization": SECRET, "body": SECRET, "nested": [{"password": SECRET}]}
        rt.invoke("r", "send_email", payload, c)
        try:
            rt.invoke("r", "delete_records", {"token": SECRET}, c)
        except E.AgentError as e:
            self.assertNotIn(SECRET, json.dumps(e.to_dict()))
        blob = json.dumps([rt.events, rt.status(), rt.telemetry.metrics_snapshot(), rt.telemetry.buffers,
                           rt.runs["r"].agent.export_transcript(), rt.decisions], default=str)
        self.assertNotIn(SECRET, blob)
        self.assertNotIn("tenant-secret-co", json.dumps(rt.status("public")))


if __name__ == "__main__":
    unittest.main()
