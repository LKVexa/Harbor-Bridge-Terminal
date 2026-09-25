"""Closure #18: model-based property testing (stdlib; seeded; minimizing; sensitivity-checked).

A pure reference model predicts the outcome of every operation; the real
runtime must agree on every step.  Failing sequences are shrunk and written to
``tests/corpus/`` so they become permanent regressions (replayed first).
"""
import json
import os
import pathlib
import random
import unittest

from _util import rt, scale

CORPUS = pathlib.Path(__file__).with_name("corpus")
SEED = int(os.environ.get("INV16_PROPERTY_SEED", "16016"))
FNS = ("a", "s", "q")


class Model:
    def __init__(self, limit, qdepth, tcap):
        self.limit, self.qdepth, self.tcap = limit, qdepth, tcap
        self.next = 1
        self.live, self.queued, self.term = {}, [], {}
        self.order = []

    def _bury(self, cid, outcome):
        self.term[cid] = outcome
        self.order.append(cid)
        while len(self.order) > self.tcap:
            self.term.pop(self.order.pop(0))

    def _promote(self, fn):
        if not any(f == fn for f in self.live.values()):
            for i, (cid, f) in enumerate(self.queued):
                if f == fn:
                    self.queued.pop(i)
                    self.live[cid] = f
                    return

    def invoke(self, fn):
        busy = fn in ("s", "q") and fn in self.live.values()
        if busy and fn == "s":
            return "ReentrancyRefused"
        if busy and fn == "q":
            if sum(1 for _, f in self.queued if f == "q") >= self.qdepth:
                return "ReentrancyQueueFull"
            cid = self.next; self.next += 1
            self.queued.append((cid, fn))
            return ("queued", cid)
        if self.limit is not None and len(self.live) >= self.limit:
            return "ConcurrencyLimitReached"
        cid = self.next; self.next += 1
        self.live[cid] = fn
        return ("live", cid)

    def _missing(self, cid, op):
        if cid in self.term:
            o = self.term[cid]
            if op == "complete":
                return {"completed": "DoubleDelivery", "cancelled": "CallCancelled", "trapped": "CallTrapped"}[o]
            return "AlreadyTerminal"
        if isinstance(cid, int) and not isinstance(cid, bool) and 1 <= cid < self.next:
            return "HistoryExpired"
        return "ValueError"

    @staticmethod
    def _bad(cid):
        return isinstance(cid, bool) or not isinstance(cid, int)

    def complete(self, cid):
        if self._bad(cid):
            return "ValueError"
        if cid in self.live:
            fn = self.live.pop(cid); self._bury(cid, "completed"); self._promote(fn)
            return "ok"
        if any(c == cid for c, _ in self.queued):
            return "CallNotStarted"
        return self._missing(cid, "complete")

    def cancel(self, cid):
        if self._bad(cid):
            return "ValueError"
        if cid in self.live:
            fn = self.live.pop(cid); self._bury(cid, "cancelled"); self._promote(fn)
            return "ok"
        for i, (c, _) in enumerate(self.queued):
            if c == cid:
                self.queued.pop(i); self._bury(cid, "cancelled")
                return "ok"
        return self._missing(cid, "cancel")

    def all(self, outcome):
        victims = [c for c, _ in self.queued] + list(self.live)
        self.queued.clear(); self.live.clear()
        for c in victims:
            self._bury(c, outcome)
        return len(victims)


def gen_ops(rng, n):
    ops = []
    for _ in range(n):
        r = rng.random()
        if r < 0.40:
            ops.append(["invoke", rng.choice(FNS)])
        elif r < 0.65:
            ops.append(["complete", rng.randint(-1, 40)])
        elif r < 0.85:
            ops.append(["cancel", rng.randint(-1, 40)])
        elif r < 0.90:
            ops.append(["complete", rng.choice([True, "1", None, 1.5, 1 << 70])])
        elif r < 0.95:
            ops.append(["cancel_all"])
        else:
            ops.append(["trap_all"])
    return ops


