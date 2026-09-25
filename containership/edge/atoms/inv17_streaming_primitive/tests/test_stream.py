"""Standalone unit/contract tests for the INV-17 runtime primitive (stdlib only)."""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("inv17_stream_runtime", PKG_DIR / "stream.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load stream.py test target")
stream = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = stream
SPEC.loader.exec_module(stream)


class StreamRuntimeTest(unittest.TestCase):
    def test_credit_and_fifo(self):
        s = stream.Stream(int, config=stream.StreamConfig(max_credit=2, max_buffer=2))
        s.grant(2)
        s.write(1); s.write(2)
        with self.assertRaises(stream.CreditExhausted): s.write(3)
        self.assertEqual([s.read(), s.read()], [1, 2])
        self.assertIs(s.read(), stream.NOT_READY)

    def test_credit_limit_is_enforced_without_mutation(self):
        s = stream.Stream(str, config=stream.StreamConfig(max_credit=2, max_buffer=2))
        s.grant(2)
        with self.assertRaises(stream.CreditLimitExceeded): s.grant(1)
        self.assertEqual(s.credit, 2)

    def test_buffer_limit_is_independent_fail_closed_guard(self):
        s = stream.Stream(int, config=stream.StreamConfig(max_credit=4, max_buffer=1))
        s.grant(2); s.write(1)
        with self.assertRaises(stream.BufferLimitExceeded): s.write(2)
        self.assertEqual(s.credit, 1)
        self.assertEqual(list(s.buffer), [1])

    def test_type_validation_and_bool_int_confusion(self):
        s = stream.Stream(int)
        s.grant(1)
        with self.assertRaises(stream.ElementTypeMismatch): s.write(True)
        self.assertEqual(s.credit, 1)
        self.assertEqual(stream.ElementTypeMismatch("bad").as_dict()["code"], "PK_STREAM_TYPE_MISMATCH")

    def test_graceful_end_drains_buffer_then_eof(self):
        s = stream.Stream(str)
        s.grant(1); s.write("x"); s.end()
        self.assertEqual(s.read(), "x")
        self.assertIsNone(s.read())
        with self.assertRaises(stream.StreamClosed): s.write("late")
        with self.assertRaises(stream.StreamClosed): s.grant(1)

    def test_reader_drop_reclaims_buffer_and_writer_errors(self):
        s = stream.Stream(bytes)
        s.grant(2); s.write(b"a"); s.write(b"b")
        s.drop_reader()
        self.assertEqual(len(s.buffer), 0)
        self.assertEqual(s.stats().dropped_items, 2)
        with self.assertRaises(stream.EndDropped): s.write(b"c")
        with self.assertRaises(stream.EndDropped): s.read()

    def test_writer_drop_allows_drain_then_reports_drop(self):
        s = stream.Stream(str)
        s.grant(1); s.write("a"); s.drop_writer()
        self.assertEqual(s.read(), "a")
        with self.assertRaises(stream.EndDropped): s.read()

    def test_thread_safe_producer_consumer_accounting(self):
        count = 500
        s = stream.Stream(int, config=stream.StreamConfig(max_credit=count, max_buffer=count))
        s.grant(count)
        errors = []
        def writer():
            try:
                for i in range(count): s.write(i)
                s.end()
            except Exception as exc:  # pragma: no cover - failure capture
                errors.append(exc)
        t = threading.Thread(target=writer)
        t.start(); t.join()
        got = []
        while True:
            value = s.read()
            if value is None: break
            self.assertIsNot(value, stream.NOT_READY)
            got.append(value)
        self.assertFalse(errors)
        self.assertEqual(got, list(range(count)))
        self.assertEqual(s.stats().transferred, count)
        self.assertEqual(s.stats().reads, count)

    def test_concurrent_writers_preserve_all_items(self):
        writers, each = 4, 200
        total = writers * each
        s = stream.Stream(tuple, config=stream.StreamConfig(max_credit=total, max_buffer=total))
        s.grant(total)
        threads = []
        for w in range(writers):
            threads.append(threading.Thread(target=lambda wid=w: [s.write((wid, i)) for i in range(each)]))
        for t in threads: t.start()
        for t in threads: t.join()
        values = [s.read() for _ in range(total)]
        self.assertEqual(len(set(values)), total)
        self.assertEqual(s.stats().transferred, total)
        self.assertEqual(s.stats().buffered, 0)

    def test_config_rejects_bool_and_nonpositive_values(self):
        for value in (True, 0, -1):
            with self.assertRaises(ValueError): stream.StreamConfig(max_credit=value)


if __name__ == "__main__":
    unittest.main()
