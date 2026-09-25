"""Hand-written instruction-family corpus.  Each case is judged against the
independent reference (V8) by test_prod.OracleCorpusTest, so expectations are
not self-graded; ``want`` is our expected code for readability/regressions."""
from wasmgen import F32, F64, FUNCREF, EXTERNREF, I32, I64, module, name, u, vec

MEM = b"\x00\x01"
TAB = bytes([FUNCREF]) + b"\x00\x02"
XTAB = bytes([EXTERNREF]) + b"\x00\x01"
GI32 = name("env") + name("g") + b"\x03" + bytes([I32, 0])


def f(code, params=(), results=(), **kw):
    kw.setdefault("types", [(params, results)])
    return module(funcs=[0], codes=[code], **kw)


#: Known, reviewed divergences from the V8 reference (spec-version gaps where we
#: are *stricter*; never a false accept).  See DIFFERENTIAL_DISPOSITIONS.md.
KNOWN_DIVERGENCE = {
    "g_local_global": "Wasm 2.0 const exprs may only global.get imported globals; V8 implements the "
                      "Wasm 3.0 relaxation. Pinned spec is wasm-core-2.0 -> stricter reject is correct.",
}

CASES = {
    # constant expressions
    "g_i64": (module(globals_=[bytes([I64, 0]) + b"\x42\x7f\x0b"]), "OK"),
    "g_f32": (module(globals_=[bytes([F32, 0]) + b"\x43\x00\x00\x80\x3f\x0b"]), "OK"),
    "g_f64": (module(globals_=[bytes([F64, 0]) + b"\x44" + b"\x00" * 8 + b"\x0b"]), "OK"),
    "g_imported": (module(imports=[GI32], globals_=[bytes([I32, 0]) + b"\x23\x00\x0b"]), "OK"),
    "g_local_global": (module(globals_=[bytes([I32, 0]) + b"\x41\x00\x0b", bytes([I32, 0]) + b"\x23\x00\x0b"]),
                       "INVALID_CONST_EXPR"),
    "g_refnull": (module(globals_=[bytes([EXTERNREF, 0]) + b"\xd0\x6f\x0b"]), "OK"),
    "g_reffunc": (module(types=[((), ())], funcs=[0], globals_=[bytes([FUNCREF, 0]) + b"\xd2\x00\x0b"],
                         codes=[b"\xd2\x00\x1a\x0b"]), "OK"),
    "g_reffunc_oob": (module(globals_=[bytes([FUNCREF, 0]) + b"\xd2\x05\x0b"]), "INVALID_CONST_EXPR"),
    "g_mut_import_get": (module(imports=[name("env") + name("g") + b"\x03" + bytes([I32, 1])],
                                globals_=[bytes([I32, 0]) + b"\x23\x00\x0b"]), "INVALID_CONST_EXPR"),
    "mut_global_export": (module(globals_=[bytes([I32, 1]) + b"\x41\x00\x0b"], exports=[("g", 3, 0)]), "OK"),
    # memory ops
    "mem_size_grow": (f(b"\x3f\x00\x40\x00\x0b", results=(I32,), mems=[MEM]), "OK"),
    "mem_grow_bad_reserved": (f(b"\x41\x00\x40\x01\x0b", results=(I32,), mems=[MEM]), "UNSUPPORTED_PROPOSAL"),
    "loads_stores": (f(b"\x41\x00\x41\x00\x29\x03\x00\x37\x03\x00"
                       b"\x41\x00\x41\x00\x2c\x00\x00\x3a\x00\x00"
                       b"\x41\x00\x44" + b"\x00" * 8 + b"\x39\x03\x08\x0b", mems=[MEM]), "OK"),
    "store_wrong_type": (f(b"\x41\x00\x42\x00\x36\x02\x00\x0b", mems=[MEM]), "TYPE_MISMATCH"),
    "memory_fill_copy": (f(b"\x41\x00\x41\x00\x41\x00\xfc\x0b\x00\x41\x00\x41\x00\x41\x00\xfc\x0a\x00\x00\x0b",
                           mems=[MEM]), "OK"),
    "data_flag2": (module(mems=[MEM], datas=[b"\x02\x00\x41\x00\x0b" + u(1) + b"a"]), "OK"),
    "data_bad_mem": (module(mems=[MEM], datas=[b"\x02\x01\x41\x00\x0b" + u(1) + b"a"]), "INVALID_INDEX"),
    "data_offset_type": (module(mems=[MEM], datas=[b"\x00\x42\x00\x0b" + u(1) + b"a"]), "TYPE_MISMATCH"),
    "datacount_mismatch": (module(mems=[MEM], datacount=2, datas=[b"\x01" + u(0)]), "COUNT_MISMATCH"),
    "data_drop": (f(b"\xfc\x09\x00\x0b", mems=[MEM], datacount=1, datas=[b"\x01" + u(0)]), "OK"),
    "data_drop_oob": (f(b"\xfc\x09\x01\x0b", mems=[MEM], datacount=1, datas=[b"\x01" + u(0)]), "INVALID_INDEX"),
    # tables / reference types
    "table_ops": (module(types=[((), (I32,))], funcs=[0], tables=[TAB], exports=[("f", 0, 0)],
                         codes=[b"\x41\x00\x25\x00\x1a\x41\x00\xd0\x70\x26\x00"
                                b"\xd0\x70\x41\x01\xfc\x0f\x00\x1a\xfc\x10\x00\x1a"
                                b"\x41\x00\xd0\x70\x41\x01\xfc\x11\x00\xfc\x10\x00\x0b"]), "OK"),
    "table_set_wrong": (f(b"\x41\x00\x41\x00\x26\x00\x0b", tables=[TAB]), "TYPE_MISMATCH"),
    "table_oob": (f(b"\xfc\x10\x03\x1a\x0b", tables=[TAB]), "INVALID_INDEX"),
    "externref_table": (f(b"\x41\x00\x25\x00\xd1\x1a\x0b", tables=[XTAB]), "OK"),
    "two_tables_call_indirect": (module(types=[((), ())], funcs=[0], tables=[TAB, TAB],
                                        codes=[b"\x41\x00\x11\x00\x01\x0b"]), "OK"),
    "call_indirect_extern": (module(types=[((), ())], funcs=[0], tables=[XTAB],
                                    codes=[b"\x41\x00\x11\x00\x00\x0b"]), "TYPE_MISMATCH"),
    "table_init_drop_copy": (module(types=[((), ())], funcs=[0], tables=[TAB],
                                    elems=[b"\x01\x00" + vec([u(0)])],
                                    codes=[b"\x41\x00\x41\x00\x41\x01\xfc\x0c\x00\x00\xfc\x0d\x00"
                                           b"\x41\x00\x41\x00\x41\x00\xfc\x0e\x00\x00\x0b"]), "OK"),
    "table_init_oob": (module(types=[((), ())], funcs=[0], tables=[TAB],
                              codes=[b"\x41\x00\x41\x00\x41\x01\xfc\x0c\x00\x00\x0b"]), "INVALID_INDEX"),
    "elem_drop_oob": (f(b"\xfc\x0d\x00\x0b"), "INVALID_INDEX"),
    "table_copy_mismatch": (f(b"\x41\x00\x41\x00\x41\x00\xfc\x0e\x00\x01\x0b", tables=[TAB, XTAB]),
                            "TYPE_MISMATCH"),
    "elem_exprs": (module(types=[((), ())], funcs=[0], tables=[TAB],
                          elems=[b"\x04\x41\x00\x0b" + vec([b"\xd2\x00\x0b", b"\xd0\x70\x0b"]),
                                 b"\x05\x70" + vec([b"\xd2\x00\x0b"]),
                                 b"\x06\x00\x41\x00\x0b\x70" + vec([b"\xd0\x70\x0b"]),
                                 b"\x07\x70" + vec([b"\xd2\x00\x0b"]),
                                 b"\x02\x00\x41\x00\x0b\x00" + vec([u(0)]),
                                 b"\x03\x00" + vec([u(0)])],
                          codes=[b"\x0b"]), "OK"),
    "elem_type_vs_table": (module(tables=[XTAB], elems=[b"\x06\x00\x41\x00\x0b\x70" + vec([b"\xd0\x70\x0b"])]),
                           "TYPE_MISMATCH"),
    "elem_bad_table": (module(types=[((), ())], funcs=[0], tables=[TAB],
                              elems=[b"\x02\x01\x41\x00\x0b\x00" + vec([u(0)])], codes=[b"\x0b"]), "INVALID_INDEX"),
    "elem_bad_func": (module(tables=[TAB], elems=[b"\x00\x41\x00\x0b" + vec([u(3)])]), "INVALID_INDEX"),
    "elem_bad_kind": (module(tables=[TAB], elems=[b"\x01\x01" + vec([])]), "MALFORMED"),
    "elem_flags8": (module(tables=[TAB], elems=[b"\x08"]), "MALFORMED"),
    "ref_func_declared_by_elem": (module(types=[((), ())], funcs=[0], elems=[b"\x03\x00" + vec([u(0)])],
                                         codes=[b"\xd2\x00\x1a\x0b"]), "OK"),
    "ref_is_null_num": (f(b"\x41\x00\xd1\x1a\x0b"), "TYPE_MISMATCH"),
    "typed_select": (f(b"\xd0\x6f\xd0\x6f\x41\x00\x1c\x01\x6f\x1a\x0b"), "OK"),
    "typed_select_two": (f(b"\x41\x00\x41\x00\x41\x00\x1c\x02\x7f\x7f\x1a\x0b"), "MALFORMED"),
    "typed_select_v128": (f(b"\x41\x00\x41\x00\x41\x00\x1c\x01\x7b\x1a\x0b"), "UNSUPPORTED_PROPOSAL"),
    # control / calls / locals
    "call": (module(types=[((I32,), (I32,))], funcs=[0, 0], codes=[b"\x20\x00\x0b", b"\x20\x00\x10\x00\x0b"]), "OK"),
    "call_oob": (f(b"\x10\x09\x0b"), "INVALID_INDEX"),
    "call_indirect_type_oob": (f(b"\x41\x00\x11\x05\x00\x0b", tables=[TAB]), "INVALID_INDEX"),
    "local_tee": (f((b"\x41\x05\x22\x00\x0b", [(1, I32)]), results=(I32,)), "OK"),
    "local_set_wrong": (f((b"\x42\x00\x21\x00\x0b", [(1, I32)])), "TYPE_MISMATCH"),
    "global_oob": (f(b"\x23\x04\x1a\x0b"), "INVALID_INDEX"),
    "block_typeidx": (module(types=[((), ()), ((I32, I32), (I32,))], funcs=[0],
                             codes=[b"\x41\x01\x41\x02\x02\x01\x6a\x0b\x1a\x0b"]), "OK"),
    "block_typeidx_oob": (f(b"\x02\x09\x0b\x0b"), "INVALID_INDEX"),
    "loop_params_br": (module(types=[((), ()), ((I32,), ())], funcs=[0],
                              codes=[b"\x41\x00\x03\x01\x0c\x00\x0b\x0b"]), "OK"),
    "if_else_params": (module(types=[((), (I32,)), ((I32,), (I32,))], funcs=[0],
                              codes=[b"\x41\x05\x41\x01\x04\x01\x05\x41\x01\x6a\x0b\x0b"]), "OK"),
    "br_if_values": (f(b"\x02\x7f\x41\x01\x41\x00\x0d\x00\x0b\x0b", results=(I32,)), "OK"),
    "br_table_ok": (f(b"\x02\x7f\x02\x7f\x41\x01\x41\x00\x0e\x01\x00\x01\x0b\x0b\x0b", results=(I32,)), "OK"),
    "return_values": (f(b"\x41\x01\x0f\x0b", results=(I32,)), "OK"),
    "nested_unreachable": (f(b"\x02\x7f\x00\x0b\x0b", results=(I32,)), "OK"),
    "unreachable_then_bad": (f(b"\x00\x41\x00\x42\x00\x6a\x1a\x0b"), "TYPE_MISMATCH"),
    "sat_all": (f(b"\x43\x00\x00\x00\x00\xfc\x01\x1a\x44" + b"\x00" * 8 + b"\xfc\x02\x1a"
                  b"\x44" + b"\x00" * 8 + b"\xfc\x07\x1a\x0b"), "OK"),
    "fc_unknown": (f(b"\xfc\x20\x0b"), "UNKNOWN_OPCODE"),
    "conversions": (f(b"\x42\x00\xa7\xac\xb9\xb6\xbb\xbd\xbf\xaa\x1a\x0b"), "OK"),
    "exceptions": (f(b"\x06\x40\x0b\x0b"), "UNSUPPORTED_PROPOSAL"),
    "memory64": (module(mems=[b"\x04\x01"]), "UNSUPPORTED_PROPOSAL"),
    "shared_no_max": (module(mems=[b"\x02\x01"]), "MALFORMED"),
    "tag_import": (module(types=[((), ())], imports=[name("e") + name("t") + b"\x04\x00\x00"]),
                   "UNSUPPORTED_PROPOSAL"),
    "import_all_kinds": (module(types=[((), ())], imports=[name("e") + name("f") + b"\x00\x00",
                                                           name("e") + name("t") + b"\x01" + TAB,
                                                           name("e") + name("m") + b"\x02" + MEM,
                                                           GI32]), "OK"),
    "import_bad_type": (module(types=[((), ())], imports=[name("e") + name("f") + b"\x00\x05"]), "INVALID_INDEX"),
    "start_oob": (module(types=[((), ())], start=3), "INVALID_INDEX"),
    "too_many_locals": (f((b"\x0b", [(0xFFFFFFFF, I32)])), "LIMIT_EXCEEDED"),
}
