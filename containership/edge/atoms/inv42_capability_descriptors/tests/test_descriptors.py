"""Standalone runtime/security tests for INV-42.

These tests deliberately do not require pk_core.  They import the runtime module
from the package directory so a missing certification framework cannot turn the
entire repository test run into a false-green all-skipped result.
"""
from __future__ import annotations

import os
import pathlib
import pickle
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

import descriptors as d  # noqa: E402


class DescriptorRuntimeTest(unittest.TestCase):
    def test_wire_round_trip(self):
        table = d.DescriptorTable("workload")
        original = table.open("stream", {"resource": 1})
        parsed = table.from_wire(original.to_wire())
        self.assertEqual(parsed, original)
        self.assertEqual(table.resolve(parsed, expect="stream"), {"resource": 1})

    def test_guessing_or_forgery_is_not_authority(self):
        table = d.DescriptorTable("workload")
        real = table.open("stream", object())
        forged = d.Descriptor(real.number, real.resource_type, real.table_id, "0" * 64)
        with self.assertRaises(d.InvalidDescriptor):
            table.resolve(forged)

    def test_tampering_number_type_table_and_auth_fails_closed(self):
        table = d.DescriptorTable("workload")
        real = table.open("stream", object())
        wire = real.to_wire()

        tampered = dict(wire)
        tampered["number"] = real.number + 1
        with self.assertRaises(d.InvalidDescriptor):
            table.from_wire(tampered)

        tampered = dict(wire)
        tampered["type"] = "socket"
        with self.assertRaises(d.InvalidDescriptor):
            table.from_wire(tampered)

        other = d.DescriptorTable("other")
        with self.assertRaises(d.ForeignDescriptor):
            other.from_wire(wire)

        tampered = dict(wire)
        tampered["auth"] = "f" * 64
        with self.assertRaises(d.InvalidDescriptor):
            table.from_wire(tampered)

    def test_parser_is_strict_and_rejects_v1(self):
        table = d.DescriptorTable("workload")
        fd = table.open("stream", object())
        wire = fd.to_wire()

        with self.assertRaises(d.InvalidDescriptor):
            table.from_wire({**wire, "unexpected": True})
        legacy = dict(wire)
        legacy["schema"] = "PK_DESCRIPTOR/1"
        with self.assertRaises(d.InvalidDescriptor):
            table.from_wire(legacy)
        malformed = dict(wire)
        malformed["number"] = True
        with self.assertRaises(d.InvalidDescriptor):
            table.from_wire(malformed)

    def test_close_is_permanent_and_number_is_not_reused(self):
        table = d.DescriptorTable("workload")
        first = table.open("stream", "A")
        receipt = table.close(first)
        second = table.open("stream", "B")
        self.assertEqual(receipt["schema"], d.CLOSE_SCHEMA)
        self.assertFalse(receipt["number_reusable"])
        self.assertGreater(second.number, first.number)
        with self.assertRaises(d.DescriptorClosed):
            table.resolve(first)

    def test_expected_type_is_enforced(self):
        table = d.DescriptorTable("workload")
        fd = table.open("stream", object())
        with self.assertRaises(d.TypeMismatch) as ctx:
            table.resolve(fd, expect="socket")
        self.assertEqual(ctx.exception.code, "type_mismatch")
        self.assertEqual(ctx.exception.as_dict()["code"], "type_mismatch")

    def test_live_limit_and_read_only_entries(self):
        table = d.DescriptorTable("workload")
        for _ in range(d.TABLE_LIMIT):
            table.open("stream", object())
        with self.assertRaises(d.TableFull):
            table.open("stream", object())
        with self.assertRaises(TypeError):
            table.entries[3] = ("stream", object())

    def test_concurrent_allocation_is_unique(self):
        table = d.DescriptorTable("workload")

        def allocate(_):
            return table.open("stream", object()).number

        with ThreadPoolExecutor(max_workers=16) as pool:
            numbers = list(pool.map(allocate, range(800)))
        self.assertEqual(len(numbers), len(set(numbers)))
        self.assertEqual(min(numbers), d.FIRST_DESCRIPTOR)
        self.assertEqual(max(numbers), d.FIRST_DESCRIPTOR + len(numbers) - 1)

    def test_fork_clone_is_rejected(self):
        table = d.DescriptorTable("workload")
        with mock.patch.object(d.os, "getpid", return_value=os.getpid() + 1):
            with self.assertRaises(d.ForkedTable):
                table.open("stream", object())

    def test_table_secret_cannot_be_pickled(self):
        table = d.DescriptorTable("workload")
        with self.assertRaises(TypeError):
            pickle.dumps(table)

    def test_destroy_revokes_table_and_zeroizes_key(self):
        table = d.DescriptorTable("workload")
        fd = table.open("stream", object())
        table.destroy()
        self.assertTrue(table.status()["destroyed"])
        self.assertEqual(table.status()["live"], 0)
        self.assertEqual(bytes(table._key), b"\x00" * 32)
        with self.assertRaises(d.TableDestroyed):
            table.resolve(fd)
        with self.assertRaises(d.TableDestroyed):
            table.open("stream", object())

    def test_session_allocation_limit_is_enforced(self):
        table = d.DescriptorTable("workload")
        with mock.patch.object(d, "SESSION_ALLOCATION_LIMIT", 2):
            first = table.open("stream", object())
            table.close(first)
            second = table.open("stream", object())
            table.close(second)
            with self.assertRaises(d.SessionExhausted):
                table.open("stream", object())

    def test_status_exposes_bounded_non_secret_counters(self):
        table = d.DescriptorTable("workload")
        fd = table.open("stream", object())
        with self.assertRaises(d.TypeMismatch):
            table.resolve(fd, expect="socket")
        status = table.status()
        self.assertEqual(status["live"], 1)
        self.assertEqual(status["issued"], 1)
        self.assertEqual(status["type_mismatches"], 1)
        self.assertNotIn("table_id", status)
        self.assertNotIn("owner", status)
        self.assertNotIn("key", status)

    def test_runtime_checks_survive_optimized_mode(self):
        code = (
            "import sys; sys.path.insert(0, %r); import descriptors as d; "
            "t=d.DescriptorTable('w'); x=t.open('stream',object()); "
            "f=d.Descriptor(x.number,x.resource_type,x.table_id,'0'*64); "
            "\ntry: t.resolve(f)\n"
            "except d.InvalidDescriptor: print('PASS')\n"
            "else: raise SystemExit(9)"
        ) % str(PKG_DIR)
        out = subprocess.run(
            [sys.executable, "-O", "-c", code],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "PASS")


if __name__ == "__main__":
    unittest.main()
