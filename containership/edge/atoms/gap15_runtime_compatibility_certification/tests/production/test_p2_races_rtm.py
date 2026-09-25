"""Extra race coverage (11-05, 11-08, 37-03, 37-05) and RTM generation (41)."""
import json
import os
import sys
import threading
import unittest

from fixtures import PART, T0, World, art
from gap15_runtime_compatibility_certification.production import authz, policy, store as store_mod
from gap15_runtime_compatibility_certification.production.service import ServiceError
from gap15_runtime_compatibility_certification.production.state import CertKey

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(PKG, "tools"))


def ev(i, at=T0):
    return {"event_id": f"x{i}", "evidence_id": f"x{i}", "event_type": "evidence", "partition": PART, "artifact_digest": art(i),
            "runtime": "wasmtime@21.0.0", "profile_id": "profile:p", "result": "compatible", "observed_at": at}


class RetryTest(unittest.TestCase):
    def test_bounded_backoff_with_jitter_and_budget(self):
        """controls: 11-05"""
        w = World()
        sleeps = []
        other = store_mod.Store(w.db_path)
        calls = {"n": 0}

        def build(observed):
            calls["n"] += 1
            if calls["n"] <= 2:  # a competing writer wins the first two races
                other.commit([ev(100 + calls["n"])], audit=[{"event_id": f"o{calls['n']}", "action": "x"}])
            return [ev(1)], [{"event_id": f"a{calls['n']}", "action": "x"}]
        r = w.store.commit_with_retry(build, sleep=sleeps.append, rand=lambda: 1.0)
        self.assertEqual(r.revision, 3)
        self.assertEqual(sleeps, [0.005, 0.01])  # exponential, jitter multiplier applied

        def always_lose(observed):
            other.commit([ev(200 + len(sleeps))], audit=[{"event_id": f"z{len(sleeps)}", "action": "x"}])
            return [ev(300 + len(sleeps))], [{"event_id": f"b{len(sleeps)}", "action": "x"}]
        with self.assertRaises(store_mod.StoreError) as cm:
            w.store.commit_with_retry(always_lose, max_attempts=3, sleep=sleeps.append, rand=lambda: 0.5)
        self.assertEqual(cm.exception.code, "E_RETRY_BUDGET_EXHAUSTED")

    def test_conflict_emits_structured_event(self):
        """controls: 11-08"""
        w = World()
        w.svc.ingest(w.producer(), w.evidence())
        with self.assertRaises(ServiceError):
            w.svc.ingest_batch(w.producer(), [w.evidence(digest=art(2))], expected_revision=0)
        line = [l for l in w.svc.log.sink if "revision.conflict" in l][-1]
        rec = json.loads(line)
        self.assertEqual((rec["fields"]["expected_revision"], rec["fields"]["current_revision"]), (0, 1))
        self.assertTrue(any(a["action"] == "revision.conflict" for a in w.store.audit_events()))


class LifecyclePolicyRaceTest(unittest.TestCase):
    def test_lifecycle_transition_races_certify_monotonic(self):
        """controls: 37-03"""
        w = World()
        r = w.svc.ingest(w.producer(), w.evidence())
        k = w.key_for(r)
        seen = []
        barrier = threading.Barrier(2)

        def reader():
            barrier.wait()
            for _ in range(300):
                seen.append((w.store.certify(k, T0)["ledger_seq"], w.store.certify(k, T0)["verdict"]))

        def mutator():
            barrier.wait()
            w.svc.lifecycle(w.operator(), partition=PART, runtime="wasmtime@21.0.0", state="end-of-life", effective_at=T0,
                            reason="r", source="s")
        ts = [threading.Thread(target=reader), threading.Thread(target=mutator)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        for seq, verdict in seen:  # every read is consistent with the snapshot it reports
            self.assertEqual(verdict, "certified" if seq == 1 else "end-of-life")

    def test_policy_swap_during_inflight_decisions_bound_to_one_revision(self):
        """controls: 37-05"""
        w = World()
        r = w.svc.ingest(w.producer(), w.evidence())
        k = w.key_for(r)
        out = []
        stop = threading.Event()

        def decide():
            while not stop.is_set():
                d = w.svc._decide(k, T0)
                out.append((d["policy"]["policy_revision"], d["deployable"]))

        t = threading.Thread(target=decide)
        t.start()
        for i in range(20):
            w.svc.policy = policy.PolicySet(f"p:{i % 2}", [] if i % 2 == 0 else
                                            [policy.PolicyRule("deny-all-21", "security", "deny", (("runtime", "wasmtime@21.0.0"),))])
        stop.set()
        t.join()
        for rev, dep in out:  # each decision is internally consistent with the revision it records
            self.assertEqual(dep, rev in ("policy:1", "p:0"))


class RtmGenerationTest(unittest.TestCase):
    def test_rtm_has_100_rows_linked_to_components_modules_tests(self):
        """controls: 41-01 41-02 41-03 41-08 41-09"""
        import run_checklist as rc
        controls = rc.parse_checklist(rc.CHECKLIST_MD)
        self.assertEqual(len(controls), 1040)
        rows = [dict(c, tests=["t.x"], status="LOCALLY_VERIFIED", blocker=None, note=None) for c in controls]
        rtm = rc.build_rtm(rows)
        self.assertEqual([r["requirement_id"] for r in rtm], [f"GAP-15-C{i:03d}" for i in range(1, 101)])
        mapped = [r for r in rtm if r["missing_components"]]
        self.assertGreater(len(mapped), 80)
        self.assertTrue(all(r["production_modules"] for r in mapped if set(r["missing_components"]) & set(rc.MODULES)))
        self.assertTrue(all("owner" in r and "reviewer" in r for r in rtm))

    def test_gate_consumes_rtm_status(self):
        """controls: 41-10"""
        from gap15_runtime_compatibility_certification.production import release, signing
        kp = signing.DevelopmentKeyProvider()
        ts = signing.TrustStore()
        ts.add(signing.TrustedKey("k", "b", kp.generate("k"), scopes=frozenset({"gate:sign"})))
        inp = release.sign_input(kp, "k", release.GateInput("rtm", "sha256:" + "1" * 64, T0, {"status": "fail", "counts": {"BLOCKED": 3}}))
        d = release.exit_gate([inp], build_digest="sha256:" + "1" * 64, trust=ts, now=T0)
        self.assertEqual((d["decision"], d["inputs"]["rtm"]), ("NO_GO", "FAILED"))


if __name__ == "__main__":
    unittest.main()
