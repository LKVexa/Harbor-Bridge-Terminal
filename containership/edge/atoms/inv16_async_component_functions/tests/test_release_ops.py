"""Closures #37 (canary) and #38 (rollback) - executed, not just documented."""
import sys
import unittest

from _util import PKG_DIR, rt

sys.path.insert(0, str(PKG_DIR))
from tools import canary, rollback  # noqa: E402


class Rollback(unittest.TestCase):
    def test_rollback_with_in_flight_and_terminal_state(self):
        cur = rt.AsyncFunctions("svc", declared={"f": True, "q": True}, tombstone_capacity=4,
                                reentrancy={"q": rt.ReentrancyPolicy(rt.ReentrancyMode.QUEUE, 2)})
        done = cur.invoke("f"); cur.complete(done.call_id, 1)
        live = [cur.invoke("f") for _ in range(5)]
        cur.invoke("q"); cur.invoke("q")
        fence, rec = rollback.rollback(cur, drain_timeout=0.01)
        self.assertEqual(rec["cancelled_in_flight"], 7)
        self.assertTrue(rec["within_rto"])
        self.assertTrue(any("queue" in w for w in rec["warnings"]))
        # old-generation traffic is fenced, even though 4.2.0 restarts ids at 1
        gen, st = fence.invoke("f")
        self.assertEqual(st.call_id, 1)
        with self.assertRaises(rollback.StaleGenerationMessage):
            fence.complete(rec["old_generation"], 1, "delayed-from-4.3.0")
        self.assertEqual(fence.complete(gen, st.call_id, "ok"), "ok")
        # the rolled-back instance rejects late deliveries for its own calls
        with self.assertRaises(rt.CallCancelled):
            cur.complete(live[-1].call_id, "late")         # still within tombstone window
        with self.assertRaises(rt.HistoryExpired):
            cur.complete(live[0].call_id, "late")          # outside the window: still rejected
        # previous version runs its own semantics (queue downgraded to refuse)
        legacy = fence.inner
        self.assertIn("q", legacy.declared)


class Canary(unittest.TestCase):
    def mk(self):
        return rt.AsyncFunctions("c", declared={"a": True, "s": True}, stateful=frozenset({"s"}))

    def test_healthy_candidate_promotes(self):
        res = canary.promote(self.mk, self.mk, rt, requests_per_stage=500)
        self.assertEqual(res["decision"], "PROMOTED")
        self.assertEqual([s["stage_pct"] for s in res["stages"]], list(canary.STAGES))

    def test_regressing_candidate_aborts(self):
        class Leaky(rt.AsyncFunctions):
            def complete(self, call_id, value, **kw):
                v = super().complete(call_id, value, **kw)
                try:
                    super().complete(call_id, value, **kw)     # simulated double-delivery regression
                except rt.DoubleDelivery:
                    pass
                return v

        bad = lambda: Leaky("c", declared={"a": True, "s": True}, stateful=frozenset({"s"}))
        res = canary.promote(self.mk, bad, rt, requests_per_stage=500)
        self.assertEqual(res["decision"], "ABORT")
        self.assertIn("double_delivery_attempts", res["stages"][0]["breaches"])


if __name__ == "__main__":
    unittest.main()
