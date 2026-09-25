"""Dependency-free security and correctness tests for the INV-70 runtime."""
import importlib
import importlib.util
import pathlib
import sys
import unittest

RUNTIME = pathlib.Path(__file__).resolve().parents[1] / "runtime.py"
spec = importlib.util.spec_from_file_location("inv70_runtime", RUNTIME)
rt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rt)


class EvilInt(int):
    touched = False
    def __add__(self, other):
        type(self).touched = True
        return 1


class RuntimeTest(unittest.TestCase):


    def test_non_finite_values_are_rejected(self):
        for value in (float("inf"), float("-inf"), float("nan")):
            with self.subTest(value=value):
                self.assertEqual(rt.run([("push", value), ("halt",)]), {"trap": "invalid value", "fuel": 1})
        out = rt.run([("push", 1), ("call", "x"), ("halt",)], caps={"x"}, host={"x": lambda _: float("inf")})
        self.assertEqual(out["trap"], "invalid value")

    def test_normal_package_import_works_without_core_framework(self):
        pkg_dir = pathlib.Path(__file__).resolve().parents[1]
        parent = str(pkg_dir.parent)
        if parent not in sys.path:
            sys.path.insert(0, parent)
        pkg = importlib.import_module(pkg_dir.name)
        self.assertEqual(pkg.__version__, "4.3.0")
        self.assertTrue(callable(pkg.run))
        self.assertEqual(pkg.run([("push", 2), ("halt",)]), {"ok": 2, "fuel": 2})

    def test_nominal_arithmetic_and_operand_order(self):
        self.assertEqual(rt.run([("push", 2), ("push", 3), ("mul",), ("push", 4), ("add",), ("halt",)]),
                         {"ok": 10, "fuel": 6})
        self.assertEqual(rt.run([("push", "a"), ("push", "b"), ("add",), ("halt",)]),
                         {"ok": "ab", "fuel": 4})

    def test_fuel_and_stack_limits(self):
        self.assertEqual(rt.run([("jmp", 0)], fuel=5), {"trap": "out of fuel", "fuel": 5})
        out = rt.run([("push", 1), ("dup",), ("jmp", 1)], fuel=100, max_stack=3)
        self.assertEqual(out, {"trap": "out of memory", "fuel": 6})

    def test_logical_memory_and_value_limits(self):
        out = rt.run([("push", "x" * 100), ("halt",)], max_memory_bytes=128, max_value_bytes=128)
        self.assertEqual(out, {"trap": "value too large", "fuel": 1})
        out = rt.run([("push", "x" * 20), ("dup",), ("halt",)], max_memory_bytes=120, max_value_bytes=100)
        self.assertEqual(out["trap"], "out of memory")

    def test_malformed_instructions_have_precise_traps(self):
        cases = [
            ([("push",)], "invalid instruction"),
            ([("halt", 1)], "invalid instruction"),
            ([("bogus",)], "invalid instruction"),
            ([("jmp", "0")], "invalid jump target"),
            ([("jmp", 9)], "invalid jump target"),
            ([("call", "")], "invalid capability"),
            ([("call", "bad\nname")], "invalid capability"),
            ([("call", "x" * 129)], "invalid capability"),
            (["push"], "invalid instruction"),
        ]
        for program, reason in cases:
            with self.subTest(program=program):
                self.assertEqual(rt.run(program), {"trap": reason, "fuel": 0})

    def test_stack_underflow_is_runtime_not_shape_error(self):
        self.assertEqual(rt.run([("add",), ("halt",)]), {"trap": "stack underflow", "fuel": 1})

    def test_guest_object_magic_methods_cannot_execute(self):
        EvilInt.touched = False
        out = rt.run([("push", EvilInt(1)), ("push", 2), ("add",), ("halt",)])
        self.assertEqual(out, {"trap": "invalid value", "fuel": 0})
        self.assertFalse(EvilInt.touched)

    def test_capability_gate_unbound_invalid_and_host_error(self):
        denied = rt.run([("push", "p"), ("call", "read"), ("halt",)], host={"read": lambda p: "secret"})
        self.assertEqual(denied["trap"], "capability denied: read")
        unbound = rt.run([("push", 1), ("call", "x"), ("halt",)], caps={"x"})
        self.assertEqual(unbound["trap"], "capability unbound: x")
        invalid = rt.run([("push", 1), ("call", "x"), ("halt",)], caps={"x"}, host={"x": 3})
        self.assertEqual(invalid["trap"], "capability invalid: x")
        failed = rt.run([("push", 1), ("call", "x"), ("halt",)], caps={"x"},
                        host={"x": lambda _: (_ for _ in ()).throw(RuntimeError("secret=abc"))})
        self.assertEqual(failed["trap"], "host error: RuntimeError")
        self.assertNotIn("secret", failed["trap"])

    def test_host_result_is_revalidated(self):
        out = rt.run([("push", 1), ("call", "x"), ("halt",)], caps={"x"}, host={"x": lambda _: object()})
        self.assertEqual(out["trap"], "invalid value")

    def test_configuration_validation(self):
        for kwargs in ({"fuel": -1}, {"fuel": True}, {"max_stack": -1}, {"max_memory_bytes": 1, "max_value_bytes": 2}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                rt.run([("halt",)], **kwargs)
        with self.assertRaises(ValueError):
            rt.run([("halt",)], caps={1})
        with self.assertRaises(ValueError):
            rt.run([("halt",)], caps="read")
        with self.assertRaises(ValueError):
            rt.run([("halt",)], host=[])

    def test_bounded_string_repeat_and_integer_multiply(self):
        out = rt.run([("push", "x"), ("push", 10_000), ("mul",), ("halt",)],
                     max_memory_bytes=1024, max_value_bytes=1000)
        self.assertEqual(out["trap"], "value too large")
        a = 1 << 1000
        out = rt.run([("push", a), ("push", a), ("mul",), ("halt",)],
                     max_memory_bytes=512, max_value_bytes=200)
        self.assertEqual(out["trap"], "value too large")


if __name__ == "__main__":
    unittest.main()
