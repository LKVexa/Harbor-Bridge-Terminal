"""Property-based and fuzz testing, stdlib only, deterministic seeds (C085, C086).

Failing seeds/inputs are appended to fixtures/fuzz_corpus.json (regression corpus) when
INV18_FUZZ_RECORD=1; the corpus is always replayed.  CI budget: bounded iteration counts.
"""
import json
import os
import random
import threading
import unittest

from _util import m, PKG_DIR

future = m("future")
errors = m("errors")
wire = m("wire")
CORPUS = PKG_DIR / "fixtures" / "fuzz_corpus.json"
ITER = int(os.environ.get("INV18_FUZZ_ITER", "400"))


def _record(kind, item):
    if os.environ.get("INV18_FUZZ_RECORD") == "1":
        data = json.loads(CORPUS.read_text())
        data.setdefault(kind, []).append(item)
        CORPUS.write_text(json.dumps(data, indent=1))


class Model:
    """Reference model of the state machine."""

    def __init__(self):
        self.state, self.taken = "PENDING", False

    def apply(self, op):
        s = self.state
        if op in ("resolve", "resolve_error", "resolve_bad"):
            if s == "CANCELLED":
                return "FUTURE_CANCELLED"
            if s != "PENDING":
                return "FUTURE_ALREADY_RESOLVED"
            if op == "resolve_bad":
                return "TYPE_MISMATCH"
            self.state = "VALUE" if op == "resolve" else "ERROR"
            return "ok"
        if op == "abandon":
            if s == "PENDING":
                self.state = "ABANDONED"; return "did"
            return "noop"
        if op == "cancel":
            if s == "PENDING" and not self.taken:
                self.state = "CANCELLED"; self.taken = True; return "did"
            return "noop"
        if op == "take":
            if self.taken:
                return "FUTURE_ALREADY_TAKEN"
            if s == "PENDING":
                return "pending"
            self.taken = True
            return {"VALUE": "ok", "ERROR": "error", "ABANDONED": "FUTURE_ABANDONED"}[s]


def _real(f, op):
    try:
        if op == "resolve":
            f.resolve(1); return "ok"
        if op == "resolve_error":
            f.resolve_error("e"); return "ok"
        if op == "resolve_bad":
            f.resolve("x"); return "ok"
        if op == "abandon":
            return "did" if f.abandon() else "noop"
        if op == "cancel":
            return "did" if f.cancel() else "noop"
        r = f.take()
        return "pending" if r is None else r[0]
    except errors.FutureError as exc:
        return exc.code
    except TypeError:
        return "TYPE_MISMATCH"


OPS = ["resolve", "resolve_error", "resolve_bad", "abandon", "cancel", "take"]


