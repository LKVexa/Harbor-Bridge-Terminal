"""Strict WebAssembly binary parser, validator and encoder (production profile).

This is the parsing/validation half of the INV-45 enforcement boundary (C046, A3).
It operates on the exact artifact bytes and implements:

* bounds-checked LEB128 decoding with the specification's length and unused-bit
  rules (padded encodings that engines accept are accepted, so the verifier and
  the engine cannot disagree about where an instruction starts); artifact
  identity is always the SHA-256 of the exact bytes, never of a decoded form;
* strict section ordering, exact section-size consumption, duplicate rejection;
* the WebAssembly 1.0 (MVP) instruction set plus the sign-extension and
  non-trapping float-to-int proposals, and nothing else - every other feature is
  ``SFI_UNSUPPORTED_FEATURE`` (profile ``PK-SFI-WASM32-MVP-1``, ADR-0001);
* complete operand/control-stack type validation following the algorithm in the
  WebAssembly specification appendix, so that the SFI verifier's local pattern
  checks rest on a validated stack discipline;
* resource limits and a cooperative deadline enforced *before* and *during*
  expensive work (C028).

Only the standard library is used.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .errors import SfiError

I32, I64, F32, F64 = 0x7F, 0x7E, 0x7D, 0x7C
VALTYPES = {I32: "i32", I64: "i64", F32: "f32", F64: "f64"}
FUNCREF = 0x70
UNKNOWN = None  # polymorphic stack slot

SECTION_ORDER = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 11, 11: 12}
SECTION_NAMES = {0: "custom", 1: "type", 2: "import", 3: "function", 4: "table", 5: "memory",
                 6: "global", 7: "export", 8: "start", 9: "element", 10: "code", 11: "data", 12: "datacount"}

# opcode -> (value type, access width bytes, is_store)
MEMORY_OPS: dict[int, tuple[int, int, bool]] = {
    0x28: (I32, 4, False), 0x29: (I64, 8, False), 0x2A: (F32, 4, False), 0x2B: (F64, 8, False),
    0x2C: (I32, 1, False), 0x2D: (I32, 1, False), 0x2E: (I32, 2, False), 0x2F: (I32, 2, False),
    0x30: (I64, 1, False), 0x31: (I64, 1, False), 0x32: (I64, 2, False), 0x33: (I64, 2, False),
    0x34: (I64, 4, False), 0x35: (I64, 4, False),
    0x36: (I32, 4, True), 0x37: (I64, 8, True), 0x38: (F32, 4, True), 0x39: (F64, 8, True),
    0x3A: (I32, 1, True), 0x3B: (I32, 2, True), 0x3C: (I64, 1, True), 0x3D: (I64, 2, True),
    0x3E: (I64, 4, True),
}
MAX_ACCESS_WIDTH = 8


def _numeric_table() -> dict[Any, tuple[tuple[int, ...], tuple[int, ...]]]:
    t: dict[Any, tuple[tuple[int, ...], tuple[int, ...]]] = {}

    def rng(a: int, b: int, sig: tuple[tuple[int, ...], tuple[int, ...]]) -> None:
        for op in range(a, b + 1):
            t[op] = sig

    rng(0x45, 0x45, ((I32,), (I32,)))
    rng(0x46, 0x4F, ((I32, I32), (I32,)))
    rng(0x50, 0x50, ((I64,), (I32,)))
    rng(0x51, 0x5A, ((I64, I64), (I32,)))
    rng(0x5B, 0x60, ((F32, F32), (I32,)))
    rng(0x61, 0x66, ((F64, F64), (I32,)))
    rng(0x67, 0x69, ((I32,), (I32,)))
    rng(0x6A, 0x78, ((I32, I32), (I32,)))
    rng(0x79, 0x7B, ((I64,), (I64,)))
    rng(0x7C, 0x8A, ((I64, I64), (I64,)))
    rng(0x8B, 0x91, ((F32,), (F32,)))
    rng(0x92, 0x98, ((F32, F32), (F32,)))
    rng(0x99, 0x9F, ((F64,), (F64,)))
    rng(0xA0, 0xA6, ((F64, F64), (F64,)))
    conv = {
        0xA7: (I64, I32), 0xA8: (F32, I32), 0xA9: (F32, I32), 0xAA: (F64, I32), 0xAB: (F64, I32),
        0xAC: (I32, I64), 0xAD: (I32, I64), 0xAE: (F32, I64), 0xAF: (F32, I64), 0xB0: (F64, I64),
        0xB1: (F64, I64), 0xB2: (I32, F32), 0xB3: (I32, F32), 0xB4: (I64, F32), 0xB5: (I64, F32),
        0xB6: (F64, F32), 0xB7: (I32, F64), 0xB8: (I32, F64), 0xB9: (I64, F64), 0xBA: (I64, F64),
        0xBB: (F32, F64), 0xBC: (F32, I32), 0xBD: (F64, I64), 0xBE: (I32, F32), 0xBF: (I64, F64),
        0xC0: (I32, I32), 0xC1: (I32, I32), 0xC2: (I64, I64), 0xC3: (I64, I64), 0xC4: (I64, I64),
    }
    for op, (a, r) in conv.items():
        t[op] = ((a,), (r,))
    sat = {0: (F32, I32), 1: (F32, I32), 2: (F64, I32), 3: (F64, I32),
           4: (F32, I64), 5: (F32, I64), 6: (F64, I64), 7: (F64, I64)}
    for sub, (a, r) in sat.items():
        t[(0xFC, sub)] = ((a,), (r,))
    return t


NUMERIC = _numeric_table()


@dataclass(frozen=True)
class Limits:
    """Parser/validator resource ceilings (C028).  Secure bounds are enforced in config."""

    max_module_bytes: int = 16 * 1024 * 1024
    max_types: int = 10_000
    max_imports: int = 1_000
    max_functions: int = 100_000
    max_globals: int = 10_000
    max_exports: int = 10_000
    max_table_elems: int = 100_000
    max_data_segments: int = 10_000
    max_function_body_bytes: int = 1_048_576
    max_locals_per_function: int = 50_000
    max_params: int = 1_000
    max_control_depth: int = 1_024
    max_br_table_targets: int = 65_536
    max_total_instructions: int = 5_000_000
    max_custom_section_bytes: int = 1_048_576
    max_name_bytes: int = 1_024
    deadline_seconds: float = 10.0


@dataclass
class Instr:
    op: Any  # int, or (0xFC, sub)
    imm: Any
    offset: int  # byte offset of the opcode inside the module


@dataclass
class FuncType:
    params: tuple[int, ...]
    results: tuple[int, ...]


@dataclass
class Import:
    module: str
    name: str
    kind: int  # 0 func, 1 table, 2 memory, 3 global
    desc: Any


@dataclass
class Global:
    valtype: int
    mutable: bool
    init: list[Instr]


@dataclass
class Function:
    type_index: int
    locals: list[tuple[int, int]]  # (count, valtype) runs as encoded
    body: list[Instr]
    body_offset: int

    def local_types(self, ftype: FuncType) -> list[int]:
        out = list(ftype.params)
        for n, t in self.locals:
            out.extend([t] * n)
        return out


@dataclass
class Module:
    types: list[FuncType] = field(default_factory=list)
    imports: list[Import] = field(default_factory=list)
    func_types: list[int] = field(default_factory=list)  # defined functions' type indices
    tables: list[tuple[int, Optional[int]]] = field(default_factory=list)  # defined tables (min,max)
    memories: list[tuple[int, Optional[int]]] = field(default_factory=list)  # defined memories
    globals: list[Global] = field(default_factory=list)
    exports: list[tuple[str, int, int]] = field(default_factory=list)
    start: Optional[int] = None
    elements: list[tuple[list[Instr], list[int]]] = field(default_factory=list)
    functions: list[Function] = field(default_factory=list)
    data: list[tuple[list[Instr], bytes]] = field(default_factory=list)
    customs: list[tuple[str, bytes]] = field(default_factory=list)
    section_ids: list[int] = field(default_factory=list)
    instruction_count: int = 0

    # --- index spaces -------------------------------------------------------------
    @property
    def imported_funcs(self) -> list[Import]:
        return [i for i in self.imports if i.kind == 0]

    @property
    def imported_globals(self) -> list[Import]:
        return [i for i in self.imports if i.kind == 3]

    def all_func_types(self) -> list[FuncType]:
        return [self.types[i.desc] for i in self.imported_funcs] + [self.types[t] for t in self.func_types]

    def all_globals(self) -> list[tuple[int, bool]]:
        return [i.desc for i in self.imported_globals] + [(g.valtype, g.mutable) for g in self.globals]

    def all_memories(self) -> list[tuple[int, Optional[int]]]:
        return [i.desc for i in self.imports if i.kind == 2] + list(self.memories)

    def all_tables(self) -> list[tuple[int, Optional[int]]]:
        return [i.desc for i in self.imports if i.kind == 1] + list(self.tables)


class _Budget:
    def __init__(self, limits: Limits, clock: Callable[[], float], cancel: Optional[Callable[[], bool]]):
        self.limits = limits
        self.clock = clock
        self.cancel = cancel
        self.deadline = clock() + limits.deadline_seconds
        self.ticks = 0

    def tick(self, n: int = 1) -> None:
        self.ticks += n
        if self.ticks & 0x3FF == 0 or n > 1:
            self.check()

    def check(self) -> None:
        if self.cancel is not None and self.cancel():
            raise SfiError("SFI_CANCELLED", "parse cancelled by caller")
        if self.clock() > self.deadline:
            raise SfiError("SFI_DEADLINE_EXCEEDED", "parse/validation deadline exceeded",
                           limit=self.limits.deadline_seconds)


class Reader:
    def __init__(self, data: bytes, pos: int = 0, end: Optional[int] = None):
        self.data = data
        self.pos = pos
        self.end = len(data) if end is None else end

    def _malformed(self, reason: str) -> SfiError:
        return SfiError("SFI_MALFORMED_ARTIFACT", f"malformed module: {reason}", reason=reason,
                        instruction_offset=self.pos)

    def eof(self) -> bool:
        return self.pos >= self.end

    def byte(self) -> int:
        if self.pos >= self.end:
            raise self._malformed("unexpected end of data")
        b = self.data[self.pos]
        self.pos += 1
        return b

    def bytes(self, n: int) -> bytes:
        if n < 0 or self.pos + n > self.end:
            raise self._malformed("length exceeds enclosing bounds")
        out = self.data[self.pos:self.pos + n]
        self.pos += n
        return bytes(out)

    def u32(self) -> int:
        result = shift = 0
        for i in range(5):
            b = self.byte()
            result |= (b & 0x7F) << shift
            if not b & 0x80:
                if i == 4 and b & 0x70:
                    raise self._malformed("u32 LEB128 unused bits set")
                return result
            shift += 7
        raise self._malformed("u32 LEB128 too long")

    def sleb(self, bits: int) -> int:
        maxlen = (bits + 6) // 7
        result = shift = 0
        for i in range(maxlen):
            b = self.byte()
            result |= (b & 0x7F) << shift
            shift += 7
            if not b & 0x80:
                if i == maxlen - 1:
                    # remaining high bits must be a sign extension of bit (bits-1)
                    used = bits - 7 * (maxlen - 1)
                    rest = (b & 0x7F) >> (used - 1)
                    if rest not in (0, (0x7F >> (used - 1))):
                        raise self._malformed(f"s{bits} LEB128 unused bits not sign extension")
                if b & 0x40:
                    result -= 1 << shift
                return result
        raise self._malformed(f"s{bits} LEB128 too long")

    def name(self, limits: Limits) -> str:
        n = self.u32()
        if n > limits.max_name_bytes:
            raise SfiError("SFI_RESOURCE_LIMIT", "name too long", limit=limits.max_name_bytes, observed=n)
        raw = self.bytes(n)
        try:
            return raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise self._malformed("name is not valid UTF-8") from None


def _unsupported(feature: str, **kw: Any) -> SfiError:
    return SfiError("SFI_UNSUPPORTED_FEATURE", f"unsupported Wasm feature: {feature}", feature=feature, **kw)


def _limit(name: str, limit: int, observed: int) -> None:
    if observed > limit:
        raise SfiError("SFI_RESOURCE_LIMIT", f"{name} exceeds limit", field=name, limit=limit, observed=observed)


def _valtype(r: Reader) -> int:
    t = r.byte()
    if t not in VALTYPES:
        if t in (0x7B, 0x70, 0x6F):
            raise _unsupported("simd/reference-types value type", opcode=t)
        raise r._malformed(f"invalid value type 0x{t:02x}")
    return t


def _limits(r: Reader, what: str) -> tuple[int, Optional[int]]:
    flag = r.byte()
    if flag == 0x00:
        return r.u32(), None
    if flag == 0x01:
        mn, mx = r.u32(), r.u32()
        if mx < mn:
            raise SfiError("SFI_INVALID_MODULE", f"{what} max < min", field=what)
        return mn, mx
    if flag in (0x02, 0x03):
        raise _unsupported("threads/shared memory", field=what)
    raise _unsupported(f"limits flag 0x{flag:02x} (memory64/custom page sizes)", field=what)


def _blocktype(r: Reader) -> tuple[int, ...]:
    b = r.data[r.pos] if r.pos < r.end else None
    if b == 0x40:
        r.pos += 1
        return ()
    if b in VALTYPES:
        r.pos += 1
        return (b,)
    raise _unsupported("multi-value / type-indexed block types")


def _decode_instr(r: Reader, limits: Limits) -> Instr:
    off = r.pos
    op = r.byte()
    if op in (0x02, 0x03, 0x04):
        return Instr(op, _blocktype(r), off)
    if op in (0x0C, 0x0D, 0x10, 0x20, 0x21, 0x22, 0x23, 0x24):
        return Instr(op, r.u32(), off)
    if op == 0x0E:
        n = r.u32()
        _limit("br_table targets", limits.max_br_table_targets, n)
        labels = [r.u32() for _ in range(n)]
        return Instr(op, (labels, r.u32()), off)
    if op == 0x11:
        ti = r.u32()
        tb = r.byte()
        if tb != 0x00:
            raise _unsupported("call_indirect table index != 0 (reference types)")
        return Instr(op, ti, off)
    if op in MEMORY_OPS:
        align, offset = r.u32(), r.u32()
        return Instr(op, (align, offset), off)
    if op in (0x3F, 0x40):
        if r.byte() != 0x00:
            raise _unsupported("multi-memory")
        return Instr(op, None, off)
    if op == 0x41:
        return Instr(op, r.sleb(32), off)
    if op == 0x42:
        return Instr(op, r.sleb(64), off)
    if op == 0x43:
        return Instr(op, r.bytes(4), off)
    if op == 0x44:
        return Instr(op, r.bytes(8), off)
    if op in (0x00, 0x01, 0x05, 0x0B, 0x0F, 0x1A, 0x1B) or op in NUMERIC:
        return Instr(op, None, off)
    if op == 0xFC:
        sub = r.u32()
        if (0xFC, sub) in NUMERIC:
            return Instr((0xFC, sub), None, off)
        raise _unsupported("bulk-memory/reference-types 0xFC prefix", opcode=f"0xfc {sub}")
    if op == 0x1C:
        raise _unsupported("typed select (reference types)")
    if op in (0x25, 0x26, 0xD0, 0xD1, 0xD2):
        raise _unsupported("table/reference instructions", opcode=f"0x{op:02x}")
    if op in (0x06, 0x07, 0x08, 0x09, 0x0A, 0x18, 0x19, 0x1F):
        raise _unsupported("exception handling", opcode=f"0x{op:02x}")
    if op in (0x12, 0x13, 0x14, 0x15):
        raise _unsupported("tail calls / typed function references", opcode=f"0x{op:02x}")
    if op == 0xFD:
        raise _unsupported("SIMD")
    if op == 0xFE:
        raise _unsupported("threads/atomics")
    if op == 0xFB:
        raise _unsupported("GC")
    raise SfiError("SFI_MALFORMED_ARTIFACT", f"unknown opcode 0x{op:02x}", opcode=f"0x{op:02x}",
                   instruction_offset=off)


def _const_expr(r: Reader, limits: Limits) -> list[Instr]:
    out = []
    while True:
        ins = _decode_instr(r, limits)
        out.append(ins)
        if ins.op == 0x0B:
            return out
        if len(out) > 2:
            raise SfiError("SFI_INVALID_MODULE", "constant expression too long")


def parse(data: bytes, limits: Limits = Limits(), *, clock: Callable[[], float] = time.monotonic,
          cancel: Optional[Callable[[], bool]] = None, validate_types: bool = True) -> Module:
    """Parse and (by default) fully validate ``data``.  Raises :class:`SfiError` only."""
    if not isinstance(data, (bytes, bytearray)):
        raise SfiError("SFI_SCHEMA_INVALID", "artifact must be bytes", field="artifact")
    data = bytes(data)
    _limit("module bytes", limits.max_module_bytes, len(data))
    budget = _Budget(limits, clock, cancel)
    try:
        module = _parse(data, limits, budget)
        if validate_types:
            validate(module, limits, budget)
        return module
    except SfiError:
        raise
    except RecursionError:
        raise SfiError("SFI_RESOURCE_LIMIT", "nesting too deep", field="nesting") from None
    except (IndexError, ValueError, KeyError, TypeError, OverflowError) as exc:
        # A parser defect must fail closed with a stable code, never a raw exception.
        raise SfiError("SFI_MALFORMED_ARTIFACT", "malformed module (internal decode guard)",
                       reason=type(exc).__name__) from None


def _parse(data: bytes, limits: Limits, budget: _Budget) -> Module:
    r = Reader(data)
    if r.bytes(4) != b"\x00asm":
        raise r._malformed("bad magic")
    version = r.bytes(4)
    if version != b"\x01\x00\x00\x00":
        raise SfiError("SFI_UNSUPPORTED_VERSION", "unsupported Wasm binary version",
                       expected_version=1, observed_version=int.from_bytes(version, "little"))
    m = Module()
    last_order = 0
    func_count_decl: Optional[int] = None
    custom_total = 0
    while not r.eof():
        sid = r.byte()
        size = r.u32()
        start = r.pos
        if start + size > len(data):
            raise r._malformed("section size exceeds module")
        s = Reader(data, start, start + size)
        if sid == 0:
            nm = s.name(limits)
            custom_total += size
            _limit("custom section bytes", limits.max_custom_section_bytes, custom_total)
            m.customs.append((nm, s.bytes(s.end - s.pos)))
        else:
            if sid == 12:
                raise _unsupported("bulk memory (datacount section)", section="datacount")
            if sid not in SECTION_ORDER:
                raise r._malformed(f"unknown section id {sid}")
            order = SECTION_ORDER[sid]
            if order <= last_order:
                raise r._malformed(f"section {SECTION_NAMES[sid]} out of order or duplicated")
            last_order = order
            m.section_ids.append(sid)
            _parse_section(sid, s, m, limits, budget)
            if sid == 3:
                func_count_decl = len(m.func_types)
            if s.pos != s.end:
                raise r._malformed(f"section {SECTION_NAMES[sid]} size mismatch")
        r.pos = start + size
        budget.check()
    if (func_count_decl or 0) != len(m.functions):
        raise r._malformed("function and code section counts differ")
    return m


def _parse_section(sid: int, s: Reader, m: Module, limits: Limits, budget: _Budget) -> None:
    if sid == 1:
        n = s.u32()
        _limit("types", limits.max_types, n)
        for _ in range(n):
            if s.byte() != 0x60:
                raise s._malformed("function type must start with 0x60")
            np_ = s.u32()
            _limit("params", limits.max_params, np_)
            params = tuple(_valtype(s) for _ in range(np_))
            nr = s.u32()
            _limit("results", limits.max_params, nr)
            results = tuple(_valtype(s) for _ in range(nr))
            if len(results) > 1:
                raise _unsupported("multi-value results")
            m.types.append(FuncType(params, results))
    elif sid == 2:
        n = s.u32()
        _limit("imports", limits.max_imports, n)
        for _ in range(n):
            mod, nm = s.name(limits), s.name(limits)
            kind = s.byte()
            if kind == 0:
                desc: Any = s.u32()
            elif kind == 1:
                if s.byte() != FUNCREF:
                    raise _unsupported("non-funcref table")
                desc = _limits(s, "table")
            elif kind == 2:
                desc = _limits(s, "memory")
            elif kind == 3:
                vt = _valtype(s)
                mut = s.byte()
                if mut not in (0, 1):
                    raise s._malformed("bad global mutability")
                desc = (vt, bool(mut))
            else:
                raise _unsupported(f"import kind {kind}")
            m.imports.append(Import(mod, nm, kind, desc))
    elif sid == 3:
        n = s.u32()
        _limit("functions", limits.max_functions, n)
        m.func_types = [s.u32() for _ in range(n)]
    elif sid == 4:
        n = s.u32()
        for _ in range(n):
            if s.byte() != FUNCREF:
                raise _unsupported("non-funcref table")
            m.tables.append(_limits(s, "table"))
    elif sid == 5:
        n = s.u32()
        for _ in range(n):
            m.memories.append(_limits(s, "memory"))
    elif sid == 6:
        n = s.u32()
        _limit("globals", limits.max_globals, n)
        for _ in range(n):
            vt = _valtype(s)
            mut = s.byte()
            if mut not in (0, 1):
                raise s._malformed("bad global mutability")
            m.globals.append(Global(vt, bool(mut), _const_expr(s, limits)))
    elif sid == 7:
        n = s.u32()
        _limit("exports", limits.max_exports, n)
        for _ in range(n):
            nm = s.name(limits)
            kind = s.byte()
            if kind > 3:
                raise s._malformed("bad export kind")
            m.exports.append((nm, kind, s.u32()))
    elif sid == 8:
        m.start = s.u32()
    elif sid == 9:
        n = s.u32()
        total = 0
        for _ in range(n):
            flags = s.u32()
            if flags != 0:
                raise _unsupported("non-MVP element segment (bulk memory / reference types)")
            off = _const_expr(s, limits)
            k = s.u32()
            total += k
            _limit("table elements", limits.max_table_elems, total)
            m.elements.append((off, [s.u32() for _ in range(k)]))
    elif sid == 10:
        n = s.u32()
        _limit("functions", limits.max_functions, n)
        for _ in range(n):
            size = s.u32()
            _limit("function body bytes", limits.max_function_body_bytes, size)
            body_start = s.pos
            if body_start + size > s.end:
                raise s._malformed("function body exceeds code section")
            b = Reader(s.data, body_start, body_start + size)
            nruns = b.u32()
            runs = []
            total = 0
            for _ in range(nruns):
                cnt = b.u32()
                total += cnt
                _limit("locals per function", limits.max_locals_per_function, total)
                runs.append((cnt, _valtype(b)))
            instrs = []
            depth = 1
            while True:
                ins = _decode_instr(b, limits)
                instrs.append(ins)
                budget.tick()
                m.instruction_count += 1
                if m.instruction_count > limits.max_total_instructions:
                    raise SfiError("SFI_RESOURCE_LIMIT", "too many instructions", field="instructions",
                                   limit=limits.max_total_instructions)
                if ins.op in (0x02, 0x03, 0x04):
                    depth += 1
                    _limit("control depth", limits.max_control_depth, depth)
                elif ins.op == 0x0B:
                    depth -= 1
                    if depth == 0:
                        break
            if b.pos != b.end:
                raise s._malformed("function body size mismatch")
            m.functions.append(Function(0, runs, instrs, body_start))
            s.pos = body_start + size
    elif sid == 11:
        n = s.u32()
        _limit("data segments", limits.max_data_segments, n)
        for _ in range(n):
            flags = s.u32()
            if flags != 0:
                raise _unsupported("passive/explicit-memory data segment (bulk memory)")
            off = _const_expr(s, limits)
            ln = s.u32()
            m.data.append((off, s.bytes(ln)))


# ------------------------------------------------------------------------------ validation

def _invalid(msg: str, **kw: Any) -> SfiError:
    return SfiError("SFI_INVALID_MODULE", f"invalid module: {msg}", reason=msg, **kw)


def _const_type(m: Module, expr: list[Instr], expect: int, imported_globals_only: bool = True) -> None:
    if len(expr) != 2 or expr[1].op != 0x0B:
        raise _invalid("constant expression must be a single instruction followed by end")
    ins = expr[0]
    types = {0x41: I32, 0x42: I64, 0x43: F32, 0x44: F64}
    if ins.op in types:
        t = types[ins.op]
    elif ins.op == 0x23:
        g = m.imported_globals
        if ins.imm >= len(g):
            raise _invalid("constant global.get must reference an imported global")
        t, mut = g[ins.imm].desc
        if mut:
            raise _invalid("constant global.get must reference an immutable global")
    else:
        raise _invalid("non-constant instruction in constant expression")
    if t != expect:
        raise _invalid("constant expression type mismatch")


def validate(m: Module, limits: Limits = Limits(), budget: Optional[_Budget] = None) -> None:
    budget = budget or _Budget(limits, time.monotonic, None)
    nt = len(m.types)
    for imp in m.imports:
        if imp.kind == 0 and imp.desc >= nt:
            raise _invalid("import type index out of range")
    for ti in m.func_types:
        if ti >= nt:
            raise _invalid("function type index out of range")
    if len(m.all_tables()) > 1:
        raise _unsupported("multiple tables")
    if len(m.all_memories()) > 1:
        raise _unsupported("multi-memory")
    for mn, mx in m.all_memories():
        if mn > 65536 or (mx is not None and mx > 65536):
            raise _invalid("memory size exceeds 4 GiB")
    for g in m.globals:
        _const_type(m, g.init, g.valtype)
    ftypes = m.all_func_types()
    nfuncs = len(ftypes)
    names = set()
    for nm, kind, idx in m.exports:
        if nm in names:
            raise _invalid("duplicate export name")
        names.add(nm)
        bound = {0: nfuncs, 1: len(m.all_tables()), 2: len(m.all_memories()), 3: len(m.all_globals())}[kind]
        if idx >= bound:
            raise _invalid("export index out of range")
    if m.start is not None:
        if m.start >= nfuncs:
            raise _invalid("start function out of range")
        st = ftypes[m.start]
        if st.params or st.results:
            raise _invalid("start function must have type [] -> []")
    for off, funcs in m.elements:
        if not m.all_tables():
            raise _invalid("element segment without table")
        _const_type(m, off, I32)
        if any(f >= nfuncs for f in funcs):
            raise _invalid("element function index out of range")
    for off, _ in m.data:
        if not m.all_memories():
            raise _invalid("data segment without memory")
        _const_type(m, off, I32)
    nimp = len(m.imported_funcs)
    for i, fn in enumerate(m.functions):
        fn.type_index = m.func_types[i]
        _validate_function(m, fn, ftypes, nimp + i, limits, budget)


def _validate_function(m: Module, fn: Function, ftypes: list[FuncType], fidx: int, limits: Limits,
                       budget: _Budget) -> None:
    ft = m.types[fn.type_index]
    locals_ = fn.local_types(ft)
    globals_ = m.all_globals()
    has_mem = bool(m.all_memories())
    has_table = bool(m.all_tables())
    vals: list[Optional[int]] = []
    ctrls: list[dict[str, Any]] = []

    def err(msg: str, ins: Instr) -> SfiError:
        return _invalid(msg, function_index=fidx, instruction_offset=ins.offset)

    def push(t: Optional[int]) -> None:
        vals.append(t)

    def pop(ins: Instr, expect: Optional[int] = UNKNOWN) -> Optional[int]:
        f = ctrls[-1]
        if len(vals) == f["height"]:
            if f["unreachable"]:
                return expect
            raise err("operand stack underflow", ins)
        actual = vals.pop()
        if actual is not UNKNOWN and expect is not UNKNOWN and actual != expect:
            raise err(f"type mismatch: expected {VALTYPES[expect]} got {VALTYPES[actual]}", ins)
        return actual if actual is not UNKNOWN else expect

    def pops(ins: Instr, types: tuple[int, ...]) -> None:
        for t in reversed(types):
            pop(ins, t)

    def push_ctrl(op: int, start: tuple[int, ...], end: tuple[int, ...]) -> None:
        ctrls.append({"op": op, "start": start, "end": end, "height": len(vals), "unreachable": False})
        for t in start:
            push(t)

    def pop_ctrl(ins: Instr) -> dict[str, Any]:
        if not ctrls:
            raise err("control stack underflow", ins)
        f = ctrls[-1]
        pops(ins, f["end"])
        if len(vals) != f["height"]:
            raise err("values remain on stack at end of block", ins)
        ctrls.pop()
        return f

    def label_types(f: dict[str, Any]) -> tuple[int, ...]:
        return f["start"] if f["op"] == 0x03 else f["end"]

    def unreachable() -> None:
        del vals[ctrls[-1]["height"]:]
        ctrls[-1]["unreachable"] = True

    def label(ins: Instr, depth: int) -> dict[str, Any]:
        if depth >= len(ctrls):
            raise err("branch depth out of range", ins)
        return ctrls[-1 - depth]

    push_ctrl(0x02, (), ft.results)
    body = fn.body
    for pos, ins in enumerate(body):
        budget.tick()
        op = ins.op
        if not ctrls:
            raise err("instructions after function end", ins)
        if op in NUMERIC:
            args, res = NUMERIC[op]
            pops(ins, args)
            for t in res:
                push(t)
        elif op == 0x00:
            unreachable()
        elif op == 0x01:
            pass
        elif op in (0x02, 0x03):
            push_ctrl(op, (), ins.imm)
        elif op == 0x04:
            pop(ins, I32)
            push_ctrl(op, (), ins.imm)
        elif op == 0x05:
            f = pop_ctrl(ins)
            if f["op"] != 0x04:
                raise err("else without matching if", ins)
            push_ctrl(0x05, f["start"], f["end"])
        elif op == 0x0B:
            f = pop_ctrl(ins)
            if f["op"] == 0x04 and f["end"] != f["start"]:
                raise err("if without else must have matching param/result types", ins)
            for t in f["end"]:
                push(t)
            if not ctrls and pos != len(body) - 1:
                raise err("instructions after function end", ins)
        elif op == 0x0C:
            pops(ins, label_types(label(ins, ins.imm)))
            unreachable()
        elif op == 0x0D:
            pop(ins, I32)
            lt = label_types(label(ins, ins.imm))
            pops(ins, lt)
            for t in lt:
                push(t)
        elif op == 0x0E:
            pop(ins, I32)
            labels, default = ins.imm
            arity = label_types(label(ins, default))
            # MVP label arity is 0 or 1, so each target is checked by peeking at most one slot:
            # O(targets), never a copy of the operand stack (resource-exhaustion guard, C028).
            f = ctrls[-1]
            top = vals[-1] if len(vals) > f["height"] else UNKNOWN
            if top is UNKNOWN and len(vals) == f["height"] and not f["unreachable"] and arity:
                raise err("operand stack underflow", ins)
            for lab in labels:
                lt = label_types(label(ins, lab))
                if len(lt) != len(arity):
                    raise err("br_table arity mismatch", ins)
                if lt and top is not UNKNOWN and lt[0] != top:
                    raise err("br_table target type mismatch", ins)
            pops(ins, arity)
            unreachable()
        elif op == 0x0F:
            pops(ins, ft.results)
            unreachable()
        elif op == 0x10:
            if ins.imm >= len(ftypes):
                raise err("call target out of range", ins)
            t = ftypes[ins.imm]
            pops(ins, t.params)
            for r in t.results:
                push(r)
        elif op == 0x11:
            if not has_table:
                raise err("call_indirect without a table", ins)
            if ins.imm >= len(m.types):
                raise err("call_indirect type index out of range", ins)
            t = m.types[ins.imm]
            pop(ins, I32)
            pops(ins, t.params)
            for r in t.results:
                push(r)
        elif op == 0x1A:
            pop(ins)
        elif op == 0x1B:
            pop(ins, I32)
            t1 = pop(ins)
            t2 = pop(ins, t1)
            push(t1 if t1 is not UNKNOWN else t2)
        elif op in (0x20, 0x21, 0x22):
            if ins.imm >= len(locals_):
                raise err("local index out of range", ins)
            t = locals_[ins.imm]
            if op == 0x20:
                push(t)
            elif op == 0x21:
                pop(ins, t)
            else:
                pop(ins, t)
                push(t)
        elif op in (0x23, 0x24):
            if ins.imm >= len(globals_):
                raise err("global index out of range", ins)
            t, mut = globals_[ins.imm]
            if op == 0x23:
                push(t)
            else:
                if not mut:
                    raise err("global.set on immutable global", ins)
                pop(ins, t)
        elif op in MEMORY_OPS:
            if not has_mem:
                raise err("memory access without memory", ins)
            vt, width, is_store = MEMORY_OPS[op]
            align, _ = ins.imm
            if align >= 32 or (1 << align) > width:
                raise err("alignment exceeds natural alignment", ins)
            if is_store:
                pop(ins, vt)
                pop(ins, I32)
            else:
                pop(ins, I32)
                push(vt)
        elif op in (0x3F, 0x40):
            if not has_mem:
                raise err("memory instruction without memory", ins)
            if op == 0x40:
                pop(ins, I32)
            push(I32)
        elif op == 0x41:
            push(I32)
        elif op == 0x42:
            push(I64)
        elif op == 0x43:
            push(F32)
        elif op == 0x44:
            push(F64)
        else:  # decoder guarantees coverage; this is an invariant guard
            raise SfiError("SFI_INTERNAL_INVARIANT", "validator reached undecoded opcode", opcode=str(op))
    if ctrls:
        raise _invalid("function body not terminated", function_index=fidx)


# ------------------------------------------------------------------------------ encoding

def uleb(n: int) -> bytes:
    if n < 0:
        raise ValueError("uleb of negative")
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def sleb(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if (n == 0 and not b & 0x40) or (n == -1 and b & 0x40):
            out.append(b)
            return bytes(out)
        out.append(b | 0x80)


def encode_instr(ins: Instr) -> bytes:
    op = ins.op
    if isinstance(op, tuple):
        return bytes([0xFC]) + uleb(op[1])
    head = bytes([op])
    imm = ins.imm
    if op in (0x02, 0x03, 0x04):
        return head + (bytes([0x40]) if not imm else bytes([imm[0]]))
    if op in (0x0C, 0x0D, 0x10, 0x20, 0x21, 0x22, 0x23, 0x24):
        return head + uleb(imm)
    if op == 0x0E:
        labels, default = imm
        return head + uleb(len(labels)) + b"".join(uleb(x) for x in labels) + uleb(default)
    if op == 0x11:
        return head + uleb(imm) + b"\x00"
    if op in MEMORY_OPS:
        return head + uleb(imm[0]) + uleb(imm[1])
    if op in (0x3F, 0x40):
        return head + b"\x00"
    if op == 0x41 or op == 0x42:
        return head + sleb(imm)
    if op in (0x43, 0x44):
        return head + imm
    return head


def encode_body(locals_: list[tuple[int, int]], body: list[Instr]) -> bytes:
    inner = uleb(len(locals_)) + b"".join(uleb(n) + bytes([t]) for n, t in locals_)
    inner += b"".join(encode_instr(i) for i in body)
    return uleb(len(inner)) + inner


def section(sid: int, payload: bytes) -> bytes:
    return bytes([sid]) + uleb(len(payload)) + payload


def split_sections(data: bytes) -> list[tuple[int, bytes]]:
    """Return (id, payload) for each section of an already-parsed module."""
    r = Reader(data, 8)
    out = []
    while not r.eof():
        sid = r.byte()
        size = r.u32()
        out.append((sid, r.bytes(size)))
    return out
