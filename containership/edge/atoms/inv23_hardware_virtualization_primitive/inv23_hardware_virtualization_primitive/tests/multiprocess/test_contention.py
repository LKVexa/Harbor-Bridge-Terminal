"""MC-04/05/11: real independent processes contend, crash, and are fenced (POSIX)."""

import multiprocessing as mp
import os
import signal
import sys
import tempfile
import time
import unittest

from tests._boot import PKG_DIR, mod

own = mod("ownership")
ob = mod("ownership.base")

ROUNDS = int(os.environ.get("INV23_MP_ROUNDS", "25"))
PROCS = int(os.environ.get("INV23_MP_PROCS", "12"))


def _provider(d):
    sys.path.insert(0, str(PKG_DIR.parent))
    from inv23_hardware_virtualization_primitive.ownership.posix import PosixClaimProvider

    return PosixClaimProvider(d)


def _contend(d, barrier, q, i, done):
    p = _provider(d)
    barrier.wait()
    try:
        c = p.acquire(f"vmm-{i}", lease_s=60)
        q.put(("win", i, c.generation))
        done.wait(60)  # stay alive: a dead winner is legitimately recoverable
    except Exception as exc:  # noqa: BLE001
        q.put(("lose", i, type(exc).__name__))


def _hold_forever(d, q):
    p = _provider(d)
    c = p.acquire("doomed", lease_s=3600)
    q.put((c.resource, c.claim_id, c.generation, c.token))
    time.sleep(3600)


def _graceful(d, q):
    p = _provider(d)
    c = p.acquire("polite", lease_s=3600)
    p.release(c)
    q.put(c.generation)


@unittest.skipIf(sys.platform == "win32", "POSIX provider; Windows provider runs in windows CI job")
class MultiProcessTest(unittest.TestCase):
    ctx = mp.get_context("spawn")

    def test_exactly_one_winner_per_round(self):
        for rnd in range(ROUNDS):
            d = tempfile.mkdtemp()
            barrier, q, done = self.ctx.Barrier(PROCS), self.ctx.Queue(), self.ctx.Event()
            ps = [self.ctx.Process(target=_contend, args=(d, barrier, q, i, done)) for i in range(PROCS)]
            for p in ps:
                p.start()
            res = [q.get(timeout=60) for _ in ps]
            st = _provider(d).status()
            done.set()
            for p in ps:
                p.join(30)
            wins = [r for r in res if r[0] == "win"]
            losers = {r[2] for r in res if r[0] == "lose"}
            self.assertEqual(len(wins), 1, f"round {rnd}: {res}")
            self.assertEqual(losers, {"ClaimConflict"})
            self.assertEqual((st["state"], st["holder"]), ("held", f"vmm-{wins[0][1]}"))

    def test_sigkill_owner_is_recovered_and_fenced(self):
        d, q = tempfile.mkdtemp(), self.ctx.Queue()
        child = self.ctx.Process(target=_hold_forever, args=(d, q))
        child.start()
        res, cid, gen, tok = q.get(timeout=60)
        p = _provider(d)
        with self.assertRaises(own.ClaimConflict):
            p.acquire("contender")
        os.kill(child.pid, signal.SIGKILL)
        child.join(10)
        new = p.acquire("contender")
        self.assertEqual(new.generation, gen + 1)
        self.assertEqual(p.status()["history"][-1]["ended"], "owner_dead")
        stale = ob.Claim(res, cid, gen, tok)
        with self.assertRaises(own.FencingRejected):
            p.validate(stale)
        with self.assertRaises(own.FencingRejected):
            p.release(stale)
        p.release(new)

    def test_graceful_exit_and_restart(self):
        d, q = tempfile.mkdtemp(), self.ctx.Queue()
        ch = self.ctx.Process(target=_graceful, args=(d, q))
        ch.start()
        g = q.get(timeout=60)
        ch.join(10)
        p = _provider(d)  # "service restart": fresh provider, same state
        self.assertEqual(p.status()["state"], "released")
        self.assertEqual(p.acquire("next").generation, g + 1)

    def test_lock_file_tampering(self):
        d = tempfile.mkdtemp()
        p = _provider(d)
        c = p.acquire("a")
        os.unlink(os.path.join(d, "hw-virt.lock"))  # lock target deleted between ops
        with self.assertRaises(own.ClaimConflict):
            p.acquire("b")
        with open(os.path.join(d, "hw-virt.gen"), "w") as fh:
            fh.write("banana")
        with self.assertRaises(own.OwnershipCorrupt):
            p.validate(c)


if __name__ == "__main__":
    unittest.main()
