"""Components 7, 9-30, 39-42: lifecycle, timing, cancellation, budgets, table."""
import itertools
import threading
import unittest

from _util import mk, FakeClock
from inv15_new_asynchronous_abi import handles as H
from inv15_new_asynchronous_abi.errors import (AbiError, CancelAck, CancelReason, ErrorCode)
from inv15_new_asynchronous_abi.host import AsyncHost, Limits, ROW_BYTES
from inv15_new_asynchronous_abi.lifecycle import State, TRANSITIONS, TERMINAL, check, IllegalTransition


def code(fn):
    try:
        fn()
    except AbiError as e:
        return e.code
    return None


class TestLifecycle(unittest.TestCase):
    def test_terminal_states_have_no_exits(self):
        for s in TERMINAL:
            self.assertEqual(TRANSITIONS[s], frozenset())

    def test_no_edge_back_to_pending(self):
        for s, dsts in TRANSITIONS.items():
            self.assertNotIn(State.PENDING, dsts)

    def test_forbidden_edges_raise(self):
        for a, b in itertools.product(State, State):
            if b in TRANSITIONS[a]:
                check(a, b)
            else:
                with self.assertRaises(IllegalTransition):
                    check(a, b)


class TestCore(unittest.TestCase):
    def setUp(self):
        self.h, self.clock = mk(Limits(instance=4))
        self.v = self.h.register("i1", tenant="t1", workload="w1")

    def test_immediate_none_is_a_value(self):
        self.assertEqual(self.v.call(None), ("value", None))

    def test_complete_wait_take(self):
        _, x = self.v.call()
        self.assertEqual(code(lambda: self.v.take(x)), ErrorCode.NOT_READY)
        self.assertEqual(self.v.wait(iter([x])), [])
        self.assertEqual(self.h.complete(x, b"r"), "published")
        self.assertEqual(self.v.wait((y for y in [x, x])), [x])
        self.assertEqual(self.v.take(x), b"r")
        self.assertEqual(code(lambda: self.v.take(x)), ErrorCode.HANDLE_CONSUMED)

    def test_duplicate_publication_keeps_first(self):
        _, x = self.v.call()
        self.h.complete(x, 1)
        self.assertEqual(code(lambda: self.h.complete(x, 2)), ErrorCode.DUPLICATE_PUBLICATION)
        self.assertEqual(code(lambda: self.h.trap(x)), ErrorCode.DUPLICATE_PUBLICATION)
        self.assertEqual(self.v.take(x), 1)

    def test_trap_state(self):
        _, x = self.v.call()
        self.h.trap(x, "boom")
        self.assertEqual(self.v.wait([x]), [x])
        self.assertEqual(code(lambda: self.v.take(x)), ErrorCode.TRAPPED)
        self.assertEqual(code(lambda: self.v.take(x)), ErrorCode.HANDLE_CONSUMED)

    def test_budget_and_recovery(self):
        hs = [self.v.call()[1] for _ in range(4)]
        self.assertEqual(code(self.v.call), ErrorCode.BUDGET_EXHAUSTED)
        self.v.cancel(hs[0])
        self.h.complete(hs[1], 0)
        self.v.take(hs[1])
        self.h.complete(hs[2], 0)
        self.v.cancel(hs[2])
        self.assertEqual(len([self.v.call() for _ in range(3)]), 3)

    def test_uniform_foreign_error(self):
        other = self.h.register("i2", tenant="t2", workload="w2")
        _, x = self.v.call()
        forged = H.Handle(x.epoch, x.slot, x.generation, bytes(16))
        bogus = H.Handle(x.epoch, 999, 0, bytes(16))
        msgs = set()
        for view, hd in ((other, x), (self.v, forged), (self.v, bogus)):
            try:
                view.wait([hd])
            except AbiError as e:
                msgs.add((e.code, e.detail))
        self.assertEqual(msgs, {(ErrorCode.FOREIGN_HANDLE, "unknown handle")})
        self.assertEqual(code(lambda: self.v.wait(["nope"])), ErrorCode.FOREIGN_HANDLE)

    def test_wait_semantics_empty_order_repeat(self):
        self.assertEqual(self.v.wait([]), [])
        xs = [self.v.call()[1] for _ in range(3)]
        for x in reversed(xs):
            self.h.complete(x, 0)
        self.assertEqual(self.v.wait([xs[2], xs[0], xs[1]]), [xs[2], xs[0], xs[1]])  # request order
        self.assertEqual(self.v.wait([xs[0]]), [xs[0]])   # waits report, never consume
        self.assertEqual(self.v.wait([xs[0]]), [xs[0]])
        self.v.take(xs[0])
        self.assertEqual(code(lambda: self.v.wait([xs[0], xs[1]])), ErrorCode.HANDLE_CONSUMED)  # no partial result

    def test_wait_set_bound(self):
        _, x = self.v.call()
        self.assertEqual(code(lambda: self.v.wait([x] * 5)), ErrorCode.WAIT_SET_TOO_LARGE)
        self.assertEqual(code(lambda: self.v.wait(5)), ErrorCode.INVALID_ARGUMENT)