class PropertyTest(unittest.TestCase):
    def test_random_operation_sequences(self):
        """REQ: C085 C081 INV18-FR-001 INV18-FR-002 INV18-FR-009 — at most one resolver/receiver, terminal states never revert, invalid input cannot corrupt"""
        seeds = list(range(ITER)) + json.loads(CORPUS.read_text()).get("seeds", [])
        for seed in seeds:
            rng = random.Random(seed)
            f, model = future.Future(int), Model()
            seen_terminal = None
            for _ in range(rng.randint(1, 12)):
                op = rng.choice(OPS)
                got, want = _real(f, op), model.apply(op)
                if got != want:
                    _record("seeds", seed)
                self.assertEqual(got, want, f"seed={seed} op={op}")
                st = f.state
                if seen_terminal is not None:
                    self.assertEqual(st, seen_terminal, f"terminal state reverted, seed={seed}")
                if st != "PENDING":
                    seen_terminal = st

    def test_concurrent_random_ordering(self):
        """REQ: C085 C086 INV18-FR-010 INV18-FR-011"""
        for seed in range(max(20, ITER // 10)):
            rng = random.Random(seed)
            f = future.Future(int)
            ops = [rng.choice(OPS) for _ in range(rng.randint(4, 12))]
            barrier = threading.Barrier(len(ops))
            out = []
            lock = threading.Lock()
            def run(op):
                barrier.wait()
                r = _real(f, op)
                with lock:
                    out.append((op, r))
            ts = [threading.Thread(target=run, args=(o,)) for o in ops]
            [t.start() for t in ts]; [t.join() for t in ts]
            wins = [o for o, r in out if o in ("resolve", "resolve_error") and r == "ok"]
            wins += [o for o, r in out if o in ("abandon", "cancel") and r == "did"]
            self.assertLessEqual(len(wins), 1, f"seed={seed} {out}")
            consumed = [o for o, r in out if o == "take" and r in ("ok", "error", "FUTURE_ABANDONED")]
            consumed += [o for o, r in out if o == "cancel" and r == "did"]
            self.assertLessEqual(len(consumed), 1, f"seed={seed} {out}")


def _mutate(rng, b: bytes) -> bytes:
    b = bytearray(b)
    for _ in range(rng.randint(1, 6)):
        k = rng.randint(0, 4)
        if k == 0 and b:
            b[rng.randrange(len(b))] = rng.randrange(256)
        elif k == 1:
            b.insert(rng.randrange(len(b) + 1), rng.randrange(256))
        elif k == 2 and b:
            del b[rng.randrange(len(b))]
        elif k == 3:
            b += rng.choice([b"}", b"]", b'"', b"\\", b"\x00", b"1e999", b"NaN", b'"ext":{}'])
        else:
            i = rng.randrange(len(b) + 1)
            b = b[:i] + b[i:i + rng.randint(0, 20)] * 2 + b[i:]
    return bytes(b)


class FuzzTest(unittest.TestCase):
    SEEDS = [wire.encode({"schema": "PK_FUTURE/1", "future_id": "f1", "value_type": "int", "epoch": 1}),
             wire.encode({"schema": "PK_FUTURE_RESOLVE/1", "future_id": "f1", "outcome": "ok", "value": 1,
                          "epoch": 1, "idempotency_key": "k"}),
             wire.encode({"schema": "PK_FUTURE_ABANDON/1", "future_id": "f1", "epoch": 1,
                          "idempotency_key": "k", "reason": "shutdown"})]

    def test_decoder_fuzz(self):
        """REQ: C085 C050 INV18-CMP-001 — decoders never crash, only structured refusals"""
        rng = random.Random(85)
        corpus = [bytes.fromhex(h) for h in json.loads(CORPUS.read_text()).get("wire_inputs", [])]
        cases = corpus + [_mutate(rng, rng.choice(self.SEEDS)) for _ in range(ITER * 3)]
        for blob in cases:
            for sid in ("PK_FUTURE/1", "PK_FUTURE_RESOLVE/1", "PK_FUTURE_ABANDON/1"):
                try:
                    doc = wire.decode(blob, sid, max_bytes=4096)
                    self.assertEqual(wire.validate(doc, sid), [])
                except errors.Rejected as exc:
                    self.assertIn(exc.code, ("INVALID_ARGUMENT", "RESOURCE_EXHAUSTED", "INCOMPATIBLE_VERSION"))
                except Exception as exc:  # noqa: BLE001
                    _record("wire_inputs", blob.hex())
                    self.fail(f"decoder crashed with {type(exc).__name__} on {blob[:80]!r}")

    def test_error_record_fuzz(self):
        """REQ: C085 C026"""
        rng = random.Random(26)
        vals = [None, 0, -1, "", "x" * 5000, [], {}, {"schema": "PK_FUTURE_ERROR/1"}, True, 1.5, "TIMEOUT"]
        keys = ["schema", "code", "message", "details", "cause", "original_code", "zzz"]
        for _ in range(ITER * 2):
            d = {"schema": "PK_FUTURE_ERROR/1", "code": "TIMEOUT", "details": {}}
            for _ in range(rng.randint(1, 4)):
                d[rng.choice(keys)] = rng.choice(vals)
            try:
                rec = errors.ErrorRecord.from_dict(d)
                out = rec.to_dict()
                self.assertEqual(wire.validate(out, "PK_FUTURE_ERROR/1"), [])
            except ValueError:
                pass

    def test_payload_metadata_extremes(self):
        """REQ: C085 C028"""
        f = future.Future(str)
        f.resolve("")                                   # empty value is a value
        self.assertEqual(f.take(), ("ok", ""))
        g = future.Future(bytes)
        g.resolve(b"\x00" * 1_000_000)
        self.assertEqual(len(g.take()[1]), 1_000_000)
        for bad in ("\x00" * 5000, "é" * 4097):
            h = future.Future(int)
            with self.assertRaises(ValueError):
                h.resolve_error(bad)

    def test_corpus_is_well_formed(self):
        """REQ: C085"""
        data = json.loads(CORPUS.read_text())
        self.assertEqual(data["schema"], "INV18_FUZZ_CORPUS/1")
        for h in data.get("wire_inputs", []):
            bytes.fromhex(h)


if __name__ == "__main__":
    unittest.main()
