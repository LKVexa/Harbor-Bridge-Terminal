"""Randomised fault schedules with safety assertions (MC-044-03/04/05)."""
from __future__ import annotations

import os
import random
import shutil
import time
import unittest

from _util import tmpdir
from inv05_current_control_state_system.errors import StateError
from inv05_current_control_state_system.wal import DurableStore, SimulatedCrash

POINTS = ["wal.before_write", "wal.mid_write", "wal.before_fsync", "wal.after_fsync", "snap.before_rename",
          "snap.after_rename"]


class RandomScheduleTest(unittest.TestCase):
    def test_random_crash_schedule_preserves_acknowledged_state(self):
        for seed in range(8):
            with self.subTest(seed=seed):
                rng = random.Random(seed)
                d = tmpdir()
                acked: dict[str, int] = {}
                pending: tuple[str, int] | None = None
                crash_at = {rng.randrange(5, 150) for _ in range(4)}
                counter = {"n": 0}

                def fault(p):
                    counter["n"] += 1
                    if counter["n"] in crash_at and p in POINTS:
                        raise SimulatedCrash(p)
                ds = DurableStore.open(d, fault=fault)
                recoveries, detect = 0, []
                for i in range(200):
                    k, v = f"k{rng.randrange(8)}", i
                    try:
                        if rng.random() < 0.05:
                            ds.checkpoint()
                        pending = (k, v)
                        ds.store.put(k, v)
                        acked[k] = v
                        pending = None
                    except SimulatedCrash:
                        try:
                            os.close(ds.wal._fd)
                        except OSError:
                            pass
                        t0 = time.perf_counter()
                        ds = DurableStore.open(d, fault=fault)
                        detect.append(time.perf_counter() - t0)
                        recoveries += 1
                        if pending:
                            got = ds.store.get(pending[0])
                            if got and got.value == pending[1]:
                                acked[pending[0]] = pending[1]  # write reached disk: now authoritative
                        pending = None
                    for kk, vv in acked.items():
                        self.assertEqual(ds.store.get(kk).value, vv)
                self.assertEqual(ds.store.check_invariants(), [])
                self.assertLess(max(detect or [0]), 2.0)  # recovery time bound (MC-044-04)
                ds.close()
                shutil.rmtree(d, ignore_errors=True)

    def test_fail_closed_under_persistent_io_errors(self):
        d = tmpdir()
        ds = DurableStore.open(d, fault=lambda p: (_ for _ in ()).throw(OSError(5, "EIO")) if p == "wal.before_fsync" else None)
        with self.assertRaises(StateError):
            ds.store.put("k", 1)
        for _ in range(3):
            with self.assertRaises(StateError):
                ds.store.put("k", 2)
        self.assertTrue(ds.store.failed)
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
