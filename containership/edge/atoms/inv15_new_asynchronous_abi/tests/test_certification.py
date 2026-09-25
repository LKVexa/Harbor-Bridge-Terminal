"""Components 55-60, 63: property, fuzz, race, lost-wakeup, soak, overload, faults.

Scale is controlled by INV15_SCALE (default 1). The defaults are CI-sized; the
counts actually executed are printed and recorded by tools/certify.py. They are
NOT the 'millions' / 'long-duration' figures the checklist asks for.
"""
import os
import random
import threading
import time
import tracemalloc
import unittest

from _util import mk
from inv15_new_asynchronous_abi import handles as H
from inv15_new_asynchronous_abi.errors import AbiError, CancelAck, CancelReason, ErrorCode
from inv15_new_asynchronous_abi.host import AsyncHost, Limits, ROW_BYTES
from inv15_new_asynchronous_abi.lifecycle import State
from inv15_new_asynchronous_abi.wire import codec

SCALE = int(os.environ.get("INV15_SCALE", "1"))
COUNTS = {}


def invariants(tc, h):
    e = h.explain()["process"]
    live_rows = [r for r in h._slots if r is not None]
    tc.assertEqual(e["live"], len(live_rows))
    tc.assertEqual(e["memory_bytes"], sum(ROW_BYTES + r.payload_bytes for r in live_rows))
    for v in h.views.values():
        tc.assertLessEqual(len(v.live), v.budget)
    tc.assertLessEqual(e["tombstones"], h.limits.tombstones)
    tc.assertEqual(len(h._tokens), len(live_rows))


class TestProperty(unittest.TestCase):
    def test_random_sequences_against_model(self):
        runs, steps = 30 * SCALE, 400
        for seed in range(runs):
            rng = random.Random(seed)
            h, clk = mk(Limits(instance=6, tombstones=16))
            vs = [h.register(f"i{k}", tenant=f"t{k % 2}", workload="w") for k in range(3)]
            model = {}   # handle -> (view, state, value)
            taken = set()
            for step in range(steps):
                op = rng.choice(["call", "call", "complete", "trap", "take", "cancel", "wait", "forge",
                                 "expire", "cancel_all", "tick"])
                v = rng.choice(vs)
                try:
                    if op == "call":
                        kind, x = v.call(timeout_ns=rng.choice([None, 5, 50]))
                        model[x] = (v, "pending", None)
                    elif op == "tick":
                        clk.t += rng.randrange(20)
                    elif op == "expire":
                        h.expire()
                        for x, (vv, st, val) in list(model.items()):
                            r = h._producer_row(x)
                            if r is not None and r.state is State.TIMED_OUT and st == "pending":
                                model[x] = (vv, "timed_out", None)
                    elif model:
                        x = rng.choice(list(model))
                        vv, st, val = model[x]
                        if op == "complete":
                            res = h.complete(x, step)
                            if st == "pending":
                                self.assertEqual(res, "published")
                                model[x] = (vv, "ready", step)
                            else:
                                self.fail("duplicate publication accepted")
                        elif op == "trap":
                            h.trap(x)
                            self.assertEqual(st, "pending")
                            model[x] = (vv, "trapped", None)
                        elif op == "take":
                            got = vv.take(x)
                            self.assertEqual((st, got), ("ready", val))
                            self.assertNotIn(x, taken)
                            taken.add(x)
                            del model[x]
                        elif op == "cancel":
                            ack = vv.cancel(x)
                            self.assertEqual(ack, CancelAck.PROPAGATED if st == "pending" else CancelAck.COMPLETED_BEFORE_CANCEL)
                            del model[x]
                        elif op == "wait":
                            self.assertEqual(bool(vv.wait([x])), st != "pending")
                        elif op == "forge":
                            forged = H.Handle(x.epoch, x.slot, x.generation, bytes(16))
                            with self.assertRaises(AbiError):
                                vv.wait([forged])
                        elif op == "cancel_all":
                            vv.cancel_all()
                            for y in [y for y, m in model.items() if m[0] is vv]:
                                del model[y]
                except AbiError as e:
                    if op == "call":
                        self.assertIn(e.code, (ErrorCode.BUDGET_EXHAUSTED,))
                    elif op == "complete":
                        self.assertEqual(e.code, ErrorCode.DUPLICATE_PUBLICATION)
                        self.assertNotEqual(model[x][1], "pending")
                    elif op == "trap":
                        self.assertNotEqual(model[x][1], "pending")
                    elif op == "take":
                        exp = {"pending": ErrorCode.NOT_READY, "trapped": ErrorCode.TRAPPED,
                               "timed_out": ErrorCode.CALL_TIMEOUT}[model[x][1]]
                        self.assertEqual(e.code, exp)
                        if exp != ErrorCode.NOT_READY:
                            del model[x]
                    else:
                        raise
                invariants(self, h)
        COUNTS["property_sequences"] = runs
        COUNTS["property_steps"] = runs * steps


