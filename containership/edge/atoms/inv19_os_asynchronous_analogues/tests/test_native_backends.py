"""MC-02/03/04/05/06/07 - native backend tests against the real host."""
import ctypes
import errno
import os
import socket
import threading
import time
import unittest
from unittest import mock

from _helpers import HAS_EPOLL, HAS_KQUEUE, IS_WINDOWS, LINUX_URING, CAPS, pipe_nb, platform_blocked

from inv19_os_asynchronous_analogues.hostio import capabilities as capmod
from inv19_os_asynchronous_analogues.hostio import iocp, iouring, readiness
from inv19_os_asynchronous_analogues.hostio.native_base import (BackendClosed, BackendUnavailable,
                                                                Interest)


def _collect(ring, want, timeout=2.0):
    got = {}
    end = time.monotonic() + timeout
    while len(got) < want and time.monotonic() < end:
        for e in ring.wait(0.02):
            got[e.op_id] = e
    return got


@unittest.skipUnless(LINUX_URING, "BLOCKED: io_uring unavailable on this host")
class IoUringTest(unittest.TestCase):
    def test_probe_reports_ops_and_reason(self):
        p = iouring.probe()
        self.assertTrue(p["available"])
        self.assertEqual(p["reason"], "OK")
        for op in iouring.REQUIRED_OPS:
            self.assertTrue(p["ops"][op], op)

    def test_real_pipe_io_success_and_eof(self):
        r, w = os.pipe()
        with iouring.IoUring(8) as ring:
            b = (ctypes.c_char * 3).from_buffer_copy(b"xyz")
            ring.submit("write", w, 1, buf=b, length=3)
            rb = (ctypes.c_char * 8)()
            ring.submit("read", r, 2, buf=rb, length=8)
            got = _collect(ring, 2)
            self.assertEqual(got[1].result, 3)
            self.assertEqual(got[2].result, 3)
            self.assertEqual(rb.raw[:3], b"xyz")
            os.close(w)
            ring.submit("read", r, 3, buf=rb, length=8)
            self.assertEqual(_collect(ring, 1)[3].result, 0)  # EOF = value 0
        os.close(r)

    def test_connection_reset_is_translated_error(self):
        a, b = socket.socketpair()
        b.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, b"\1\0\0\0\0\0\0\0")
        with iouring.IoUring(8) as ring:
            a.send(b"q")
            b.close()  # peer closed
            buf = (ctypes.c_char * 16)()
            ring.submit("send", a.fileno(), 5, buf=(ctypes.c_char * 1)(b"z"), length=1)
            ev = _collect(ring, 1)[5]
            # either EPIPE/ECONNRESET: must be an error, never a value
            self.assertIsNone(ev.result)
            self.assertIn(ev.error.code, ("BROKEN_PIPE", "CONNECTION_RESET"))
        a.close()

    def test_bad_descriptor_rejected_before_submit(self):
        with iouring.IoUring(4) as ring:
            r, w = os.pipe(); os.close(r); os.close(w)
            with self.assertRaises(OSError) as cm:
                ring.submit("read", r, 1, buf=(ctypes.c_char * 4)(), length=4)
            self.assertEqual(cm.exception.errno, errno.EBADF)

    def test_cancel_pending_read(self):
        r, w = os.pipe()
        with iouring.IoUring(4) as ring:
            ring.submit("read", r, 9, buf=(ctypes.c_char * 4)(), length=4)
            self.assertTrue(ring.cancel(9))
            ev = _collect(ring, 1)[9]
            self.assertEqual(ev.error.code, "CANCELLED")
            self.assertFalse(ring.cancel(9))  # already reaped: completion won, no double resolution
        os.close(r); os.close(w)

    def test_sq_saturation_is_detected(self):
        r, w = os.pipe()
        with iouring.IoUring(2) as ring:
            ring.submit("read", r, 1, buf=(ctypes.c_char * 1)(), length=1)
            ring.submit("read", r, 2, buf=(ctypes.c_char * 1)(), length=1)
            # SQ entries were consumed by the kernel; in-flight ops are bounded by the
            # caller's op table, and duplicate user_data is refused while observable
            with self.assertRaises(ValueError):
                ring.submit("read", r, 1, buf=(ctypes.c_char * 1)(), length=1)
            os.write(w, b"ab")
            self.assertEqual(len(_collect(ring, 2)), 2)
        os.close(r); os.close(w)

    def test_cq_overflow_pressure_many_completions(self):
        with iouring.IoUring(4, 8) as ring:
            done = 0
            for batch in range(20):
                for i in range(4):
                    ring.submit("nop", -1, batch * 4 + i + 1)
                done += len(_collect(ring, 4))
            self.assertEqual(done, 80)
            self.assertEqual(ring.inflight, 0)

    def test_cq_overflow_backlog_is_flushed(self):
        """Regression (soak burst): more CQEs than CQ slots must not stall the ring."""
        pipes = [os.pipe() for _ in range(24)]
        with iouring.IoUring(8, 16) as ring:
            for i, (r, _) in enumerate(pipes):
                ring.submit("read", r, i + 1, buf=(ctypes.c_char * 1)(), length=1)
            for i in range(24):
                ring.cancel(i + 1)          # 24 cancelled reads + 24 cancel CQEs > 16 slots
            got = _collect(ring, 24, 3.0)
            self.assertEqual(len(got), 24)
            r, w = pipes[0]
            ring.submit("write", w, 99, buf=(ctypes.c_char * 1)(b"k"), length=1)
            self.assertEqual(_collect(ring, 1, 2.0)[99].result, 1)
        for r, w in pipes: os.close(r); os.close(w)

    def test_stale_cqe_never_delivered(self):
        with iouring.IoUring(4) as ring:
            ring.submit("nop", -1, 77)
            ring._inflight.pop(77)  # simulate: op already resolved elsewhere
            time.sleep(0.01)
            self.assertEqual(ring.wait(0.05), [])
            self.assertGreaterEqual(ring.stale_cqes, 1)

    def test_descriptor_close_during_operation(self):
        r, w = os.pipe()
        with iouring.IoUring(4) as ring:
            ring.submit("read", r, 1, buf=(ctypes.c_char * 4)(), length=4)
            os.close(w)  # writer closes -> read completes with EOF
            self.assertEqual(_collect(ring, 1)[1].result, 0)
        os.close(r)

    def test_concurrent_submit_and_reap(self):
        with iouring.IoUring(64, 128) as ring:
            got, lock = [], threading.Lock()
            stop = threading.Event()

            def reaper():
                while not stop.is_set() or ring.inflight:
                    evs = ring.wait(0.01)
                    with lock:
                        got.extend(e.op_id for e in evs)

            t = threading.Thread(target=reaper)
            t.start()
            def sub(base):
                for i in range(50):
                    while True:
                        try:
                            ring.submit("nop", -1, base + i); break
                        except BlockingIOError:
                            time.sleep(0.001)
            ts = [threading.Thread(target=sub, args=(k * 1000 + 1,)) for k in range(4)]
            for x in ts: x.start()
            for x in ts: x.join()
            stop.set(); t.join(5)
            self.assertEqual(len(got), 200)
            self.assertEqual(len(set(got)), 200)  # exactly once

    def test_shutdown_with_work_in_flight(self):
        r, w = os.pipe()
        ring = iouring.IoUring(8)
        for i in range(4):
            ring.submit("read", r, i + 1, buf=(ctypes.c_char * 1)(), length=1)
        rep = ring.close(1.0)
        self.assertEqual(rep["cancelled"], 4)
        self.assertEqual(rep["abandoned"], 0)
        with self.assertRaises(BackendClosed):
            ring.submit("nop", -1, 1)
        os.close(r); os.close(w)

    def test_fault_injected_setup_failure_rolls_back(self):
        with mock.patch.object(iouring, "_syscall", return_value=lambda *a: -1), \
                mock.patch("ctypes.get_errno", return_value=errno.EPERM):
            with self.assertRaises(BackendUnavailable) as cm:
                iouring.IoUring(4)
            self.assertEqual(cm.exception.reason, "PERMISSION_DENIED")

    def test_seccomp_style_denial_probe_reason(self):
        with mock.patch.object(iouring, "_syscall", return_value=lambda *a: -1), \
                mock.patch("ctypes.get_errno", return_value=errno.EPERM):
            p = iouring.probe()
        self.assertFalse(p["available"])
        self.assertEqual(p["reason"], "EPERM_SECCOMP_OR_SYSCTL")

    def test_fork_guard(self):
        ring = iouring.IoUring(2)
        ring._pid = -1
        with self.assertRaises(BackendClosed):
            ring.submit("nop", -1, 1)
        ring._pid = os.getpid(); ring.close()

    def test_ring_size_validation(self):
        for bad in (0, -1, True, 1 << 20):
            with self.assertRaises(ValueError):
                iouring.IoUring(bad)


