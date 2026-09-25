"""INV-72 v4.3.0 control suites.  Class names are referenced from ops/RTM_SOURCE.json - renaming one
breaks tools/rtm.py --check, which is the point."""
import io
import json
import os
import tempfile
import threading
import time
import unittest

from harness import CALLER_KEY, KEY, M, PKG_DIR, Clock, Tokens, build, fleet_dicts, pkg

Device, match, decide = pkg.Device, pkg.match, pkg.decide
AccelError = M["errors"].AccelError


def req(**kw):
    base = {"class": "gpu-large", "mem_gb": 80, "tenant": "t1"}
    base.update(kw)
    return base


# --------------------------------------------------------------------------- C026 / C014
class ErrorRegistryTest(unittest.TestCase):
    def test_every_code_has_an_outcome_class(self):
        for code, c in M["errors"].REGISTRY.items():
            self.assertIn(c.outcome, M["errors"].OUTCOMES)
            self.assertRegex(code, r"^ACCEL_[A-Z_]+$")

    def test_unregistered_code_is_refused(self):
        with self.assertRaises(KeyError):
            AccelError("ACCEL_NOT_A_CODE")

    def test_error_document_validates(self):
        doc = AccelError("ACCEL_DEADLINE_EXCEEDED", budget_ms=5).to_dict()
        self.assertEqual(M["schema_check"].check(doc, "PK_ACCEL_ERROR-1"), [])
        self.assertTrue(doc["retryable"])

    def test_validation_exceptions_carry_codes(self):
        with self.assertRaises(pkg.RequirementValidationError) as cm:
            match({"class": "x"}, [])
        self.assertEqual(cm.exception.code, "ACCEL_INVALID_REQUIREMENT")

    def test_matcher_reason_codes_are_registered(self):
        fleet = [Device(**d) for d in fleet_dicts()]
        for r in (req(mem_gb=120), req(**{"class": "tpu"}), req(count=5), req(count=3, interconnect=True)):
            d = decide(r, fleet)
            self.assertIn(d["code"], M["errors"].REGISTRY)
            for x in d["reasons"]:
                self.assertIn(x["code"], M["errors"].REGISTRY)


# --------------------------------------------------------------------------- C028 / C067
class LimitsTest(unittest.TestCase):
    def test_count_over_max_is_limit_error(self):
        with self.assertRaises(pkg.LimitExceededError):
            match(req(count=M["matcher"].MAX_COUNT + 1), [])

    def test_limit_error_is_still_value_error(self):
        self.assertTrue(issubclass(pkg.LimitExceededError, ValueError))

    def test_inventory_over_max_refused_without_materialising_it_all(self):
        def endless():
            i = 0
            while True:
                yield Device(f"d{i}", "gpu", 1, "n", "l")
                i += 1
        with self.assertRaises(pkg.LimitExceededError):
            match(req(**{"class": "gpu", "mem_gb": 1}), endless())

    def test_identifier_length_bound(self):
        with self.assertRaises(pkg.LimitExceededError):
            match(req(tenant="t" * 129), [])
        with self.assertRaises(pkg.LimitExceededError):
            Device("x" * 129, "gpu", 1, "n", "l")

    def test_absurd_memory_is_malformed(self):
        with self.assertRaises(pkg.RequirementValidationError):
            match(req(mem_gb=1e9), [])

    def test_boundary_values_accepted(self):
        fleet = [Device(f"d{i}", "gpu", 1, "n", "l") for i in range(M["matcher"].MAX_COUNT)]
        sel, _ = match({"class": "gpu", "mem_gb": 1, "tenant": "t", "count": M["matcher"].MAX_COUNT}, fleet, reserve=False)
        self.assertEqual(len(sel), M["matcher"].MAX_COUNT)

    def test_profile_limits_are_stricter_than_code_limits(self):
        svc, _, _ = build("far_edge")
        tok = Tokens()
        with self.assertRaises(AccelError) as cm:
            svc.request(req(count=5), token=tok.caller())
        self.assertEqual(cm.exception.code, "ACCEL_LIMIT_EXCEEDED")


# --------------------------------------------------------------------------- C022 / C029 / C082
class SchemaContractTest(unittest.TestCase):
    def test_all_schemas_load_and_use_supported_keywords(self):
        for name in M["schema_check"].ALL:
            s = M["schema_check"].load(name)
            M["schema_check"].validate({}, s)  # raises SchemaError on unknown keyword

    def test_unknown_keyword_in_schema_is_an_error(self):
        with self.assertRaises(M["schema_check"].SchemaError):
            M["schema_check"].validate(1, {"type": "integer", "multipleOf": 2})

    def test_service_output_validates_against_match_schema(self):
        svc, _, _ = build()
        tok = Tokens()
        for r in (req(count=2, interconnect=True), req(mem_gb=500)):
            doc = svc.request(r, token=tok.caller())
            self.assertEqual(M["schema_check"].check(doc, "PK_ACCEL_MATCH-1"), [], doc)

    def test_status_validates(self):
        svc, _, _ = build()
        self.assertEqual(M["schema_check"].check(svc.status(), "PK_ACCEL_STATUS-1"), [])

    def test_request_schema_rejects_unknown_fields(self):
        self.assertTrue(M["schema_check"].check(req(colour="red"), "PK_ACCEL_REQ-1"))

    def test_bool_is_not_a_number(self):
        self.assertTrue(M["schema_check"].check(req(mem_gb=True), "PK_ACCEL_REQ-1"))


class ConformanceFixturesTest(unittest.TestCase):
    """tests/fixtures/conformance/*.json: versioned golden cases every implementation must reproduce."""

    def test_golden_cases(self):
        d = PKG_DIR / "tests" / "fixtures" / "conformance"
        files = sorted(d.glob("*.json"))
        self.assertGreaterEqual(len(files), 10)
        for f in files:
            case = json.loads(f.read_text())
            self.assertEqual(case["schema"], "PK_ACCEL_CONFORMANCE/1")
            fleet = [Device(**{**x, "tenants": set(x.get("tenants", []))}) for x in case["inventory"]]
            with self.subTest(case=f.name):
                if "raises" in case["expect"]:
                    with self.assertRaises(ValueError) as cm:
                        decide(case["request"], fleet)
                    self.assertEqual(cm.exception.code, case["expect"]["raises"])
                else:
                    out = decide(case["request"], fleet)
                    self.assertEqual(out["selected"], case["expect"]["selected"])
                    self.assertEqual(out["code"], case["expect"]["code"])


