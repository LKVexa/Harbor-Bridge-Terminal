"""P0-01..P0-04: pk_core pin/probe, WASI adapter, versioned contracts, INV-15 bridge."""
import json, os, pathlib, sys, textwrap, threading, time, unittest
from _support import PKG_DIR, tmpdir
import core_probe, wasi_adapter, schema_check, migration, polling, clock


def _fake_core(root, version="1.2.3", drop=None):
    pk = pathlib.Path(root) / "pk_core"
    pk.mkdir(parents=True)
    (pk / "__init__.py").write_text(f'__version__ = "{version}"\n')
    mods = {"contract": "class Contract: pass\nclass Dependency: pass\nclass Slo: pass\n",
            "checklist": "class ChecklistItem: pass\nclass Finding: pass\n",
            "component": "class Component: pass\n"}
    for m, src in mods.items():
        if drop == m:
            src = src.split("\n")[0] + "\n"
        (pk / f"{m}.py").write_text(src)
    return pk


class C01PkCorePin(unittest.TestCase):
    def setUp(self):
        self._path = list(sys.path)
        for m in [m for m in sys.modules if m.startswith("pk_core")]:
            del sys.modules[m]

    def tearDown(self):
        sys.path[:] = self._path
        for m in [m for m in sys.modules if m.startswith("pk_core")]:
            del sys.modules[m]

    def _lock(self, **core):
        base = {"name": "pk_core", "status": "RESOLVED", "version": "1.2.3", "source": "https://index.example/pk_core",
                "tree_sha256": "0" * 64}
        base.update(core)
        return {"schema": "PK_CORE_LOCK/1", "python_requires": ">=3.8,<4.99", "pk_core": base}

    def test_c01_shipped_lock_is_unresolved_and_probe_fails_closed(self):
        r = core_probe.probe()
        self.assertFalse(r["ok"])
        self.assertEqual(r["code"], "PK_CORE_UNPINNED")

    def test_c01_floating_and_mutable_pins_rejected(self):
        self.assertIn("PK_CORE_FLOATING_VERSION", core_probe.validate_lock(self._lock(version="latest")))
        self.assertIn("PK_CORE_FLOATING_VERSION", core_probe.validate_lock(self._lock(version=">=1.0")))
        self.assertIn("PK_CORE_MUTABLE_SOURCE", core_probe.validate_lock(self._lock(source="/home/x/pk_core")))
        self.assertIn("PK_CORE_MUTABLE_SOURCE", core_probe.validate_lock(self._lock(source="C:\\pk")))
        self.assertIn("PK_CORE_NO_DIGEST", core_probe.validate_lock(self._lock(tree_sha256="abc")))

    def test_c01_probe_absent_version_hash_api_ok_paths(self):
        d = tmpdir()
        pk = _fake_core(d)
        lock = self._lock(tree_sha256=core_probe.tree_digest(pk))
        self.assertEqual(core_probe.probe(lock)["code"], "PK_CORE_ABSENT")
        sys.path.insert(0, d)
        r = core_probe.probe(lock)
        self.assertTrue(r["ok"], r)
        self.assertNotIn(d, json.dumps(r))  # no local path disclosure
        self.assertEqual(core_probe.probe(self._lock(version="9.9.9", tree_sha256=lock["pk_core"]["tree_sha256"]))["code"],
                         "PK_CORE_VERSION_MISMATCH")
        self.assertEqual(core_probe.probe(self._lock(tree_sha256="1" * 64))["code"], "PK_CORE_HASH_MISMATCH")
        self.assertEqual(core_probe.probe(dict(lock, python_requires=">=9.0"))["code"], "PK_CORE_INTERPRETER")

    def test_c01_api_incompatible_core_refused(self):
        d = tmpdir()
        pk = _fake_core(d, drop="checklist")
        sys.path.insert(0, d)
        r = core_probe.probe(self._lock(tree_sha256=core_probe.tree_digest(pk)))
        self.assertEqual(r["code"], "PK_CORE_API_INCOMPATIBLE")

    def test_c01_tree_digest_is_deterministic_and_ignores_bytecode(self):
        d = tmpdir()
        pk = _fake_core(d)
        a = core_probe.tree_digest(pk)
        (pk / "__pycache__").mkdir()
        (pk / "__pycache__" / "x.pyc").write_bytes(b"junk")
        self.assertEqual(a, core_probe.tree_digest(pk))
        (pk / "contract.py").write_text("changed")
        self.assertNotEqual(a, core_probe.tree_digest(pk))


