"""Standalone tests for the completion primitive; no pk_core dependency."""
from __future__ import annotations

import importlib.util
import pathlib
import threading
import unittest

MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "future.py"
spec = importlib.util.spec_from_file_location("inv18_future_standalone", MODULE_PATH)
future_mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(future_mod)

Future = future_mod.Future
AlreadyResolved = future_mod.AlreadyResolved
AlreadyTaken = future_mod.AlreadyTaken
Abandoned = future_mod.Abandoned


class FutureTest(unittest.TestCase):
    def test_success_is_one_shot(self):
        """REQ: C081 C015 INV18-FR-001 INV18-FR-002 INV18-FR-007"""
        f = Future(str)
        self.assertIsNone(f.take())
        f.resolve("done")
        self.assertEqual(f.take(), ("ok", "done"))
        with self.assertRaises(AlreadyTaken):
            f.take()
        with self.assertRaises(AlreadyResolved):
            f.resolve("again")

    def test_error_is_one_shot(self):
        """REQ: C081 INV18-FR-004 INV18-FR-007"""
        f = Future(str)
        f.resolve_error("upstream refused")
        self.assertEqual(f.take(), ("error", "upstream refused"))
        with self.assertRaises(AlreadyResolved):
            f.resolve_error("again")
        with self.assertRaises(AlreadyResolved):
            f.resolve_error("")

    def test_error_must_be_nonempty_string(self):
        """REQ: C081 INV18-FR-004 INV18-FR-009"""
        for bad in (None, "", 0, False):
            with self.subTest(bad=bad):
                f = Future(str)
                with self.assertRaises(TypeError):
                    f.resolve_error(bad)  # type: ignore[arg-type]
                self.assertFalse(f.resolved)

    def test_bool_is_not_int_payload(self):
        """REQ: C081 INV18-FR-003"""
        f = Future(int)
        with self.assertRaises(TypeError):
            f.resolve(True)
        self.assertFalse(f.resolved)

    def test_abandonment_is_terminal_for_writer(self):
        """REQ: C081 INV18-FR-005 INV18-FR-006"""
        f = Future(str)
        f.abandon()
        self.assertTrue(f.abandoned)
        with self.assertRaises(Abandoned):
            f.take()
        with self.assertRaises(AlreadyTaken):
            f.take()
        with self.assertRaises(AlreadyResolved):
            f.resolve("late")
        with self.assertRaises(AlreadyResolved):
            f.resolve_error("late")

    def test_abandon_after_resolution_is_noop(self):
        """REQ: C081 C015"""
        f = Future(str)
        f.resolve("done")
        f.abandon()
        self.assertFalse(f.abandoned)
        self.assertEqual(f.take(), ("ok", "done"))

    def test_concurrent_resolution_has_exactly_one_winner(self):
        """REQ: C086 INV18-FR-010"""
        f = Future(int)
        barrier = threading.Barrier(16)
        winners: list[int] = []
        rejected: list[int] = []
        guard = threading.Lock()

        def worker(value: int) -> None:
            barrier.wait()
            try:
                f.resolve(value)
                with guard:
                    winners.append(value)
            except AlreadyResolved:
                with guard:
                    rejected.append(value)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(winners), 1)
        self.assertEqual(len(rejected), 15)
        self.assertEqual(f.take(), ("ok", winners[0]))

    def test_concurrent_take_has_exactly_one_winner(self):
        """REQ: C086 INV18-FR-011"""
        f = Future(str)
        f.resolve("done")
        barrier = threading.Barrier(16)
        winners = []
        rejected = []
        guard = threading.Lock()

        def worker() -> None:
            barrier.wait()
            try:
                result = f.take()
                with guard:
                    winners.append(result)
            except AlreadyTaken:
                with guard:
                    rejected.append(True)

        threads = [threading.Thread(target=worker) for _ in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(winners, [("ok", "done")])
        self.assertEqual(len(rejected), 15)


class FutureV43Test(unittest.TestCase):
    """New v4.3.0 behaviour of the bare primitive."""

    def test_state_property_and_lifecycle(self):
        """REQ: C015 C081"""
        f = Future(int)
        self.assertEqual(f.state, "PENDING")
        f.resolve(3)
        self.assertEqual(f.state, "VALUE")
        g = Future(int); g.resolve_error("e"); self.assertEqual(g.state, "ERROR")
        h = Future(int); h.abandon(); self.assertEqual(h.state, "ABANDONED")
        c = Future(int); c.cancel(); self.assertEqual(c.state, "CANCELLED")

    def test_cancel_is_terminal_and_refuses_resolution(self):
        """REQ: C025 INV18-FR-013"""
        f = Future(int)
        self.assertTrue(f.cancel())
        self.assertFalse(f.cancel())
        with self.assertRaises(future_mod.Cancelled) as cm:
            f.resolve(1)
        self.assertEqual(cm.exception.code, "FUTURE_CANCELLED")
        with self.assertRaises(AlreadyTaken):
            f.take()
        g = Future(int); g.resolve(1)
        self.assertFalse(g.cancel())            # cancel after resolution is a no-op
        self.assertEqual(g.take(), ("ok", 1))

    def test_resolve_cancel_race_has_one_winner(self):
        """REQ: C025 C086 INV18-FR-001"""
        for _ in range(200):
            f = Future(int)
            b = threading.Barrier(2)
            res = {}
            def p():
                b.wait()
                try:
                    f.resolve(1); res["r"] = True
                except future_mod.Cancelled:
                    res["r"] = False
            def c():
                b.wait(); res["c"] = f.cancel()
            ts = [threading.Thread(target=p), threading.Thread(target=c)]
            [t.start() for t in ts]; [t.join() for t in ts]
            self.assertNotEqual(res["r"], res["c"])

    def test_wait_timeout_does_not_change_state(self):
        """REQ: C025 INV18-FR-015"""
        f = Future(int)
        self.assertFalse(f.wait(0.01))
        self.assertEqual(f.state, "PENDING")
        self.assertIsNone(f.take())
        threading.Timer(0.02, lambda: f.resolve(9)).start()
        self.assertTrue(f.wait(2))
        self.assertEqual(f.take(), ("ok", 9))
        with self.assertRaises(ValueError):
            f.wait(-1)

    def test_happens_before_visibility(self):
        """REQ: C086 INV18-FR-012"""
        for _ in range(100):
            f = Future(list)
            payload = []
            def producer():
                payload.extend(range(100))
                f.resolve(payload)
            t = threading.Thread(target=producer); t.start()
            self.assertTrue(f.wait(5))
            tag, v = f.take()
            self.assertEqual(len(v), 100)
            t.join()

    def test_error_message_bounded(self):
        """REQ: C028 INV18-FR-004"""
        f = Future(int)
        with self.assertRaises(ValueError):
            f.resolve_error("x" * 4097)
        self.assertEqual(f.state, "PENDING")
        f.resolve_error("x" * 4096)

    def test_state_error_precedes_argument_error(self):
        """REQ: C014 INV18-FR-009"""
        f = Future(int); f.resolve(1)
        with self.assertRaises(AlreadyResolved):
            f.resolve("bad type")
        g = Future(int); g.abandon()
        with self.assertRaises(AlreadyResolved):
            g.resolve_error(None)  # type: ignore[arg-type]

    def test_exceptions_carry_stable_codes(self):
        """REQ: C026"""
        self.assertEqual(AlreadyResolved.code, "FUTURE_ALREADY_RESOLVED")
        self.assertEqual(AlreadyTaken.code, "FUTURE_ALREADY_TAKEN")
        self.assertEqual(Abandoned.code, "FUTURE_ABANDONED")

    def test_payload_released_after_take(self):
        """REQ: C067 INV18-NFR-002"""
        import gc, weakref
        class P: pass
        f = Future(P); p = P(); w = weakref.ref(p)
        f.resolve(p); del p
        f.take(); gc.collect()
        self.assertIsNone(w())

    def test_observer_exception_never_breaks_transition(self):
        """REQ: C056 C081"""
        def boom(ev, fut):
            raise RuntimeError("telemetry down")
        f = Future(int, observer=boom)
        f.resolve(1)
        self.assertEqual(f.take(), ("ok", 1))


if __name__ == "__main__":
    unittest.main()
