"""Self-contained tests for the INV-57 durable replay engine (stdlib only)."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import threading
import unittest

from . import _path  # noqa: F401

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inv57_durable_execution.durable import (  # noqa: E402
    ActivityInDoubt,
    ConcurrentRun,
    Crash,
    HistoryCorruption,
    HistoryLimitExceeded,
    InMemoryHistoryStore,
    NonDeterminism,
    RecordedActivityFailure,
    UnsupportedResult,
    Worker,
)


class DurableReplayTest(unittest.TestCase):
    def test_completed_activities_replay_without_duplicate_effects(self):
        charges: list[int] = []
        crash_once = {"armed": True}

        def workflow(worker: Worker):
            worker.activity("reserve", lambda: "r-1")
            worker.activity("charge", lambda: charges.append(1) or "c-1")
            if crash_once["armed"]:
                crash_once["armed"] = False
                raise Crash()
            return worker.activity("ship", lambda: "s-1")

        worker = Worker()
        with self.assertRaises(Crash):
            worker.run(workflow)
        self.assertEqual(worker.run(workflow), "s-1")
        self.assertEqual(charges, [1])
        self.assertEqual(worker.executed, ["reserve", "charge", "ship"])
        self.assertEqual(worker.history, [("reserve", "r-1"), ("charge", "c-1"), ("ship", "s-1")])

    def test_changed_activity_is_rejected_before_new_effect(self):
        worker = Worker()
        worker.run(lambda w: [w.activity("a", lambda: 1), w.activity("b", lambda: 2)])
        effects: list[str] = []
        with self.assertRaises(NonDeterminism):
            worker.run(
                lambda w: [
                    w.activity("a", lambda: effects.append("a") or 10),
                    w.activity("c", lambda: effects.append("c") or 30),
                ]
            )
        self.assertEqual(effects, [])
        self.assertEqual(worker.executed, ["a", "b"])

    def test_shorter_workflow_is_rejected(self):
        worker = Worker()
        worker.run(lambda w: [w.activity("a", lambda: 1), w.activity("b", lambda: 2)])
        with self.assertRaises(NonDeterminism):
            worker.run(lambda w: w.activity("a", lambda: 1))

    def test_fingerprint_change_is_rejected(self):
        worker = Worker()
        worker.run(lambda w: w.activity("compile", lambda: "ok", fingerprint="input:v1"))
        with self.assertRaises(NonDeterminism):
            worker.run(lambda w: w.activity("compile", lambda: "new", fingerprint="input:v2"))

    def test_crash_inside_activity_becomes_in_doubt_not_duplicate(self):
        worker = Worker()
        effects: list[str] = []

        def abrupt():
            effects.append("charged")
            raise Crash()

        with self.assertRaises(Crash):
            worker.run(lambda w: w.activity("charge", abrupt))
        self.assertEqual([e.kind for e in worker.history_store.events], ["started"])

        with self.assertRaises(ActivityInDoubt):
            worker.run(lambda w: w.activity("charge", lambda: effects.append("DUP") or "c-1"))
        self.assertEqual(effects, ["charged"])

        worker.resolve_in_doubt("step-0:charge", "receipt-1")
        self.assertEqual(
            worker.run(lambda w: w.activity("charge", lambda: effects.append("DUP") or "x")),
            "receipt-1",
        )
        self.assertEqual(effects, ["charged"])

    def test_regular_activity_failure_is_recorded_without_message(self):
        worker = Worker()

        def fail():
            raise ValueError("secret-token-should-not-enter-history")

        with self.assertRaisesRegex(ValueError, "secret-token"):
            worker.run(lambda w: w.activity("validate", fail))
        serialized = worker.history_store.to_json()
        self.assertNotIn("secret-token", serialized)
        self.assertEqual([e.kind for e in worker.history_store.events], ["started", "failed"])
        with self.assertRaises(RecordedActivityFailure):
            worker.run(lambda w: w.activity("validate", lambda: "must-not-run"))

    def test_capacity_is_checked_before_user_code_runs(self):
        worker = Worker(max_history_events=2)
        worker.run(lambda w: w.activity("one", lambda: 1))
        effects: list[str] = []
        with self.assertRaises(HistoryLimitExceeded):
            worker.run(
                lambda w: [
                    w.activity("one", lambda: 1),
                    w.activity("two", lambda: effects.append("ran") or 2),
                ]
            )
        self.assertEqual(effects, [])

    def test_json_round_trip_and_hash_chain_tamper_detection(self):
        worker = Worker()
        worker.run(lambda w: w.activity("a", lambda: {"x": [1, 2], "blob": b"abc"}))
        text = worker.history_store.to_json()
        restored = InMemoryHistoryStore.from_json(text)
        replay = Worker(restored)
        self.assertEqual(
            replay.run(lambda w: w.activity("a", lambda: "must-not-run")),
            {"blob": b"abc", "x": [1, 2]},
        )

        raw = json.loads(text)
        raw[1]["digest"] = "0" * 64
        with self.assertRaises(HistoryCorruption):
            InMemoryHistoryStore.from_json(json.dumps(raw))

    def test_legacy_completed_history_is_migrated(self):
        worker = Worker([("a", 1), ("b", 2)])
        self.assertEqual(
            worker.run(lambda w: [w.activity("a", lambda: 10), w.activity("b", lambda: 20)]),
            [1, 2],
        )
        self.assertEqual(worker.executed, [])
        self.assertEqual(len(worker.history_store.events), 4)

    def test_unsupported_result_leaves_activity_in_doubt(self):
        worker = Worker()
        with self.assertRaises(UnsupportedResult):
            worker.run(lambda w: w.activity("bad", lambda: object()))
        self.assertEqual([e.kind for e in worker.history_store.events], ["started"])
        with self.assertRaises(ActivityInDoubt):
            worker.run(lambda w: w.activity("bad", lambda: "must-not-run"))

    def test_concurrent_run_on_same_worker_is_refused(self):
        worker = Worker()
        entered = threading.Event()
        release = threading.Event()
        errors: list[BaseException] = []

        def slow_workflow(w: Worker):
            entered.set()
            release.wait(2)
            return w.activity("a", lambda: 1)

        def first_run():
            try:
                worker.run(slow_workflow)
            except BaseException as exc:  # pragma: no cover - diagnostic capture
                errors.append(exc)

        thread = threading.Thread(target=first_run)
        thread.start()
        self.assertTrue(entered.wait(1))
        try:
            with self.assertRaises(ConcurrentRun):
                worker.run(lambda w: None)
        finally:
            release.set()
            thread.join(2)
        self.assertFalse(errors)

    def test_core_semantics_survive_optimized_mode(self):
        code = (
            "from inv57_durable_execution import Worker, NonDeterminism; "
            "w=Worker(); w.run(lambda x:[x.activity('a',lambda:1),x.activity('b',lambda:2)]); "
            "\ntry: w.run(lambda x:x.activity('a',lambda:9))\n"
            "except NonDeterminism: print('PASS')\n"
            "else: raise SystemExit(3)"
        )
        proc = subprocess.run(
            [sys.executable, "-O", "-c", code],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "PASS")


if __name__ == "__main__":
    unittest.main()