class TestFuzz(unittest.TestCase):
    def test_decoders_never_crash(self):
        rng = random.Random(7)
        seeds = [codec.encode_call_result("value", b"abc"),
                 codec.encode_call_result("subtask", H.Handle(1, 2, 3, bytes(range(16)))),
                 codec.encode_call_result("error", {"code": 4, "retryable": True, "detail": "x"}),
                 codec.encode_wait([H.Handle(1, 2, 3, bytes(16))]),
                 codec.encode_cancel(H.Handle(1, 2, 3, bytes(16)), CancelReason.DRAIN), codec.encode_ack(CancelAck.PROPAGATED)]
        n = 20000 * SCALE
        outcomes = {}
        for i in range(n):
            base = bytearray(rng.choice(seeds))
            m = rng.randrange(4)
            if m == 0 and base:
                base[rng.randrange(len(base))] = rng.randrange(256)
            elif m == 1:
                del base[rng.randrange(len(base) + 1):]
            elif m == 2:
                base += bytes(rng.randrange(256) for _ in range(rng.randrange(8)))
            else:
                base = bytearray(rng.randrange(256) for _ in range(rng.randrange(64)))
            for dec in (codec.decode_call_result, codec.decode_wait, codec.decode_cancel, codec.decode_ack, H.decode):
                try:
                    dec(bytes(base))
                    outcomes["ok"] = outcomes.get("ok", 0) + 1
                except AbiError as e:
                    outcomes[e.code.name] = outcomes.get(e.code.name, 0) + 1
        COUNTS["fuzz_inputs"] = n
        COUNTS["fuzz_decodes"] = n * 5
        self.assertGreater(outcomes.get("MALFORMED", 0), 0)

    def test_oversized_wait(self):
        with self.assertRaises(AbiError):
            codec.decode_wait(b"\x01\x01\xff\xff")


class TestRaces(unittest.TestCase):
    def test_complete_take_cancel_teardown_interleavings(self):
        rounds = 40 * SCALE
        for r in range(rounds):
            h = AsyncHost(Limits(instance=64, workload=512, tenant=512, process=512, tenant_share=1.0))
            vs = [h.register(f"i{k}", tenant="t", workload="w") for k in range(4)]
            handles = [(v, v.call()[1]) for v in vs for _ in range(16)]
            outcomes = {}
            lock = threading.Lock()

            def act(kind):
                rng = random.Random(r * 10 + len(kind))
                for v, x in rng.sample(handles, len(handles)):
                    try:
                        if kind == "complete":
                            res = h.complete(x, 1)
                        elif kind == "take":
                            res = v.take(x)
                        elif kind == "cancel":
                            res = v.cancel(x).name
                        elif kind == "teardown":
                            if rng.random() < 0.05:
                                h.teardown(v)
                            continue
                        else:
                            res = len(v.wait([x]))
                    except AbiError as e:
                        res = e.code.name
                    with lock:
                        outcomes.setdefault((x.slot, x.generation), []).append((kind, res))

            ts = [threading.Thread(target=act, args=(k,)) for k in ("complete", "take", "cancel", "wait", "teardown")]
            [t.start() for t in ts]
            [t.join() for t in ts]
            for key, evs in outcomes.items():
                pub = [res for k, res in evs if k == "complete" and res == "published"]
                took = [res for k, res in evs if k == "take" and res == 1]
                cancelled = [res for k, res in evs if k == "cancel" and res in ("PROPAGATED", "COMPLETED_BEFORE_CANCEL")]
                self.assertLessEqual(len(pub), 1)
                self.assertLessEqual(len(took), 1)
                self.assertLessEqual(len(took) + len(cancelled), 1)
                if took:
                    self.assertEqual(len(pub), 1)
            for v in vs:
                if v.state != "torn_down":
                    v.cancel_all()
            e = h.explain()["process"]
            self.assertEqual((e["live"], e["memory_bytes"]), (0, 0))
        COUNTS["race_rounds"] = rounds


