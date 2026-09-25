"""P1 semantics: negotiation (16), capabilities (17), versions (18), feature subsets (19), lifecycle (20),
negative ageing (21), recert scheduler (22), policy precedence (23), offline cache (24), partitions (25)."""
import os
import random
import time
import unittest

from fixtures import ENV, PART, PART2, T0, World, art
from gap15_runtime_compatibility_certification.production import (capability as cap, features, negotiation, offline,
                                                                   partition, policy, scheduler, versions)
from gap15_runtime_compatibility_certification.production.service import ServiceError
from gap15_runtime_compatibility_certification.production.state import CertKey


def profile(**over):
    base = dict(arch="aarch64", name="wasmtime", version="21.0.0", wasi="preview2", cm="0.2")
    base.update(over)
    caps = [cap.capability("cpu.arch", base["arch"], layer="hardware", provenance="measured"),
            cap.capability("runtime.name", base["name"], layer="runtime", provenance="attested"),
            cap.capability("runtime.version", base["version"], layer="runtime", provenance="attested"),
            cap.capability("wasi.preview", base["wasi"], layer="runtime", provenance="attested"),
            cap.capability("component_model", base["cm"], layer="runtime", provenance="attested"),
            cap.capability("wit.interface", "wasi:http/outgoing-handler@0.2.0", layer="runtime", provenance="attested"),
            cap.capability("threads", "none", layer="runtime", provenance="discovered")]
    return cap.RuntimeProfile(caps)


class NegotiationTest(unittest.TestCase):
    def req(self, **kw):
        c = [negotiation.Constraint("wasi.preview", "mandatory", ("preview2",)),
             negotiation.Constraint("runtime.version", "mandatory", version_range=">=21.0.0 <22.0.0"),
             negotiation.Constraint("threads", "forbidden", ("shared-memory",))]
        return negotiation.Requirements(c, ["wasi:http/outgoing-handler@0.2.0"], **kw)

    def test_fit_transcript_and_determinism(self):
        """controls: 16-01 16-03 16-05 16-06"""
        r1 = negotiation.negotiate(self.req(), profile())
        r2 = negotiation.negotiate(self.req(), profile())
        self.assertTrue(r1.fits)
        self.assertEqual(r1.as_dict(), r2.as_dict())
        self.assertEqual(r1.engine_version, negotiation.ENGINE_VERSION)
        self.assertTrue(all({"step", "rule", "outcome"} <= set(t) for t in r1.transcript))

    def test_rejections_version_gap_missing_interface_forbidden(self):
        """controls: 16-03 16-09 18-02"""
        self.assertFalse(negotiation.negotiate(self.req(), profile(version="22.0.0")).fits)
        self.assertFalse(negotiation.negotiate(self.req(), profile(wasi="preview1")).fits)
        r = negotiation.Requirements(self.req().constraints, ["wasi:keyvalue/store@0.2.0"])
        self.assertFalse(negotiation.negotiate(r, profile()).fits)

    def test_aliases_normalised_ambiguous_rejected(self):
        """controls: 16-02 17-06"""
        self.assertEqual(cap.normalize("wasi.preview", "wasip2"), "preview2")
        self.assertEqual(cap.normalize("cpu.arch", "amd64"), "x86_64")
        with self.assertRaises(cap.CapabilityError):
            cap.normalize("cpu.arch", "ARM64 ")
        with self.assertRaises(cap.CapabilityError):
            cap.normalize("wasi.preview", "preview9")

    def test_shims_only_explicit_and_trusted(self):
        """controls: 16-04"""
        req = negotiation.Requirements([negotiation.Constraint("wasi.preview", "mandatory", ("preview2",))])
        p1 = profile(wasi="preview1")
        shim = negotiation.Adapter("p1-to-p2", "1.0.0", ("wasi.preview", "preview1"), ("wasi.preview", "preview2"), trusted=False)
        self.assertFalse(negotiation.negotiate(req, p1, adapters=(shim,)).fits)
        trusted = negotiation.Adapter("p1-to-p2", "1.0.0", ("wasi.preview", "preview1"), ("wasi.preview", "preview2"), trusted=True)
        r = negotiation.negotiate(req, p1, adapters=(trusted,))
        self.assertTrue(r.fits)
        self.assertEqual(r.adapters_used[0]["name"], "p1-to-p2")

    def test_precedence_revocation_lifecycle_policy(self):
        """controls: 16-07"""
        r = negotiation.negotiate(self.req(), profile(), revoked_runtimes=frozenset({"wasmtime@21.0.0"}),
                                  eol_runtimes=frozenset({"wasmtime@21.0.0"}))
        self.assertFalse(r.fits)
        self.assertEqual(r.rejected[0]["reason"], "REVOKED")

    def test_experimental_needs_opt_in(self):
        """controls: 16-08 18-04"""
        req = negotiation.Requirements([negotiation.Constraint("wasi.preview", "mandatory", ("preview3",))])
        p = profile(wasi="preview3")
        self.assertFalse(negotiation.negotiate(req, p).fits)
        req.allow_experimental = True
        self.assertTrue(negotiation.negotiate(req, p).fits)

    def test_cardinality_bound_and_benchmark(self):
        """controls: 16-10 39-05"""
        big = negotiation.Requirements([negotiation.Constraint("threads", "optional", ("none",))] * 300)
        with self.assertRaises(negotiation.NegotiationError):
            negotiation.negotiate(big, profile())
        ok = negotiation.Requirements([negotiation.Constraint("threads", "optional", ("none",))] * 256)
        t0 = time.perf_counter()
        negotiation.negotiate(ok, profile())
        self.assertLess(time.perf_counter() - t0, 1.0)


