"""Durability, crash consistency, fencing, backup/restore (components 44, 45, 47, 48, 77, 83)."""
from __future__ import annotations

import json
import os
import unittest

from _support import TmpDirCase
from inv53_message_reliability.durable import (CorruptStoreError, DurableQueue, EpochFencedError, OwnershipError,
                                               StorageError, restore)
from inv53_message_reliability.reliability import DuplicateMessageError, QueueCapacityError


class Crash(OSError):
    pass


class DurableTest(TmpDirCase):
    def q(self, **kw):
        kw.setdefault("visibility", 5)
        kw.setdefault("max_attempts", 3)
        return DurableQueue(self.tmp / "q", **kw)

    def test_messages_survive_restart(self):
        with self.q() as q:
            for i in range(5):
                q.put({"id": f"m{i}", "n": i})
            d = q.receive(now=0)
            self.assertTrue(q.ack(d, now=1))
        with self.q() as q:
            self.assertEqual(q.snapshot()["ready"], 4)
            self.assertEqual(q.snapshot()["acks"], 1)
            self.assertEqual(q.receive(now=2).message_id, "m1")

    def test_lease_survives_restart_and_is_not_redelivered_early(self):
        with self.q() as q:
            q.put({"id": "a"})
            first = q.receive(now=0)
        with self.q() as q:
            self.assertIsNone(q.receive(now=4.9), "lease must be honoured across restart")
            again = q.receive(now=5)
            self.assertEqual(again.attempt, 2)
            self.assertFalse(q.ack(first, now=5), "pre-crash lease is superseded")
            self.assertTrue(q.ack(again, now=5))

    def crash(self, q):
        """Abandon a queue the way a killed process does: no clean-shutdown marker is written."""
        q._jfh.close()
        q._oslock.release()

    def test_torn_final_record_is_truncated_and_reported(self):
        q = self.q()
        q.put({"id": "a"})
        q.put({"id": "b"})
        self.crash(q)
        j = self.tmp / "q" / "journal.jsonl"
        with open(j, "ab") as fh:
            fh.write(b'{"seq": 99, "op": "put", "a": {"msg": {"id": "ha')   # crash mid-append
        with self.q() as q:
            self.assertTrue(any("torn" in n for n in q.recovery_notes))
            self.assertEqual(q.snapshot()["ready"], 2)
            q.put({"id": "c"})
        with self.q() as q:
            self.assertEqual(q.snapshot()["ready"], 3)

    def test_mid_journal_corruption_refuses_to_open(self):
        with self.q() as q:
            for i in range(3):
                q.put({"id": f"m{i}"})
        j = self.tmp / "q" / "journal.jsonl"
        lines = j.read_bytes().split(b"\n")
        lines[2] = lines[2].replace(b'"m1"', b'"mX"')
        j.write_bytes(b"\n".join(lines))
        with self.assertRaises(CorruptStoreError):
            self.q()

    def test_deleted_record_detected(self):
        with self.q() as q:
            for i in range(3):
                q.put({"id": f"m{i}"})
        j = self.tmp / "q" / "journal.jsonl"
        lines = j.read_bytes().split(b"\n")
        del lines[2]
        j.write_bytes(b"\n".join(lines))
        with self.assertRaises(CorruptStoreError):
            self.q()

    def test_write_failure_before_write_fail_stops_and_loses_nothing(self):
        armed = {"on": False}

        def fault(point, op):
            if armed["on"] and point == "before_write" and op == "ack":
                raise Crash("disk full")
        q = self.q(fault=fault)
        q.put({"id": "a"})
        d = q.receive(now=0)
        armed["on"] = True
        with self.assertRaises(StorageError):
            q.ack(d, now=1)
        with self.assertRaises(StorageError, msg="fail-stop: no further ops on untrusted memory"):
            q.put({"id": "b"})
        q.close()
        with self.q() as q2:
            self.assertEqual(q2.snapshot()["in_flight"], 1, "ack never reached disk, message still owned by broker")

    def test_crash_after_write_is_recovered_by_replay(self):
        armed = {"on": False}

        def fault(point, op):
            if armed["on"] and point == "after_write" and op == "ack":
                raise Crash("power loss after fsync")
        q = self.q(fault=fault)
        q.put({"id": "a"})
        d = q.receive(now=0)
        armed["on"] = True
        with self.assertRaises(StorageError):
            q.ack(d, now=1)
        q.close()
        with self.q() as q2:
            s = q2.snapshot()
            self.assertEqual((s["in_flight"], s["acks"]), (0, 1), "the durable ack is the truth after replay")

    def test_idempotent_put_after_indeterminate_failure(self):
        with self.q() as q:
            self.assertTrue(q.put({"id": "a", "v": 1}))
            self.assertFalse(q.put({"id": "a", "v": 1}))
            with self.assertRaises(DuplicateMessageError):
                q.put({"id": "a", "v": 2})

    def test_second_live_writer_is_refused(self):
        q = self.q()
        with self.assertRaises(OwnershipError):
            self.q()
        q.close()
        self.q().close()

    def test_epoch_fencing_refuses_superseded_writer(self):
        q = self.q()
        q.put({"id": "a"})
        # Simulate another host taking ownership on shared storage where the OS lock is not honoured.
        tmp = self.tmp / "q" / "EPOCH.new"
        tmp.write_text(str(q.epoch + 1))
        os.replace(tmp, self.tmp / "q" / "EPOCH")         # owners always publish epochs atomically
        with self.assertRaises(EpochFencedError):
            q.put({"id": "b"})
        q.close()

    def test_epoch_fencing_holds_when_stat_identity_is_unchanged(self):
        """Adversarial-review defect 3: an in-place epoch rewrite with the old mtime must still fence."""
        q = self.q()
        q.put({"id": "a"})
        p = self.tmp / "q" / "EPOCH"
        st = os.stat(p)
        with open(p, "r+") as fh:            # same inode, same size
            fh.write(str(q.epoch + 1)[: st.st_size].rjust(st.st_size, "9"))
        os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
        with self.assertRaises(EpochFencedError):
            q.put({"id": "b"})
        q.close()

    def test_closed_failed_or_fenced_writer_cannot_compact_or_back_up(self):
        """Adversarial re-review R1/R2: compaction from a stale or untrusted writer rewrote the store."""
        q1 = self.q()
        q1.put({"id": "a"})
        q1.close()
        q2 = self.q()
        self.assertTrue(q2.put({"id": "b"}))
        with self.assertRaises(StorageError):
            q1.compact()
        q2.close()
        with self.q() as r:
            self.assertEqual(r.snapshot()["ready"], 2)
        arm = {"on": False}

        def fault(p, op):
            if arm["on"] and p == "after_write" and op == "ack":
                raise Crash("x")
        q = self.q(fault=fault)
        d = q.receive(now=0)
        arm["on"] = True
        with self.assertRaises(StorageError):
            q.ack(d, now=1)                        # ack is durable, writer fail-stopped
        with self.assertRaises(StorageError):
            q.backup(self.tmp / "bk")
        q.close()
        with self.q() as r:
            self.assertEqual((r.snapshot()["in_flight"], r.snapshot()["acks"]), (0, 1), "the durable ack survives")

    def test_compaction_and_replay_equivalence(self):
        with self.q(compact_every=4) as q:
            for i in range(10):
                q.put({"id": f"m{i}"})
            d = q.receive(now=0)
            q.ack(d, now=0)
            digest = q.state_digest()
        self.assertTrue((self.tmp / "q" / "snapshot.json").exists())
        with self.q() as q:
            self.assertEqual(q.state_digest(), digest)

    def test_snapshot_tamper_detected(self):
        with self.q() as q:
            q.put({"id": "a"})
            q.compact()
        p = self.tmp / "q" / "snapshot.json"
        doc = json.loads(p.read_text())
        doc["state"]["msgs"]["a"]["evil"] = 1
        p.write_text(json.dumps(doc))
        with self.assertRaises(CorruptStoreError):
            self.q()

    def test_backup_restore_roundtrip_and_tamper(self):
        with self.q() as q:
            for i in range(4):
                q.put({"id": f"m{i}"})
            q.receive(now=0)
            man = q.backup(self.tmp / "bk")
            digest = q.state_digest()
        r = restore(self.tmp / "bk", self.tmp / "restored", visibility=5, max_attempts=3)
        self.assertEqual(r.state_digest(), digest)
        self.assertEqual(man["state_digest"], digest)
        r.close()
        (self.tmp / "bk" / "journal.jsonl").write_bytes(b"x")
        with self.assertRaises(CorruptStoreError):
            restore(self.tmp / "bk", self.tmp / "restored2", visibility=5, max_attempts=3)

    def test_restore_refuses_non_empty_target(self):
        with self.q() as q:
            q.put({"id": "a"})
            q.backup(self.tmp / "bk")
        (self.tmp / "busy").mkdir()
        (self.tmp / "busy" / "x").write_text("x")
        with self.assertRaises(Exception):
            restore(self.tmp / "bk", self.tmp / "busy")

    def test_dead_letter_redrive_and_purge_are_durable(self):
        with self.q(max_attempts=1) as q:
            q.put({"id": "p"})
            q.put({"id": "r"})
            q.receive(now=0)
            q.receive(now=0)
            q.expire(now=10)
            self.assertEqual(len(q.dlq), 2)
            self.assertTrue(q.redrive("p", now=11))
            self.assertTrue(q.purge_dead_letter("r"))
            self.assertFalse(q.redrive("nope", now=11))
        with self.q(max_attempts=1) as q:
            s = q.snapshot()
            self.assertEqual((s["ready"], s["dead_lettered"], s["redrives"], s["purges"]), (1, 0, 1, 1))
            d = q.receive(now=12)
            self.assertEqual(d.attempt, 1, "redrive grants a fresh attempt budget")

    def test_capacity_refusal_changes_nothing(self):
        with self.q(max_ready=2) as q:
            q.put({"id": "a"})
            q.put({"id": "b"})
            before = q.state_digest()
            with self.assertRaises(QueueCapacityError):
                q.put({"id": "c"})
            self.assertEqual(q.state_digest(), before)

    def test_message_size_limit(self):
        with self.q(max_message_bytes=100) as q:
            with self.assertRaises(QueueCapacityError):
                q.put({"id": "big", "x": "y" * 200})

    def test_explain_view(self):
        with self.q(max_attempts=1) as q:
            q.put({"id": "a"})
            q.put({"id": "b"})
            self.assertEqual(q.explain("b")["state"], "ready")
            q.receive(now=0)
            self.assertEqual(q.explain("a")["state"], "in_flight")
            q.expire(now=6)
            self.assertEqual(q.explain("a")["reason"], "visibility_timeout")
            self.assertEqual(q.explain("zzz")["state"], "unknown_or_settled")

    def test_unknown_schema_snapshot_refused(self):
        with self.q() as q:
            q.put({"id": "a"})
            q.compact()
        p = self.tmp / "q" / "snapshot.json"
        doc = json.loads(p.read_text())
        doc["schema"] = "inv53.store/999"
        import hashlib
        from inv53_message_reliability.durable import _canon
        body = {k: doc[k] for k in ("schema", "seq", "head", "state")}
        doc["digest"] = hashlib.sha256(_canon(body)).hexdigest()
        p.write_text(json.dumps(doc))
        with self.assertRaises(CorruptStoreError):
            self.q()

    def test_tail_removal_after_clean_shutdown_is_detected(self):
        """Adversarial-review defect 2: dropping or re-tearing the last complete record must not pass silently."""
        for mode in ("drop_last_line", "tamper_and_strip_newline"):
            with self.subTest(mode):
                d = self.tmp / mode
                with DurableQueue(d) as q:
                    q.put({"id": "a"})
                    self.assertTrue(q.put({"id": "b"}))
                j = d / "journal.jsonl"
                lines = j.read_bytes().rstrip(b"\n").split(b"\n")
                if mode == "drop_last_line":
                    j.write_bytes(b"\n".join(lines[:-1]) + b"\n")
                else:
                    j.write_bytes(b"\n".join(lines[:-1] + [lines[-1].replace(b'"b"', b'"B"')]))
                with self.assertRaises(CorruptStoreError):
                    DurableQueue(d)

    def test_external_anchor_detects_tail_loss_after_a_crash(self):
        q = self.q()
        q.put({"id": "a"})
        q.put({"id": "b"})
        anchor = q.head()
        self.crash(q)
        j = self.tmp / "q" / "journal.jsonl"
        lines = j.read_bytes().rstrip(b"\n").split(b"\n")
        j.write_bytes(b"\n".join(lines[:-1]) + b"\n")
        with self.assertRaises(CorruptStoreError):
            self.q(anchored_head=anchor)
        q2 = self.q()          # without an anchor the loss is invisible -- and reported as unprovable
        self.assertTrue(any("external anchor" in n for n in q2.recovery_notes))
        q2.close()

    def test_crash_between_snapshot_and_journal_reset_recovers(self):
        """Adversarial-review defect 1: a crash inside compact() must not brick the store."""
        import inv53_message_reliability.durable as D
        q = self.q()
        for i in range(5):
            q.put({"id": f"m{i}"})
        digest = q.state_digest()
        real = D._atomic_write

        def failing(path, data):
            if path.name == "journal.jsonl":
                raise OSError("crash after snapshot, before journal reset")
            return real(path, data)
        D._atomic_write = failing
        try:
            with self.assertRaises(StorageError):
                q.compact()
            with self.assertRaises(StorageError):
                q.put({"id": "refused"})      # fail-stopped, not writing into a closed file
        finally:
            D._atomic_write = real
        self.crash(q)
        with self.q() as r:
            self.assertEqual(r.state_digest(), digest)
            self.assertTrue(any("folded into the snapshot" in n for n in r.recovery_notes))
            r.put({"id": "after"})
        with self.q() as r:
            self.assertEqual(r.snapshot()["ready"], 6)

    def test_compaction_failure_inside_append_fail_stops(self):
        import inv53_message_reliability.durable as D
        q = self.q(compact_every=3)
        real = D._atomic_write
        D._atomic_write = lambda path, data: (_ for _ in ()).throw(OSError("disk full"))
        try:
            with self.assertRaises(StorageError):
                q.put({"id": "a"})     # epoch record is seq 1; this put is seq 2 ...
                q.put({"id": "b"})     # ... seq 3 triggers compaction
        finally:
            D._atomic_write = real
        with self.assertRaises(StorageError):
            q.put({"id": "c"})
        self.crash(q)
        with self.q() as r:
            self.assertEqual(r.snapshot()["ready"], 2, "both durable puts survive the failed compaction")


if __name__ == "__main__":
    unittest.main()