class TestLostWakeup(unittest.TestCase):
    def test_subscribe_publication_race(self):
        n = 3000 * SCALE
        h = AsyncHost(Limits(instance=64, tombstones=64))
        v = h.register("i", tenant="t", workload="w")
        missed = 0
        for i in range(n):
            _, x = v.call()
            fired = threading.Event()
            t = threading.Thread(target=h.complete, args=(x, i))
            if i % 2:
                t.start()
                v.subscribe([x], lambda s: fired.set())
            else:
                v.subscribe([x], lambda s: fired.set())
                t.start()
            t.join()
            if not fired.wait(1):
                missed += 1
            v.take(x)
        COUNTS["lost_wakeup_iterations"] = n
        self.assertEqual(missed, 0)
        self.assertEqual(v.waiters, 0)

    def test_blocking_wait_publication_race(self):
        n = 500 * SCALE
        h = AsyncHost()
        v = h.register("i", tenant="t", workload="w")
        for i in range(n):
            _, x = v.call()
            t = threading.Thread(target=h.complete, args=(x, i))
            t.start()
            self.assertEqual(v.wait_blocking([x], 2_000_000_000), [x])
            t.join()
            v.take(x)
        COUNTS["blocking_wait_iterations"] = n


class TestSoakOverload(unittest.TestCase):
    def test_soak_bounded_memory(self):
        cycles = 20000 * SCALE
        h = AsyncHost(Limits(instance=32, tombstones=256))
        v = h.register("i", tenant="t", workload="w")
        rng = random.Random(3)
        tracemalloc.start()
        snap0 = None
        for i in range(cycles):
            _, x = v.call(idempotency_key=f"k{i}")
            r = rng.random()
            if r < 0.5:
                h.complete(x, b"p" * 32)
                v.take(x)
            elif r < 0.8:
                v.cancel(x)
            else:
                h.complete(x, b"q")
                v.cancel(x)
            if i == cycles // 2:  # after bounded rings (events, histogram windows) have filled
                snap0 = tracemalloc.take_snapshot()
        snap1 = tracemalloc.take_snapshot()
        tracemalloc.stop()
        growth = sum(s.size_diff for s in snap1.compare_to(snap0, "filename"))
        e = h.explain()["process"]
        COUNTS["soak_cycles"] = cycles
        COUNTS["soak_heap_growth_bytes"] = growth
        self.assertEqual((e["live"], e["memory_bytes"]), (0, 0))
        self.assertEqual(e["tombstones"], 256)
        self.assertLess(growth, 256 * 1024)
        self.assertLess(sum(len(q) for q in h._ready.values()), 2 * 32 + 64 + 1)

    def test_overload_and_recovery(self):
        h = AsyncHost(Limits(instance=16, workload=64, tenant=64, process=32, tenant_share=0.5))
        a = h.register("a", tenant="t1", workload="w1")
        b = h.register("b", tenant="t2", workload="w2")
        refused = {"a": 0, "b": 0}
        held = {"a": [], "b": []}
        lat = []
        for i in range(5000 * SCALE):
            for name, v in (("a", a), ("b", b)):
                t = time.perf_counter_ns()
                try:
                    held[name].append(v.call()[1])
                except AbiError:
                    refused[name] += 1
                lat.append(time.perf_counter_ns() - t)
            if i % 3 == 0:
                for name, v in (("a", a), ("b", b)):
                    if held[name]:
                        v.cancel(held[name].pop(0))
        lat.sort()
        COUNTS["overload_ops"] = len(lat)
        COUNTS["overload_p99_ns"] = lat[int(.99 * len(lat))]
        self.assertGreater(refused["a"], 0)
        self.assertLess(abs(len(held["a"]) - len(held["b"])), 2)  # fairness under sustained exhaustion
        a.cancel_all(); b.cancel_all()
        self.assertEqual(len([a.call() for _ in range(16)]), 16)


