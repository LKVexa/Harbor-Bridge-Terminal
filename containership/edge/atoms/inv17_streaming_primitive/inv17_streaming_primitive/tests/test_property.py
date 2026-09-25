"""C085: property-based / fuzz tests (stdlib ``random``; seeds are reported for reproduction).

A reference model re-implements the normative state machine (spec/stream-state-machine.md)
independently; random operation sequences must produce identical outcomes and never break
the invariants. INV17_FUZZ_CASES scales the run (default 300 sequences x 60 ops).
"""
import os
import random
import unittest

from _pkg import adapters as A, configuration as K, stream as S, wire as W

CASES = int(os.environ.get("INV17_FUZZ_CASES", "300"))


class Model:
    def __init__(self, mc, mb):
        self.mc, self.mb = mc, mb
        self.credit = 0; self.buf = []; self.ended = self.rd = self.wd = self.frozen = False
        self.keys = []

    def grant(self, n):
        if isinstance(n, bool) or not isinstance(n, int) or n <= 0: return "ValueError"
        if self.rd: return "EndDropped"
        if self.ended or self.wd: return "StreamClosed"
        if self.frozen: return "StreamFrozen"
        if self.credit + n > self.mc: return "CreditLimitExceeded"
        self.credit += n; return None

    def write(self, v, key):
        if self.rd or self.wd: return "EndDropped"
        if self.ended: return "StreamClosed"
        if self.frozen: return "StreamFrozen"
        if not isinstance(v, int) or isinstance(v, bool): return "ElementTypeMismatch"
        if key is not None and key in self.keys: return False
        if self.credit <= 0: return "CreditExhausted"
        if len(self.buf) >= self.mb: return "BufferLimitExceeded"
        self.credit -= 1; self.buf.append(v)
        if key is not None: self.keys.append(key)
        return True

    def read(self):
        if self.rd: return "EndDropped"
        if self.buf: return ("v", self.buf.pop(0))
        if self.wd: return "EndDropped"
        return None if self.ended else "NOT_READY"

    def end(self):
        if self.rd or self.wd: return "EndDropped"
        self.ended = True; self.credit = 0; return None

    def drop_reader(self):
        if not self.rd: self.rd = True; self.buf.clear(); self.credit = 0

    def drop_writer(self):
        if not self.wd: self.wd = True; self.credit = 0


def outcome(fn):
    try:
        r = fn()
    except S.StreamError as e:
        return type(e).__name__
    except ValueError:
        return "ValueError"
    if r is S.NOT_READY: return "NOT_READY"
    return r


class StateMachinePropertyTest(unittest.TestCase):
    def test_random_sequences_match_reference_model(self):
        for seed in range(CASES):
            rng = random.Random(seed)
            mc, mb = rng.randint(1, 6), rng.randint(1, 6)
            s = S.Stream(int, config=S.StreamConfig(max_credit=mc, max_buffer=mb, idempotency_window=10_000))
            m = Model(mc, mb)
            for step in range(60):
                op = rng.choices(["grant", "write", "read", "end", "dr", "dw", "fz", "uf"],
                                 [5, 8, 6, 1, 0.5, 0.5, 0.5, 0.5])[0]
                ctx = f"seed={seed} step={step} op={op}"
                if op == "grant":
                    n = rng.choice([1, 2, 3, 0, -1, True, 2.0, 10])
                    self.assertEqual(outcome(lambda: s.grant(n)), m.grant(n), ctx)
                elif op == "write":
                    v = rng.choice([1, 2, 3, True, "x", 4.0, None])
                    key = rng.choice([None, None, "k1", "k2", f"u{step}"])
                    got = outcome(lambda: s.write(v, idempotency_key=key))
                    self.assertEqual(got, m.write(v, key), ctx)
                elif op == "read":
                    got = outcome(s.read)
                    exp = m.read()
                    if isinstance(exp, tuple):
                        self.assertEqual(got, exp[1], ctx)
                    else:
                        self.assertEqual(got, exp, ctx)
                elif op == "end":
                    self.assertEqual(outcome(s.end), m.end(), ctx)
                elif op == "dr":
                    s.drop_reader(); m.drop_reader()
                elif op == "dw":
                    s.drop_writer(); m.drop_writer()
                elif op == "fz":
                    s.freeze("f"); m.frozen = True
                else:
                    s.unfreeze(); m.frozen = False
                # invariants
                self.assertLessEqual(len(s.buffer), mb, ctx)
                self.assertLessEqual(s.credit, mc, ctx)
                self.assertGreaterEqual(s.credit, 0, ctx)
                self.assertEqual(list(s.buffer), m.buf, ctx)
                st = s.stats()
                self.assertEqual(st.transferred - st.reads - st.dropped_items, st.buffered, ctx)


class CreditArithmeticTest(unittest.TestCase):
    def test_grant_write_conservation(self):
        rng = random.Random(1234)
        for _ in range(CASES):
            s = S.Stream(int, config=S.StreamConfig(max_credit=1000, max_buffer=1000))
            granted = written = 0
            for _ in range(50):
                if rng.random() < 0.5:
                    n = rng.randint(1, 30)
                    try:
                        s.grant(n); granted += n
                    except S.CreditLimitExceeded:
                        pass
                else:
                    try:
                        s.write(1); written += 1
                    except S.CreditExhausted:
                        pass
            self.assertEqual(s.credit, granted - written)


class ParserFuzzTest(unittest.TestCase):
    def test_config_validator_never_crashes(self):
        rng = random.Random(99)
        atoms = [0, -1, 1, 2 ** 40, 1.5, True, None, "x", "", [], {}, {"a": 1}]
        keys = ["stream", "max_credit", "max_buffer", "tenants", "health", "overload", "environment", "zz"]
        def rand(d=0):
            if d > 2 or rng.random() < 0.4:
                return rng.choice(atoms)
            return {rng.choice(keys): rand(d + 1) for _ in range(rng.randint(0, 3))}
        for _ in range(CASES * 3):
            doc = rand()
            try:
                K.load_layers(doc if isinstance(doc, dict) else {"x": doc})
            except K.ConfigInvalid:
                pass

    def test_wire_and_codec_never_crash(self):
        rng = random.Random(7)
        codec = A.CanonicalCodec()
        for _ in range(CASES * 3):
            blob = bytes(rng.getrandbits(8) for _ in range(rng.randint(0, 24)))
            try:
                codec.lift(blob, rng.choice([int, str, bytes, float, dict]))
            except A.AdapterError:
                pass
            doc = {"interface": rng.choice(["PK_STREAM_CREDIT", "PK_STREAM_CLOSE", "X"]),
                   "version": rng.choice([1, 2, "1", None]), "stream_id": rng.choice(["s", "", "s" * 200, 5]),
                   "credit": rng.choice([1, 0, -3, "2", True]), "kind": rng.choice(["end", "x", None])}
            for k in list(doc):
                if rng.random() < 0.2:
                    del doc[k]
            s = S.Stream(int, stream_id="s")
            for fn in (W.apply_credit, W.apply_close):
                try:
                    fn(s, doc)
                except S.StreamError:
                    pass


if __name__ == "__main__":
    unittest.main()
