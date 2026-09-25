"""Strict parser / validator tests (C021, C022, C026, C028, C046, C085 seed cases)."""
from __future__ import annotations

import unittest

from inv45_sfi_mechanisms.tests import support  # noqa: F401  (sys.path)
from inv45_sfi_mechanisms.production import builder, wasm
from inv45_sfi_mechanisms.production.builder import F32, F64, I32, I64, Func, ModuleBuilder
from inv45_sfi_mechanisms.production.errors import SfiError
from inv45_sfi_mechanisms.production.wasm import Limits, Reader

HDR = b"\x00asm\x01\x00\x00\x00"


def code(fn, *a, **k):
    try:
        fn(*a, **k)
    except SfiError as e:
        return e.code
    return "OK"


def one_func(body, params=(I32,), results=(I32,), locals_=None, memory=(4, None)):
    b = ModuleBuilder(memory=memory)
    b.add(Func(params, results, body, locals=locals_ or []))
    return b.build()


class LebTest(unittest.TestCase):
    def test_u32_bounds_and_unused_bits(self):
        self.assertEqual(Reader(b"\xff\xff\xff\xff\x0f").u32(), 0xFFFFFFFF)
        self.assertEqual(code(Reader(b"\xff\xff\xff\xff\x1f").u32), "SFI_MALFORMED_ARTIFACT")
        self.assertEqual(code(Reader(b"\x80\x80\x80\x80\x80\x00").u32), "SFI_MALFORMED_ARTIFACT")
        self.assertEqual(code(Reader(b"\x80").u32), "SFI_MALFORMED_ARTIFACT")

    def test_padded_encoding_accepted_like_engines(self):
        self.assertEqual(Reader(b"\x80\x00").u32(), 0)
        self.assertEqual(Reader(b"\x81\x80\x80\x80\x00").u32(), 1)

    def test_s32_s64_sign_rules(self):
        self.assertEqual(Reader(b"\x7f").sleb(32), -1)
        self.assertEqual(Reader(b"\xff\xff\xff\xff\x07").sleb(32), 0x7FFFFFFF)
        self.assertEqual(Reader(b"\x80\x80\x80\x80\x78").sleb(32), -(1 << 31))
        self.assertEqual(code(Reader(b"\xff\xff\xff\xff\x0f").sleb, 32), "SFI_MALFORMED_ARTIFACT")
        self.assertEqual(code(Reader(b"\x80" * 10 + b"\x00").sleb, 64), "SFI_MALFORMED_ARTIFACT")

    def test_roundtrip(self):
        for n in (0, 1, 63, 64, 127, 128, 2**31 - 1, -1, -64, -65, -(2**31), 2**40, -(2**63)):
            bits = 64 if abs(n) >= 2**31 and n != -(2**31) else 32
            self.assertEqual(Reader(wasm.sleb(n)).sleb(bits), n)
        for n in (0, 1, 127, 128, 2**32 - 1):
            self.assertEqual(Reader(wasm.uleb(n)).u32(), n)