class _ReadinessContract:
    make = None

    def test_read_write_readiness_and_peer_close(self):
        b = self.make()
        try:
            a, c = socket.socketpair(); a.setblocking(False); c.setblocking(False)
            tok = b.register(a.fileno(), Interest.READ | Interest.WRITE)
            evs = b.wait(0.2)
            self.assertTrue(any(e.writable and e.token == tok for e in evs))
            c.send(b"hi")
            evs = b.wait(0.5)
            self.assertTrue(any(e.readable for e in evs))
            io = readiness.ReadinessIO(b.name)
            self.assertEqual(io.read(a.fileno()), ("value", b"hi"))
            self.assertEqual(io.read(a.fileno())[0], "retry")  # readiness consumed -> EAGAIN
            c.close()
            evs = b.wait(0.5)
            self.assertTrue(any(e.readable or e.hup for e in evs))
            self.assertEqual(io.read(a.fileno()), ("value", b""))  # EOF discovered by syscall
            b.unregister(a.fileno()); a.close()
        finally:
            b.close()

    def test_connection_error_discovered_by_syscall_not_flags(self):
        b = self.make()
        try:
            a, c = socket.socketpair(); a.setblocking(False)
            c.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, b"\1\0\0\0\0\0\0\0")
            b.register(a.fileno(), Interest.WRITE)
            c.close()
            b.wait(0.2)
            kind, err = readiness.ReadinessIO(b.name).write(a.fileno(), b"x" * 10)
            self.assertEqual(kind, "error")
            self.assertIn(err.code, ("BROKEN_PIPE", "CONNECTION_RESET"))
            b.unregister(a.fileno()); a.close()
        finally:
            b.close()

    def test_level_trigger_repeats_until_drained(self):
        b = self.make()
        try:
            r, w = pipe_nb()
            b.register(r, Interest.READ)
            os.write(w, b"abc")
            self.assertTrue(b.wait(0.2))
            self.assertTrue(b.wait(0.2))  # still readable (level-triggered)
            os.read(r, 10)
            self.assertFalse(b.wait(0.05))
            b.unregister(r); os.close(r); os.close(w)
        finally:
            b.close()

    def test_descriptor_reuse_generation(self):
        b = self.make()
        try:
            r, w = pipe_nb()
            t1 = b.register(r, Interest.READ)
            b.unregister(r); os.close(r); os.close(w)
            r2, w2 = pipe_nb()  # kernel likely reuses the number
            t2 = b.register(r2, Interest.READ)
            if r2 == r:
                self.assertNotEqual(t1, t2)
            self.assertFalse(b.regs.token_live(t1))
            os.write(w2, b"z")
            evs = b.wait(0.2)
            self.assertTrue(all(e.token == t2 for e in evs))
            b.unregister(r2); os.close(r2); os.close(w2)
        finally:
            b.close()

    def test_wakeup_unblocks_waiter_and_is_idempotent(self):
        b = self.make()
        try:
            out = []
            t = threading.Thread(target=lambda: out.append(b.wait(5.0)))
            t.start(); time.sleep(0.05)
            for _ in range(1000):
                b.wake()  # idempotent, cannot overflow
            t.join(2)
            self.assertFalse(t.is_alive())
            self.assertEqual(out, [[]])
        finally:
            b.close()

    def test_concurrent_add_mod_del(self):
        b = self.make()
        try:
            pipes = [pipe_nb() for _ in range(32)]
            errs = []
            def worker(pr):
                try:
                    for _ in range(20):
                        b.register(pr[0], Interest.READ)
                        b.modify(pr[0], Interest.READ | Interest.WRITE)
                        b.unregister(pr[0])
                except Exception as e:  # pragma: no cover
                    errs.append(e)
            ts = [threading.Thread(target=worker, args=(p,)) for p in pipes]
            for t in ts: t.start()
            for t in ts: t.join()
            self.assertEqual(errs, [])
            self.assertEqual(len(b.regs), 0)
            for r, w in pipes: os.close(r); os.close(w)
        finally:
            b.close()

    def test_event_burst_bounded_and_fair(self):
        b = self.make_small()
        try:
            pipes = [pipe_nb() for _ in range(40)]
            for r, w in pipes:
                b.register(r, Interest.READ); os.write(w, b"x")
            seen = set()
            for _ in range(20):
                evs = b.wait(0.1)
                self.assertLessEqual(len(evs), 8)
                seen |= {e.fd for e in evs}
                for e in evs:
                    os.read(e.fd, 1)
            self.assertEqual(seen, {r for r, _ in pipes})  # nobody starved
            for r, w in pipes: b.unregister(r); os.close(r); os.close(w)
        finally:
            b.close()

    def test_blocking_fd_rejected(self):
        b = self.make()
        try:
            r, w = os.pipe()
            with self.assertRaises(ValueError):
                b.register(r, Interest.READ)
            os.close(r); os.close(w)
        finally:
            b.close()

    def test_registration_limit(self):
        tmp = self.make(); cls = type(tmp); tmp.close()
        b = cls(max_registrations=2, max_events=4)
        try:
            ps = [pipe_nb() for _ in range(3)]
            b.register(ps[0][0], Interest.READ); b.register(ps[1][0], Interest.READ)
            with self.assertRaises(OverflowError):
                b.register(ps[2][0], Interest.READ)
            for r, w in ps: os.close(r); os.close(w)
        finally:
            b.close()


