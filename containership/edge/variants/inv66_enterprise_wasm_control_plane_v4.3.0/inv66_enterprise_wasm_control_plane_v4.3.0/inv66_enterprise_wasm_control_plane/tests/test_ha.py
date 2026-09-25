"""Leader lease, fencing and multi-process races (MC-039 / MC-058)."""
from __future__ import annotations

import multiprocessing as mp
import os
import sys
import tempfile
import unittest

from support import ANCHOR_KEY, Harness, request
from inv66_enterprise_wasm_control_plane.errors import ControlPlaneError
from inv66_enterprise_wasm_control_plane.store import JournalStore


class LeaseTest(unittest.TestCase):
    def test_second_node_cannot_write_until_lease_expires_then_old_leader_is_fenced(self):
        h = Harness(node="a")
        h.svc.admit(h.tok(), request(rid="1"))
        with self.assertRaises(ControlPlaneError) as cm:
            JournalStore(h.path, "b", anchor_key=ANCHOR_KEY, clock=h.clock, fsync=False).acquire()
        self.assertEqual(cm.exception.error.code, "NOT_LEADER")
        h.clock.t += 60                                    # a stalls (GC pause / partition)
        sb = JournalStore(h.path, "b", anchor_key=ANCHOR_KEY, clock=h.clock, fsync=False)
        epoch_b = sb.acquire()
        self.assertGreater(epoch_b, h.svc.store.epoch)
        self.assertFalse(h.svc.is_leader())
        with self.assertRaises(ControlPlaneError) as cm:  # stale leader wakes up and tries to admit
            h.svc.admit(h.tok(), request(rid="2"))
        self.assertEqual(cm.exception.error.code, "NOT_LEADER")
        with self.assertRaises(ControlPlaneError):
            h.svc.store.append({"kind": "maintenance", "ts": 0})
        self.assertFalse(h.svc.heartbeat())
        sb.append({"kind": "maintenance", "ts": 1})
        self.assertEqual(sb.records()[-1]["epoch"], epoch_b)
        h.close()


def _worker(path, node, n, q):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from inv66_enterprise_wasm_control_plane.store import JournalStore as JS
    from inv66_enterprise_wasm_control_plane.errors import ControlPlaneError as E
    ok = 0
    for i in range(n):
        try:
            s = JS(path, node, anchor_key=b"a" * 32, lease_ttl_s=0.05, fsync=False)
            s.acquire()
            s.append({"kind": "maintenance", "ts": 0, "node": node, "i": i})
            s.release()
            ok += 1
        except E:
            pass
    q.put(ok)


class MultiProcessRaceTest(unittest.TestCase):
    def test_contending_processes_never_fork_the_chain(self):
        path = tempfile.mkdtemp()
        q = mp.Queue()
        procs = [mp.Process(target=_worker, args=(path, f"p{i}", 25, q)) for i in range(4)]
        for p in procs:
            p.start()
        for p in procs:
            p.join(60)
        wins = sum(q.get() for _ in procs)
        s = JournalStore(path, "checker", anchor_key=ANCHOR_KEY, fsync=False)
        ok, detail = s.verify_all()
        self.assertTrue(ok, detail)
        self.assertEqual(len(s.records()), wins)
        seqs = [r["sequence"] for r in s.records()]
        self.assertEqual(seqs, list(range(1, wins + 1)))


if __name__ == "__main__":
    unittest.main()
