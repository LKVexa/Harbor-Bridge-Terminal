"""Durable storage, crash recovery, corruption handling, encryption, fault injection
(MC-006, MC-024-04, MC-025-03/06, MC-044)."""
from __future__ import annotations

import errno
import os
import shutil
import unittest

from _util import readb, tmpdir, writeb
from inv05_current_control_state_system.errors import CorruptionError, FailedClosed, InvalidArgument
from inv05_current_control_state_system.store import Put
from inv05_current_control_state_system.wal import DurableStore, Keyring, Sealer, SimulatedCrash

FAULT_POINTS = ["wal.before_write", "wal.mid_write", "wal.before_fsync", "wal.after_fsync"]


def sealer(*ids):
    ids = ids or ("k1",)
    return Sealer(Keyring({i: bytes([n + 1]) * 32 for n, i in enumerate(ids)}, ids[-1]))


class DurabilityTest(unittest.TestCase):
    def setUp(self):
        self.dir = tmpdir()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_acknowledged_writes_survive_restart(self):
        ds = DurableStore.open(self.dir)
        for i in range(50):
            r = ds.store.put(f"k{i}", i)
            self.assertEqual(r.durability, "fsync")
        l = ds.store.lease_grant(30, owner="o")
        ds.store.put("leased", 1, lease=l.id)
        ds.store.delete("k0")
        ds.store.compact(10)
        before = ds.store.export_state()
        ds.close()
        ds2 = DurableStore.open(self.dir)
        after = ds2.store.export_state()
        self.assertEqual(before["revision"], after["revision"])
        self.assertEqual(before["keys"], after["keys"])
        self.assertEqual(before["compact_revision"], after["compact_revision"])
        self.assertEqual([x["id"] for x in before["leases"]], [x["id"] for x in after["leases"]])
        self.assertEqual(ds2.report.records_replayed, 54)
        ds2.close()

    def test_checkpoint_and_recover_from_snapshot_plus_wal(self):
        ds = DurableStore.open(self.dir)
        for i in range(20):
            ds.store.put("k", i)
        gen = ds.checkpoint()
        for i in range(5):
            ds.store.put("j", i)
        ds.close()
        self.assertTrue(os.path.exists(os.path.join(self.dir, f"snap-{gen:016d}.bin")))
        ds2 = DurableStore.open(self.dir)
        self.assertEqual((ds2.store.get("k").value, ds2.store.get("j").value, ds2.store.revision), (19, 4, 25))
        self.assertEqual(ds2.report.records_replayed, 5)
        ds2.close()

    def test_crash_at_every_persistence_boundary(self):
        """Acked writes are never lost; an unacked write is atomically present or absent."""
        for point in FAULT_POINTS:
            with self.subTest(point=point):
                d = tmpdir()
                armed = {"on": False}

                def fault(p, point=point):
                    if armed["on"] and p == point:
                        raise SimulatedCrash(p)
                ds = DurableStore.open(d, fault=fault)
                for i in range(5):
                    ds.store.put("k", i)
                armed["on"] = True
                with self.assertRaises(SimulatedCrash):
                    ds.store.put("k", "crash")
                os.close(ds.wal._fd)  # process death: no clean close
                ds2 = DurableStore.open(d)
                v = ds2.store.get("k").value
                self.assertIn(v, (4, "crash"))
                if point in ("wal.before_write", "wal.mid_write"):
                    self.assertEqual(v, 4)
                if point == "wal.mid_write":
                    self.assertGreater(ds2.report.torn_tail_bytes, 0)
                self.assertEqual(ds2.store.check_invariants(), [])
                ds2.store.put("k", "after")  # writable after recovery
                ds2.close()
                shutil.rmtree(d, ignore_errors=True)

    def test_crash_during_snapshot(self):
        for point in ("snap.before_rename", "snap.after_rename"):
            with self.subTest(point=point):
                d = tmpdir()
                ds = DurableStore.open(d, fault=lambda p, point=point: (_ for _ in ()).throw(SimulatedCrash(p))
                                       if p == point else None)
                for i in range(10):
                    ds.store.put("k", i)
                with self.assertRaises(SimulatedCrash):
                    ds.checkpoint()
                os.close(ds.wal._fd)
                ds2 = DurableStore.open(d)
                self.assertEqual(ds2.store.get("k").value, 9)
                ds2.close()
                shutil.rmtree(d, ignore_errors=True)

    def test_io_error_fails_closed_and_never_acks(self):
        for err in (errno.ENOSPC, errno.EIO):
            with self.subTest(err=err):
                d = tmpdir()
                armed = {"on": False}

                def fault(p, err=err):
                    if armed["on"] and p == "wal.before_fsync":
                        raise OSError(err, os.strerror(err))
                ds = DurableStore.open(d, fault=fault)
                ds.store.put("k", 1)
                armed["on"] = True
                with self.assertRaises(FailedClosed):
                    ds.store.put("k", 2)
                self.assertTrue(ds.store.failed)
                self.assertEqual(ds.store.revision, 1)  # the failed write was not applied
                with self.assertRaises(FailedClosed):
                    ds.store.get("k")  # fail closed for reads too: state may diverge from disk
                shutil.rmtree(d, ignore_errors=True)

    def test_mid_file_corruption_is_fatal(self):
        ds = DurableStore.open(self.dir)
        for i in range(10):
            ds.store.put("k", i)
        path = ds.wal.path
        ds.close()
        with open(path, "r+b") as fh:
            fh.seek(40)
            b = fh.read(1)
            fh.seek(40)
            fh.write(bytes([b[0] ^ 0xFF]))
        with self.assertRaises(CorruptionError):
            DurableStore.open(self.dir)

    def test_bad_crc_on_last_record_requires_operator(self):
        ds = DurableStore.open(self.dir)
        for i in range(3):
            ds.store.put("k", i)
        path = ds.wal.path
        ds.close()
        size = os.path.getsize(path)
        with open(path, "r+b") as fh:
            fh.seek(size - 2)
            fh.write(b"\x00\x00")
        with self.assertRaises(CorruptionError):
            DurableStore.open(self.dir)
        ds2 = DurableStore.open(self.dir, allow_tail_truncation=True)
        self.assertTrue(ds2.report.tail_truncated_by_operator)
        self.assertEqual(ds2.store.get("k").value, 1)
        ds2.close()

    def test_corrupt_snapshot_is_fatal(self):
        ds = DurableStore.open(self.dir)
        ds.store.put("k", 1)
        gen = ds.checkpoint()
        ds.close()
        p = os.path.join(self.dir, f"snap-{gen:016d}.bin")
        data = bytearray(readb(p))
        data[-5] ^= 0x01
        writeb(p, bytes(data))
        with self.assertRaises(CorruptionError):
            DurableStore.open(self.dir)

    def test_encryption_at_rest_and_key_rotation(self):
        s = sealer("k1")
        ds = DurableStore.open(self.dir, sealer=s)
        ds.store.put("secret", "plaintext-marker-123")
        ds.checkpoint()
        s.keyring.rotate("k2", b"\x09" * 32)  # new writes use k2, old data still readable
        ds.store.put("secret2", "plaintext-marker-456")
        ds.close()
        for name in os.listdir(self.dir):
            blob = readb(os.path.join(self.dir, name))
            self.assertNotIn(b"plaintext-marker", blob, name)
        ds2 = DurableStore.open(self.dir, sealer=s)
        self.assertEqual(ds2.store.get("secret2").value, "plaintext-marker-456")
        ds2.close()
        with self.assertRaises(CorruptionError):
            DurableStore.open(self.dir)  # encrypted data, no keyring
        with self.assertRaises(CorruptionError):
            DurableStore.open(self.dir, sealer=sealer("k1"))  # k2 missing

    def test_tampered_ciphertext_detected(self):
        ds = DurableStore.open(self.dir, sealer=sealer())
        ds.store.put("k", 1)
        path = ds.wal.path
        ds.close()
        data = bytearray(readb(path))
        data[-1] ^= 1
        # fix the CRC so only the AEAD tag can catch it
        import struct, zlib
        n = struct.unpack(">I", data[4:8])[0]
        data[8:12] = struct.pack(">I", zlib.crc32(bytes(data[12:12 + n])))
        writeb(path, bytes(data))
        with self.assertRaises(CorruptionError):
            DurableStore.open(self.dir, sealer=sealer())

    def test_unsafe_durability_requires_opt_in(self):
        with self.assertRaises(InvalidArgument):
            DurableStore.open(self.dir, durability="none")
        ds = DurableStore.open(self.dir, durability="group", group_commit=4)
        self.assertEqual(ds.store.put("k", 1).durability, "group")
        ds.close()

    def test_file_permissions(self):
        ds = DurableStore.open(self.dir)
        ds.store.put("k", 1)
        self.assertEqual(os.stat(ds.wal.path).st_mode & 0o077, 0)
        ds.close()


if __name__ == "__main__":
    unittest.main()
