"""Adjacent-layer end-to-end tests against the real V8 engine (C030, C083, C046, C089).

Lane: requires ``node`` (>= 20) on PATH.  When absent every test here SKIPS with the
reason, and ``tools/ci.py`` reports the lane NOT RUN (never PASS).
"""
from __future__ import annotations

import random
import unittest

from inv45_sfi_mechanisms.tests.support import Harness, node_available
from inv45_sfi_mechanisms.production import builder, engine, sfi
from inv45_sfi_mechanisms.production.builder import I32, I64, Func, ModuleBuilder
from inv45_sfi_mechanisms.production.errors import SfiError
from inv45_sfi_mechanisms.production.wasm import MEMORY_OPS

NODE = node_available()
PAGES = 6
A = sfi.Profile(region_base=65536, region_log2=16, require_imported_memory=True)
B = sfi.Profile(region_base=65536 * 3, region_log2=16, require_imported_memory=True)
CANARY = 0xA5


def i32(v):
    return {"t": "i32", "v": v}


def attacker(pages=PAGES):
    """Stores/loads at caller-chosen addresses with every width - the escape attempt."""
    b = ModuleBuilder(memory=(pages, None), import_memory=("env", "memory"))
    b.add(Func((I32, I32), (), [(0x20, 0), (0x20, 1), (0x36, (0, 0)), (0x0B, None)], export="w32"))
    b.add(Func((I32, I64), (), [(0x20, 0), (0x20, 1), (0x37, (0, 0xFFFF)), (0x0B, None)], export="w64off"))
    b.add(Func((I32, I32), (), [(0x20, 0), (0x20, 1), (0x3A, (0, 0xFFFFFFFF)), (0x0B, None)], export="w8maxoff"))
    b.add(Func((I32,), (I32,), [(0x20, 0), (0x28, (0, 0)), (0x0B, None)], export="r32"))
    return b.build()


