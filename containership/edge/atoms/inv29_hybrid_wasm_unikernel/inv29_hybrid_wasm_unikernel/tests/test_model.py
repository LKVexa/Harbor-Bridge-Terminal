"""Standalone security and correctness tests; no pk_core dependency."""
import importlib.util
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("inv29_model", PKG_DIR / "model.py")
assert _spec and _spec.loader
_model = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _model
_spec.loader.exec_module(_model)
HostImage = _model.HostImage
ImportUnsatisfied = _model.ImportUnsatisfied
LayerMissing = _model.LayerMissing
WasmModule = _model.WasmModule
compose = _model.compose
verify = _model.verify


class ModelTest(unittest.TestCase):
    def setUp(self):
        self.host = HostImage("host", frozenset({"clock", "net-send"}))
        self.module = WasmModule("svc", frozenset({"clock"}))

    def test_valid_composition(self):
        record = compose(self.module, self.host)
        self.assertEqual(record["schema"], "PK_HYBRID_COMPOSITION/1")
        self.assertEqual(record["layer_count"], 2)
        self.assertTrue(record["verification"]["verified"])

    def test_verify_interface(self):
        record = verify(self.module, self.host)
        self.assertEqual(record["schema"], "PK_HYBRID_VERIFICATION/1")
        self.assertTrue(record["layers"]["unikernel"]["verified"])
        self.assertTrue(record["layers"]["wasm"]["verified"])

    def test_unsatisfied_import_refused(self):
        with self.assertRaises(ImportUnsatisfied):
            compose(WasmModule("svc", frozenset({"raw-socket"})), self.host)

    def test_either_layer_failure_refused(self):
        with self.assertRaises(LayerMissing):
            compose(self.module, HostImage("host", frozenset({"clock"}), sealed=False))
        with self.assertRaises(LayerMissing):
            compose(WasmModule("svc", frozenset({"clock"}), hardened=False), self.host)

    def test_unsupported_architectures_refused(self):
        with self.assertRaises(LayerMissing):
            compose(WasmModule("svc", frozenset(), architecture="x86_64"), self.host)
        with self.assertRaises(LayerMissing):
            compose(self.module, HostImage("host", frozenset({"clock"}), architecture="mips"))

    def test_required_layers_cannot_be_lowered_or_bool(self):
        for value in (0, 1, True, False, 1.5, "2"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                compose(self.module, self.host, required_layers=value)

    def test_higher_environmental_layer_requirement_refuses(self):
        with self.assertRaises(LayerMissing):
            compose(self.module, self.host, required_layers=3)

    def test_capabilities_must_be_frozenset_of_nonempty_strings(self):
        with self.assertRaises(TypeError):
            compose(WasmModule("svc", {"clock"}), self.host)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            compose(WasmModule("svc", frozenset({1})), self.host)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            compose(WasmModule("svc", frozenset({""})), self.host)

    def test_names_must_be_nonempty(self):
        with self.assertRaises(ValueError):
            compose(WasmModule(" ", frozenset()), self.host)

    def test_input_size_limits(self):
        with self.assertRaises(ValueError):
            compose(WasmModule("x" * 257, frozenset()), self.host)
        with self.assertRaises(ValueError):
            compose(WasmModule("svc", frozenset({"x" * 257})), self.host)
        with self.assertRaises(ValueError):
            compose(WasmModule("svc", frozenset(f"cap-{i}" for i in range(4097))), self.host)


if __name__ == "__main__":
    unittest.main()
