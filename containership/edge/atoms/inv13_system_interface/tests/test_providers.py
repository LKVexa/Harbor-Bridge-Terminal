"""MC-008 env/stdio/secrets, MC-009 clocks, MC-010 randomness, MC-013 async semantics."""
import asyncio, os, statistics, unittest
import _fx
from inv13_system_interface.host import stdio_env as se, clocks, randomness as rnd, aio
from inv13_system_interface.host.errors import ErrorCode, Inv13Error


class EnvStdio(unittest.TestCase):
    def test_non_inheritance(self):
        os.environ["INV13_HOST_SECRET"] = "leak-me"
        env = dict(se.build_environment({"MODE": "prod"}))
        self.assertEqual(env, {"MODE": "prod"})
        self.assertNotIn("leak-me", repr(env))

    def test_validation_and_secret_exclusion(self):
        for bad in ({"lower": "x"}, {"A": "x\0"}, {"A": se.SecretRef("db")}, {"A": "x" * 40000}):
            with self.assertRaises(Inv13Error):
                se.build_environment(bad)
        with self.assertRaises(Inv13Error):
            se.build_argv(["--pw", se.SecretRef("db")])
        with self.assertRaises(Inv13Error):
            se.build_argv(["x"] * 300)

    def test_secret_broker_and_redaction(self):
        io = se.Stdio()
        broker = se.SecretBroker(lambda n: "hunter2-" + n, {"api": frozenset({"db"})})
        val = broker.reveal("api", se.SecretRef("db"), sinks=[io.stdout, io.stderr])
        io.stdout.write(f"connecting with {val}\n".encode())
        self.assertNotIn(b"hunter2", io.stdout.getvalue())
        self.assertIn(b"[REDACTED]", io.stdout.getvalue())
        with self.assertRaises(Inv13Error):
            broker.reveal("other", se.SecretRef("db"))
        self.assertNotIn("hunter2", repr(se.SecretRef("db")))

    def test_stdin_not_granted_and_bounded_output(self):
        with self.assertRaises(Inv13Error):
            se.Stdio(b"data").read_stdin()
        io = se.Stdio(b"abc", grant_stdin=True, out_limit=4)
        self.assertEqual(io.read_stdin(2), b"ab")
        self.assertEqual(io.stdout.write(b"123456"), 4)
        with self.assertRaises(Inv13Error):
            io.stdout.write(b"7")


class Clocks(unittest.TestCase):
    def test_quantised_and_monotone(self):
        m = clocks.MonotonicClock(resolution_ns=1_000_000)
        vals = [m.now() for _ in range(2000)]
        self.assertTrue(all(v % 1_000_000 == 0 for v in vals))
        self.assertEqual(vals, sorted(vals))
        s, ns = clocks.WallClock(resolution_ns=10_000_000).now()
        self.assertEqual(ns % 10_000_000, 0)
        self.assertGreater(s, 1_700_000_000)

    def test_backwards_source_never_regresses(self):
        seq = iter([5_000_000, 3_000_000, 9_000_000])
        m = clocks.MonotonicClock(source=lambda: next(seq))
        self.assertEqual([m.now(), m.now(), m.now()], [5_000_000, 5_000_000, 9_000_000])

    def test_side_channel_resolution_floor(self):
        # a 100 ns-scale timing difference must be invisible at the default resolution
        m = clocks.MonotonicClock(resolution_ns=1_000_000)
        deltas = []
        for _ in range(200):
            a = m.now(); sum(range(50)); b = m.now()
            deltas.append(b - a)
        self.assertTrue(set(deltas) <= {0, 1_000_000})
        with self.assertRaises(Inv13Error):
            clocks.MonotonicClock(resolution_ns=10)

    def test_replay_refused_in_production(self):
        with self.assertRaises(Inv13Error):
            clocks.ReplayClock([1, 2], profile="production")
        r = clocks.ReplayClock([1, 2], profile="test")
        self.assertEqual([r.now(), r.now()], [1, 2])
        with self.assertRaises(Inv13Error):
            r.now()