class CapabilityTest(unittest.TestCase):
    def test_typed_layers_provenance_and_identity(self):
        """controls: 17-01 17-02 17-04 17-07"""
        p = profile()
        self.assertEqual(p.get("cpu.arch", min_provenance="measured"), "aarch64")
        self.assertEqual(p.get("threads", min_provenance="attested"), cap.UNKNOWN)
        claimed = cap.RuntimeProfile(p.capabilities + [cap.capability("x-acme.fastpath", "on", layer="operator", provenance="claimed")])
        self.assertEqual(p.identity(), claimed.identity())  # claimed facts never mint a new profile

    def test_unknown_core_values_and_extensions(self):
        """controls: 17-03 17-10"""
        with self.assertRaises(cap.CapabilityError):
            cap.capability("cpu.arch", "vax", layer="hardware", provenance="measured")
        with self.assertRaises(cap.CapabilityError):
            cap.capability("cpu.speed", "fast", layer="hardware", provenance="measured")
        ext = cap.capability("x-acme.accel", "v2", layer="runtime", provenance="claimed")
        p = cap.RuntimeProfile([ext])
        self.assertEqual(p.trusted_extensions(set()), [])
        self.assertEqual(p.trusted_extensions({"x-acme.accel"}), [ext])
        with self.assertRaises(cap.CapabilityError):
            cap.RuntimeProfile([cap.capability("cpu.arch", "x86_64", layer="hardware", provenance="measured"),
                                cap.capability("cpu.arch", "aarch64", layer="hardware", provenance="measured")])

    def test_parameterised_capabilities_and_unknown_state(self):
        """controls: 17-05 17-08 17-09"""
        c = cap.capability("threads", "wasi-threads", layer="runtime", provenance="attested", max_threads=64)
        self.assertEqual(dict(c.params), {"max_threads": 64})
        p = cap.RuntimeProfile([c])
        self.assertEqual(p.get("accelerator"), cap.UNKNOWN)
        migrated = p.migrate_missing(["accelerator"])
        self.assertEqual(migrated.get("accelerator"), cap.UNKNOWN)
        req = negotiation.Requirements([negotiation.Constraint("accelerator", "forbidden", ("gpu",))])
        self.assertFalse(negotiation.negotiate(req, migrated).fits)  # unknown never proves absence


