"""Tiny WebAssembly binary builder for tests/fuzz seeds (no external tools)."""
from __future__ import annotations

I32, I64, F32, F64, FUNCREF, EXTERNREF, V128 = 0x7F, 0x7E, 0x7D, 0x7C, 0x70, 0x6F, 0x7B
HEADER = b"\x00asm\x01\x00\x00\x00"


def u(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def s(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        done = (n == 0 and not b & 0x40) or (n == -1 and b & 0x40)
        out.append(b if done else b | 0x80)
        if done:
            return bytes(out)


def vec(items) -> bytes:
    items = list(items)
    return u(len(items)) + b"".join(items)


def name(t: str) -> bytes:
    b = t.encode()
    return u(len(b)) + b


def section(sid: int, payload: bytes) -> bytes:
    return bytes([sid]) + u(len(payload)) + payload


def functype(params, results) -> bytes:
    return b"\x60" + vec(bytes([p]) for p in params) + vec(bytes([r]) for r in results)


def body(code: bytes, locals_=()) -> bytes:
    inner = vec(u(c) + bytes([t]) for c, t in locals_) + code
    return u(len(inner)) + inner


def module(types=(), imports=(), funcs=(), tables=(), mems=(), globals_=(), exports=(),
           start=None, elems=(), datacount=None, codes=(), datas=(), customs=()) -> bytes:
    out = bytearray(HEADER)
    for c in customs:
        out += section(0, name(c[0]) + c[1])
    if types:
        out += section(1, vec(functype(*t) for t in types))
    if imports:
        out += section(2, vec(imports))
    if funcs:
        out += section(3, vec(u(f) for f in funcs))
    if tables:
        out += section(4, vec(tables))
    if mems:
        out += section(5, vec(mems))
    if globals_:
        out += section(6, vec(globals_))
    if exports:
        out += section(7, vec(name(n) + bytes([k]) + u(i) for n, k, i in exports))
    if start is not None:
        out += section(8, u(start))
    if elems:
        out += section(9, vec(elems))
    if datacount is not None:
        out += section(12, u(datacount))
    if codes:
        out += section(10, vec(body(*c) if isinstance(c, tuple) else body(c) for c in codes))
    if datas:
        out += section(11, vec(datas))
    return bytes(out)


def add_module() -> bytes:
    """(func (export "add") (param i32 i32) (result i32) local.get 0 local.get 1 i32.add)"""
    return module(types=[((I32, I32), (I32,))], funcs=[0], exports=[("add", 0, 0)],
                  codes=[b"\x20\x00\x20\x01\x6a\x0b"])


def seeds() -> dict[str, bytes]:
    """Valid seed corpus covering each certified feature family."""
    mem = b"\x00" + u(1)
    return {
        "empty": HEADER,
        "add": add_module(),
        "float": module(types=[((F64, F64), (F64,))], funcs=[0], codes=[b"\x20\x00\x20\x01\xa0\x0b"]),
        "memory": module(types=[((I32,), (I32,))], funcs=[0], mems=[mem], exports=[("m", 2, 0)],
                         codes=[b"\x20\x00\x28\x02\x00\x0b"],
                         datas=[b"\x00\x41\x00\x0b" + u(3) + b"abc"]),
        "control": module(types=[((I32,), (I32,))], funcs=[0],
                          codes=[b"\x02\x7f\x41\x07\x20\x00\x0d\x00\x1a\x41\x09\x0b\x04\x7f\x41\x01\x05\x41\x02\x0b\x0b"]),
        "loop_br_table": module(types=[((I32,), ())], funcs=[0],
                                codes=[b"\x03\x40\x02\x40\x20\x00\x0e\x02\x00\x01\x00\x0b\x0b\x0b"]),
        "globals": module(types=[((), (I32,))], funcs=[0],
                          globals_=[bytes([I32, 1]) + b"\x41\x2a\x0b"],
                          codes=[b"\x23\x00\x41\x01\x6a\x24\x00\x23\x00\x0b"]),
        "multi_value": module(types=[((), (I32, I32))], funcs=[0], codes=[b"\x41\x01\x41\x02\x0b"]),
        "sign_ext": module(types=[((I32,), (I32,))], funcs=[0], codes=[b"\x20\x00\xc0\x0b"]),
        "sat": module(types=[((F32,), (I32,))], funcs=[0], codes=[b"\x20\x00\xfc\x00\x0b"]),
        "bulk": module(types=[((), ())], funcs=[0], mems=[mem], datacount=1,
                       codes=[b"\x41\x00\x41\x00\x41\x01\xfc\x08\x00\x00\xfc\x09\x00"
                              b"\x41\x00\x41\x00\x41\x00\xfc\x0a\x00\x00\x0b"],
                       datas=[b"\x01" + u(1) + b"z"]),
        "reftypes": module(types=[((), (I32,))], funcs=[0], tables=[bytes([FUNCREF]) + b"\x00\x01"],
                           exports=[("f", 0, 0)],
                           codes=[b"\xd2\x00\xd1\x0b"]),
        "call_indirect": module(types=[((), (I32,))], funcs=[0, 0], tables=[bytes([FUNCREF]) + b"\x00\x02"],
                                elems=[b"\x00\x41\x00\x0b" + vec([u(0), u(1)])],
                                codes=[b"\x41\x05\x0b", b"\x41\x00\x11\x00\x00\x0b"]),
        "wasi_import": module(types=[((I32, I32, I32, I32), (I32,))],
                              imports=[name("wasi_snapshot_preview1") + name("fd_write") + b"\x00\x00"]),
        "clock_import": module(types=[((I32, I64, I32), (I32,))],
                               imports=[name("wasi_snapshot_preview1") + name("clock_time_get") + b"\x00\x00"]),
        "custom": module(customs=[("name", b"\x00")], types=[((), ())], funcs=[0], codes=[b"\x0b"]),
        "start": module(types=[((), ())], funcs=[0], start=0, codes=[b"\x01\x0b"]),
        "unreachable_poly": module(types=[((), (I32,))], funcs=[0], codes=[b"\x00\x6a\x0b"]),
    }
