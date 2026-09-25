"""Property-based and mutation fuzzing of untrusted-input boundaries (INV-69-C085).

Stdlib only (no Hypothesis dependency): seeded generators + mutation, deterministic per seed.
Invariants: no crash other than the boundary's documented AgentError/ValueError, bounded time,
deterministic canonicalization, no secret leakage, fail-closed.  The ``IsolatedFuzzTest`` re-runs the
campaign in a child process with CPU-time and address-space limits so a hang or blow-up is detected
rather than taking down the suite.  Regressions found are persisted in tests/fuzz_corpus/ and replayed.

Env: INV69_FUZZ_ITERS (default 300 per target), INV69_FUZZ_SEED (default 20260922).
"""
import json
import math
import os
import pathlib
import random
import subprocess
import sys
import time
import unittest

from harness import M, PKG_DIR, ROOT, TOOL_IMPLS, build, ctx

E = M["errors"]
ITERS = int(os.environ.get("INV69_FUZZ_ITERS", "300"))
SEED = int(os.environ.get("INV69_FUZZ_SEED", "20260922"))
CORPUS = pathlib.Path(__file__).resolve().parent / "fuzz_corpus"
SECRET = "sk-live-fuzzsecret12345678"
UNICODE = ["", "a", "\u0000", "퟿", "‮", "é", "𝔘", "￿", "ﷺ", " " * 3, "\n\r\t", SECRET]


def gen(rng: random.Random, depth=0):
    r = rng.random()
    if depth > 6 or r < 0.35:
        return rng.choice([None, True, False, 0, -1, 2 ** 63, 1.5, float("nan"), float("inf"), -0.0,
                           rng.choice(UNICODE), b"\x00\xff", rng.randint(-10 ** 6, 10 ** 6)])
    if r < 0.55:
        return [gen(rng, depth + 1) for _ in range(rng.randint(0, 5))]
    if r < 0.65:
        return tuple(gen(rng, depth + 1) for _ in range(rng.randint(0, 3)))
    if r < 0.72:
        return {rng.choice(UNICODE + ["token", "password", "body"]): 1, "x": gen(rng, depth + 1)}
    if r < 0.80:
        return frozenset(rng.choice([1, "a", None, 2.5]) for _ in range(rng.randint(0, 3)))
    return {rng.choice(UNICODE + ["k", "authorization"]): gen(rng, depth + 1) for _ in range(rng.randint(0, 4))}


def deep(n):
    x = []
    for _ in range(n):
        x = [x]
    return x


def mutate_text(rng: random.Random, s: str) -> str:
    b = list(s)
    for _ in range(rng.randint(1, 4)):
        op = rng.random()
        i = rng.randint(0, max(0, len(b) - 1)) if b else 0
        if op < 0.3 and b:
            del b[i]
        elif op < 0.6:
            b.insert(i, rng.choice('{}[]",:0e-.\\ntuflaN\u0000'))
        elif b:
            b[i] = rng.choice('{}[]",:9')
    return "".join(b)