class TestGenerations(unittest.TestCase):
    def test_slot_reuse_rejects_stale_handle(self):
        h, _ = mk(Limits(instance=1, process=1, tenant=1, workload=1, tenant_share=1.0), max_slots=1)
        v = h.register("i", tenant="t", workload="w")
        _, a = v.call()
        v.cancel(a)
        _, b = v.call()
        self.assertEqual((a.slot, b.slot), (0, 0))
        self.assertEqual(b.generation, a.generation + 1)
        self.assertEqual(code(lambda: v.take(a)), ErrorCode.HANDLE_CONSUMED)
        self.assertEqual(h.complete(a, "late"), "discarded_late")  # cannot publish into new occupant
        self.assertEqual(v.wait([b]), [])

    def test_generation_wrap_retires_slot(self):
        h, _ = mk(Limits(instance=1, process=1, tenant=1, workload=1, tenant_share=1.0), max_slots=1, max_generation=3)
        v = h.register("i", tenant="t", workload="w")
        seen = []
        for _ in range(4):
            _, x = v.call()
            seen.append((x.slot, x.generation))
            v.cancel(x)
        self.assertEqual(seen, [(0, 0), (0, 1), (0, 2), (0, 3)])
        self.assertEqual(code(v.call), ErrorCode.HANDLE_SPACE_EXHAUSTED)
        self.assertEqual(h.explain()["process"]["retired_slots"], 1)
        # accounting did not leak on the failed admission
        self.assertEqual(h.explain()["process"]["live"], 0)


class TestRng(unittest.TestCase):
    def test_fail_closed(self):
        def boom(n):
            raise OSError("no entropy")
        h, _ = mk(token_source=boom)
        v = h.register("i", tenant="t", workload="w")
        self.assertEqual(code(v.call), ErrorCode.RNG_UNAVAILABLE)
        self.assertEqual(h.explain()["process"]["live"], 0)
        self.assertEqual(h.explain()["process"]["memory_bytes"], 0)

    def test_health_checks(self):
        for src in (lambda n: bytes(16), lambda n: b"x" * 15, lambda n: b"\x07" * 16):
            h, _ = mk(token_source=src)
            v = h.register("i", tenant="t", workload="w")
            if src(16) == b"\x07" * 16:
                v.call()
            self.assertEqual(code(v.call), ErrorCode.RNG_UNAVAILABLE)