class VersionTest(unittest.TestCase):
    def test_namespaces_and_semver_rules(self):
        """controls: 18-01 18-02 18-03"""
        v = versions.parse_version
        self.assertLess(v("semver", "1.0.0-rc.1"), v("semver", "1.0.0"))
        self.assertEqual(v("semver", "1.0.0+build.5"), v("semver", "1.0.0"))
        self.assertLess(v("spec", "preview1"), v("spec", "preview2"))
        self.assertLess(v("date", "2026-01-01"), v("date", "2026-09-22"))
        with self.assertRaises(versions.VersionError):
            v("semver", "1.0")
        with self.assertRaises(versions.VersionError):
            v("semver", "01.0.0")
        with self.assertRaises(versions.VersionError):
            v("semver", "1.0.0") < v("spec", "p2")

    def test_no_implicit_widening_and_exclusions(self):
        """controls: 18-04 18-05"""
        for expr in ("^1.2.0", "~1.2.0", "1.x", "*", ">=1.0.0"):
            with self.assertRaises(versions.VersionError):
                versions.parse_range("semver", expr)
        r = versions.parse_range("semver", ">=1.0.0 <2.0.0", exclusions=("1.4.2",))
        self.assertTrue(r.matches(versions.parse_version("semver", "1.4.1")))
        self.assertFalse(r.matches(versions.parse_version("semver", "1.4.2")))
        self.assertFalse(r.matches(versions.parse_version("semver", "1.5.0-beta")))

    def test_ruleset_revision_in_verdicts_and_canonical_ranges(self):
        """controls: 18-06 18-07"""
        a = versions.parse_range("semver", ">=1.0.0 <2.0.0 || =3.0.0")
        b = versions.parse_range("semver", "=3.0.0 || >=1.0.0 <2.0.0")
        self.assertEqual(a.canonical(), b.canonical())
        self.assertTrue(versions.RULESET_REVISION)

    def test_unsatisfiable_explained(self):
        """controls: 18-08"""
        with self.assertRaises(versions.VersionError) as cm:
            versions.parse_range("semver", ">=2.0.0 <1.0.0")
        self.assertEqual(cm.exception.code, "E_RANGE_UNSATISFIABLE")
        a = versions.parse_range("semver", ">=1.0.0 <1.5.0")
        b = versions.parse_range("semver", ">=2.0.0 <3.0.0")
        self.assertIsNone(versions.intersect(a, b))

    def test_property_based_interval_boundaries(self):
        """controls: 18-09"""
        rnd = random.Random(1818)
        for _ in range(500):
            lo = (rnd.randint(0, 5), rnd.randint(0, 5), rnd.randint(0, 5))
            hi = (lo[0] + rnd.randint(0, 3), rnd.randint(0, 5), rnd.randint(0, 5))
            if hi <= lo:
                continue
            los, his = ".".join(map(str, lo)), ".".join(map(str, hi))
            r = versions.parse_range("semver", f">={los} <{his}")
            cand = (rnd.randint(0, 9), rnd.randint(0, 5), rnd.randint(0, 5))
            want = lo <= cand < hi
            self.assertEqual(r.matches(versions.parse_version("semver", ".".join(map(str, cand)))), want)
            x = versions.intersect(r, r)
            self.assertEqual(x.canonical(), r.canonical())

    def test_rule_change_regression_report(self):
        """controls: 18-10 23-09"""
        old = policy.PolicySet("p:1", [])
        new = policy.PolicySet("p:2", [policy.PolicyRule("deny-21", "security", "deny", (("runtime", "wasmtime@21.0.0"),))])
        ctxs = [{"runtime": "wasmtime@21.0.0"}, {"runtime": "wasmtime@22.0.0"}]
        rep = policy.simulate(old, new, ctxs, T0)
        self.assertEqual(len(rep["changed"]), 1)
        self.assertEqual(rep["changed"][0]["to"], "deny")


class FeatureSubsetTest(unittest.TestCase):
    def setUp(self):
        self.g = features.FeatureGraph(prerequisites={"wasi:http/outgoing": {"wasi:io/streams"}},
                                       conflicts={"wasi:threads": {"wasi:single-thread"}})

    def test_child_pass_never_implies_parent(self):
        """controls: 19-01 19-02 19-03"""
        st = features.aggregate([features.FeatureEvidence("wasi:http/outgoing", "passed", "e1", T0)], now=T0, ttl_s=500)
        d = features.subset_decision({"wasi:http/outgoing"}, self.g, st)
        self.assertFalse(d["compatible"])
        self.assertEqual(d["blocked"], ["wasi:io/streams"])
        self.assertEqual(d["coverage"], "feature-subset")

    def test_aggregation_conflicts_and_provenance(self):
        """controls: 19-04 19-05 19-06"""
        recs = [features.FeatureEvidence("f", "passed", "e1", T0, 1), features.FeatureEvidence("f", "failed", "e2", T0 + 1, 1)]
        st = features.aggregate(recs, now=T0 + 2, ttl_s=500)
        self.assertEqual(st["f"]["status"], "failed")
        self.assertEqual(st["f"]["evidence"], ["e1", "e2"])
        recs.append(features.FeatureEvidence("f", "passed", "e3", T0 + 5, 3))
        self.assertEqual(features.aggregate(recs, now=T0 + 6, ttl_s=500)["f"]["status"], "conflict")
        st = features.aggregate(recs, now=T0 + 6, ttl_s=500, revoked_evidence=frozenset({"e1", "e2", "e3"}))
        self.assertEqual(st["f"]["status"], "revoked")

    def test_admission_requires_complete_feature_set_and_cache_key(self):
        """controls: 19-07 19-08 19-09 19-10"""
        w = World()
        r = w.svc.ingest(w.producer(), w.evidence(features=[{"feature": "wasi:io/streams", "result": "passed"},
                                                            {"feature": "wasi:http/outgoing", "result": "passed"}]))
        k = w.key_for(r)
        d = w.svc.certify(w.reader(), k, required_features={"wasi:io/streams"})
        self.assertTrue(d["deployable"])
        d2 = w.svc.certify(w.reader(), k, required_features={"wasi:io/streams", "wasi:sockets/tcp"})
        self.assertFalse(d2["deployable"])
        self.assertEqual(d2["reason_code"], "R_FEATURES_UNCERTIFIED")
        self.assertNotEqual(d["feature_subset"]["required_set_digest"], d2["feature_subset"]["required_set_digest"])


