"""4.3.0 lifecycle semantics: reasons, policies, tombstones, call ids, generations, trace, events."""
import unittest

from _util import rt, sub

AF = rt.AsyncFunctions


class CancellationReasons(unittest.TestCase):  # closure #10
    def test_reason_retained_and_first_cause_wins(self):
        f = AF("i", declared={"a": True})
        c = f.invoke("a")
        f.cancel(c.call_id, rt.CancelReason(rt.CancelCode.DEADLINE, "slow", "gw"))
        with self.assertRaises(rt.AlreadyTerminal) as cm:
            f.cancel(c.call_id, rt.CancelReason(rt.CancelCode.OPERATOR, "abort"))
        self.assertEqual(cm.exception.tombstone.reason.code, rt.CancelCode.DEADLINE)
        info = f.terminal_info(c.call_id)
        self.assertEqual((info.outcome, info.reason.code, info.reason.message),
                         (rt.Outcome.CANCELLED, rt.CancelCode.DEADLINE, "slow"))
        with self.assertRaises(rt.CallCancelled) as late:
            f.complete(c.call_id, 1)
        self.assertEqual(late.exception.tombstone.reason.code, rt.CancelCode.DEADLINE)
        self.assertEqual(f.double_delivery_attempts, 0)

    def test_cancel_all_shares_one_batch_cause(self):
        f = AF("i", declared={"a": True})
        ids = [f.invoke("a").call_id for _ in range(4)]
        self.assertEqual(f.cancel_all(rt.CancelReason(rt.CancelCode.SHUTDOWN, "drain")), 4)
        reasons = {id(f.terminal_info(i).reason) for i in ids}
        self.assertEqual(len(reasons), 1)
        self.assertEqual(f.terminal_info(ids[0]).reason.code, rt.CancelCode.SHUTDOWN)

    def test_string_reason_back_compat_and_sanitised(self):
        f = AF("i", declared={"a": True})
        c = f.invoke("a")
        f.cancel(c.call_id, "boom\x00\x1b[31m token=abc123 " + "x" * 500)
        r = f.terminal_info(c.call_id).reason
        self.assertEqual(r.code, rt.CancelCode.CALLER)
        self.assertNotIn("\x00", r.message)
        self.assertNotIn("abc123", r.message)
        self.assertLessEqual(len(r.message), rt.MAX_REASON_TEXT)
        c2 = f.invoke("a")
        f.cancel(c2.call_id, "deadline")
        self.assertEqual(f.terminal_info(c2.call_id).reason.code, rt.CancelCode.DEADLINE)

    def test_cancel_after_complete_is_not_double_delivery(self):
        f = AF("i", declared={"a": True})
        c = f.invoke("a")
        f.complete(c.call_id, 1)
        with self.assertRaises(rt.AlreadyTerminal):
            f.cancel(c.call_id)
        self.assertEqual(f.double_delivery_attempts, 0)
        self.assertEqual(f.terminal_info(c.call_id).outcome, rt.Outcome.COMPLETED)


