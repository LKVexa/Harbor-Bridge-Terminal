"""Tiny deterministic Wasm module assembler used by fixtures, tests and benchmarks.

Instructions are given as ``(opcode, immediate)`` pairs using the same immediate
shapes as :class:`production.wasm.Instr`.  Output is byte-for-byte deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .wasm import Instr, encode_body, section, uleb

I32, I64, F32, F64 = 0x7F, 0x7E, 0x7D, 0x7C


def _name(s: str) -> bytes:
    b = s.encode("utf-8")
    return uleb(len(b)) + b


def _limits(mn: int, mx: Optional[int]) -> bytes:
    return b"\x00" + uleb(mn) if mx is None else b"\x01" + uleb(mn) + uleb(mx)


@dataclass
class Func:
    params: tuple[int, ...]
    results: tuple[int, ...]
    body: list[tuple[Any, Any]]
    locals: list[tuple[int, int]] = field(default_factory=list)
    export: Optional[str] = None


@dataclass
class ModuleBuilder:
    funcs: list[Func] = field(default_factory=list)
    func_imports: list[tuple[str, str, tuple[int, ...], tuple[int, ...]]] = field(default_factory=list)
    memory: Optional[tuple[int, Optional[int]]] = (1, None)
    import_memory: Optional[tuple[str, str]] = None
    export_memory: Optional[str] = None
    table: Optional[tuple[int, Optional[int]]] = None
    elements: list[tuple[int, list[int]]] = field(default_factory=list)
    data: list[tuple[int, bytes]] = field(default_factory=list)
    globals: list[tuple[int, bool, int]] = field(default_factory=list)
    customs: list[tuple[str, bytes]] = field(default_factory=list)

    def add(self, f: Func) -> int:
        self.funcs.append(f)
        return len(self.func_imports) + len(self.funcs) - 1

    def build(self) -> bytes:
        types: list[tuple[tuple[int, ...], tuple[int, ...]]] = []

        def tidx(p: tuple[int, ...], r: tuple[int, ...]) -> int:
            if (p, r) not in types:
                types.append((p, r))
            return types.index((p, r))

        imp_idx = [tidx(p, r) for _, _, p, r in self.func_imports]
        fn_idx = [tidx(f.params, f.results) for f in self.funcs]
        out = [b"\x00asm\x01\x00\x00\x00"]
        out.append(section(1, uleb(len(types)) + b"".join(
            b"\x60" + uleb(len(p)) + bytes(p) + uleb(len(r)) + bytes(r) for p, r in types)))
        imports = [_name(m) + _name(n) + b"\x00" + uleb(t) for (m, n, _, _), t in zip(self.func_imports, imp_idx)]
        if self.import_memory and self.memory:
            imports.append(_name(self.import_memory[0]) + _name(self.import_memory[1]) + b"\x02"
                           + _limits(*self.memory))
        if imports:
            out.append(section(2, uleb(len(imports)) + b"".join(imports)))
        out.append(section(3, uleb(len(fn_idx)) + b"".join(uleb(t) for t in fn_idx)))
        if self.table:
            out.append(section(4, b"\x01\x70" + _limits(*self.table)))
        if self.memory and not self.import_memory:
            out.append(section(5, b"\x01" + _limits(*self.memory)))
        if self.globals:
            g = b"".join(bytes([vt, int(mut)]) + b"\x41" + _sleb(v) + b"\x0b" for vt, mut, v in self.globals)
            out.append(section(6, uleb(len(self.globals)) + g))
        exports = []
        base = len(self.func_imports)
        for i, f in enumerate(self.funcs):
            if f.export:
                exports.append(_name(f.export) + b"\x00" + uleb(base + i))
        if self.export_memory:
            exports.append(_name(self.export_memory) + b"\x02\x00")
        if exports:
            out.append(section(7, uleb(len(exports)) + b"".join(exports)))
        if self.elements:
            segs = b"".join(b"\x00\x41" + _sleb(off) + b"\x0b" + uleb(len(fs)) + b"".join(uleb(x) for x in fs)
                            for off, fs in self.elements)
            out.append(section(9, uleb(len(self.elements)) + segs))
        bodies = [encode_body(f.locals, [Instr(op, imm, -1) for op, imm in f.body]) for f in self.funcs]
        out.append(section(10, uleb(len(bodies)) + b"".join(bodies)))
        if self.data:
            segs = b"".join(b"\x00\x41" + _sleb(off) + b"\x0b" + uleb(len(d)) + d for off, d in self.data)
            out.append(section(11, uleb(len(self.data)) + segs))
        for nm, payload in self.customs:
            out.append(section(0, _name(nm) + payload))
        return b"".join(out)


def _sleb(n: int) -> bytes:
    from .wasm import sleb
    if n >= 1 << 31:
        n -= 1 << 32
    return sleb(n)


def rw_module(memory_pages: int = 4, import_memory: bool = False) -> bytes:
    """Canonical tenant module: load32(addr), store32(addr, v), load64/store64, f64 ops, sum loop."""
    b = ModuleBuilder(memory=(memory_pages, None), import_memory=("env", "memory") if import_memory else None)
    b.add(Func((I32,), (I32,), [(0x20, 0), (0x28, (2, 0)), (0x0B, None)], export="load"))
    b.add(Func((I32, I32), (), [(0x20, 0), (0x20, 1), (0x36, (2, 0)), (0x0B, None)], export="store"))
    b.add(Func((I32,), (I64,), [(0x20, 0), (0x29, (3, 16)), (0x0B, None)], export="load64_off16"))
    b.add(Func((I32, I64), (), [(0x20, 0), (0x20, 1), (0x37, (3, 8)), (0x0B, None)], export="store64_off8"))
    b.add(Func((I32, F64), (), [(0x20, 0), (0x20, 1), (0x39, (3, 0)), (0x0B, None)], export="storef64"))
    b.add(Func((I32,), (I32,), [(0x20, 0), (0x2D, (0, 0)), (0x0B, None)], export="load8u"))
    # sum(n): s=0; i=0; loop { s += load32(i*4); i++; br_if i<n }
    b.add(Func((I32,), (I32,), [
        (0x02, ()), (0x03, ()),
        (0x20, 2), (0x20, 1), (0x41, 2), (0x74, None), (0x28, (2, 0)), (0x6A, None), (0x21, 2),
        (0x20, 1), (0x41, 1), (0x6A, None), (0x22, 1), (0x20, 0), (0x48, None), (0x0D, 0),
        (0x0B, None), (0x0B, None), (0x20, 2), (0x0B, None)], locals=[(2, I32)], export="sum"))
    # fill(n): for i<n: store32(i*4, i)
    b.add(Func((I32,), (), [
        (0x02, ()), (0x03, ()),
        (0x20, 1), (0x41, 2), (0x74, None), (0x20, 1), (0x36, (2, 0)),
        (0x20, 1), (0x41, 1), (0x6A, None), (0x22, 1), (0x20, 0), (0x48, None), (0x0D, 0),
        (0x0B, None), (0x0B, None), (0x0B, None)], locals=[(1, I32)], export="fill"))
    return b.build()