class LifecycleTest(unittest.TestCase):
    def setUp(self):
        self.w = World()
        r = self.w.svc.ingest(self.w.producer(), self.w.evidence())
        self.k = self.w.key_for(r)

    def lc(self, state, **kw):
        args = dict(partition=PART, runtime="wasmtime@21.0.0", state=state, effective_at=kw.pop("effective_at", T0),
                    reason="vendor EOL", source="advisory-1", replacement="wasmtime@22.0.0")
        args.update(kw)
        return self.w.svc.lifecycle(self.w.operator(), **args)

    def test_transition_graph_and_metadata(self):
        """controls: 20-01 20-02 20-03"""
        self.lc("deprecated")
        with self.assertRaises(ServiceError):
            self.lc("active")  # regression without waiver is illegal
        ev = [e for e in self.w.store.events() if e["event_type"] == "lifecycle"][0]
        for f in ("effective_at", "announced_at", "reason", "source", "approver", "replacement", "policy_revision"):
            self.assertIn(f, ev)

    def test_existing_vs_new_admissions(self):
        """controls: 20-04"""
        self.lc("blocked-for-new")
        self.assertEqual(self.w.svc.certify(self.w.reader(), self.k, new_admission=True)["reason_code"], "R_BLOCKED_FOR_NEW")
        self.assertEqual(self.w.svc.certify(self.w.reader(), self.k, new_admission=False)["verdict"], "certified")

    def test_reactivation_needs_waiver_and_two_people(self):
        """controls: 20-05 49-01 49-02"""
        self.lc("end-of-life")
        with self.assertRaises(ServiceError):
            self.lc("reactivated-by-waiver", waiver_id=None, second_approver_token=self.w.operator("bob"))
        w = policy.Waiver("wv-1", 1, "lifecycle-reactivation", "CTL-EOL", (("runtime", "wasmtime@21.0.0"), ("partition", PART)),
                          "vendor extended support", "high", ("extra monitoring",), "alice", ("bob", "carol"), T0, T0, T0 + 3600)
        self.w.svc.waivers.submit(w, non_waivable_controls=set())
        self.lc("reactivated-by-waiver", waiver_id="wv-1", second_approver_token=self.w.operator("bob"))
        self.assertEqual(self.w.svc.certify(self.w.reader(), self.k)["lifecycle"]["waiver_id"], "wv-1")
        states = [e["state"] for e in self.w.store.events() if e["event_type"] == "lifecycle"]
        self.assertEqual(states, ["end-of-life", "reactivated-by-waiver"])  # original EOL never overwritten

    def test_future_effective_dates_and_warnings(self):
        """controls: 20-06 20-07 20-09"""
        self.lc("end-of-life", effective_at=T0 + 200)
        self.assertEqual(self.w.svc.certify(self.w.reader(), self.k)["verdict"], "certified")
        up = self.w.svc.upcoming_lifecycle(PART, T0, 3600)
        self.assertEqual(up[0]["state"], "end-of-life")
        d = self.w.svc.certify(self.w.reader(), self.k)
        self.assertEqual(d["expires_at"], T0 + 200)  # EOL caps certification expiry
        self.w.advance(200)
        self.assertEqual(self.w.svc.certify(self.w.reader(), self.k)["verdict"], "end-of-life")

    def test_historical_lifecycle_views_and_explain(self):
        """controls: 20-08 20-10 28-06"""
        d0 = self.w.svc.certify(self.w.reader(), self.k)
        self.lc("end-of-life")
        d1 = self.w.svc.certify(self.w.reader(), self.k)
        self.assertEqual(self.w.svc.explain(self.w.reader(), d0["decision_id"])["verdict"], "certified")
        ex = self.w.svc.explain(self.w.reader(), d1["decision_id"])
        self.assertEqual((ex["verdict"], ex["replacement_runtime"]), ("end-of-life", "wasmtime@22.0.0"))
        view = self.w.svc.lifecycle_view(PART, T0)
        self.assertEqual(view["runtimes"][0]["state"], "end-of-life")


