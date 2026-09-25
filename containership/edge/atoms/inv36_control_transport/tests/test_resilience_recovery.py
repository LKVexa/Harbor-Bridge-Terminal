"""Health, retry, backpressure, circuit breaking, failover, restart/recovery."""
from __future__ import annotations

import json
import pathlib
import random
import statistics
import tempfile
import tracemalloc
import unittest

import _util  # noqa: F401

from inv36_control_transport import health as H
from inv36_control_transport import recovery as R
from inv36_control_transport import schema_check
from inv36_control_transport.errors import ErrorCode, Inv36Error


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


class HealthTest(unittest.TestCase):
    """REQ: INV36-REQ-021, INV36-REQ-038 | KIND: unit"""

    def test_states_hysteresis_and_required_dependencies(self):
        clk = Clock()
        transitions = []
        hm = H.HealthMonitor(stall_threshold_s=10, hysteresis=3, clock=clk,
                             on_transition=lambda a, b, r: transitions.append((a, b)))
        hm.set_dependency("identity", H.DepKind.REQUIRED, True)
        hm.set_dependency("telemetry", H.DepKind.OPTIONAL, True)
        for _ in range(3):
            hm.evaluate()
        self.assertEqual(hm.state, H.HealthState.READY)
        hm.set_dependency("telemetry", H.DepKind.OPTIONAL, False)
        hm.evaluate()
        self.assertEqual(hm.state, H.HealthState.READY)  # hysteresis: not yet
        hm.evaluate()
        hm.evaluate()
        self.assertEqual(hm.state, H.HealthState.DEGRADED)
        hm.set_dependency("identity", H.DepKind.REQUIRED, False)
        rep = hm.evaluate()
        self.assertEqual(hm.state, H.HealthState.NOT_READY)  # required loss is immediate
        self.assertFalse(rep["ready"])
        self.assertIn("required_dependency_down:identity", rep["reasons"])
        schema_check.validate(rep, schema_check.load("health.schema.json"))
        self.assertEqual(transitions[-1], ("degraded", "not_ready"))

    def test_stall_detection_uses_monotonic_clock(self):
        clk = Clock()
        hm = H.HealthMonitor(stall_threshold_s=5, hysteresis=1, clock=clk)
        hm.evaluate()
        clk.t += 6
        self.assertIn("stalled", hm.evaluate()["reasons"])
        hm.progress()
        self.assertEqual(hm.evaluate()["state"], "ready")

    def test_no_flapping_under_alternating_signal(self):
        clk = Clock()
        n = []
        hm = H.HealthMonitor(hysteresis=3, clock=clk, on_transition=lambda a, b, r: n.append(b))
        hm.evaluate(), hm.evaluate(), hm.evaluate()
        for i in range(20):
            hm.queue_saturation = 0.95 if i % 2 else 0.0
            hm.evaluate()
        self.assertEqual(n, ["ready"])


