"""C031 pinned per-operation Wasm sandbox tests.

Engine-dependent tests SKIP when the pinned engine is not installed; with
INV70_REQUIRE_WASM=1 (release certification) a missing engine is a FAILURE, so a
skip can never be reported as PASS for production certification.
"""
import importlib
import os
import pathlib
import re
import unittest

import _path
ex = importlib.import_module(_path.PKG + ".executor")
LOCK = pathlib.Path(ex.__file__).parent / "requirements" / "wasm.lock"
REQUIRE = os.environ.get("INV70_REQUIRE_WASM") == "1"

# (wat, expected) - loop, memory growth, forbidden import
WAT_LOOP = '(module (func (export "run") (result i64) (loop $l (br $l)) (i64.const 0)))'
WAT_MEM = '(module (memory 1) (func (export "run") (result i64) (drop (memory.grow (i32.const 100000))) (i64.const 1)))'
WAT_ENV = '(module (import "wasi_snapshot_preview1" "fd_write" (func (param i32 i32 i32 i32) (result i32))) (func (export "run") (result i64) (i64.const 1)))'
WAT_OK = '(module (func (export "run") (result i64) (i64.const 42)))'


class Pin(unittest.TestCase):
    def test_lock_is_exact(self):
        text = LOCK.read_text()
        line = [l for l in text.splitlines() if l.startswith("wasmtime")][0]
        self.assertRegex(line, r"^wasmtime==\d+\.\d+\.\d+ --hash=sha256:")
        self.assertNotRegex(line, r"[<>~^*]")

    def test_backend_fails_closed_without_engine(self):
        b = ex.WasmBackend()
        if b.available:
            self.skipTest("engine present")
        self.assertEqual(b.execute(b"\0asm", limits={"fuel": 1, "max_memory_bytes": 65536}, caps=frozenset(),
                                   host={}, wall_clock_s=1, host_call_timeout_s=1),
                         {"trap": "backend unavailable", "fuel": 0})


class Engine(unittest.TestCase):
    def setUp(self):
        self.b = ex.WasmBackend()
        if not self.b.available:
            if REQUIRE:
                self.fail(f"pinned wasm engine required for certification: {self.b.reason}")
            self.skipTest(f"pinned engine unavailable: {self.b.reason}")
        self.wt = self.b.engine

    def go(self, wat, **kw):
        lim = {"fuel": 100_000, "max_memory_bytes": 1 << 20}
        return self.b.execute(self.wt.wat2wasm(wat), limits=lim, caps=kw.get("caps", frozenset()),
                              host=kw.get("host", {}), wall_clock_s=1, host_call_timeout_s=1)

    def test_ok(self):
        self.assertEqual(self.go(WAT_OK)["ok"], 42)

    def test_infinite_loop_bounded(self):
        self.assertIn(self.go(WAT_LOOP)["trap"], ("out of fuel", "deadline exceeded"))

    def test_memory_limit(self):
        self.assertEqual(self.go(WAT_MEM).get("ok"), 1)   # memory.grow returns -1, bounded

    def test_no_ambient_wasi(self):
        self.assertTrue(self.go(WAT_ENV)["trap"].startswith("capability denied"))

    def test_invalid_module(self):
        r = self.b.execute(b"not wasm", limits={"fuel": 1, "max_memory_bytes": 65536}, caps=frozenset(), host={},
                           wall_clock_s=1, host_call_timeout_s=1)
        self.assertEqual(r["trap"], "invalid module")


if __name__ == "__main__":
    unittest.main()
