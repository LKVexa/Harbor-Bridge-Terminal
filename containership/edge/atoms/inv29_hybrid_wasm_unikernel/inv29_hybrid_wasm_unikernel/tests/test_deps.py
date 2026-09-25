"""Dependency boundary, timeout/retry/circuit breaker, chaos / failure injection,
partition + reconnect, and integration-shaped tests against labelled test
doubles for INV-27 / INV-44 / PLN-04 (MC001, MC003-MC005 local parts, MC025-MC028
local parts, MC038, MC039, MC067, MC068).

These doubles are NOT the real elements.  Real-element integration remains
BLOCKED_EXTERNAL in MISSING_COMPONENTS_STATUS.json.
"""
import dataclasses
import sys
import types
import unittest

import _fixtures as F
from inv29_hybrid_wasm_unikernel import admission as adm
from inv29_hybrid_wasm_unikernel import deps as D


class Mono:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def attested_request(kr, inv27, inv44, **kw):
    req = F.request(kr, atts=(), **kw)
    return dataclasses.replace(req, attestations=(inv27.attest(req.host_digest), inv44.attest(req.module_digest)))


class DependencyTest(unittest.TestCase):
    def setUp(self):
        self.kr = F.keyring()
        self.clock = F.Clock()
        self.a = F.admitter(self.kr, clock=self.clock)

    def doubles(self, mode27="ok", mode44="ok", **kw):
        mk = lambda n, c, m: D.AttestorTestDouble(n, c, self.kr, F.ATTEST_KEY, mode=m, clock=self.clock,
                                                  timeout_s=0.05, **kw)
        return mk("INV-27", "sealed", mode27), mk("INV-44", "hardened", mode44)

    def test_end_to_end_with_doubles_and_execution_plane(self):
        inv27, inv44 = self.doubles()
        rec = self.a.admit(attested_request(self.kr, inv27, inv44))
        pln = D.ExecutionPlaneTestDouble(self.kr, F.SIGN_KEY)
        import time as _t
        real_now = int(_t.time())
        rec_now = F.admitter(self.kr, clock=lambda: real_now).admit(
            attested_request(self.kr, *self.doubles_real_clock()))
        self.assertEqual(pln.submit(rec_now), "scheduled")
        with self.assertRaises(adm.AttestationInvalid):
            pln.submit({k: v for k, v in rec_now.items() if k != "signature"})

    def doubles_real_clock(self):
        import time as _t
        return (D.AttestorTestDouble("INV-27", "sealed", self.kr, F.ATTEST_KEY, clock=_t.time),
                D.AttestorTestDouble("INV-44", "hardened", self.kr, F.ATTEST_KEY, clock=_t.time))

    # chaos / failure injection: every fault must end in a refusal, never an allow
    def test_fault_modes_fail_closed(self):
        for mode in ("timeout", "crash", "absent"):
            inv27, inv44 = self.doubles(mode27=mode)
            with self.subTest(mode=mode), self.assertRaises(D.DependencyUnavailable):
                attested_request(self.kr, inv27, inv44)
        inv27, inv44 = self.doubles(mode27="malformed")
        with self.assertRaises(adm.AttestationInvalid):
            self.a.admit(attested_request(self.kr, inv27, inv44))

    def test_revocation_mid_flight(self):
        inv27, inv44 = self.doubles(mode44="revoked")
        req = attested_request(self.kr, inv27, inv44)  # signer revoked right after issuing
        with self.assertRaises(adm.AttestationInvalid):
            self.a.admit(req)

    def test_circuit_breaker_opens_and_recovers_after_partition(self):
        mono = Mono()
        br = D.CircuitBreaker(threshold=2, cooldown_s=10, clock=mono)
        inv27 = D.AttestorTestDouble("INV-27", "sealed", self.kr, F.ATTEST_KEY, mode="crash",
                                     clock=self.clock, breaker=br, retries=0)
        for _ in range(2):
            with self.assertRaises(D.DependencyUnavailable):
                inv27.attest(adm.digest_bytes(b"h"))
        self.assertEqual(br.state, "open")
        self.assertEqual(inv27.probe().state, D.UNAVAILABLE)
        with self.assertRaisesRegex(D.DependencyUnavailable, "circuit open"):
            inv27.attest(adm.digest_bytes(b"h"))
        mono.t = 11  # partition heals
        inv27.mode = "ok"
        self.assertEqual(br.state, "half-open")
        self.assertTrue(inv27.attest(adm.digest_bytes(b"h"))["mac"])
        self.assertEqual(br.state, "closed")

    def test_retry_is_bounded(self):
        calls = []
        ad = D.Adapter(timeout_s=0.5, retries=2)
        ad.name = "flaky"
        def fn():
            calls.append(1)
            raise ConnectionError("x")
        with self.assertRaises(D.DependencyUnavailable):
            ad.call(fn)
        self.assertEqual(len(calls), 3)

    def test_refusal_from_dependency_is_not_retried(self):
        calls = []
        ad = D.Adapter(retries=3)
        def fn():
            calls.append(1)
            raise PermissionError("denied")
        with self.assertRaises(PermissionError):
            ad.call(fn)
        self.assertEqual(len(calls), 1)

    # pk_core startup compatibility assertion (MC001 negative fixtures)
    def test_pk_core_absent_incompatible_and_available(self):
        saved = {k: v for k, v in sys.modules.items() if k == "pk_core" or k.startswith("pk_core.")}
        try:
            for k in saved:
                del sys.modules[k]
            sys.modules["pk_core"] = None  # import -> ModuleNotFoundError
            self.assertEqual(D.pk_core_status().state, D.ABSENT)
            with self.assertRaises(D.DependencyUnavailable):
                D.require_pk_core()
            fake = types.ModuleType("pk_core"); fake.__version__ = "3.9.0"
            sys.modules["pk_core"] = fake
            self.assertEqual(D.pk_core_status().state, D.INCOMPATIBLE)
            fake.__version__ = "5.0.0"
            self.assertEqual(D.pk_core_status().state, D.INCOMPATIBLE)
            fake.__version__ = "4.1.0"
            self.assertEqual(D.pk_core_status().state, D.INCOMPATIBLE)  # submodules missing
            for sub in ("contract", "checklist", "component", "integration"):
                sys.modules[f"pk_core.{sub}"] = types.ModuleType(f"pk_core.{sub}")
            self.assertEqual(D.pk_core_status().state, D.AVAILABLE)
        finally:
            for k in [k for k in sys.modules if k == "pk_core" or k.startswith("pk_core.")]:
                del sys.modules[k]
            sys.modules.update(saved)

    def test_lazy_component_import_fails_with_clear_error(self):
        import inv29_hybrid_wasm_unikernel as pkg
        if D.pk_core_status().state != D.AVAILABLE:
            with self.assertRaisesRegex(D.DependencyUnavailable, "pk_core"):
                pkg.COMPONENT

    def test_dependency_report_flags_required_missing(self):
        rep = D.dependency_report()
        self.assertIn("INV-11", rep["dependencies"])
        if rep["dependencies"]["pk_core"]["state"] != D.AVAILABLE:
            self.assertFalse(rep["all_required_available"])


if __name__ == "__main__":
    unittest.main()
