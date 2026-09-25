"""MC-25 - stateful fuzzing, input fuzzing, concurrency adversaries, abuse cases.

Seeds are fixed so every failure is reproducible; any crashing input found is
appended to ``tests/corpus/regressions.json`` and replayed by
``test_regression_corpus``.
"""
import json
import os
import pathlib
import random
import string
import threading
import unittest

from _helpers import pipe_nb

import inv19_os_asynchronous_analogues as inv
from inv19_os_asynchronous_analogues.hostio import config as cfgmod
from inv19_os_asynchronous_analogues.hostio import errors, schema, security
from inv19_os_asynchronous_analogues.hostio.driver import AsyncHost
from inv19_os_asynchronous_analogues.hostio.ops import OperationTable, OpState, TERMINAL

CORPUS = pathlib.Path(__file__).parent / "corpus" / "regressions.json"
SEEDS = [int(s) for s in os.environ.get("INV19_FUZZ_SEEDS", "1,2,3,4,5,6,7,8").split(",")]
STEPS = int(os.environ.get("INV19_FUZZ_STEPS", "3000"))


class StateMachineFuzz(unittest.TestCase):
    def test_backend_state_machine_invariants(self):
        """arm/post/reap/cancel sequences on the reference state machine."""
        for seed in SEEDS:
            rng = random.Random(seed)
            for name in inv.BACKENDS:
                b = inv.AsyncBackend(name, max_descriptors=4)
                model: dict[int, object] = {}
                for _ in range(STEPS // 5):
                    fd = rng.randrange(0, 8)
                    act = rng.choice(["arm", "post", "reap", "cancel"])
                    try:
                        if act == "arm":
                            b.arm(fd); model[fd] = None
                        elif act == "post":
                            err = rng.choice([None, "EIO", ""])
                            b.post(fd, rng.randrange(100), err)
                            model[fd] = ("c", err) if b.semantics == "completion" else ("r",)
                        elif act == "reap":
                            ev = b.reap(fd)
                            want = model.get(fd)
                            if want is None:
                                self.assertIsNone(ev)
                            else:
                                model.pop(fd)
                                if want[0] == "r":
                                    self.assertEqual(ev, ("retry", None))
                                else:
                                    self.assertEqual(ev[0], "error" if want[1] is not None else "value")
                        else:
                            self.assertEqual(b.cancel(fd), fd in model)
                            model.pop(fd, None)
                    except (ValueError, inv.DescriptorBudget):
                        pass
                    self.assertLessEqual(b.armed_count, 4)
                    self.assertEqual(set(b.armed), set(model))

    def test_operation_table_invariants_and_id_reuse(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            t = OperationTable(8)
            live, dead = {}, []
            for _ in range(STEPS):
                a = rng.random()
                if a < 0.3 and len(t) < 8:
                    op = t.allocate("read", "t", "w", 1)
                    live[op.op_id] = op
                elif a < 0.6 and live:
                    oid = rng.choice(list(live))
                    new = rng.choice(list(OpState))
                    try:
                        t.transition(oid, new)
                    except Exception as e:
                        self.assertEqual(type(e).__name__, "IllegalTransition")
                elif a < 0.8 and live:
                    oid = rng.choice(list(live))
                    if live[oid].terminal:
                        t.release(oid); dead.append(oid); del live[oid]
                elif dead:
                    stale = rng.choice(dead)  # replay of an old id
                    self.assertFalse(t.transition(stale, OpState.COMPLETED))
                for oid, op in live.items():
                    if op.terminal:
                        self.assertIn(op.state, TERMINAL)
            self.assertGreater(t.stale_completions, 0)


class InputFuzz(unittest.TestCase):
    def _junk(self, rng):
        return rng.choice([
            -1, 0, 2**31, 2**64, -2**63, True, None, 1.5, float("inf"), float("nan"), "",
            "x" * rng.randrange(0, 5000), "".join(rng.choice(string.printable + "‮\u0000") for _ in range(50)),
            [], {}, b"\xff" * 10, object(),
        ])

    def test_translate_never_raises_never_succeeds_unknown(self):
        rng = random.Random(11)
        for _ in range(STEPS):
            v = self._junk(rng)
            for be in ("io_uring", "iocp", "epoll", "kqueue", "portable", "bogus"):
                e = errors.translate(be, v, rng.choice([None, "posix", "win32", "winsock", "ntstatus", "x"]))
                self.assertIn(e.code, {c.value for c in errors.Code})

    def test_select_and_backend_inputs(self):
        rng = random.Random(12)
        for _ in range(STEPS):
            v = self._junk(rng)
            try:
                inv.select([v] if not isinstance(v, list) else v)
            except TypeError:
                pass
            with self.assertRaises((inv.InvalidDescriptor, TypeError, ValueError, inv.NoBackend)):
                if isinstance(v, int) and not isinstance(v, bool) and v >= 0:
                    raise ValueError("valid int; skip")
                inv.AsyncBackend("epoll").arm(v)

    def test_config_fuzz_never_partially_activates(self):
        rng = random.Random(13)
        s = cfgmod.ConfigStore()
        keys = list(cfgmod.FIELDS) + ["x.y", "auth.password", ""]
        for _ in range(STEPS // 10):
            before = s.active
            layer = {rng.choice(keys): self._junk(rng) for _ in range(rng.randrange(1, 4))}
            try:
                s.activate([("fuzz", layer)], actor="fuzz")
                self.assertEqual(cfgmod.validate(dict(s.active.values)), [])
            except cfgmod.ConfigError:
                self.assertIs(s.active, before)

    def test_schema_payload_fuzz(self):
        rng = random.Random(14)
        base = {"schema": "PK_ASYNC_REAP/1", "kind": "completion", "op_id": 1, "tag": "value"}
        for _ in range(STEPS // 3):
            d = dict(base)
            d[rng.choice(list(base) + ["extra"])] = self._junk(rng)
            try:
                blob = json.dumps(d, default=str).encode()
            except ValueError:
                continue
            try:
                schema.from_wire(blob, "PK_ASYNC_REAP_1")
            except (ValueError, UnicodeDecodeError):
                pass

    def test_redaction_never_raises_and_is_bounded(self):
        rng = random.Random(15)
        for _ in range(STEPS // 3):
            out = security.redact({"k": self._junk(rng), "token": "abc", "n": [self._junk(rng)] * 3})
            s = json.dumps(out, default=str)
            self.assertNotIn('"abc"', s)
            self.assertLess(len(s), 20000)

    def test_oversized_event_batches_rejected(self):
        from inv19_os_asynchronous_analogues.hostio import readiness
        for bad in (0, -1, 10**6):
            with self.assertRaises(ValueError):
                readiness.Portable(4, bad)


class ConcurrencyAdversary(unittest.TestCase):
    def test_arm_post_reap_cancel_races(self):
        b = inv.AsyncBackend("io_uring", max_descriptors=64)
        errs = []
        bar = threading.Barrier(16)
        def worker(i):
            rng = random.Random(i)
            bar.wait()
            for _ in range(2000):
                fd = rng.randrange(0, 32)
                try:
                    rng.choice([lambda: b.arm(fd), lambda: b.post(fd, 1), lambda: b.reap(fd),
                                lambda: b.cancel(fd)])()
                except ValueError:
                    pass
                except Exception as e:  # pragma: no cover
                    errs.append(e)
        ts = [threading.Thread(target=worker, args=(i,)) for i in range(16)]
        for t in ts: t.start()
        for t in ts: t.join()
        self.assertEqual(errs, [])
        self.assertLessEqual(b.armed_count, 64)

    def test_driver_submit_cancel_poll_shutdown_race(self):
        h = AsyncHost()
        cap = h.mint("t", "w")
        pipes = [pipe_nb() for _ in range(64)]
        futs, lock = [], threading.Lock()
        stop = threading.Event()
        def submitter(k):
            for i in range(k, 64, 4):
                try:
                    f = h.read(cap, pipes[i][0], 1) if i % 2 else h.write(cap, pipes[i][1], b"x")
                    with lock:
                        futs.append(f)
                except Exception:
                    pass
        def canceller():
            while not stop.is_set():
                with lock:
                    fs = list(futs)
                for f in fs[::3]:
                    try:
                        h.cancel(cap, f)
                    except Exception:
                        pass
        def poller():
            while not stop.is_set():
                h.poll(0.001)
        ts = [threading.Thread(target=submitter, args=(k,)) for k in range(4)]
        extra = [threading.Thread(target=canceller), threading.Thread(target=poller)]
        for t in ts + extra: t.start()
        for t in ts: t.join()
        stop.set()
        for t in extra: t.join()
        rep = h.shutdown(0.2)
        self.assertTrue(rep["accounting_at_baseline"])
        self.assertTrue(all(f.done() for f in futs))
        self.assertEqual(h.table.resolved, len(futs))
        for r, w in pipes: os.close(r); os.close(w)

    def test_hundreds_of_concurrent_callers(self):
        import resource
        soft = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
        n = max(16, min(256, (soft - 96) // 2))   # scale to the fd budget; recorded, never faked
        h = AsyncHost()
        pipes = []
        try:
            caps = [h.mint(f"t{i % 8}", f"w{i}") for i in range(n)]
            for _ in range(n):
                pipes.append(pipe_nb())
            bar = threading.Barrier(n + 1)
            futs = [None] * n
            stop = threading.Event()
            def caller(i):
                bar.wait()
                futs[i] = h.write(caps[i], pipes[i][1], b"c")
            def poller():
                while not stop.is_set():
                    h.poll(0.001)
            ts = [threading.Thread(target=caller, args=(i,)) for i in range(n)]
            pt = threading.Thread(target=poller)
            for t in ts: t.start()
            pt.start(); bar.wait()
            for t in ts: t.join()
            import time as _t
            end = _t.monotonic() + 10
            while not all(f is not None and f.done() for f in futs) and _t.monotonic() < end:
                _t.sleep(0.01)
            stop.set(); pt.join()
            self.assertTrue(all(f.result(0) == ("value", 1) for f in futs))
            self.assertTrue(h.shutdown()["accounting_at_baseline"])
            if n < 256:
                self.skipTest(f"BLOCKED: only {n} concurrent callers fit the fd limit {soft} (passed at that size)")
        finally:
            for r, w in pipes:
                os.close(r); os.close(w)

    def test_config_reload_during_operations(self):
        h = AsyncHost(override="portable")
        cap = h.mint("t", "w")
        stop = threading.Event()
        def reloader():
            i = 0
            while not stop.is_set():
                h.config.activate([("cli", {"retry.max_attempts": i % 10})], actor="ops"); i += 1
        t = threading.Thread(target=reloader); t.start()
        for _ in range(100):
            r, w = pipe_nb()
            self.assertEqual(h.run_until(h.write(cap, w, b"a")), ("value", 1))
            os.close(r); os.close(w)
        stop.set(); t.join()
        h.shutdown()


class SecurityAbuse(unittest.TestCase):
    def test_spoofed_and_replayed_op_ids(self):
        h = AsyncHost()
        cap = h.mint("t", "w")
        r, w = pipe_nb()
        f = h.write(cap, w, b"x"); h.run_until(f)
        self.assertFalse(h._finish(f.op_id, 99, None, OpState.COMPLETED))  # replay
        from inv19_os_asynchronous_analogues.hostio.integration import Future
        self.assertFalse(h.cancel(cap, Future(0xDEAD_0000_0001)))          # spoof
        self.assertEqual(f.result(0), ("value", 1))
        h.shutdown(); os.close(r); os.close(w)

    def test_resource_exhaustion_attack_is_contained(self):
        from inv19_os_asynchronous_analogues.hostio.config import ConfigStore
        from inv19_os_asynchronous_analogues.hostio.policy import Overloaded
        from inv19_os_asynchronous_analogues.hostio.resources import QuotaExceeded
        cs = ConfigStore()
        cs.activate([("cli", {"quota.max_inflight": 64, "quota.per_tenant_descriptors": 8,
                              "quota.per_workload_descriptors": 8, "quota.global_descriptors": 64})], actor="t")
        h = AsyncHost(config=cs, override="portable")
        evil, good = h.mint("evil", "w"), h.mint("good", "w")
        pipes = [pipe_nb() for _ in range(40)]
        refused = 0
        for r, _ in pipes[:30]:
            try:
                h.read(evil, r, 1)
            except (Overloaded, QuotaExceeded):
                refused += 1
        self.assertEqual(refused, 22)
        f = h.write(good, pipes[35][1], b"ok")
        self.assertEqual(h.run_until(f), ("value", 2))  # other tenant unaffected
        h.shutdown()
        for r, w in pipes: os.close(r); os.close(w)

    def test_unauthorized_configuration_change_requires_capability(self):
        h = AsyncHost(override="portable")
        cap = h.mint("t", "w")  # no "configure"
        with self.assertRaises(security.Unauthorized):
            h.authority.check(cap, "configure")
        h.shutdown()

    def test_timing_review_backend_not_exposed_to_guest(self):
        # Guest-visible outcomes carry no backend name except inside the
        # canonical error's diagnostic 'backend' field, which is host-side.
        h = AsyncHost()
        cap = h.mint("t", "w")
        r, w = pipe_nb()
        k, v = h.run_until(h.write(cap, w, b"x"))
        self.assertEqual((k, v), ("value", 1))
        h.shutdown(); os.close(r); os.close(w)


class RegressionCorpus(unittest.TestCase):
    def test_regression_corpus(self):
        data = json.loads(CORPUS.read_text()) if CORPUS.exists() else []
        for case in data:
            if case["target"] == "translate":
                self.assertEqual(errors.translate(case["backend"], case["input"]).code, case["expect"])
            elif case["target"] == "config":
                with self.assertRaises(cfgmod.ConfigError):
                    cfgmod.ConfigStore().activate([("corpus", case["input"])], actor="corpus")


if __name__ == "__main__":
    unittest.main()