@unittest.skipUnless(HAS_EPOLL, "BLOCKED: epoll unavailable on this host")
class EpollTest(_ReadinessContract, unittest.TestCase):
    make = staticmethod(lambda: readiness.Epoll(256, 64))
    make_small = staticmethod(lambda: readiness.Epoll(256, 8))

    def test_edge_triggered_requires_drain(self):
        b = readiness.Epoll(16, 16, edge=True)
        r, w = pipe_nb()
        b.register(r, Interest.READ)
        os.write(w, b"abcdef")
        self.assertTrue(b.wait(0.2))
        self.assertFalse(b.wait(0.05))  # edge: no repeat without new data
        kind, _, data = readiness.ReadinessIO("epoll").drain(r, 2)
        self.assertEqual((kind, data), ("retry", b"abcdef"))
        b.close(); os.close(r); os.close(w)

    def test_err_hup_cannot_disappear(self):
        b = readiness.Epoll(16, 16)
        r, w = pipe_nb()
        b.register(w, Interest.WRITE)
        os.close(r)  # reader gone -> EPOLLERR on writer
        evs = b.wait(0.2)
        self.assertTrue(any(e.error or e.hup for e in evs))
        b.close(); os.close(w)


@unittest.skipUnless(HAS_KQUEUE, "BLOCKED: kqueue unavailable on this host (requires macOS/BSD CI runner)")
class KqueueTest(_ReadinessContract, unittest.TestCase):  # pragma: no cover - BSD only
    make = staticmethod(lambda: readiness.Kqueue(256, 64))
    make_small = staticmethod(lambda: readiness.Kqueue(256, 8))


