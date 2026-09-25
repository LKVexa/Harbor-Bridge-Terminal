"""MC-04/05: fencing, leases, stale-owner recovery, corruption, identity."""

import json
import os
import tempfile
import unittest

from tests._boot import mod

own = mod("ownership")
ob = mod("ownership.base")
posix = mod("ownership.posix")
tel = mod("telemetry")


class Clock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


class Live:
    """Fake liveness: pids in ``alive`` are alive with the given start identity."""

    def __init__(self):
        self.alive = {os.getpid(): "s0"}
        self.boot = "b0"

    def pid_alive(self, pid):
        return pid in self.alive

    def start_identity(self, pid):
        return self.alive.get(pid)

    def boot_id(self):
        return self.boot


def providers(clock, live, sink=None):
    t = tel.Telemetry(sink) if sink else None
    yield own.MemoryClaimProvider(clock=clock, liveness=live, host="h", telemetry=t)
    yield posix.PosixClaimProvider(tempfile.mkdtemp(), clock=clock, liveness=live, host="h", telemetry=t)


class OwnershipTest(unittest.TestCase):
    def each(self, fn):
        for i in range(2):
            p = list(providers(Clock(), Live()))[i]
            with self.subTest(provider=p.name):
                fn(p, p.clock, p.liveness)

    def test_exclusive_and_token_authority(self):
        def t(p, clock, live):
            c = p.acquire("vmm-a")
            self.assertEqual(c.generation, 1)
            self.assertNotIn(c.token, repr(c))
            with self.assertRaises(own.ClaimConflict):
                p.acquire("vmm-a")  # same display name != authority
            forged = ob.Claim(c.resource, c.claim_id, c.generation, "forged", holder="vmm-a")
            with self.assertRaises(own.StaleToken):
                p.release(forged)
            p.release(c)
            c2 = p.acquire("vmm-b")
            self.assertEqual(c2.generation, 2)
            with self.assertRaises(own.FencingRejected):
                p.release(c)  # old generation cannot release newer owner
            with self.assertRaises(own.FencingRejected):
                p.validate(c)
            self.assertEqual(p.validate(c2), 2)

        self.each(t)

    def test_lease_expiry_takeover_and_fencing(self):
        def t(p, clock, live):
            c1 = p.acquire("a", lease_s=10)
            clock.t += 5
            c1 = p.renew(c1)
            clock.t += 11  # owner paused beyond lease
            with self.assertRaises(own.LeaseLost):
                p.renew(c1)
            c2 = p.acquire("b")
            self.assertEqual(c2.generation, c1.generation + 1)
            with self.assertRaises(own.FencingRejected):  # old owner resumes
                p.validate(c1)
            st = p.status()
            self.assertEqual(st["history"][-1]["ended"], "lease_expired")
            self.assertNotIn("token_sha256", json.dumps(st))

        self.each(t)

    def test_dead_owner_pid_reuse_and_reboot(self):
        def t(p, clock, live):
            live.alive[4242] = "s1"
            rec_pid = os.getpid
            os.getpid = lambda: 4242
            try:
                c = p.acquire("dead", lease_s=3600)
            finally:
                os.getpid = rec_pid
            with self.assertRaises(own.ClaimConflict):
                p.acquire("x")
            live.alive[4242] = "s2"  # PID reused by another process
            c2 = p.acquire("x")
            self.assertEqual(p.status()["history"][-1]["ended"], "pid_reused")
            live.boot = "b1"  # reboot invalidates the epoch
            c3 = p.acquire("y")
            self.assertEqual(c3.generation, c.generation + 2)
            del live.alive[os.getpid()]  # owner process gone
            c4 = p.acquire("z")
            self.assertEqual(p.status()["history"][-1]["ended"], "owner_dead")
            self.assertGreater(c4.generation, c3.generation)
            del c2

        self.each(t)

    def test_validation(self):
        def t(p, clock, live):
            for bad in ("", " ", None):
                with self.assertRaises(ValueError):
                    p.acquire(bad)
            for res in ("", "../x", ".hidden", "a/b", "x" * 65):
                with self.assertRaises(ValueError):
                    p.acquire("h", resource=res)
            for ls in (0, -1, 3601, True, float("nan")):
                with self.assertRaises(ValueError):
                    p.acquire("h", lease_s=ls)

        self.each(t)


class PosixDurabilityTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.clock, self.live = Clock(), Live()
        self.p = posix.PosixClaimProvider(self.d, clock=self.clock, liveness=self.live, host="h")

    def test_state_dir_permissions_and_symlink_refused(self):
        self.assertEqual(os.stat(self.d).st_mode & 0o077, 0)
        link = self.d + "-link"
        os.symlink(self.d, link)
        with self.assertRaises(own.OwnershipCorrupt):
            posix.PosixClaimProvider(link)
        loose = tempfile.mkdtemp()
        os.chmod(loose, 0o777)
        with self.assertRaises(own.OwnershipCorrupt):
            posix.PosixClaimProvider(loose)

    def test_corruption_fails_closed_then_repair_preserves_generation(self):
        c = self.p.acquire("a")
        path = os.path.join(self.d, "hw-virt.json")
        with open(path, "w") as fh:
            fh.write('{"schema": "PK_VIRT_OWNERSHIP/1", "resou')  # partial write
        with self.assertRaises(own.OwnershipCorrupt):
            self.p.acquire("b")
        self.assertEqual(self.p.status()["state"], "corrupt")
        floor = self.p.repair()
        c2 = self.p.acquire("b")
        self.assertGreater(c2.generation, c.generation)
        self.assertGreaterEqual(c2.generation, floor)

    def test_impossible_records_rejected(self):
        c = self.p.acquire("a")
        path = os.path.join(self.d, "hw-virt.json")
        with open(path) as fh:
            rec = json.load(fh)
        for mutate in (
            lambda r: r.update(generation=-1),
            lambda r: r.update(generation=True),
            lambda r: r.update(acquired_at=self.clock.t + 10_000),
            lambda r: r.update(lease_expires_at=r["acquired_at"] - 1),
            lambda r: r.update(token_sha256="x"),
            lambda r: r.update(schema="PK_VIRT_OWNERSHIP/9"),
        ):
            r = dict(rec)
            mutate(r)
            with open(path, "w") as fh:
                json.dump(r, fh)
            with self.assertRaises(own.OwnershipCorrupt):
                self.p.validate(c)

    def test_symlinked_record_not_followed(self):
        target = os.path.join(tempfile.mkdtemp(), "evil.json")
        with open(target, "w") as fh:
            fh.write("{}")
        os.symlink(target, os.path.join(self.d, "hw-virt.json"))
        with self.assertRaises(own.OwnershipCorrupt):
            self.p.acquire("a")

    def test_read_only_storage_fails_without_split_brain(self):
        c = self.p.acquire("a")
        self.p.release(c)
        os.chmod(self.d, 0o500)
        try:
            if os.geteuid() == 0:
                self.skipTest("root ignores directory permissions")
            with self.assertRaises(OSError):
                self.p.acquire("b")
        finally:
            os.chmod(self.d, 0o700)
        self.assertEqual(self.p.status()["state"], "released")

    def test_token_hash_only_on_disk(self):
        c = self.p.acquire("a")
        with open(os.path.join(self.d, "hw-virt.json")) as fh:
            blob = fh.read()
        self.assertNotIn(c.token, blob)
        self.assertEqual(os.stat(os.path.join(self.d, "hw-virt.json")).st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
