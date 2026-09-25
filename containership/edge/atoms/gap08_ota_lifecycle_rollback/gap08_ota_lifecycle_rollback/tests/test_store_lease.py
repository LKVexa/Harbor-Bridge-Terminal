"""Components 1, 2, 24, 32: durable CAS store, lease/fencing, backup/restore, concurrency races."""
from __future__ import annotations

import json
import multiprocessing as mp
import tempfile
import threading
import unittest
from pathlib import Path

import _path  # noqa: F401
from gap08_ota_lifecycle_rollback.common import FakeClock
from gap08_ota_lifecycle_rollback.errors import (Conflict, IntegrityFailure, StaleFence, StaleRevision,
                                                 ValidationFailed)
from gap08_ota_lifecycle_rollback.lease import LeaseService
from gap08_ota_lifecycle_rollback.store import FileStateStore, MemoryStateStore


def _state(pin="v1", log=()):
    return {"rollout_id": "r1", "pinned_target": pin, "audit_log": list(log), "x": 0}


def _race_worker(root, expected, fence, q):
    store = FileStateStore(root)
    try:
        store.commit("r1", {**_state(), "x": fence}, expected_revision=expected, fence=fence)
        q.put("win")
    except (StaleRevision, StaleFence):
        q.put("lose")


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def backends(self):
        return [MemoryStateStore(), FileStateStore(self.dir / "s")]

    def test_cas_exactly_one_winner_threads(self):
        for store in self.backends():
            store.create("r1", _state(), fence=1)
            results = []

            def go(i):
                try:
                    store.commit("r1", {**_state(), "x": i}, expected_revision=1, fence=1)
                    results.append("win")
                except StaleRevision:
                    results.append("lose")
            ts = [threading.Thread(target=go, args=(i,)) for i in range(16)]
            [t.start() for t in ts]
            [t.join() for t in ts]
            self.assertEqual(results.count("win"), 1, type(store).__name__)
            self.assertEqual(store.load("r1").revision, 2)

    def test_cas_exactly_one_winner_processes(self):
        root = self.dir / "mp"
        FileStateStore(root).create("r1", _state(), fence=1)
        q = mp.get_context("fork").Queue()
        ps = [mp.get_context("fork").Process(target=_race_worker, args=(root, 1, 1, q)) for _ in range(8)]
        [p.start() for p in ps]
        [p.join() for p in ps]
        res = [q.get() for _ in ps]
        self.assertEqual(res.count("win"), 1)

    def test_fence_regression_rejected(self):
        for store in self.backends():
            store.create("r1", _state(), fence=5)
            with self.assertRaises(StaleFence):
                store.commit("r1", _state(), expected_revision=1, fence=4)

    def test_pinned_target_and_audit_prefix_immutable(self):
        for store in self.backends():
            ev = {"event_hash": "a" * 64}
            store.create("r1", _state(log=[ev]), fence=1)
            with self.assertRaises(IntegrityFailure):
                store.commit("r1", _state(pin="v0", log=[ev]), expected_revision=1, fence=1)
            with self.assertRaises(IntegrityFailure):
                store.commit("r1", _state(log=[]), expected_revision=1, fence=1)
            store.commit("r1", _state(log=[ev, {"event_hash": "b" * 64}]), expected_revision=1, fence=1)

    def test_rejects_secrets_and_bad_ids(self):
        for store in self.backends():
            with self.assertRaises(ValidationFailed):
                store.create("r1", {**_state(), "api_token": "abc"}, fence=1)
            with self.assertRaises(ValidationFailed):
                store.create("../etc", _state(), fence=1)

    def test_tamper_and_torn_record_detected(self):
        store = FileStateStore(self.dir / "t")
        store.create("r1", _state(), fence=1)
        p = self.dir / "t" / "r1.json"
        raw = json.loads(p.read_text())
        raw["state"]["x"] = 99
        p.write_text(json.dumps(raw))
        with self.assertRaises(IntegrityFailure):
            store.load("r1")
        p.write_text(p.read_text()[:20])
        with self.assertRaises(IntegrityFailure):
            store.load("r1")

    def test_restart_continuity_byte_for_byte(self):
        store = FileStateStore(self.dir / "c")
        store.create("r1", _state(), fence=1)
        rec = store.commit("r1", {**_state(), "x": 7}, expected_revision=1, fence=2)
        again = FileStateStore(self.dir / "c").load("r1")
        self.assertEqual(again.to_dict(), rec.to_dict())

    def test_backup_restore_verified(self):
        store = FileStateStore(self.dir / "b")
        store.create("r1", _state(), fence=1)
        man = store.backup(self.dir / "bk")
        restored = FileStateStore.restore(self.dir / "bk", self.dir / "restored")
        self.assertEqual(restored.load("r1").to_dict(), store.load("r1").to_dict())
        self.assertIn("r1.json", man["files"])
        with self.assertRaises(Conflict):
            FileStateStore.restore(self.dir / "bk", self.dir / "restored")
        (self.dir / "bk" / "r1.json").write_text("{}")
        with self.assertRaises(IntegrityFailure):
            FileStateStore.restore(self.dir / "bk", self.dir / "r2")


class LeaseTest(unittest.TestCase):
    def test_tokens_monotonic_and_persisted(self):
        d = Path(tempfile.mkdtemp())
        clk = FakeClock()
        ls = LeaseService(clock=clk, persist_path=d / "l.json")
        a = ls.acquire("r", "A", 10)
        with self.assertRaises(Conflict):
            ls.acquire("r", "B", 10)
        clk.advance(11)
        b = ls.acquire("r", "B", 10)
        self.assertGreater(b.token, a.token)
        with self.assertRaises(StaleFence):
            ls.check("r", a.token)
        with self.assertRaises(StaleFence):
            ls.renew(a)
        ls2 = LeaseService(clock=clk, persist_path=d / "l.json")  # service restart
        c = ls2.acquire("r", "C", 10)
        self.assertGreater(c.token, b.token)

    def test_two_controller_race_only_current_fence_advances(self):
        clk = FakeClock()
        ls = LeaseService(clock=clk)
        store = MemoryStateStore(fence_check=lambda rid, tok: ls.check(f"rollout/{rid}", tok))
        a = ls.acquire("rollout/r1", "A", 5)
        store.create("r1", _state(), fence=a.token)
        clk.advance(6)                          # A pauses (GC / partition)
        b = ls.acquire("rollout/r1", "B", 5)    # B takes over
        store.commit("r1", _state(), expected_revision=1, fence=b.token)
        with self.assertRaises(StaleFence):     # A wakes and tries to write with its old view
            store.commit("r1", _state(), expected_revision=2, fence=a.token)


if __name__ == "__main__":
    unittest.main()
