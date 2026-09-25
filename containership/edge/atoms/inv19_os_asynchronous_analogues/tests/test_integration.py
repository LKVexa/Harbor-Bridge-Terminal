"""MC-08/09/10/19/23 - adjacent-layer integration, parity, recovery, failover."""
import os
import socket
import threading
import time
import unittest

from _helpers import AVAILABLE, pipe_nb

from inv19_os_asynchronous_analogues.hostio import integration as ig
from inv19_os_asynchronous_analogues.hostio.driver import AsyncHost, Health
from inv19_os_asynchronous_analogues.hostio.errors import Code, canonical
from inv19_os_asynchronous_analogues.hostio.native_base import Interest
from inv19_os_asynchronous_analogues.hostio.policy import Overloaded

BACKENDS = [b for b in ("io_uring", "epoll", "kqueue", "portable") if b in AVAILABLE]


def scenario(h):
    """Guest op -> backend -> future. Returns the component-visible outcomes."""
    cap = h.mint("t", "w")
    out = []
    r, w = pipe_nb()
    out.append(h.run_until(h.write(cap, w, b"hello"))[0])
    out.append(h.run_until(h.read(cap, r, 16)))
    out.append(h.run_until(h.read(cap, r, 16, timeout=0.05))[1].code)
    os.close(w)
    out.append(h.run_until(h.read(cap, r, 16)))
    os.close(r)
    a, b = socket.socketpair(); a.setblocking(False)
    b.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, b"\1\0\0\0\0\0\0\0"); b.close()
    k, e = h.run_until(h.write(cap, a.fileno(), b"x"))
    out.append((k, e.code in ("BROKEN_PIPE", "CONNECTION_RESET")))
    a.close()
    return out


class ParityTest(unittest.TestCase):
    def test_identical_component_outcomes_on_every_available_backend(self):
        results = {}
        for b in BACKENDS:
            h = AsyncHost(override=b)
            self.assertEqual(h.name, b)
            results[b] = scenario(h)
            self.assertTrue(h.shutdown()["accounting_at_baseline"])
        self.assertGreaterEqual(len(results), 2)
        first = next(iter(results.values()))
        self.assertEqual(first, ["value", ("value", b"hello"), "TIMED_OUT", ("value", b""), ("error", True)])
        for b, r in results.items():
            self.assertEqual(r, first, b)


class FutureTest(unittest.TestCase):
    def test_exactly_once(self):
        f = ig.Future(1)
        self.assertTrue(f.resolve_value(3))
        self.assertFalse(f.resolve_error(canonical(Code.IO_ERROR)))
        self.assertFalse(f.cancel())
        self.assertEqual((f.result(0), f.duplicate_resolutions), (("value", 3), 2))

    def test_unmapped_error_quarantined_not_swallowed(self):
        f = ig.Future(1)
        f.resolve_error("EWHAT")
        self.assertEqual(f.result(0)[1].code, "UNKNOWN_HOST_ERROR")

    def test_race_many_resolvers(self):
        for _ in range(50):
            f = ig.Future(1)
            wins = []
            bar = threading.Barrier(8)
            def go(i):
                bar.wait()
                if (f.resolve_value(i) if i % 2 else f.cancel("race")):
                    wins.append(i)
            ts = [threading.Thread(target=go, args=(i,)) for i in range(8)]
            for t in ts: t.start()
            for t in ts: t.join()
            self.assertEqual(len(wins), 1)

    def test_cancel_after_native_completion_loses(self):
        h = AsyncHost()
        cap = h.mint("t", "w")
        r, w = pipe_nb()
        f = h.write(cap, w, b"x")
        h.run_until(f)
        self.assertFalse(h.cancel(cap, f))
        self.assertEqual(f.result(0)[0], "value")
        h.shutdown(); os.close(r); os.close(w)

    def test_cancel_before_completion(self):
        for b in BACKENDS:
            h = AsyncHost(override=b)
            cap = h.mint("t", "w")
            r, w = pipe_nb()
            f = h.read(cap, r, 4)
            self.assertTrue(h.cancel(cap, f))
            os.write(w, b"late")
            for _ in range(10):
                h.poll(0.01)
            self.assertEqual(f.state, ig.FutureState.CANCELLED)
            self.assertEqual(f.duplicate_resolutions, 0)
            self.assertTrue(h.shutdown()["accounting_at_baseline"])
            os.close(r); os.close(w)

    def test_shutdown_with_pending_futures(self):
        h = AsyncHost()
        cap = h.mint("t", "w")
        pipes = [pipe_nb() for _ in range(5)]
        fs = [h.read(cap, r, 4) for r, _ in pipes]
        rep = h.shutdown(0.05)
        self.assertEqual(rep["cancelled_at_shutdown"], 5)
        self.assertTrue(rep["accounting_at_baseline"])
        self.assertTrue(all(f.cancel_cause == "SHUTDOWN" for f in fs))
        for r, w in pipes: os.close(r); os.close(w)

    def test_high_concurrency_exactly_once(self):
        h = AsyncHost()
        cap = h.mint("t", "w")
        pipes = [pipe_nb() for _ in range(64)]
        fs = [h.write(cap, w, b"z") for _, w in pipes]
        end = time.monotonic() + 5
        while not all(f.done() for f in fs) and time.monotonic() < end:
            h.poll(0.01)
        self.assertTrue(all(f.result(0) == ("value", 1) for f in fs))
        self.assertEqual(sum(f.duplicate_resolutions for f in fs), 0)
        h.shutdown()
        for r, w in pipes: os.close(r); os.close(w)