class StructureTest(unittest.TestCase):
    def test_typical_module_parses(self):
        m = wasm.parse(builder.rw_module())
        self.assertEqual(len(m.functions), 8)
        self.assertEqual(m.all_memories(), [(4, None)])

    def test_header_errors(self):
        self.assertEqual(code(wasm.parse, b"\x00asn\x01\x00\x00\x00"), "SFI_MALFORMED_ARTIFACT")
        self.assertEqual(code(wasm.parse, b"\x00asm\x02\x00\x00\x00"), "SFI_UNSUPPORTED_VERSION")
        self.assertEqual(code(wasm.parse, b"\x00as"), "SFI_MALFORMED_ARTIFACT")
        self.assertEqual(code(wasm.parse, "not bytes"), "SFI_SCHEMA_INVALID")

    def test_section_rules(self):
        self.assertEqual(code(wasm.parse, HDR + b"\x01\x01\x00\x01\x01\x00"), "SFI_MALFORMED_ARTIFACT")  # dup
        self.assertEqual(code(wasm.parse, HDR + b"\x03\x01\x00\x01\x01\x00"), "SFI_MALFORMED_ARTIFACT")  # order
        self.assertEqual(code(wasm.parse, HDR + b"\x01\x05\x00"), "SFI_MALFORMED_ARTIFACT")  # size overrun
        self.assertEqual(code(wasm.parse, HDR + b"\x01\x02\x00\x00"), "SFI_MALFORMED_ARTIFACT")  # size slack
        self.assertEqual(code(wasm.parse, HDR + b"\x0d\x00"), "SFI_MALFORMED_ARTIFACT")
        self.assertEqual(code(wasm.parse, HDR + b"\x0c\x01\x00"), "SFI_UNSUPPORTED_FEATURE")  # datacount
        self.assertEqual(code(wasm.parse, HDR + b"\x03\x02\x01\x00"), "SFI_MALFORMED_ARTIFACT")  # no code sec

    def test_custom_section_utf8_and_limit(self):
        self.assertEqual(code(wasm.parse, HDR + b"\x00\x03\x02\xff\xfe"), "SFI_MALFORMED_ARTIFACT")
        big = b"x" * 2000
        payload = wasm.uleb(1) + b"n" + big
        self.assertEqual(code(wasm.parse, HDR + b"\x00" + wasm.uleb(len(payload)) + payload,
                              Limits(max_custom_section_bytes=1000)), "SFI_RESOURCE_LIMIT")

    def test_unsupported_features(self):
        cases = {
            "shared memory": HDR + b"\x05\x04\x01\x03\x01\x01",
            "memory64": HDR + b"\x05\x03\x01\x04\x01",
            "multi-value": HDR + b"\x01\x06\x01\x60\x00\x02\x7f\x7f",
            "simd valtype": HDR + b"\x01\x05\x01\x60\x01\x7b\x00",
            "passive data": HDR + b"\x05\x03\x01\x00\x01\x0b\x04\x01\x01\x01\x00",
        }
        for name, blob in cases.items():
            with self.subTest(name):
                self.assertEqual(code(wasm.parse, blob), "SFI_UNSUPPORTED_FEATURE")
        for op, name in ((0xFD, "simd"), (0xFE, "atomics"), (0x06, "exceptions"), (0x12, "tail call"),
                         (0xD0, "ref.null"), (0x25, "table.get")):
            with self.subTest(name):
                blob = one_func([(0x20, 0), (0x0B, None)])
                blob = blob.replace(b"\x20\x00\x0b", bytes([op]) + b"\x00\x0b")
                self.assertEqual(code(wasm.parse, blob), "SFI_UNSUPPORTED_FEATURE")
        blob = one_func([(0x20, 0), (0x0B, None)]).replace(b"\x20\x00\x0b", b"\xfc\x0a\x0b")  # memory.copy
        self.assertEqual(code(wasm.parse, blob), "SFI_UNSUPPORTED_FEATURE")

    def test_block_type_index_unsupported(self):
        blob = one_func([(0x20, 0), (0x0B, None)]).replace(b"\x20\x00\x0b", b"\x02\x00\x0b\x20\x00\x0b")
        self.assertEqual(code(wasm.parse, blob), "SFI_UNSUPPORTED_FEATURE")

    def test_sat_trunc_and_sign_ext_supported(self):
        wasm.parse(one_func([(0x20, 0), (0xB2, None), ((0xFC, 0), None), (0xC0, None), (0x0B, None)]))


class ValidationTest(unittest.TestCase):
    def bad(self, body, **kw):
        self.assertEqual(code(wasm.parse, one_func(body, **kw)), "SFI_INVALID_MODULE")

    def test_type_mismatches(self):
        self.bad([(0x20, 0), (0x0B, None)], results=(I64,))
        self.bad([(0x42, 1), (0x0B, None)])
        self.bad([(0x20, 0), (0x42, 1), (0x6A, None), (0x0B, None)])
        self.bad([(0x6A, None), (0x0B, None)])  # underflow
        self.bad([(0x20, 0), (0x20, 0), (0x0B, None)])  # leftover
        self.bad([(0x20, 5), (0x0B, None)])  # local oob
        self.bad([(0x10, 9), (0x0B, None)])  # call oob
        self.bad([(0x0C, 3), (0x0B, None)])  # br depth
        self.bad([(0x20, 0), (0x28, (3, 0)), (0x0B, None)])  # over-aligned
        self.bad([(0x20, 0), (0x28, (2, 0)), (0x0B, None)], memory=None)  # no memory
        self.bad([(0x20, 0), (0x11, 0), (0x0B, None)])  # call_indirect no table
        self.bad([(0x20, 0), (0x04, (I32,)), (0x41, 1), (0x0B, None), (0x0B, None)])  # if w/o else result

    def test_valid_control_flow_and_unreachable(self):
        wasm.parse(one_func([(0x02, (I32,)), (0x41, 1), (0x0C, 0), (0x0B, None), (0x0B, None)]))
        wasm.parse(one_func([(0x00, None), (0x6A, None), (0x0B, None)]))  # polymorphic stack
        wasm.parse(one_func([(0x20, 0), (0x04, (I32,)), (0x41, 1), (0x05, None), (0x41, 2), (0x0B, None),
                             (0x0B, None)]))
        wasm.parse(one_func([(0x02, ()), (0x20, 0), (0x0E, ([0, 0], 0)), (0x0B, None), (0x41, 0), (0x0B, None)]))
        wasm.parse(one_func([(0x20, 0), (0x44, b"\x00" * 8), (0x43, b"\x00" * 4), (0x1A, None), (0x1A, None),
                             (0x0B, None)]))

    def test_select_and_globals(self):
        b = ModuleBuilder(memory=None, globals=[(I32, True, 5), (I32, False, 1)])
        b.add(Func((), (I32,), [(0x23, 0), (0x41, 1), (0x6A, None), (0x24, 0), (0x23, 0), (0x0B, None)]))
        wasm.parse(b.build())
        b = ModuleBuilder(memory=None, globals=[(I32, False, 1)])
        b.add(Func((), (), [(0x41, 1), (0x24, 0), (0x0B, None)]))
        self.assertEqual(code(wasm.parse, b.build()), "SFI_INVALID_MODULE")
        wasm.parse(one_func([(0x44, b"\0" * 8), (0x44, b"\0" * 8), (0x20, 0), (0x1B, None), (0x1A, None),
                             (0x41, 0), (0x0B, None)]))