# --------------------------------------------------------------------------- C015
class LifecycleTest(unittest.TestCase):
    def test_legal_and_illegal_transitions(self):
        lc = M["lifecycle"]
        lc.check(lc.REQUEST, "received", "validated")
        with self.assertRaises(AccelError):
            lc.check(lc.REQUEST, "released", "reserved")
        with self.assertRaises(AccelError):
            lc.check(lc.REQUEST, "refused", "reserved")

    def test_terminal_states_have_no_exits(self):
        lc = M["lifecycle"]
        for s in lc.REQUEST_TERMINAL:
            self.assertEqual(lc.REQUEST[s], set())

    def test_every_target_is_a_state(self):
        lc = M["lifecycle"]
        for m in (lc.REQUEST, lc.DEVICE):
            for a, b in lc.table(m):
                self.assertIn(b, m)


# --------------------------------------------------------------------------- C012 / C033-C039
class ConfigTest(unittest.TestCase):
    def test_every_tier_profile_validates(self):
        for tier in M["config"].TIERS:
            self.assertEqual(M["config"].validate(M["config"].load_profile(tier)), [], tier)

    def test_invalid_candidate_does_not_replace_active(self):
        cs = M["config"].ConfigStore()
        g1 = cs.activate(M["config"].compose("cloud"), author="a", reason="r")
        bad = M["config"].compose("cloud", {"admission": {"burst": 0}})
        with self.assertRaises(AccelError):
            cs.activate(bad, author="a", reason="r")
        self.assertIs(cs.active, g1)

    def test_secret_in_config_is_refused(self):
        for over in ({"description": "key sk-live-abcdefghijkl"}, {"telemetry": {"api_key": "x"}}):
            with self.subTest(over=over):
                self.assertTrue(M["config"].validate(M["config"].compose("cloud", over)))

    def test_semantic_rule_auth_off_only_far_edge(self):
        self.assertTrue(M["config"].validate(M["config"].compose("cloud", {"require_authentication": False})))

    def test_overlays_apply_without_rebuild(self):
        env = json.loads((PKG_DIR / "config/overlays/example.environment.json").read_text())
        site = json.loads((PKG_DIR / "config/overlays/example.site.json").read_text())
        cfg = M["config"].compose("datacenter", env, site)
        self.assertEqual(cfg["admission"]["rate_per_s"], 500)
        self.assertEqual(cfg["quotas"]["per_tenant"]["tenant-a"], 8)
        self.assertEqual(M["config"].validate(cfg), [])

    def test_provenance_recorded(self):
        cs = M["config"].ConfigStore()
        g = cs.activate(M["config"].compose("cloud"), author="alice", reason="rollout", sources=("profiles/cloud.json",))
        p = g.provenance()
        self.assertEqual((p["author"], p["reason"], p["generation"]), ("alice", "rollout", 1))
        self.assertEqual(len(p["digest"]), 64)
        with self.assertRaises(AccelError):
            cs.activate(M["config"].compose("cloud"), author="", reason="x")

    def test_active_generation_is_immutable(self):
        cs = M["config"].ConfigStore()
        cs.activate(M["config"].compose("cloud"), author="a", reason="r")
        with self.assertRaises(TypeError):
            cs.get()["limits"]["max_count"] = 1000

    def test_operator_and_automatic_rollback(self):
        events = []
        cs = M["config"].ConfigStore(audit=lambda a, d: events.append(a))
        g1 = cs.activate(M["config"].compose("cloud"), author="a", reason="r")
        cs.activate(M["config"].compose("datacenter"), author="a", reason="r")
        g3 = cs.rollback(author="op", reason="bad rollout")
        self.assertEqual(g3.digest, g1.digest)
        with self.assertRaises(AccelError):
            cs.activate(M["config"].compose("near_edge"), author="a", reason="r", probe=lambda c: False)
        self.assertEqual(cs.active.digest, g1.digest)
        self.assertIn("config.rolled_back", events)

    def test_concurrent_readers_see_whole_generations(self):
        cs = M["config"].ConfigStore()
        cs.activate(M["config"].compose("cloud"), author="a", reason="r")
        seen, stop = set(), threading.Event()

        def reader():
            while not stop.is_set():
                c = cs.get()
                seen.add((c["profile"], c["limits"]["max_count"]))
        ts = [threading.Thread(target=reader) for _ in range(4)]
        [t.start() for t in ts]
        for i in range(50):
            cs.activate(M["config"].compose("far_edge" if i % 2 else "cloud"), author="a", reason="flip")
        stop.set()
        [t.join() for t in ts]
        self.assertTrue(seen <= {("cloud", 64), ("far_edge", 4)}, seen)


# --------------------------------------------------------------------------- C019
class PrecedenceTest(unittest.TestCase):
    def test_security_beats_cost(self):
        P = M["precedence"]
        r = P.resolve([P.Claim("cost", "allow", "cheaper"), P.Claim("security", "deny", "isolation")])
        self.assertEqual((r["action"], r["by"]), ("deny", "security"))

    def test_residency_beats_slo(self):
        P = M["precedence"]
        r = P.resolve([P.Claim("slo", "allow", "faster"), P.Claim("residency", "deny", "region")])
        self.assertEqual(r["by"], "residency")

    def test_empty_or_unknown_fails_closed(self):
        P = M["precedence"]
        self.assertEqual(P.resolve([])["action"], "deny")
        self.assertEqual(P.resolve([P.Claim("vibes", "allow", "x")])["action"], "deny")

    def test_far_edge_forces_dedicated_even_when_shared_requested(self):
        svc, _, _ = build("far_edge")
        tok = Tokens()
        doc = svc.request(req(mem_gb=20, isolation="shared", tenant="t1"), token=tok.caller())
        self.assertNotIn("p0", doc["selected"] or [])
        self.assertTrue(any("precedence: security" in r for r in doc["rationale"]))

    def test_residency_restricts_nodes(self):
        svc, _, _ = build()
        doc = svc.request(req(allowed_nodes=["n2"]), token=Tokens().caller())
        self.assertEqual(doc["selected"], ["b0"])