class C02WasiAdapter(unittest.TestCase):
    def setUp(self):
        self.h = wasi_adapter.ReferenceWasiHost()
        self.a, self.b = self.h.new_pollable("o"), self.h.new_pollable("o")
        self.ad = wasi_adapter.WasiPollAdapter(self.h, "o")

    def test_c02_timeout_maps_timer_index_to_timed_out(self):
        t0 = time.monotonic()
        r = self.ad.poll(["a", "b"], [self.a, self.b], timeout_ticks=30)
        self.assertTrue(r["timed_out"])
        self.assertGreaterEqual(time.monotonic() - t0, 0.025)
        self.assertEqual(schema_check.check(r, "pk_poll.schema.json"), [])

    def test_c02_ready_indexes_exclude_timer_and_match_python_semantics(self):
        self.h.set_ready(self.b)
        r = self.ad.poll(["a", "b"], [self.a, self.b], timeout_ticks=30)
        self.assertEqual((r["ready"], r["ready_indexes"], r["timed_out"]), (["b"], [1], False))

    def test_c02_late_readiness_wakes_poll(self):
        threading.Timer(0.02, self.h.set_ready, args=(self.a,)).start()
        r = self.ad.poll(["a", "b"], [self.a, self.b], timeout_ticks=2000)
        self.assertEqual(r["ready"], ["a"])

    def test_c02_empty_set_refused_before_trap_and_timer_dropped(self):
        with self.assertRaises(polling.PollValidationError) as cm:
            self.ad.poll([], [], timeout_ticks=5)
        self.assertEqual(cm.exception.code, "PK_POLL_EMPTY_SET")
        live = set(self.h.live)
        self.ad.poll(["a"], [self.a], timeout_ticks=1)
        self.assertEqual(self.h.live, live)  # timer handle released

    def test_c02_foreign_duplicate_and_limit_refusals(self):
        f = self.h.new_pollable("other")
        with self.assertRaises(polling.ForeignPollable):
            self.ad.poll(["a", "f"], [self.a, f], timeout_ticks=5)
        for names, hs, code in ((["a", "a"], [self.a, self.b], "PK_POLL_DUPLICATE_NAME"),
                                (["a", "b"], [self.a, self.a], "PK_POLL_DUPLICATE_HANDLE"),
                                (["a"], [self.a, self.b], "PK_POLL_INVALID_SET")):
            with self.assertRaises(polling.PollValidationError) as cm:
                self.ad.poll(names, hs, timeout_ticks=5)
            self.assertEqual(cm.exception.code, code)
        with self.assertRaises(polling.PollValidationError) as cm:
            self.ad.poll(["a"], [self.a], timeout_ticks=60_001)
        self.assertEqual(cm.exception.code, "PK_POLL_TIMEOUT_LIMIT")

    def test_c02_tick_to_wasi_duration_is_exact_integer(self):
        self.assertEqual(clock.ticks_to_ns(250, clock.DEFAULT_CLOCK_CONFIG), 250_000_000)

    def test_c02_runtime_detection_reports_without_claiming(self):
        d = wasi_adapter.detect_runtimes()
        self.assertFalse(d["compiled_fixture"])
        self.assertEqual(set(d), {"wasmtime_cli", "wasmtime_py", "jco", "wasm_tools", "compiled_fixture"})


