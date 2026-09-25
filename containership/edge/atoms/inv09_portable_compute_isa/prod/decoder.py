"""M01 - raw WebAssembly binary decoder and structural validator.

Decodes untrusted module bytes into an immutable :class:`ParsedModule`.
Everything here is byte-derived; nothing is taken from a manifest or header.

Guarantees:
* strict magic/version; exact consumption of every section payload;
* canonical-width LEB128 (u32 <= 5 bytes, s33 <= 5, s64 <= 10) with unused
  high bits checked, overflow and truncation refused;
* section ordering (incl. data-count before code) and singleton uniqueness;
* index spaces bounded across sections; limits validated;
* every ceiling from :mod:`limits` applied *before* allocation;
* UTF-8 names decoded strictly; every error carries byte offset + section.

Function bodies are kept as (offset, bytes) slices and type-checked by
:mod:`typecheck` (M02).  Unknown sections/opcodes/flags fail closed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .errors import Code, InvalidModule
from .limits import DEFAULT_LIMITS, Governor, Limits

MAGIC = b"\x00asm"
VERSION = b"\x01\x00\x00\x00"

I32, I64, F32, F64, V128, FUNCREF, EXTERNREF = 0x7F, 0x7E, 0x7D, 0x7C, 0x7B, 0x70, 0x6F
NUM_TYPES = frozenset({I32, I64, F32, F64})
REF_TYPES = frozenset({FUNCREF, EXTERNREF})
VAL_TYPES = NUM_TYPES | REF_TYPES | {V128}
TYPE_NAMES = {I32: "i32", I64: "i64", F32: "f32", F64: "f64", V128: "v128",
              FUNCREF: "funcref", EXTERNREF: "externref"}

#: heap/value-type bytes from the GC, typed-function-reference and EH proposals
GC_TYPE_BYTES = frozenset({0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x6B, 0x6C, 0x6D,
                           0x6E, 0x71, 0x72, 0x73, 0x74})

SECTION_NAMES = {0: "custom", 1: "type", 2: "import", 3: "function", 4: "table",
                 5: "memory", 6: "global", 7: "export", 8: "start", 9: "element",
                 10: "code", 11: "data", 12: "datacount"}
# canonical order of non-custom sections (datacount sits between element and code)
SECTION_ORDER = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 12: 10, 10: 11, 11: 12}
MAX_PAGES = 65536
MAX_TABLE = 0xFFFFFFFF


@dataclass(frozen=True)
class FuncType:
    params: tuple[int, ...]
    results: tuple[int, ...]


@dataclass(frozen=True)
class LimitsT:
    min: int
    max: Optional[int]
    shared: bool = False


@dataclass(frozen=True)
class TableType:
    elem: int
    limits: LimitsT


@dataclass(frozen=True)
class GlobalType:
    valtype: int
    mutable: bool


@dataclass(frozen=True)
class ConstExpr:
    offset: int
    code: bytes  # raw bytes incl. trailing 0x0B, checked by typecheck


@dataclass(frozen=True)
class Import:
    module: str
    name: str
    kind: int  # 0 func 1 table 2 mem 3 global
    desc: object  # typeidx | TableType | LimitsT | GlobalType
    offset: int


@dataclass(frozen=True)
class Export:
    name: str
    kind: int
    index: int
    offset: int


@dataclass(frozen=True)
class Global:
    type: GlobalType
    init: ConstExpr


@dataclass(frozen=True)
class Elem:
    mode: str  # active | passive | declarative
    reftype: int
    table: int
    offset_expr: Optional[ConstExpr]
    func_indices: Optional[tuple[int, ...]]  # when encoded as indices
    exprs: Optional[tuple[ConstExpr, ...]]   # when encoded as expressions
    flags: int
    at: int


@dataclass(frozen=True)
class Data:
    mode: str  # active | passive
    memory: int
    offset_expr: Optional[ConstExpr]
    size: int
    flags: int
    at: int


@dataclass(frozen=True)
class Body:
    offset: int
    locals: tuple[tuple[int, int], ...]  # (count, type)
    code_offset: int
    code: bytes


@dataclass(frozen=True)
class SectionInfo:
    id: int
    name: str
    offset: int
    size: int


@dataclass(frozen=True)
class ParsedModule:
    size_bytes: int
    sections: tuple[SectionInfo, ...]
    types: tuple[FuncType, ...]
    imports: tuple[Import, ...]
    func_type_indices: tuple[int, ...]  # defined functions only
    tables: tuple[TableType, ...]
    memories: tuple[LimitsT, ...]
    globals: tuple[Global, ...]
    exports: tuple[Export, ...]
    start: Optional[int]
    elems: tuple[Elem, ...]
    data_count: Optional[int]
    bodies: tuple[Body, ...]
    datas: tuple[Data, ...]
    customs: tuple[tuple[str, int, int], ...]  # (name, offset, size)
    structural_features: frozenset[str] = field(default_factory=frozenset)
    feature_evidence: tuple[tuple[str, int, str], ...] = ()

    # --- derived index spaces -------------------------------------------
    def imported(self, kind: int) -> tuple[Import, ...]:
        return tuple(i for i in self.imports if i.kind == kind)

    @property
    def all_func_types(self) -> tuple[int, ...]:
        return tuple(i.desc for i in self.imported(0)) + self.func_type_indices  # type: ignore[operator]

    @property
    def all_tables(self) -> tuple[TableType, ...]:
        return tuple(i.desc for i in self.imported(1)) + self.tables  # type: ignore[operator]

    @property
    def all_memories(self) -> tuple[LimitsT, ...]:
        return tuple(i.desc for i in self.imported(2)) + self.memories  # type: ignore[operator]

    @property
    def all_globals(self) -> tuple[GlobalType, ...]:
        return tuple(i.desc for i in self.imported(3)) + tuple(g.type for g in self.globals)  # type: ignore[operator]


class Reader:
    """Bounded cursor over an immutable bytes object."""

    __slots__ = ("buf", "pos", "end", "gov", "section")

    def __init__(self, buf: bytes, pos: int, end: int, gov: Governor, section: str = "module"):
        self.buf, self.pos, self.end, self.gov, self.section = buf, pos, end, gov, section

    def fail(self, code: Code, detail: str, at: int | None = None) -> InvalidModule:
        return InvalidModule(code, detail, offset=self.pos if at is None else at, section=self.section)

    def eof(self) -> bool:
        return self.pos >= self.end

    def u8(self) -> int:
        if self.pos >= self.end:
            raise self.fail(Code.TRUNCATED, "unexpected end")
        b = self.buf[self.pos]
        self.pos += 1
        return b

    def bytes_(self, n: int) -> bytes:
        if n < 0 or n > self.end - self.pos:
            raise self.fail(Code.TRUNCATED, f"need {n} bytes, have {self.end - self.pos}")
        b = self.buf[self.pos:self.pos + n]
        self.pos += n
        return b

    def _uleb(self, bits: int) -> int:
        start = self.pos
        result = shift = 0
        max_bytes = (bits + 6) // 7
        for i in range(max_bytes):
            b = self.u8()
            result |= (b & 0x7F) << shift
            if not b & 0x80:
                if i == max_bytes - 1 and bits % 7:
                    unused = b >> (bits % 7)
                    if unused:
                        raise self.fail(Code.BAD_LEB128, f"u{bits} overflow", start)
                return result
            shift += 7
        raise self.fail(Code.BAD_LEB128, f"u{bits} too long", start)

    def _sleb(self, bits: int) -> int:
        start = self.pos
        result = shift = 0
        max_bytes = (bits + 6) // 7
        for i in range(max_bytes):
            b = self.u8()
            result |= (b & 0x7F) << shift
            shift += 7
            if not b & 0x80:
                if i == max_bytes - 1:
                    # remaining high bits must be a sign extension of bit (bits-1)
                    used = bits - 7 * (max_bytes - 1)  # bits significant in last byte
                    sign_and_unused = (b & 0x7F) >> (used - 1)
                    if sign_and_unused not in (0, (0x7F >> (used - 1))):
                        raise self.fail(Code.BAD_LEB128, f"s{bits} overflow", start)
                if b & 0x40:
                    result -= 1 << shift
                return result
        raise self.fail(Code.BAD_LEB128, f"s{bits} too long", start)

    def u32(self) -> int:
        return self._uleb(32)

    def s32(self) -> int:
        return self._sleb(32)

    def s33(self) -> int:
        return self._sleb(33)

    def s64(self) -> int:
        return self._sleb(64)

    def count(self, ceiling: int, what: str) -> int:
        at = self.pos
        n = self.u32()
        lim = self.gov.limits
        self.gov.cap(n, min(ceiling, lim.max_vector_count), what, at)
        # every element needs >= 1 byte: refuse vector-count bombs up front
        if n > self.end - self.pos:
            raise self.fail(Code.TRUNCATED, f"{what} count {n} exceeds remaining bytes", at)
        return n

    def name(self) -> str:
        at = self.pos
        n = self.u32()
        self.gov.cap(n, self.gov.limits.max_name_bytes, "name bytes", at)
        raw = self.bytes_(n)
        try:
            return raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise self.fail(Code.BAD_UTF8, f"invalid UTF-8 name: {exc.reason}", at) from None


def _valtype(r: Reader, feats: "_Feat") -> int:
    at = r.pos
    t = r.u8()
    if t not in VAL_TYPES:
        if t in GC_TYPE_BYTES:
            raise r.fail(Code.UNSUPPORTED_PROPOSAL, f"gc/typed-reference value type 0x{t:02x}", at)
        raise r.fail(Code.MALFORMED, f"invalid value type 0x{t:02x}", at)
    if t in REF_TYPES:
        feats.add("reference-types", at, "reference-typed value")
    if t == V128:
        feats.add("simd", at, "v128 value type")
    return t


def _reftype(r: Reader) -> int:
    at = r.pos
    t = r.u8()
    if t not in REF_TYPES:
        if t in GC_TYPE_BYTES:
            raise r.fail(Code.UNSUPPORTED_PROPOSAL, f"gc/typed-reference type 0x{t:02x}", at)
        raise r.fail(Code.MALFORMED, f"invalid reference type 0x{t:02x}", at)
    return t


def _limits(r: Reader, ceiling: int, what: str, feats: "_Feat", allow_shared: bool) -> LimitsT:
    at = r.pos
    flag = r.u8()
    if flag == 0x00:
        mn, mx, shared = r.u32(), None, False
    elif flag == 0x01:
        mn, mx, shared = r.u32(), None, False
        mx = r.u32()
    elif flag == 0x03 and allow_shared:
        mn = r.u32()
        mx = r.u32()
        shared = True
        feats.add("threads", at, "shared memory")
    elif flag in (0x04, 0x05, 0x06, 0x07):
        raise r.fail(Code.UNSUPPORTED_PROPOSAL, "memory64 limits not enabled", at)
    else:
        raise r.fail(Code.MALFORMED, f"invalid limits flag 0x{flag:02x}", at)
    if mn > ceiling or (mx is not None and mx > ceiling):
        raise r.fail(Code.INVALID_LIMITS, f"{what} limit exceeds {ceiling}", at)
    if mx is not None and mn > mx:
        raise r.fail(Code.INVALID_LIMITS, f"{what} min {mn} > max {mx}", at)
    return LimitsT(mn, mx, shared)


class _Feat:
    def __init__(self) -> None:
        self.names: set[str] = {"core"}
        self.evidence: list[tuple[str, int, str]] = []

    def add(self, name: str, at: int, why: str) -> None:
        if name not in self.names:
            self.evidence.append((name, at, why))
        self.names.add(name)


def _const_expr(r: Reader) -> ConstExpr:
    """Capture a constant expression's bytes; typing happens in M02.

    Only the opcodes legal in constant expressions are walked, so we can find
    the terminating ``end`` without a general instruction decoder."""
    start = r.pos
    while True:
        r.gov.step()
        at = r.pos
        op = r.u8()
        if op == 0x0B:
            return ConstExpr(start, r.buf[start:r.pos])
        if op == 0x41:
            r.s32()
        elif op == 0x42:
            r.s64()
        elif op == 0x43:
            r.bytes_(4)
        elif op == 0x44:
            r.bytes_(8)
        elif op == 0x23:  # global.get
            r.u32()
        elif op == 0xD0:  # ref.null
            if r.pos < r.end and r.buf[r.pos] < 0x40:
                raise r.fail(Code.UNSUPPORTED_PROPOSAL, "typed ref.null heap type", at)
            _reftype(r)
        elif op == 0xD2:  # ref.func
            r.u32()
        elif op == 0xFD:
            raise r.fail(Code.UNSUPPORTED_PROPOSAL, "simd constant expressions not enabled", at)
        else:
            raise r.fail(Code.INVALID_CONST_EXPR, f"opcode 0x{op:02x} not constant", at)
        if r.pos - start > 64:
            raise r.fail(Code.INVALID_CONST_EXPR, "constant expression too long", start)


def decode(data: bytes, limits: Limits = DEFAULT_LIMITS, gov: Governor | None = None) -> ParsedModule:
    """Decode untrusted bytes.  Raises :class:`InvalidModule` on any defect."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise InvalidModule(Code.MALFORMED, "module must be bytes")
    buf = bytes(data)  # immutable private snapshot (M11)
    gov = gov or Governor(limits)
    lim = gov.limits
    if len(buf) > lim.max_module_bytes:
        raise InvalidModule(Code.LIMIT_EXCEEDED, f"module {len(buf)} bytes > {lim.max_module_bytes}", offset=0)
    if len(buf) < 8:
        raise InvalidModule(Code.TRUNCATED if buf == MAGIC[:len(buf)] else Code.BAD_MAGIC,
                            "shorter than header", offset=0)
    if buf[:4] != MAGIC:
        raise InvalidModule(Code.BAD_MAGIC, "bad magic", offset=0)
    if buf[4:8] != VERSION:
        raise InvalidModule(Code.BAD_VERSION, f"unsupported binary version {buf[4:8].hex()}", offset=4)

    feats = _Feat()
    r = Reader(buf, 8, len(buf), gov)
    sections: list[SectionInfo] = []
    seen: set[int] = set()
    last_order = 0
    customs: list[tuple[str, int, int]] = []
    types: list[FuncType] = []
    imports: list[Import] = []
    funcs: list[int] = []
    tables: list[TableType] = []
    mems: list[LimitsT] = []
    globals_: list[Global] = []
    exports: list[Export] = []
    start: Optional[int] = None
    elems: list[Elem] = []
    data_count: Optional[int] = None
    bodies: list[Body] = []
    datas: list[Data] = []

    def n_funcs() -> int:
        return sum(1 for i in imports if i.kind == 0) + len(funcs)

    def n_tables() -> int:
        return sum(1 for i in imports if i.kind == 1) + len(tables)

    def n_mems() -> int:
        return sum(1 for i in imports if i.kind == 2) + len(mems)

    def n_globals() -> int:
        return sum(1 for i in imports if i.kind == 3) + len(globals_)

    while not r.eof():
        gov.step()
        sec_at = r.pos
        sid = r.u8()
        size = r.u32()
        payload_at = r.pos
        if size > r.end - r.pos:
            raise InvalidModule(Code.TRUNCATED, f"section size {size} exceeds module", offset=sec_at,
                                section=SECTION_NAMES.get(sid, f"id{sid}"))
        if sid not in SECTION_NAMES:
            raise InvalidModule(Code.UNKNOWN_SECTION, f"unknown section id {sid}", offset=sec_at)
        name = SECTION_NAMES[sid]
        gov.cap(len(sections) + 1, lim.max_sections, "section count", sec_at)
        sections.append(SectionInfo(sid, name, sec_at, size))
        s = Reader(buf, payload_at, payload_at + size, gov, name)
        r.pos = payload_at + size

        if sid == 0:
            gov.cap(len(customs) + 1, lim.max_custom_sections, "custom sections", sec_at)
            cname = s.name()
            customs.append((cname, sec_at, size))
            continue  # custom payload is opaque; its bytes are covered by the M07 digest

        if sid in seen:
            raise InvalidModule(Code.DUPLICATE_SECTION, f"duplicate {name} section", offset=sec_at, section=name)
        if SECTION_ORDER[sid] <= last_order:
            raise InvalidModule(Code.SECTION_ORDER, f"{name} section out of order", offset=sec_at, section=name)
        seen.add(sid)
        last_order = SECTION_ORDER[sid]

        if sid == 1:
            for _ in range(s.count(lim.max_types, "types")):
                gov.step()
                at = s.pos
                form = s.u8()
                if form != 0x60:
                    raise s.fail(Code.MALFORMED, f"expected functype 0x60, got 0x{form:02x}", at)
                params = tuple(_valtype(s, feats) for _ in range(s.count(lim.max_type_arity, "params")))
                results = tuple(_valtype(s, feats) for _ in range(s.count(lim.max_type_arity, "results")))
                if len(results) > 1:
                    feats.add("multi-value", at, "function type with >1 result")
                types.append(FuncType(params, results))
        elif sid == 2:
            for _ in range(s.count(lim.max_imports, "imports")):
                gov.step()
                at = s.pos
                mod, nm = s.name(), s.name()
                kat = s.pos
                kind = s.u8()
                desc: object
                if kind == 0:
                    ti = s.u32()
                    if ti >= len(types):
                        raise s.fail(Code.INVALID_INDEX, f"import type index {ti}", kat)
                    desc = ti
                elif kind == 1:
                    rt = _reftype(s)
                    desc = TableType(rt, _limits(s, MAX_TABLE, "table", feats, False))
                elif kind == 2:
                    desc = _limits(s, MAX_PAGES, "memory", feats, True)
                elif kind == 3:
                    vt = _valtype(s, feats)
                    m = s.u8()
                    if m not in (0, 1):
                        raise s.fail(Code.MALFORMED, "invalid mutability", s.pos - 1)
                    desc = GlobalType(vt, bool(m))
                    if m:
                        feats.add("mutable-globals-import", at, "imported mutable global")
                elif kind == 4:
                    raise s.fail(Code.UNSUPPORTED_PROPOSAL, "exception-handling tag import", kat)
                else:
                    raise s.fail(Code.MALFORMED, f"invalid import kind {kind}", kat)
                imports.append(Import(mod, nm, kind, desc, at))
        elif sid == 3:
            for _ in range(s.count(lim.max_functions, "functions")):
                gov.step()
                at = s.pos
                ti = s.u32()
                if ti >= len(types):
                    raise s.fail(Code.INVALID_INDEX, f"function type index {ti}", at)
                funcs.append(ti)
            gov.cap(n_funcs(), lim.max_functions, "functions")
        elif sid == 4:
            for _ in range(s.count(lim.max_tables, "tables")):
                gov.step()
                rt = _reftype(s)
                tables.append(TableType(rt, _limits(s, MAX_TABLE, "table", feats, False)))
        elif sid == 5:
            for _ in range(s.count(lim.max_memories + 1, "memories")):
                gov.step()
                mems.append(_limits(s, MAX_PAGES, "memory", feats, True))
        elif sid == 6:
            for _ in range(s.count(lim.max_globals, "globals")):
                gov.step()
                vt = _valtype(s, feats)
                m = s.u8()
                if m not in (0, 1):
                    raise s.fail(Code.MALFORMED, "invalid mutability", s.pos - 1)
                globals_.append(Global(GlobalType(vt, bool(m)), _const_expr(s)))
        elif sid == 7:
            names: set[str] = set()
            for _ in range(s.count(lim.max_exports, "exports")):
                gov.step()
                at = s.pos
                nm = s.name()
                if nm in names:
                    raise s.fail(Code.DUPLICATE_EXPORT, f"duplicate export {nm!r}", at)
                names.add(nm)
                kind = s.u8()
                idx = s.u32()
                bound = {0: n_funcs(), 1: n_tables(), 2: n_mems(), 3: n_globals()}.get(kind)
                if bound is None:
                    raise s.fail(Code.MALFORMED, f"invalid export kind {kind}", at)
                if idx >= bound:
                    raise s.fail(Code.INVALID_INDEX, f"export {nm!r} index {idx}", at)
                exports.append(Export(nm, kind, idx, at))
        elif sid == 8:
            at = s.pos
            start = s.u32()
            if start >= n_funcs():
                raise s.fail(Code.INVALID_INDEX, f"start function {start}", at)
        elif sid == 9:
            for _ in range(s.count(lim.max_elem_segments, "element segments")):
                gov.step()
                at = s.pos
                flags = s.u32()
                if flags > 7:
                    raise s.fail(Code.MALFORMED, f"invalid element flags {flags}", at)
                passive_or_decl = flags & 1
                explicit_table = flags & 2
                uses_exprs = flags & 4
                if flags not in (0, 4):
                    feats.add("bulk-memory", at, f"element segment flags {flags}")
                if uses_exprs:
                    feats.add("reference-types", at, "element expressions")
                table = 0
                off = None
                if not passive_or_decl:
                    mode = "active"
                    if explicit_table:
                        table = s.u32()
                    off = _const_expr(s)
                else:
                    mode = "declarative" if explicit_table else "passive"
                if flags in (0, 4):
                    reftype = FUNCREF
                elif uses_exprs:
                    reftype = _reftype(s)
                else:
                    ek = s.u8()
                    if ek != 0x00:
                        raise s.fail(Code.MALFORMED, f"invalid elemkind {ek}", s.pos - 1)
                    reftype = FUNCREF
                n = s.count(lim.max_vector_count, "element items")
                if uses_exprs:
                    exprs = tuple(_const_expr(s) for _ in range(n))
                    fidx = None
                else:
                    fidx = tuple(s.u32() for _ in range(n))
                    exprs = None
                    gov.step(n)
                elems.append(Elem(mode, reftype, table, off, fidx, exprs, flags, at))
        elif sid == 12:
            data_count = s.u32()
            gov.cap(data_count, lim.max_data_segments, "data count", payload_at)
            feats.add("bulk-memory", sec_at, "datacount section")
        elif sid == 10:
            n = s.count(lim.max_functions, "code entries")
            if n != len(funcs):
                raise s.fail(Code.COUNT_MISMATCH, f"{n} bodies for {len(funcs)} functions", payload_at)
            for _ in range(n):
                gov.step()
                at = s.pos
                bsize = s.u32()
                gov.cap(bsize, lim.max_function_body_bytes, "function body bytes", at)
                if bsize > s.end - s.pos:
                    raise s.fail(Code.TRUNCATED, "function body exceeds section", at)
                b = Reader(buf, s.pos, s.pos + bsize, gov, "code")
                s.pos += bsize
                groups = []
                total = 0
                for _ in range(b.count(lim.max_locals_per_function, "local groups")):
                    lat = b.pos
                    c = b.u32()
                    total += c
                    gov.cap(total, lim.max_locals_per_function, "locals", lat)
                    groups.append((c, _valtype(b, feats)))
                if b.eof():
                    raise b.fail(Code.TRUNCATED, "function body has no expression")
                code = buf[b.pos:b.end]
                if code[-1:] != b"\x0b":
                    raise b.fail(Code.MALFORMED, "function body does not end with 'end'", b.end - 1)
                bodies.append(Body(at, tuple(groups), b.pos, code))
        elif sid == 11:
            n = s.count(lim.max_data_segments, "data segments")
            if data_count is not None and n != data_count:
                raise s.fail(Code.COUNT_MISMATCH, f"{n} data segments but datacount {data_count}", payload_at)
            for _ in range(n):
                gov.step()
                at = s.pos
                flags = s.u32()
                if flags == 0:
                    mem, off, mode = 0, _const_expr(s), "active"
                elif flags == 1:
                    mem, off, mode = 0, None, "passive"
                    feats.add("bulk-memory", at, "passive data segment")
                elif flags == 2:
                    mem = s.u32()
                    off, mode = _const_expr(s), "active"
                else:
                    raise s.fail(Code.MALFORMED, f"invalid data flags {flags}", at)
                sz = s.u32()
                s.bytes_(sz)
                datas.append(Data(mode, mem, off, sz, flags, at))
        if not s.eof():
            raise InvalidModule(Code.SECTION_SIZE_MISMATCH,
                                f"{s.end - s.pos} unconsumed bytes", offset=s.pos, section=name)

    # ---- cross-section structural checks ------------------------------
    if funcs and 10 not in seen:
        raise InvalidModule(Code.COUNT_MISMATCH, f"{len(funcs)} functions but no code section", section="code")
    nt, nm_ = n_tables(), n_mems()
    gov.cap(nm_, lim.max_memories, "memories")
    if nt > 1:
        feats.add("reference-types", 0, "multiple tables")
    if any(i.kind == 2 and i.desc.shared for i in imports) or any(m.shared for m in mems):  # type: ignore[union-attr]
        feats.add("threads", 0, "shared memory")
    for e in elems:
        if e.mode == "active" and e.table >= nt:
            raise InvalidModule(Code.INVALID_INDEX, f"element table {e.table}", offset=e.at, section="element")
        if e.func_indices is not None:
            for fi in e.func_indices:
                if fi >= n_funcs():
                    raise InvalidModule(Code.INVALID_INDEX, f"element function {fi}", offset=e.at, section="element")
    for d in datas:
        if d.mode == "active" and d.memory >= nm_:
            raise InvalidModule(Code.INVALID_INDEX, f"data memory {d.memory}", offset=d.at, section="data")
    if data_count is not None and 11 not in seen and data_count != 0:
        raise InvalidModule(Code.COUNT_MISMATCH, "datacount without data section", section="data")

    return ParsedModule(
        size_bytes=len(buf), sections=tuple(sections), types=tuple(types), imports=tuple(imports),
        func_type_indices=tuple(funcs), tables=tuple(tables), memories=tuple(mems),
        globals=tuple(globals_), exports=tuple(exports), start=start, elems=tuple(elems),
        data_count=data_count, bodies=tuple(bodies), datas=tuple(datas), customs=tuple(customs),
        structural_features=frozenset(feats.names), feature_evidence=tuple(feats.evidence),
    )