class TestDeadlines(unittest.TestCase):
    def setUp(self):
        self.h, self.c = mk()
        self.v = self.h.register("i", tenant="t", workload="w")

    def test_call_timeout_and_inherited_deadline(self):
        _, p = self.v.call(timeout_ns=100)
        _, c = self.v.call(parent=p, timeout_ns=10_000)
        self.c.t += 101
        self.assertEqual(self.h.expire(), 2)
        self.assertEqual(code(lambda: self.v.take(p)), ErrorCode.CALL_TIMEOUT)
        self.assertEqual(code(lambda: self.v.take(c)), ErrorCode.DEADLINE_EXCEEDED)

    def test_admission_validation(self):
        self.assertEqual(code(lambda: self.v.call(timeout_ns=-1)), ErrorCode.INVALID_ARGUMENT)
        self.assertEqual(code(lambda: self.v.call(deadline_ns=1 << 63)), ErrorCode.INVALID_ARGUMENT)
        self.assertEqual(code(lambda: self.v.call(timeout_ns=(1 << 63) - 10)), ErrorCode.INVALID_ARGUMENT)
        self.assertEqual(code(lambda: self.v.call(deadline_ns=self.c.t)), ErrorCode.DEADLINE_EXCEEDED)
        self.assertEqual(self.h.explain()["process"]["live"], 0)

    def test_completion_before_expire_wins(self):
        _, x = self.v.call(timeout_ns=5)
        self.h.complete(x, "v")
        self.c.t += 10
        self.assertEqual(self.h.expire(), 0)
        self.assertEqual(self.v.take(x), "v")

    def test_wait_timeout_leaves_handle_live(self):
        _, x = self.v.call()
        for _ in range(5):
            self.assertEqual(code(lambda: self.v.wait_blocking([x], 1_000)), ErrorCode.WAIT_TIMEOUT)
        self.assertEqual(self.v.waiters, 0)
        self.h.complete(x, 7)
        self.assertEqual(self.v.wait_blocking([x], 1_000), [x])
        self.assertEqual(self.v.take(x), 7)

    def test_clock_regression_and_failure(self):
        self.h.now()
        self.c.t -= 500
        self.h.now()
        self.assertEqual(self.h.clock_regressions, 1)
        bad = AsyncHost(clock=lambda: 1 / 0)
        v = bad.register("i", tenant="t", workload="w")
        self.assertEqual(code(v.call), ErrorCode.HOST_FAILURE)


class TestCancellation(unittest.TestCase):
    def setUp(self):
        self.h, self.c = mk()
        self.v = self.h.register("i", tenant="t", workload="w")

    def test_ack_states(self):
        _, a = self.v.call()
        _, b = self.v.call()
        _, u = self.v.call(cancellable=False)
        self.h.complete(b, 1)
        self.assertEqual(self.v.cancel(a), CancelAck.PROPAGATED)
        self.assertEqual(self.v.cancel(a), CancelAck.ALREADY_TERMINAL)
        self.assertEqual(self.v.cancel(b), CancelAck.COMPLETED_BEFORE_CANCEL)
        self.assertEqual(self.v.cancel(u), CancelAck.UNABLE_TO_CANCEL)
        self.assertEqual(self.h.complete(a, "late"), "discarded_late")
        self.assertEqual(code(lambda: self.v.cancel(a, "free text")), ErrorCode.INVALID_ARGUMENT)
        self.assertGreater(self.h.metrics.hist["cancel_ack_ns"].n, 0)

    def test_tree_and_detached(self):
        _, root = self.v.call()
        kids = [self.v.call(parent=root)[1] for _ in range(3)]
        grand = self.v.call(parent=kids[0])[1]
        det = self.v.call(parent=root, detached=True)[1]
        self.h.complete(kids[1], "done")
        self.assertEqual(self.v.cancel(root), CancelAck.PROPAGATED)
        for x in (root, kids[0], kids[2], grand):
            self.assertEqual(self.v.cancel(x), CancelAck.ALREADY_TERMINAL)
        self.assertEqual(self.v.wait([kids[1], det]), [kids[1]])  # completed child survives, detached runs
        self.assertEqual(self.v.stats["cancellations"], {"CALLER_REQUESTED": 1, "PARENT_CANCELLED": 3})
        self.h.teardown(self.v)
        self.assertEqual(self.h.explain()["process"]["live"], 0)

    def test_depth_limit(self):
        h, _ = mk(Limits(instance=100))
        v = h.register("i", tenant="t", workload="w")
        _, p = v.call()
        for _ in range(63):  # root is level 1; levels 2..64 allowed
            _, p = v.call(parent=p)
        self.assertEqual(code(lambda: v.call(parent=p)), ErrorCode.INVALID_ARGUMENT)

    def test_cancel_all_releases_ready_and_pending(self):
        hs = [self.v.call()[1] for _ in range(3)]
        self.h.complete(hs[0], 0)
        self.assertEqual(self.v.cancel_all(), 2)
        self.assertEqual(self.v.stats["abandoned"], 1)
        self.assertEqual(self.h.explain()["process"]["memory_bytes"], 0)


