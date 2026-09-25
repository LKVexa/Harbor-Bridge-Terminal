"""Fault-injection / partition / reconnect / restart suite (items 7, 33, 34, 36)."""
import os
import tempfile
import unittest

import _support as S

State = S.lifecycle.State


class Faults(unittest.TestCase):
    def test_api_outage_then_recovery(self):
        h = S.Harness()
        h.kube.apply(S.workload())
        h.kube.down = True
        h.settle(3, step=1)
        self.assertEqual(h.rt.launches, 0)
        h.kube.down = False
        h.settle(6, step=31)
        self.assertEqual(h.obj()["status"]["state"], "Placed")
        self.assertEqual(h.rt.launches, 1)

    def test_downstream_outage_degraded_breaker_then_converges_once(self):
        h = S.Harness(cfg={"circuit": {"threshold": 2, "resetAfter": 5.0}})
        h.rt.down = True
        h.kube.apply(S.workload())
        h.settle(6, step=1)
        st = h.obj()["status"]
        self.assertEqual(st["state"], "Degraded")
        self.assertEqual(S.status.get_condition(st["conditions"], "Degraded")["status"], "True")
        self.assertEqual(h.ctrl.breaker.state, "open")
        h.rt.down = False
        h.settle(10, step=31)
        self.assertEqual(h.obj()["status"]["state"], "Placed")
        self.assertEqual(h.rt.launches, 1)

    def test_watch_history_expired_relists(self):
        h = S.Harness(kube_=S.kube.FakeKube(history_window=3))
        h.ctrl.rv = "0"
        for i in range(6):
            h.kube.apply(S.workload(name=f"w{i}"))
        h.settle(4)
        self.assertGreaterEqual(h.ctrl.metrics.get("inv67_watch_relists_total"), 1)
        self.assertEqual(h.rt.launches, 6)

    def test_crash_between_intent_and_done_replays_without_duplicate_launch(self):
        with tempfile.TemporaryDirectory() as d:
            jp = os.path.join(d, "journal.jsonl")
            kube, rt = S.kube.FakeKube(), S.downstream.InMemoryRuntime()
            lease = S.leader.LeaseStore()
            clock = S.Clock()
            a = S.Harness(kube_=kube, runtime=rt, journal_path=jp, lease_store=lease, clock=clock)
            kube.apply(S.workload())
            # crash window: place reaches the runtime, then the process dies before journal.done / status write
            orig_done = a.journal.done
            a.journal.done = lambda *x: (_ for _ in ()).throw(SystemExit("crash"))
            with self.assertRaises(SystemExit):
                a.settle(2)
            a.journal.done = orig_done
            self.assertEqual(rt.launches, 1)
            with open(jp, "a") as fh:
                fh.write('{"t": "intent", "key": "torn')        # torn tail from the crash
            clock.tick(20)                                          # old lease expires
            b = S.Harness(kube_=kube, runtime=rt, journal_path=jp, lease_store=lease, clock=clock, ident="ctrl-1")
            self.assertEqual(b.journal.torn, 1)
            self.assertEqual(len(b.journal.pending()), 1)
            b.ctrl.replay_journal()
            b.ctrl.resync()
            b.settle(3)
            self.assertEqual(kube.get("team-a", "web")["status"]["state"], "Placed")
            self.assertEqual(rt.launches, 1, "replay must reuse the idempotency key")
            self.assertEqual(b.journal.pending(), [])

    def test_stale_observation_goes_unknown(self):
        h = S.Harness(cfg={"staleObservationSec": 60.0, "circuit": {"threshold": 100, "resetAfter": 1.0}})
        h.kube.apply(S.workload())
        h.settle(3)
        h.rt.down = True
        h.clock.tick(61)
        h.ctrl.queue.add(("team-a", "web"))
        h.settle(2, step=31)
        st = h.obj()["status"]
        self.assertEqual(st["state"], "Unknown")
        self.assertEqual(S.status.get_condition(st["conditions"], "Ready")["status"], "Unknown")
        h.rt.down = False
        h.rt.advance(st["appId"], State.RUNNING)
        h.settle(4, step=31)
        self.assertEqual(h.obj()["status"]["phase"], "Running")

    def test_delete_during_downstream_outage_keeps_finalizer_until_cancel(self):
        h = S.Harness(cfg={"circuit": {"threshold": 100, "resetAfter": 1.0}})
        h.kube.apply(S.workload())
        h.settle(3)
        app = h.obj()["status"]["appId"]
        h.rt.down = True
        h.kube.delete("team-a", "web")
        h.settle(3, step=31)
        self.assertIn(S.controller.FINALIZER, h.obj()["metadata"]["finalizers"])   # no leaked runtime
        h.rt.down = False
        h.settle(4, step=31)
        with self.assertRaises(S.kube.ApiError):
            h.obj()
        self.assertEqual(h.rt.placements[app]["state"], "Cancelled")

    def test_placement_lost_is_replaced(self):
        h = S.Harness()
        h.kube.apply(S.workload())
        h.settle(3)
        h.rt.placements.clear(); h.rt.by_key.clear()
        h.ctrl.queue.add(("team-a", "web"))
        h.settle(4, step=1)
        self.assertEqual(h.obj()["status"]["state"], "Placed")
        self.assertEqual(h.rt.launches, 2)

    def test_leader_failover_and_split_brain_fencing(self):
        kube, rt, lease, clock = S.kube.FakeKube(), S.downstream.InMemoryRuntime(), S.leader.LeaseStore(), S.Clock()
        a = S.Harness(kube_=kube, runtime=rt, lease_store=lease, clock=clock, ident="a")
        b = S.Harness(kube_=kube, runtime=rt, lease_store=lease, clock=clock, ident="b")
        kube.apply(S.workload())
        a.settle(3)
        b.settle(3)
        self.assertEqual(rt.launches, 1)
        self.assertEqual(b.ctrl.run_once(), 0)                  # standby does nothing
        token_a = a.elector.token
        clock.tick(20)                                           # a is paused past its lease
        self.assertTrue(b.elector.try_acquire_or_renew())
        self.assertGreater(b.elector.token, token_a)
        kube.apply(S.workload(name="w2"))
        b.settle(3)
        # a wakes up and tries to act with its stale token: the runtime refuses
        with self.assertRaises(S.lifecycle.PlaneError):
            rt.place(S.downstream.envelope({"units": []}, {"appId": "app-z"}, "zz", token_a))
        self.assertFalse(a.elector.try_acquire_or_renew())
        self.assertEqual(rt.launches, 2)

    def test_lease_store_partition_loses_leadership_after_margin(self):
        clock, lease = S.Clock(), S.leader.LeaseStore()
        e = S.leader.Elector(lease, "a", 10, clock)
        self.assertTrue(e.try_acquire_or_renew())
        lease.down = True
        clock.tick(5)
        self.assertTrue(e.try_acquire_or_renew())               # inside 80% safety margin
        clock.tick(4)
        self.assertFalse(e.try_acquire_or_renew())
        self.assertFalse(e.is_leader())

    def test_disconnected_control_plane_reconnect_converges(self):
        h = S.Harness()
        h.kube.apply(S.workload())
        h.settle(3)
        app = h.obj()["status"]["appId"]
        h.kube.down = True                                       # API server unreachable for a long time
        h.rt.advance(app, State.RUNNING)                         # runtime keeps running workloads
        h.settle(5, step=60)
        self.assertEqual(h.rt.placements[app]["state"], "Running")   # no teardown while disconnected
        h.kube.down = False
        h.ctrl.resync()
        h.settle(4, step=31)
        self.assertEqual(h.obj()["status"]["phase"], "Running")
        self.assertEqual(h.rt.launches, 1)


if __name__ == "__main__":
    unittest.main()
