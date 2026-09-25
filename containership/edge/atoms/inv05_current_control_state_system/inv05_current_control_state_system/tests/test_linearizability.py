"""History-based linearizability checking of the engine under concurrency (MC-043)."""
from __future__ import annotations

import json
import os
import random
import threading
import unittest

from _util import tmpdir
from inv05_current_control_state_system.linearizability import INF, Operation, Recorder, check, check_key
from inv05_current_control_state_system.store import Compare, ControlStore, Delete, Put


def run_workload(store: ControlStore, rec: Recorder, clients=8, ops=60, keys=3, seed=1):
    def client(cid):
        rng = random.Random(seed * 100 + cid)
        for _ in range(ops):
            k = f"k{rng.randrange(keys)}"
            r = rng.random()
            if r < 0.35:
                op = rec.invoke(f"c{cid}", k, "read")
                kv = store.get(k)
                rec.complete(op, None if kv is None else kv.value, store.revision)
            elif r < 0.65:
                v = rng.randrange(5)
                op = rec.invoke(f"c{cid}", k, "write", v)
                res = store.txn((), [Put(k, v)])
                rec.complete(op, "ok", res.revision)
            elif r < 0.92:
                exp, new = rng.randrange(5), rng.randrange(5)
                op = rec.invoke(f"c{cid}", k, "cas", (exp, new))
                res = store.txn([Compare(k, "EXISTS", "==", True), Compare(k, "VALUE", "==", exp)], [Put(k, new)])
                rec.complete(op, res.succeeded, res.revision)
            else:
                op = rec.invoke(f"c{cid}", k, "delete")
                res = store.txn((), [Delete(k)])
                rec.complete(op, "ok", res.revision)
    ts = [threading.Thread(target=client, args=(i,)) for i in range(clients)]
    [t.start() for t in ts]
    [t.join() for t in ts]


class LinearizabilityTest(unittest.TestCase):
    def test_engine_histories_are_linearizable(self):
        for seed in range(1, 6):
            with self.subTest(seed=seed):
                rec = Recorder()
                run_workload(ControlStore(), rec, seed=seed)
                res = check(rec.history)
                if not res.ok:
                    path = os.path.join(tmpdir(), f"counterexample-{seed}.json")
                    with open(path, "w") as fh:
                        json.dump(res.counterexample, fh, indent=1, default=str)
                self.assertTrue(res.ok, res.counterexample)
                self.assertEqual(res.ops_checked, 480)

    def test_checker_rejects_a_stale_read(self):
        h = [Operation(0, "a", "k", "write", 1, "ok", 0.0, 1.0),
             Operation(1, "b", "k", "write", 2, "ok", 2.0, 3.0),
             Operation(2, "c", "k", "read", None, 1, 4.0, 5.0)]   # reads overwritten value after write 2 completed
        ok, cex, _ = check_key(h)
        self.assertFalse(ok)
        self.assertTrue(cex["unplaceable"])

    def test_checker_rejects_double_cas_winner(self):
        h = [Operation(0, "a", "k", "write", 0, "ok", 0.0, 1.0),
             Operation(1, "b", "k", "cas", (0, 1), True, 2.0, 5.0),
             Operation(2, "c", "k", "cas", (0, 2), True, 2.0, 5.0)]
        self.assertFalse(check_key(h)[0])

    def test_concurrent_ops_may_linearize_either_way(self):
        h = [Operation(0, "a", "k", "write", 1, "ok", 0.0, 10.0),
             Operation(1, "b", "k", "read", None, None, 1.0, 2.0),
             Operation(2, "c", "k", "read", None, 1, 3.0, 4.0)]
        self.assertTrue(check_key(h)[0])

    def test_indeterminate_operations(self):
        # a crashed write may or may not have taken effect
        h = [Operation(0, "a", "k", "write", 7, None, 0.0, INF),
             Operation(1, "b", "k", "read", None, 7, 1.0, 2.0)]
        self.assertTrue(check_key(h)[0])
        h2 = [Operation(0, "a", "k", "write", 7, None, 0.0, INF),
              Operation(1, "b", "k", "read", None, None, 1.0, 2.0)]
        self.assertTrue(check_key(h2)[0])

    def test_history_under_injected_crash_and_recovery(self):
        """Faults during history generation (MC-043-05): crash the durable store mid-workload,
        recover, continue; acknowledged ops + indeterminate in-flight op must be linearizable."""
        from inv05_current_control_state_system.wal import DurableStore, SimulatedCrash
        d = tmpdir()
        arm = {"n": 0}

        def fault(p):
            if p == "wal.mid_write":
                arm["n"] += 1
                if arm["n"] == 25:
                    raise SimulatedCrash(p)
        ds = DurableStore.open(d, fault=fault)
        rec = Recorder()
        store = ds.store
        rng = random.Random(3)
        for i in range(60):
            v = rng.randrange(4)
            op = rec.invoke("c", "k", "write", v)
            try:
                store.txn((), [Put("k", v)])
                rec.complete(op, "ok")
            except SimulatedCrash:
                os.close(ds.wal._fd)
                ds = DurableStore.open(d)   # op stays indeterminate (done = INF)
                store = ds.store
            r = rec.invoke("c2", "k", "read")
            kv = store.get("k")
            rec.complete(r, None if kv is None else kv.value)
        ds.close()
        self.assertTrue(check(rec.history).ok)


if __name__ == "__main__":
    unittest.main()
