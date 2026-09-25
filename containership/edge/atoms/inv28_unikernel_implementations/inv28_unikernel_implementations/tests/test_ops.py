"""Advisories, timeouts/cancellation, cache, resource bounds, capacity model (MC-037, MC-077..MC-080)."""
import datetime as dt
import json
import pathlib
import threading
import time
import unittest

from harness import F, Reason, ValidationError, codes_for, refusal
from inv28_unikernel_implementations.advisories import AdvisoryStore, sign_feed
from inv28_unikernel_implementations.model import fmt_utc
from inv28_unikernel_implementations.policy import SelectionPolicy, Waiver, default_policy
from inv28_unikernel_implementations.selection import CACHE_SIZE

R = Reason
PKG = pathlib.Path(F.__file__).resolve().parent


def adv(i, toolchain="rumprun", versions=("1.0.0-fixture",), severity="high", **kw):
    return {"id": f"ADV-{i}", "toolchain": toolchain, "affected_versions": list(versions), "severity": severity,
            "published": "2026-09-20", **kw}


class Advisories(unittest.TestCase):                                            # MC-037
    def test_open_high_advisory_eliminates_in_production(self):
        w = F.world()
        w["advisories"].ingest(sign_feed(w["ring"], [adv(1)], fmt_utc(F.NOW)))
        w["selector"].invalidate()
        _, ref = refusal(lambda: w["selector"].select(F.request(), now=F.NOW))
        self.assertIn(R.ADVISORY_OPEN.value, codes_for(ref, "rumprun@1.0.0-fixture"))

    def test_low_severity_or_other_version_or_withdrawn_does_not(self):
        for a in (adv(2, severity="low"), adv(3, versions=("0.9",)), adv(4, withdrawn=True)):
            with self.subTest(a=a["id"]):
                w = F.world()
                w["advisories"].ingest(sign_feed(w["ring"], [a], fmt_utc(F.NOW)))
                w["selector"].invalidate()
                self.assertEqual(w["selector"].select(F.request(), now=F.NOW).toolchain, "rumprun")

    def test_waiver_can_cover_advisory(self):
        base = default_policy()
        wv = Waiver("W-ADV", "rumprun@1.0.0-fixture", frozenset({R.ADVISORY_OPEN.value}), frozenset({"production"}),
                    "owner-a", "approver-b", "mitigated by network policy", "2026-10-01T00:00:00Z")
        w = F.world(policy=SelectionPolicy(base.policy_id, 2, base.environments, {}, (wv,)))
        w["advisories"].ingest(sign_feed(w["ring"], [adv(1)], fmt_utc(F.NOW)))
        w["selector"].invalidate()
        self.assertEqual(w["selector"].select(F.request(), now=F.NOW).waivers, ("W-ADV",))

    def test_feed_integrity_rules(self):
        w = F.world()
        good = sign_feed(w["ring"], [adv(1)], fmt_utc(F.NOW))
        bad_sig = dict(good, advisories=[adv(9)])
        wildcard = sign_feed(w["ring"], [adv(5, versions=("1.*",))], fmt_utc(F.NOW))
        sev = sign_feed(w["ring"], [adv(6, severity="urgent")], fmt_utc(F.NOW))
        older = sign_feed(w["ring"], [], fmt_utc(F.NOW - dt.timedelta(days=5)))
        w["advisories"].ingest(good)
        for bad in (bad_sig, wildcard, sev, older):
            with self.subTest(), self.assertRaises(ValidationError):
                w["advisories"].ingest(bad)

    def test_stale_feed_blocks_production_not_dev(self):
        w = F.world()
        later = F.NOW + dt.timedelta(days=3)
        code, _ = refusal(lambda: w["selector"].select(F.request(), now=later))
        self.assertEqual(code, R.DEPENDENCY_UNAVAILABLE.value)
        self.assertTrue(w["selector"].select(F.request(environment="dev"), now=later))

    def test_empty_store_is_stale(self):
        from inv28_unikernel_implementations.trust import KeyRing
        self.assertTrue(AdvisoryStore(KeyRing.ephemeral()).stale(F.NOW))