class NegativeAgeingTest(unittest.TestCase):
    def test_failure_classes_and_ttl_boundaries(self):
        """controls: 21-01 21-02 21-03 21-04 21-07 21-10"""
        w = World()
        r = w.svc.ingest(w.producer(), w.evidence(result="incompatible", failure_class="deterministic"))
        k = w.key_for(r)
        w.advance(10 * 86400)
        d = w.svc.certify(w.reader(), k)
        self.assertEqual((d["verdict"], d["next_retest_at"]), ("incompatible", None))
        w2 = World()
        r = w2.svc.ingest(w2.producer(), w2.evidence(result="incompatible", failure_class="transient"))
        k2 = w2.key_for(r)
        w2.advance(3600)
        self.assertEqual(w2.svc.certify(w2.reader(), k2)["verdict"], "incompatible")
        w2.advance(1)
        d = w2.svc.certify(w2.reader(), k2)
        self.assertEqual((d["verdict"], d["deployable"]), ("retest-required", False))
        self.assertIn("next_retest_at", d)

    def test_newer_positive_supersedes_with_linkage_and_producer_conflict(self):
        """controls: 21-05 21-06 31-03"""
        w = World()
        r = w.svc.ingest(w.producer(), w.evidence(result="incompatible", failure_class="transient"))
        k = w.key_for(r)
        w.advance(10)
        w.svc.ingest(w.producer(), w.evidence(result="compatible", mutate=lambda e: e.update(supersedes=r["evidence_id"])))
        self.assertEqual(w.svc.certify(w.reader(), k)["verdict"], "certified")
        w.advance(10)
        w.svc.ingest(w.producer("producer-b"), w.evidence(producer="producer-b", result="incompatible", failure_class="deterministic"))
        self.assertEqual(w.svc.certify(w.reader(), k)["reason_code"], "R_CONFLICT")

    def test_offline_cache_never_ages_negative_into_positive(self):
        """controls: 21-08 24-04"""
        w = World()
        c = offline.OfflineCache(os.path.join(w.tmp, "cache.json"), w.trust, "edge-1", "node-1", ENV)
        b = offline.build_bundle(w.kp, "svc-key", site="edge-1", node="node-1", environment=ENV, counter=1, issued_at=T0,
                                 not_after=T0 + 100, revocation_checkpoint_at=T0, policy_revision="p:1",
                                 entries=[{"key": "k-neg", "verdict": "incompatible"}])
        c.install(b)
        self.assertFalse(c.decide("k-neg", now=T0 + 10)["deployable"])
        self.assertFalse(c.decide("k-neg", now=T0 + 1000)["deployable"])
        self.assertFalse(c.decide("k-absent", now=T0 + 10)["deployable"])

    def test_negative_metrics_visible(self):
        """controls: 21-09"""
        w = World()
        r = w.svc.ingest(w.producer(), w.evidence(result="incompatible", failure_class="flaky"))
        w.svc.certify(w.reader(), w.key_for(r))
        self.assertEqual(w.svc.metrics.get("gap15_certifications_total", verdict="incompatible"), 1)