class StreamCreditTest(unittest.TestCase):
    def test_readiness_to_credit_coalesces_and_is_bounded(self):
        pool = ig.CreditPool(2)
        s1, s2, s3 = ig.CreditStream(1, 1, pool), ig.CreditStream(2, 1, pool), ig.CreditStream(3, 1, pool)
        self.assertTrue(s1.grant("read"))
        self.assertFalse(s1.grant("read"))  # repeated level-trigger: coalesced
        self.assertEqual(s1.coalesced, 1)
        self.assertTrue(s2.grant("read"))
        self.assertFalse(s3.grant("read"))  # pool exhausted -> backpressure
        s1.consume("read")
        self.assertTrue(s3.grant("read"))
        with self.assertRaises(ig.CreditExhausted):
            s1.consume("read")

    def test_real_stream_readiness_credit_then_eagain(self):
        for b in [x for x in BACKENDS if x != "io_uring"]:
            h = AsyncHost(override=b)
            cap = h.mint("t", "w")
            r, w = pipe_nb()
            s = h.open_stream(cap, r)
            h.backend.register(r, Interest.READ)
            os.write(w, b"abc")
            for ev in h.backend.wait(0.2):
                h.feed_readiness(ev)
            self.assertEqual(s.outstanding("read"), 1)
            s.consume("read")
            self.assertEqual(h.rio.read(r, 2), ("value", b"ab"))  # partial read
            for ev in h.backend.wait(0.2):
                h.feed_readiness(ev)      # still readable -> new credit
            s.consume("read")
            self.assertEqual(h.rio.read(r, 2), ("value", b"c"))
            self.assertEqual(h.rio.read(r, 2), ("retry", None))  # credit was not proof of data
            h.backend.unregister(r)
            h.close_stream(r)
            self.assertTrue(h.shutdown()["accounting_at_baseline"])
            os.close(r); os.close(w)

    def test_close_returns_credit_and_error_stops_grants(self):
        pool = ig.CreditPool(1)
        s = ig.CreditStream(1, 1, pool)
        s.grant("read")
        s.close(canonical(Code.CONNECTION_RESET))
        self.assertEqual(pool.used, 0)
        self.assertFalse(s.grant("read"))

    def test_multi_stream_fairness(self):
        pool = ig.CreditPool(4)
        streams = [ig.CreditStream(i, 1, pool) for i in range(8)]
        granted = {i: 0 for i in range(8)}
        for rnd in range(40):
            for s in streams[rnd % 8:] + streams[: rnd % 8]:
                if s.grant("read"):
                    granted[s.stream_id] += 1
                    s.consume("read")
        self.assertEqual(len(set(granted.values())), 1)