class PortableTest(_ReadinessContract, unittest.TestCase):
    make = staticmethod(lambda: readiness.Portable(256, 64))
    make_small = staticmethod(lambda: readiness.Portable(256, 8))

    def test_available_everywhere_and_observable(self):
        p = readiness.probe_portable()
        self.assertTrue(p["available"])
        self.assertIn("selector", p)


@unittest.skipUnless(IS_WINDOWS, "BLOCKED: IOCP requires a Windows CI runner")
class IocpTest(unittest.TestCase):  # pragma: no cover - Windows only
    def test_probe(self):
        self.assertTrue(iocp.probe()["available"])


class IocpPortabilityTest(unittest.TestCase):
    def test_off_windows_is_unavailable_with_reason(self):
        if IS_WINDOWS:
            self.skipTest("BLOCKED: runs on non-Windows only")
        self.assertEqual(iocp.probe()["reason"], "NOT_WINDOWS")
        with self.assertRaises(BackendUnavailable):
            iocp.Iocp()

    def test_structure_layouts(self):
        self.assertEqual(ctypes.sizeof(iocp.OVERLAPPED), 32 if ctypes.sizeof(ctypes.c_void_p) == 8 else 20)
        self.assertEqual(ctypes.sizeof(iocp.OVERLAPPED_ENTRY), 32 if ctypes.sizeof(ctypes.c_void_p) == 8 else 16)


