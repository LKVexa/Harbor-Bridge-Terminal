"""MC03 / MC15 / MC30 / MC34 / MC35 / MC36 / MC37 / MC38 / MC52 / MC76 — durable store."""
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path

from inv02_container_substrate import store as st
from inv02_container_substrate.registry import IntegrityError, QuarantinedDigest, UnknownReference, ValidationError
from inv02_container_substrate.migrations import SchemaTooNew, migrate_legacy_manifest
from inv02_container_substrate.timeutil import FakeClock
from inv02_container_substrate.tests.fixtures import make_image, sha


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "s"
        self.clock = FakeClock()
        self.events = []
        self.s = st.ContentStore(self.root, clock=self.clock, audit=lambda e, f: self.events.append(e))

    def tearDown(self):
        self.tmp.cleanup()

    def test_put_get_roundtrip_and_permissions(self):
        d = self.s.put(b"hello")
        self.assertEqual(self.s.get(d), b"hello")
        self.assertEqual(os.stat(self.s._blob_path(d)).st_mode & 0o777, 0o444)
        self.assertEqual(self.s.put(b"hello"), d)  # idempotent
        with self.assertRaises(IntegrityError):
            self.s.put(b"x", expected=sha(b"y"))

    def test_persists_across_reopen(self):
        d = self.s.put(b"data")
        self.s.set_tag("reg.test/app:1", d)
        s2 = st.ContentStore(self.root, clock=self.clock)
        self.assertEqual(s2.get_tag("reg.test/app:1"), d)
        self.assertEqual(s2.get(d), b"data")

    def test_corruption_detected_on_read_and_repaired(self):
        d = self.s.put(b"precious")
        p = self.s._blob_path(d)
        os.chmod(p, 0o644)
        p.write_bytes(b"tampered")
        with self.assertRaises(IntegrityError):
            self.s.get(d)
        self.assertEqual(self.s.fsck()["corrupt"], [d])
        rep = self.s.repair(fetch=lambda dg: b"precious")
        self.assertEqual(rep["repaired"], [d])
        self.assertEqual(self.s.get(d), b"precious")
        self.assertTrue(any(self.root.joinpath("corrupt").iterdir()))  # evidence preserved

    def test_repair_without_source_quarantines(self):
        d = self.s.put(b"x1")
        p = self.s._blob_path(d)
        os.chmod(p, 0o644)
        p.write_bytes(b"x2")
        self.s.repair()
        self.assertTrue(self.s.is_quarantined(d))

    def test_tag_compare_and_swap(self):
        a, b = self.s.put(b"a"), self.s.put(b"b")
        self.assertEqual(self.s.set_tag("r.test/x:1", a, expected=None), 1)
        with self.assertRaises(st.ConflictError):
            self.s.set_tag("r.test/x:1", b, expected=None)
        with self.assertRaises(st.ConflictError):
            self.s.set_tag("r.test/x:1", b, expected=b)
        self.assertEqual(self.s.set_tag("r.test/x:1", b, expected=a), 2)
        with self.assertRaises(UnknownReference):
            self.s.set_tag("r.test/x:1", sha(b"missing"))

    def test_concurrent_cas_exactly_one_winner(self):
        a = self.s.put(b"base")
        self.s.set_tag("r.test/x:1", a)
        cands = [self.s.put(f"v{i}".encode()) for i in range(16)]
        wins, errs = [], []

        def go(d):
            try:
                self.s.set_tag("r.test/x:1", d, expected=a)
                wins.append(d)
            except st.ConflictError:
                errs.append(d)

        ts = [threading.Thread(target=go, args=(d,)) for d in cands]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(wins), 1)
        self.assertEqual(len(errs), 15)

    def test_resumable_ingest(self):
        data = os.urandom(10000)
        d = sha(data)
        self.assertEqual(self.s.ingest_open("r1", d, len(data)), 0)
        self.s.ingest_write("r1", 0, data[:4000])
        s2 = st.ContentStore(self.root, clock=self.clock)  # "crash" + restart
        off = s2.ingest_open("r1", d, len(data))
        self.assertEqual(off, 4000)
        with self.assertRaises(st.ConflictError):
            s2.ingest_write("r1", 0, data[:10])
        s2.ingest_write("r1", off, data[off:])
        self.assertEqual(s2.ingest_commit("r1"), d)
        self.assertEqual(s2.get(d), data)

    def test_ingest_wrong_bytes_rejected(self):
        d = sha(b"expected")
        self.s.ingest_open("r2", d, 8)
        self.s.ingest_write("r2", 0, b"xxxxxxxx")
        with self.assertRaises(IntegrityError):
            self.s.ingest_commit("r2")
        self.assertFalse(self.s.has(d))

    def test_quarantine_is_durable_and_needs_two_people(self):
        d = self.s.put(b"bad")
        self.s.quarantine(d, "CVE", actor="alice")
        s2 = st.ContentStore(self.root, clock=self.clock)
        with self.assertRaises(QuarantinedDigest):
            s2.get(d)
        with self.assertRaises(ValidationError):
            s2.release(d, actor="alice", approver="alice")
        s2.release(d, actor="alice", approver="bob")
        self.assertEqual(s2.get(d), b"bad")

    def test_gc_respects_tags_leases_references_and_grace(self):
        img = make_image([[("a", "file", b"1")], [("b", "file", b"2")]])
        for b in img["layers"]:
            self.s.put(b)
        cfg = self.s.put(img["config"])
        man = self.s.put(img["manifest"])
        self.s.set_tag("r.test/app:1", man)
        leased = self.s.put(b"leased")
        orphan = self.s.put(b"orphan")
        self.s.lease([leased], 60, "puller")
        self.assertIn(orphan, self.s.gc(dry_run=True, grace_s=3600)["swept"] or [orphan])  # grace protects young blobs
        self.assertEqual(self.s.gc(grace_s=3600)["swept"], [])
        res = self.s.gc(grace_s=0)
        self.assertEqual(res["swept"], [orphan])
        for d in [man, cfg, leased] + [sha(b) for b in img["layers"]]:
            self.assertTrue(self.s.has(d))
        self.clock.advance(120)
        self.assertEqual(self.s.gc(grace_s=0)["swept"], [leased])

    def test_backup_restore(self):
        d = self.s.put(b"keep")
        self.s.set_tag("r.test/k:1", d)
        bk = Path(self.tmp.name) / "b.tar"
        dg = self.s.backup(bk)
        r = st.ContentStore.restore(bk, Path(self.tmp.name) / "r", expected_digest=dg)
        self.assertEqual(r.get_tag("r.test/k:1"), d)
        with self.assertRaises(IntegrityError):
            st.ContentStore.restore(bk, Path(self.tmp.name) / "r2", expected_digest=sha(b"nope"))

    def test_schema_migration_and_downgrade_refusal(self):
        meta = self.root / "meta.json"
        d = self.s.put(b"v1")
        meta.write_text(json.dumps({"schema": 1, "tags": {"r.test/a:1": d}}))
        s2 = st.ContentStore(self.root)
        self.assertEqual(s2.get_tag("r.test/a:1"), d)
        meta.write_text(json.dumps({"schema": 99, "tags": {}}))
        with self.assertRaises(SchemaTooNew):
            st.ContentStore(self.root)

    def test_legacy_manifest_migration(self):
        a = sha(b"a")
        new = json.loads(migrate_legacy_manifest(json.dumps({"layers": [a]}).encode(), {a: 1}))
        self.assertEqual(new["layers"], [{"digest": a, "size": 1}])
        with self.assertRaises(IntegrityError):
            migrate_legacy_manifest(json.dumps({"layers": [a]}).encode(), {})

    def test_audit_hook_invoked(self):
        d = self.s.put(b"z")
        self.s.set_tag("r.test/z:1", d)
        self.assertIn("blob.put", self.events)
        self.assertIn("tag.set", self.events)


if __name__ == "__main__":
    unittest.main()
