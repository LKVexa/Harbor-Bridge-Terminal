"""Durable checkpoint store: crash consistency, fencing, quarantine, GC (C018, C057-C059, C095)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

from _support import PKG_DIR, ROOT, pkg
from inv37_bulk_data_plane.checkpoint import CheckpointStore


class CheckpointTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.key = os.urandom(32)
        self.store = CheckpointStore(self.tmp.name, seal_key=self.key)
        self.data = os.urandom(10_000)
        self.m = pkg.manifest(self.data, 4096)

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, lease, idx, verified):
        self.store.write_chunk(lease, idx, idx * 4096, self.data[idx * 4096:(idx + 1) * 4096], verified, "receiving")

    def test_roundtrip_and_restart(self):
        lease = self.store.acquire("tx1", "n1")
        self.store.create(lease, self.m, tenant="acme")
        self.put(lease, 0, {0}); self.put(lease, 2, {0, 2})
        again = CheckpointStore(self.tmp.name, seal_key=self.key)  # "restart"
        st = again.load("tx1")
        self.assertEqual(st["verified"], [0, 2])
        self.assertEqual(st["tenant"], "acme")

    def test_corrupt_data_is_dropped_not_trusted(self):
        lease = self.store.acquire("tx1", "n1")
        self.store.create(lease, self.m, tenant="acme")
        self.put(lease, 0, {0}); self.put(lease, 1, {0, 1})
        p = self.store.data_path("tx1")
        b = bytearray(p.read_bytes()); b[5000] ^= 0xFF; p.write_bytes(bytes(b))
        st = self.store.load("tx1")
        self.assertEqual(st["verified"], [0])
        self.assertEqual(st["dropped_on_load"], [1])

    def test_broken_seal_quarantines(self):
        lease = self.store.acquire("tx1", "n1")
        self.store.create(lease, self.m, tenant="acme")
        sp = self.store._dir("tx1") / "state.json"
        st = json.loads(sp.read_text()); st["verified"] = [0, 1, 2]; sp.write_text(json.dumps(st))
        with self.assertRaises(pkg.CodedError) as cm:
            self.store.load("tx1")
        self.assertEqual(cm.exception.code, "checkpoint_corrupt")
        self.assertNotIn("tx1", self.store.list())
        self.assertEqual(len(list((Path(self.tmp.name) / "quarantine").iterdir())), 1)

    def test_wrong_key_is_corrupt(self):
        lease = self.store.acquire("tx1", "n1")
        self.store.create(lease, self.m, tenant="acme")
        other = CheckpointStore(self.tmp.name, seal_key=os.urandom(32))
        self.assertRaises(pkg.CodedError, other.load, "tx1")

    def test_fencing_split_brain(self):
        a = self.store.acquire("tx1", "node-a")
        self.store.create(a, self.m, tenant="acme")
        b = self.store.acquire("tx1", "node-b")  # takeover
        with self.assertRaises(pkg.CodedError) as cm:
            self.put(a, 0, {0})
        self.assertEqual(cm.exception.code, "stale_owner")
        self.put(b, 0, {0})
        self.assertGreater(b.epoch, a.epoch)

    def test_ids_are_validated(self):
        for bad in ("../x", "", "a/b", "x" * 200):
            self.assertRaises(pkg.CodedError, self.store.acquire, bad, "n")

    def test_refuses_package_dir(self):
        self.assertRaises(pkg.CodedError, CheckpointStore, PKG_DIR / "state")

    def test_storage_quota(self):
        s = CheckpointStore(self.tmp.name + "/q", seal_key=self.key, max_bytes=5000)
        lease = s.acquire("tx1", "n")
        with self.assertRaises(pkg.CodedError) as cm:
            s.create(lease, self.m, tenant="a")
        self.assertEqual(cm.exception.code, "quota_exceeded")

    def test_gc_and_inventory(self):
        lease = self.store.acquire("old", "n")
        self.store.create(lease, self.m, tenant="acme")
        inv = self.store.export_inventory()
        self.assertEqual(inv[0]["transfer_id"], "old")
        self.assertEqual(self.store.gc(retention_seconds=3600), [])
        self.assertEqual(self.store.gc(retention_seconds=10, now=time.time() + 100), ["old"])

    def test_crash_during_write_sequence(self):
        """Kill a writer process at every step boundary; the survivor must load
        a consistent state whose verified set only contains good chunks."""
        for crash_after in ("data", "state"):
            with tempfile.TemporaryDirectory() as d:
                script = textwrap.dedent(f"""
                    import os, sys; sys.path.insert(0, {str(ROOT)!r})
                    import {PKG_DIR.name} as pkg
                    from {PKG_DIR.name} import checkpoint as ck
                    key = bytes.fromhex({self.key.hex()!r}); data = bytes.fromhex({self.data.hex()!r})
                    s = ck.CheckpointStore({d!r}, seal_key=key)
                    m = pkg.manifest(data, 4096); l = s.acquire('tx', 'n'); s.create(l, m, tenant='t')
                    s.write_chunk(l, 0, 0, data[:4096], {{0}}, 'receiving')
                    orig = ck.atomic_write_json
                    if {crash_after!r} == 'data':
                        ck.atomic_write_json = lambda *a, **k: os._exit(9)   # die before state commit
                    else:
                        def die(*a, **k):
                            orig(*a, **k); os._exit(9)
                        ck.atomic_write_json = die
                    s.write_chunk(l, 1, 4096, data[4096:8192], {{0, 1}}, 'receiving')
                """)
                r = subprocess.run([sys.executable, "-c", script], capture_output=True, timeout=60)
                self.assertEqual(r.returncode, 9, r.stderr.decode())
                st = CheckpointStore(d, seal_key=self.key).load("tx")
                self.assertEqual(st["verified"], [0] if crash_after == "data" else [0, 1])
                self.assertFalse([p for p in (Path(d) / "transfers" / "tx").iterdir() if p.name.startswith(".tmp")]
                                 and crash_after == "state")


if __name__ == "__main__":
    unittest.main()


class CrossProcessFencingTest(unittest.TestCase):
    def test_concurrent_acquire_yields_unique_epochs(self):
        with tempfile.TemporaryDirectory() as d:
            key = os.urandom(32).hex()
            script = textwrap.dedent(f"""
                import sys; sys.path.insert(0, {str(ROOT)!r})
                from {PKG_DIR.name} import checkpoint as ck
                s = ck.CheckpointStore({d!r}, seal_key=bytes.fromhex({key!r}))
                print(" ".join(str(s.acquire('race', 'p' + sys.argv[1]).epoch) for _ in range(25)))
            """)
            procs = [subprocess.Popen([sys.executable, "-c", script, str(i)], stdout=subprocess.PIPE, text=True) for i in range(4)]
            epochs = []
            for p in procs:
                out, _ = p.communicate(timeout=120)
                epochs += [int(x) for x in out.split()]
            self.assertEqual(len(epochs), 100)
            self.assertEqual(len(set(epochs)), 100)   # no two acquisitions share an epoch
            self.assertEqual(max(epochs), 100)

    def test_out_of_range_verified_index_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            s = CheckpointStore(d, seal_key=os.urandom(32))
            data = os.urandom(5000)
            m = pkg.manifest(data, 4096)
            lease = s.acquire("x", "n")
            s.create(lease, m, tenant="t")
            s.write_chunk(lease, 0, 0, data[:4096], {0}, "receiving")
            st = s._read_state_raw("x"); st["verified"] = [0, 7, -1, "a"]
            s._write_state(lease, st)  # validly sealed but nonsensical indices
            got = s.load("x")
            self.assertEqual(got["verified"], [0])
            self.assertEqual(got["dropped_on_load"], [7, -1, "a"])
