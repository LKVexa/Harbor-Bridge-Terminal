"""Backup/restore, compaction controller, GAP-05 replication and site fencing (MC-019, MC-039, MC-040, MC-041)."""
from __future__ import annotations

import json
import os
import shutil
import unittest

from _util import FakeClock, readb, tmpdir, writeb
from inv05_current_control_state_system.backup import CompactionController, create_backup, restore_backup, verify_backup
from inv05_current_control_state_system.errors import CompactedError, CorruptionError, Fenced, InvalidArgument
from inv05_current_control_state_system.replication import ReplicaApplier, ReplicationSource, sync_once
from inv05_current_control_state_system.store import ControlStore, Put
from inv05_current_control_state_system.wal import DurableStore, Keyring, Sealer
from inv05_current_control_state_system.watch import WatchHub


def sealer(tag):
    return Sealer(Keyring({tag: bytes([len(tag)]) * 32}, tag))


class BackupTest(unittest.TestCase):
    def setUp(self):
        self.dir = tmpdir()
        self.bs, self.ds, self.key = sealer("backup1"), sealer("data1"), b"s" * 32
        self.src = ControlStore()
        for i in range(30):
            self.src.put(f"k/{i}", {"i": i})
        self.src.delete("k/0")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_backup_verify_restore_roundtrip(self):
        b = create_backup(self.src, self.dir, sealer=self.bs, sign_key=self.key, config_sha256="abc")
        self.assertEqual(b["status"], "verified")
        self.assertNotIn(b'"k/1"', readb(os.path.join(b["path"], "state.bin")))  # encrypted
        ds = restore_backup(b["path"], os.path.join(self.dir, "restored"), backup_sealer=self.bs,
                            sign_key=self.key, data_sealer=self.ds)
        self.assertEqual(ds.store.snapshot().to_dict()["kvs"], self.src.snapshot().to_dict()["kvs"])
        self.assertEqual(ds.store.revision, self.src.revision)
        with self.assertRaises(CompactedError):  # pre-backup watch positions must relist
            WatchHub(ds.store).create(start_revision=5)
        ds.store.put("after", 1)  # restored store is writable and durable
        ds.close()
        ds2 = DurableStore.open(os.path.join(self.dir, "restored"), sealer=self.ds)
        self.assertEqual(ds2.store.get("after").value, 1)
        ds2.close()

    def test_tampering_is_detected(self):
        b = create_backup(self.src, self.dir, sealer=self.bs, sign_key=self.key)
        mp = os.path.join(b["path"], "manifest.json")
        m = json.loads(readb(mp))
        m["revision"] = 1
        writeb(mp, json.dumps(m).encode())
        with self.assertRaises(CorruptionError):
            verify_backup(b["path"], sealer=self.bs, sign_key=self.key)
        b2 = create_backup(self.src, os.path.join(self.dir, "b2"), sealer=self.bs, sign_key=self.key)
        sp = os.path.join(b2["path"], "state.bin")
        data = bytearray(readb(sp))
        data[-3] ^= 1
        writeb(sp, bytes(data))
        with self.assertRaises(CorruptionError):
            verify_backup(b2["path"], sealer=self.bs, sign_key=self.key)
        with self.assertRaises(CorruptionError):
            verify_backup(b2["path"], sealer=self.bs, sign_key=b"x" * 32)

    def test_backup_keys_independent_of_data_keys(self):
        b = create_backup(self.src, self.dir, sealer=self.bs, sign_key=self.key)
        with self.assertRaises(CorruptionError):
            verify_backup(b["path"], sealer=self.ds, sign_key=self.key)

    def test_restore_never_overwrites_live_state(self):
        b = create_backup(self.src, self.dir, sealer=self.bs, sign_key=self.key)
        target = os.path.join(self.dir, "live")
        os.makedirs(target)
        writeb(os.path.join(target, "wal-0000000000000000.log"), b"x")
        with self.assertRaises(InvalidArgument):
            restore_backup(b["path"], target, backup_sealer=self.bs, sign_key=self.key, data_sealer=None)