class DeadlinesAndCancellation(unittest.TestCase):                              # MC-079
    def test_deadline_exceeded(self):
        w = F.world()
        code, _ = refusal(lambda: w["selector"].select(F.request(), now=F.NOW, deadline=time.monotonic() - 1))
        self.assertEqual(code, R.DEADLINE_EXCEEDED.value)

    def test_cancelled(self):
        w = F.world()
        ev = threading.Event()
        ev.set()
        code, _ = refusal(lambda: w["selector"].select(F.request(), now=F.NOW, cancel=ev))
        self.assertEqual(code, R.CANCELLED.value)

    def test_slow_dependency_hits_deadline(self):
        from inv28_unikernel_implementations.certification import CertificationStore
        w = F.world()
        store = CertificationStore(w["ring"], source=lambda: (time.sleep(0.05), [])[1])
        w["selector"].certifications = store
        w["selector"].invalidate()
        code, _ = refusal(lambda: w["selector"].select(F.request(), now=F.NOW, deadline=time.monotonic() + 0.01))
        self.assertEqual(code, R.DEADLINE_EXCEEDED.value)

    def test_deadline_refusal_not_cached(self):
        w = F.world()
        refusal(lambda: w["selector"].select(F.request(), now=F.NOW, deadline=time.monotonic() - 1))
        self.assertEqual(w["selector"].select(F.request(), now=F.NOW).toolchain, "rumprun")


class Cache(unittest.TestCase):                                                  # MC-080
    def test_hit_and_invalidation_on_registry_change(self):
        w = F.world()
        s = w["selector"]
        a = s.select(F.request(), now=F.NOW)
        s.select(F.request(), now=F.NOW)
        self.assertEqual(s.cache_hits, 1)
        w["registry"].emergency_disable(a.ref, actor="operator", reason="x")
        refusal(lambda: s.select(F.request(), now=F.NOW))

    def test_policy_change_invalidates(self):
        w = F.world()
        s = w["selector"]
        s.select(F.request(language="rust", environment="staging"), now=F.NOW)
        base = default_policy()
        from inv28_unikernel_implementations.policy import EnvironmentRule
        strict = SelectionPolicy(base.policy_id, 2, {**base.environments, "staging": EnvironmentRule()})
        s.set_policy(strict)
        refusal(lambda: s.select(F.request(language="rust", environment="staging"), now=F.NOW))

    def test_cache_bounded(self):
        w = F.world()
        for i in range(CACHE_SIZE + 10):
            w["selector"].select(F.request(workload_id=f"w{i}"), now=F.NOW)
        self.assertLessEqual(len(w["selector"]._cache), CACHE_SIZE)

    def test_cached_selection_gets_fresh_ticket(self):
        w = F.world()
        a = w["selector"].select(F.request(), now=F.NOW)
        b = w["selector"].select(F.request(), now=F.NOW)
        self.assertEqual(a.decision_id, b.decision_id)
        self.assertTrue(b.ticket)


class CapacityModel(unittest.TestCase):                                        # MC-077, MC-078
    def test_capacity_document_matches_code_bounds(self):
        from inv28_unikernel_implementations import advisories, certification, model, registry, selection
        doc = json.loads((PKG / "ops" / "CAPACITY.json").read_text())
        b = doc["bounds"]
        self.assertEqual(b["registry_entries"], registry.MAX_ENTRIES)
        self.assertEqual(b["eliminations_reported"], selection.MAX_ELIMINATIONS)
        self.assertEqual(b["selection_cache_entries"], selection.CACHE_SIZE)
        self.assertEqual(b["token_length"], model.MAX_TOKEN_LEN)
        self.assertEqual(b["set_size"], model.MAX_SET_SIZE)
        self.assertEqual(b["certificates"], certification.MAX_CERTS)
        self.assertEqual(b["advisories"], advisories.MAX_ADVISORIES)
        for t in doc["saturation_thresholds"]:
            self.assertIn(t["action"], ("alert", "refuse"))

    def test_full_registry_selection_stays_fast(self):
        from inv28_unikernel_implementations.registry import MAX_ENTRIES
        recs = [F.record(f"t{i:04d}", languages=("c",) if i % 7 == 0 else ("ocaml",)) for i in range(MAX_ENTRIES)]
        w = F.world(records=recs, with_certs=False)
        w["selector"].policy  # noqa: B018
        t = time.perf_counter()
        r = w["selector"].select(F.request(environment="dev"), now=F.NOW)
        elapsed = time.perf_counter() - t
        self.assertEqual(r.toolchain, "t0000")
        self.assertLess(elapsed, 2.0, "1024-entry selection took > 2 s")


if __name__ == "__main__":
    unittest.main()
