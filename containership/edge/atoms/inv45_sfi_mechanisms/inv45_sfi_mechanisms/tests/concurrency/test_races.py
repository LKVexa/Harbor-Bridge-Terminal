"""Concurrency / race tests for shared state (C086, C058)."""
from __future__ import annotations

import copy
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from inv45_sfi_mechanisms.tests.support import Harness
from inv45_sfi_mechanisms.production import audit, config
from inv45_sfi_mechanisms.production.authz import ReplayCache
from inv45_sfi_mechanisms.production.controls import Admission
from inv45_sfi_mechanisms.production.errors import SfiError


def attempt(fn):
    try:
        fn()
        return "OK"
    except SfiError as e:
        return e.code


class RaceTest(unittest.TestCase):
    def test_descriptor_replay_race_exactly_one_load(self):
        h = Harness()
        try:
            r = h.submit()
            tok = h.tenant_token("t1", caps=("sfi.load",))
            with ThreadPoolExecutor(16) as ex:
                res = list(ex.map(lambda _: attempt(lambda: h.svc.load(tok, r["artifact"], r["descriptor"])),
                                  range(32)))
            self.assertEqual(res.count("OK"), 1)
            self.assertEqual(res.count("SFI_REPLAY_DETECTED"), 31)
        finally:
            h.close()

    def test_replay_cache_bounded(self):
        rc = ReplayCache(capacity=4, clock=lambda: 0.0)
        for i in range(4):
            rc.consume(str(i), 10.0)
        self.assertEqual(attempt(lambda: rc.consume("x", 10.0)), "SFI_OVERLOADED")
        rc2 = ReplayCache(capacity=4, clock=lambda: 100.0)
        for i in range(4):
            rc2.consume(str(i), 10.0)  # already expired
        rc2.consume("x", 200.0)  # expired entries purged, not live ones
        self.assertEqual(len(rc2), 1)

    def test_config_cas_race_exactly_one_winner(self):
        with tempfile.TemporaryDirectory() as td:
            s = config.GenerationStore(Path(td))
            barrier = threading.Barrier(8)

            def go(i):
                c = copy.deepcopy(config.DEFAULTS)
                c["telemetry"]["retention_days"] = 10 + i
                barrier.wait()
                return attempt(lambda: s.activate(c, author=f"w{i}", source="t", approval=None, expected_current=0))
            with ThreadPoolExecutor(8) as ex:
                res = list(ex.map(go, range(8)))
            self.assertEqual(res.count("OK"), 1, res)
            winner = res.index("OK")
            self.assertEqual(s.active()[1]["telemetry"]["retention_days"], 10 + winner)  # winner's content is active
            self.assertEqual(len(list((Path(td) / "generations").glob("gen-*.json"))), 1)  # losers wrote nothing
            self.assertTrue(all(r in ("OK", "SFI_CONFIG_CONFLICT") for r in res))

    def test_audit_concurrent_emit_chain_intact(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "a.jsonl"
            log = audit.AuditLog(p, fsync=False)
            with ThreadPoolExecutor(8) as ex:
                list(ex.map(lambda i: log.emit({"event": "e", "target": str(i)}), range(400)))
            self.assertEqual(audit.verify_chain(p)["events"], 400)

    def test_admission_never_exceeds_caps(self):
        a = Admission(max_concurrent=3, max_per_tenant=2, max_queue=100, queue_timeout=5)
        seen = []
        lock = threading.Lock()
        cur = {"n": 0, "t": {}}

        def work(i):
            t = f"t{i % 4}"
            try:
                with a.slot(t):
                    with lock:
                        cur["n"] += 1
                        cur["t"][t] = cur["t"].get(t, 0) + 1
                        seen.append((cur["n"], cur["t"][t]))
                    threading.Event().wait(0.002)
                    with lock:
                        cur["n"] -= 1
                        cur["t"][t] -= 1
            except SfiError:
                pass
        with ThreadPoolExecutor(12) as ex:
            list(ex.map(work, range(200)))
        self.assertLessEqual(max(n for n, _ in seen), 3)
        self.assertLessEqual(max(t for _, t in seen), 2)
        self.assertEqual(a.snapshot()["active"], 0)

    def test_parallel_submits_are_independent(self):
        h = Harness()
        try:
            toks = {t: h.tenant_token(t) for t in ("a", "b", "c", "d")}
            with ThreadPoolExecutor(4) as ex:
                res = list(ex.map(lambda t: attempt(lambda: h.submit(tenant=t, workload=f"w-{t}", token=toks[t])),
                                  ["a", "b", "c", "d"] * 3))
            self.assertTrue(all(r in ("OK", "SFI_OVERLOADED") for r in res), res)
            self.assertGreaterEqual(res.count("OK"), 4)
        finally:
            h.close()


if __name__ == "__main__":
    unittest.main()
