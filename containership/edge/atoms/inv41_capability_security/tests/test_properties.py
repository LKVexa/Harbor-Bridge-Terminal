"""Property-based and model-based (stateful) fuzzing, stdlib only (Section 20).

Seeds are deterministic (INV41_SEED, default 4130); INV41_ITER scales the
campaign (PR default 300; nightly uses e.g. 20000).  Any failure prints the
seed and the minimized action trace so it can be pinned in
``tests/vectors/regressions.json``.
"""
from __future__ import annotations

import json
import pickle
import unittest

from _common import ITERATIONS, PKG_DIR, SEED, rng

from inv41_capability_security import errors
from inv41_capability_security.capabilities import (
    Authority, CapabilityError, CrossAuthority, Forged, Membrane, Reference, Revoked, Widening,
)

OPS = ["read", "write", "admin", "send", "recv", "list"]
WEIRD_IDS = ["", " ", "\x00", "a​b", "é", "é", "../x", "a/b", "a|b", "x" * 257, "x" * 256, "\U0001F600",
             "﻿id", "A" * 10_000, "\t", "ok"]


def gen_ops(r):
    return set(r.sample(OPS, r.randint(0, len(OPS))))


class PropertyTest(unittest.TestCase):
    def test_PR001_non_forgeability(self):
        r = rng(1)
        a = Authority({"s": set(OPS)}, authority_id="p")
        h = a.bind_holder("h", {"s": a.grant("s")})
        for _ in range(ITERATIONS):
            fake = object.__new__(Reference)
            for slot, val in (("_authority_id", "p"), ("_authority_seal", bytes(r.getrandbits(8) for _ in range(32))),
                              ("_resource", "s"), ("_operations", frozenset(OPS)), ("_token", "t"),
                              ("_signature", "%064x" % r.getrandbits(256)), ("_membranes", ()), ("_sealed", True)):
                object.__setattr__(fake, slot, val)
            with self.assertRaises(CapabilityError):
                a.bind_holder("x", {"s": fake})
            with self.assertRaises(CapabilityError):
                fake.invoke("read")
        self.assertTrue(h.use("s", "read")["permitted"])

    def test_PR002_monotonic_attenuation(self):
        r = rng(2)
        a = Authority({"s": set(OPS)})
        for i in range(ITERATIONS):
            parent = a.grant("s", gen_ops(r) or {"read"})
            req = gen_ops(r)
            try:
                child = parent.attenuate(req)
            except Widening:
                self.assertFalse(req <= parent.operations, f"seed={SEED} i={i}")
                continue
            self.assertTrue(child.operations <= parent.operations, f"seed={SEED} i={i}")

    def test_PR003_cross_authority_isolation(self):
        r = rng(3)
        domains = [Authority({"s": set(OPS)}, authority_id=r.choice(["same", "same", f"d{i}"])) for i in range(8)]
        for _ in range(ITERATIONS):
            src, dst = r.sample(domains, 2)
            with self.assertRaises(CrossAuthority):
                dst.bind_holder("x", {"s": src.grant("s")})

    def test_PR004_identifier_fuzz_deterministic_denial(self):
        r = rng(4)
        for _ in range(ITERATIONS):
            ident = r.choice(WEIRD_IDS) + "".join(chr(r.randint(0, 0x2FF)) for _ in range(r.randint(0, 4)))
            outcomes = set()
            for _rep in range(2):
                try:
                    Authority({ident: {"read"}})
                    outcomes.add("ok")
                except (ValueError, TypeError) as exc:
                    outcomes.add(errors.code_for(exc))
            self.assertEqual(len(outcomes), 1, repr(ident))

    def test_PR005_redaction_property(self):
        r = rng(5)
        a = Authority({"s": set(OPS)})
        for _ in range(min(ITERATIONS, 200)):
            ref = a.grant("s", gen_ops(r) or {"read"})
            texts = [repr(ref), repr(a)]
            for fn in (lambda: ref.invoke("nope"), lambda: ref.attenuate({"zzz"}), lambda: pickle.dumps(ref)):
                try:
                    fn()
                except Exception as exc:
                    texts += [str(exc), json.dumps(errors.describe(exc))]
            for t in texts:
                self.assertNotIn(ref.token, t)
                self.assertNotIn(ref._signature, t)
                self.assertNotIn(a._authority_seal.hex(), t)