class CompactionControllerTest(unittest.TestCase):
    def test_policy_margin_protection_watch_floor_and_rate(self):
        clock = FakeClock()
        s = ControlStore()
        hub = WatchHub(s)
        for i in range(100):
            s.put("k", i)
        slow = hub.create(start_revision=40)  # lagging live consumer at 40
        events = []
        c = CompactionController(s, retain_revisions=10, safety_margin=5, min_interval_s=60, clock=clock,
                                 watch_floor=lambda: min((w._resume_point() for w in hub._watchers.values()), default=None),
                                 on_compact=lambda r, n: events.append(r))
        c.run_once()
        self.assertEqual(s.compact_revision, 34)  # floor 40 - 1 - margin 5
        self.assertEqual(c.run_once(), 0)  # rate limited
        slow.cancel()
        s.protect("backup", 70)
        clock.advance(61)
        c.run_once()
        self.assertEqual(s.compact_revision, 70)
        s.unprotect("backup")
        clock.advance(61)
        c.run_once()
        self.assertEqual(s.compact_revision, 85)  # 100 - 10 - 5
        self.assertEqual(events, [34, 70, 85])

    def test_maintenance_window(self):
        s = ControlStore()
        for i in range(50):
            s.put("k", i)
        c = CompactionController(s, retain_revisions=5, safety_margin=0, min_interval_s=0, window=lambda: False)
        self.assertEqual(c.run_once(), 0)


class ReplicationTest(unittest.TestCase):
    def setUp(self):
        self.primary = ControlStore()
        self.src = ReplicationSource(self.primary, "site-a", epoch=1)
        self.follower = ControlStore()
        self.dst = ReplicaApplier(self.follower, "site-b", max_safe_lag=5)

    def test_ordered_apply_lag_and_idempotent_redelivery(self):
        for i in range(20):
            self.primary.txn((), [Put(f"k{i}", i), Put(f"j{i}", i)])
        self.assertEqual(sync_once(self.src, self.dst, max_events=7), 8)  # whole revisions only
        self.assertFalse(self.dst.safe_to_read())
        while self.follower.revision < self.primary.revision:
            sync_once(self.src, self.dst)
        self.assertTrue(self.dst.safe_to_read())
        self.assertEqual(self.follower.snapshot().to_dict(), self.primary.snapshot().to_dict())
        self.assertEqual(self.dst.apply(self.src.batch(1)), 0)  # duplicates ignored

    def test_gap_detected(self):
        for i in range(5):
            self.primary.put("k", i)
        b = self.src.batch(3)
        with self.assertRaises(InvalidArgument):
            self.dst.apply(b)

    def test_stale_epoch_fenced_after_failover(self):
        self.primary.put("k", 1)
        sync_once(self.src, self.dst)
        new_primary = ReplicationSource(self.follower, "site-b", epoch=2)  # promoted
        self.dst.epoch = 2
        with self.assertRaises(Fenced):
            self.dst.apply(self.src.batch(1))  # old primary's epoch 1
        with self.assertRaises(Fenced):
            self.src.hello({"schema": "cstate.repl_hello/1.0", "site": "site-b", "epoch": 2})
        self.assertEqual(new_primary.hello({"schema": "cstate.repl_hello/1.0", "epoch": 1})["epoch"], 2)

    def test_resync_after_compaction(self):
        for i in range(10):
            self.primary.put("k", i)
        self.primary.compact(8)
        self.assertEqual(sync_once(self.src, self.dst), -1)  # snapshot resync
        self.assertEqual(self.follower.get("k").value, 9)
        self.primary.put("k", 10)
        sync_once(self.src, self.dst)
        self.assertEqual(self.follower.get("k").value, 10)


if __name__ == "__main__":
    unittest.main()