class RetryTest(unittest.TestCase):
    """REQ: INV36-REQ-022 | KIND: unit"""

    def test_bounded_attempts_and_jitter_distribution(self):
        pol = H.RetryPolicy(max_attempts=6, base_s=0.1, cap_s=1.0, rng=random.Random(1))
        samples = [list(pol.delays()) for _ in range(400)]
        self.assertTrue(all(len(s) == 5 for s in samples))
        for i in range(5):
            col = [s[i] for s in samples]
            cap = min(1.0, 0.1 * 2 ** i)
            self.assertTrue(all(0 <= x <= cap for x in col))
            self.assertAlmostEqual(statistics.fmean(col), cap / 2, delta=cap * 0.12)  # full jitter ~ U(0, cap)
        dec = H.RetryPolicy(max_attempts=6, base_s=0.1, cap_s=1.0, jitter="decorrelated", rng=random.Random(2))
        self.assertTrue(all(0.1 <= x <= 1.0 for x in dec.delays()))

    def test_terminal_errors_never_retried(self):
        calls = []

        def fail():
            calls.append(1)
            raise Inv36Error("auth", code=ErrorCode.AUTH_FAILURE)

        with self.assertRaises(Inv36Error):
            H.RetryPolicy(sleep=lambda s: None).run(fail, operation="handshake")
        self.assertEqual(len(calls), 1)

    def test_retryable_until_exhausted_budget_and_deadline(self):
        calls = []

        def flaky():
            calls.append(1)
            raise Inv36Error("down", code=ErrorCode.STREAM_UNAVAILABLE)

        with self.assertRaises(H.RetryExhausted):
            H.RetryPolicy(max_attempts=4, sleep=lambda s: None).run(flaky, operation="connect")
        self.assertEqual(len(calls), 4)
        budget = H.RetryBudget(tokens=1.0)
        with self.assertRaises(H.RetryExhausted) as cm:
            H.RetryPolicy(max_attempts=10, budget=budget, sleep=lambda s: None).run(flaky, operation="connect")
        self.assertIn("budget", str(cm.exception))
        clk = Clock()
        pol = H.RetryPolicy(max_attempts=10, base_s=5, cap_s=5, clock=clk, sleep=lambda s: None,
                            rng=random.Random(3))
        with self.assertRaises((H.DeadlineExceeded, H.RetryExhausted)):
            pol.run(flaky, operation="connect", deadline_s=0.001)
        with self.assertRaises(H.DeadlineExceeded):
            H.RetryPolicy().run(flaky, operation="connect", cancelled=lambda: True)

    def test_non_retryable_operation_class(self):
        calls = []

        def flaky():
            calls.append(1)
            raise Inv36Error("down", code=ErrorCode.STREAM_UNAVAILABLE)

        with self.assertRaises(Inv36Error):
            H.RetryPolicy(sleep=lambda s: None).run(flaky, operation="ERROR_REPORT")
        self.assertEqual(len(calls), 1)
        self.assertEqual(H.OPERATION_RETRY_CLASS["LEASE_REVOKE"], H.Retryability.DEDUP_TOKEN)


class BreakerAdmissionFailoverTest(unittest.TestCase):
    """REQ: INV36-REQ-023, INV36-REQ-024, INV36-REQ-025, INV36-REQ-037 | KIND: unit"""

    def test_breaker_open_half_open_closed(self):
        clk = Clock()
        changes = []
        br = H.CircuitBreaker("kms", failure_threshold=2, reset_s=5, clock=clk,
                              on_change=lambda n, s: changes.append(s))

        def boom():
            raise RuntimeError("down")

        for _ in range(2):
            with self.assertRaises(RuntimeError):
                br.call(boom)
        with self.assertRaises(H.CircuitOpen):
            br.call(lambda: 1)
        clk.t += 5
        with self.assertRaises(RuntimeError):
            br.call(boom)          # half-open probe fails -> open again
        clk.t += 5
        self.assertEqual(br.call(lambda: 7), 7)
        self.assertEqual(changes, ["open", "half_open", "open", "half_open", "closed"])

    def test_admission_bounds_priorities_and_tenants(self):
        ac = H.AdmissionController(high_water=10, low_water=3, per_tenant=4)
        for i in range(4):
            ac.admit("a", H.Priority.NORMAL)
        with self.assertRaises(H.OverloadError) as cm:
            ac.admit("a", H.Priority.CRITICAL)  # tenant quota applies to everyone
        self.assertTrue(cm.exception.code.retryable)
        self.assertIsNotNone(cm.exception.retry_after_s)
        for t in "bcdefg":
            ac.admit(t, H.Priority.NORMAL)          # depth reaches HWM (10)
        self.assertEqual(ac.depth, 10)
        with self.assertRaises(H.OverloadError):
            ac.admit("z", H.Priority.OPTIONAL)       # optional shed first
        with self.assertRaises(H.OverloadError):
            ac.admit("z", H.Priority.NORMAL)
        ac.admit("y", H.Priority.CRITICAL)           # critical admitted above HWM up to the hard bound
        for _ in range(ac.depth - 3):
            ac.release("b")
        ac.release("y")
        ac.release("c")
        ac.admit("q", H.Priority.CRITICAL)
        self.assertTrue(ac.shedding or ac.depth <= ac.low_water)

    def test_queue_saturation_bounded_memory(self):
        ac = H.AdmissionController(high_water=100, low_water=10, per_tenant=10 ** 6)
        tracemalloc.start()
        for i in range(100_000):
            try:
                ac.admit("t", H.Priority.CRITICAL)
            except H.OverloadError:
                pass
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self.assertLessEqual(ac.depth, 116)
        self.assertLess(peak, 2_000_000)

    def test_failover_preserves_residency_and_fences(self):
        fs = H.FailoverSelector("eu", [H.Alternate("host-us", "us", frozenset({"t1"})),
                                       H.Alternate("host-eu2", "eu", frozenset({"t2"})),
                                       H.Alternate("host-eu3", "eu", frozenset({"t1"}))])
        self.assertEqual(fs.select("t1").endpoint, "host-eu3")
        with self.assertRaises(H.OverloadError):
            fs.select("t1", exclude=["host-eu3"])
        tok_a = fs.take_ownership("host-eu1")
        fs.validate("host-eu1", tok_a)
        tok_b = fs.take_ownership("host-eu3")
        with self.assertRaises(H.OverloadError):
            fs.validate("host-eu1", tok_a)  # stale owner fenced: no dual-active
        fs.validate("host-eu3", tok_b)

    def test_degraded_mode_catalog(self):
        for k in ("telemetry_exporter_down", "policy_service_down", "identity_or_attestation_down", "reentry"):
            self.assertIn(k, H.DEGRADED_MODE)


