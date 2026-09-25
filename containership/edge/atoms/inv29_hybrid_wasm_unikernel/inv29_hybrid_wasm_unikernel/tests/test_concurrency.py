"""Concurrency / race tests (MC034): replay guard, idempotent submit, keyring
revocation, metrics and the ledger under contention."""
import pathlib
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

import _fixtures as F
from inv29_hybrid_wasm_unikernel import admission as adm
from inv29_hybrid_wasm_unikernel import evidence as E
from inv29_hybrid_wasm_unikernel import lifecycle as L
from inv29_hybrid_wasm_unikernel import telemetry as T

THREADS = 16


class ConcurrencyTest(unittest.TestCase):
    def test_same_nonce_admitted_exactly_once_under_race(self):
        kr = F.keyring()
        a = F.admitter(kr)
        req = F.request(kr)
        barrier = threading.Barrier(THREADS)
        results = []

        def go():
            barrier.wait()
            try:
                a.admit(req)
                results.append("ok")
            except adm.ReplayDetected:
                results.append("replay")

        with ThreadPoolExecutor(THREADS) as ex:
            for _ in range(THREADS):
                ex.submit(go)
        self.assertEqual(results.count("ok"), 1)
        self.assertEqual(results.count("replay"), THREADS - 1)

    def test_idempotent_submit_under_race(self):
        with tempfile.TemporaryDirectory() as d:
            kr = F.keyring()
            lc = L.Lifecycle(F.admitter(kr), L.Store(pathlib.Path(d)))
            req = F.request(kr)
            with ThreadPoolExecutor(THREADS) as ex:
                docs = list(ex.map(lambda _: lc.submit(req), range(THREADS * 2)))
            self.assertEqual({doc["id"] for doc in docs}.__len__(), 1)
            self.assertTrue(all(doc["state"] == L.ADMITTED for doc in docs))
            self.assertEqual(lc.counts(), {L.ADMITTED: 1})

    def test_distinct_requests_all_admitted(self):
        kr = F.keyring()
        a = F.admitter(kr, replay=adm.ReplayGuard(capacity=10_000))
        reqs = [F.request(kr) for _ in range(400)]
        with ThreadPoolExecutor(THREADS) as ex:
            recs = list(ex.map(a.admit, reqs))
        self.assertEqual(len({r["admission"]["nonce"] for r in recs}), 400)
        self.assertEqual(len(a.replay), 400)

    def test_revocation_races_with_admission(self):
        """After revoke() returns, no admission using that key can succeed."""
        kr = F.keyring()
        a = F.admitter(kr)
        reqs = [F.request(kr) for _ in range(300)]
        revoked = threading.Event()
        late_ok = []

        def go(req):
            before = revoked.is_set()
            try:
                a.admit(req)
                if before:
                    late_ok.append(req.nonce)
            except adm.AttestationInvalid:
                pass

        with ThreadPoolExecutor(THREADS) as ex:
            futs = [ex.submit(go, r) for r in reqs[:150]]
            kr.revoke(F.ATTEST_KEY); revoked.set()
            futs += [ex.submit(go, r) for r in reqs[150:]]
            for f in futs:
                f.result()
        self.assertEqual(late_ok, [])

    def test_metrics_and_ledger_are_consistent_under_contention(self):
        m = T.Metrics()
        with ThreadPoolExecutor(THREADS) as ex:
            list(ex.map(lambda i: m.inc("inv29_x_total", outcome="admitted"), range(5000)))
        self.assertEqual(m.value("inv29_x_total", outcome="admitted"), 5000)
        with tempfile.TemporaryDirectory() as d:
            led = E.Ledger(pathlib.Path(d) / "l.jsonl")
            with ThreadPoolExecutor(8) as ex:
                list(ex.map(lambda i: led.append("t", {"i": i}), range(200)))
            self.assertEqual(led.verify()["entries"], 200)


if __name__ == "__main__":
    unittest.main()
