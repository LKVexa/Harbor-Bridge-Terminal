"""MC-53 property/fuzz tests and MC-54 concurrency tests (seeded, deterministic, stdlib-only)."""
from __future__ import annotations

import json
import os
import random
import tempfile
import threading
import unittest

from . import _path  # noqa: F401

from inv57_durable_execution.durable import (DurableExecutionError, HistoryCorruption,
                                             InMemoryHistoryStore, NonDeterminism, Worker,
                                             _decode_value, _encode_value)
from inv57_durable_execution.errors import ConcurrentAppend, InvalidIdentity, StaleOwner
from inv57_durable_execution.identity import WorkflowIdentity
from inv57_durable_execution.sqlite_store import SQLiteBackend, SQLiteHistoryStore

SEED = int(os.environ.get("INV57_PROPERTY_SEED", "5701"))
N = int(os.environ.get("INV57_PROPERTY_CASES", "300"))


def rand_value(rng: random.Random, depth: int = 0):
    kinds = ["none", "bool", "int", "float", "str", "bytes"] + (["list", "tuple", "dict"] if depth < 3 else [])
    k = rng.choice(kinds)
    if k == "none":
        return None
    if k == "bool":
        return rng.random() < 0.5
    if k == "int":
        return rng.randint(-(2 ** 80), 2 ** 80)
    if k == "float":
        return rng.uniform(-1e300, 1e300) * rng.choice([1, 1e-300])
    if k == "str":
        return "".join(chr(rng.randint(0, 0x2FFF)) for _ in range(rng.randint(0, 12)))
    if k == "bytes":
        return bytes(rng.randint(0, 255) for _ in range(rng.randint(0, 16)))
    if k == "list":
        return [rand_value(rng, depth + 1) for _ in range(rng.randint(0, 4))]
    if k == "tuple":
        return tuple(rand_value(rng, depth + 1) for _ in range(rng.randint(0, 4)))
    return {f"k{rng.randint(0, 99)}": rand_value(rng, depth + 1) for _ in range(rng.randint(0, 4))}


class PropertyTests(unittest.TestCase):
    def test_encoding_roundtrip_is_exact_and_canonical(self):
        rng = random.Random(SEED)
        for _ in range(N):
            v = rand_value(rng)
            enc = _encode_value(v)
            self.assertEqual(_decode_value(json.loads(json.dumps(enc))), v)
            self.assertEqual(_encode_value(_decode_value(enc)), enc)

    def test_replay_equals_first_run_for_random_workflows(self):
        rng = random.Random(SEED + 1)
        for _ in range(N // 3):
            values = [rand_value(rng) for _ in range(rng.randint(1, 8))]
            wf = lambda w: [w.activity(f"a{i}", lambda v=v: v) for i, v in enumerate(values)]
            w = Worker()
            first = w.run(wf)
            again = Worker(InMemoryHistoryStore.from_json(w.history_store.to_json())).run(wf)
            self.assertEqual(first, again)

    def test_any_single_byte_mutation_of_history_is_detected_or_harmless(self):
        rng = random.Random(SEED + 2)
        w = Worker()
        w.run(lambda w: [w.activity(f"a{i}", lambda i=i: {"i": i, "s": "x" * i}) for i in range(5)])
        text = w.history_store.to_json()
        detected = 0
        for _ in range(N):
            pos = rng.randrange(len(text))
            mutated = text[:pos] + chr((ord(text[pos]) + rng.randint(1, 50)) % 127 or 65) + text[pos + 1:]
            try:
                s = InMemoryHistoryStore.from_json(mutated)
            except (HistoryCorruption, ValueError, TypeError):
                detected += 1
                continue
            # Survived parsing: it must be semantically identical (e.g. whitespace-only change).
            self.assertEqual([e.to_dict() for e in s.events],
                             [e.to_dict() for e in w.history_store.events])
        self.assertGreater(detected, N * 0.8)

    def test_identity_fuzz_never_crashes_uncontrolled(self):
        rng = random.Random(SEED + 3)
        for _ in range(N):
            s = "".join(chr(rng.randint(0, 0x7FF)) for _ in range(rng.randint(0, 140)))
            try:
                WorkflowIdentity(s, "e", "s", "n", "w", "r")
            except InvalidIdentity:
                pass

    def test_random_divergence_always_detected(self):
        rng = random.Random(SEED + 4)
        for _ in range(N // 3):
            names = [f"n{rng.randint(0, 3)}" for _ in range(rng.randint(2, 6))]
            w = Worker()
            w.run(lambda w: [w.activity(n, lambda: 1) for n in names])
            changed = list(names)
            i = rng.randrange(len(changed))
            changed[i] = changed[i] + "x"
            ran_before = len(w.executed)
            with self.assertRaises(NonDeterminism):
                w.run(lambda w: [w.activity(n, lambda: 1) for n in changed])
            self.assertEqual(len(w.executed), ran_before)


class ConcurrencyTests(unittest.TestCase):
    def test_competing_workers_single_owner_no_lost_or_duplicate_appends(self):
        db = os.path.join(tempfile.mkdtemp(), "c.db")
        ident = WorkflowIdentity("t", "test", "s", "n", "wf", "run-1")
        clock = {"t": 0.0}
        lock = threading.Lock()
        outcomes = []

        def contender(k):
            b = SQLiteBackend(db, clock=lambda: clock["t"])
            try:
                for _ in range(20):
                    try:
                        lease = b.acquire(ident, f"w{k}", 1.0)
                        store = SQLiteHistoryStore(b, ident, lease)
                        n = len(store) // 2
                        Worker(store).run(lambda w: [w.activity(f"s{i}", lambda i=i: i) for i in range(n + 1)])
                        outcomes.append("committed")
                        with lock:
                            clock["t"] += 2.0          # let the lease expire so others can take over
                    except (StaleOwner, ConcurrentAppend, DurableExecutionError):
                        outcomes.append("fenced")
            finally:
                b.close()
        ts = [threading.Thread(target=contender, args=(k,)) for k in range(4)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        b = SQLiteBackend(db)
        events = b.load_events(ident.key())
        # Chain validated by load_events; activities form an exact prefix s0..sK with no gaps/dupes.
        names = [e.name for e in events if e.kind == "completed"]
        self.assertEqual(names, [f"s{i}" for i in range(len(names))])
        self.assertIn("committed", outcomes)


if __name__ == "__main__":
    unittest.main()