class TestIdempotency(unittest.TestCase):
    def test_dedup_and_resolved_key(self):
        h, _ = mk()
        v = h.register("i", tenant="t", workload="w")
        _, a = v.call(idempotency_key="k1")
        _, b = v.call(idempotency_key="k1")
        self.assertEqual(a, b)
        self.assertEqual(h.explain()["process"]["live"], 1)
        h.complete(a, 1)
        v.take(a)
        self.assertEqual(code(lambda: v.call(idempotency_key="k1")), ErrorCode.HANDLE_CONSUMED)

    def test_window_bounded(self):
        h, _ = mk(Limits(idempotency_window=4))
        v = h.register("i", tenant="t", workload="w")
        for i in range(20):
            _, x = v.call(idempotency_key=f"k{i}")
            v.cancel(x)
        self.assertEqual(len(v.idem_done), 4)


class TestBudgetsFairness(unittest.TestCase):
    def test_precedence_and_scopes(self):
        h, _ = mk(Limits(instance=4, workload=5, tenant=6, process=7, tenant_share=1.0))
        a = h.register("a", tenant="t", workload="w")
        b = h.register("b", tenant="t", workload="w")
        c = h.register("c", tenant="t", workload="w2")
        d = h.register("d", tenant="u", workload="w3")
        for _ in range(4):
            a.call()
        self.assertEqual(code(a.call), ErrorCode.BUDGET_EXHAUSTED)
        b.call()
        self.assertEqual(code(b.call), ErrorCode.BUDGET_EXHAUSTED)   # workload
        c.call()
        self.assertEqual(code(c.call), ErrorCode.BUDGET_EXHAUSTED)   # tenant
        d.call()
        self.assertEqual(code(d.call), ErrorCode.BUDGET_EXHAUSTED)   # process
        self.assertEqual((a.stats["refusals"], b.stats["refusals"], c.stats["refusals"], d.stats["refusals"]),
                         ({"instance": 1}, {"workload": 1}, {"tenant": 1}, {"process": 1}))

    def test_fair_share_prevents_monopoly(self):
        h, _ = mk(Limits(instance=64, workload=64, tenant=64, process=10, tenant_share=0.5))
        hog = h.register("hog", tenant="t1", workload="w1")
        other = h.register("o", tenant="t2", workload="w2")
        n = 0
        while True:
            try:
                hog.call(priority="high")
                n += 1
            except AbiError:
                break
        self.assertEqual(n, 5)
        self.assertEqual(len([other.call() for _ in range(5)]), 5)

    def test_priority_is_validated_and_does_not_bypass(self):
        h, _ = mk(Limits(instance=1))
        v = h.register("i", tenant="t", workload="w")
        self.assertEqual(code(lambda: v.call(priority="urgent")), ErrorCode.INVALID_ARGUMENT)
        v.call(priority="high")
        self.assertEqual(code(lambda: v.call(priority="high")), ErrorCode.BUDGET_EXHAUSTED)

    def test_concurrent_admission_never_oversubscribes(self):
        h = AsyncHost(Limits(instance=50, workload=50, tenant=50, process=50, tenant_share=1.0))
        vs = [h.register(f"i{k}", tenant="t", workload="w") for k in range(8)]
        ok = []

        def worker(v):
            for _ in range(20):
                try:
                    v.call()
                    ok.append(1)
                except AbiError:
                    pass

        ts = [threading.Thread(target=worker, args=(v,)) for v in vs]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(ok), 50)
        self.assertEqual(h.explain()["process"]["live"], 50)