@unittest.skipUnless(NODE, "node-v8 engine lane not available (node missing or preflight failed)")
class EngineEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.eng = engine.NodeV8Engine(timeout=20.0, expected_major=None)

    def run_job(self, modules, calls, regions):
        return self.eng.run({"modules": modules, "memory_pages": PAGES, "canary": CANARY, "calls": calls,
                             "regions": regions})

    def test_unrewritten_module_escapes_without_sfi(self):
        """Control experiment: proves the harness can observe an escape at all."""
        raw = attacker()
        out = self.run_job([{"name": "a", "bytes": raw}], [{"module": "a", "export": "w32",
                                                           "args": [i32(65536 * 3 + 100), i32(1)]}],
                           [[65536 * 3, 65536 * 4]])
        self.assertTrue(out["calls"][0]["ok"])
        self.assertFalse(out["regions"][0]["untouched"], "control write did not land - harness is blind")

    def test_two_tenants_share_memory_without_crossing_partitions(self):
        ra = sfi.rewrite(attacker(), A).artifact
        rb = sfi.rewrite(attacker(), B).artifact
        sfi.verify(ra, A)
        sfi.verify(rb, B)
        rng = random.Random(4545)
        addrs = [0, 1, 65535, 65536, 65536 * 3 + 7, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0xFFFFFFFC] + \
                [rng.randrange(0, 1 << 32) for _ in range(200)]
        calls = []
        for a in addrs:
            s = a - (1 << 32) if a >= 1 << 31 else a
            calls.append({"module": "a", "export": "w32", "args": [i32(s), i32(-1)]})
            calls.append({"module": "a", "export": "w64off", "args": [i32(s), {"t": "i64", "v": "-1"}]})
            calls.append({"module": "a", "export": "w8maxoff", "args": [i32(s), i32(0)]})
        out = self.run_job([{"name": "a", "bytes": ra}, {"name": "b", "bytes": rb}], calls,
                           [[0, A.region_base], [A.region_base + A.size + 8, B.region_base],
                            [B.region_base, B.region_base + B.size], [B.region_base + B.size, PAGES * 65536],
                            [A.region_base, A.region_base + A.size]])
        self.assertTrue(all(c["ok"] for c in out["calls"]), [c for c in out["calls"] if not c["ok"]][:3])
        below, gap, b_part, above, a_part = out["regions"]
        self.assertTrue(below["untouched"])
        self.assertTrue(gap["untouched"])
        self.assertTrue(b_part["untouched"], "tenant A wrote into tenant B's partition")
        self.assertTrue(above["untouched"])
        self.assertFalse(a_part["untouched"])

    def test_guard_is_load_bearing_and_adjacent_partitions_refused(self):
        """Adversarial-review finding: a top-of-partition i64 store reaches the guard, so partitions must
        be spaced by size + 8; check_partitions refuses adjacency."""
        b = ModuleBuilder(memory=(PAGES, None), import_memory=("env", "memory"))
        b.add(Func((I32,), (), [(0x20, 0), (0x42, -1), (0x37, (0, 0)), (0x0B, None)], export="w"))
        ra = sfi.rewrite(b.build(), A).artifact
        out = self.run_job([{"name": "a", "bytes": ra}], [{"module": "a", "export": "w", "args": [i32(A.mask)]}],
                           [[A.region_base + A.size, A.region_base + A.size + 8],
                            [A.region_base + A.size + 8, PAGES * 65536]])
        self.assertFalse(out["regions"][0]["untouched"])
        self.assertTrue(out["regions"][1]["untouched"])
        adjacent = sfi.Profile(A.region_base + A.size, 16, require_imported_memory=True)
        with self.assertRaises(SfiError):
            sfi.check_partitions([A, adjacent])
        sfi.check_partitions([A, B])

    def test_generated_programs_never_escape(self):
        """Randomised escape fuzz executed in V8 (C085/C050)."""
        rng = random.Random(1045)
        for round_ in range(6):
            b = ModuleBuilder(memory=(PAGES, None), import_memory=("env", "memory"))
            body = []
            for _ in range(rng.randrange(5, 40)):
                op = rng.choice([0x36, 0x37, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x38, 0x39])
                vt, width, _ = MEMORY_OPS[op]
                align = {1: 0, 2: 1, 4: 2, 8: 3}[width]
                val = {0x7F: (0x41, -1), 0x7E: (0x42, -1), 0x7D: (0x43, b"\xff" * 4), 0x7C: (0x44, b"\xff" * 8)}[vt]
                if rng.random() < 0.3:  # statically known address -> exercises the constant-fold path
                    addr = [(0x41, rng.randrange(-2**31, 2**31))]
                else:
                    addr = [(0x20, 0), (0x41, rng.randrange(-2**31, 2**31)), (0x6A, None)]
                body += addr + [val, (op, (align, rng.randrange(0, 1 << 32)))]
            b.add(Func((I32,), (), body + [(0x0B, None)], export="go"))
            ra = sfi.rewrite(b.build(), A).artifact
            sfi.verify(ra, A)
            calls = [{"module": "a", "export": "go", "args": [i32(rng.randrange(-2**31, 2**31))]} for _ in range(40)]
            out = self.run_job([{"name": "a", "bytes": ra}], calls,
                               [[0, A.region_base], [A.region_base + A.size + 8, PAGES * 65536]])
            self.assertTrue(all(c["ok"] for c in out["calls"]))
            self.assertTrue(all(r["untouched"] for r in out["regions"]), f"escape in round {round_}")

    def test_accepted_modules_are_engine_valid(self):
        """Differential oracle: nothing our verifier accepts is invalid to V8."""
        blobs = [sfi.rewrite(builder.rw_module(), sfi.Profile(65536, 16)).artifact,
                 sfi.rewrite(attacker(), A).artifact]
        self.assertEqual(engine.validate_with_engine(blobs), [True, True])

    def test_hostcall_not_allowlisted_is_absent(self):
        b = ModuleBuilder(memory=(PAGES, None), import_memory=("env", "memory"),
                          func_imports=[("env", "trace_i32", (I32,), ())])
        b.add(Func((), (), [(0x41, 7), (0x10, 0), (0x0B, None)], export="t"))
        blob = b.build()
        with self.assertRaises(SfiError) as cm:
            self.eng.run({"modules": [{"name": "a", "bytes": blob, "allow": []}], "memory_pages": PAGES, "calls": []})
        self.assertEqual(cm.exception.code, "SFI_POLICY_REJECTED")
        out = self.eng.run({"modules": [{"name": "a", "bytes": blob, "allow": ["env.trace_i32"]}],
                            "memory_pages": PAGES, "calls": [{"module": "a", "export": "t", "args": []}]})
        self.assertEqual(out["trace"], [7])

    def test_runaway_execution_is_killed(self):
        b = ModuleBuilder(memory=None)
        b.add(Func((), (), [(0x03, ()), (0x0C, 0), (0x0B, None), (0x0B, None)], export="spin"))
        eng = engine.NodeV8Engine(timeout=1.5, expected_major=None)
        with self.assertRaises(SfiError) as cm:
            eng.run({"modules": [{"name": "a", "bytes": b.build()}], "memory_pages": 0,
                     "calls": [{"module": "a", "export": "spin", "args": []}]})
        self.assertEqual(cm.exception.code, "SFI_DEADLINE_EXCEEDED")


