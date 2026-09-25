"""Closure #20: deterministic fault injection at every named lifecycle point."""
import unittest

from _util import rt, sub

AF = rt.AsyncFunctions


class Injector:
    def __init__(self, point, times=1):
        self.point, self.times, self.hits, self.armed = point, times, 0, False

    def __call__(self, point, call_id):
        if self.armed and point == self.point and self.times:
            self.times -= 1
            self.hits += 1
            raise rt.FaultInjected(point)


def snapshot_state(f):
    return (dict(f.in_flight), dict(f._queued), dict(f._terminal), dict(f._active_by_fn), f._ids.next_id)


FAULT_MATRIX = []   # (point, scenario, result) - exported by tools/gen_evidence.py


class FaultInjection(unittest.TestCase):
    def _mk(self, inj):
        return AF("i", declared={"a": True, "q": True},
                  reentrancy={"q": rt.ReentrancyPolicy(rt.ReentrancyMode.QUEUE, 2)}, fault_injector=inj)

    def test_every_point_is_atomic_and_recoverable(self):
        scenarios = {
            "admit": lambda f, c: f.invoke("a"),
            "allocate": lambda f, c: f.invoke("a"),
            "publish_completion": lambda f, c: f.complete(c.call_id, 1),
            "cancel": lambda f, c: f.cancel(c.call_id),
            "trap": lambda f, c: f.trap_all(),
            "promote": lambda f, c: f.complete(c.call_id, 1),
        }
        self.assertEqual(set(scenarios), set(rt.FAULT_POINTS))
        for point, action in scenarios.items():
            with self.subTest(point):
                inj = Injector(point)
                f = self._mk(inj)
                c = f.invoke("q")
                f.invoke("q")                       # queued behind c (exercises promote)
                before = snapshot_state(f)
                inj.armed = True
                with self.assertRaises(rt.FaultInjected):
                    action(f, c)
                self.assertEqual(inj.hits, 1)
                self.assertEqual(snapshot_state(f), before, "fault left partial state")
                # recovery: the same operation now succeeds without restart
                action(f, c)
                f.cancel_all("drain")
                self.assertEqual(f.calls_in_flight + f.calls_queued, 0)
                self.assertEqual(f.double_delivery_attempts, 0)
                FAULT_MATRIX.append((point, "inject-then-retry", "PASS"))

    def test_trap_before_first_suspension_during_and_before_completion(self):
        f = AF("i", declared={"a": True})
        early = f.invoke("a")                          # before first suspension
        self.assertEqual(f.trap_all(), 1)
        mid = f.invoke("a")
        f.add_terminal_listener(mid.call_id, lambda *a: None)
        late = f.invoke("a")
        f.trap_all()
        for c in (early, mid, late):
            with self.assertRaises(rt.CallTrapped):
                f.complete(c.call_id, "late")
        self.assertEqual(f.trapped_calls, 3)

    def test_sink_and_listener_failures_are_isolated(self):
        def bad_sink(ev):
            raise OSError("disk full")

        f = AF("i", declared={"s": True}, stateful=frozenset({"s"}), event_sink=bad_sink)
        c = f.invoke("s")

        def bad_listener(*a):
            raise RuntimeError("consumer bug")

        f.add_terminal_listener(c.call_id, bad_listener)
        self.assertEqual(f.complete(c.call_id, 5), 5)    # correctness path unaffected
        self.assertEqual(f.listener_failures, 1)
        self.assertGreaterEqual(f.sink_failures, 1)
        c2 = f.invoke("s")                                # lock not left held
        f.complete(c2.call_id, 6)

    def test_slow_sink_never_runs_under_lock(self):
        import threading
        f = AF("i", declared={"a": True})
        inside = []

        def sink(ev):
            got = f._lock.acquire(blocking=False)
            # RLock is re-entrant for the same thread: prove it is not *held* by checking depth.
            inside.append(f._depth)
            if got:
                f._lock.release()

        f.event_sink = sink
        c = f.invoke("a")
        f.complete(c.call_id, 1)
        self.assertTrue(inside and all(d == 0 for d in inside))

        # and from another thread the lock is free while a sink blocks
        gate = threading.Event()
        released = threading.Event()

        def blocking_sink(ev):
            gate.wait(2)

        f.event_sink = blocking_sink
        c = f.invoke("a")
        t = threading.Thread(target=lambda: (f.complete(c.call_id, 1), released.set()))
        t.start()
        other = f.invoke("a")                  # would deadlock if the sink held the lock
        gate.set()
        t.join(2)
        self.assertTrue(released.is_set())
        f.complete(other.call_id, 1)

    def test_abi_transport_fault_leaves_call_live(self):
        abi = sub("abi")
        f = AF("i", declared={"a": True}, transport=abi.Codec())
        c = f.invoke("a")
        with self.assertRaises(abi.AbiTypeError):
            f.complete(c.call_id, object())            # unserialisable payload
        self.assertEqual(f.calls_in_flight, 1)
        self.assertEqual(f.complete(c.call_id, {"ok": 1}), {"ok": 1})

    def test_unsupported_topology_rejected(self):
        pre = sub("preflight")
        self.assertTrue(pre.run(topology="single-owner")["ok"])
        rep = pre.run(topology="multi-owner")
        self.assertFalse(rep["ok"])
        self.assertIn("process-local", " ".join(rep["errors"]))

    def test_dependency_unavailable_fails_closed(self):
        pre = sub("preflight")
        rep = pre.run(require_pk_core=True, pk_core_module="pk_core_definitely_missing")
        self.assertFalse(rep["ok"])
        self.assertIn("pk_core", " ".join(rep["errors"]))


if __name__ == "__main__":
    unittest.main()
