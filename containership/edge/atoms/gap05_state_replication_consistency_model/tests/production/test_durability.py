import json
import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest

import _util
from gap05_state_replication_consistency_model.production import errors as E
from gap05_state_replication_consistency_model.production.durable import (HEADER, SnapshotStore,
                                                                          WriteAheadLog)
from gap05_state_replication_consistency_model.production.lifecycle import (backup, migrate_snapshot_dir,
                                                                            migrate_state, restore, verify_backup)
from gap05_state_replication_consistency_model.production.anti_entropy import reconcile
from gap05_state_replication_consistency_model.production.testkit import Cluster, E as ENV, T


class WalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.tmp.name) / "wal.log"

    def tearDown(self):
        self.tmp.cleanup()

    def test_framing_and_sequence(self):
        """items: MC04-001 MC04-002 MC24-001
        Records carry format, sequence, kind, sha256 framing; reopen yields identical records."""
        w = WriteAheadLog(self.path)
        for i in range(5):
            w.append("apply", {"i": i})
        w.close()
        w2 = WriteAheadLog(self.path)
        self.assertEqual([r["seq"] for r in w2.records], [1, 2, 3, 4, 5])
        self.assertTrue(all(r["format"] == "GAP05_WAL/1" for r in w2.records))
        self.assertEqual(w2.next_seq, 6)

    def test_torn_tail_truncated_prior_kept(self):
        """items: MC04-005 MC35-005 MC04-010
        Every possible torn-tail length is truncated; all prior records survive."""
        w = WriteAheadLog(self.path)
        for i in range(3):
            w.append("apply", {"i": i})
        w.close()
        full = self.path.read_bytes()
        rec3 = full.rfind(b"G5WL")
        for cut in range(rec3 + 1, len(full)):
            self.path.write_bytes(full[:cut])
            w = WriteAheadLog(self.path)
            self.assertEqual(len(w.records), 2, cut)
            self.assertGreater(w.recovery_report["truncated_bytes"], 0)
            w.close()

    def test_mid_log_corruption_fails_closed(self):
        """items: MC04-005 MC05-007 MC35-007
        A corrupted record followed by valid records is corruption, not a torn tail."""
        w = WriteAheadLog(self.path)
        for i in range(3):
            w.append("apply", {"i": i})
        w.close()
        data = bytearray(self.path.read_bytes())
        data[HEADER.size + 5] ^= 0xFF
        self.path.write_bytes(bytes(data))
        with self.assertRaises(E.IntegrityError) as cm:
            WriteAheadLog(self.path)
        self.assertEqual(cm.exception.code, "CORR_WAL_CORRUPT")

    def test_compaction_keeps_uncovered(self):
        """items: MC04-007 MC04-008 MC05-009
        Compaction drops only records covered by the snapshot sequence."""
        w = WriteAheadLog(self.path)
        for i in range(6):
            w.append("apply", {"i": i})
        w.compact_before(4)
        self.assertEqual([r["seq"] for r in w.records], [5, 6])
        w.close()
        self.assertEqual([r["seq"] for r in WriteAheadLog(self.path).records], [5, 6])


class SnapshotTests(unittest.TestCase):
    def test_atomic_validated_fallback(self):
        """items: MC05-001 MC05-003 MC05-004 MC05-006 MC05-007 MC05-011
        A corrupted newest snapshot falls back to the previous valid generation."""
        with tempfile.TemporaryDirectory() as d:
            s = SnapshotStore(pathlib.Path(d))
            s.write(1, 10, {"x": 1})
            p2 = s.write(2, 20, {"x": 2})
            p2.write_bytes(p2.read_bytes()[:-5])
            body, rejected = s.latest_valid()
            self.assertEqual(body["generation"], 1)
            self.assertEqual(rejected[0]["generation"], 2)
            self.assertFalse(list(pathlib.Path(d).glob("*.tmp")))

    def test_restore_rejects_dominated_frontier(self):
        """items: MC05-005 MC33-006
        Restoring a frontier containing a causally dominated write is refused by the core invariant check."""
        from gap05_state_replication_consistency_model.model import ReplicatedKey, Write
        with self.assertRaises(ValueError):
            ReplicatedKey("k", frozenset("ab"), siblings=[Write("k", "1", "a", (("a", 1),)),
                                                          Write("k", "2", "a", (("a", 2),))])


class NodeRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.c = Cluster(("a", "b"))

    def tearDown(self):
        self.c.close()

    def test_snapshot_plus_wal_restores_same_state(self):
        """items: MC04-004 MC05-002 MC05-008 MC05-012 MC05-009
        Checkpoint mid-stream + residual WAL reproduces conflicts and quarantine exactly."""
        a, b = self.c.nodes["a"], self.c.nodes["b"]
        for i in range(12):
            a.write(T, ENV, f"k{i}", f"a{i}", principal="operator")
            b.write(T, ENV, f"k{i}", f"b{i}", principal="operator")
        reconcile(a, b, T, ENV, principal_a=self.c.principal("a"), principal_b=self.c.principal("b"))
        a.checkpoint()
        a.write(T, ENV, "late", "x", principal="operator")
        before = {k: a.conflict_set(*k.split("\x1f")) for k in a.state_keys()}
        a2 = self.c.reopen("a")
        after = {k: a2.conflict_set(*k.split("\x1f")) for k in a2.state_keys()}
        self.assertEqual(before, after)
        self.assertEqual(a2.recovery_report["replayed"], 1)

    def test_duplicate_across_restart(self):
        """items: MC09-001 MC09-003 MC09-011 MC09-012 MC04-005
        Exact replay after restart and checkpoint is idempotent (duplicate or superseded, never re-applied)."""
        a, b = self.c.nodes["a"], self.c.nodes["b"]
        r = b.write(T, ENV, "k", "v", principal="operator")
        doc = b.docs[r["op_id"]]
        self.assertEqual(a.submit(doc, principal=self.c.principal("b"), relay=True)["outcome"], "converged")
        a = self.c.reopen("a")
        self.assertEqual(a.submit(doc, principal=self.c.principal("b"), relay=True)["outcome"], "duplicate")
        a.checkpoint()
        a = self.c.reopen("a")
        self.assertEqual(a.submit(doc, principal=self.c.principal("b"), relay=True)["outcome"], "duplicate")
        wal_before = len(a.wal.records)
        a.submit(doc, principal=self.c.principal("b"), relay=True)
        self.assertEqual(len(a.wal.records), wal_before)

    def test_equivocation_detected_and_audited(self):
        """items: MC09-004 MC09-005 MC03-005 MC34-006
        Same author counter reused for different content is rejected as equivocation."""
        from gap05_state_replication_consistency_model.production.protect import sign_write
        from gap05_state_replication_consistency_model.production.schemas import make_write_doc
        a = self.c.nodes["a"]
        kb = self.c.keys["b"].private_key
        d1 = sign_write(make_write_doc(tenant=T, environment=ENV, key="k", value="1", site="b", vector={"b": 1},
                                       epoch=1), kb)
        d2 = sign_write(make_write_doc(tenant=T, environment=ENV, key="k", value="2", site="b", vector={"b": 1},
                                       epoch=1), kb)
        a.submit(d1, principal=self.c.principal("b"), relay=True)
        with self.assertRaises(E.SecurityError) as cm:
            a.submit(d2, principal=self.c.principal("b"), relay=True)
        self.assertEqual(cm.exception.code, "SEC_COUNTER_EQUIVOCATION")
        self.assertEqual(a.guard.evidence[-1]["kind"], "equivocation")
        self.assertIn(b"SEC_COUNTER_EQUIVOCATION", "\n".join(a.log.lines).encode())


CRASH_SCRIPT = textwrap.dedent("""
    import sys, pathlib, json
    sys.path.insert(0, {root!r})
    from gap05_state_replication_consistency_model.production.testkit import Cluster, T, E
    c = Cluster(("a",), root=pathlib.Path({dir!r}))
    n = c.nodes["a"]
    acked = pathlib.Path({dir!r}) / "acked.jsonl"
    i = len(acked.read_text().splitlines()) if acked.exists() else 0
    for j in range(i, i + 5):
        r = n.write(T, E, f"k{{j}}", f"v{{j}}", principal="operator")
        with open(acked, "a") as fh:
            fh.write(json.dumps([f"k{{j}}", f"v{{j}}"]) + "\\n")
        if j == i + 2:
            n.checkpoint()
""")