class WaitableSetTest(unittest.TestCase):
    def test_no_lost_wakeup_under_race(self):
        ws = ig.WaitableSet(16)
        ws.add(1)
        for _ in range(200):
            got = []
            t = threading.Thread(target=lambda: got.extend(ws.wait(2.0)))
            t.start()
            ws.notify(1)
            t.join(3)
            self.assertEqual(got, [1])

    def test_coalesce_capacity_invalid_bounded(self):
        ws = ig.WaitableSet(2)
        ws.add(1); ws.add(2)
        with self.assertRaises(ig.WaitableSetFull):
            ws.add(3)
        for bad in (-1, 2**32, True):
            with self.assertRaises(ValueError):
                ws.add(bad)
        for _ in range(100):
            ws.notify(1)
        ws.notify(2); ws.notify(99)
        self.assertEqual(ws.coalesced, 99)
        self.assertEqual(ws.wait(0, max_items=1), [1])
        self.assertEqual(ws.wait(0), [2])
        ws.notify(1); ws.remove(1)
        self.assertEqual(ws.wait(0.01), [])

    def test_protocol_conformance(self):
        self.assertIsInstance(ig.WaitableSet(), ig.WaitableSetLike)
        self.assertIsInstance(ig.Future(1), ig.FutureLike)
        self.assertIsInstance(ig.CreditStream(1), ig.StreamSink)

    def test_authoritative_binding_reported(self):
        st = ig.bind_authoritative()
        self.assertEqual(set(st), {"INV-17", "INV-18", "INV-15", "INV-13", "SCH-01"})


