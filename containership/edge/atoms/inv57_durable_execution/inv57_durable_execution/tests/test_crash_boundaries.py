"""SG-09: kill a real worker process immediately before and after every history
commit boundary, restart, and check the exact recovered state.

A three-activity workflow appends six events (seq 0..5).  For each seq and each
boundary the child process calls ``os._exit(137)``.  Expectations:

  before_commit:N  → N events durable; event N absent (transaction never committed)
  after_commit:N   → N+1 events durable

Recovery then runs the same workflow in-process with a fresh lease and must
either finish with each activity's side effect counted exactly once, or halt
with ActivityInDoubt when the tail is an unresolved ``started`` event (never a
blind re-run).
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest

from . import _path  # noqa: F401

from inv57_durable_execution.durable import ActivityInDoubt, Worker
from inv57_durable_execution.identity import WorkflowIdentity
from inv57_durable_execution.sqlite_store import CRASH_ENV, SQLiteBackend, SQLiteHistoryStore

ROOT = str(_path.ROOT)
CHILD = textwrap.dedent("""
    import sys, os
    sys.path.insert(0, {root!r})
    from inv57_durable_execution.durable import Worker
    from inv57_durable_execution.identity import WorkflowIdentity
    from inv57_durable_execution.sqlite_store import SQLiteBackend, SQLiteHistoryStore
    ident = WorkflowIdentity("t", "test", "s", "ns", "wf", "run-1")
    b = SQLiteBackend(sys.argv[1])
    store = SQLiteHistoryStore(b, ident, b.acquire(ident, "child", 30))
    def effect(n):
        with open(sys.argv[2], "a") as fh:
            fh.write(n + "\\n"); fh.flush(); os.fsync(fh.fileno())
        return n
    Worker(store).run(lambda w: [w.activity(n, lambda n=n: effect(n)) for n in ("a", "b", "c")])
    sys.exit(0)
""")


def _ident():
    return WorkflowIdentity("t", "test", "s", "ns", "wf", "run-1")


class CrashBoundaryTests(unittest.TestCase):
    def _run_child(self, db, effects, crash):
        script = CHILD.format(root=ROOT)
        env = dict(os.environ, **({CRASH_ENV: crash} if crash else {}))
        return subprocess.run([sys.executable, "-c", script, db, effects], env=env,
                              capture_output=True, text=True, timeout=60)

    def test_every_boundary(self):
        seen = 0
        for seq in range(6):
            for boundary in ("before_commit", "after_commit"):
                with self.subTest(boundary=boundary, seq=seq):
                    d = tempfile.mkdtemp()
                    db, effects = os.path.join(d, "h.db"), os.path.join(d, "effects.log")
                    proc = self._run_child(db, effects, f"{boundary}:{seq}")
                    self.assertEqual(proc.returncode, 137, proc.stderr)
                    b = SQLiteBackend(db, clock=lambda: 1e12)        # far future: child lease expired
                    durable = b.load_events(_ident().key())
                    expect = seq if boundary == "before_commit" else seq + 1
                    self.assertEqual(len(durable), expect)
                    store = SQLiteHistoryStore(b, _ident(), b.acquire(_ident(), "recovery", 60))
                    self.assertGreater(store.lease.epoch, 1)            # recovery fenced out the child

                    counts = {}

                    def effect(n):
                        counts[n] = counts.get(n, 0) + 1
                        return n
                    tail_started = bool(durable) and durable[-1].kind == "started"
                    w = Worker(store)
                    if tail_started:
                        with self.assertRaises(ActivityInDoubt):
                            w.run(lambda w: [w.activity(n, lambda n=n: effect(n)) for n in "abc"])
                        # The activity ran in the child (its started was durable and fn executed
                        # unless the crash came right after 'started'): never re-run automatically.
                        self.assertEqual(counts, {})
                    else:
                        self.assertEqual(
                            w.run(lambda w: [w.activity(n, lambda n=n: effect(n)) for n in "abc"]),
                            ["a", "b", "c"])
                        child_ran = []
                        if os.path.exists(effects):
                            with open(effects) as fh:
                                child_ran = fh.read().split()
                        completed_in_child = [e.name for e in durable if e.kind == "completed"]
                        for n in "abc":
                            total = counts.get(n, 0) + (1 if n in completed_in_child else 0)
                            self.assertEqual(total, 1, f"{n} effect count")
                        # Nothing that completed durably in the child was re-executed.
                        self.assertFalse(set(counts) & set(completed_in_child))
                        self.assertTrue(set(completed_in_child) <= set(child_ran))
                    b.close()
                    seen += 1
        self.assertEqual(seen, 12)

    def test_clean_run_has_no_crash(self):
        d = tempfile.mkdtemp()
        proc = self._run_child(os.path.join(d, "h.db"), os.path.join(d, "e.log"), None)
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