class SchedulerTest(unittest.TestCase):
    def test_idempotent_queue_priority_and_quota(self):
        """controls: 22-01 22-02 22-03 22-04"""
        s = scheduler.RecertScheduler(lab_quota={"lab-a": 1})
        p_hi = scheduler.priority(seconds_to_expiry=60, criticality=5, population=500, severity=3, coverage_gap=False)
        p_lo = scheduler.priority(seconds_to_expiry=86400, criticality=1, population=1, severity=0, coverage_gap=False)
        s.enqueue("k1", "ttl-expiry", 7, lab="lab-a", prio=p_lo, now=T0)
        _, created = s.enqueue("k1", "ttl-expiry", 7, lab="lab-a", prio=p_lo, now=T0)
        self.assertFalse(created)
        s.enqueue("k2", "revocation-advisory", 1, lab="lab-a", prio=p_hi, now=T0)
        j = s.lease("w1", T0)
        self.assertEqual(j.scope, "k2")
        self.assertIsNone(s.lease("w2", T0))  # lab quota 1

    def test_leases_fencing_retry_dead_letter(self):
        """controls: 22-05 22-06"""
        s = scheduler.RecertScheduler(lab_quota={"l": 5}, max_attempts=2, lease_s=10)
        s.enqueue("k", "coverage-gap", 1, lab="l", prio=1, now=T0)
        j = s.lease("w1", T0)
        j2 = s.lease("w2", T0 + 11)  # w1's lease expired; w2 fences it off
        with self.assertRaises(scheduler.SchedulerError):
            s.complete(j.job_key, "w1", 1, ok=True)
        s.complete(j2.job_key, "w2", j2.fence, ok=False, error="runtime unavailable")
        self.assertEqual(s.jobs[j.job_key].state, "dead")

    def test_supersession_cancel_controls_and_metrics(self):
        """controls: 22-07 22-08 22-09"""
        s = scheduler.RecertScheduler(lab_quota={"l": 5})
        s.enqueue("k", "input-change", 1, lab="l", prio=1, now=T0)
        s.enqueue("k", "input-change", 2, lab="l", prio=1, now=T0)
        self.assertEqual(s.jobs["k|input-change|1"].state, "superseded")
        s.control("pause", actor="alice")
        self.assertIsNone(s.lease("w", T0))
        s.control("resume", actor="alice")
        self.assertEqual(s.metrics(T0 + 5)["depth"], 1)
        self.assertEqual(s.audit[0]["actor"], "alice")

    def test_massive_expiry_storm_bounded(self):
        """controls: 22-10 32-10"""
        s = scheduler.RecertScheduler(lab_quota={"l": 8})
        for i in range(5000):
            s.enqueue(f"k{i}", "ttl-expiry", 1, lab="l", prio=random.Random(i).random(), now=T0)
        leased = [s.lease(f"w{i}", T0) for i in range(20)]
        self.assertEqual(sum(1 for j in leased if j), 8)


class PolicyTest(unittest.TestCase):
    def setUp(self):
        self.p = policy.PolicySet("p:1", [
            policy.PolicyRule("rev", "revocation", "deny", (("verdict", "revoked"),)),
            policy.PolicyRule("eol", "lifecycle", "deny", (("lifecycle", "end-of-life"),), control_id="CTL-EOL"),
            policy.PolicyRule("cost-allow", "cost", "allow", (("site", "edge-1"),)),
            policy.PolicyRule("res", "residency", "deny", (("site", "eu-1"),), control_id="CTL-RES"),
        ])

    def test_precedence_and_trace(self):
        """controls: 23-01 23-02 23-04"""
        r = policy.evaluate(self.p, {"lifecycle": "end-of-life", "site": "edge-1"}, T0)
        self.assertEqual((r["effect"], r["decided_by"]), ("deny", "eol"))
        self.assertEqual([t["rule"] for t in r["trace"]], ["eol", "cost-allow"])

    def test_waivers_scoped_non_waivable(self):
        """controls: 23-03 49-03 49-07"""
        reg = policy.WaiverRegistry()
        with self.assertRaises(policy.PolicyError):
            reg.submit(policy.Waiver("w0", 1, "security-control", "CTL-REV", (("site", "x"),), "j", "low", (), "o", ("a",), T0, T0, T0 + 10),
                       non_waivable_controls={"CTL-REV"})
        reg.submit(policy.Waiver("w1", 1, "policy-bypass", "CTL-RES", (("site", "eu-1"),), "j", "low", ("c",), "o", ("a",), T0, T0, T0 + 100),
                   non_waivable_controls=set())
        r = policy.evaluate(self.p, {"site": "eu-1"}, T0 + 1, reg)
        self.assertEqual((r["effect"], r["waivers"]), ("allow", ["w1@1"]))
        r = policy.evaluate(self.p, {"verdict": "revoked", "site": "eu-1"}, T0 + 1, reg)
        self.assertEqual(r["effect"], "deny")

    def test_bundle_validation(self):
        """controls: 23-05 23-06"""
        bad = policy.PolicySet("p:x", [policy.PolicyRule("a", "security", "deny", (("site", "s"),)),
                                       policy.PolicyRule("b", "security", "allow", (("site", "s"),)),
                                       policy.PolicyRule("c", "lifecycle", "allow", (("site", "*"),)),
                                       policy.PolicyRule("d", "moon", "deny", (("colour", "red"),))])
        probs = bad.validate()
        self.assertEqual(len(probs), 4)
        self.assertTrue(self.p.digest().startswith("sha256:"))
        w = World()
        r = w.svc.ingest(w.producer(), w.evidence())
        d = w.svc.certify(w.reader(), w.key_for(r))
        self.assertEqual(d["policy"]["policy_revision"], "policy:1")

    def test_canary_simulation_and_unavailable_policy(self):
        """controls: 23-07 23-08 23-10"""
        new = policy.PolicySet("p:2", self.p.rules + [policy.PolicyRule("slo", "slo", "deny", (("site", "edge-1"),))])
        rep = policy.simulate(self.p, new, [{"site": "edge-1"}, {"site": "edge-2"}], T0)
        self.assertEqual(len(rep["changed"]), 1)
        empty = policy.PolicySet("p:none", [])
        self.assertEqual(policy.evaluate(empty, {"verdict": "untested"}, T0)["effect"], "allow")  # policy never upgrades a verdict
        w = World()
        d = w.svc._decide(CertKey(PART, art(9), "wasmtime@21.0.0", "profile:x"), T0)
        self.assertFalse(d["deployable"])