class CrashInjectionTests(unittest.TestCase):
    POINTS = ["wal_before_write", "wal_mid_write", "wal_before_fsync", "wal_after_fsync",
              "atomic_before_fsync", "atomic_before_replace", "node_after_wal_before_audit"]

    def test_crash_matrix_no_acked_loss(self):
        """items: MC04-011 MC04-012 MC04-003 MC35-001 MC35-002 MC35-003 MC35-004 MC35-006 MC35-009 MC35-012 MC05-011
        Real process kill (os._exit) at every persistence boundary, three crash cycles each; every
        write acknowledged before the kill is present after recovery from durable files only."""
        root = str(_util.ROOT)
        for point in self.POINTS:
            with self.subTest(point=point), tempfile.TemporaryDirectory() as d:
                # NOTE: a fresh Cluster generates fresh keys; the crash runs reuse one directory per
                # point but membership + keys come from the first run's files -> use one process that
                # persists keys: simplest faithful approach is one Cluster per process with fixed root,
                # and verification by reading WAL/snapshot directly (no harness repair of state).
                crashes = 0
                for cycle in range(3):
                    env = dict(os.environ, GAP05_CRASH_AT=point if cycle < 2 else "")
                    p = subprocess.run([sys.executable, "-c", CRASH_SCRIPT.format(root=root, dir=d)],
                                       env=env, capture_output=True, timeout=120)
                    crashes += p.returncode == 77
                    self.assertIn(p.returncode, (0, 77), p.stderr.decode()[-800:])
                from gap05_state_replication_consistency_model.production.cli import inspect
                acked = [json.loads(l) for l in (pathlib.Path(d) / "acked.jsonl").read_text().splitlines()] \
                    if (pathlib.Path(d) / "acked.jsonl").exists() else []
                state = inspect(pathlib.Path(d) / "a" / "data")
                present = {k.split("/")[-1] for k in state["keys"]}
                for key, _v in acked:
                    self.assertIn(key, present, f"acked write {key} lost at crash point {point}")
                self.assertGreaterEqual(crashes, 1, f"crash point {point} never triggered")
                # every write present in durable state has an audit record (no crash-window gap)
                audit_ops = set()
                for seg in (pathlib.Path(d) / "a" / "data" / "audit").glob("audit-*.jsonl"):
                    for line in seg.read_text().splitlines():
                        rec = json.loads(line)
                        if rec["event"] in ("apply", "apply_recovered"):
                            audit_ops.add(rec["op_id"])
                wal_ops = set()
                from gap05_state_replication_consistency_model.production.cli import _load_docs
                for doc in _load_docs(pathlib.Path(d) / "a" / "data")[0]:
                    wal_ops.add(doc["op_id"])
                self.assertLessEqual(wal_ops, audit_ops, f"unaudited durable writes at {point}")


AUDIT_GAP_SCRIPT = textwrap.dedent("""
    import sys, pathlib
    sys.path.insert(0, {root!r})
    from gap05_state_replication_consistency_model.production.testkit import Cluster, T, E
    c = Cluster(("a",), root=pathlib.Path({dir!r}))
    c.nodes["a"].write(T, E, "k", "v", principal="operator")
""")


class AuditCrashWindowTests(unittest.TestCase):
    def test_wal_durable_write_is_audited_after_crash(self):
        """items: MC10-009 MC35-001 MC35-002 MC04-010
        Kill between WAL fsync and audit append; recovery back-fills the audit record."""
        with tempfile.TemporaryDirectory() as d:
            env = dict(os.environ, GAP05_CRASH_AT="node_after_wal_before_audit")
            p = subprocess.run([sys.executable, "-c", AUDIT_GAP_SCRIPT.format(root=str(_util.ROOT), dir=d)],
                               env=env, capture_output=True, timeout=120)
            self.assertEqual(p.returncode, 77, p.stderr.decode()[-500:])
            c = Cluster(("a",), root=pathlib.Path(d))
            try:
                n = c.nodes["a"]
                self.assertEqual(n.recovery_report["audit_backfilled"], 1)
                wal_op = n.wal.records[-1]["body"]["doc"]["op_id"]
                events = [json.loads(l) for seg in (n.dir / "audit").glob("audit-*.jsonl")
                          for l in seg.read_text().splitlines()]
                self.assertIn(("apply_recovered", wal_op), {(e["event"], e.get("op_id")) for e in events})
                again = c.reopen("a")
                self.assertEqual(again.recovery_report["audit_backfilled"], 0)  # idempotent
            finally:
                c.close()


