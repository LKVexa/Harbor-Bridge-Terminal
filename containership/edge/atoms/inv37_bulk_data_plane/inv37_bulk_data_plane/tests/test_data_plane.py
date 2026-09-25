"""Dependency-free security and correctness tests for INV-37."""
from __future__ import annotations

import importlib
import json
import os
import pathlib
import subprocess
import sys
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pkg = importlib.import_module(PKG_DIR.name)


class DataPlaneTest(unittest.TestCase):
    def test_version_is_consistent(self):
        self.assertEqual(pkg.__version__, "4.3.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text(encoding="utf-8").strip(), "4.3.0")

    def test_round_trip_and_corruption_rejection(self):
        data = (bytes(range(251)) * 79) + b"tail"
        m = pkg.manifest(data, chunk=1024)
        rx = pkg.Receiver(m)
        chunks = [data[i : i + 1024] for i in range(0, len(data), 1024)]
        with self.assertRaises(pkg.DigestMismatch):
            rx.accept(0, b"x" + chunks[0][1:])
        for i, chunk in enumerate(chunks):
            rx.accept(i, chunk)
        self.assertEqual(rx.assemble(), data)
        self.assertEqual(rx.state, pkg.TransferState.COMPLETE)

    def test_manifest_tampering_and_geometry_are_rejected(self):
        data = b"a" * 9000
        m = pkg.manifest(data)
        tampered = dict(m)
        tampered["chunks"] = list(m["chunks"])
        tampered["chunks"][0] = "0" * 64
        with self.assertRaises(pkg.InvalidManifest):
            pkg.validate_manifest(tampered)

        bad_geometry = dict(m)
        bad_geometry["size"] += m["chunk"]
        with self.assertRaises(pkg.InvalidManifest):
            pkg.validate_manifest(bad_geometry)

    def test_manifest_is_copied_after_validation(self):
        data = b"immutable-manifest" * 600
        m = pkg.manifest(data, chunk=512)
        rx = pkg.Receiver(m)
        first = rx.m["chunks"][0]
        m["chunks"][0] = "0" * 64
        self.assertEqual(rx.m["chunks"][0], first)

    def test_wrong_chunk_length_and_index_are_rejected(self):
        data = b"b" * 5000
        m = pkg.manifest(data, chunk=4096)
        rx = pkg.Receiver(m)
        with self.assertRaises(pkg.DigestMismatch):
            rx.accept(-1, data[:4096])
        with self.assertRaises(pkg.DigestMismatch):
            rx.accept(True, data[:4096])
        with self.assertRaises(pkg.DigestMismatch):
            rx.accept(0, data[:4095])

    def test_duplicate_delivery_is_idempotent(self):
        data = b"c" * 5000
        m = pkg.manifest(data, chunk=4096)
        rx = pkg.Receiver(m)
        first = data[:4096]
        rx.accept(0, first)
        rx.accept(0, first)
        self.assertEqual(rx.duplicate_chunks, 1)
        self.assertEqual(rx.bytes_received, len(first))

    def test_resume_tracks_holes_and_contiguous_prefix(self):
        data = b"d" * (4096 * 4 + 17)
        m = pkg.manifest(data)
        rx = pkg.Receiver(m)
        chunks = [data[i : i + 4096] for i in range(0, len(data), 4096)]
        rx.accept(0, chunks[0])
        rx.accept(2, chunks[2])
        token = rx.resume_token()
        self.assertEqual(token["last_verified"], 0)
        self.assertEqual(token["verified"], [0, 2])
        self.assertEqual(rx.missing(), [1, 3, 4])
        with self.assertRaises(pkg.TransferIncomplete):
            rx.assemble()

    def test_resource_limits_fail_closed(self):
        limits = pkg.TransferLimits(max_object_bytes=16, max_chunk_bytes=8, max_chunks=2, max_concurrent_transfers=1)
        with self.assertRaises(ValueError):
            pkg.manifest(b"x" * 17, chunk=8, limits=limits)
        with self.assertRaises(ValueError):
            pkg.manifest(b"x" * 8, chunk=9, limits=limits)

    def test_bounded_concurrency_rejects_overflow(self):
        pool = pkg.BoundedTransferPool(max_active=1)
        with pool.slot():
            with self.assertRaises(pkg.AdmissionRejected):
                with pool.slot(timeout=0):
                    pass
        metrics = pool.metrics()
        self.assertEqual(metrics["transfers_active"], 0)
        self.assertEqual(metrics["transfers_rejected"], 1)
        self.assertEqual(metrics["transfers_high_water"], 1)

    def test_receiver_is_safe_under_parallel_distinct_chunk_delivery(self):
        data = bytes(range(256)) * 256
        m = pkg.manifest(data, chunk=1024)
        rx = pkg.Receiver(m)
        chunks = [data[i : i + 1024] for i in range(0, len(data), 1024)]
        threads = [threading.Thread(target=rx.accept, args=(i, chunk)) for i, chunk in enumerate(chunks)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(rx.assemble(), data)

    def test_schema_documents_are_valid_json_and_present(self):
        for name in ("PK_BULK_MANIFEST_1.schema.json", "PK_BULK_CHUNK_1.schema.json", "PK_BULK_RESUME_1.schema.json"):
            path = PKG_DIR / "schemas" / name
            parsed = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(parsed["type"], "object")

    def test_core_survives_optimised_mode_without_pk_core(self):
        code = (
            "import sys;sys.path.insert(0,%r);import %s as p;"
            "d=b'x'*9000;m=p.manifest(d);r=p.Receiver(m);"
            "[r.accept(i,d[i*m['chunk']:(i+1)*m['chunk']]) for i in range(m['chunk_count'])];"
            "print(len(r.assemble()))"
        ) % (str(ROOT), PKG_DIR.name)
        out = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "9000")


if __name__ == "__main__":
    unittest.main()