class WaiverRegistryTest(unittest.TestCase):
    def mk(self, **kw):
        base = dict(waiver_id="w", revision=1, wtype="operational", control_id="C", scope=(("site", "s"),), justification="j",
                    risk="medium", compensating_controls=("c",), owner="o", approvers=("a",), created_at=T0, effective_at=T0,
                    expires_at=T0 + 100)
        base.update(kw)
        return policy.Waiver(**base)

    def test_sod_expiry_renewal_history(self):
        """controls: 49-04 49-05 49-06 49-08 49-10"""
        reg = policy.WaiverRegistry()
        with self.assertRaises(policy.PolicyError):
            reg.submit(self.mk(risk="high", approvers=("a",)), non_waivable_controls=set())
        with self.assertRaises(policy.PolicyError):
            reg.submit(self.mk(scope=(("site", "*"),)), non_waivable_controls=set())
        with self.assertRaises(policy.PolicyError):
            reg.submit(self.mk(approvers=("o",)), non_waivable_controls=set())
        reg.submit(self.mk(), non_waivable_controls=set())
        with self.assertRaises(policy.PolicyError):
            reg.submit(self.mk(revision=2, expires_at=T0 + 200), non_waivable_controls=set())  # silent renewal
        reg.submit(self.mk(revision=2, expires_at=T0 + 200, approvers=("b",)), non_waivable_controls=set())
        self.assertEqual(len(reg.expiring(T0, 250)), 1)
        self.assertEqual(reg.active(T0 + 201), [])
        reg.revoke("w", T0 + 50)
        self.assertEqual([h.revision for h in reg.history], [1, 2, 3])
        self.assertFalse(self.mk().applies({"site": "other"}, T0 + 1))

    def test_governance_report(self):
        """controls: 49-09"""
        reg = policy.WaiverRegistry()
        reg.submit(self.mk(), non_waivable_controls=set())
        rep = reg.report(T0 + 1)
        self.assertEqual((rep["active"], rep["by_risk"]["medium"]), (1, 1))


