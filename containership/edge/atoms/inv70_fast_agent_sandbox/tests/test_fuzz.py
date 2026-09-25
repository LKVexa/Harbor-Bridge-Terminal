"""C085 fuzzing / property-based tests of every untrusted boundary.

Deterministic seeds (INV70_FUZZ_SEED, INV70_FUZZ_ITERS) so any failure reproduces.
Properties: no uncaught exception crosses a boundary; every result carries a
known stable reason code; fuel never exceeds the budget; parsers reject rather
than mis-accept.
"""
import importlib
import os
import random
import time
import unittest

import _path
rt = importlib.import_module(_path.PKG + ".runtime")
svc = importlib.import_module(_path.PKG + ".service")
sec = importlib.import_module(_path.PKG + ".security")
tel = importlib.import_module(_path.PKG + ".telemetry")
cfg = importlib.import_module(_path.PKG + ".config")
sem = importlib.import_module(_path.PKG + ".semantics")

SEED = int(os.environ.get("INV70_FUZZ_SEED", "7070"))
ITERS = int(os.environ.get("INV70_FUZZ_ITERS", "3000"))
OPS = ["push", "add", "mul", "dup", "jmp", "jz", "call", "halt", "bogus"]
KNOWN = {c for c, _ in svc.REASON_CODES.values()} | {"FB-OK"}


def rand_value(r):
    return r.choice([None, True, 0, -1, r.randint(-2**70, 2**70), 1.5, float("inf"), "", "ab" * r.randint(0, 50),
                     b"x" * r.randint(0, 50), [], {}, object(), 2**4000])


def rand_program(r):
    n = r.randint(0, 12)
    prog = []
    for _ in range(n):
        op = r.choice(OPS)
        shape = r.random()
        if shape < 0.05:
            prog.append(rand_value(r))
            continue
        inst = [op]
        if op in ("push",):
            inst.append(rand_value(r))
        elif op in ("jmp", "jz"):
            inst.append(r.choice([r.randint(-2, n + 2), "1", 1.0]))
        elif op == "call":
            inst.append(r.choice(["double", "x" * 200, "", "a\nb", "boom", 5]))
        if r.random() < 0.05:
            inst.append(1)
        prog.append(tuple(inst) if r.random() < .5 else inst)
    return prog


class FuzzRuntime(unittest.TestCase):
    def test_runtime_properties(self):
        r = random.Random(SEED)
        for i in range(ITERS):
            fuel = r.randint(0, 300)
            prog = rand_program(r)
            try:
                out = rt.run(prog, fuel=fuel, caps={"double"}, host={"double": lambda x: x * 2},
                             max_memory_bytes=4096, max_value_bytes=1024)
            except Exception as e:  # pragma: no cover
                self.fail(f"seed={SEED} iter={i} raised {type(e).__name__}: {prog!r}")
            self.assertTrue(("ok" in out) ^ ("trap" in out))
            self.assertLessEqual(out["fuel"], fuel)
            if "trap" in out:
                self.assertNotEqual(svc.reason_code(out["trap"])[0], "FB-X999", out["trap"])


class FuzzService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ts = sec.TrustStore()
        cls.ts.add("c1", b"f" * 32, "caller")
        cls.sb = svc.Sandbox(environment="dev", trust=cls.ts, audit_key=b"a" * 32)
        cls.sb.register_capability("double", lambda x: 2 * x)
        cls.sb.admission.rate = 1e9
        cls.sb.admission.burst = 1e9

    @classmethod
    def tearDownClass(cls):
        cls.sb.close()

    def test_request_envelope(self):
        r = random.Random(SEED + 1)
        for i in range(ITERS // 3):
            good = sec.issue_token(self.ts, "c1", subject="s", tenant="t", capabilities={"double"},
                                   audience="inv70", ttl_s=60, now=time.time(), token_id=f"z{i}")
            req = {}
            for k in ("token", "versions", "program", "caps", "fuel", "idempotency_key", "junk"):
                if r.random() < 0.8:
                    req[k] = {"token": r.choice([good, good[:-3], "", None, 7, "a.b"]),
                              "versions": r.choice([[2], [1], [9], "2", None, [2, "x"]]),
                              "program": rand_program(r),
                              "caps": r.choice([["double"], "double", [1], [], None]),
                              "fuel": r.choice([None, -5, 3, 10**12, "9"]),
                              "idempotency_key": r.choice([None, "", "k", "x" * 500, 3]),
                              "junk": rand_value(r)}[k]
            if r.random() < 0.05:
                req = r.choice([None, [], "x", 5])
            tp = r.choice([None, "", "00-" + "a" * 32 + "-" + "b" * 16 + "-01", "zz" * 30])
            try:
                out = self.sb.handle(req, traceparent=tp)
            except Exception as e:  # pragma: no cover
                self.fail(f"seed={SEED + 1} iter={i} {type(e).__name__}: {req!r}")
            code = out.get("reason_code")
            if code is not None:
                self.assertIn(code, KNOWN)
            else:  # v1 shape
                self.assertTrue(("ok" in out) ^ ("trap" in out))


class FuzzParsers(unittest.TestCase):
    def test_tokens_attestations_traceparent_config_versions(self):
        r = random.Random(SEED + 2)
        auth = sec.Authenticator(sec.TrustStore(), sec.Clock())
        for _ in range(ITERS // 3):
            blob = "".join(r.choice("abcXYZ019-_.=") for _ in range(r.randint(0, 80)))
            with self.assertRaises(sec.AuthError):
                auth.authenticate(blob)
            with self.assertRaises(sec.AuthError):
                sec.verify_attestation(sec.TrustStore(), sec.Clock(), r.choice([None, {}, {"statement": blob}]),
                                       role="node", expected_measurements=set())
            c = tel.TraceContext.from_header(blob)
            self.assertEqual(len(c.trace_id), 32)
            overlay = {r.choice(list(cfg.SCHEMA) + ["zzz"]): rand_value(r)}
            try:
                cfg.resolve("prod", overlay)
            except cfg.ConfigError:
                pass
            try:
                sem.negotiate("PK_FASTBOX_RUN", r.choice([[r.randint(-3, 5)], blob, None, [blob]]))
            except sem.VersionError:
                pass


if __name__ == "__main__":
    unittest.main()