class TestDrainDisable(unittest.TestCase):
    def test_drain_policies(self):
        h, c = mk()
        v = h.register("i", tenant="t", workload="w")
        _, x = v.call()
        _, y = v.call()
        p = h.drain(v, "allow")
        self.assertEqual((p["state"], p["live"]), ("draining", 2))
        self.assertEqual(code(v.call), ErrorCode.DRAINING)
        h.complete(x, 1)
        v.take(x)
        p = h.drain(v, "cancel")
        self.assertEqual((p["state"], p["live"]), ("drained", 0))
        self.assertEqual(h.complete(y, "late"), "discarded_late")
        h.resume_admission(v)
        v.call()

    def test_emergency_disable(self):
        h, _ = mk()
        v = h.register("i", tenant="t", workload="w")
        _, x = v.call()
        h.disable()
        self.assertEqual(code(v.call), ErrorCode.DISABLED)
        self.assertEqual(v.cancel(x), CancelAck.ALREADY_TERMINAL)
        self.assertEqual(v.stats["cancellations"], {"EMERGENCY_DISABLE": 1})
        h.enable()
        v.call()


class TestTeardownRestart(unittest.TestCase):
    def test_teardown_wakes_waiters_and_reclaims(self):
        h = AsyncHost()
        v = h.register("i", tenant="t", workload="w")
        _, x = v.call()
        released = []
        _, y = v.call()
        h.complete(y, b"payload", release=released.append)
        err = []

        def waiter():
            try:
                v.wait_blocking([x], 5_000_000_000)
            except AbiError as e:
                err.append(e.code)

        t = threading.Thread(target=waiter)
        t.start()
        import time
        time.sleep(0.05)
        h.teardown(v)
        t.join(2)
        self.assertEqual(err, [ErrorCode.INVALIDATED])
        self.assertEqual(released, [b"payload"])
        self.assertEqual(h.complete(x, 1), "discarded_late")
        e = h.explain()["process"]
        self.assertEqual((e["live"], e["memory_bytes"]), (0, 0))
        self.assertEqual(code(lambda: v.take(x)), ErrorCode.INVALIDATED)
        self.assertEqual(code(v.call), ErrorCode.INVALIDATED)

    def test_restart_epoch(self):
        h = AsyncHost()
        v = h.register("i", tenant="t", workload="w")
        _, x = v.call()
        blob = v.serialize(x)
        h.restart()
        v2 = h.register("i", tenant="t", workload="w")
        self.assertEqual(code(lambda: v2.wait([x])), ErrorCode.INVALIDATED)
        self.assertEqual(code(lambda: v2.deserialize(blob)), ErrorCode.INVALIDATED)
        self.assertEqual(h.complete(x, 1), "discarded_late")


class TestReplayTenant(unittest.TestCase):
    def test_serialized_handle_bound_to_tenant_instance(self):
        h = AsyncHost()
        a = h.register("a", tenant="t1", workload="w")
        b = h.register("b", tenant="t2", workload="w")
        _, x = a.call()
        blob = a.serialize(x)
        self.assertEqual(a.deserialize(blob), x)
        self.assertEqual(code(lambda: b.deserialize(blob)), ErrorCode.REPLAYED)
        a.cancel(x)
        self.assertEqual(code(lambda: a.deserialize(blob)), ErrorCode.HANDLE_CONSUMED)
        self.assertTrue(any(r["kind"] == "replay" for r in h.audit.records))