class Policies(unittest.TestCase):  # closure #11
    def test_config_validation(self):
        P, M = rt.ReentrancyPolicy, rt.ReentrancyMode
        with self.assertRaises(ValueError):
            AF("i", declared={"a": True}, stateful=frozenset({"a"}), reentrancy={"a": rt.ALLOW})
        with self.assertRaises(ValueError):
            AF("i", declared={"a": True}, reentrancy={"zz": rt.REFUSE})
        with self.assertRaises(ValueError):
            P(M.QUEUE, 0)
        with self.assertRaises(ValueError):
            P(M.REFUSE, 3)
        with self.assertRaises(ValueError):
            P("bogus")
        with self.assertRaises(TypeError):
            AF("i", declared={"a": True}, reentrancy={"a": "refuse"})

    def test_stateful_defaults_to_refuse(self):
        f = AF("i", declared={"a": True}, stateful=frozenset({"a"}))
        self.assertEqual(f.reentrancy["a"].mode, rt.ReentrancyMode.REFUSE)

    def test_queue_fifo_bounded_and_cancel_queued(self):
        f = AF("i", declared={"s": True}, reentrancy={"s": rt.ReentrancyPolicy(rt.ReentrancyMode.QUEUE, 2)})
        a = f.invoke("s")
        b = f.invoke("s")
        c = f.invoke("s")
        self.assertEqual((a.status, b.status, c.status), ("live", "queued", "queued"))
        with self.assertRaises(rt.ReentrancyQueueFull):
            f.invoke("s")
        self.assertEqual(f.queue_refusals, 1)
        with self.assertRaises(rt.CallNotStarted):
            f.complete(b.call_id, 0)
        f.cancel(b.call_id, "operator")          # queued entry never executes
        f.complete(a.call_id, 1)
        self.assertEqual(c.status, "live")       # FIFO promotion skipped the cancelled one
        self.assertEqual(f.calls_in_flight, 1)
        self.assertEqual(f.calls_queued, 0)
        f.complete(c.call_id, 2)
        self.assertEqual(f.snapshot()["calls_in_flight"], 0)

    def test_queue_respects_concurrency_limit(self):
        f = AF("i", declared={"s": True, "o": True}, concurrency_limit=2,
               reentrancy={"s": rt.ReentrancyPolicy(rt.ReentrancyMode.QUEUE, 4)})
        a = f.invoke("s")
        f.invoke("s")
        f.invoke("o")
        with self.assertRaises(rt.ConcurrencyLimitReached):
            f.invoke("o")
        f.complete(a.call_id, None)
        self.assertLessEqual(f.calls_in_flight, 2)

    def test_allow_permits_overlap(self):
        f = AF("i", declared={"a": True})
        f.invoke("a")
        f.invoke("a")
        self.assertEqual(f.calls_in_flight, 2)


class Tombstones(unittest.TestCase):  # closure #12
    def test_bounded_and_expired_classification(self):
        f = AF("i", declared={"a": True}, tombstone_capacity=8)
        ids = []
        for _ in range(100):
            c = f.invoke("a")
            f.complete(c.call_id, 0)
            ids.append(c.call_id)
        self.assertEqual(f.tombstones, 8)
        self.assertEqual(f.tombstone_evictions, 92)
        with self.assertRaises(rt.DoubleDelivery):
            f.complete(ids[-1], 0)             # inside the window: duplicate detected
        with self.assertRaises(rt.HistoryExpired):
            f.complete(ids[0], 0)              # outside: issued-but-expired, not "never issued"
        with self.assertRaises(ValueError) as cm:
            f.complete(10_000, 0)
        self.assertNotIsInstance(cm.exception, rt.HistoryExpired)
        self.assertEqual(f.expired_late_events, 1)

    def test_hostile_late_events_do_not_extend_retention(self):
        f = AF("i", declared={"a": True}, tombstone_capacity=2)
        first = f.invoke("a"); f.complete(first.call_id, 0)
        for _ in range(50):
            with self.assertRaises(rt.DoubleDelivery):
                f.complete(first.call_id, 0)
        for _ in range(2):
            c = f.invoke("a"); f.complete(c.call_id, 0)
        with self.assertRaises(rt.HistoryExpired):
            f.complete(first.call_id, 0)


