"""P0 durable store, ledger, concurrency, audit, recovery, backup (components 01, 02, 11, 12, 15, 37, 38, 47)."""
import os
import sqlite3
import subprocess
import sys
import threading
import unittest

from fixtures import PART, PART2, T0, World, art
from gap15_runtime_compatibility_certification.production import store as store_mod
from gap15_runtime_compatibility_certification.production.canonical import canonical_bytes
from gap15_runtime_compatibility_certification.production.signing import b64d, b64e
from gap15_runtime_compatibility_certification.production import ed25519
from gap15_runtime_compatibility_certification.production.state import CertKey, replay

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def ev(i, part=PART, result="compatible", at=T0, digest=None, runtime="wasmtime@21.0.0", profile="profile:p"):
    return {"event_id": f"e{i}", "evidence_id": f"e{i}", "event_type": "evidence", "partition": part,
            "artifact_digest": digest or art(i), "runtime": runtime, "profile_id": profile, "result": result,
            "observed_at": at, "producer": "producer-a", "idem_key": f"producer-a|{i}", "payload_digest": f"d{i}"}


def audit(i):
    return {"event_id": f"a{i}", "action": "test"}


class DurableStoreTest(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.s = self.w.store

    def test_persistence_model_columns(self):
        """controls: 01-01 01-04"""
        cols = {r[1] for r in self.s.db.execute("PRAGMA table_info(matrix)")}
        for c in ("partition", "artifact_digest", "runtime", "profile_id", "result", "evidence_id", "matrix_revision",
                  "created_seq", "updated_seq", "tombstone"):
            self.assertIn(c, cols)
        lcols = {r[1] for r in self.s.db.execute("PRAGMA table_info(ledger)")}
        self.assertTrue({"signer", "observed_at", "recorded_at", "idem_key"} <= lcols)

    def test_engine_settings_wal_full_sync(self):
        """controls: 01-02 01-07"""
        self.assertEqual(self.s.db.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        self.assertEqual(self.s.db.execute("PRAGMA synchronous").fetchone()[0], 2)  # FULL

    def test_cas_rejects_lost_update(self):
        """controls: 01-03 11-01 11-02 11-04"""
        r1 = self.s.commit([ev(1)], audit=[audit(1)], expected_revision=0)
        self.assertEqual(r1.revision, 1)
        with self.assertRaises(store_mod.Conflict) as cm:
            self.s.commit([ev(2)], audit=[audit(2)], expected_revision=0)
        self.assertEqual((cm.exception.expected, cm.exception.current), (0, 1))
        self.assertEqual(self.s.revision, 1)

    def test_indexed_historical_lookup_uses_partition_leading_index(self):
        """controls: 01-04 01-09 25-03 32-05"""
        self.s.commit([ev(1), ev(2, part=PART2)], audit=[audit(1)])
        plan = " ".join(self.s.query_plan("SELECT seq FROM ledger WHERE partition=? AND signer=?", (PART, "k")))
        self.assertRegex(plan, r"USING (COVERING )?INDEX ledger_by_signer")
        self.assertEqual([e["event_id"] for e in self.s.lookup(PART)], ["e1"])
        self.assertEqual([e["event_id"] for e in self.s.lookup(PART2)], ["e2"])
        with self.assertRaises(store_mod.StoreError):
            self.s.lookup("")
        self.assertEqual(len(self.s.lookup(PART, limit=10**9)), 1)  # limit clamped, no unbounded scan

    def test_atomic_commit_fault_at_every_stage_leaves_no_partial_state(self):
        """controls: 01-05 10-05 38-01"""
        for stage in ("before_ledger_append", "after_ledger_append", "before_revision_update", "before_audit", "before_commit"):
            w = World(fault_hook=lambda s, stage=stage: (_ for _ in ()).throw(RuntimeError("crash")) if s == stage else None)
            with self.assertRaises(RuntimeError):
                w.store.commit([ev(1)], audit=[audit(1)])
            s2 = store_mod.Store(w.db_path)
            self.assertEqual((s2.revision, s2.head("ledger")[0], s2.head("audit")[0]), (0, 0, 0), stage)
            self.assertEqual(s2.db.execute("SELECT COUNT(*) FROM matrix").fetchone()[0], 0)

    def test_process_kill_mid_transaction_recovers(self):
        """controls: 01-07 15-03 38-01 38-09"""
        path = os.path.join(self.w.tmp, "kill.db")
        code = (
            "import sys,os; sys.path.insert(0,%r);"
            "from gap15_runtime_compatibility_certification.production import store as s;"
            "st=s.Store(%r, fault_hook=lambda stage: os._exit(9) if stage=='before_commit' else None);"
            "st.fault_hook=lambda stage: None; st.commit([%r],audit=[{'event_id':'a0','action':'x'}]);"
            "st.fault_hook=lambda stage: os._exit(9) if stage=='before_commit' else None;"
            "st.commit([%r],audit=[{'event_id':'a1','action':'x'}])"
        ) % (ROOT, path, ev(1), ev(2))
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(r.returncode, 9, r.stderr)
        s2 = store_mod.Store(path)
        self.assertEqual(s2.revision, 1)
        self.assertEqual(s2.recover()["events"], 1)

    def test_forward_only_migration_and_downgrade_refusal(self):
        """controls: 01-06 15-06 47-05 47-06 44-09"""
        path = os.path.join(self.w.tmp, "old.db")
        s = store_mod.Store.__new__(store_mod.Store)
        s.db = sqlite3.connect(path, isolation_level=None)
        s._lock = threading.RLock()
        s.fault_hook = lambda stage: None
        s.migrate(target=1)
        self.assertEqual(s.schema_version(), 1)
        self.assertEqual([m[0] for m in s.migrate(dry_run=True)], [2, 3])
        s.db.close()
        full = store_mod.Store(path)
        self.assertEqual(full.schema_version(), store_mod.SCHEMA_VERSION)
        full.db.execute("UPDATE meta SET v='99' WHERE k='schema_version'")
        with self.assertRaises(store_mod.StoreError) as cm:
            store_mod.Store(path)
        self.assertEqual(cm.exception.code, "E_SCHEMA_TOO_NEW")

    def test_interrupted_migration_rolls_back(self):
        """controls: 01-07 47-06"""
        path = os.path.join(self.w.tmp, "mig.db")

        def hook(stage):
            if stage == "migration:2":
                raise RuntimeError("power loss")
        with self.assertRaises(RuntimeError):
            store_mod.Store(path, fault_hook=hook)
        s = store_mod.Store(path)
        self.assertEqual(s.schema_version(), store_mod.SCHEMA_VERSION)

    def test_disk_full_style_io_failure_fails_closed(self):
        """controls: 01-07 38-02"""
        self.s.db.execute("PRAGMA max_page_count=1")  # simulate a full volume for new pages
        with self.assertRaises(Exception):
            for i in range(200):
                self.s.commit([ev(i)], audit=[audit(i)])
        self.s.db.execute("PRAGMA max_page_count=1073741823")
        self.assertEqual(store_mod.Store(self.w.db_path).recover()["revision"], self.s.revision)

    def test_retention_keeps_history_hot_table_bounded(self):
        """controls: 01-10 02-09 32-04"""
        for i in range(5):
            self.s.commit([ev(100 + i, digest=art(7), at=T0 + i)], audit=[audit(i)])
        self.assertEqual(self.s.db.execute("SELECT COUNT(*) FROM matrix").fetchone()[0], 1)
        self.assertEqual(self.s.db.execute("SELECT COUNT(*) FROM ledger").fetchone()[0], 5)
        k = CertKey(PART, art(7), "wasmtime@21.0.0", "profile:p")
        self.assertEqual(len(self.s.state.history[k]), 5)


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.s = self.w.store
        self.s.commit([ev(1), ev(2)], audit=[audit(1)])

    def test_append_only_enforced_by_database(self):
        """controls: 02-02 12-03"""
        for sql in ("UPDATE ledger SET partition='x'", "DELETE FROM ledger", "UPDATE audit SET body=x''", "DELETE FROM audit"):
            with self.assertRaises(sqlite3.DatabaseError):
                self.s.db.execute(sql)

    def test_hash_chain_detects_tamper_reorder_truncate(self):
        """controls: 02-03 02-10 12-08 12-10"""
        head = self.s.verify_chain("ledger")
        self.assertEqual(head, self.s.head("ledger")[1])
        path = self.w.db_path
        raw = sqlite3.connect(path, isolation_level=None)
        raw.execute("DROP TRIGGER ledger_no_update")
        raw.execute("UPDATE ledger SET body=replace(body, 'compatible', 'incompatib') WHERE seq=1")
        with self.assertRaises(store_mod.StoreError) as cm:
            store_mod.Store(path)
        self.assertEqual(cm.exception.code, "E_CHAIN_BROKEN")
        raw.execute("DROP TRIGGER ledger_no_delete")
        raw.execute("DELETE FROM ledger WHERE seq=1")
        with self.assertRaises(store_mod.StoreError) as cm:
            store_mod.Store(path)
        self.assertIn(cm.exception.code, ("E_CHAIN_GAP", "E_CHAIN_BROKEN"))

    def test_deterministic_historical_reconstruction(self):
        """controls: 02-04 28-05 47-07"""
        k = CertKey(PART, art(1), "wasmtime@21.0.0", "profile:p")
        seq_before = self.s.head("ledger")[0]
        self.s.commit([ev(3, digest=art(1), result="incompatible", at=T0 + 10) | {"failure_class": "deterministic"}], audit=[audit(3)])
        self.assertEqual(self.s.certify(k, T0 + 20)["verdict"], "incompatible")
        self.assertEqual(self.s.reconstruct(k, T0 + 20, seq_before)["verdict"], "certified")
        self.assertEqual(self.s.reconstruct(k, T0 + 20, seq_before), self.s.reconstruct(k, T0 + 20, seq_before))

    def test_idempotency_key_unique_per_partition(self):
        """controls: 02-05 10-04"""
        with self.assertRaises(store_mod.StoreError):
            self.s.commit([ev(1) | {"event_id": "e1b", "evidence_id": "e1b", "artifact_digest": art(50)}], audit=[audit(9)])
        self.assertIsNotNone(self.s.find_idempotent(PART, "producer-a|1"))

    def test_canonical_bytes_stored(self):
        """controls: 02-06"""
        body = self.s.db.execute("SELECT body FROM ledger WHERE seq=1").fetchone()[0]
        from gap15_runtime_compatibility_certification.production.canonical import parse
        self.assertEqual(canonical_bytes(parse(body)), body)

    def test_export_and_signed_checkpoint_offline_verifiable(self):
        """controls: 02-07 02-08 12-07 03-08"""
        out = os.path.join(self.w.tmp, "ledger.jsonl")
        info = self.s.export_ledger(out)
        self.assertEqual(info["entries"], 2)
        pub = self.w.kp.public_key("svc-key")
        cp = self.s.checkpoint(lambda data: {"key_id": "svc-key", "value": b64e(self.w.kp.sign("svc-key", data))})
        self.assertTrue(ed25519.verify(pub, canonical_bytes(cp["checkpoint"]), b64d(cp["signature"]["value"])))
        # independent re-verification from the export alone
        prev = store_mod.GENESIS
        import json
        for line in open(out, "rb"):
            rec = json.loads(line)
            self.assertEqual(rec["prev_hash"], prev)
            prev = store_mod._chain(prev, rec["body"].encode())
            self.assertEqual(prev, rec["entry_hash"])
        self.assertEqual(prev, cp["checkpoint"]["ledger_head"])

    def test_lineage_query_by_signer_and_result(self):
        """controls: 02-08"""
        self.s.commit([ev(4) | {"signer_key_id": "producer-b-key", "result": "incompatible", "failure_class": "flaky"}], audit=[audit(4)])
        self.assertEqual([e["event_id"] for e in self.s.lookup(PART, signer="producer-b-key")], ["e4"])
        self.assertEqual([e["event_id"] for e in self.s.lookup(PART, result="incompatible")], ["e4"])

    def test_reordered_duplicated_stream_rejected_by_replay(self):
        """controls: 02-10"""
        events = self.s.events()
        with self.assertRaises(Exception):
            replay([events[1], {**events[0], "seq": events[1]["seq"]}])
        stale = dict(events[0], seq=10, observed_at=T0 - 5, event_id="x", evidence_id="x")
        with self.assertRaises(Exception):
            replay(events + [stale])


class ConcurrencyTest(unittest.TestCase):
    def test_parallel_writers_no_lost_updates_or_dup_seq(self):
        """controls: 11-02 11-03 11-10 37-01 37-02 37-08 11-09"""
        w = World()
        barrier = threading.Barrier(8)
        errors, conflicts = [], []

        def writer(n):
            barrier.wait()
            for j in range(10):
                i = n * 100 + j
                for _attempt in range(50):
                    try:
                        w.store.commit([ev(i)], audit=[audit(i)], expected_revision=w.store.revision)
                        break
                    except store_mod.Conflict:
                        conflicts.append(i)
                    except Exception as exc:  # pragma: no cover
                        errors.append(repr(exc))
                        break
        ts = [threading.Thread(target=writer, args=(n,)) for n in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(errors, [])
        self.assertEqual(w.store.revision, 80)
        seqs = [r[0] for r in w.store.db.execute("SELECT seq FROM ledger ORDER BY seq")]
        self.assertEqual(seqs, list(range(1, 81)))
        w.store.verify_chain("ledger")

    def test_two_processes_cas_across_connections(self):
        """controls: 11-02 11-06 37-06"""
        w = World()
        other = store_mod.Store(w.db_path)
        w.store.commit([ev(1)], audit=[audit(1)], expected_revision=0)
        with self.assertRaises(store_mod.Conflict):
            other.commit([ev(2)], audit=[audit(2)], expected_revision=0)  # stale view refreshed then CAS fails
        other.commit([ev(2)], audit=[audit(2)], expected_revision=1)
        self.assertEqual(store_mod.Store(w.db_path).revision, 2)

    def test_revocation_vs_certify_race_revocation_wins(self):
        """controls: 11-03 11-10 37-04 13-04"""
        w = World()
        w.store.commit([ev(1)], audit=[audit(1)])
        k = CertKey(PART, art(1), "wasmtime@21.0.0", "profile:p")
        results = []
        barrier = threading.Barrier(2)

        def reader():
            barrier.wait()
            for _ in range(200):
                results.append(w.store.certify(k, T0 + 1)["verdict"])

        def revoker():
            barrier.wait()
            w.store.commit([{"event_id": "r1", "event_type": "revoke", "partition": PART, "subject_type": "artifact",
                             "subject_id": art(1), "reason": "cve", "effective_at": T0}], audit=[audit(99)])
        ts = [threading.Thread(target=reader), threading.Thread(target=revoker)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(w.store.certify(k, T0 + 1)["verdict"], "revoked")
        # monotonic: once revoked is observed, no later read returns certified
        if "revoked" in results:
            self.assertNotIn("certified", results[results.index("revoked"):])

    def test_randomized_stress_with_seed(self):
        """controls: 37-10 37-09"""
        import random
        seed = 1507
        rnd = random.Random(seed)
        w = World()
        conflicts = 0
        for i in range(150):
            exp = w.store.revision if rnd.random() > 0.2 else max(0, w.store.revision - 1)
            try:
                w.store.commit([ev(i, at=T0 + rnd.randint(0, 5))], audit=[audit(i)], expected_revision=exp)
            except store_mod.Conflict:
                conflicts += 1
        self.assertGreater(conflicts, 0, f"seed={seed}")
        self.assertEqual(store_mod.Store(w.db_path).revision, w.store.revision)

    def test_snapshot_reads_expose_revision(self):
        """controls: 11-06"""
        w = World()
        w.store.commit([ev(1)], audit=[audit(1)])
        v = w.store.matrix_view(PART)
        self.assertEqual(v["revision"], 1)
        d = w.store.certify(CertKey(PART, art(1), "wasmtime@21.0.0", "profile:p"), T0)
        self.assertEqual((d["matrix_revision"], d["ledger_seq"]), (1, 1))


class BackupRestoreTest(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.w.store.commit([ev(1), ev(2, part=PART2)], audit=[audit(1)])
        self.sign = lambda data: {"key_id": "svc-key", "value": b64e(self.w.kp.sign("svc-key", data))}
        pub = self.w.kp.public_key("svc-key")
        self.verify = lambda data, sig: ed25519.verify(pub, data, b64d(sig["value"]))
        self.bk = os.path.join(self.w.tmp, "backup.db")
        self.manifest = self.w.store.backup(self.bk, sign=self.sign, created_at=T0, service_version="4.3.0")

    def test_backup_manifest_and_restore_to_staging(self):
        """controls: 01-08 15-02 15-05 47-01 47-02 47-04 47-07 38-06"""
        m = self.manifest["manifest"]
        self.assertEqual(m["revision"], 2)
        r = store_mod.restore_to_staging(self.bk, os.path.join(self.w.tmp, "staging.db"), verify_sig=self.verify,
                                         expected_partitions={PART, PART2})
        self.assertEqual(r["keys_verified"], 2)
        self.assertEqual(r["store"].revision, 2)

    def test_restore_refuses_corrupt_forged_and_existing_target(self):
        """controls: 47-04 15-06 38-06"""
        data = bytearray(open(self.bk, "rb").read())
        data[200] ^= 0xFF
        bad = os.path.join(self.w.tmp, "bad.db")
        open(bad, "wb").write(bytes(data))
        open(bad + ".manifest.json", "wb").write(open(self.bk + ".manifest.json", "rb").read())
        with self.assertRaises(store_mod.StoreError) as cm:
            store_mod.restore_to_staging(bad, os.path.join(self.w.tmp, "s1.db"), verify_sig=self.verify)
        self.assertEqual(cm.exception.code, "E_BACKUP_CORRUPT")
        with self.assertRaises(store_mod.StoreError) as cm:
            store_mod.restore_to_staging(self.bk, os.path.join(self.w.tmp, "s2.db"), verify_sig=lambda d, s: False)
        self.assertEqual(cm.exception.code, "E_BACKUP_SIGNATURE")
        with self.assertRaises(store_mod.StoreError):
            store_mod.restore_to_staging(self.bk, self.w.db_path, verify_sig=self.verify)

    def test_restore_refuses_foreign_partition(self):
        """controls: 25-06 25-10"""
        with self.assertRaises(store_mod.StoreError) as cm:
            store_mod.restore_to_staging(self.bk, os.path.join(self.w.tmp, "s3.db"), verify_sig=self.verify,
                                         expected_partitions={PART})
        self.assertEqual(cm.exception.code, "E_RESTORE_PARTITION")

    def test_backup_while_writes_active(self):
        """controls: 37-07"""
        stop = threading.Event()

        def writer():
            i = 1000
            while not stop.is_set():
                self.w.store.commit([ev(i)], audit=[audit(i)])
                i += 1
        t = threading.Thread(target=writer)
        t.start()
        bk2 = os.path.join(self.w.tmp, "live.db")
        self.w.store.backup(bk2, sign=self.sign, created_at=T0, service_version="4.3.0")
        stop.set()
        t.join()
        r = store_mod.restore_to_staging(bk2, os.path.join(self.w.tmp, "live-staging.db"), verify_sig=self.verify)
        r["store"].verify_chain("ledger")

    def test_measured_rpo_rto(self):
        """controls: 15-01 15-09 38-08"""
        import time
        t0 = time.perf_counter()
        r = store_mod.restore_to_staging(self.bk, os.path.join(self.w.tmp, "rto.db"), verify_sig=self.verify)
        rto = time.perf_counter() - t0
        committed = self.w.store.revision
        self.assertEqual(r["store"].revision, committed)  # RPO = 0 events for a completed backup
        self.assertLess(rto, 30.0)

    def test_cli_verify_and_export(self):
        """controls: 47-01 48-06"""
        from gap15_runtime_compatibility_certification.production import cli
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(cli.main(["verify", "--db", self.w.db_path]), 0)
        self.assertIn('"ok": true', buf.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["export", "--db", self.w.db_path, "--out", os.path.join(self.w.tmp, "x.jsonl")]), 0)
            self.assertEqual(cli.main(["diagnose", "--alert", "GAP15AuditChainBroken"]), 0)


class AuditStreamTest(unittest.TestCase):
    def test_audit_captures_security_actions_and_redacts(self):
        """controls: 12-01 12-02 12-06 12-04"""
        w = World()
        r = w.svc.ingest(w.producer(), w.evidence())
        w.svc.revoke(w.operator(), subject_type="artifact", subject_id=art(1), partition=PART, reason="cve", severity="high")
        with self.assertRaises(Exception):
            w.svc.ingest(w.producer(), b"{not json")
        acts = [a["action"] for a in w.store.audit_events()]
        self.assertIn("evidence.accepted", acts)
        self.assertIn("revoke", acts)
        self.assertIn("evidence.rejected", acts)
        for a in w.store.audit_events():
            self.assertTrue({"event_id", "action", "actor", "partition", "result", "at", "time_confidence"} <= set(a))
            self.assertNotIn("eyJ", canonical_bytes(a).decode())  # no token material
        rev = [a for a in w.store.audit_events() if a["action"] == "revoke"][0]
        self.assertTrue(rev["detail"]["subject"].startswith("h:"))
        # audit lives in its own chained table: log sink changes cannot touch it
        w.svc.log.sink.clear()
        w.store.verify_chain("audit")

    def test_audit_chain_independent_export(self):
        """controls: 12-07 12-09"""
        w = World()
        w.svc.ingest(w.producer(), w.evidence())
        cp = w.store.checkpoint(lambda d: {"value": b64e(w.kp.sign("svc-key", d))})
        self.assertEqual(cp["checkpoint"]["audit_head"], w.store.head("audit")[1])
        siem = [{"type": a["action"], "severity": "high" if a["classification"] == "security" else "info"} for a in w.store.audit_events()]
        self.assertTrue(all(s["type"] for s in siem))


if __name__ == "__main__":
    unittest.main()
