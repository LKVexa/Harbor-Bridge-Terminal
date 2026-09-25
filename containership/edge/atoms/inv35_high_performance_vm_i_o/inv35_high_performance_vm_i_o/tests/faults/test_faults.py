"""INV-35-C051-C060, C089: fault injection, recovery objectives, degraded and offline behaviour.

Recovery objectives asserted here (docs/resilience/FMEA.md §RTO):
  * key-service outage: fail closed immediately; first success on the first call after restore.
  * backend fault storm: breaker opens after `breaker_threshold` failures, half-opens after cooldown.
  * process crash: journal replay restores exact reservations; queues return FROZEN, never SERVING.
  * control-plane partition: bulk datapath keeps its safety invariants throughout.
"""
from __future__ import annotations

import unittest

from _support import (BULK, CTL, REGION, DegradedMode, FakeClock, Inv35Error, State, one, rt, security, stack)


def code(fn):
    try:
        fn()
    except Inv35Error as exc:
        return exc.code
    return "INV35-E000"


class FaultInjector:
    """Small harness: named faults that can be armed and cleared on a Runtime."""

    def __init__(self, r):
        self.r = r

    def kms_down(self, down=True):
        self.r.keyring.available = not down

    def time_untrusted(self, bad=True):
        self.r.authority.time_trusted = not bad

    def backend_failures(self, n):
        for _ in range(n):
            self.r.breaker.record(False)

    def crash_and_recover(self):
        return rt.Runtime.recover(self.r.snapshot_journal(), keyring=self.r.keyring,
                                  regions={n: REGION for n in self.r.queues})


