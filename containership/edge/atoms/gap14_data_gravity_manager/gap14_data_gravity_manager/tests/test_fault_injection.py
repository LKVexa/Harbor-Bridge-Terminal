"""P1-24: fault-injection suite -- dependency loss, stale inputs, partial partitions, feed corruption.

Invariant under every fault: either a correct, audited decision is returned, or
a registered fail-closed/retryable code is raised and NO decision.issued record
is written.  There is no third outcome.
"""
import itertools
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fixtures.estate import Estate  # noqa: E402

from gap14_data_gravity_manager.audit import verify_chain  # noqa: E402
from gap14_data_gravity_manager.engine import GravityDecisionError  # noqa: E402
from gap14_data_gravity_manager.errors import REGISTRY  # noqa: E402

DEPS = ("policy", "topology", "replication", "placement")
FAULTS = {
    "outage": lambda s: setattr(s, "outage", True),
    "timeout": lambda s: setattr(s, "delay", 10.0),
    "stale": lambda s: setattr(s, "stale_by", 10_000),
    "future": lambda s: setattr(s, "stale_by", -10_000),
    "tamper": lambda s: setattr(s, "tamper", True),
    "rollback": lambda s: setattr(s, "version", 0),
    "transient": lambda s: setattr(s, "fail_times", 1),
}
EXPECT = {"outage": "G14_DEPENDENCY_UNAVAILABLE", "timeout": "G14_DEPENDENCY_TIMEOUT", "stale": "G14_STALE_INPUT",
          "future": "G14_CLOCK_SKEW", "tamper": "G14_SIGNATURE_INVALID", "rollback": "G14_VERSION_ROLLBACK"}


class FaultMatrix(unittest.TestCase):
    def run_case(self, faults):
        e = Estate()
        e.decide(size=2)  # establish watermarks
        for dep, fault in faults:
            FAULTS[fault](getattr(e, dep))
        before = len([r for r in e.audit.records if r["event"] == "decision.issued"])
        try:
            d = e.decide(size=2)
            outcome = ("ok", d)
        except GravityDecisionError as exc:
            outcome = ("err", exc.code)
        issued = len([r for r in e.audit.records if r["event"] == "decision.issued"])
        verify_chain(e.audit.records, e.keys)
        return e, outcome, issued - before

    def test_single_faults(self):
        for dep, fault in itertools.product(DEPS, FAULTS):
            with self.subTest(dep=dep, fault=fault):
                _, (kind, val), delta = self.run_case([(dep, fault)])
                if fault == "transient":
                    self.assertEqual(kind, "ok")        # retried idempotent read recovers
                    self.assertEqual(delta, 1)
                    continue
                self.assertEqual(kind, "err")
                self.assertEqual(val, EXPECT[fault])
                self.assertIn(val, REGISTRY)
                self.assertEqual(delta, 0)

    def test_pairwise_faults_never_emit_unaudited_or_wrong_decisions(self):
        combos = [c for c in itertools.combinations(itertools.product(DEPS, FAULTS), 2) if c[0][0] != c[1][0]]
        for combo in combos:
            with self.subTest(combo=combo):
                _, (kind, val), delta = self.run_case(list(combo))
                if kind == "ok":
                    self.assertTrue(all(f == "transient" for _, f in combo))
                    self.assertEqual(delta, 1)
                else:
                    self.assertIn(val, REGISTRY)
                    self.assertEqual(delta, 0)

    def test_partial_partition_one_site_unreachable(self):
        e = Estate()
        e.topology.unavailable |= {("dub", "ams"), ("ams", "dub")}
        with self.assertRaises(GravityDecisionError) as ctx:
            e.placement.sites["dub"]["available"] = False
            e.decide(size=2)
        self.assertEqual(ctx.exception.code, "PK_GRAVITY_NO_LEGAL_OPTION")

    def test_cost_feed_corruption_rejected(self):
        e = Estate()
        for bad in (-1.0, float("inf"), "1", None, 1e9):
            with self.subTest(bad=bad):
                e2 = Estate()
                e2.topology.routes[("dub", "ams")] = bad
                with self.assertRaises(GravityDecisionError) as ctx:
                    e2.decide(size=2)
                self.assertIn(ctx.exception.code, ("G14_INVALID_REQUEST", "G14_SIGNATURE_INVALID"))

    def test_audit_loss_mid_stream(self):
        e = Estate()
        e.decide()
        e.audit.fail = True
        with self.assertRaises(GravityDecisionError) as ctx:
            e.decide()
        self.assertEqual(ctx.exception.code, "G14_AUDIT_UNAVAILABLE")
        e.audit.fail = False
        e.decide()
        self.assertTrue(e.service.health()["ready"])
        verify_chain(e.audit.records, e.keys)


if __name__ == "__main__":
    unittest.main()
