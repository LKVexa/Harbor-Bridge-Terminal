"""Outcome registry, lifecycle state machine, retry/cancel (C014, C015, C025, C053)."""
from __future__ import annotations

import itertools
import random
import re
import unittest

from _support import PKG_DIR, pkg

L, E = pkg.Lifecycle, pkg.Event
from inv37_bulk_data_plane.lifecycle import IDEMPOTENT, TRANSITIONS  # noqa: E402
from inv37_bulk_data_plane.retry import CancelToken, RetryPolicy  # noqa: E402


class OutcomeRegistryTest(unittest.TestCase):
    def test_every_code_used_in_source_is_registered(self):
        used = set()
        for p in PKG_DIR.glob("*.py"):
            used |= set(re.findall(r'CodedError\(\s*"([a-z_]+)"', p.read_text()))
            used |= set(re.findall(r'SecurityRejected\(\s*"([a-z_]+)"', p.read_text()))
        used |= {"invalid_manifest", "digest_mismatch", "transfer_incomplete", "admission_rejected", "transfer_closed",
                 "illegal_transition", "invalid_config"}
        self.assertFalse(used - set(pkg.ERROR_CODES), used - set(pkg.ERROR_CODES))

    def test_integrity_and_security_codes_never_retryable(self):
        for code in ("digest_mismatch", "object_digest_mismatch", "authentication_failed", "authorization_denied",
                     "replay_detected", "checkpoint_corrupt", "invalid_manifest"):
            self.assertFalse(pkg.ERROR_CODES[code].retryable, code)

    def test_classify_unknown_exception_is_terminal(self):
        self.assertEqual(pkg.classify(RuntimeError("x"))["outcome"], "terminal_failure")
        self.assertEqual(pkg.classify(pkg.CodedError("timeout", "t"))["outcome"], "retryable_failure")


class LifecycleTest(unittest.TestCase):
    def test_every_undefined_transition_is_refused(self):
        for s, e in itertools.product(L, E):
            sm = pkg.StateMachine(state=s)
            if (s, e) in TRANSITIONS:
                self.assertEqual(sm.fire(e), TRANSITIONS[(s, e)])
            elif e in IDEMPOTENT and s in IDEMPOTENT[e]:
                self.assertEqual(sm.fire(e), s)
            else:
                with self.assertRaises(pkg.IllegalTransition) as cm:
                    sm.fire(e)
                self.assertEqual(cm.exception.code, "illegal_transition")
                self.assertEqual(sm.state, s)  # no implicit repair

    def test_closed_is_absorbing(self):
        for e in E:
            sm = pkg.StateMachine(state=L.CLOSED)
            if e is E.CLOSE:
                self.assertEqual(sm.fire(e), L.CLOSED)
            else:
                self.assertRaises(pkg.IllegalTransition, sm.fire, e)

    def test_random_walks_only_visit_legal_states(self):
        rng = random.Random(37)
        for _ in range(300):
            sm = pkg.StateMachine()
            for _ in range(40):
                e = rng.choice(list(E))
                before = sm.state
                try:
                    sm.fire(e)
                    self.assertTrue((before, e) in TRANSITIONS or (e in IDEMPOTENT and before in IDEMPOTENT[e]))
                except pkg.IllegalTransition:
                    self.assertEqual(sm.state, before)

    def test_snapshot_exposes_reason(self):
        sm = pkg.StateMachine()
        sm.fire(E.VALIDATE, "manifest received")
        self.assertEqual(sm.snapshot()["last_reason"], "manifest received")


class RetryTest(unittest.TestCase):
    def test_only_retryable_codes_retry(self):
        calls = []
        pol = RetryPolicy(base_delay=0, max_delay=0, max_attempts=5, budget_ratio=10)

        def bad():
            calls.append(1)
            raise pkg.DigestMismatch("x")

        self.assertRaises(pkg.DigestMismatch, pol.run, bad, sleep=lambda s: None)
        self.assertEqual(len(calls), 1)

    def test_retryable_eventually_succeeds_and_bounded(self):
        n = {"i": 0}
        pol = RetryPolicy(base_delay=0.001, max_delay=0.002, max_attempts=5, budget_ratio=10)

        def flaky():
            n["i"] += 1
            if n["i"] < 3:
                raise pkg.AdmissionRejected("busy")
            return "ok"

        self.assertEqual(pol.run(flaky, sleep=lambda s: None), "ok")

        def always():
            raise pkg.AdmissionRejected("busy")

        pol2 = RetryPolicy(base_delay=0, max_delay=0, max_attempts=3, budget_ratio=10)
        self.assertRaises(pkg.AdmissionRejected, pol2.run, always, sleep=lambda s: None)
        self.assertEqual(pol2.stats["retries"], 2)

    def test_backoff_jitter_bounds(self):
        pol = RetryPolicy(base_delay=0.1, max_delay=1.0, rng=random.Random(1))
        for a in range(10):
            self.assertLessEqual(pol.delay(a), min(1.0, 0.1 * 2 ** a))

    def test_retry_budget(self):
        pol = RetryPolicy(base_delay=0, max_delay=0, max_attempts=5, budget_ratio=0.0)

        def always():
            raise pkg.AdmissionRejected("busy")

        self.assertRaises(pkg.AdmissionRejected, pol.run, always, sleep=lambda s: None)
        self.assertRaises(pkg.AdmissionRejected, pol.run, always, sleep=lambda s: None)
        self.assertGreaterEqual(pol.stats["budget_exhausted"], 1)

    def test_cancel_unwinds_lifo_and_checks(self):
        order = []
        tok = CancelToken()
        tok.on_cancel(lambda: order.append("slot"))
        tok.on_cancel(lambda: order.append("mapping"))
        tok.cancel("test")
        tok.cancel("again")  # idempotent
        self.assertEqual(order, ["mapping", "slot"])
        with self.assertRaises(pkg.CodedError) as cm:
            tok.check()
        self.assertEqual(cm.exception.code, "cancelled")

    def test_deadline(self):
        import time
        tok = CancelToken(deadline=time.monotonic() - 1)
        with self.assertRaises(pkg.CodedError) as cm:
            tok.check()
        self.assertEqual(cm.exception.code, "timeout")


if __name__ == "__main__":
    unittest.main()