class ModelBasedTest(unittest.TestCase):
    """Random action sequences compared against a trivially-correct reference model."""

    def test_PR006_state_machine_against_model(self):
        r = rng(6)
        steps = ITERATIONS * 4
        a = Authority({"s": set(OPS), "q": {"send"}}, authority_id="model")
        refs: list = []   # (ref, ops, membranes)
        membranes: list = []
        trace = []
        for step in range(steps):
            act = r.choice(["grant", "attenuate", "wrap", "revoke", "use", "use", "bind"])
            trace.append(act)
            try:
                if act == "grant" or not refs:
                    res = r.choice(["s", "q"])
                    ops = gen_ops(r) if res == "s" else {"send"}
                    ops = ops or None
                    allowed = set(OPS) if res == "s" else {"send"}
                    try:
                        ref = a.grant(res, ops)
                        self.assertTrue(ops is None or ops <= allowed)
                        refs.append((ref, frozenset(ops or allowed), ()))
                    except Widening:
                        self.assertFalse(ops <= allowed)
                    continue
                ref, ops, mems = r.choice(refs)
                dead = any(m.revoked for m in mems)
                if act == "attenuate":
                    req = gen_ops(r)
                    try:
                        child = ref.attenuate(req)
                        self.assertFalse(dead)
                        self.assertTrue(req <= ops)
                        refs.append((child, frozenset(req), mems))
                    except Revoked:
                        self.assertTrue(dead)
                    except Widening:
                        self.assertFalse(dead)
                        self.assertFalse(req <= ops)
                elif act == "wrap":
                    m = Membrane(f"m{step}") if not membranes or r.random() < 0.5 else r.choice(membranes)
                    membranes.append(m)
                    try:
                        w = m.wrap(ref)
                        self.assertFalse(dead or m.revoked)
                        refs.append((w, ops, (m,) + tuple(x for x in mems if x is not m)))
                    except Revoked:
                        self.assertTrue(dead or m.revoked)
                    except CapabilityError:
                        pass  # depth limit
                elif act == "revoke" and membranes:
                    r.choice(membranes).revoke()
                elif act == "use":
                    op = r.choice(OPS)
                    try:
                        ref.invoke(op)
                        self.assertFalse(dead, "post-revocation use succeeded")
                        self.assertIn(op, ops)
                    except Revoked:
                        self.assertTrue(dead)
                    except Forged:
                        self.assertFalse(dead)
                        self.assertNotIn(op, ops)
                elif act == "bind":
                    try:
                        a.bind_holder("h", {"x": ref})
                        self.assertFalse(dead)
                    except Revoked:
                        self.assertTrue(dead)
            except AssertionError as exc:
                raise AssertionError(f"seed={SEED} step={step} trace_tail={trace[-12:]}") from exc
            # invariant after every step: every ref behind a revoked membrane is dead
            for rf, _o, ms in refs[-20:]:
                if any(m.revoked for m in ms):
                    with self.assertRaises(Revoked):
                        rf.invoke("read")

    def test_PR007_pinned_regressions(self):
        path = PKG_DIR / "tests" / "vectors" / "regressions.json"
        cases = json.loads(path.read_text())["cases"]
        a = Authority({"s": {"read"}})
        for c in cases:
            with self.subTest(c["id"]):
                if c["kind"] == "operations":
                    with self.assertRaises((ValueError, TypeError)):
                        a.grant("s", c["input"])
                elif c["kind"] == "identifier":
                    with self.assertRaises((ValueError, TypeError)):
                        Authority({c["input"]: {"read"}})


if __name__ == "__main__":
    unittest.main()