class EnginePreflightTest(unittest.TestCase):
    """T20 / U-02 / U-07: engine prerequisites are detected, and a wrong engine fails closed."""

    def test_preflight_reports_structured_checks(self):
        rep = engine.preflight(None)
        self.assertIn("checks", rep)
        if NODE:
            self.assertTrue(rep["checks"]["permission_model_denies_writes"])

    @unittest.skipUnless(NODE, "node-v8 engine lane not available")
    def test_pinned_major_mismatch_fails_closed(self):
        with self.assertRaises(SfiError) as cm:
            engine.NodeV8Engine(expected_major=3)
        self.assertEqual(cm.exception.code, "SFI_DEPENDENCY_UNAVAILABLE")


@unittest.skipUnless(NODE, "node-v8 engine lane not available")
class ServiceEndToEnd(unittest.TestCase):
    def setUp(self):
        self.h = Harness(with_engine=True)

    def tearDown(self):
        self.h.close()

    def test_verify_seal_authorize_load_execute(self):
        r = self.h.submit()
        tok = self.h.tenant_token("t1")
        handle = self.h.svc.load(tok, r["artifact"], r["descriptor"])
        out = self.h.svc.execute(tok, handle, [
            {"export": "store", "args": [i32(0x7FFFFFFF), i32(42)]},
            {"export": "load", "args": [i32(0x7FFFFFFF)]},
            {"export": "fill", "args": [i32(64)]}, {"export": "sum", "args": [i32(64)]}])
        self.assertEqual([c["result"]["v"] if c["result"] else None for c in out["calls"]], [None, 42, None, 2016])

    def test_raw_artifact_cannot_be_loaded(self):
        r = self.h.submit()
        tok = self.h.tenant_token("t1")
        raw = builder.rw_module()
        with self.assertRaises(SfiError) as cm:
            self.h.svc.load(tok, raw, r["descriptor"])
        self.assertEqual(cm.exception.code, "SFI_DIGEST_MISMATCH")

    def test_engine_unavailable_fails_closed_and_breaker_opens(self):
        r = self.h.submit()
        tok = self.h.tenant_token("t1")
        handle = self.h.svc.load(tok, r["artifact"], r["descriptor"])

        class Down:
            def run(self, job):
                raise SfiError("SFI_DEPENDENCY_UNAVAILABLE", "injected", dependency="node-v8")
        self.h.svc.engine = Down()
        for _ in range(3):
            with self.assertRaises(SfiError):
                self.h.svc.execute(tok, handle, [{"export": "load", "args": [i32(0)]}])
        self.assertEqual(self.h.svc.engine_breaker.state, "open")
        self.assertEqual(self.h.svc.health()["status"], "degraded")


if __name__ == "__main__":
    unittest.main()