class TestMemoryOwnership(unittest.TestCase):
    def test_accounting_and_ceiling(self):
        h, _ = mk(Limits(mem_instance=ROW_BYTES * 2 + 100))
        v = h.register("i", tenant="t", workload="w")
        _, x = v.call()
        _, y = v.call()
        self.assertEqual(code(v.call), ErrorCode.MEMORY_EXHAUSTED)
        self.assertEqual(h.explain()["process"]["live"], 2)  # budget rolled back
        self.assertEqual(code(lambda: h.complete(x, b"z" * 101)), ErrorCode.MEMORY_EXHAUSTED)
        self.assertEqual(v.wait([x]), [])                     # stays pending
        h.complete(x, b"z" * 100)
        self.assertEqual(h.explain()["process"]["memory_bytes"], 2 * ROW_BYTES + 100)
        v.take(x)
        v.cancel(y)
        self.assertEqual(h.explain()["process"]["memory_bytes"], 0)

    def test_release_exactly_once_and_ownership_transfer(self):
        h, _ = mk()
        v = h.register("i", tenant="t", workload="w")
        rel = []
        hs = [v.call()[1] for _ in range(4)]
        for i, x in enumerate(hs):
            h.complete(x, f"p{i}", release=rel.append)
        v.take(hs[0])               # transferred: no release
        v.cancel(hs[1])             # abandoned: released
        v.cancel_all()              # hs[2], hs[3] abandoned
        self.assertEqual(sorted(rel), ["p1", "p2", "p3"])
        _, z = v.call()
        v.cancel(z)
        self.assertEqual(h.complete(z, "late", release=rel.append), "discarded_late")
        self.assertEqual(rel.count("late"), 1)

    def test_mutable_buffers_are_copied(self):
        h, _ = mk()
        v = h.register("i", tenant="t", workload="w")
        _, x = v.call()
        buf = bytearray(b"abc")
        h.complete(x, buf)
        buf[0] = 0
        self.assertEqual(v.take(x), b"abc")

    def test_release_errors_contained(self):
        h, _ = mk()
        v = h.register("i", tenant="t", workload="w")
        _, x = v.call()
        h.complete(x, 1, release=lambda _: 1 / 0)
        v.cancel(x)
        self.assertEqual(h.release_errors, 1)


class TestReadyQueue(unittest.TestCase):
    def test_round_robin_batches_and_lazy_deletion(self):
        h, _ = mk(Limits(instance=64, tenant_share=1.0))
        a = h.register("a", tenant="t1", workload="w")
        b = h.register("b", tenant="t2", workload="w")
        ha = [a.call()[1] for _ in range(6)]
        hb = [b.call()[1] for _ in range(2)]
        for x in ha + hb:
            h.complete(x, 0)
        a.cancel(ha[1])   # retired before delivery -> skipped
        batch = h.ready_batch(4)
        self.assertEqual([n for n, _ in batch], ["a", "b", "a", "b"])
        rest = h.ready_batch(64)
        self.assertEqual(len(batch) + len(rest), 7)
        self.assertEqual(h.ready_batch(8), [])
        self.assertEqual(code(lambda: h.ready_batch(0)), ErrorCode.INVALID_ARGUMENT)


class TestSubscribe(unittest.TestCase):
    def test_fires_once_including_already_ready(self):
        h, _ = mk()
        v = h.register("i", tenant="t", workload="w")
        _, x = v.call()
        _, y = v.call()
        h.complete(y, 1)
        got = []
        s1 = v.subscribe([x, y], lambda s: got.append(s.result))
        self.assertEqual(got, ["ready"])
        s2 = v.subscribe([x], lambda s: got.append("x"))
        h.complete(x, 2)
        self.assertEqual(got, ["ready", "x"])
        self.assertFalse(s2.cancel())
        self.assertEqual(v.waiters, 0)
        self.assertTrue(s1.fired)

    def test_cancelled_subscription_never_fires(self):
        h, _ = mk()
        v = h.register("i", tenant="t", workload="w")
        _, x = v.call()
        got = []
        s = v.subscribe([x], lambda s: got.append(1))
        self.assertTrue(s.cancel())
        h.complete(x, 1)
        self.assertEqual(got, [])
        self.assertEqual(v.waiters, 0)

    def test_waiter_quota(self):
        h, _ = mk(Limits(waiters_per_instance=2))
        v = h.register("i", tenant="t", workload="w")
        _, x = v.call()
        v.subscribe([x], lambda s: None)
        v.subscribe([x], lambda s: None)
        self.assertEqual(code(lambda: v.subscribe([x], lambda s: None)), ErrorCode.BUDGET_EXHAUSTED)


if __name__ == "__main__":
    unittest.main()