class C03Contracts(unittest.TestCase):
    def test_c03_generated_contracts_are_current(self):
        import subprocess
        r = subprocess.run([sys.executable, "-B", str(PKG_DIR / "tools" / "gen_contracts.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_c03_wit_records_match_json_schemas(self):
        import re
        wit = (PKG_DIR / "wit" / "inv14-legacy-poll.wit").read_text()
        pairs = {"poll-result": "pk_poll.schema.json", "poll-metrics": "pk_poll_metrics.schema.json",
                 "pollable-descriptor": "pk_pollable.schema.json", "poll-error": "pk_poll_error.schema.json"}
        for rec, sch in pairs.items():
            body = re.search(r"record %s \{(.*?)\n  \}" % rec, wit, re.S).group(1)
            wit_fields = {l.strip().split(":")[0].replace("-", "_") for l in body.splitlines() if ":" in l}
            required = set(schema_check.load_schema(sch)["required"])
            if rec == "poll-error":
                required -= {"details"}  # details are JSON-only; WIT carries the code enum
            self.assertEqual(wit_fields, required, rec)

    def test_c03_error_schema_enum_equals_code_registry(self):
        reg = json.loads((PKG_DIR / "schemas" / "error_codes.json").read_text())
        enum = schema_check.load_schema("pk_poll_error.schema.json")["properties"]["code"]["enum"]
        self.assertEqual(sorted(enum), sorted(c["code"] for c in reg["codes"]))

    def test_c03_every_schema_is_versioned(self):
        for p in (PKG_DIR / "schemas").glob("*.schema.json"):
            s = json.loads(p.read_text())
            self.assertEqual(s.get("x-version"), "4.3.0", p.name)
            self.assertIn("/1", s["$id"], p.name)

    def test_c03_validator_fails_closed_on_unknown_keyword(self):
        self.assertTrue(schema_check.validate(1, {"type": "integer", "multipleOf": 2}))


class C04Migration(unittest.TestCase):
    def test_c04_parity_between_legacy_and_shim(self):
        r = migration.parity_check()
        self.assertTrue(r["equivalent"], r)

    def test_c04_reverse_shim_signals_once_from_inv15_future(self):
        f = migration.SimpleFuture()
        fp = migration.FuturePollable("fut", "t/c/i", f)
        threading.Timer(0.01, f.set_result).start()
        r = polling.PollSet("t/c/i").poll([fp], timeout_ticks=2000)
        self.assertEqual(r["ready"], ["fut"])
        f.set_result()  # idempotent
        f2 = migration.SimpleFuture(); f2.set_result()
        self.assertTrue(migration.FuturePollable("done", "t/c/i", f2).is_ready())

    def test_c04_state_machine_requires_parity_and_allows_rollback(self):
        m = migration.MigrationStateMachine("svc-a")
        self.assertEqual(m.advance(actor="ops"), "DUAL_STACK")
        with self.assertRaises(migration.MigrationError) as cm:
            m.advance(actor="ops")
        self.assertEqual(cm.exception.code, "PK_MIGRATION_PARITY_REQUIRED")
        m.record_parity({"equivalent": False})
        with self.assertRaises(migration.MigrationError):
            m.advance(actor="ops")
        m.record_parity(migration.parity_check())
        self.assertEqual(m.advance(actor="ops"), "CANARY")
        self.assertEqual(m.rollback(actor="ops", reason="error spike"), "ROLLED_BACK")
        self.assertEqual(m.advance(actor="ops"), "DUAL_STACK")
        m.record_parity({"equivalent": True}); m.advance(actor="ops")
        m.record_parity({"equivalent": True}); self.assertEqual(m.advance(actor="ops"), "MIGRATED")
        with self.assertRaises(migration.MigrationError) as cm:
            m.rollback(actor="ops", reason="x")
        self.assertEqual(cm.exception.code, "PK_MIGRATION_ROLLBACK")
        with self.assertRaises(migration.MigrationError):
            m.advance(actor="ops")

    def test_c04_forward_shim_cancel_is_idempotent(self):
        f = migration.PollableFuture(polling.Pollable("x", "t/c/i"), "t/c/i")
        self.assertTrue(f.cancel()); self.assertFalse(f.cancel())
        self.assertFalse(f.wait(0.01)); self.assertFalse(f.done())
        with self.assertRaises(migration.MigrationError):
            migration.PollableFuture("nope", "t/c/i")


if __name__ == "__main__":
    unittest.main()