class CallIds(unittest.TestCase):  # closure #13
    def test_reduced_width_exhaustion_fails_closed(self):
        f = AF("i", declared={"a": True}, call_id_bits=3)   # ids 1..7
        seen = []
        for _ in range(7):
            c = f.invoke("a"); seen.append(c.call_id); f.complete(c.call_id, 0)
        self.assertEqual(seen, list(range(1, 8)))
        with self.assertRaises(rt.CallIdExhausted):
            f.invoke("a")
        self.assertTrue(f.snapshot()["call_id_near_exhaustion"])

    def test_generation_renewal_rejects_stale(self):
        f = AF("i", declared={"a": True}, call_id_bits=3, require_generation=True)
        old = f.invoke("a")
        with self.assertRaises(rt.StaleGeneration):
            f.complete(old.call_id, 0)                     # generation mandatory
        with self.assertRaises(RuntimeError):
            f.renew_generation()                           # not drained
        f.complete(old.call_id, 0, generation=0)
        self.assertEqual(f.renew_generation(), 1)
        new = f.invoke("a")
        self.assertEqual(new.call_id, old.call_id)         # numerically reused ...
        with self.assertRaises(rt.StaleGeneration):
            f.complete(old.call_id, "late", generation=0)  # ... but never aliased
        self.assertEqual(f.complete(new.call_id, "ok", generation=1), "ok")

    def test_encode_decode_and_validation(self):
        a = rt.CallIdAllocator(16)
        self.assertEqual(a.decode(a.encode(513)), 513)
        for bad in (0, 1 << 16, -1):
            with self.assertRaises(ValueError):
                a.encode(bad)
        with self.assertRaises(ValueError):
            a.decode(b"\x00" * 8)
        f = AF("i", declared={"a": True})
        for bad in (True, -1, 0, "1", None, 1.0, 1 << 80):
            with self.assertRaises(ValueError):
                f.complete(bad, 0)


class TraceAndEvents(unittest.TestCase):  # closure #24/#25
    TP = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"

    def test_trace_child_span_and_rejection(self):
        f = AF("i", declared={"a": True}, tracing=True)
        c = f.invoke("a", traceparent=self.TP)
        self.assertEqual(c.trace.trace_id, "4bf92f3577b34da6a3ce929d0e0e4736")
        self.assertEqual(c.trace.parent_span_id, "00f067aa0ba902b7")
        self.assertNotEqual(c.trace.span_id, "00f067aa0ba902b7")
        for bad in ("garbage", "00-" + "0" * 32 + "-00f067aa0ba902b7-01", "01-x-y-z", "x" * 500):
            d = f.invoke("a", traceparent=bad)
            self.assertIsNotNone(d.trace)            # new root, never trusted
        self.assertEqual(f.trace_context_rejected, 4)

    def test_events_schema_and_no_payload(self):
        log = sub("observability").EventLog()
        f = AF("i", declared={"a": True}, stateful=frozenset({"a"}), event_sink=log)
        c = f.invoke("a", traceparent=self.TP)
        with self.assertRaises(rt.ReentrancyRefused):
            f.invoke("a")
        f.complete(c.call_id, {"secret": "payload-XYZ"})
        with self.assertRaises(rt.DoubleDelivery):
            f.complete(c.call_id, 1)
        evs = log.events()
        types = [e["type"] for e in evs]
        self.assertEqual(types, ["reentrancy_refused", "call_completed", "double_delivery"])
        for e in evs:
            self.assertEqual(e["schema"], "inv16.event/1")
            self.assertNotIn("payload-XYZ", str(e))
        self.assertEqual(evs[1]["trace_id"], "4bf92f3577b34da6a3ce929d0e0e4736")
        self.assertEqual([e["seq"] for e in evs], sorted(e["seq"] for e in evs))

    def test_prometheus_export_bounded_labels(self):
        obs = sub("observability")
        f = AF("inst\"1\n", declared={"a": True})
        f.invoke("a")
        h = obs.Histogram()
        h.record(3000)
        text = obs.prometheus_text([f.snapshot()], {"inv16_bridge_latency_ns": h},
                                   resource={"version": "4.3.0", "abi": "PK_ASYNC_INVOKE/1"})
        self.assertIn('inv16_calls_in_flight{instance="inst_1_",function="a"} 1', text)
        self.assertIn("inv16_double_delivery_attempts_total", text)
        self.assertIn('inv16_bridge_latency_ns_bucket{le="4096"} 1', text)
        for name in obs.METRICS:
            self.assertIn(f"# TYPE {name}", text)
        self.assertNotIn("call_id=", text)


if __name__ == "__main__":
    unittest.main()
