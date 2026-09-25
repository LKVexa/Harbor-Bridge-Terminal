"""SG-01/SG-03/SG-05-reference/SG-08/MC-40: persistent fenced store and lifecycle."""
from __future__ import annotations

import os
import sqlite3
import tempfile
import threading
import unittest

from . import _path  # noqa: F401

from inv57_durable_execution.durable import ActivityInDoubt, Crash, Worker
from inv57_durable_execution.errors import (ConcurrentAppend, HistoryQuarantined, IllegalTransition,
                                            OwnershipConflict, StaleOwner, Unauthorized)
from inv57_durable_execution.identity import WorkflowIdentity
from inv57_durable_execution.sqlite_store import SQLiteBackend, SQLiteHistoryStore
from inv57_durable_execution import lifecycle as lc


class Clock:
    def __init__(self, t: float = 1000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


def ident(wf="wf-1"):
    return WorkflowIdentity("tenant-a", "test", "site-1", "orders", wf, "run-1")


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.db = os.path.join(self.dir, "h.db")
        self.clock = Clock()
        self.b = SQLiteBackend(self.db, clock=self.clock)

    def tearDown(self):
        self.b.close()

    def open_store(self, owner="w1", ttl=30, wf="wf-1", backend=None):
        b = backend or self.b
        lease = b.acquire(ident(wf), owner, ttl)
        return SQLiteHistoryStore(b, ident(wf), lease)

    def test_history_survives_process_restart_and_replays(self):
        calls = []
        wf = lambda w: [w.activity("a", lambda: calls.append("a") or 1),
                        w.activity("b", lambda: calls.append("b") or {"k": [1, 2]})]
        self.assertEqual(Worker(self.open_store()).run(wf), [1, {"k": [1, 2]}])
        self.b.close()
        self.b = SQLiteBackend(self.db, clock=self.clock)          # "new process"
        w2 = Worker(self.open_store())
        self.assertEqual(w2.run(wf), [1, {"k": [1, 2]}])
        self.assertEqual(calls, ["a", "b"])
        self.assertEqual(w2.executed, [])

    def test_live_lease_blocks_second_owner(self):
        self.open_store("w1")
        with self.assertRaises(OwnershipConflict):
            self.b.acquire(ident(), "w2", 30)

    def test_stale_owner_cannot_commit_after_takeover(self):
        s1 = self.open_store("w1", ttl=5)
        Worker(s1).run(lambda w: w.activity("a", lambda: 1))
        self.clock.t += 10                                          # lease expires (paused worker)
        s2 = self.open_store("w2", ttl=30)
        self.assertEqual(s2.lease.epoch, s1.lease.epoch + 1)
        with self.assertRaises(StaleOwner):                          # zombie w1 wakes up
            Worker(s1).run(lambda w: [w.activity("a", lambda: 1), w.activity("b", lambda: 2)])
        self.assertEqual(len(self.b.load_events(ident().key())), 2)  # nothing from w1 landed

    def test_expired_lease_rejects_append_even_without_takeover(self):
        s1 = self.open_store("w1", ttl=5)
        self.clock.t += 6
        with self.assertRaises(StaleOwner):
            Worker(s1).run(lambda w: w.activity("a", lambda: 1))

    def test_renew_extends(self):
        s1 = self.open_store("w1", ttl=5)
        self.clock.t += 4
        s1.renew(5)
        self.clock.t += 4
        Worker(s1).run(lambda w: w.activity("a", lambda: 1))

    def test_conditional_append_rejects_out_of_order(self):
        s1 = self.open_store()
        Worker(s1).run(lambda w: w.activity("a", lambda: 1))
        ev = s1.events[-1]
        with self.assertRaises(ConcurrentAppend):
            self.b.conditional_append(s1.lease, ev)                  # duplicate seq

    def test_same_owner_two_caches_detects_tail_race(self):
        s1 = self.open_store("w1")
        s1b = SQLiteHistoryStore(self.b, ident(), s1.lease)          # same lease, stale cache
        Worker(s1).run(lambda w: w.activity("a", lambda: 1))
        with self.assertRaises(ConcurrentAppend):
            Worker(s1b).run(lambda w: w.activity("x", lambda: 9))

    def test_tampered_row_quarantines(self):
        Worker(self.open_store()).run(lambda w: w.activity("a", lambda: 1))
        con = sqlite3.connect(self.db)
        con.execute("UPDATE events SET body=replace(body,'\"v\":\"1\"','\"v\":\"2\"') WHERE seq=1")
        con.commit()
        con.close()
        with self.assertRaises(HistoryQuarantined):
            self.open_store()
        with self.assertRaises(HistoryQuarantined):                 # stays quarantined
            self.open_store()
        with self.assertRaises(Unauthorized):
            self.b.release_quarantine(ident().key(), capabilities=["workflow:control"])

    def test_tenants_isolated_by_key(self):
        Worker(self.open_store(wf="wf-1")).run(lambda w: w.activity("a", lambda: 1))
        s = self.open_store(wf="wf-2")
        self.assertEqual(len(s), 0)

    def test_crash_then_in_doubt_is_persisted(self):
        s = self.open_store()

        def wf(w):
            w.activity("pay", lambda: (_ for _ in ()).throw(Crash()))
        with self.assertRaises(Crash):
            Worker(s).run(wf)
        self.b.close()
        self.b = SQLiteBackend(self.db, clock=self.clock)
        with self.assertRaises(ActivityInDoubt):
            Worker(self.open_store()).run(wf)

    def test_concurrent_acquire_exactly_one_wins(self):
        results = []

        def go(owner):
            b = SQLiteBackend(self.db, clock=self.clock)
            try:
                b.acquire(ident(), owner, 30)
                results.append("won")
            except OwnershipConflict:
                results.append("lost")
            finally:
                b.close()
        ts = [threading.Thread(target=go, args=(f"w{i}",)) for i in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(results.count("won"), 1)

    def test_newer_backend_schema_refused(self):
        self.b._conn.execute("UPDATE meta SET v='99' WHERE k='schema_version'")
        from inv57_durable_execution.durable import HistoryCorruption
        with self.assertRaises(HistoryCorruption):
            SQLiteBackend(self.db)


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.b = SQLiteBackend(os.path.join(tempfile.mkdtemp(), "l.db"))
        self.ctl = ["workflow:control"]
        self.op = ["operator"]

    def test_happy_path_and_log(self):
        i = ident()
        self.b.control(i, "start", actor="svc", capabilities=self.ctl)
        self.b.control(i, "suspend", actor="svc", capabilities=self.ctl)
        self.b.control(i, "resume", actor="svc", capabilities=self.ctl)
        self.b.control(i, "complete", actor="svc", capabilities=self.ctl)
        self.assertEqual(self.b.lifecycle_state(i), (lc.State.COMPLETED, 4))
        self.assertEqual([r["control"] for r in self.b.lifecycle_log(i)],
                         ["start", "suspend", "resume", "complete"])

    def test_terminal_refuses_and_idempotent_repeat(self):
        i = ident()
        self.b.control(i, "start", actor="s", capabilities=self.ctl)
        self.b.control(i, "complete", actor="s", capabilities=self.ctl)
        t = self.b.control(i, "complete", actor="s", capabilities=self.ctl)
        self.assertFalse(t.changed)
        with self.assertRaises(IllegalTransition):
            self.b.control(i, "resume", actor="s", capabilities=self.ctl)

    def test_operator_only_controls(self):
        i = ident()
        self.b.control(i, "start", actor="s", capabilities=self.ctl)
        with self.assertRaises(Unauthorized):
            self.b.control(i, "terminate", actor="s", capabilities=self.ctl)
        with self.assertRaises(Unauthorized):
            self.b.control(i, "start", actor="anon", capabilities=[])
        self.assertEqual(self.b.control(i, "terminate", actor="op", capabilities=self.op).after,
                         lc.State.TERMINATED)

    def test_cas_version(self):
        i = ident()
        self.b.control(i, "start", actor="s", capabilities=self.ctl)
        with self.assertRaises(ConcurrentAppend):
            self.b.control(i, "suspend", actor="s", capabilities=self.ctl, expected_version=0)

    def test_every_table_row_is_reachable_and_unknown_control_refused(self):
        with self.assertRaises(IllegalTransition):
            lc.transition(lc.State.RUNNING, "explode")
        for row in lc.table():
            t = lc.transition(lc.State(row["from"]), row["control"])
            self.assertEqual(t.after.value, row["to"])
        for s in lc.TERMINAL:
            self.assertFalse(any(r["from"] == s.value for r in lc.table()))


if __name__ == "__main__":
    unittest.main()


class BackupRestoreAndFixtureTests(unittest.TestCase):
    """MC-61 backup/restore and MC-17 versioned conformance fixture."""

    def test_backup_restore_verifies_and_fences_old_workers(self):
        d = tempfile.mkdtemp()
        b = SQLiteBackend(os.path.join(d, "a.db"))
        lease = b.acquire(ident(), "w1", 60)
        Worker(SQLiteHistoryStore(b, ident(), lease)).run(
            lambda w: [w.activity("a", lambda: 1), w.activity("b", lambda: 2)])
        manifest = b.backup(os.path.join(d, "bk.db"))
        r = SQLiteBackend.restore(os.path.join(d, "bk.db"), os.path.join(d, "r.db"), manifest)
        self.assertEqual(len(r.load_events(ident().key())), 4)
        with self.assertRaises(StaleOwner):                          # pre-backup lease is dead
            r.conditional_append(lease, r.load_events(ident().key())[-1])
        s = SQLiteHistoryStore(r, ident(), r.acquire(ident(), "w2", 60))
        self.assertGreater(s.lease.epoch, 1000)
        self.assertEqual(Worker(s).run(lambda w: [w.activity("a", lambda: 9), w.activity("b", lambda: 9)]),
                         [1, 2])
        with self.assertRaises(FileExistsError):
            SQLiteBackend.restore(os.path.join(d, "bk.db"), os.path.join(d, "r.db"), manifest)

    def test_restore_detects_truncated_backup(self):
        d = tempfile.mkdtemp()
        b = SQLiteBackend(os.path.join(d, "a.db"))
        Worker(SQLiteHistoryStore(b, ident(), b.acquire(ident(), "w", 60))).run(
            lambda w: [w.activity("a", lambda: 1), w.activity("b", lambda: 2)])
        manifest = b.backup(os.path.join(d, "bk.db"))
        con = sqlite3.connect(os.path.join(d, "bk.db"))
        con.execute("DELETE FROM events WHERE seq >= 2")             # tail truncation keeps a valid chain
        con.commit()
        con.close()
        from inv57_durable_execution.durable import HistoryCorruption
        with self.assertRaises(HistoryCorruption):
            SQLiteBackend.restore(os.path.join(d, "bk.db"), os.path.join(d, "r.db"), manifest)

    def test_golden_fixture_replays(self):
        import pathlib
        from inv57_durable_execution.durable import InMemoryHistoryStore
        text = (pathlib.Path(__file__).parents[1] / "fixtures" / "history_v2_golden.json").read_text()
        w = Worker(InMemoryHistoryStore.from_json(text))
        out = w.run(lambda w: [
            w.activity("reserve", lambda: "X", activity_id="reserve-1", fingerprint="v1"),
            w.activity("charge", lambda: "X", activity_id="charge-1"),
            w.activity("blob", lambda: "X")])
        self.assertEqual(out, ["r-1", {"amount": 1250, "currency": "EUR", "ok": True},
                               (b"\x00\xff", 1.5, None, [1, 2])])
        self.assertEqual(w.executed, [])
        self.assertEqual(w.history_store.to_json(), text)            # byte-stable encoding
