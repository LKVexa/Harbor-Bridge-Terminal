"""MC-001 WIT surface gate, MC-002 runtime adapter (real V8 engine), MC-019 negotiation."""
import copy, datetime, json, shutil, unittest
import _fx
from inv13_system_interface.host import wit_surface as ws, wasm_loader as w, compat
from inv13_system_interface.host.errors import ErrorCode, Inv13Error

ROOT = _fx.ROOT / "inv13_system_interface"
I32, I64 = w.I32, w.I64


def hello_module(imports=(("inv13:stdio@4.3.0", "stdout-write"),), body=b"\x41\x00\x41\x05\x10\x00"):
    return w.build_module([([I32, I32], [I32]), ([], [I32])], [(m, n, 0) for m, n in imports],
                          [(1, [], body)], [("memory", 2, 0), ("run", 0, len(imports))], 1, [(0, b"hello")])


class WitSurface(unittest.TestCase):
    def test_lock_and_approved_surface_match(self):
        cur = ws.surface()
        lock = json.loads((ROOT / "WIT.lock").read_text())
        self.assertEqual(lock["sha256"], cur["sha256"])
        self.assertEqual(cur["version"], "4.3.0")
        self.assertEqual(ws.diff(json.loads((ROOT / "APPROVED_SURFACE.json").read_text()), cur), [])

    def test_gate_detects_authority_expansion_and_breaks(self):
        approved = ws.surface()
        cur = copy.deepcopy(approved)
        cur["worlds"]["minimal"]["imports"].append("sockets")
        cur["worlds"]["minimal"]["capabilities"].append("sockets")
        cur["interfaces"]["random"]["get-random-bytes"] = "func(len: u64) -> list<u8>"
        probs = ws.diff(approved, cur)
        self.assertTrue(any("minimal adds imports" in p for p in probs))
        self.assertTrue(any("breaking: random.get-random-bytes" in p for p in probs))

    def test_parser_rejects_unversioned_and_undeclared(self):
        with self.assertRaises(ValueError):
            ws.parse("package inv13:x;\ninterface stdio { f: func(); }")
        with self.assertRaises(ValueError):
            ws.parse("package inv13:x@1.0.0;\nworld w { import ghost; }")

    def test_worlds_are_least_privilege(self):
        s = ws.surface()["worlds"]
        self.assertEqual(s["minimal"]["capabilities"], ["stdio"])
        self.assertNotIn("filesystem", s["http-client"]["capabilities"])
        self.assertNotIn("sockets", s["batch-file-worker"]["capabilities"])
        self.assertTrue(all(len(v["capabilities"]) < 8 for v in s.values()))  # no all-powerful world


class WasmLoader(unittest.TestCase):
    def test_parse_and_map(self):
        info = w.parse(hello_module())
        self.assertEqual(info.imports, (("inv13:stdio@4.3.0", "stdout-write", "func"),))
        self.assertEqual(w.required_capabilities(info), {"stdio"})

    def test_undeclared_import_rejected_before_engine(self):
        for mod in (hello_module([("wasi_snapshot_preview1", "fd_write")]),
                    hello_module([("inv13:random@4.3.0", "get-random-bytes")])):
            with self.assertRaises(Inv13Error) as cm:
                w.admit(mod, {"stdio"})
            self.assertEqual(cm.exception.code, ErrorCode.CAP_NOT_GRANTED)

    def test_malformed_and_component_and_digest(self):
        for bad in (b"", b"\0asx\1\0\0\0", b"\0asm\2\0\0\0", hello_module()[:-3], b"\0asm\1\0\0\0\x02\xff\xff\xff\xff\x7f"):
            with self.assertRaises(Inv13Error):
                w.admit(bad, {"stdio"})
        comp = w.MAGIC + w.COMPONENT_VERSION
        with self.assertRaises(Inv13Error) as cm:
            w.admit(comp, {"stdio"})
        self.assertEqual(cm.exception.code, ErrorCode.UNSUPPORTED_VERSION)
        with self.assertRaises(Inv13Error) as cm:
            w.admit(hello_module(), {"stdio"}, allowed_digests={"0" * 64})
        self.assertEqual(cm.exception.code, ErrorCode.POLICY_DENIED)