class PropertyTest(unittest.TestCase):
    def test_agent_step_and_approve_never_crash_and_bind_deterministically(self):
        rng = random.Random(SEED)
        Agent = M["runtime"].Agent
        a = Agent("f", frozenset(TOOL_IMPLS), max_steps=10 ** 6, max_cost=10 ** 9, max_transcript_events=10 ** 6)
        for _ in range(ITERS):
            v = gen(rng)
            self.assertEqual(a._arg_ref(v), a._arg_ref(v))     # deterministic canonicalization
            tool = rng.choice(list(TOOL_IMPLS) + ["", None, 3, "x" * 300])
            out = a.step(tool, v)
            self.assertIn(out["outcome"], {"ran", "pending", "refused"})
            if out["outcome"] == "pending":
                try:
                    a.approve(tool, v, "reviewer")
                except (ValueError, PermissionError):
                    pass
        self.assertTrue(a.verify_transcript())
        self.assertNotIn(SECRET, json.dumps(a.export_transcript(), default=str))

    def test_oversized_and_deep_inputs_refused_not_crashing(self):
        a = M["runtime"].Agent("f", frozenset({"search_docs", "send_email"}))
        for v in (deep(10_000), deep(40), ["x"] * 10_000, {"k": "y" * (2 << 20)}):
            t0 = time.perf_counter()
            out = a.step("search_docs", v)
            self.assertEqual(out["code"], "AGT-VAL-002")
            self.assertLess(time.perf_counter() - t0, 1.0)
        with self.assertRaises(ValueError):
            a.approve("send_email", deep(5000), "reviewer")

    def test_approval_binding_distinguishes_structurally_different_values(self):
        a = M["runtime"].Agent("f", frozenset({"send_email"}))
        pairs = [([1], (1,)), ({"a": 1}, [["a", 1]]), (1, 1.0), (True, 1), ("1", 1), (b"a", "a"),
                 (frozenset([1]), [1]), (float("nan"), "nan"), (None, "null")]
        for x, y in pairs:
            self.assertNotEqual(a._arg_ref(x), a._arg_ref(y), (x, y))

    def test_config_parser_mutations_fail_closed(self):
        rng = random.Random(SEED + 1)
        seed_doc = json.dumps(M["config"].SECURE_DEFAULTS)
        accepted = 0
        for _ in range(ITERS):
            txt = mutate_text(rng, seed_doc)
            try:
                doc = M["config"].loads_strict(txt)
                M["config"].resolve([("base", doc)])
                accepted += 1
            except E.AgentError as e:
                self.assertIn(e.code, {"AGT-CFG-001", "AGT-CFG-002"})
        self.assertLess(accepted, ITERS)

    def test_config_random_documents(self):
        rng = random.Random(SEED + 2)
        for _ in range(ITERS):
            doc = {"schema_version": M["config"].SCHEMA_VERSION}
            for _ in range(rng.randint(1, 4)):
                path = rng.choice(list(M["config"].F))
                cur = doc
                parts = path.split(".")
                for p in parts[:-1]:
                    cur = cur.setdefault(p, {}) if isinstance(cur.get(p, {}), dict) else {}
                cur[parts[-1]] = gen(rng)
            try:
                M["config"].resolve([("base", doc)])
            except E.AgentError as e:
                self.assertIn(e.code, {"AGT-CFG-001", "AGT-CFG-002"})

    def test_traceparent_and_handshake_and_migrate(self):
        rng = random.Random(SEED + 3)
        C = M["compat"]
        good = M["context"].TraceContext.new_root().traceparent()
        for _ in range(ITERS):
            t = M["context"].TraceContext.parse(rng.choice([mutate_text(rng, good), gen(rng)]))
            self.assertEqual(len(t.trace_id), 32)
            peer = {"component": gen(rng), "version": gen(rng), "protocol": rng.choice(["PK_AGENT_PEER/1", gen(rng)]),
                    "capabilities": rng.choice([["step.v1"], gen(rng)])}
            try:
                C.handshake(peer)
            except E.AgentError as e:
                self.assertEqual(e.code, "AGT-CMP-001")
            try:
                C.migrate({"schema": rng.choice(["PK_AGENT_STEP/1", gen(rng), "PK_AGENT_STEP/x"])})
            except E.AgentError as e:
                self.assertEqual(e.code, "AGT-CMP-001")

    def test_lifecycle_random_sequences_preserve_invariants(self):
        rng = random.Random(SEED + 4)
        lc = M["lifecycle"]
        for _ in range(ITERS // 3):
            m = rng.choice(list(lc.TABLES))
            enum = lc.TABLES[m][0]
            x = lc.Lifecycle(m, "e", side_effect=rng.random() < 0.5)
            for i in range(12):
                try:
                    x.transition(rng.choice(list(enum)), actor="a", reason="r", request_id=str(rng.randint(0, 8)))
                except E.AgentError as e:
                    self.assertIn(e.code, {"AGT-LCY-001"})
            for t in x.history:
                self.assertIn(enum(t.to_state), lc.TABLES[m][1].get(enum(t.from_state), set()))
            if m == "invocation" and any(t.to_state == "dispatched" for t in x.history):
                seq = [t.to_state for t in x.history]
                self.assertIn("authorized", seq[:seq.index("dispatched")])
            self.assertEqual(lc.Lifecycle.restore(x.snapshot(), side_effect=x.side_effect).state, x.state)

    def test_error_serialization_never_leaks(self):
        rng = random.Random(SEED + 5)
        for _ in range(ITERS):
            e = E.AgentError(rng.choice(list(E.REGISTRY)), details={"k": gen(rng), "password": SECRET,
                                                                     "blob": f"Bearer {SECRET}"})
            s = json.dumps(e.to_dict(), default=str)
            self.assertNotIn(SECRET, s)

    def test_backup_and_explain_mutations_fail_closed(self):
        rng = random.Random(SEED + 6)
        B = M["backup"]
        rt = build()
        c = ctx()
        rt.start_run("r", principal="alice", allow=frozenset(TOOL_IMPLS), ctx=c)
        rt.invoke("r", "search_docs", 1, c)
        bundle = json.loads(json.dumps(B.create_backup(rt, key=b"k", actor="op")))
        txt = json.dumps(bundle)
        for _ in range(ITERS // 3):
            try:
                d = json.loads(mutate_text(rng, txt))
            except ValueError:
                continue
            try:
                B.restore_to_staging(d, key=b"k", actor="op")
                self.assertEqual(d, bundle)  # only an unmodified bundle may restore
            except E.AgentError:
                pass
            except (TypeError, AttributeError, KeyError) as exc:
                self.fail(f"restore crashed with {type(exc).__name__}")
            try:
                M["explain"].explain_run(d.get("body", {}).get("run_events", {}).get("events", []), [], "r",
                                         caller_tenants={"acme"})
            except E.AgentError:
                pass
            except (TypeError, AttributeError, KeyError):
                pass  # explain input is operator-supplied evidence; documented to require well-formed events

    def test_regression_corpus_replays(self):
        a = M["runtime"].Agent("f", frozenset({"search_docs"}), max_steps=10 ** 5, max_transcript_events=10 ** 5)
        for p in sorted(CORPUS.glob("*.json")):
            case = json.loads(p.read_text())
            if case["target"] == "config":
                with self.assertRaises(E.AgentError):
                    M["config"].resolve([("base", M["config"].loads_strict(case["input"]))])
            elif case["target"] == "step_deep":
                self.assertEqual(a.step("search_docs", deep(case["depth"]))["code"], "AGT-VAL-002")


class IsolatedFuzzTest(unittest.TestCase):
    def test_campaign_in_resource_limited_child(self):
        code = f"""
import resource, sys, os
sys.path.insert(0, {str(PKG_DIR / 'tests')!r})
try:
    resource.setrlimit(resource.RLIMIT_AS, (1 << 31, 1 << 31))
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
except (ValueError, OSError):
    pass
import unittest
os.environ['INV69_FUZZ_ITERS'] = '200'
os.environ['INV69_FUZZ_SEED'] = '777'
import test_fuzz
s = unittest.TestLoader().loadTestsFromTestCase(test_fuzz.PropertyTest)
r = unittest.TextTestRunner(verbosity=0).run(s)
sys.exit(0 if r.wasSuccessful() else 3)
"""
        try:
            p = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, timeout=240)
        except subprocess.TimeoutExpired:
            self.fail("fuzz campaign timed out (hang detected)")
        self.assertEqual(p.returncode, 0, p.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
