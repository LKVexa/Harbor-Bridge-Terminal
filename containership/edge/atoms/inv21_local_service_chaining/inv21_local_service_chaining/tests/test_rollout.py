"""GAP-033 staged rollout + automated rollback."""
import unittest
from _support import build, prod_config
from inv21_local_service_chaining.config import ConfigStore
from inv21_local_service_chaining.rollout import CohortSignals, apply_verdict, evaluate

BASE = CohortSignals(10000, 10, 5, 50.0)


class RolloutTest(unittest.TestCase):
    def test_promote_hold_complete(self):
        self.assertEqual(evaluate(1, CohortSignals(100, 0, 0, 50), BASE)["verdict"], "hold")
        v = evaluate(1, CohortSignals(1000, 1, 0, 52), BASE)
        self.assertEqual((v["verdict"], v["next_stage"]), ("promote", 10))
        self.assertEqual(evaluate(100, CohortSignals(1000, 1, 0, 52), BASE)["verdict"], "complete")

    def test_each_criterion_triggers_rollback(self):
        for sig, why in ((CohortSignals(1000, 50, 0, 50), "error_rate"),
                         (CohortSignals(1000, 0, 0, 90), "latency_p99"),
                         (CohortSignals(1000, 0, 100, 50), "refusal_rate"),
                         (CohortSignals(1000, 0, 0, 50, {"PK_CHAIN_INTERNAL": 1}), "zero_tolerance_code")):
            v = evaluate(10, sig, BASE)
            self.assertEqual(v["verdict"], "rollback"); self.assertIn(why, v["reasons"])

    def test_automated_config_rollback(self):
        ch, res, prov, v = build()
        store = ConfigStore(ch.config); ch.bind(store)
        store.activate(prod_config(max_depth=9), author="dev", source="canary")
        verdict = evaluate(10, CohortSignals(1000, 90, 0, 50), BASE)
        rev = apply_verdict(verdict, store)
        self.assertEqual((rev.config.max_depth, ch.max_depth), (4, 4))
        self.assertTrue(rev.source.startswith("rollback-to-"))


if __name__ == "__main__":
    unittest.main()