class OfflineCacheTest(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.path = os.path.join(self.w.tmp, "offline.json")
        self.c = offline.OfflineCache(self.path, self.w.trust, "edge-1", "node-1", ENV)

    def bundle(self, counter=1, entries=None, **kw):
        args = dict(site="edge-1", node="node-1", environment=ENV, counter=counter, issued_at=T0, not_after=T0 + 1000,
                    revocation_checkpoint_at=T0, policy_revision="p:1",
                    entries=entries or [{"key": "k1", "verdict": "certified", "expires_at": T0 + 500},
                                        {"key": "k2", "verdict": "revoked"}])
        args.update(kw)
        return offline.build_bundle(self.w.kp, "svc-key", **args)

    def test_signed_scoped_typed_entries(self):
        """controls: 24-01 24-02 24-04 24-09"""
        self.c.install(self.bundle())
        self.assertTrue(self.c.decide("k1", now=T0 + 10)["deployable"])
        self.assertEqual(self.c.decide("k2", now=T0 + 10)["verdict"], "revoked")
        other = offline.OfflineCache(self.path + "2", self.w.trust, "edge-2", "node-1", ENV)
        with self.assertRaises(offline.OfflineError):
            other.install(self.bundle())
        self.assertEqual(self.c.status(T0 + 10)["bundle_counter"], 1)

    def test_hard_expiry_revocation_freshness_rollback(self):
        """controls: 24-03 24-05 24-10"""
        self.c.install(self.bundle(counter=2))
        self.assertEqual(self.c.decide("k1", now=T0 + 501)["verdict"], "expired")
        self.assertEqual(self.c.decide("k1", now=T0 + 3601)["reason_code"], "R_OFFLINE_BUNDLE_EXPIRED")
        c2 = offline.OfflineCache(self.path, self.w.trust, "edge-1", "node-1", ENV, max_revocation_age_s=5)
        c2.install(self.bundle(counter=3))
        self.assertEqual(c2.decide("k1", now=T0 + 6)["reason_code"], "R_OFFLINE_REVOCATION_STALE")
        with self.assertRaises(offline.OfflineError):
            c2.install(self.bundle(counter=3))

    def test_atomic_write_and_tamper(self):
        """controls: 24-06 24-10"""
        self.c.install(self.bundle())
        raw = open(self.path, "rb").read().replace(b'"revoked"', b'"certified"')
        open(self.path, "wb").write(raw)
        with self.assertRaises(offline.OfflineError):
            self.c.load()
        self.assertFalse(os.path.exists(self.path + ".tmp"))

    def test_deny_first_eviction(self):
        """controls: 24-07"""
        entries = [{"key": f"p{i}", "verdict": "certified", "expires_at": T0 + 500} for i in range(5)] + \
                  [{"key": "d1", "verdict": "revoked"}, {"key": "d2", "verdict": "quarantined"}]
        b = offline.build_bundle(self.w.kp, "svc-key", site="edge-1", node="node-1", environment=ENV, counter=1, issued_at=T0,
                                 not_after=T0 + 1000, revocation_checkpoint_at=T0, policy_revision="p:1", entries=entries, max_entries=3)
        keys = [e["key"] for e in b["bundle"]["entries"]]
        self.assertIn("d1", keys)
        self.assertIn("d2", keys)

    def test_reconnect_reconciliation(self):
        """controls: 24-08 31-10"""
        self.c.install(self.bundle())
        self.c.decide("k1", now=T0 + 10)
        diffs = self.c.reconcile(lambda key, at: {"deployable": False, "verdict": "revoked"})
        self.assertEqual(diffs, [{"key": "k1", "offline": "certified", "online": "revoked"}])


class PartitionTest(unittest.TestCase):
    def test_canonical_identifiers(self):
        """controls: 25-01"""
        self.assertEqual(partition.Partition.parse(PART).key, PART)
        for bad in ("Acme/prod/edge-1", "acme/prod", "acme/prod/edge_1", " acme/prod/e", "acme/prod/-e"):
            with self.assertRaises(partition.PartitionError):
                partition.Partition.parse(bad)

    def test_no_cross_partition_evidence_reuse(self):
        """controls: 25-04 25-02 36-07"""
        w = World()
        r = w.svc.ingest(w.producer(), w.evidence(partition=PART))
        k2 = w.key_for(r, partition=PART2)
        self.assertEqual(w.svc.certify(w.reader(), k2)["verdict"], "untested")
        self.assertEqual(w.store.matrix_view(PART2)["results"], [])

    def test_per_partition_quota_fairness(self):
        """controls: 25-07 32-07"""
        from gap15_runtime_compatibility_certification.production.capacity import CapacityError, FairQueue
        q = FairQueue(capacity=100, per_partition=3, weights={PART: 2, PART2: 1})
        for i in range(3):
            q.put(PART, i)
        with self.assertRaises(CapacityError):
            q.put(PART, 99)
        q.put(PART2, "x")
        order = [q.get()[0] for _ in range(4)]
        self.assertEqual(order, [PART, PART, PART2, PART])

    def test_replication_export_rules_documented(self):
        """controls: 25-05"""
        adr = open(os.path.join(os.path.dirname(__file__), "..", "..", "docs", "ADR.md")).read()
        self.assertIn("ADR-006", adr)
        self.assertIn("residency", adr)

    def test_partition_context_in_traces_logs(self):
        """controls: 25-08"""
        w = World()
        w.svc.ingest(w.producer(), w.evidence())
        a = w.store.audit_events()[-1]
        self.assertEqual(a["partition"], PART)
        self.assertIsNotNone(a["trace_id"])


if __name__ == "__main__":
    unittest.main()
