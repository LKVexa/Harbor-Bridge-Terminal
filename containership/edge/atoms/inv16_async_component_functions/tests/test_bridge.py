"""Closure #7: sync->async bridge semantics, stress, misuse and interruption."""
import asyncio
import threading
import time
import unittest

from _util import rt, scale, sub

br = sub("bridge")
AF = rt.AsyncFunctions


def later(f, delay, value=None, op="complete"):
    def go(st):
        def run():
            time.sleep(delay)
            try:
                if op == "complete":
                    f.complete(st.call_id, value)
                elif op == "trap":
                    f.trap_all()
            except rt.TerminalConflict:
                pass
        threading.Thread(target=run, daemon=True).start()
    return go


class Bridge(unittest.TestCase):
    def setUp(self):
        self.f = AF("i", declared={"a": True, "s": False})
        self.b = br.SyncBridge(self.f)

    def test_immediate_completion_fast_path(self):
        v = self.b.call("a", lambda st: self.f.complete(st.call_id, 42))
        self.assertEqual(v, 42)
        self.assertEqual(self.b.slow_path, 0)
        self.assertEqual(self.f.bridge_calls, 1)

    def test_delayed_completion(self):
        self.assertEqual(self.b.call("a", later(self.f, 0.02, "x")), "x")
        self.assertEqual(self.b.slow_path, 1)

    def test_timeout_cancels_with_deadline_code(self):
        with self.assertRaises(br.BridgeTimeout):
            self.b.call("a", lambda st: None, timeout=0.02)
        self.assertEqual(self.f.calls_in_flight, 0)
        (cid,) = [c for c in self.f._terminal]
        self.assertEqual(self.f.terminal_info(cid).reason.code, rt.CancelCode.DEADLINE)

    def test_cancel_before_and_during_wait(self):
        tok = br.CancelToken()
        tok.cancel(rt.CancelReason(rt.CancelCode.DISCONNECT))
        with self.assertRaises(rt.CallCancelled):
            self.b.call("a", lambda st: None, token=tok)
        tok2 = br.CancelToken()
        threading.Timer(0.02, tok2.cancel).start()
        with self.assertRaises(rt.CallCancelled):
            self.b.call("a", lambda st: None, token=tok2)
        self.assertEqual(self.f.calls_in_flight, 0)

    def test_trap_propagates_once(self):
        with self.assertRaises(rt.CallTrapped):
            self.b.call("a", later(self.f, 0.01, op="trap"))

    def test_start_failure_cleans_up(self):
        def boom(st):
            raise KeyError("callee failed to start")
        with self.assertRaises(KeyError):
            self.b.call("a", boom)
        self.assertEqual(self.f.calls_in_flight, 0)
        self.assertEqual(self.b.waiters, 0)

    def test_event_loop_thread_refused(self):
        async def main():
            with self.assertRaises(br.BridgeRefused):
                self.b.call("a", lambda st: self.f.complete(st.call_id, 1))
        asyncio.run(main())
        self.assertEqual(self.f.calls_in_flight, 0)

    def test_nesting_bounded(self):
        b = br.SyncBridge(self.f, max_depth=2)
        depth = []

        def nest(st):
            depth.append(1)
            try:
                inner = b.call("a", nest)
            except br.BridgeRefused:
                inner = "refused"
            self.f.complete(st.call_id, inner)

        self.assertEqual(b.call("a", nest), "refused")
        self.assertEqual(len(depth), 2)

    def test_waiter_bound(self):
        b = br.SyncBridge(self.f, max_waiters=2)
        hold = threading.Event()
        started = threading.Barrier(3)
        calls = []

        def park(st):
            calls.append(st)
            started.wait()

        ts = [threading.Thread(target=lambda: b.call("a", park, timeout=2)) for _ in range(2)]
        for t in ts:
            t.start()
        started.wait()
        with self.assertRaises(br.BridgeSaturated):
            b.call("a", lambda st: None)
        for st in calls:
            self.f.complete(st.call_id, None)
        for t in ts:
            t.join()
        self.assertEqual(b.waiters, 0)
        del hold

    def test_completion_racing_timeout_is_exactly_once(self):
        for _ in range(scale(200)):
            f = AF("i", declared={"a": True})
            b = br.SyncBridge(f)
            out = []
            try:
                out.append(b.call("a", later(f, 0.001, "v"), timeout=0.001))
            except br.BridgeTimeout:
                out.append("timeout")
            self.assertEqual(len(out), 1)
            self.assertEqual(f.completed_calls + f.cancelled_calls, 1)
            self.assertEqual(f.double_delivery_attempts, 0)

    def test_many_concurrent_bridged_calls_no_lost_wakeups(self):
        f = AF("i", declared={"a": True})
        b = br.SyncBridge(f, max_waiters=2000)
        results = []
        lock = threading.Lock()
        n = scale(400)

        def caller(k):
            v = b.call("a", later(f, 0.0005 * (k % 7), k), timeout=10)
            with lock:
                results.append(v)

        ts = [threading.Thread(target=caller, args=(k,)) for k in range(n)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(15)
        self.assertEqual(sorted(results), list(range(n)))
        self.assertEqual(f.calls_in_flight, 0)
        self.assertEqual(b.waiters, 0)

    def test_latency_recorded(self):
        obs = sub("observability")
        h = obs.Histogram()
        b = br.SyncBridge(self.f, latency_recorder=h.record)
        for _ in range(100):
            b.call("a", lambda st: self.f.complete(st.call_id, 1))
        self.assertEqual(h.total, 100)


if __name__ == "__main__":
    unittest.main()
