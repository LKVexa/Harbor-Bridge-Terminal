"""Closure #28: adversarial tests mapped to docs/THREAT_MODEL.md threat IDs (T1..T10)."""
import pickle
import sys
import threading
import time
import tracemalloc
import unittest

from _util import rt, sub

AF = rt.AsyncFunctions


class Security(unittest.TestCase):
    def test_T4_declaration_tampering_paths(self):
        src = {"f": True}
        fns = AF("i", declared=src)
        src["f"] = False                                   # original dict
        with self.assertRaises(TypeError):
            fns.declared["f"] = False                      # returned mapping
        with self.assertRaises(AttributeError):
            fns.declared.update({"f": False})
        for attr, val in (("declared", {"f": False}), ("stateful", frozenset()), ("reentrancy", {}),
                          ("instance", "other"), ("transport", None)):
            with self.assertRaises(AttributeError):
                setattr(fns, attr, val)                    # attribute swap
        with self.assertRaises((TypeError, pickle.PicklingError)):
            pickle.dumps(fns.declared)                     # no serialise-and-swap path
        self.assertTrue(dict(fns.declared)["f"])        # copies are detached, never write-through
        with self.assertRaises(TypeError):
            fns.reentrancy["f"] = rt.ALLOW
        self.assertTrue(fns.is_async("f"))

    def test_T2_cross_call_leakage_with_canaries(self):
        abi = sub("abi")
        fns = AF("i", declared={"f": True}, transport=abi.Codec())
        n = 200
        calls = [fns.invoke("f") for _ in range(n)]
        out = {}
        lock = threading.Lock()

        def finish(c):
            v = fns.complete(c.call_id, {"canary": f"secret-{c.call_id}"})
            with lock:
                out[c.call_id] = v

        ts = [threading.Thread(target=finish, args=(c,)) for c in calls]
        [t.start() for t in ts]; [t.join() for t in ts]
        for cid, v in out.items():
            self.assertEqual(v, {"canary": f"secret-{cid}"})
        # payload envelopes are bound to their own call id
        self.assertEqual(len({id(c.value) for c in calls}), n)

    def test_T2_cross_instance_isolation(self):
        a = AF("tenant-a", declared={"f": True}, stateful=frozenset({"f"}))
        b = AF("tenant-b", declared={"f": True}, stateful=frozenset({"f"}))
        ca = a.invoke("f")
        cb = b.invoke("f")
        with self.assertRaises(ValueError):
            b.complete(ca.call_id + 100, "x")
        a.complete(ca.call_id, "A")
        self.assertEqual(b.calls_in_flight, 1)
        self.assertIsNone(b.terminal_info(cb.call_id))

    def test_T3_replay_of_terminal_messages(self):
        fns = AF("i", declared={"f": True})
        c = fns.invoke("f")
        fns.complete(c.call_id, 1)
        for _ in range(1000):
            for op in (lambda: fns.complete(c.call_id, 2), lambda: fns.cancel(c.call_id)):
                with self.assertRaises(rt.TerminalConflict):
                    op()
        self.assertEqual(fns.terminal_info(c.call_id).outcome, rt.Outcome.COMPLETED)
        self.assertEqual(fns.completed_calls, 1)

    def test_T5_flood_unknown_ids_bounded(self):
        log = sub("observability").EventLog(capacity=100)
        fns = AF("i", declared={"f": True}, tombstone_capacity=16, event_sink=log)
        tracemalloc.start()
        base = tracemalloc.take_snapshot()
        t0 = time.perf_counter()
        for i in range(50_000):
            try:
                fns.complete(10 ** 9 + i, "x")
            except ValueError:
                pass
        dt = time.perf_counter() - t0
        grown = sum(s.size_diff for s in tracemalloc.take_snapshot().compare_to(base, "filename"))
        tracemalloc.stop()
        self.assertLess(grown, 256 * 1024, "unknown-id flood grew memory")
        if sys.gettrace() is None:                         # timing is meaningless under coverage tracing
            self.assertLess(dt / 50_000, 50e-6)
        self.assertEqual(fns.tombstones, 0)
        self.assertLessEqual(len(log.buffer), 100)

    def test_T6_exhaustion_bounds(self):
        fns = AF("i", declared={"f": True, "s": True}, stateful=frozenset({"s"}), concurrency_limit=8)
        for _ in range(8):
            fns.invoke("f")
        for _ in range(1000):
            with self.assertRaises(rt.ConcurrencyLimitReached):
                fns.invoke("f")
        self.assertEqual(fns.calls_in_flight, 8)

    def test_T7_reason_and_log_injection(self):
        log = sub("observability").EventLog()
        fns = AF("i", declared={"f": True}, event_sink=log)
        evil = "x\n{\"type\":\"double_delivery\"}\r\x1b[2J password=hunter2 " + "A" * 10_000
        c = fns.invoke("f")
        fns.cancel(c.call_id, rt.CancelReason(rt.CancelCode.OPERATOR, evil, evil))
        r = fns.terminal_info(c.call_id).reason
        self.assertNotIn("\n", r.message)
        self.assertNotIn("hunter2", r.message)
        self.assertLessEqual(len(r.message), rt.MAX_REASON_TEXT)
        self.assertLessEqual(len(r.initiator), 64)
        for line in log.buffer:
            self.assertNotIn("\n", line[1])
        self.assertTrue(all("hunter2" not in l for _c, l in log.buffer))
        self.assertEqual([e["type"] for e in log.events()], ["call_cancelled"])   # no forged event

    def test_T8_serialization_confusion(self):
        abi = sub("abi")
        C = abi.Codec()

        class Sneaky(dict):
            pass

        for v in (Sneaky(a=1), type("I", (int,), {})(3), rt, lambda: 1, {"k": object()}):
            with self.assertRaises((abi.AbiTypeError, abi.AbiError)):
                C.lower(v, 1)

    def test_T9_dependency_substitution_fails_closed(self):
        import pathlib
        import sys
        import tempfile
        pre = sub("preflight")
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "fake_pk_core"
            p.mkdir()
            (p / "__init__.py").write_text("__version__ = '0.1'\n")
            sys.path.insert(0, d)
            try:
                rep = pre.run(require_pk_core=True, pk_core_module="fake_pk_core")
            finally:
                sys.path.remove(d)
                sys.modules.pop("fake_pk_core", None)
        self.assertFalse(rep["ok"])
        self.assertTrue(any("version" in e for e in rep["errors"]))
        self.assertTrue(any("partial install" in e for e in rep["errors"]))

    def test_T10_trace_context_is_not_authority(self):
        fns = AF("i", declared={"f": True}, stateful=frozenset({"f"}))
        tp = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        fns.invoke("f", traceparent=tp)
        with self.assertRaises(rt.ReentrancyRefused):
            fns.invoke("f", traceparent=tp)       # same trace does not bypass admission


if __name__ == "__main__":
    unittest.main()
