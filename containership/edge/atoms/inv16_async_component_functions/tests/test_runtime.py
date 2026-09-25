"""Stdlib-only runtime tests for INV-16; no pk_core dependency required."""
from __future__ import annotations

import importlib.util
import pathlib
import threading
import unittest
import sys

RUNTIME = pathlib.Path(__file__).resolve().parents[1] / "runtime.py"
spec = importlib.util.spec_from_file_location("inv16_runtime", RUNTIME)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
assert spec.loader is not None
spec.loader.exec_module(mod)


class RuntimeTest(unittest.TestCase):
    def test_declarations_are_frozen_and_validated(self):
        source = {"fetch": True}
        fns = mod.AsyncFunctions("i", declared=source)
        source["fetch"] = False
        self.assertTrue(fns.is_async("fetch"))
        with self.assertRaises(TypeError):
            fns.declared["fetch"] = False
        with self.assertRaises(ValueError):
            fns.is_async("missing")

    def test_exactly_once_and_terminal_reason(self):
        fns = mod.AsyncFunctions("i", declared={"fetch": True})
        call = fns.invoke("fetch")
        self.assertEqual(fns.complete(call.call_id, 7), 7)
        with self.assertRaises(mod.DoubleDelivery):
            fns.complete(call.call_id, 8)
        self.assertEqual(fns.double_delivery_attempts, 1)

        cancelled = fns.invoke("fetch")
        fns.cancel(cancelled.call_id)
        with self.assertRaises(mod.CallCancelled):
            fns.complete(cancelled.call_id, 9)

    def test_concurrency_limit_and_reentrancy(self):
        fns = mod.AsyncFunctions(
            "i", declared={"step": True, "other": True},
            stateful=frozenset({"step"}), concurrency_limit=2)
        fns.invoke("step")
        with self.assertRaises(mod.ReentrancyRefused):
            fns.invoke("step")
        fns.invoke("other")
        with self.assertRaises(mod.ConcurrencyLimitReached):
            fns.invoke("other")

    def test_trap_clears_calls_and_rejects_late_delivery(self):
        fns = mod.AsyncFunctions("i", declared={"fetch": True})
        calls = [fns.invoke("fetch") for _ in range(3)]
        self.assertEqual(fns.trap_all(), 3)
        self.assertEqual(fns.calls_in_flight, 0)
        with self.assertRaises(mod.CallTrapped):
            fns.complete(calls[0].call_id, "late")

    def test_parallel_issue_produces_unique_ids(self):
        fns = mod.AsyncFunctions("i", declared={"fetch": True}, concurrency_limit=500)
        ids = []
        ids_lock = threading.Lock()

        def issue():
            local = [fns.invoke("fetch").call_id for _ in range(25)]
            with ids_lock:
                ids.extend(local)

        threads = [threading.Thread(target=issue) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(ids), 200)
        self.assertEqual(len(set(ids)), 200)
        self.assertEqual(fns.calls_in_flight, 200)


if __name__ == "__main__":
    unittest.main()
