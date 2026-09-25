"""C025: timeout, cancellation, retry and idempotency semantics; C059 freeze at stream level."""
import threading
import time
import unittest

from _pkg import stream as S


class TimeoutCancelTest(unittest.TestCase):
    def test_read_wait_times_out_without_inferring_eof(self):
        s = S.Stream(int)
        t0 = time.monotonic()
        with self.assertRaises(S.StreamTimeout) as cm:
            s.read_wait(timeout=0.05)
        self.assertGreaterEqual(time.monotonic() - t0, 0.04)
        self.assertEqual(cm.exception.code, "PK_STREAM_TIMEOUT")
        self.assertEqual(s.state, "credit_stalled")  # not ended: timeout is not EOS
        self.assertIs(s.read(), S.NOT_READY)

    def test_read_wait_wakes_on_write_and_on_end(self):
        s = S.Stream(int); s.grant(1)
        threading.Timer(0.02, lambda: s.write(7)).start()
        self.assertEqual(s.read_wait(timeout=2), 7)
        threading.Timer(0.02, s.end).start()
        self.assertIsNone(s.read_wait(timeout=2))

    def test_read_wait_reports_drop(self):
        s = S.Stream(int)
        threading.Timer(0.02, s.drop_writer).start()
        with self.assertRaises(S.EndDropped):
            s.read_wait(timeout=2)

    def test_cancellation(self):
        s = S.Stream(int)
        tok = S.CancelToken()
        threading.Timer(0.02, lambda: tok.cancel("shutdown")).start()
        with self.assertRaises(S.StreamCancelled) as cm:
            s.read_wait(timeout=5, cancel=tok)
        self.assertEqual(cm.exception.details["reason"], "shutdown")
        pre = S.CancelToken(); pre.cancel()
        with self.assertRaises(S.StreamCancelled):
            s.write_wait(1, timeout=5, cancel=pre)

    def test_write_wait_waits_for_credit(self):
        s = S.Stream(int)
        threading.Timer(0.02, lambda: s.grant(1)).start()
        self.assertTrue(s.write_wait(3, timeout=2))
        with self.assertRaises(S.StreamTimeout):
            s.write_wait(4, timeout=0.03)
        self.assertEqual(s.credit_stalls, 0)  # a bounded wait is not a refused write

    def test_write_wait_surfaces_reader_drop(self):
        s = S.Stream(int)
        threading.Timer(0.02, s.drop_reader).start()
        with self.assertRaises(S.EndDropped):
            s.write_wait(1, timeout=2)

    def test_invalid_timeout(self):
        s = S.Stream(int)
        for bad in (-1, True, "1"):
            with self.assertRaises(ValueError):
                s.read_wait(timeout=bad)


class IdempotencyTest(unittest.TestCase):
    def test_retry_with_same_key_enqueues_once(self):
        s = S.Stream(str); s.grant(3)
        self.assertTrue(s.write("a", idempotency_key="k1"))
        self.assertFalse(s.write("a", idempotency_key="k1"))
        self.assertEqual(s.credit, 2)
        self.assertEqual(list(s.buffer), ["a"])
        self.assertEqual(s.stats().duplicate_writes, 1)

    def test_type_is_checked_before_duplicate_ack(self):
        s = S.Stream(str); s.grant(2)
        s.write("a", idempotency_key="k")
        with self.assertRaises(S.ElementTypeMismatch):
            s.write(1, idempotency_key="k")

    def test_window_is_bounded(self):
        s = S.Stream(int, config=S.StreamConfig(max_credit=10, max_buffer=10, idempotency_window=2))
        s.grant(4)
        for k in ("a", "b", "c"):
            s.write(1, idempotency_key=k)
        self.assertTrue(s.write(1, idempotency_key="a"))  # evicted from the window -> new write
        self.assertEqual(len(s._seen_set), 2)

    def test_bad_key(self):
        s = S.Stream(int); s.grant(1)
        for bad in ("", 5):
            with self.assertRaises(ValueError):
                s.write(1, idempotency_key=bad)

    def test_retry_after_timeout_is_safe(self):
        s = S.Stream(int)
        with self.assertRaises(S.StreamTimeout):
            s.write_wait(1, timeout=0.02, idempotency_key="op-1")
        s.grant(2)
        self.assertTrue(s.write_wait(1, timeout=1, idempotency_key="op-1"))
        self.assertFalse(s.write_wait(1, timeout=1, idempotency_key="op-1"))
        self.assertEqual(s.transferred, 1)


class FreezeTest(unittest.TestCase):
    def test_freeze_refuses_writes_and_grants_but_allows_drain(self):
        s = S.Stream(int); s.grant(2); s.write(1)
        s.freeze("incident-42")
        self.assertEqual(s.state, "frozen")
        with self.assertRaises(S.StreamFrozen): s.write(2)
        with self.assertRaises(S.StreamFrozen): s.grant(1)
        self.assertEqual(s.read(), 1)
        s.unfreeze(); s.write(2)
        self.assertEqual(s.read(), 2)

    def test_config_type_checked(self):
        with self.assertRaises(TypeError):
            S.Stream(int, config={"max_credit": 1})


if __name__ == "__main__":
    unittest.main()
