"""Disaster / partition / reconnect / degraded-control-plane scenarios (MC-051) and soak/burst (MC-050).

The soak here is the in-suite short form (``INV28_SOAK_N`` selections, default 3000); the long form
is ``tools/soak.py`` whose result is retained in evidence/SOAK_RESULTS.json.  Fleet-scale tests
against a real multi-site deployment are out of reach of this archive and stay a recorded blocker.
"""
import datetime as dt
import os
import random
import tempfile
import threading
import unittest

from harness import F, Reason, refusal
from inv28_unikernel_implementations.certification import CertificationStore
from inv28_unikernel_implementations.registry import FileStore, Registry

R = Reason


class Flaky:
    def __init__(self, docs):
        self.docs, self.up, self.calls = docs, True, 0

    def __call__(self):
        self.calls += 1
        if not self.up:
            raise TimeoutError("partitioned")
        return self.docs


class Scenarios(unittest.TestCase):
    def test_partition_then_reconnect(self):
        w = F.world()
        src = Flaky([])
        w["selector"].certifications = CertificationStore(w["ring"], source=src)
        for c in w["certs"]._certs.values():
            w["selector"].certifications.ingest(c.to_dict())
        w["selector"].invalidate()
        self.assertEqual(w["selector"].select(F.request(), now=F.NOW).toolchain, "rumprun")
        src.up = False
        w["selector"].invalidate()
        code, _ = refusal(lambda: w["selector"].select(F.request(workload_id="w2"), now=F.NOW))
        self.assertEqual(code, R.DEPENDENCY_UNAVAILABLE.value)
        self.assertTrue(w["selector"].select(F.request(environment="dev"), now=F.NOW))   # non-prod keeps working
        src.up = True
        self.assertEqual(w["selector"].select(F.request(workload_id="w3"), now=F.NOW).toolchain, "rumprun")

    def test_advisory_feed_outage_then_recovery(self):
        from inv28_unikernel_implementations.advisories import sign_feed
        from inv28_unikernel_implementations.model import fmt_utc
        w = F.world()
        later = F.NOW + dt.timedelta(days=3)
        refusal(lambda: w["selector"].select(F.request(), now=later))
        w["advisories"].ingest(sign_feed(w["ring"], [], fmt_utc(later)))
        w["selector"].invalidate()
        # reviews are still fresh at +3 days; certificate still valid
        self.assertEqual(w["selector"].select(F.request(), now=later).toolchain, "rumprun")

    def test_control_plane_loss_restore_from_disk(self):
        w = F.world()
        with tempfile.TemporaryDirectory() as d:
            fs = FileStore(d)
            fs.save(w["registry"].snapshot())
            before = w["selector"].select(F.request(), now=F.NOW).ref
            # disaster: process state lost; restart from disk with the same keys
            snap, problems = fs.reconstruct(w["ring"])
            self.assertEqual(problems, [])
            reg = Registry(w["ring"])
            reg.load(snap)
            from inv28_unikernel_implementations.selection import Selector
            sel = Selector(reg, w["selector"].policy, certifications=w["certs"], advisories=w["advisories"])
            self.assertEqual(sel.select(F.request(), now=F.NOW).ref, before)

    def test_restore_with_wrong_keys_fails_closed(self):
        from inv28_unikernel_implementations.trust import KeyRing
        w = F.world()
        with tempfile.TemporaryDirectory() as d:
            fs = FileStore(d)
            fs.save(w["registry"].snapshot())
            snap, problems = fs.reconstruct(KeyRing.ephemeral())
            self.assertIsNone(snap)
            self.assertEqual(len(problems), 1)

    def test_degraded_gap08_rollback_still_works(self):
        from inv28_unikernel_implementations.rollout import Stage

        class Down:
            def announce(self, e):
                raise ConnectionError("down")
        w = F.world(records=[F.record("t", version="1"), F.record("t", version="2")])
        w["rollout"]._gap08 = None
        w["rollout"].plan("t@2", [Stage("c", 50), Stage("all", 100)])
        w["rollout"]._gap08 = Down()
        w["rollout"].rollback("t@2", reason="control plane degraded")
        w["selector"].invalidate()
        self.assertEqual(w["selector"].select(F.request(workload_id="any"), now=F.NOW).version, "1")


class SoakBurst(unittest.TestCase):
    def test_burst_and_soak(self):
        n = int(os.environ.get("INV28_SOAK_N", "3000"))
        w = F.world()
        rng = random.Random(7)
        langs = ("c", "ocaml", "rust", "go", "cobol")
        results = {"ok": 0, "refused": 0}
        lock = threading.Lock()

        def worker(k):
            for i in range(n // 6):
                req = F.request(workload_id=f"w{k}-{i % 50}", language=rng.choice(langs),
                                environment=rng.choice(("production", "staging", "dev")))
                try:
                    w["selector"].select(req, now=F.NOW)
                    key = "ok"
                except Exception as exc:  # noqa: BLE001
                    self.assertIn(getattr(exc, "code", None), (R.NO_SUITABLE_TOOLCHAIN,), exc)
                    key = "refused"
                with lock:
                    results[key] += 1
        ts = [threading.Thread(target=worker, args=(k,)) for k in range(6)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(sum(results.values()), (n // 6) * 6)
        self.assertEqual(w["audit"].verify(), [])
        self.assertLessEqual(len(w["selector"]._cache), 1024)


if __name__ == "__main__":
    unittest.main()