class Randomness(unittest.TestCase):
    def test_csprng_output_and_bounds(self):
        p = rnd.CsprngProvider()
        a, b = p.get(32), p.get(32)
        self.assertNotEqual(a, b)
        self.assertEqual(p.get(0), b"")
        for bad in (-1, 1 << 17, True, 1.5):
            with self.assertRaises(Inv13Error):
                p.get(bad)
        # crude sanity: byte distribution of 64 KiB is not degenerate
        data = p.get(65536)
        counts = [data.count(bytes([i])) for i in range(256)]
        self.assertLess(statistics.pstdev(counts), 40)

    def test_rate_limit_backpressure(self):
        t = [0.0]
        p = rnd.CsprngProvider(bytes_per_sec=100, clock=lambda: t[0])
        p.get(100)
        with self.assertRaises(Inv13Error) as cm:
            p.get(1)
        self.assertEqual(cm.exception.code, ErrorCode.BACKPRESSURE)
        t[0] = 1.0
        p.get(100)

    def test_source_failure_is_not_masked(self):
        def boom(n): raise OSError(38, "getrandom unavailable")
        with self.assertRaises(Inv13Error) as cm:
            rnd.CsprngProvider(source=boom).get(8)
        self.assertEqual(cm.exception.code, ErrorCode.ENTROPY_UNAVAILABLE)
        with self.assertRaises(Inv13Error):
            rnd.CsprngProvider(source=lambda n: b"\0").get(8)   # short read

    def test_deterministic_provider_guarded(self):
        for profile, ack in (("production", rnd.INSECURE_ACK), ("test", "yes")):
            with self.assertRaises(Inv13Error):
                rnd.DeterministicProvider(b"s", profile=profile, ack=ack)
        d1 = rnd.DeterministicProvider(b"s", profile="test", ack=rnd.INSECURE_ACK)
        d2 = rnd.DeterministicProvider(b"s", profile="test", ack=rnd.INSECURE_ACK)
        self.assertEqual(d1.get(100), d2.get(100))


class Async(unittest.TestCase):
    def test_backpressure_bounded(self):
        s = aio.BoundedStream(capacity=2)
        s.write(b"a"); s.write(b"b")
        self.assertFalse(s.poll_writable())
        with self.assertRaises(Inv13Error) as cm:
            s.write(b"c")
        self.assertEqual(cm.exception.code, ErrorCode.BACKPRESSURE)

    def test_cancellation_propagates(self):
        async def main():
            parent = aio.CancelScope(); child = aio.CancelScope(parent)
            s = aio.BoundedStream()
            task = asyncio.ensure_future(s.read(child))
            await asyncio.sleep(0.01)
            parent.cancel()
            with self.assertRaises(Inv13Error) as cm:
                await task
            self.assertEqual(cm.exception.code, ErrorCode.CANCELLED)
            self.assertTrue(aio.CancelScope(parent).cancelled)   # late children born cancelled
        asyncio.run(main())

    def test_deadline_and_close(self):
        async def main():
            s = aio.BoundedStream()
            with self.assertRaises(Inv13Error) as cm:
                await aio.call_with_deadline(s.read(), 0.05)
            self.assertEqual(cm.exception.code, ErrorCode.TIMED_OUT)
            s.write(b"x"); s.close()
            self.assertEqual(await s.read(), b"x")
            self.assertIsNone(await s.read())
        asyncio.run(main())

    def test_retry_only_idempotent(self):
        calls = []
        async def flaky():
            calls.append(1)
            raise Inv13Error(ErrorCode.PROVIDER_UNAVAILABLE)
        async def main():
            for idem, n in ((False, 1), (True, 3)):
                calls.clear()
                with self.assertRaises(Inv13Error):
                    await aio.retry(flaky, idempotent=idem, backoff=0)
                self.assertEqual(len(calls), n)
        asyncio.run(main())


if __name__ == "__main__":
    unittest.main()