class LimitsTest(unittest.TestCase):
    """limit-1 / limit / limit+1 boundaries (C028)."""

    def test_module_bytes(self):
        blob = builder.rw_module()
        wasm.parse(blob, Limits(max_module_bytes=len(blob)))
        self.assertEqual(code(wasm.parse, blob, Limits(max_module_bytes=len(blob) - 1)), "SFI_RESOURCE_LIMIT")

    def test_function_count(self):
        b = ModuleBuilder(memory=None)
        for _ in range(10):
            b.add(Func((), (), [(0x0B, None)]))
        blob = b.build()
        wasm.parse(blob, Limits(max_functions=10))
        self.assertEqual(code(wasm.parse, blob, Limits(max_functions=9)), "SFI_RESOURCE_LIMIT")

    def test_nesting_and_instructions(self):
        body = [(0x02, ())] * 50 + [(0x0B, None)] * 51
        blob = one_func(body, params=(), results=())
        wasm.parse(blob, Limits(max_control_depth=51))
        self.assertEqual(code(wasm.parse, blob, Limits(max_control_depth=50)), "SFI_RESOURCE_LIMIT")
        self.assertEqual(code(wasm.parse, blob, Limits(max_total_instructions=100)), "SFI_RESOURCE_LIMIT")
        wasm.parse(blob, Limits(max_total_instructions=101))

    def test_br_table_and_locals(self):
        blob = one_func([(0x02, ()), (0x20, 0), (0x0E, ([0] * 100, 0)), (0x0B, None), (0x41, 0), (0x0B, None)])
        wasm.parse(blob, Limits(max_br_table_targets=100))
        self.assertEqual(code(wasm.parse, blob, Limits(max_br_table_targets=99)), "SFI_RESOURCE_LIMIT")
        blob = one_func([(0x20, 0), (0x0B, None)], locals_=[(1000, I32)])
        wasm.parse(blob, Limits(max_locals_per_function=1000))
        self.assertEqual(code(wasm.parse, blob, Limits(max_locals_per_function=999)), "SFI_RESOURCE_LIMIT")

    def test_br_table_with_deep_stack_is_linear(self):
        """Regression: 4.3.0-dev copied the operand stack per br_table target (quadratic)."""
        import time
        body = [(0x02, ())] + [(0x41, 1)] * 200_000 + [(0x41, 0), (0x0E, ([0] * 65_536, 0)), (0x0B, None),
                                                       (0x0B, None)]
        b = ModuleBuilder(memory=None)
        b.add(Func((), (), body))
        t0 = time.monotonic()
        wasm.parse(b.build())
        self.assertLess(time.monotonic() - t0, 5.0)

    def test_br_table_type_mismatch(self):
        def body(outer):
            return [(0x02, (outer,)), (0x02, (I32,)), (0x41, 1), (0x41, 0), (0x0E, ([0], 1)), (0x0B, None),
                    (0x1A, None), (0x42, 0) if outer == I64 else (0x41, 0), (0x0B, None), (0x1A, None),
                    (0x41, 0), (0x0B, None)]
        self.assertEqual(code(wasm.parse, one_func(body(I64))), "SFI_INVALID_MODULE")
        wasm.parse(one_func(body(I32)))

    def test_huge_declared_counts_fail_fast(self):
        # declares 2**32-1 types in a 5-byte payload: rejected before allocation
        self.assertEqual(code(wasm.parse, HDR + b"\x01\x05\xff\xff\xff\xff\x0f"), "SFI_RESOURCE_LIMIT")

    def test_deadline_and_cancel(self):
        blob = builder.rw_module()
        t = iter([0.0] + [100.0] * 10_000)
        self.assertEqual(code(wasm.parse, blob, Limits(deadline_seconds=1.0), clock=lambda: next(t)),
                         "SFI_DEADLINE_EXCEEDED")
        self.assertEqual(code(wasm.parse, blob, cancel=lambda: True), "SFI_CANCELLED")


class EncodeTest(unittest.TestCase):
    def test_encode_decode_roundtrip_all_float_types(self):
        blob = one_func([(0x20, 0), (0xB7, None), (0xB6, None), (0xBB, None), (0xAA, None), (0x0B, None)])
        m = wasm.parse(blob)
        fn = m.functions[0]
        self.assertEqual(wasm.encode_body(fn.locals, fn.body), wasm.split_sections(blob)[-1][1][1:])
        _ = (F32, F64)


if __name__ == "__main__":
    unittest.main()