class BackupMigrationTests(unittest.TestCase):
    def test_backup_verify_restore_fenced_until_sync(self):
        """items: MC25-001 MC25-002 MC25-004 MC25-005 MC25-006 MC25-009 MC25-012 MC09-010 MC03-007
        Backup -> verify -> restore into an empty dir; restored node refuses to author until reconciled."""
        c = Cluster(("a", "b"))
        try:
            a, b = c.nodes["a"], c.nodes["b"]
            a.write(T, ENV, "k", "v1", principal="operator")
            reconcile(a, b, T, ENV, principal_a=c.principal("a"), principal_b=c.principal("b"))
            bdir = c.root / "backup"
            backup(a, bdir, membership_dir=c.membership_dirs["a"])
            verify_backup(bdir, c.keys["a"].private_key.public_key())
            b.write(T, ENV, "k", "v2", principal="operator")   # progress after the backup point
            a.close()
            import shutil
            shutil.rmtree(a.dir)
            restore(bdir, a.dir, audit_public_key=c.keys["a"].private_key.public_key())
            a2 = c.open("a")
            c.nodes["a"] = a2
            self.assertTrue(a2.recovery_mode)
            self.assertFalse(a2.health()["ready"])
            with self.assertRaises(E.IntegrityError) as cm:
                a2.write(T, ENV, "k", "stale", principal="operator")
            self.assertEqual(cm.exception.code, "CORR_RECOVERY_MODE")
            r = reconcile(a2, b, T, ENV, principal_a=c.principal("a"), principal_b=c.principal("b"))
            self.assertTrue(r["converged"])
            self.assertFalse(a2.recovery_mode)
            self.assertEqual(a2.read(T, ENV, "k", principal="operator")["value"], "v2")
            w = a2.write(T, ENV, "k", "v3", principal="operator")
            self.assertEqual(w["outcome"], "converged")
        finally:
            c.close()

    def test_backup_tamper_detected(self):
        """items: MC25-011 MC25-003
        A modified file in a backup set fails verification before restore touches anything."""
        c = Cluster(("a",))
        try:
            c.nodes["a"].write(T, ENV, "k", "v", principal="operator")
            bdir = c.root / "backup"
            backup(c.nodes["a"], bdir, membership_dir=c.membership_dirs["a"])
            snap = sorted((bdir / "snapshots").glob("*.json"))[-1]
            snap.write_bytes(snap.read_bytes().replace(b'"v"', b'"X"'))
            with self.assertRaises(E.IntegrityError):
                restore(bdir, c.root / "fresh", audit_public_key=c.keys["a"].private_key.public_key())
            self.assertFalse((c.root / "fresh").exists())
        finally:
            c.close()

    def test_migration_v1_to_v2_and_downgrade_refused(self):
        """items: MC24-001 MC24-002 MC24-004 MC24-005 MC24-006 MC24-010 MC24-012
        Format-1 snapshot migrates (backup kept, dry-run first); a future format is refused."""
        with tempfile.TemporaryDirectory() as d:
            s = SnapshotStore(pathlib.Path(d))
            s.write(1, 0, {"state_format": 1, "writes": [
                {"key": "k", "value": "a", "site": "a", "vector": [["a", 1]]},
                {"key": "k", "value": "b", "site": "b", "vector": [["b", 1]]}]})
            dry = migrate_snapshot_dir(pathlib.Path(d), dry_run=True, tenant=T, environment=ENV)
            self.assertEqual(dry[0]["action"], "1->2")
            self.assertEqual(s.latest_valid()[0]["state"]["state_format"], 1)
            migrate_snapshot_dir(pathlib.Path(d), tenant=T, environment=ENV)
            body = s.latest_valid()[0]
            self.assertEqual(body["state"]["state_format"], 2)
            self.assertEqual(len(body["state"]["frontier"]), 2)
            self.assertTrue(list(pathlib.Path(d).glob("*.pre-migration-v1")))
            again = migrate_snapshot_dir(pathlib.Path(d), tenant=T, environment=ENV)
            self.assertEqual(again[0]["action"], "none")  # idempotent re-run
        with self.assertRaises(E.IntegrityError) as cm:
            migrate_state({"state_format": 3})
        self.assertEqual(cm.exception.code, "CORR_DOWNGRADE_REFUSED")
        with self.assertRaises(TypeError):
            migrate_state({"state_format": 1, "writes": []})  # namespace must be named, never guessed


if __name__ == "__main__":
    unittest.main()