@unittest.skipUnless(shutil.which("node"), "node (V8) not installed")
class V8Adapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from inv13_system_interface.host import runtime_adapter as ra
        cls.ra = ra
        cls.ad = ra.RuntimeAdapter(ra.V8NodeEngine())

    def test_granted_world_runs_in_real_engine(self):
        res = self.ad.instantiate_and_run(hello_module(), {"stdio"})
        self.assertEqual(res["stdout"], b"hello")
        self.assertTrue(res["engine"].startswith("v8 "))

    def test_ungranted_capability_never_reaches_engine(self):
        with self.assertRaises(Inv13Error):
            self.ad.instantiate_and_run(hello_module(), {"random"})

    def test_random_and_clock_bound_only_when_granted(self):
        # type0 (i32,i32)->i32 random ; type1 ()->i32 run ; type2 ()->i64 monotonic
        mod = w.build_module([([I32, I32], [I32]), ([], [I32]), ([], [I64])],
                             [("inv13:random@4.3.0", "get-random-bytes", 0), ("inv13:clocks@4.3.0", "monotonic-now", 2)],
                             [(1, [], b"\x10\x01\x1a\x41\x10\x41\x20\x10\x00")],
                             [("memory", 2, 0), ("run", 0, 2)], 1)
        res = self.ad.instantiate_and_run(mod, {"random", "monotonic-clock"})
        self.assertEqual(res["result"], "32")
        with self.assertRaises(Inv13Error):
            self.ad.instantiate_and_run(mod, {"random"})

    def test_out_of_bounds_request_refused_by_host_function(self):
        body = b"\x41\xf0\xff\x03\x41\x80\x02\x10\x00"   # get-random-bytes(65520, 256) -> beyond 1 page
        mod = w.build_module([([I32, I32], [I32]), ([], [I32])], [("inv13:random@4.3.0", "get-random-bytes", 0)],
                             [(1, [], body)], [("memory", 2, 0), ("run", 0, 1)], 1)
        self.assertEqual(self.ad.instantiate_and_run(mod, {"random"})["result"], "-1")

    def test_trap_maps_to_stable_code_without_detail(self):
        mod = w.build_module([([], [I32])], [], [(0, [], b"\x00")], [("memory", 2, 0), ("run", 0, 0)], 1)
        with self.assertRaises(Inv13Error) as cm:
            self.ad.instantiate_and_run(mod, set())
        self.assertEqual(cm.exception.code, ErrorCode.INTERNAL)
        self.assertNotIn("wasm", json.dumps(cm.exception.to_guest()))

    def test_timeout(self):
        loop = w.build_module([([], [I32])], [], [(0, [], b"\x03\x40\x0c\x00\x0b\x41\x00")],
                              [("memory", 2, 0), ("run", 0, 0)], 1)
        with self.assertRaises(Inv13Error) as cm:
            self.ad.instantiate_and_run(loop, set(), timeout=1.5)
        self.assertEqual(cm.exception.code, ErrorCode.TIMED_OUT)


class Negotiation(unittest.TestCase):
    def test_negotiate(self):
        d = datetime.date(2026, 9, 22)
        self.assertEqual(compat.negotiate(["inv13:system-interface@4.3.0"], today=d), "inv13:system-interface@4.3.0")
        self.assertEqual(compat.negotiate(["inv13:system-interface@4.1.0"], today=d), "inv13:system-interface@4.3.0")
        for bad in (["inv13:system-interface@5.0.0"], ["inv13:system-interface@4.4.0"], ["other:pkg@4.3.0"], []):
            with self.assertRaises(Inv13Error):
                compat.negotiate(bad, today=d)
        with self.assertRaises(Inv13Error):   # past EOL
            compat.negotiate(["inv13:system-interface@4.2.0"], today=datetime.date(2028, 1, 1))


if __name__ == "__main__":
    unittest.main()