def execute(ops, cfg, factory=rt.AsyncFunctions):
    """Returns None on agreement, else (step, expected, got)."""
    limit, qdepth, tcap = cfg
    m = Model(limit, qdepth, tcap)
    f = factory("p", declared={"a": True, "s": True, "q": True}, stateful=frozenset({"s"}),
                reentrancy={"q": rt.ReentrancyPolicy(rt.ReentrancyMode.QUEUE, qdepth)},
                concurrency_limit=limit, tombstone_capacity=tcap)
    for i, op in enumerate(ops):
        kind = op[0]
        exp = getattr(m, kind)(op[1]) if kind in ("invoke", "complete", "cancel") else \
            m.all("cancelled" if kind == "cancel_all" else "trapped")
        try:
            if kind == "invoke":
                st = f.invoke(op[1]); got = (st.status, st.call_id)
            elif kind == "complete":
                f.complete(op[1], i); got = "ok"
            elif kind == "cancel":
                f.cancel(op[1]); got = "ok"
            elif kind == "cancel_all":
                got = f.cancel_all()
            else:
                got = f.trap_all()
        except Exception as e:  # noqa: BLE001
            got = type(e).__name__
        if got != exp:
            return i, exp, got
        # global invariants after every step
        if f.calls_in_flight != len(m.live) or f.calls_queued != len(m.queued):
            return i, "counts", (f.calls_in_flight, f.calls_queued)
        if len(f._terminal) > tcap:
            return i, "bound", len(f._terminal)
        if limit is not None and f.calls_in_flight > limit:
            return i, "limit", f.calls_in_flight
    return None


def shrink(ops, cfg, factory):
    changed = True
    while changed:
        changed = False
        for i in range(len(ops)):
            cand = ops[:i] + ops[i + 1:]
            if execute(cand, cfg, factory) is not None:
                ops, changed = cand, True
                break
    return ops


def campaign(n_cases, seed, factory=rt.AsyncFunctions):
    rng = random.Random(seed)
    for case in range(n_cases):
        cfg = (rng.choice([None, 1, 2, 5]), rng.randint(1, 3), rng.choice([1, 3, 64]))
        ops = gen_ops(rng, rng.randint(5, 80))
        bad = execute(ops, cfg, factory)
        if bad is not None:
            return case, cfg, shrink(ops, cfg, factory), bad
    return None


class PropertyTests(unittest.TestCase):
    def test_replay_corpus(self):
        for p in sorted(CORPUS.glob("*.json")):
            d = json.loads(p.read_text())
            with self.subTest(p.name):
                self.assertIsNone(execute(d["ops"], tuple(d["cfg"])), p.name)

    def test_model_agreement_campaign(self):
        res = campaign(scale(1500), SEED)
        if res is not None:
            case, cfg, ops, bad = res
            CORPUS.mkdir(exist_ok=True)
            (CORPUS / f"fail_{SEED}_{case}.json").write_text(json.dumps({"cfg": cfg, "ops": ops, "bad": repr(bad)}))
            self.fail(f"model disagreement seed={SEED} case={case} cfg={cfg} minimized={ops} at={bad}")

    def test_harness_detects_injected_defects(self):
        """Sensitivity: each seeded mutant must be caught (else the harness is too weak)."""

        class NoTombstoneBound(rt.AsyncFunctions):
            def __post_init__(self):
                super().__post_init__()
                self.tombstone_capacity = 10 ** 9

        class ResurrectsCancelled(rt.AsyncFunctions):
            def complete(self, call_id, value, **kw):
                t = self._terminal.get(call_id) if isinstance(call_id, int) else None
                if t is not None and t.outcome is rt.Outcome.CANCELLED:
                    return value
                return super().complete(call_id, value, **kw)

        class IgnoresLimit(rt.AsyncFunctions):
            def __post_init__(self):
                super().__post_init__()
                self.concurrency_limit = None

        for mutant in (NoTombstoneBound, ResurrectsCancelled, IgnoresLimit):
            with self.subTest(mutant.__name__):
                self.assertIsNotNone(campaign(400, SEED, mutant), f"{mutant.__name__} escaped")


class DeclarationFuzz(unittest.TestCase):
    def test_random_declaration_maps(self):
        rng = random.Random(SEED)
        junk = [None, 1, 0, "", "x", True, b"f", 1.0, ("t",)]
        for _ in range(scale(500)):
            decl = {rng.choice(junk + ["f", "g"]): rng.choice(junk + [True, False]) for _ in range(rng.randint(0, 4))}
            stateful = frozenset(rng.sample(["f", "g", "h"], rng.randint(0, 2)))
            limit = rng.choice([None, 0, -1, 1, True, 2.0, "3", 10 ** 30])
            try:
                f = rt.AsyncFunctions("i", declared=decl, stateful=stateful, concurrency_limit=limit)
            except (TypeError, ValueError):
                continue
            for name, v in f.declared.items():     # anything accepted is well-formed and frozen
                self.assertIsInstance(name, str)
                self.assertIsInstance(v, bool)
            self.assertTrue(f.stateful <= set(f.declared))


if __name__ == "__main__":
    unittest.main()
