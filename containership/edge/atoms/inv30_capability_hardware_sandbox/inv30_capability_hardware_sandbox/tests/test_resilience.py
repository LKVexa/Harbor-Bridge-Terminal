# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Fault injection, retry, breaker, admission, stall, failover/degraded, restart & duplicate controller (GAP-033..039)."""
import os
import random
import tempfile
import unittest

from ..backend import CheriHardwareBackend, SemanticModelBackend, select_backend
from ..errors import BackendUnavailable
from ..errors import CircuitOpen, Overloaded, Unauthenticated
from ..resilience import AdmissionController, CircuitBreaker, Deadline, RetryPolicy, StallDetector
from ..service import Lease
from ._util import access, make_service, mint


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class FlakyBackend(SemanticModelBackend):
    def __init__(self, fail_times):
        self.fail = fail_times

    def mint(self, *a):
        if self.fail:
            self.fail -= 1
            raise BackendUnavailable("injected backend outage")
        return super().mint(*a)


class ResilienceTest(unittest.TestCase):
    def test_retry_only_retryable(self):
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise BackendUnavailable("x")
            return "ok"
        self.assertEqual(RetryPolicy().run(flaky, rng=random.Random(1), sleep=lambda s: None), "ok")
        calls.clear()

        def security():
            calls.append(1)
            raise Unauthenticated("no")
        with self.assertRaises(Unauthenticated):
            RetryPolicy().run(security, sleep=lambda s: None)
        self.assertEqual(len(calls), 1)

    def test_backoff_bounded_with_jitter(self):
        d = RetryPolicy(max_attempts=10, base_s=0.1, cap_s=1.0).delays(random.Random(3))
        self.assertTrue(all(0 <= x <= 1.0 for x in d))
        self.assertGreater(len(set(d)), 5)

    def test_breaker_opens_and_half_opens(self):
        clk = Clock()
        br = CircuitBreaker(failure_threshold=2, reset_s=10, clock=clk)
        for _ in range(2):
            with self.assertRaises(BackendUnavailable):
                br.call(lambda: (_ for _ in ()).throw(BackendUnavailable("down")))
        with self.assertRaises(CircuitOpen):
            br.call(lambda: 1)
        clk.t = 11
        self.assertEqual(br.call(lambda: 1), 1)
        self.assertEqual(br.state, "closed")

    def test_admission_sheds_and_releases(self):
        clk = Clock()
        ac = AdmissionController(max_inflight=1, tenant_rate=1, tenant_burst=2, clock=clk)
        t = ac.admit("a")
        with self.assertRaises(Overloaded):
            ac.admit("a")
        t.__exit__(None, None, None)
        ac.admit("a").__exit__(None, None, None)
        with self.assertRaises(Overloaded):
            ac.admit("a")  # tenant bucket exhausted (fairness)
        ac.admit("b").__exit__(None, None, None)  # other tenants unaffected

    def test_deadline_and_cancel(self):
        clk = Clock()
        d = Deadline(1.0, clock=clk)
        d.check()
        clk.t = 2
        with self.assertRaises(Exception) as cm:
            d.check()
        self.assertEqual(cm.exception.code, "DEADLINE_EXCEEDED")
        d2 = Deadline(10, clock=clk)
        d2.cancel()
        with self.assertRaises(Exception) as cm:
            d2.check()
        self.assertEqual(cm.exception.code, "CANCELLED")

    def test_stall_detector(self):
        clk = Clock()
        s = StallDetector(stall_s=5, clock=clk)
        clk.t = 6
        self.assertFalse(s.stalled(0))
        self.assertTrue(s.stalled(1))
        s.beat()
        self.assertFalse(s.stalled(1))

    def test_injected_backend_outage_degrades_then_recovers(self):
        svc = make_service()
        svc.backend = FlakyBackend(fail_times=5)
        codes = [mint(svc).get("code", "OK") for _ in range(7)]
        self.assertEqual(codes[:5], ["BACKEND_UNAVAILABLE"] * 5)
        self.assertEqual(codes[5], "CIRCUIT_OPEN")
        self.assertEqual(svc.health()["status"], "degraded")
        svc.breaker.opened_at -= 60
        self.assertEqual(mint(svc).get("code", "OK"), "OK")
        self.assertEqual(svc.health()["status"], "healthy")

    def test_failover_never_downgrades_hardware_workloads(self):
        hw = CheriHardwareBackend(helper="", probe=lambda: {"state": "present", "signal": "test"})
        with self.assertRaises(Exception) as cm:
            select_backend(require_hardware=True, mode="production", hardware=hw)
        self.assertEqual(cm.exception.code, "HARDWARE_REQUIRED")
        self.assertIsInstance(select_backend(require_hardware=False, mode="production", hardware=hw),
                              SemanticModelBackend)

    def test_restart_invalidates_all_handles(self):
        svc = make_service()
        h = mint(svc)["handle"]
        svc2 = make_service()  # simulated crash/restart: volatile table
        self.assertEqual(access(svc2, h, 0x1000)["code"], "NOT_FOUND")

    def test_duplicate_controller_is_fenced(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "lease")
            from ..authz import Authenticator, MintingAuthority
            from ..config import load
            from ..service import CapabilityService
            from ._util import KEY_A, MINT_KEY
            auth = Authenticator()
            auth.register("ctl-a", KEY_A, {"mint", "access"}, {"tenant-a"})
            old = CapabilityService(load(), authenticator=auth, authority=MintingAuthority(MINT_KEY),
                                    lease=Lease(path))
            new = CapabilityService(load(), authenticator=auth, authority=MintingAuthority(MINT_KEY),
                                    lease=Lease(path))
            self.assertEqual(mint(old).get("code"), "DISABLED")
            self.assertIn("handle", mint(new))

    def test_partition_and_reconnect_of_discovery(self):
        from ..discovery import probe_cheri
        self.assertEqual(probe_cheri(machine="x86_64", system="FreeBSD", sysctl=lambda: None)["state"], "unprobed")
        self.assertEqual(probe_cheri(machine="aarch64", system="FreeBSD", sysctl=lambda: True)["state"], "present")
        self.assertEqual(probe_cheri(machine="x86_64", system="Plan9")["state"], "unprobed")

    def test_key_service_unavailable_fails_closed(self):
        from ..config import ConfigInvalid
        from ..secret_refs import resolve
        with self.assertRaises(ConfigInvalid):
            resolve("env:INV30_DEFINITELY_UNSET_KEY")
        with self.assertRaises(ConfigInvalid):
            resolve("hunter2hunter2hunter2hunter2hunter2")


if __name__ == "__main__":
    unittest.main()
