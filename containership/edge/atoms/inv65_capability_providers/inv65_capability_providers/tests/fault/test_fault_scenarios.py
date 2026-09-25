import json, pathlib, unittest
from inv65_capability_providers.tests.helpers import World
from inv65_capability_providers.errors.mapping import ProviderFault


class FaultScenarios(unittest.TestCase):
    def test_backend_outage_opens_breaker_then_recovers(self):
        w = World(); w.svc.start(); w.link()
        w.svc.breaker.cooldown = 0.05
        w.backend.up = False
        self.assertEqual(w.svc.health()["state"], "degraded")
        self.assertFalse(w.svc.health()["ready"])
        codes = set()
        for _ in range(6):
            try:
                w.call()
            except ProviderFault as e:
                codes.add(e.code)
        self.assertIn("PK_PROVIDER_CIRCUIT_OPEN", codes)
        w.backend.up = True
        import time; time.sleep(0.06)
        self.assertEqual(w.call()["result"]["bucket"], "acme-primary")
        self.assertEqual(w.svc.breaker.state, "closed")

    def test_slow_backend_hits_deadline(self):
        w = World(); w.svc.start(); w.link()
        w.backend.latency_s = 0.3
        with self.assertRaises(ProviderFault) as c:
            w.call(op="set", payload={"key": "a", "value": 1}, meta={"correlation_id": "ab" * 8, "deadline_ms": 50})
        self.assertEqual(c.exception.code, "PK_PROVIDER_DEADLINE_EXCEEDED")

    def test_transient_failure_retry_rules(self):
        w = World(); w.svc.start(); w.link()
        w.backend.fail_next = 1
        self.assertEqual(w.call(op="get")["result"]["bucket"], "acme-primary")  # retried
        w.backend.fail_next = 1
        with self.assertRaises(ProviderFault):
            w.call(op="set", payload={"key": "a", "value": 1})  # not idempotent, no key -> no retry
        w.backend.fail_next = 1
        out = w.call(op="set", payload={"key": "a", "value": 1}, meta={"correlation_id": "cd" * 8, "deadline_ms": 2000, "idempotency_key": "idem-0001"})
        self.assertTrue(out["result"]["ok"])

    def test_fault_matrix_references_existing_tests(self):
        root = pathlib.Path(__file__).resolve().parents[2]
        m = json.loads((root / "tests/fault/fault_matrix.json").read_text())
        for s in m["scenarios"]:
            f, _, name = s["test"].partition("::")
            self.assertIn("def " + name, (root / f).read_text(), s["id"])
