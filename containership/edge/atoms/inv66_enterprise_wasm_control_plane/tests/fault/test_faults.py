"""Fault injection and recovery (MC-040/041/043; C052-C060, C089)."""
from __future__ import annotations

import unittest

from tests.support import EcpError, Estate, FakeClock
from inv66_enterprise_wasm_control_plane.production.adapters import InMemoryDeploymentManager
from inv66_enterprise_wasm_control_plane.production.policy_engine import ExternalPolicy
from inv66_enterprise_wasm_control_plane.production.resilience import RetryPolicy


class FaultTest(unittest.TestCase):
    def test_journal_failure_admits_nothing_and_degrades(self):
        e = Estate()
        s = e.service
        state = {"fail": True}

        def fault():
            if state["fail"]:
                raise OSError(28, "No space left on device")
        s.journal._fault = fault
        with self.assertRaises(EcpError) as cm:
            s.admit(e.request("api"), e.token("ops"))
        self.assertEqual(cm.exception.code, "ECP_AUDIT_UNAVAILABLE")
        self.assertEqual(s.deployer.calls, 0)          # I1/I2: nothing forwarded
        self.assertEqual(len(s.inventory), 0)
        h = s.health()
        self.assertFalse(h["ready"])
        self.assertEqual(h["dependencies"]["journal"]["status"], "down")
        state["fail"] = False
        self.assertTrue(s.admit(e.request("api"), e.token("ops"))["admitted"])
        self.assertTrue(s.health()["ready"])

    def test_deployment_outage_then_reconnect_delivers_once(self):
        dm = InMemoryDeploymentManager()
        e = Estate(deployer=dm, retry=RetryPolicy(max_attempts=2, sleep=lambda s: None))
        dm.fail_next = 10
        d = e.service.admit(e.request("api"), e.token("ops"))
        self.assertTrue(d["admitted"])
        self.assertEqual(d["state"], "delivery_pending")
        self.assertIn(d["decision_id"], e.service.pending)
        dm.fail_next = 0
        e.service.delivery_breaker.state = "closed"
        self.assertEqual(e.service.redeliver_pending(), {d["decision_id"]: "delivered"})
        self.assertEqual(e.service.redeliver_pending(), {})
        self.assertEqual(len(dm.received), 1)

    def test_crash_between_decision_and_delivery_resumes_after_restart(self):
        dm = InMemoryDeploymentManager()
        e = Estate(deployer=dm, retry=RetryPolicy(max_attempts=1, sleep=lambda s: None))
        dm.fail_next = 1
        d = e.service.admit(e.request("api"), e.token("ops"))
        self.assertEqual(d["state"], "delivery_pending")
        s2 = e.open(deployer=dm)  # "restart": state rebuilt from journal only
        self.assertIn(d["decision_id"], s2.pending)
        self.assertEqual(s2.redeliver_pending()[d["decision_id"]], "delivered")
        s3 = e.open(deployer=dm)
        self.assertEqual(s3.lifecycle.get(d["decision_id"]), "delivered")
        self.assertEqual(s3.pending, {})

    def test_permanent_refusal_is_rejected_not_retried(self):
        dm = InMemoryDeploymentManager()
        dm.refuse = True
        e = Estate(deployer=dm)
        d = e.service.admit(e.request("api"), e.token("ops"))
        self.assertEqual(d["state"], "rejected")
        self.assertEqual(dm.calls, 1)

    def test_breaker_opens_on_repeated_delivery_failure(self):
        dm = InMemoryDeploymentManager()
        dm.fail_next = 100
        e = Estate(deployer=dm, retry=RetryPolicy(max_attempts=1, sleep=lambda s: None))
        for _ in range(6):
            e.service.admit(e.request("api"), e.token("ops"))
        self.assertEqual(e.service.delivery_breaker.state, "open")
        calls = dm.calls
        e.service.admit(e.request("api"), e.token("ops"))
        self.assertEqual(dm.calls, calls)  # open breaker: no call made

    def test_policy_engine_down_fails_closed_or_uses_fresh_cache(self):
        class Flaky:
            up = True

            def evaluate(self, payload, timeout_s, headers):
                if not self.up:
                    raise EcpError("ECP_DEPENDENCY_UNAVAILABLE", "down", dependency="policy")
                return {"allow": True, "policy_version": "v7"}
        clk = FakeClock()
        client = Flaky()
        for mode, expect in (("deny", False), ("use_cached", True)):
            ext = ExternalPolicy(client, expected_version="v7", on_unavailable=mode, cache_ttl_s=30, clock=clk)
            e = Estate(external_policy=ext)
            pol = dict(e.config()["policy"], engine="external", external_endpoint="http://opa", on_unavailable=mode)
            gen = e.service.stage_config(e.config(policy=pol), e.principal("sec1"), source_repo="g", source_rev="r")
            e.service.approve_config(gen, e.principal("sec2"))
            e.service.approve_config(gen, e.principal("auditor2", groups=["platform-admins"]))
            e.service.activate_config(gen, e.principal("p", groups=["platform-admins"]),
                                      expected_active=e.service.config.active.generation)
            client.up = True
            req = e.request("api")
            self.assertTrue(e.service.admit(req, e.token("ops"))["admitted"])
            client.up = False
            req2 = dict(req, request_id="again")
            d = e.service.admit(req2, e.token("ops"))
            self.assertEqual(d["admitted"], expect, mode)
            clk.advance(31)
            d = e.service.admit(dict(req, request_id="late"), e.token("ops"))
            self.assertFalse(d["admitted"])  # stale cache never used

    def test_policy_version_pin(self):
        class Wrong:
            def evaluate(self, payload, timeout_s, headers):
                return {"allow": True, "policy_version": "v8-unreviewed"}
        ext = ExternalPolicy(Wrong(), expected_version="v7")
        self.assertFalse(ext.evaluate({"x": 1})["allow"])

    def test_deadline_exceeded_records_nothing(self):
        e = Estate()
        head = e.service.journal.head
        r = e.request("api")
        r["deadline_ms"] = 1
        import time
        orig = e.service._evaluate

        def slow(*a, **k):
            time.sleep(0.01)
            return orig(*a, **k)
        e.service._evaluate = slow
        with self.assertRaises(EcpError) as cm:
            e.service.admit(r, e.token("ops"))
        self.assertEqual(cm.exception.code, "ECP_DEADLINE_EXCEEDED")
        self.assertEqual(e.service.journal.head, head)

    def test_overload_sheds_before_work(self):
        e = Estate(max_inflight=1, per_tenant_inflight=1)
        e.service.shedder.acquire("payments")
        with self.assertRaises(EcpError) as cm:
            e.service.admit(e.request("api"), e.token("ops"))
        self.assertEqual(cm.exception.code, "ECP_OVERLOADED")
        self.assertTrue(cm.exception.spec.retryable)
        self.assertEqual(e.service.metrics.value("ecp_shed_total", tenant="payments"), 1.0)

    def test_quota_exhaustion_is_retryable_and_journaled(self):
        e = Estate()
        q = {"default": {"rate_per_s": 0.001, "burst": 2, "max_inflight": 4}}
        gen = e.service.stage_config(e.config(quotas=q), e.principal("sec1"), source_repo="g", source_rev="r")
        e.service.approve_config(gen, e.principal("sec2"))
        e.service.approve_config(gen, e.principal("x", groups=["platform-admins"]))
        e.service.activate_config(gen, e.principal("x", groups=["platform-admins"]),
                                  expected_active=e.service.config.active.generation)
        e.service.admit(e.request("api"), e.token("ops"))
        e.service.admit(e.request("api"), e.token("ops"))
        with self.assertRaises(EcpError) as cm:
            e.service.admit(e.request("api"), e.token("ops"))
        self.assertEqual(cm.exception.code, "ECP_QUOTA_EXCEEDED")
        self.assertEqual(e.service.journal.query(kind="admit.refused")[-1]["body"]["code"], "ECP_QUOTA_EXCEEDED")

    def test_stale_controller_cannot_write_after_config_moved(self):
        e = Estate()
        stale = e.open()                     # second process with an old in-memory view
        gen = e.service.stage_config(e.config(site="b"), e.principal("sec1"), source_repo="g", source_rev="r")
        e.service.approve_config(gen, e.principal("sec2"))
        e.service.approve_config(gen, e.principal("x", groups=["platform-admins"]))
        e.service.activate_config(gen, e.principal("x", groups=["platform-admins"]),
                                  expected_active=e.service.config.active.generation)
        # without a lease the stale process could still append; with refresh() it converges
        stale.refresh()
        self.assertEqual(stale.config.active.generation, gen)


if __name__ == "__main__":
    unittest.main()