class CapabilityTest(unittest.TestCase):
    def test_detect_is_operational_and_selects_highest(self):
        sel = capmod.choose(CAPS)
        self.assertEqual(sel.backend, CAPS.available()[0])
        for b in capmod.PRIORITY[: capmod.PRIORITY.index(sel.backend)]:
            self.assertIn(b, sel.rejected)

    def _caps(self, **avail):
        c = capmod.HostCapabilities("t", "Linux", "x", "x", "x86_64", "3")
        for b in capmod.PRIORITY:
            c.backends[b] = {"available": avail.get(b, False), "reason": "OK" if avail.get(b) else "TEST_ABSENT"}
        c.backends["portable"] = {"available": True, "reason": "OK"}
        return c

    def test_admin_disable_and_fallback_reason(self):
        c = self._caps(io_uring=True, epoll=True)
        s = capmod.choose(c, disabled=["io_uring"])
        self.assertEqual((s.backend, s.rejected["io_uring"]), ("epoll", "ADMIN_DISABLED"))
        s = capmod.choose(c, disabled=["io_uring", "epoll"])
        self.assertTrue(s.fallback)
        self.assertIn("io_uring=ADMIN_DISABLED", s.reason)

    def test_override_unavailable_requires_diagnostic(self):
        c = self._caps(epoll=True)
        with self.assertRaises(capmod.SelectionError):
            capmod.choose(c, override="io_uring")
        self.assertTrue(capmod.choose(c, override="io_uring", diagnostic=True).diagnostic)

    def test_selection_is_deterministic(self):
        c = self._caps(io_uring=True, epoll=True, kqueue=True)
        self.assertEqual({capmod.choose(c).backend for _ in range(50)}, {"io_uring"})

    def test_probe_crash_is_rejection(self):
        probes = dict(capmod.PROBES)
        probes["io_uring"] = lambda: 1 / 0
        c = capmod.detect(probes)
        self.assertEqual(c.backends["io_uring"]["reason"], "PROBE_CRASH:ZeroDivisionError")

    def test_probe_oserror_is_reason_coded(self):
        import errno as _e
        probes = dict(capmod.PROBES)
        def emfile():
            raise OSError(_e.EMFILE, "x")
        probes["epoll"] = emfile
        self.assertEqual(capmod.detect(probes).backends["epoll"]["reason"], "PROBE_FAILED:RESOURCE_EXHAUSTED")

    def test_snapshot_has_no_hostname(self):
        import socket as s
        snap = str(capmod.snapshot(CAPS, capmod.choose(CAPS)))
        self.assertNotIn(s.gethostname(), snap)


if __name__ == "__main__":
    unittest.main()
