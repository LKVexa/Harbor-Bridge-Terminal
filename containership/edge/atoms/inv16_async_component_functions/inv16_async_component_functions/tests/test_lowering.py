"""Closure #8 (reference half): lowered state machine vs native coroutine, isolation, cleanup."""
import asyncio
import itertools
import unittest

from _util import sub

lw = sub("lowering")
ENV = {"inc": lambda x: x + 1, "add": lambda a, b: a + b, "pos": lambda x: x > 0, "neg": lambda x: -x,
       "zero": lambda: 0}

PROGRAMS = {
    "zero_suspend": [("let", "z", "zero"), ("let", "r", "inc", "z"), ("return", "r")],
    "one_suspend": [("await", "a", "t1"), ("let", "r", "inc", "a"), ("return", "r")],
    "multi_branch": [("await", "a", "t1"), ("await", "b", "t2"), ("let", "s", "add", "a", "b"),
                     ("let", "p", "pos", "s"),
                     ("if", "p", [("let", "r", "inc", "s")], [("let", "r", "neg", "s")]),
                     ("return", "r")],
}


async def reference(name, resumes):
    """Native coroutine equivalents (the differential oracle)."""
    it = iter(resumes)

    async def sub_(_t):
        return next(it)
    if name == "zero_suspend":
        return 0 + 1
    if name == "one_suspend":
        return (await sub_("t1")) + 1
    a = await sub_("t1"); b = await sub_("t2"); s = a + b
    return s + 1 if s > 0 else -s


def drive(machine, resumes):
    fr = lw.start(machine)
    kind, v = lw.step(fr, ENV)
    it = iter(resumes)
    while kind == "suspend":
        kind, v = lw.step(fr, ENV, next(it), discriminant=fr.pc)
    return v, fr


class Lowering(unittest.TestCase):
    def test_golden_shapes(self):
        shapes = {k: [s["suspend"] for s in lw.lower(k, p).describe()] for k, p in PROGRAMS.items()}
        self.assertEqual(shapes, {"zero_suspend": [None], "one_suspend": ["t1", None],
                                  "multi_branch": ["t1", "t2", None]})

    def test_differential_against_coroutines(self):
        for name, prog in PROGRAMS.items():
            m = lw.lower(name, prog)
            for resumes in itertools.product([-5, 0, 3], repeat=2):
                got, fr = drive(m, resumes)
                exp = asyncio.run(reference(name, resumes))
                self.assertEqual(got, exp, (name, resumes))
                self.assertEqual(fr.cleanups, 1)

    def test_per_call_storage_is_isolated(self):
        m = lw.lower("one_suspend", PROGRAMS["one_suspend"])
        f1, f2 = lw.start(m), lw.start(m)
        lw.step(f1, ENV); lw.step(f2, ENV)
        self.assertIsNot(f1.locals, f2.locals)
        lw.step(f1, ENV, 10, discriminant=0)
        self.assertEqual(lw.step(f2, ENV, 20, discriminant=0), ("return", 21))
        self.assertEqual(f1.result, 11)

    def test_cancel_at_every_suspension_point_cleans_once(self):
        m = lw.lower("multi_branch", PROGRAMS["multi_branch"])
        for stop_at in range(2):
            fr = lw.start(m)
            lw.step(fr, ENV)
            for k in range(stop_at):
                lw.step(fr, ENV, 1, discriminant=fr.pc)
            lw.cancel(fr); lw.cancel(fr)
            self.assertEqual((fr.status, fr.cleanups, fr.locals), ("cancelled", 1, {}))
            with self.assertRaises(lw.InvalidResume):
                lw.step(fr, ENV, 1, discriminant=fr.pc)

    def test_trap_unwinds_once(self):
        m = lw.lower("t", [("await", "a", "t1"), ("let", "r", "boom", "a"), ("return", "r")])
        fr = lw.start(m)
        lw.step(fr, ENV)
        with self.assertRaises(ZeroDivisionError):
            lw.step(fr, {"boom": lambda a: 1 / 0}, 1, discriminant=0)
        self.assertEqual((fr.status, fr.cleanups), ("trapped", 1))

    def test_invalid_discriminants_fail_closed(self):
        m = lw.lower("one_suspend", PROGRAMS["one_suspend"])
        for bad in (None, 1, -1, 99, "0"):
            fr = lw.start(m)
            lw.step(fr, ENV)
            with self.assertRaises(lw.InvalidResume):
                lw.step(fr, ENV, 1, discriminant=bad)
            self.assertEqual(fr.status, "suspended")      # rejected resume does not corrupt the frame
        fr = lw.start(m)
        with self.assertRaises(lw.InvalidResume):
            lw.step(fr, ENV, discriminant=5)


if __name__ == "__main__":
    unittest.main()