class TestFaultInjection(unittest.TestCase):
    def test_rng_failure_midstream(self):
        state = {"fail": False}
        import secrets

        def src(n):
            if state["fail"]:
                raise OSError
            return secrets.token_bytes(n)

        h = AsyncHost(token_source=src)
        v = h.register("i", tenant="t", workload="w")
        _, x = v.call()
        state["fail"] = True
        with self.assertRaises(AbiError):
            v.call()
        state["fail"] = False
        h.complete(x, 1)
        self.assertEqual(v.take(x), 1)
        invariants(self, h)

    def test_clock_failure_does_not_corrupt(self):
        state = {"fail": False}

        def clk():
            if state["fail"]:
                raise OSError("clock")
            return time.monotonic_ns()

        h = AsyncHost(clock=clk)
        v = h.register("i", tenant="t", workload="w")
        _, x = v.call()
        state["fail"] = True
        with self.assertRaises(AbiError):
            v.call(timeout_ns=5)
        with self.assertRaises(AbiError):
            h.complete(x, 1)   # publication needs a timestamp; refused atomically
        state["fail"] = False
        self.assertEqual(v.wait([x]), [])
        h.complete(x, 2)
        self.assertEqual(v.take(x), 2)
        invariants(self, h)

    def test_callback_faults_contained(self):
        h = AsyncHost()
        v = h.register("i", tenant="t", workload="w")
        h.on_ready.append(lambda *a: None)
        _, x = v.call()
        v.subscribe([x], lambda s: 1 / 0)
        h.complete(x, 1)
        self.assertEqual(v.take(x), 1)
        self.assertEqual(h.release_errors, 1)

    def test_producer_death_mid_publication(self):
        """A producer that raises during payload sizing leaves the row PENDING."""
        h = AsyncHost()
        v = h.register("i", tenant="t", workload="w")
        _, x = v.call()
        with self.assertRaises(AbiError):
            h.complete(x, object(), payload_bytes=-1)
        self.assertEqual(v.wait([x]), [])
        h.complete(x, "ok")
        self.assertEqual(v.take(x), "ok")

    def test_scheduler_stall_does_not_lose_readiness(self):
        from inv15_new_asynchronous_abi.adapters import SchedulerAdapter
        h = AsyncHost()
        v = h.register("i", tenant="t", workload="w")
        s = SchedulerAdapter(h, lambda view: None)
        xs = [v.call()[1] for _ in range(10)]
        for x in xs:
            h.complete(x, 0)
        time.sleep(0.01)  # scheduler never ran
        self.assertEqual(len(v.wait(xs)), 10)
        self.assertEqual(s.runnable(), ["i"])


@classmethod
def _dump(cls):
    import json
    out = os.environ.get("INV15_COUNTS")
    if out:
        with open(out, "w") as f:
            json.dump(COUNTS, f, indent=1, sort_keys=True)


unittest.TestCase.tearDownClass = _dump

if __name__ == "__main__":
    unittest.main()