class RecoveryTest(unittest.TestCase):
    def test_stall_detection(self):
        h = AsyncHost(override="portable")
        h.config.activate([("cli", {"health.stall_s": 0.05})], actor="t")
        cap = h.mint("t", "w")
        r, w = pipe_nb()
        h.read(cap, r, 4)
        time.sleep(0.1)
        h.poll(0)
        self.assertEqual(h.health, Health.DEGRADED)
        h.shutdown(); os.close(r); os.close(w)

    def test_recovery_fails_inflight_exactly_once_then_failover(self):
        h = AsyncHost()
        first = h.name
        h.config.activate([("cli", {"health.max_recoveries": 1})], actor="t")
        cap = h.mint("t", "w")
        r, w = pipe_nb()
        f = h.read(cap, r, 4)
        rep = h.recover("injected-stall")
        self.assertEqual(rep["failed_ops"], 1)
        self.assertEqual(f.cancel_cause, "BACKEND_RECOVERY")
        self.assertEqual(h.name, first)          # reinitialised, same backend
        rep = h.recover("injected-stall-2")      # exceeds bound -> quarantine + failover
        if first != "portable":
            self.assertIn(first, h.quarantined)
            self.assertNotEqual(h.name, first)
            self.assertEqual(h.failovers[-1]["from"], first)
        f2 = h.write(cap, w, b"ok")
        self.assertEqual(h.run_until(f2), ("value", 2))
        self.assertEqual(f.duplicate_resolutions, 0)
        self.assertTrue(h.shutdown()["accounting_at_baseline"])
        os.close(r); os.close(w)

    def test_event_loss_simulation_never_loses_the_operation(self):
        for b in [x for x in BACKENDS if x != "io_uring"]:
            h = AsyncHost(override=b)
            cap = h.mint("t", "w")
            r, w = pipe_nb()
            f = h.read(cap, r, 4)
            os.write(w, b"data")
            real = h.backend.wait
            h.backend.wait = lambda timeout=0.0: []      # drop one batch of events
            h.poll(0.01)
            h.backend.wait = real
            self.assertEqual(h.run_until(f), ("value", b"data"))  # level-triggered: re-reported
            f2 = h.read(cap, r, 4, timeout=0.05)
            h.backend.wait = lambda timeout=0.0: []      # permanent loss -> bounded by deadline
            end = time.monotonic() + 1
            while not f2.done() and time.monotonic() < end:
                h.poll(0.01)
            h.backend.wait = real
            self.assertEqual(f2.result(0)[1].code, "TIMED_OUT")
            self.assertTrue(h.shutdown()["accounting_at_baseline"])
            os.close(r); os.close(w)

    def test_buffer_bytes_are_accounted(self):
        from inv19_os_asynchronous_analogues.hostio.config import ConfigStore
        from inv19_os_asynchronous_analogues.hostio.resources import QuotaExceeded
        cs = ConfigStore()
        cs.activate([("cli", {"quota.buffer_bytes_per_workload": 8192, "quota.buffer_bytes_per_tenant": 8192,
                              "quota.buffer_bytes_global": 1 << 20})], actor="t")
        h = AsyncHost(config=cs, override="portable")
        cap = h.mint("t", "w")
        r, w = pipe_nb()
        f = h.read(cap, r, 8192)
        self.assertEqual(h.accountant.used("io_buffer_bytes"), 8192)
        r2, w2 = pipe_nb()
        with self.assertRaises(QuotaExceeded):
            h.read(cap, r2, 1)
        h.cancel(cap, f)
        self.assertTrue(h.shutdown()["accounting_at_baseline"])
        for x in (r, w, r2, w2): os.close(x)

    def test_descriptor_exhaustion_at_startup_is_reason_coded(self):
        import resource
        from inv19_os_asynchronous_analogues.hostio.native_base import BackendUnavailable
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        held = []
        try:
            resource.setrlimit(resource.RLIMIT_NOFILE, (min(soft, 128), hard))
            try:
                while True:
                    held.append(os.open(os.devnull, os.O_RDONLY))
            except OSError:
                pass
            with self.assertRaises(BackendUnavailable) as cm:
                AsyncHost()
            self.assertEqual(cm.exception.reason, "NO_USABLE_BACKEND")
            self.assertIn("portable=PROBE_FAILED:RESOURCE_EXHAUSTED", cm.exception.detail)
        finally:
            for fd in held:
                os.close(fd)
            resource.setrlimit(resource.RLIMIT_NOFILE, (soft, hard))

    def test_backend_crash_during_poll(self):
        h = AsyncHost(override="portable")
        h.backend.close()
        h.poll(0)
        self.assertEqual(h.health, Health.UNHEALTHY)
        h.recover("crashed")
        self.assertEqual(h.health, Health.HEALTHY)
        h.shutdown()

    def test_admin_quarantine_and_portable_protected(self):
        h = AsyncHost()
        if h.name != "portable":
            old = h.name
            h.quarantine(old)
            self.assertNotEqual(h.name, old)
        with self.assertRaises(ValueError):
            h.quarantine("portable")
        h.shutdown()

    def test_admission_stops_during_migration(self):
        h = AsyncHost(override="portable")
        h.admitting = False
        with self.assertRaises(Overloaded):
            h.read(h.mint("t", "w"), 0, 4)
        h.admitting = True
        h.shutdown()

    def test_open_failure_falls_back_with_reason(self):
        from inv19_os_asynchronous_analogues.hostio import driver as drv
        from inv19_os_asynchronous_analogues.hostio.native_base import BackendUnavailable
        real = drv._make_backend
        def flaky(name, cfg):
            if name != "portable":
                raise BackendUnavailable(name, "INJECTED_INIT_FAILURE")
            return real(name, cfg)
        drv._make_backend = flaky
        try:
            h = AsyncHost()
        finally:
            drv._make_backend = real
        self.assertEqual(h.name, "portable")
        self.assertTrue(h.selection.fallback)
        self.assertIn("INJECTED_INIT_FAILURE", h.decisions.explain() + str(h.decisions.decisions))
        h.shutdown()


class OverloadTest(unittest.TestCase):
    def test_quota_refusal_is_explicit_and_state_unchanged(self):
        from inv19_os_asynchronous_analogues.hostio.config import ConfigStore
        cs = ConfigStore()
        cs.activate([("cli", {"quota.max_inflight": 4, "quota.per_tenant_descriptors": 2,
                              "quota.per_workload_descriptors": 2, "quota.global_descriptors": 8})], actor="t")
        h = AsyncHost(config=cs, override="portable")
        cap = h.mint("t", "w")
        pipes = [pipe_nb() for _ in range(3)]
        h.read(cap, pipes[0][0], 1); h.read(cap, pipes[1][0], 1)
        with self.assertRaises(Overloaded) as cm:
            h.read(cap, pipes[2][0], 1)
        self.assertEqual(cm.exception.reason, "OVERLOAD_TENANT")
        self.assertEqual(len(h._pending), 2)
        h.shutdown()
        for r, w in pipes: os.close(r); os.close(w)


if __name__ == "__main__":
    unittest.main()