class FaultTest(unittest.TestCase):
    def setUp(self):
        self.r, self.cp, self.dp, self.ctl, self.bulk = stack()
        self.fi = FaultInjector(self.r)

    def submit(self, dp=None, tok=None):
        return code(lambda: (dp or self.dp).submit(tok or self.bulk, tenant="t1", queue="q0", chain=one(), head=0))

    def test_kms_outage_fail_closed_then_recover(self):
        self.fi.kms_down()
        self.assertEqual(self.submit(), "INV35-E306")
        self.assertEqual(self.r.queues["q0"].vq.in_flight, 0)
        self.fi.kms_down(False)
        self.assertEqual(self.submit(), "INV35-E000")

    def test_breaker_opens_and_half_opens(self):
        clock = FakeClock()
        self.r.clock = clock
        self.r._rebuild_policy()
        self.fi.backend_failures(self.r.config.active.values["breaker_threshold"])
        self.assertEqual(self.submit(), "INV35-E202")
        clock.advance(self.r.config.active.values["breaker_cooldown_s"] + 0.01)
        self.assertEqual(self.submit(), "INV35-E000")  # half-open probe admitted
        self.dp.complete(self.bulk, tenant="t1", queue="q0", guest_wants_notification=True)
        self.assertEqual(self.r.breaker.state, "closed")

    def test_crash_recovery_restores_reservations_and_freezes(self):
        for _ in range(3):
            self.submit()
        self.dp.complete(self.bulk, tenant="t1", queue="q0", guest_wants_notification=True)
        r2 = self.fi.crash_and_recover()
        q = r2.queues["q0"]
        self.assertEqual(q.vq.in_flight_descriptors, 2)
        self.assertEqual(r2.quota.used["t1"], 2)
        self.assertIs(q.life.state, State.FROZEN)
        dp2 = rt.Datapath(r2)
        self.assertEqual(self.submit(dp2), "INV35-E401")
        dp2.complete(self.bulk, tenant="t1", queue="q0", guest_wants_notification=True)  # completions still drain
        self.assertEqual(q.vq.in_flight_descriptors, 1)

    def test_crash_recovery_preserves_quarantine(self):
        self.cp.transition(self.ctl, tenant="t1", queue="q0", target=State.QUARANTINED, reason="ioc", actor="sec", epoch=1)
        r2 = self.fi.crash_and_recover()
        self.assertIs(r2.queues["q0"].life.state, State.QUARANTINED)

    def test_idempotent_retry_across_crash_is_not_applied_twice(self):
        self.dp.submit(self.bulk, tenant="t1", queue="q0", chain=one(), head=0, idempotency_key="once")
        r2 = self.fi.crash_and_recover()
        r2.queues["q0"].life.state = State.SERVING  # operator resume
        again = rt.Datapath(r2).submit(self.bulk, tenant="t1", queue="q0", chain=one(), head=0, idempotency_key="once")
        self.assertTrue(again["replayed"])
        self.assertEqual(r2.queues["q0"].vq.in_flight, 1)

    def test_quarantine_freeze_disable_act_on_live_queue(self):
        self.submit()
        self.cp.transition(self.ctl, tenant="t1", queue="q0", target=State.FROZEN, reason="maint", actor="op", epoch=1)
        self.assertEqual(self.submit(), "INV35-E401")
        self.dp.complete(self.bulk, tenant="t1", queue="q0", guest_wants_notification=True)
        self.cp.transition(self.ctl, tenant="t1", queue="q0", target=State.QUARANTINED, reason="ioc", actor="sec", epoch=1)
        self.assertEqual(self.submit(), "INV35-E402")
        self.assertEqual(code(lambda: self.dp.complete(self.bulk, tenant="t1", queue="q0", guest_wants_notification=True)), "INV35-E402")
        self.assertEqual(code(lambda: self.cp.transition(self.ctl, tenant="t1", queue="q0", target=State.SERVING,
                                                          reason="x", actor="op", epoch=1)), "INV35-E400")
        self.cp.transition(self.ctl, tenant="t1", queue="q0", target=State.DISABLED, reason="kill", actor="sec", epoch=1)
        self.assertEqual(self.submit(), "INV35-E403")

    def test_degraded_no_suppression_mode_forces_notification(self):
        self.cp.transition(self.ctl, tenant="t1", queue="q0", target=State.DEGRADED, reason="suspected lost wakeup",
                           actor="op", epoch=1, mode=DegradedMode.NO_SUPPRESSION)
        res = self.dp.submit(self.bulk, tenant="t1", queue="q0", chain=one(), head=0)
        self.assertEqual(res["code"], "INV35-E001")
        done = self.dp.complete(self.bulk, tenant="t1", queue="q0", guest_wants_notification=False)
        self.assertTrue(done["notified"])

    def test_degraded_requires_declared_mode(self):
        self.assertEqual(code(lambda: self.cp.transition(self.ctl, tenant="t1", queue="q0", target=State.DEGRADED,
                                                          reason="x", actor="op", epoch=1)), "INV35-E400")

    def test_stall_detection(self):
        clock = FakeClock()
        self.r.clock = clock
        self.r._rebuild_policy()
        self.submit()
        self.r.stalls.progress("q0")
        clock.advance(self.r.config.active.values["stall_threshold_s"] + 0.01)
        st = self.r.status()
        self.assertTrue(st["stalls"] and st["stalls"][0]["stalled"])
        self.assertFalse(st["ready"])
        self.assertEqual(self.r.metrics.gauge("stalled", queue="q0"), 1.0)


class PartitionTest(unittest.TestCase):
    def test_within_grace_serves_degraded_then_restores(self):
        r, cp, dp, ctl, bulk = stack()
        r.control_plane_lost(elapsed_s=1.0)
        self.assertIs(r.queues["q0"].life.state, State.DEGRADED)
        self.assertEqual(dp.submit(bulk, tenant="t1", queue="q0", chain=one(), head=0)["code"], "INV35-E001")
        self.assertEqual(code(lambda: dp.submit(bulk, tenant="t1", queue="q0", chain=one(addr=0), head=0)), "INV35-E105")
        r.control_plane_restored()
        self.assertIs(r.queues["q0"].life.state, State.SERVING)

    def test_beyond_grace_freeze_policy(self):
        r, cp, dp, ctl, bulk = stack(offline_policy="freeze", offline_grace_s=10.0)
        r.control_plane_lost(elapsed_s=11.0)
        self.assertIs(r.queues["q0"].life.state, State.FROZEN)

    def test_beyond_grace_quarantine_policy(self):
        r, cp, dp, ctl, bulk = stack(offline_policy="quarantine", offline_grace_s=10.0)
        r.control_plane_lost(elapsed_s=11.0)
        self.assertIs(r.queues["q0"].life.state, State.QUARANTINED)
        self.assertTrue(r.audit.verify())


if __name__ == "__main__":
    unittest.main()
