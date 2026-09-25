"""Components 03 (durable replay), 11 (WAL), 14 (audit ledger), 38 (state
reconstruction), 43 (backup/restore).  Crash/restart/corruption are exercised
by actually truncating and corrupting files, not inferred."""
import json
import os
import unittest

from fixtures import sample, tmpdir
from gap09_unified_observability.components.audit_ledger import AuditLedger
from gap09_unified_observability.components.durable import (DurableReplayGuard, WriteAheadBuffer, backup, read_snapshot,
                                                            restore, restore_store, snapshot_store, write_snapshot)
from gap09_unified_observability.components.errors import Corrupted, QuotaExceeded
from gap09_unified_observability.runtime import HMACFixtureVerifier, ReplayDetected, ReporterAuthority, SignalStore


class TestReplay(unittest.TestCase):
    def test_survives_restart_and_window(self):
        d = tmpdir(); p = os.path.join(d, "r.log")
        g = DurableReplayGuard(p, window=100)
        g.check_and_record("a", "s1", 1000, 1000)
        g2 = DurableReplayGuard(p, window=100)          # "restart"
        with self.assertRaises(ReplayDetected):
            g2.check_and_record("a", "s1", 1000, 1050)
        with self.assertRaises(ReplayDetected):         # too old to judge: boundary issued == now-window
            g2.check_and_record("a", "s-old", 950, 1050)
        g2.check_and_record("a", "s2", 951, 1050)
        self.assertEqual(g2.compact(1200), 0)            # both evicted after window
        self.assertEqual(len(DurableReplayGuard(p, window=100)), 0)

    def test_torn_tail_recovered_and_mid_corruption_refused(self):
        d = tmpdir(); p = os.path.join(d, "r.log")
        g = DurableReplayGuard(p, window=100)
        for i in range(3):
            g.check_and_record("a", f"s{i}", 1000, 1000)
        with open(p, "ab") as fh:
            fh.write(b"deadbeef\t{\"r\":")                # crash mid-write
        g2 = DurableReplayGuard(p, window=100)
        self.assertGreater(g2.recovered_dropped_bytes, 0)
        self.assertEqual(len(g2), 3)
        data = open(p, "rb").read().split(b"\n")
        data[0] = data[0][:-2] + b"xx"
        open(p, "wb").write(b"\n".join(data))
        with self.assertRaises(Corrupted):
            DurableReplayGuard(p, window=100)

    def test_disk_bound(self):
        g = DurableReplayGuard(os.path.join(tmpdir(), "r.log"), window=100, max_bytes=200)
        with self.assertRaises(QuotaExceeded):
            for i in range(50):
                g.check_and_record("a", f"s{i}", 1000, 1000)


class TestWAL(unittest.TestCase):
    def test_resume_only_unacked_in_order(self):
        p = os.path.join(tmpdir(), "w.log")
        w = WriteAheadBuffer(p)
        for i in range(5):
            w.append({"i": i})
        w.ack(0); w.ack(2)
        w2 = WriteAheadBuffer(p)
        self.assertEqual([v["i"] for _, v in w2.pending()], [1, 3, 4])
        self.assertEqual(w2.append({"i": 5}), 5)

    def test_crash_between_append_and_ack(self):
        p = os.path.join(tmpdir(), "w.log")
        w = WriteAheadBuffer(p); w.append({"i": 0})
        with open(p, "ab") as fh:
            fh.write(b"0000")                            # torn ack record
        self.assertEqual(len(WriteAheadBuffer(p).pending()), 1)


class TestAuditLedger(unittest.TestCase):
    def test_chain_tamper_truncation_and_scrub(self):
        p = os.path.join(tmpdir(), "a.jsonl")
        a = AuditLedger(p)
        for i in range(4):
            a.append("x", {"i": i, "api_token": "SECRET-VALUE"}, actor="t")
        head = a.head()
        a.verify(head)
        self.assertNotIn("SECRET-VALUE", open(p).read())
        lines = open(p).read().splitlines()
        e = json.loads(lines[1]); e["payload"]["i"] = 99; lines[1] = json.dumps(e, sort_keys=True)
        open(p, "w").write("\n".join(lines) + "\n")
        with self.assertRaises(Corrupted):
            a.verify()
        p2 = os.path.join(tmpdir(), "b.jsonl")
        b = AuditLedger(p2)
        for i in range(4):
            b.append("x", {"i": i}, actor="t")
        head = b.head()
        kept = open(p2).read().splitlines()[:3]
        open(p2, "w").write("\n".join(kept) + "\n")
        AuditLedger.verify_entries(AuditLedger._load(p2))   # chain alone cannot see truncation...
        with self.assertRaises(Corrupted):
            b.verify(head)                                  # ...the external anchor can


class TestStateAndBackup(unittest.TestCase):
    def _store(self):
        auth = ReporterAuthority("rep", "software", frozenset({"t1"}))
        st = SignalStore(trust_verifier=HMACFixtureVerifier({("rep", "k"): b"k" * 32}, {"rep": auth}))
        s = [sample()]
        payload = st.canonical_submission_payload(reporter="rep", submission_id="x", issued_at=100, samples=s)
        st.submit_verified("rep", s, submission_id="x", issued_at=100,
                           signature=HMACFixtureVerifier.sign(b"k" * 32, payload), attestation={"key_id": "k"}, now=100)
        return st

    def test_snapshot_restart_equivalence_and_corruption(self):
        st = self._store()
        d = tmpdir(); p = os.path.join(d, "snap.json")
        write_snapshot(p, snapshot_store(st))
        st2 = restore_store(read_snapshot(p))
        q = dict(caller_tenant="t1", tenant="t1", environment="prod", site="s1", workload="w1", signal="cpu", now=110)
        self.assertEqual(st.read(**q), st2.read(**q))
        with open(p, "r+b") as fh:
            fh.seek(5); fh.write(b"X")
        with self.assertRaises(Corrupted):
            read_snapshot(p)

    def test_backup_restore_verifies(self):
        src = tmpdir()
        write_snapshot(os.path.join(src, "snap.json"), snapshot_store(self._store()))
        bk = tmpdir(); backup(src, bk)
        dst = tmpdir(); restore(bk, dst)
        self.assertTrue(os.path.exists(os.path.join(dst, "snap.json")))
        with open(os.path.join(bk, "snap.json"), "ab") as fh:
            fh.write(b" ")
        with self.assertRaises(Corrupted):
            restore(bk, tmpdir())


if __name__ == "__main__":
    unittest.main()
