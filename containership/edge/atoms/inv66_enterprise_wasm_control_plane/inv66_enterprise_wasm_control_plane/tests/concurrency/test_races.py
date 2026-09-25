"""Concurrency and multi-process race suite (MC-058; C055, C058, C086)."""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from tests.support import EcpError, Estate, FakeClock, PKG_DIR
from inv66_enterprise_wasm_control_plane.production.journal import Journal
from inv66_enterprise_wasm_control_plane.production.replication import FencedJournal, LeaseManager


def _writer(root: str, node: str, n: int, out: "mp.Queue") -> None:
    sys.path.insert(0, str(PKG_DIR.parent))
    from inv66_enterprise_wasm_control_plane.production.journal import Journal as J
    from inv66_enterprise_wasm_control_plane.production.replication import FencedJournal as F, LeaseManager as L
    from inv66_enterprise_wasm_control_plane.production.errors import EcpError as E
    lease = L(Path(root), node, ttl_s=0.05)
    j = F(J(Path(root) / "journal", fsync=False), lease)
    ok = refused = 0
    for i in range(n):
        lease.acquire()
        try:
            j.append("race.w", {"node": node, "i": i})
            ok += 1
        except E:
            refused += 1
    out.put((node, ok, refused))


class RaceTest(unittest.TestCase):
    def test_threads_admit_concurrently_chain_valid(self):
        e = Estate(fsync=False)
        tok = e.token("ops", ttl=3600)
        errs = []

        def go(i):
            try:
                e.service.admit(e.request(f"svc{i}"), tok)
            except Exception as x:  # noqa: BLE001
                errs.append(x)
        ts = [threading.Thread(target=go, args=(i,)) for i in range(64)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(errs, [])
        self.assertEqual(len(e.service.inventory), 64)
        self.assertEqual(e.service.journal.verify()["result"], "INTACT")

    def test_idempotent_duplicates_under_race_yield_one_decision(self):
        e = Estate(fsync=False)
        req = e.request("api", key="dup-1")
        tok = e.token("ops", ttl=3600)
        out = []
        ts = [threading.Thread(target=lambda: out.append(e.service.admit(dict(req), tok))) for _ in range(20)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len({d["decision_id"] for d in out}), 1)
        self.assertEqual(sum(not d["idempotent_replay"] for d in out), 1)
        self.assertEqual(len(e.service.deployer.received), 1)

    def test_multiprocess_fenced_writers_keep_one_chain(self):
        root = tempfile.mkdtemp(prefix="inv66-mp-")
        ctx = mp.get_context("spawn")
        q = ctx.Queue()
        ps = [ctx.Process(target=_writer, args=(root, f"node{i}", 60, q)) for i in range(3)]
        [p.start() for p in ps]
        [p.join(60) for p in ps]
        results = [q.get(timeout=5) for _ in ps]
        total_ok = sum(r[1] for r in results)
        j = Journal(Path(root) / "journal", fsync=False)
        v = j.verify()
        self.assertEqual(v["result"], "INTACT")
        self.assertEqual(v["records"], total_ok)
        self.assertGreater(total_ok, 0)
        # epochs never go backwards along the chain
        epochs = [r["body"]["_epoch"] for r in j.records()]
        self.assertEqual(epochs, sorted(epochs))

    def test_stale_leader_is_fenced(self):
        clk = FakeClock()
        root = Path(tempfile.mkdtemp(prefix="inv66-lease-"))
        a = LeaseManager(root, "a", ttl_s=10, clock=clk)
        b = LeaseManager(root, "b", ttl_s=10, clock=clk)
        ja = FencedJournal(Journal(root / "journal", fsync=False), a)
        jb = FencedJournal(Journal(root / "journal", fsync=False), b)
        self.assertTrue(a.acquire())
        self.assertFalse(b.acquire())
        ja.append("x", {"by": "a"})
        clk.advance(11)                      # a pauses past its lease (GC pause / partition)
        self.assertTrue(b.acquire())
        self.assertGreater(b.epoch, a.epoch)
        jb.append("x", {"by": "b"})
        with self.assertRaises(EcpError) as cm:  # a wakes up and tries to write: fenced
            ja.append("x", {"by": "a-stale"})
        self.assertEqual(cm.exception.code, "ECP_NOT_LEADER")
        self.assertEqual([r["body"]["by"] for r in Journal(root / "journal", fsync=False).records()], ["a", "b"])
        self.assertEqual(a.status()["role"], "follower")

    def test_two_unleased_journal_handles_cannot_fork_the_chain(self):
        root = Path(tempfile.mkdtemp(prefix="inv66-fork-"))
        j1, j2 = Journal(root, fsync=False), Journal(root, fsync=False)
        for i in range(10):
            (j1 if i % 3 else j2).append("x", {"i": i})
        v = Journal(root, fsync=False).verify()
        self.assertEqual((v["result"], v["records"]), ("INTACT", 10))

    def test_config_activation_race_one_winner(self):
        e = Estate(fsync=False)
        cur = e.service.config.active.generation
        gens = []
        for site in ("s1", "s2", "s3", "s4"):
            g = e.service.config.stage(e.config(site=site), author="a", source_repo="g", source_rev=site)
            e.service.config.approve(g, "b"); e.service.config.approve(g, "c")
            gens.append(g)
        wins, losses = [], []

        def go(g):
            try:
                e.service.config.activate(g, activated_by="b", expected_active=cur)
                wins.append(g)
            except EcpError as x:
                losses.append(x.code)
        ts = [threading.Thread(target=go, args=(g,)) for g in gens]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(wins), 1)
        self.assertEqual(losses, ["ECP_CONFIG_CONFLICT"] * 3)


if __name__ == "__main__":
    unittest.main()