class RecoveryTest(unittest.TestCase):
    """REQ: INV36-REQ-026, INV36-REQ-047, INV36-REQ-008 | KIND: unit"""

    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())

    def test_clean_unclean_and_dedup_across_restart(self):
        store = R.StateStore(self.d / "state.json")
        m1 = R.RecoveryManager(store)
        st = m1.start()
        self.assertEqual(st["last_shutdown"], "none")
        self.assertTrue(m1.dedup.check_and_record(b"\x01" * 16))
        m1.checkpoint(clean=False)
        m2 = R.RecoveryManager(store)          # crash: no shutdown()
        st2 = m2.start()
        self.assertEqual(st2["last_shutdown"], "unclean")
        self.assertEqual(st2["sessions_resumed"], 0)
        self.assertFalse(m2.dedup.check_and_record(b"\x01" * 16))  # replay across restart refused
        m2.shutdown()
        self.assertEqual(R.RecoveryManager(store).start()["last_shutdown"], "clean")
        self.assertLess(st2["recovery_s"], R.RTO_TARGET_S)

    def test_corrupt_and_incompatible_state(self):
        p = self.d / "state.json"
        store = R.StateStore(p)
        store.write({"instance_id": "x", "clean_shutdown": True, "dedup": {}})
        p.write_text(p.read_text().replace('"x"', '"y"'))
        with self.assertRaises(R.StateCorrupt):
            store.read()
        st = R.RecoveryManager(store).start()
        self.assertTrue(st["state_corrupt"])
        self.assertTrue(st["operator_action"])
        p.write_text(json.dumps({"schema": "inv36.state/99", "body": {}, "sha256": ""}))
        with self.assertRaises(R.StateCorrupt):
            store.read()

    def test_crash_mid_write_keeps_previous_complete_state(self):
        p = self.d / "state.json"
        store = R.StateStore(p)
        store.write({"instance_id": "a", "clean_shutdown": True, "dedup": {}})
        p.with_suffix(".tmp").write_text("{partial")
        self.assertEqual(store.read()["instance_id"], "a")

    def test_session_material_never_persisted(self):
        store = R.StateStore(self.d / "s.json")
        for bad in ("traffic_key", "shared", "session_id", "send_seq"):
            with self.subTest(bad), self.assertRaises(R.StateCorrupt):
                store.write({bad: "x"})
        self.assertEqual(R.STATE_CLASSIFICATION["traffic_keys"], "ephemeral")

    def test_dedup_window_bounded_and_ttl(self):
        clk = Clock()
        dw = R.DedupWindow(ttl_s=10, capacity=100, clock=clk)
        for i in range(1000):
            dw.check_and_record(i.to_bytes(16, "big"))
        self.assertLessEqual(len(dw._seen), 101)
        clk.t += 11
        self.assertTrue(dw.check_and_record((999).to_bytes(16, "big")))


if __name__ == "__main__":
    unittest.main()