# --------------------------------------------------------------------------- C023 / C024 / C042 / C044 / C048
class TrustTest(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.svc, _, self.kp = build(clock=self.clock)
        self.tok = Tokens(self.clock)

    def code(self, fn):
        with self.assertRaises(AccelError) as cm:
            fn()
        return cm.exception.code

    def test_missing_and_malformed_tokens(self):
        for t in (None, "", "Bearer x", "PK_ACCEL_TOKEN/1:a|b"):
            self.assertEqual(self.code(lambda: self.svc.request(req(), token=t)), "ACCEL_UNAUTHENTICATED")

    def test_forged_signature(self):
        t = M["trust"].mint(b"wrong-key-000000000000000000000000", "sched", ["t1"], ["accel.reserve"], "x", int(self.clock()) + 60)
        self.assertEqual(self.code(lambda: self.svc.request(req(), token=t)), "ACCEL_UNAUTHENTICATED")

    def test_replay_refused(self):
        t = self.tok.caller()
        self.svc.request(req(), token=t)
        self.assertEqual(self.code(lambda: self.svc.request(req(), token=t)), "ACCEL_REPLAY")

    def test_expired_and_overlong_tokens(self):
        old = M["trust"].mint(CALLER_KEY, "sched", ["t1"], ["accel.reserve"], "e1", int(self.clock()) - 100)
        self.assertEqual(self.code(lambda: self.svc.request(req(), token=old)), "ACCEL_UNAUTHENTICATED")
        far = M["trust"].mint(CALLER_KEY, "sched", ["t1"], ["accel.reserve"], "e2", int(self.clock()) + 10_000)
        self.assertEqual(self.code(lambda: self.svc.request(req(), token=far)), "ACCEL_UNAUTHENTICATED")

    def test_tenant_scope_enforced(self):
        t = self.tok.caller(tenants=("t2",))
        self.assertEqual(self.code(lambda: self.svc.request(req(tenant="t1"), token=t)), "ACCEL_FORBIDDEN")

    def test_capability_least_privilege(self):
        t = self.tok.caller(caps=["accel.match"])
        self.assertEqual(self.code(lambda: self.svc.request(req(), token=t)), "ACCEL_FORBIDDEN")
        t2 = self.tok.caller(caps=["accel.match"])
        self.assertIsNotNone(self.svc.request(req(), token=t2, reserve=False))
        t3 = self.tok.caller()
        self.assertEqual(self.code(lambda: self.svc.disable("x", token=t3)), "ACCEL_FORBIDDEN")

    def test_token_cannot_claim_capability_beyond_grant(self):
        t = M["trust"].mint(CALLER_KEY, "sched", ["*"], ["accel.operate"], "g1", int(self.clock()) + 60)
        self.assertEqual(self.code(lambda: self.svc.disable("x", token=t)), "ACCEL_FORBIDDEN")

    def test_key_service_down_fails_closed(self):
        self.kp.available = False
        self.assertEqual(self.code(lambda: self.svc.request(req(), token=self.tok.caller())), "ACCEL_DEPENDENCY_UNAVAILABLE")

    def test_auth_required_but_absent_fails_closed(self):
        svc, _, _ = build(auth=False)
        self.assertEqual(self.code(lambda: svc.request(req())), "ACCEL_DEPENDENCY_UNAVAILABLE")


# --------------------------------------------------------------------------- C044 / C045 / C004 / C018 / C055 / C056
class DiscoveryTest(unittest.TestCase):
    def test_tampered_inventory_refused_and_previous_kept(self):
        clock = Clock()
        svc, pub, _ = build(clock=clock)
        good_gen = svc.inventory.status()["generation"]
        orig = pub.publish

        def tampered():
            s = orig()
            s["devices"][0]["mem_gb"] = 999
            return s
        svc.inventory.sources[0].fetch = tampered
        with self.assertRaises(AccelError):
            svc.inventory.refresh()
        self.assertEqual(svc.inventory.status()["generation"], good_gen)

    def test_unsigned_inventory_refused_when_mac_required(self):
        pub = M["adapters"].Gap02Publisher("s", None, fleet_dicts())
        cache = M["discovery"].InventoryCache([M["discovery"].Source("s", pub.publish, None)])
        with self.assertRaises(AccelError):
            cache.refresh()

    def test_generation_rollback_refused(self):
        clock = Clock()
        svc, pub, _ = build(clock=clock)
        old = pub.publish()
        pub.publish()
        svc.inventory.refresh()
        svc.inventory.sources[0].fetch = lambda: old
        with self.assertRaises(AccelError):
            svc.inventory.refresh()

    def test_offline_grace_then_stale(self):
        clock = Clock()
        svc, _, _ = build("near_edge", clock=clock)
        tok = Tokens(clock)
        clock.t += 900 + 10       # past max_age, inside grace
        doc = svc.request(req(), token=tok.caller())
        self.assertEqual(doc["outcome"], "degraded")
        self.assertIn("inventory-offline-grace", doc["degraded"])
        clock.t += 1800           # past grace
        with self.assertRaises(AccelError) as cm:
            svc.request(req(tenant="t2"), token=tok.caller())
        self.assertEqual(cm.exception.code, "ACCEL_INVENTORY_STALE")
        self.assertFalse(svc.status()["ready"])

    def test_cloud_has_no_offline_grace(self):
        clock = Clock()
        svc, _, _ = build("cloud", clock=clock)
        clock.t += 301
        with self.assertRaises(AccelError) as cm:
            svc.request(req(), token=Tokens(clock).caller())
        self.assertEqual(cm.exception.code, "ACCEL_INVENTORY_STALE")

    def test_failover_to_verified_secondary_only(self):
        pa = M["adapters"].Gap02Publisher("a", KEY, fleet_dicts())
        pb = M["adapters"].Gap02Publisher("b", KEY, fleet_dicts()[:2])
        pc = M["adapters"].Gap02Publisher("c", b"other-key-00000000000000000000000", fleet_dicts())
        down = lambda: (_ for _ in ()).throw(ConnectionError("down"))
        D = M["discovery"]
        cache = D.InventoryCache([D.Source("a", down, KEY), D.Source("c", pc.publish, KEY), D.Source("b", pb.publish, KEY)])
        self.assertEqual(cache.refresh(), "b")   # c's MAC does not verify with the registered key
        self.assertEqual(cache.status()["devices"], 2)


# --------------------------------------------------------------------------- C025 / C053 / C054
class ResilienceTest(unittest.TestCase):
    def test_deadline_bounds(self):
        R = M["resilience"]
        for bad in (0, 60_001, True, 1.5):
            with self.assertRaises(AccelError):
                R.Deadline.after(bad)
        t = [0.0]
        d = R.Deadline.after(10, clock=lambda: t[0])
        d.check()
        t[0] = 0.011
        with self.assertRaises(AccelError):
            d.check()

    def test_cancellation_before_reserve_reserves_nothing(self):
        svc, _, _ = build()
        c = M["resilience"].CancelToken()
        c.cancel()
        with self.assertRaises(AccelError) as cm:
            svc.request(req(), token=Tokens().caller(), cancel=c)
        self.assertEqual(cm.exception.code, "ACCEL_CANCELLED")
        self.assertEqual(svc.store.active(), [])

    def test_admission_sheds_per_tenant_without_starving_others(self):
        t = [0.0]
        a = M["resilience"].Admission(rate_per_s=1, burst=2, max_inflight=100, clock=lambda: t[0])
        for _ in range(2):
            with a.admit("noisy"):
                pass
        with self.assertRaises(AccelError):
            with a.admit("noisy"):
                pass
        with a.admit("quiet"):
            pass
        t[0] = 1.0
        with a.admit("noisy"):
            pass

    def test_inflight_cap(self):
        a = M["resilience"].Admission(rate_per_s=1000, burst=1000, max_inflight=1)
        with a.admit("x"):
            with self.assertRaises(AccelError):
                with a.admit("y"):
                    pass

    def test_admission_tenant_table_is_bounded(self):
        a = M["resilience"].Admission(rate_per_s=1, burst=1, max_inflight=10, max_tenants=5)
        for i in range(50):
            with a.admit(f"t{i}"):
                pass
        self.assertLessEqual(len(a._buckets), 5)

    def test_retry_only_retryable_and_idempotent(self):
        R, calls = M["resilience"], []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise AccelError("ACCEL_CIRCUIT_OPEN")
            return "ok"
        import random
        self.assertEqual(R.retry(flaky, idempotent=True, sleep=lambda s: None, rng=random.Random(1)), "ok")
        calls.clear()
        with self.assertRaises(AccelError):
            R.retry(flaky, idempotent=False, sleep=lambda s: None)
        self.assertEqual(len(calls), 1)

        def terminal():
            calls.append(1)
            raise AccelError("ACCEL_FORBIDDEN")
        calls.clear()
        with self.assertRaises(AccelError):
            R.retry(terminal, idempotent=True, sleep=lambda s: None)
        self.assertEqual(len(calls), 1)

    def test_backoff_is_bounded_and_jittered(self):
        import random
        d = M["resilience"].backoff_delays(5, 0.05, 1.0, random.Random(7))
        self.assertEqual(len(d), 4)
        self.assertTrue(all(0 <= x <= 1.0 for x in d))
        self.assertGreater(len(set(d)), 1)
        with self.assertRaises(ValueError):
            M["resilience"].retry(lambda: 1, idempotent=True, attempts=9)

    def test_retry_respects_deadline(self):
        R = M["resilience"]
        dl = R.Deadline(at=0.0, clock=lambda: 0.0)
        with self.assertRaises(AccelError) as cm:
            R.retry(lambda: (_ for _ in ()).throw(AccelError("ACCEL_OVERLOADED")), idempotent=True, deadline=dl,
                    sleep=lambda s: None)
        self.assertEqual(cm.exception.code, "ACCEL_DEADLINE_EXCEEDED")

    def test_circuit_breaker_cycle(self):
        t = [0.0]
        cb = M["resilience"].CircuitBreaker("gap02", failure_threshold=2, reset_after_s=10, clock=lambda: t[0])
        boom = lambda: (_ for _ in ()).throw(ConnectionError())
        for _ in range(2):
            with self.assertRaises(ConnectionError):
                cb.call(boom)
        with self.assertRaises(AccelError):
            cb.call(lambda: 1)
        t[0] = 11
        self.assertEqual(cb.call(lambda: 1), 1)
        self.assertEqual(cb.state, "closed")

    def test_service_sheds_under_overload(self):
        svc, _, _ = build(devices=[dict(dev_id=f"d{i}", cls="gpu-large", mem_gb=80, node="n", link_group="l")
                                   for i in range(100)])
        cfg = M["config"].compose("cloud", {"admission": {"rate_per_s": 0.001, "burst": 3, "max_inflight": 10}})
        svc.config.activate(cfg, author="t", reason="tight")
        tok, shed = Tokens(), 0
        for i in range(10):
            try:
                svc.request(req(tenant="t1"), token=tok.caller(), reserve=False)
            except AccelError as e:
                self.assertEqual(e.code, "ACCEL_OVERLOADED")
                shed += 1
        self.assertEqual(shed, 7)


# --------------------------------------------------------------------------- C017 / quotas
class QuotaFairnessTest(unittest.TestCase):
    def test_quota_refuses_with_code(self):
        svc, _, _ = build(devices=[dict(dev_id=f"d{i}", cls="gpu-large", mem_gb=80, node="n", link_group="l")
                                   for i in range(10)])
        cfg = M["config"].compose("cloud", {"quotas": {"default_devices_per_tenant": 2, "per_tenant": {"t2": 5}}})
        svc.config.activate(cfg, author="t", reason="quota")
        tok = Tokens()
        self.assertIsNotNone(svc.request(req(count=2), token=tok.caller())["selected"])
        doc = svc.request(req(), token=tok.caller())
        self.assertEqual(doc["code"], "ACCEL_QUOTA_EXCEEDED")
        self.assertIsNotNone(svc.request(req(tenant="t2", count=5), token=tok.caller())["selected"])


# --------------------------------------------------------------------------- C057 / C058 / C059 / C095 / C086
class StateStoreTest(unittest.TestCase):
    def fleet(self):
        return [Device(**d) for d in fleet_dicts()]

    def test_same_tenant_cannot_get_one_whole_device_twice(self):
        # v4.2.0 defect: match(reserve=True) tracked ownership per tenant, so a second job of the same
        # tenant was handed the same whole device.  Reproduce on the old API, then prove the store closes it.
        fleet = self.fleet()
        first, _ = match(req(), fleet)
        second, _ = match(req(), fleet)
        self.assertEqual(first, second)        # the legacy behaviour, kept for compatibility
        s = M["state"].ReservationStore()
        r1, _ = s.reserve(req(), self.fleet())
        r2, _ = s.reserve(req(), self.fleet())
        self.assertNotEqual(r1.devices, r2.devices)

    def test_idempotent_reserve_and_conflicting_reuse(self):
        s = M["state"].ReservationStore()
        a, _ = s.reserve(req(idempotency_key="k1"), self.fleet())
        b, d = s.reserve(req(idempotency_key="k1"), self.fleet())
        self.assertEqual(a.reservation_id, b.reservation_id)
        self.assertTrue(d.get("replayed"))
        with self.assertRaises(AccelError):
            s.reserve(req(idempotency_key="k1", mem_gb=10), self.fleet())

    def test_release_is_idempotent_and_tenant_bound(self):
        s = M["state"].ReservationStore()
        r, _ = s.reserve(req(), self.fleet())
        with self.assertRaises(AccelError):
            s.release(r.reservation_id, tenant="t2")
        s.release(r.reservation_id, tenant="t1")
        s.release(r.reservation_id, tenant="t1")
        with self.assertRaises(AccelError):
            s.release("rsv-nope", tenant="t1")

    def test_stale_fence_refused(self):
        s = M["state"].ReservationStore()
        s.advance_fence(5)
        with self.assertRaises(AccelError) as cm:
            s.reserve(req(), self.fleet(), fence=4)
        self.assertEqual(cm.exception.code, "ACCEL_STALE_FENCE")
        s.reserve(req(), self.fleet(), fence=5)

    def test_quarantine_drain_revoke(self):
        s = M["state"].ReservationStore()
        r, _ = s.reserve(req(), self.fleet())
        dev = r.devices[0]
        s.drain("b0", "firmware")
        r2, d2 = s.reserve(req(tenant="t2"), self.fleet())
        self.assertNotIn("b0", r2.devices)
        revoked = s.revoke_device(dev, "ecc errors")
        self.assertEqual(revoked, [r.reservation_id])
        self.assertEqual(s.reservations[r.reservation_id].state, "revoked")
        d = decide(req(), s.overlay(self.fleet()), excluded=s.excluded())
        self.assertTrue(any(x["code"] == "ACCEL_DEVICE_QUARANTINED" for x in d["reasons"]))
        s.unquarantine(dev)
        self.assertNotIn(dev, s.excluded())

    def test_journal_replay_restores_state(self):
        with tempfile.TemporaryDirectory() as td:
            j = os.path.join(td, "journal.jsonl")
            s = M["state"].ReservationStore(journal_path=j, fsync=True)
            r1, _ = s.reserve(req(idempotency_key="a"), self.fleet())
            r2, _ = s.reserve(req(tenant="t2"), self.fleet())
            s.release(r2.reservation_id, tenant="t2")
            s.quarantine("c0", "thermal")
            s.advance_fence(3)
            t = M["state"].ReservationStore.recover(j)
            self.assertEqual({r.reservation_id for r in t.active()}, {r1.reservation_id})
            self.assertEqual(t.quarantined, {"c0": "thermal"})
            self.assertEqual(t.max_fence, 3)
            self.assertEqual(t.by_idem, s.by_idem)

    def test_snapshot_restore_and_tamper(self):
        s = M["state"].ReservationStore()
        s.reserve(req(), self.fleet())
        snap = s.snapshot()
        t = M["state"].ReservationStore.restore(json.loads(json.dumps(snap)))
        self.assertEqual(t.owners(), s.owners())
        snap["max_fence"] = 99
        with self.assertRaises(AccelError):
            M["state"].ReservationStore.restore(snap)


class ConcurrencyTest(unittest.TestCase):
    def test_no_double_allocation_under_contention(self):
        s = M["state"].ReservationStore()
        fleet = [Device(f"d{i}", "gpu", 80, f"n{i % 4}", "l") for i in range(20)]
        results, errors = [], []
        barrier = threading.Barrier(16)

        def worker(i):
            barrier.wait()
            for j in range(5):
                try:
                    r, _ = s.reserve({"class": "gpu", "mem_gb": 1, "tenant": f"t{i % 5}"}, fleet)
                    if r:
                        results.append(r)
                except Exception as e:  # pragma: no cover - failure path
                    errors.append(e)
        ts = [threading.Thread(target=worker, args=(i,)) for i in range(16)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(errors, [])
        taken = [d for r in results for d in r.devices]
        self.assertEqual(len(taken), 20)
        self.assertEqual(len(set(taken)), 20)

    def test_partition_never_crosses_tenants_under_contention(self):
        s = M["state"].ReservationStore()
        fleet = [Device("p0", "gpu", 80, "n", "l", partition_of="g0")]
        winners = []
        barrier = threading.Barrier(8)

        def w(i):
            barrier.wait()
            r, _ = s.reserve({"class": "gpu", "mem_gb": 1, "tenant": f"t{i}", "isolation": "shared"}, fleet)
            if r:
                winners.append(r.tenant)
        ts = [threading.Thread(target=w, args=(i,)) for i in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(winners), 1)

    def test_idempotency_key_race_yields_one_reservation(self):
        s = M["state"].ReservationStore()
        fleet = [Device(f"d{i}", "gpu", 80, "n", "l") for i in range(8)]
        ids, barrier = set(), threading.Barrier(8)

        def w():
            barrier.wait()
            r, _ = s.reserve({"class": "gpu", "mem_gb": 1, "tenant": "t", "idempotency_key": "same"}, fleet)
            ids.add(r.reservation_id)
        ts = [threading.Thread(target=w) for _ in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(ids), 1)
        self.assertEqual(len(s.active()), 1)

    def test_audit_chain_intact_under_concurrency(self):
        a = M["audit"].AuditLog()
        ts = [threading.Thread(target=lambda: [a.emit("x", "y", "z", "ok") for _ in range(100)]) for _ in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(M["audit"].AuditLog.verify(a.events), [])
        self.assertEqual(len(a.events), 800)


# --------------------------------------------------------------------------- C060 / C089 fault injection
class FaultInjectionTest(unittest.TestCase):
    def test_torn_journal_tail_recovers(self):
        with tempfile.TemporaryDirectory() as td:
            j = os.path.join(td, "j.jsonl")
            s = M["state"].ReservationStore(journal_path=j, fsync=False)
            fleet = [Device(**d) for d in fleet_dicts()]
            r, _ = s.reserve(req(), fleet)
            with open(j, "a") as f:
                f.write('{"seq": 1, "op": "reserve", "da')       # crash mid-write
            t = M["state"].ReservationStore.recover(j)
            self.assertTrue(t.recovery_report["torn_tail"])
            self.assertEqual([x.reservation_id for x in t.active()], [r.reservation_id])
            t.reserve(req(tenant="t2"), fleet)                    # journal usable after truncation
            self.assertEqual(len(M["state"].ReservationStore.recover(j).active()), 2)

    def test_mid_journal_corruption_refused(self):
        with tempfile.TemporaryDirectory() as td:
            j = os.path.join(td, "j.jsonl")
            s = M["state"].ReservationStore(journal_path=j, fsync=False)
            fleet = [Device(**d) for d in fleet_dicts()]
            s.reserve(req(), fleet)
            s.reserve(req(tenant="t2"), fleet)
            lines = open(j).read().splitlines()
            lines[0] = lines[0].replace('"t1"', '"t9"')
            open(j, "w").write("\n".join(lines) + "\n")
            with self.assertRaises(AccelError):
                M["state"].ReservationStore.recover(j)

    def test_discovery_partition_then_reconnect(self):
        clock = Clock()
        svc, pub, _ = build("near_edge", clock=clock)
        src = svc.inventory.sources[0]
        good = src.fetch
        src.fetch = lambda: (_ for _ in ()).throw(ConnectionError("partition"))
        clock.t += 950
        with self.assertRaises(AccelError):
            svc.inventory.refresh()
        self.assertEqual(svc.inventory.status()["state"], "degraded")
        src.fetch = good
        svc.inventory.refresh()
        self.assertEqual(svc.inventory.status()["state"], "fresh")

    def test_telemetry_sink_failure_does_not_fail_decisions(self):
        class Broken(io.StringIO):
            def write(self, s):
                raise OSError("disk full")
        svc, _, _ = build()
        svc.logger.stream = Broken()
        doc = svc.request(req(), token=Tokens().caller())
        self.assertIsNotNone(doc["selected"])
        self.assertGreater(svc.logger.failures, 0)
        self.assertEqual(svc.status()["dependencies"]["telemetry_log_failures"], svc.logger.failures)

    def test_controller_failover_fences_old_leader(self):
        svc_a, _, _ = build()
        svc_b = M["service"].AcceleratorService(svc_a.config, svc_a.inventory, svc_a.store, svc_a.auth,
                                                logger=svc_a.logger)
        tok = Tokens()
        svc_b.take_leadership(1)
        with self.assertRaises(AccelError) as cm:
            svc_a.request(req(), token=tok.caller())
        self.assertEqual(cm.exception.code, "ACCEL_STALE_FENCE")
        self.assertIsNotNone(svc_b.request(req(), token=tok.caller())["selected"])

    def test_restart_from_journal_preserves_isolation(self):
        with tempfile.TemporaryDirectory() as td:
            j = os.path.join(td, "j.jsonl")
            svc, _, _ = build(journal=j)
            tok = Tokens()
            svc.request(req(mem_gb=10, isolation="shared", allowed_nodes=["n4"]), token=tok.caller())
            store2 = M["state"].ReservationStore.recover(j)
            d = decide(req(tenant="t2", mem_gb=10, isolation="shared"), store2.overlay([Device(**fleet_dicts()[4])]))
            self.assertIsNone(d["selected"])
            self.assertEqual(d["code"], "ACCEL_INSUFFICIENT_COUNT")
            self.assertEqual(d["reasons"][0]["code"], "ACCEL_PARTITION_FOREIGN_TENANT")


# --------------------------------------------------------------------------- C049
class AuditTest(unittest.TestCase):
    def test_edit_delete_reorder_detected(self):
        a = M["audit"].AuditLog(key=b"k" * 32)
        for i in range(5):
            a.emit("op", "act", f"s{i}", "ok")
        ev = [dict(e) for e in a.events]
        V = M["audit"].AuditLog.verify
        self.assertEqual(V(ev, key=b"k" * 32), [])
        edited = [dict(e) for e in ev]
        edited[2]["outcome"] = "denied"
        self.assertTrue(V(edited, key=b"k" * 32))
        self.assertTrue(V(ev[:2] + ev[3:], key=b"k" * 32))
        self.assertTrue(V([ev[1], ev[0]] + ev[2:], key=b"k" * 32))
        self.assertTrue(V(ev, key=b"x" * 32))

    def test_tail_truncation_needs_external_head(self):
        a = M["audit"].AuditLog()
        for i in range(4):
            a.emit("op", "act", "s", "ok")
        head = a.head()
        self.assertEqual(M["audit"].AuditLog.verify(a.events[:3]), [])          # chain alone cannot see it
        self.assertTrue(M["audit"].AuditLog.verify(a.events[:3], expect_head=head))

    def test_export_keeps_chain_continuous(self):
        a = M["audit"].AuditLog()
        a.emit("o", "a", "s", "ok")
        first = a.export()
        a.emit("o", "a", "s", "ok")
        self.assertEqual(M["audit"].AuditLog.verify(first + a.events), [])

    def test_overflow_refused_before_append(self):
        a = M["audit"].AuditLog(max_events=2)
        a.emit("o", "a", "s", "ok")
        a.emit("o", "a", "s", "ok")
        with self.assertRaises(OverflowError):
            a.emit("o", "a", "s", "ok")
        self.assertEqual(len(a.events), 2)

    def test_service_actions_are_audited_and_schema_valid(self):
        svc, _, _ = build()
        tok = Tokens()
        d = svc.request(req(), token=tok.caller())
        svc.release(d["reservation_id"], tenant="t1", token=tok.caller())
        svc.quarantine("c0", "thermal", token=tok.operator())
        with self.assertRaises(AccelError):
            svc.request(req(tenant="t9"), token=tok.caller())
        actions = [e["action"] for e in svc.audit.events]
        self.assertEqual(actions, ["accel.reserve", "accel.release", "accel.quarantine", "accel.request"])
        for e in svc.audit.events:
            self.assertEqual(M["schema_check"].check(e, "PK_ACCEL_AUDIT_EVENT-1"), [])

    def test_secrets_redacted_in_audit(self):
        a = M["audit"].AuditLog()
        e = a.emit("o", "a", "s", "ok", {"token": "abc", "note": "Bearer abcdefghijklmnop"})
        self.assertEqual(e["detail"]["token"], "[REDACTED]")
        self.assertNotIn("abcdefghijklmnop", json.dumps(e))


# --------------------------------------------------------------------------- C059 / C092 operator controls
class OperatorControlTest(unittest.TestCase):
    def test_emergency_disable_and_enable(self):
        svc, _, _ = build()
        tok = Tokens()
        svc.disable("incident 42", token=tok.operator())
        with self.assertRaises(AccelError) as cm:
            svc.request(req(), token=tok.caller())
        self.assertEqual(cm.exception.code, "ACCEL_DISABLED")
        self.assertFalse(svc.status()["ready"])
        svc.enable(token=tok.operator())
        self.assertIsNotNone(svc.request(req(), token=tok.caller())["selected"])

    def test_quarantine_with_revoke_via_service(self):
        svc, _, _ = build()
        tok = Tokens()
        d = svc.request(req(), token=tok.caller())
        out = svc.quarantine(d["selected"][0], "xid 79", token=tok.operator(), revoke=True)
        self.assertEqual(out, [d["reservation_id"]])


# --------------------------------------------------------------------------- C052 / C071
class HealthTest(unittest.TestCase):
    def test_ready_and_reasons(self):
        svc, _, _ = build()
        st = svc.status()
        self.assertTrue(st["ready"] and st["live"])
        self.assertEqual(st["version"], pkg.__version__)
        self.assertIn("fencing", st["capabilities"])

    def test_stall_detection(self):
        clock = Clock()
        svc, _, _ = build(clock=clock, stall_after_s=5)
        svc._adm()._inflight = 1          # a request that never finishes
        svc.last_progress = clock.t
        clock.t += 6
        st = svc.status()
        self.assertTrue(st["stalled"])
        self.assertFalse(st["live"])


# --------------------------------------------------------------------------- C072-C075, C079
class TelemetryTest(unittest.TestCase):
    def test_metrics_emitted_for_rate_errors_latency_saturation(self):
        svc, _, _ = build()
        tok = Tokens()
        svc.request(req(), token=tok.caller())
        svc.request(req(mem_gb=999), token=tok.caller())
        with self.assertRaises(AccelError):
            svc.request(req(), token="bad")
        text = svc.metrics.render()
        for name in ("accel_matched_total", "accel_refused_total", "accel_errors_total", "accel_decision_latency_ms_bucket",
                     "accel_inflight", "accel_active_reservations", "accel_inventory_age_seconds"):
            self.assertIn(name, text)
        self.assertIsNotNone(svc.metrics.quantile("accel_decision_latency_ms", 0.99))

    def test_series_cardinality_bounded(self):
        m = M["telemetry"].Metrics(max_series=30)
        for i in range(500):
            m.inc("accel_refused_total", reason=f"r{i}")
        self.assertLessEqual(len(m.counters) + len(m.gauges) + len(m.hists), 30)
        self.assertGreater(m.dropped_series, 0)

    def test_tenant_labels_pseudonymised(self):
        m = M["telemetry"].Metrics()
        m.inc("accel_matched_total", tenant="acme-secret-project")
        self.assertNotIn("acme-secret-project", m.render())

    def test_structured_log_has_stable_keys_and_no_secrets(self):
        buf = io.StringIO()
        lg = M["telemetry"].Logger(stream=buf, node="n1")
        tr = M["telemetry"].TraceContext.new()
        lg.log("info", "request", "ok", tenant="t1", workload="w", decision_id="d", trace=tr, code=None,
               authorization="Bearer abcdefghijklmnopq")
        rec = json.loads(buf.getvalue())
        for k in ("ts", "level", "component", "node", "tenant", "workload", "operation", "decision_id", "trace_id",
                  "span_id", "code", "msg"):
            self.assertIn(k, rec)
        self.assertNotIn("abcdefghijklmnopq", buf.getvalue())
        self.assertNotEqual(rec["tenant"], "t1")

    def test_traceparent_propagation_and_hostile_headers(self):
        T = M["telemetry"].TraceContext
        tid = "4bf92f3577b34da6a3ce929d0e0e4736"
        c = T.parse(f"00-{tid}-00f067aa0ba902b7-01")
        self.assertEqual(c.trace_id, tid)
        for bad in (None, "", "garbage", "00-" + "0" * 32 + "-00f067aa0ba902b7-01", "x" * 10_000, 5):
            self.assertRegex(T.parse(bad).trace_id, r"^[0-9a-f]{32}$")
        svc, _, _ = build()
        doc = svc.request(req(), token=Tokens().caller(), traceparent=f"00-{tid}-00f067aa0ba902b7-01")
        self.assertEqual(doc["trace_id"], tid)

    def test_telemetry_policy_file_is_complete(self):
        pol = json.loads((PKG_DIR / "ops" / "TELEMETRY_POLICY.json").read_text())
        for k in ("retention", "sampling", "privacy", "export"):
            self.assertIn(k, pol)


# --------------------------------------------------------------------------- C076-C078
class ExplainTest(unittest.TestCase):
    def test_explain_links_inputs_policy_inventory_config_lineage(self):
        svc, _, _ = build()
        svc.lineage.release_manifest_sha256 = "ab" * 32
        svc.lineage.workload_release = "trainer@1.2.3"
        tok = Tokens()
        d = svc.request(req(count=2, interconnect=True), token=tok.caller())
        text = svc.explain(d["decision_id"], token=tok.operator())
        for needle in ("rationale", "inventory        : generation=1", "configuration    : generation=1",
                       "ACCEL_PARTITION_DEDICATED", "trainer@1.2.3", d["trace_id"]):
            self.assertIn(needle, text)

    def test_success_has_rationale(self):
        d = decide(req(), [Device(**x) for x in fleet_dicts()])
        self.assertTrue(d["rationale"])

    def test_explain_requires_read_capability(self):
        svc, _, _ = build()
        tok = Tokens()
        d = svc.request(req(), token=tok.caller(caps=["accel.reserve"]))
        with self.assertRaises(AccelError):
            svc.explain(d["decision_id"], token=tok.caller(caps=["accel.reserve"]))

    def test_decision_ring_is_bounded(self):
        svc, _, _ = build(decisions_kept=3,
                          devices=[dict(dev_id=f"d{i}", cls="gpu-large", mem_gb=80, node="n", link_group="l") for i in range(10)])
        tok = Tokens()
        for _ in range(6):
            svc.request(req(), token=tok.caller(), reserve=False)
        self.assertEqual(len(svc._decisions), 3)


# --------------------------------------------------------------------------- C016 / C027
class CompatibilityTest(unittest.TestCase):
    def test_negotiation(self):
        C = M["compat"]
        self.assertEqual(C.negotiate({"PK_ACCEL_REQ": [1, 2]}), {"PK_ACCEL_REQ": 1})
        with self.assertRaises(AccelError):
            C.negotiate({"PK_ACCEL_REQ": [2]})

    def test_newer_minor_peer_optional_fields_ignored_security_fields_not(self):
        C = M["compat"]
        out = C.accept_request(req(hints={"x": 1}, labels=["a"]))
        self.assertNotIn("hints", out)
        svc, _, _ = build()
        with self.assertRaises(AccelError):
            svc.request(req(unknown_security_field=1), token=Tokens().caller())
        with self.assertRaises(AccelError):
            svc.request(req(schema="PK_ACCEL_REQ/2"), token=Tokens().caller())

    def test_peer_window(self):
        C = M["compat"]
        self.assertTrue(C.peer_supported("4.2.0"))
        self.assertTrue(C.peer_supported("4.4.9"))
        self.assertFalse(C.peer_supported("3.9.0"))
        self.assertFalse(C.peer_supported("5.0.0"))

    def test_v42_api_still_works(self):
        fleet = [Device(**d) for d in fleet_dicts()]
        sel, reasons = match(req(count=2, interconnect=True, isolation="dedicated"), fleet)
        self.assertEqual(sel, ["a0", "a1"])
        self.assertIsInstance(reasons[0], str)

    def test_component_version_synced(self):
        self.assertEqual(M["compat"].COMPONENT_VERSION, pkg.__version__)


# --------------------------------------------------------------------------- C030 / C083
class IntegrationAdaptersTest(unittest.TestCase):
    def test_gap11_scheduler_lifecycle(self):
        svc, _, _ = build()
        tok = Tokens()
        s = M["adapters"].Gap11Scheduler(svc, tok.caller)
        s.submit("j1", req(count=2, interconnect=True))
        s.submit("j2", req(mem_gb=500))
        s.submit("j3", req(tenant="t2"))
        s.tick()
        self.assertIn("j1", s.running)
        self.assertEqual(s.final["j2"], "ACCEL_INSUFFICIENT_MEMORY")
        s.complete("j1")
        self.assertEqual(s.final["j1"], "completed")

    def test_gap11_requeues_retryable_only(self):
        svc, _, _ = build()
        tok = Tokens()
        svc.disable("x", token=tok.operator())
        s = M["adapters"].Gap11Scheduler(svc, tok.caller)
        s.submit("j", req())
        s.tick()
        self.assertEqual(s.final["j"], "ACCEL_DISABLED")     # terminal: not requeued

    def test_inv68_packing_constrains_nodes(self):
        svc, _, _ = build()
        pk = M["adapters"].Inv68Packing({"n1": {"cpu": 2, "ram_gb": 8}, "n2": {"cpu": 64, "ram_gb": 512}})
        doc = svc.request(pk.constrain(req(), cpu=32, ram_gb=256), token=Tokens().caller())
        self.assertEqual(doc["selected"], ["b0"])

    def test_inv69_agent_tool_calls_are_idempotent(self):
        svc, _, _ = build()
        tok = Tokens()
        ag = M["adapters"].Inv69AgentLayer(svc, tok.caller)
        a = ag.tool_call("run-1", 3, "t1", "gpu-large", 80)
        b = ag.tool_call("run-1", 3, "t1", "gpu-large", 80)
        self.assertEqual(a["reservation_id"], b["reservation_id"])
        self.assertEqual(len(svc.store.active()), 1)


# --------------------------------------------------------------------------- C069
class CapacityTest(unittest.TestCase):
    def test_model_levels(self):
        C = M["capacity"]
        fleet = [Device(**d) for d in fleet_dicts()]
        m = C.model(offered_per_s=100, base_us=50, per_device_us=1, inventory=5, devices=fleet,
                    reserved_ids={"a0", "a1", "b0", "c0", "p0"})
        self.assertEqual(m["fleet"]["gpu-large"]["level"], "critical")
        self.assertEqual(m["decision_level"], "ok")


# --------------------------------------------------------------------------- C050 / C087 adversarial
class AdversarialTest(unittest.TestCase):
    """Derived from ops/THREAT_MODEL.md; each test names its threat id."""

    def test_T1_tenant_escalation_via_isolation_value(self):
        for iso in ("Shared", "shared ", "SHARED", "any", "", None, 1):
            with self.assertRaises(ValueError):
                match(req(isolation=iso), [Device("p0", "gpu-large", 80, "n", "l", partition_of="g")])

    def test_T2_injection_in_identifiers_is_inert(self):
        evil = "t1\n{\"level\":\"error\"}"
        buf = io.StringIO()
        lg = M["telemetry"].Logger(stream=buf)
        lg.log("info", "op", evil, tenant=evil)
        self.assertEqual(len(buf.getvalue().strip().splitlines()), 1)
        self.assertTrue(M["schema_check"].check(req(tenant="a b;rm -rf"), "PK_ACCEL_REQ-1"))

    def test_T3_replay_of_reservation_token(self):
        svc, _, _ = build()
        t = Tokens().caller()
        svc.request(req(), token=t)
        with self.assertRaises(AccelError):
            svc.request(req(tenant="t2"), token=t)

    def test_T4_spoofed_discovery_source(self):
        D = M["discovery"]
        pub = M["adapters"].Gap02Publisher("gap02-a", b"attacker-key-000000000000000000000", fleet_dicts())
        cache = D.InventoryCache([D.Source("gap02-a", pub.publish, KEY)])
        with self.assertRaises(AccelError):
            cache.refresh()

    def test_T5_escape_other_tenants_release(self):
        svc, _, _ = build()
        tok = Tokens()
        d = svc.request(req(), token=tok.caller(tenants=("t1",)))
        with self.assertRaises(AccelError):
            svc.release(d["reservation_id"], tenant="t1", token=tok.caller(tenants=("t2",)))

    def test_T6_advertised_label_not_trusted(self):
        # a caller cannot inject its own inventory through the service API
        svc, _, _ = build()
        with self.assertRaises(AccelError):
            svc.request(req(devices=[{"dev_id": "fake"}]), token=Tokens().caller())

    def test_T7_resource_exhaustion_bounded(self):
        a = M["audit"].AuditLog(max_events=10)
        for _ in range(10):
            a.emit("x", "y", "z", "ok")
        with self.assertRaises(OverflowError):
            a.emit("x", "y", "z", "ok")
        auth = M["trust"].Authenticator(M["trust"].StaticKeyProvider({"p": b"k" * 32}, {"p": {"accel.match"}}),
                                        max_nonces=3)
        for i in range(3):
            auth.authenticate(M["trust"].mint(b"k" * 32, "p", ["t"], ["accel.match"], f"x{i}", int(time.time()) + 60))
        with self.assertRaises(AccelError):
            auth.authenticate(M["trust"].mint(b"k" * 32, "p", ["t"], ["accel.match"], "x9", int(time.time()) + 60))

    def test_T8_mutated_device_after_construction_rejected(self):
        d = Device("a", "gpu", 1, "n", "l")
        d.mem_gb = float("nan")
        with self.assertRaises(pkg.InventoryValidationError):
            match({"class": "gpu", "mem_gb": 0, "tenant": "t"}, [d])


if __name__ == "__main__":
    unittest.main()
