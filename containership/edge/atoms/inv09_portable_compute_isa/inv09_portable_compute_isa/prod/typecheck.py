"""M02 - WebAssembly type validator + M03 byte-derived feature detector.

Implements the validation algorithm of the WebAssembly core specification
(Appendix "Validation Algorithm"): an explicit typed operand stack and an
explicit control-frame stack, iterative (no recursion proportional to nesting),
bounded by the M13 governor.

Certified instruction families: MVP core, mutable-global import/export,
sign-extension, non-trapping float-to-int, multi-value, bulk-memory,
reference-types.  SIMD (0xFD), threads/atomics (0xFE), exception handling,
tail calls, typed function references, GC, memory64 and multi-memory are
recognised and refused with ``UNSUPPORTED_PROPOSAL`` - fail closed, never
skipped.

The feature set returned by :func:`validate_module` is derived exclusively
from the bytes (decoder facts + instruction evidence); a caller cannot supply
or alter it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .decoder import (GC_TYPE_BYTES, EXTERNREF, F32, F64, FUNCREF, I32, I64, NUM_TYPES, REF_TYPES, V128,
                      VAL_TYPES, ConstExpr, ParsedModule, Reader, decode)
from .errors import Code, InvalidModule, boundary
from .limits import DEFAULT_LIMITS, Governor, Limits

U = None  # the "unknown" operand type in unreachable code


@dataclass(frozen=True)
class TypedFacts:
    """Immutable byte-derived facts handed to policy/admission (M03 output)."""

    features: frozenset[str]
    evidence: tuple[tuple[str, int, str], ...]  # (feature, byte offset, reason)
    uses_float: bool
    float_evidence_offset: Optional[int]
    imports: tuple[tuple[str, str, int], ...]   # (module, name, kind)
    exports: tuple[tuple[str, int], ...]
    function_count: int
    instruction_count: int
    section_count: int
    size_bytes: int


# ---------------------------------------------------------------- op tables
_SIMPLE: dict[int, tuple[tuple[int, ...], tuple[int, ...]]] = {}


def _reg(ops, params, results):
    for op in ops:
        _SIMPLE[op] = (params, results)


_reg([0x45], (I32,), (I32,))
_reg(range(0x46, 0x50), (I32, I32), (I32,))
_reg([0x50], (I64,), (I32,))
_reg(range(0x51, 0x5B), (I64, I64), (I32,))
_reg(range(0x5B, 0x61), (F32, F32), (I32,))
_reg(range(0x61, 0x67), (F64, F64), (I32,))
_reg(range(0x67, 0x6A), (I32,), (I32,))
_reg(range(0x6A, 0x79), (I32, I32), (I32,))
_reg(range(0x79, 0x7C), (I64,), (I64,))
_reg(range(0x7C, 0x8B), (I64, I64), (I64,))
_reg(range(0x8B, 0x92), (F32,), (F32,))
_reg(range(0x92, 0x99), (F32, F32), (F32,))
_reg(range(0x99, 0xA0), (F64,), (F64,))
_reg(range(0xA0, 0xA7), (F64, F64), (F64,))
for _op, _p, _r in [
    (0xA7, I64, I32), (0xA8, F32, I32), (0xA9, F32, I32), (0xAA, F64, I32), (0xAB, F64, I32),
    (0xAC, I32, I64), (0xAD, I32, I64), (0xAE, F32, I64), (0xAF, F32, I64), (0xB0, F64, I64),
    (0xB1, F64, I64), (0xB2, I32, F32), (0xB3, I32, F32), (0xB4, I64, F32), (0xB5, I64, F32),
    (0xB6, F64, F32), (0xB7, I32, F64), (0xB8, I32, F64), (0xB9, I64, F64), (0xBA, I64, F64),
    (0xBB, F32, F64), (0xBC, F32, I32), (0xBD, F64, I64), (0xBE, I32, F32), (0xBF, I64, F64),
    (0xC0, I32, I32), (0xC1, I32, I32), (0xC2, I64, I64), (0xC3, I64, I64), (0xC4, I64, I64),
]:
    _SIMPLE[_op] = ((_p,), (_r,))
_SIGN_EXT = frozenset(range(0xC0, 0xC5))
_FLOAT_OPS = frozenset(set(range(0x5B, 0x67)) | set(range(0x8B, 0xA7)) | set(range(0xA8, 0xAC))
                       | set(range(0xAE, 0xB2)) | set(range(0xB2, 0xBC)) | {0x2A, 0x2B, 0x38, 0x39, 0x43, 0x44})
_SAT = {0: (F32, I32), 1: (F32, I32), 2: (F64, I32), 3: (F64, I32),
        4: (F32, I64), 5: (F32, I64), 6: (F64, I64), 7: (F64, I64)}
# loads/stores: op -> (valtype, max log2 alignment)
_LOADS = {0x28: (I32, 2), 0x29: (I64, 3), 0x2A: (F32, 2), 0x2B: (F64, 3), 0x2C: (I32, 0),
          0x2D: (I32, 0), 0x2E: (I32, 1), 0x2F: (I32, 1), 0x30: (I64, 0), 0x31: (I64, 0),
          0x32: (I64, 1), 0x33: (I64, 1), 0x34: (I64, 2), 0x35: (I64, 2)}
_STORES = {0x36: (I32, 2), 0x37: (I64, 3), 0x38: (F32, 2), 0x39: (F64, 3), 0x3A: (I32, 0),
           0x3B: (I32, 1), 0x3C: (I64, 0), 0x3D: (I64, 1), 0x3E: (I64, 2)}
_UNSUPPORTED = {
    0x06: "exception-handling", 0x07: "exception-handling", 0x08: "exception-handling",
    0x09: "exception-handling", 0x18: "exception-handling", 0x19: "exception-handling",
    0x1F: "exception-handling", 0x0A: "exception-handling",
    0x12: "tail-call", 0x13: "tail-call", 0x14: "typed-function-references",
    0x15: "typed-function-references", 0xD3: "typed-function-references",
    0xD4: "typed-function-references", 0xD5: "typed-function-references",
    0xD6: "typed-function-references", 0xFB: "gc", 0xFD: "simd", 0xFE: "threads",
}


class _Frame:
    __slots__ = ("op", "start", "end", "height", "unreachable")

    def __init__(self, op, start, end, height):
        self.op, self.start, self.end, self.height, self.unreachable = op, start, end, height, False

    def labels(self):
        return self.start if self.op == 0x03 else self.end


class _Ctx:
    def __init__(self, m: ParsedModule, gov: Governor):
        self.m = m
        self.gov = gov
        self.types = m.types
        self.funcs = m.all_func_types
        self.tables = m.all_tables
        self.mems = m.all_memories
        self.globals = m.all_globals
        self.n_imported_globals = len(m.imported(3))
        self.refs = self._declared_refs()
        self.features: dict[str, tuple[int, str]] = {}
        self.uses_float = False
        self.float_at: Optional[int] = None
        self.instructions = 0

    def _declared_refs(self) -> frozenset[int]:
        refs: set[int] = set()
        for e in self.m.elems:
            if e.func_indices:
                refs.update(e.func_indices)
            for ce in e.exprs or ():
                refs.update(_ref_funcs_in_const(ce))
        for x in self.m.exports:
            if x.kind == 0:
                refs.add(x.index)
        for g in self.m.globals:
            refs.update(_ref_funcs_in_const(g.init))
        return frozenset(refs)

    def feat(self, name: str, at: int, why: str) -> None:
        self.features.setdefault(name, (at, why))


def _ref_funcs_in_const(ce: ConstExpr) -> set[int]:
    out: set[int] = set()
    r = Reader(ce.code, 0, len(ce.code), Governor(), "const")
    while not r.eof():
        op = r.u8()
        if op == 0xD2:
            out.add(r.u32())
        elif op == 0x41:
            r.s32()
        elif op == 0x42:
            r.s64()
        elif op == 0x43:
            r.bytes_(4)
        elif op == 0x44:
            r.bytes_(8)
        elif op == 0x23:
            r.u32()
        elif op == 0xD0:
            r.u8()
    return out


def _check_const(ctx: _Ctx, ce: ConstExpr, expected: int, section: str, n_globals_visible: int) -> None:
    r = Reader(ce.code, 0, len(ce.code), ctx.gov, section)
    stack: list[int] = []

    def fail(detail):
        return InvalidModule(Code.INVALID_CONST_EXPR, detail, offset=ce.offset + r.pos, section=section)

    while True:
        op = r.u8()
        if op == 0x0B:
            break
        if op == 0x41:
            r.s32(); stack.append(I32)
        elif op == 0x42:
            r.s64(); stack.append(I64)
        elif op == 0x43:
            r.bytes_(4); stack.append(F32); ctx.uses_float = True
        elif op == 0x44:
            r.bytes_(8); stack.append(F64); ctx.uses_float = True
        elif op == 0x23:
            gi = r.u32()
            if gi >= min(n_globals_visible, ctx.n_imported_globals):
                raise fail(f"global.get {gi} must reference an imported global")
            gt = ctx.globals[gi]
            if gt.mutable:
                raise fail(f"global.get {gi} references a mutable global")
            stack.append(gt.valtype)
        elif op == 0xD0:
            t = r.u8()
            if t not in REF_TYPES:
                if t in GC_TYPE_BYTES or t < 0x40:
                    raise InvalidModule(Code.UNSUPPORTED_PROPOSAL, "typed/gc ref.null",
                                        offset=ce.offset + r.pos, section=section)
                raise fail("bad ref.null type")
            ctx.feat("reference-types", ce.offset, "ref.null in constant")
            stack.append(t)
        elif op == 0xD2:
            fi = r.u32()
            if fi >= len(ctx.funcs):
                raise fail(f"ref.func {fi} out of range")
            stack.append(FUNCREF)
        else:
            raise fail(f"opcode 0x{op:02x} not constant")
    if not r.eof():
        raise fail("trailing bytes after constant expression")
    if stack != [expected]:
        raise InvalidModule(Code.TYPE_MISMATCH, "constant expression result type mismatch",
                            offset=ce.offset, section=section)


def _validate_body(ctx: _Ctx, fidx: int, body) -> None:
    gov = ctx.gov
    lim = gov.limits
    ft = ctx.types[ctx.funcs[fidx]]
    locals_: list[int] = list(ft.params)
    for count, t in body.locals:
        locals_.extend([t] * count)  # counts already capped by M13 in decoder
    r = Reader(body.code, 0, len(body.code), gov, "code")
    base = body.code_offset
    vals: list[Optional[int]] = []
    ctrls: list[_Frame] = [_Frame(0x02, (), ft.results, 0)]

    def at() -> int:
        return base + r.pos

    def err(code: Code, detail: str) -> InvalidModule:
        return InvalidModule(code, f"func {fidx}: {detail}", offset=at(), section="code")

    def push(t):
        vals.append(t)
        if len(vals) > lim.max_operand_stack:
            raise err(Code.LIMIT_EXCEEDED, "operand stack too deep")

    def pop(expect: Optional[int] = U) -> Optional[int]:
        f = ctrls[-1]
        if len(vals) == f.height:
            if f.unreachable:
                return expect
            raise err(Code.STACK_UNDERFLOW, "operand stack underflow")
        actual = vals.pop()
        if actual is not U and expect is not U and actual != expect:
            raise err(Code.TYPE_MISMATCH, f"expected {_n(expect)}, got {_n(actual)}")
        return actual if actual is not U else expect

    def pops(ts):
        return [pop(t) for t in reversed(ts)][::-1]

    def pushes(ts):
        for t in ts:
            push(t)

    def push_ctrl(op, start, end):
        ctrls.append(_Frame(op, start, end, len(vals)))
        if len(ctrls) > lim.max_control_depth:
            raise err(Code.LIMIT_EXCEEDED, "control nesting too deep")
        pushes(start)

    def pop_ctrl() -> _Frame:
        f = ctrls[-1]
        pops(f.end)
        if len(vals) != f.height:
            raise err(Code.TYPE_MISMATCH, "values remaining on stack at end of block")
        ctrls.pop()
        return f

    def unreachable():
        del vals[ctrls[-1].height:]
        ctrls[-1].unreachable = True

    def blocktype():
        b = r.buf[r.pos] if r.pos < r.end else None
        if b == 0x40:
            r.pos += 1
            return (), ()
        if b is not None and b in VAL_TYPES:
            r.pos += 1
            if b == V128:
                raise err(Code.UNSUPPORTED_PROPOSAL, "simd")
            if b in REF_TYPES:
                ctx.feat("reference-types", at(), "reference-typed block")
            return (), (b,)
        idx = r.s33()
        if idx < 0 or idx >= len(ctx.types):
            raise err(Code.INVALID_INDEX, f"block type index {idx}")
        t = ctx.types[idx]
        if t.params or len(t.results) > 1:
            ctx.feat("multi-value", at(), "block with type index")
        return t.params, t.results

    def label(depth):
        if depth >= len(ctrls):
            raise err(Code.INVALID_BRANCH, f"branch depth {depth}")
        return ctrls[-1 - depth].labels()

    def memarg(max_align):
        a = r.u32()
        r.u32()  # offset (memory32: any u32)
        if a >= 64:
            raise err(Code.UNSUPPORTED_PROPOSAL, "multi-memory memarg")
        if a > max_align:
            raise err(Code.INVALID_ALIGNMENT, f"alignment 2**{a} > natural 2**{max_align}")
        need_mem()

    def need_mem():
        if not ctx.mems:
            raise err(Code.INVALID_INDEX, "memory instruction without memory")

    def zero_byte(what):
        if r.u8() != 0:
            raise err(Code.UNSUPPORTED_PROPOSAL, f"multi-memory {what}")

    def table(i) -> int:
        if i >= len(ctx.tables):
            raise err(Code.INVALID_INDEX, f"table {i}")
        return ctx.tables[i].elem

    def local(i) -> int:
        if i >= len(locals_):
            raise err(Code.INVALID_INDEX, f"local {i}")
        return locals_[i]

    def glob(i):
        if i >= len(ctx.globals):
            raise err(Code.INVALID_INDEX, f"global {i}")
        return ctx.globals[i]

    while True:
        gov.step()
        ctx.instructions += 1
        if r.eof():
            raise err(Code.TRUNCATED, "function body ended inside a block")
        op_at = at()
        op = r.u8()
        if op in _UNSUPPORTED:
            raise err(Code.UNSUPPORTED_PROPOSAL, _UNSUPPORTED[op])
        if op in _FLOAT_OPS and not ctx.uses_float:
            ctx.uses_float, ctx.float_at = True, op_at
        if op in _SIMPLE:
            if op in _SIGN_EXT:
                ctx.feat("sign-ext", op_at, "sign-extension operator")
            p, res = _SIMPLE[op]
            pops(p)
            pushes(res)
        elif op == 0x00:
            unreachable()
        elif op == 0x01:
            pass
        elif op in (0x02, 0x03):
            p, res = blocktype()
            pops(p)
            push_ctrl(op, p, res)
        elif op == 0x04:
            p, res = blocktype()
            pop(I32)
            pops(p)
            push_ctrl(op, p, res)
        elif op == 0x05:
            f = pop_ctrl()
            if f.op != 0x04:
                raise err(Code.MALFORMED, "else without if")
            push_ctrl(0x05, f.start, f.end)
        elif op == 0x0B:
            f = pop_ctrl()
            if f.op == 0x04 and f.start != f.end:
                raise err(Code.TYPE_MISMATCH, "if without else must have matching param/result types")
            if not ctrls:
                if not r.eof():
                    raise err(Code.MALFORMED, "trailing bytes after function end")
                return
            pushes(f.end)
        elif op == 0x0C:
            pops(label(r.u32()))
            unreachable()
        elif op == 0x0D:
            d = r.u32()
            pop(I32)
            ls = label(d)
            pushes(pops(ls))
        elif op == 0x0E:
            n = r.u32()
            gov.cap(n, lim.max_br_table_targets, "br_table targets", op_at)
            if n > r.end - r.pos:
                raise err(Code.TRUNCATED, "br_table target vector")
            targets = [r.u32() for _ in range(n)]
            gov.step(n)
            default = r.u32()
            pop(I32)
            arity = len(label(default))
            for t in targets:
                ls = label(t)
                if len(ls) != arity:
                    raise err(Code.TYPE_MISMATCH, "br_table targets have inconsistent arity")
                pushes(pops(ls))
            pops(label(default))
            unreachable()
        elif op == 0x0F:
            pops(ctrls[0].end)
            unreachable()
        elif op == 0x10:
            fi = r.u32()
            if fi >= len(ctx.funcs):
                raise err(Code.INVALID_INDEX, f"call {fi}")
            t = ctx.types[ctx.funcs[fi]]
            pops(t.params)
            pushes(t.results)
        elif op == 0x11:
            ti, tab = r.u32(), r.u32()
            if tab != 0:
                ctx.feat("reference-types", op_at, "call_indirect on table != 0")
            if table(tab) != FUNCREF:
                raise err(Code.TYPE_MISMATCH, "call_indirect table is not funcref")
            if ti >= len(ctx.types):
                raise err(Code.INVALID_INDEX, f"call_indirect type {ti}")
            t = ctx.types[ti]
            pop(I32)
            pops(t.params)
            pushes(t.results)
        elif op == 0x1A:
            pop()
        elif op == 0x1B:
            pop(I32)
            t1, t2 = pop(), pop()
            for t in (t1, t2):
                if t is not U and t not in NUM_TYPES:
                    raise err(Code.TYPE_MISMATCH, "untyped select requires numeric operands")
            if t1 is not U and t2 is not U and t1 != t2:
                raise err(Code.TYPE_MISMATCH, "select operands differ")
            push(t1 if t1 is not U else t2)
        elif op == 0x1C:
            n = r.u32()
            if n != 1:
                raise err(Code.MALFORMED, "typed select must have exactly one type")
            t = r.u8()
            if t not in VAL_TYPES or t == V128:
                raise err(Code.MALFORMED if t not in VAL_TYPES else Code.UNSUPPORTED_PROPOSAL, "select type")
            ctx.feat("reference-types", op_at, "typed select")
            pop(I32); pop(t); pop(t); push(t)
        elif op == 0x20:
            push(local(r.u32()))
        elif op == 0x21:
            pop(local(r.u32()))
        elif op == 0x22:
            t = local(r.u32())
            pop(t); push(t)
        elif op == 0x23:
            push(glob(r.u32()).valtype)
        elif op == 0x24:
            gi = r.u32()
            g = glob(gi)
            if not g.mutable:
                raise err(Code.IMMUTABLE_GLOBAL, f"global.set on immutable global {gi}")
            pop(g.valtype)
        elif op == 0x25:
            t = table(r.u32())
            ctx.feat("reference-types", op_at, "table.get")
            pop(I32); push(t)
        elif op == 0x26:
            t = table(r.u32())
            ctx.feat("reference-types", op_at, "table.set")
            pop(t); pop(I32)
        elif op in _LOADS:
            vt, al = _LOADS[op]
            memarg(al)
            pop(I32); push(vt)
        elif op in _STORES:
            vt, al = _STORES[op]
            memarg(al)
            pop(vt); pop(I32)
        elif op == 0x3F:
            zero_byte("memory.size"); need_mem(); push(I32)
        elif op == 0x40:
            zero_byte("memory.grow"); need_mem(); pop(I32); push(I32)
        elif op == 0x41:
            r.s32(); push(I32)
        elif op == 0x42:
            r.s64(); push(I64)
        elif op == 0x43:
            r.bytes_(4); push(F32)
        elif op == 0x44:
            r.bytes_(8); push(F64)
        elif op == 0xD0:
            t = r.u8()
            if t not in REF_TYPES:
                if t in GC_TYPE_BYTES or t < 0x40:  # abstract GC heap type or type index
                    raise err(Code.UNSUPPORTED_PROPOSAL, "typed/gc ref.null heap type")
                raise err(Code.MALFORMED, "ref.null heap type")
            ctx.feat("reference-types", op_at, "ref.null")
            push(t)
        elif op == 0xD1:
            ctx.feat("reference-types", op_at, "ref.is_null")
            t = pop()
            if t is not U and t not in REF_TYPES:
                raise err(Code.TYPE_MISMATCH, "ref.is_null on non-reference")
            push(I32)
        elif op == 0xD2:
            fi = r.u32()
            ctx.feat("reference-types", op_at, "ref.func")
            if fi >= len(ctx.funcs):
                raise err(Code.INVALID_INDEX, f"ref.func {fi}")
            if fi not in ctx.refs:
                raise err(Code.UNDECLARED_FUNC_REF, f"ref.func {fi} not declared")
            push(FUNCREF)
        elif op == 0xFC:
            sub = r.u32()
            if sub in _SAT:
                ctx.feat("sat-float-to-int", op_at, "non-trapping float-to-int")
                if not ctx.uses_float:
                    ctx.uses_float, ctx.float_at = True, op_at
                p, res = _SAT[sub]
                pop(p); push(res)
            elif sub == 8:  # memory.init
                ctx.feat("bulk-memory", op_at, "memory.init")
                di = r.u32(); zero_byte("memory.init"); need_mem()
                _need_data(ctx, di, err)
                pop(I32); pop(I32); pop(I32)
            elif sub == 9:
                ctx.feat("bulk-memory", op_at, "data.drop")
                _need_data(ctx, r.u32(), err)
            elif sub == 10:
                ctx.feat("bulk-memory", op_at, "memory.copy")
                zero_byte("memory.copy"); zero_byte("memory.copy"); need_mem()
                pop(I32); pop(I32); pop(I32)
            elif sub == 11:
                ctx.feat("bulk-memory", op_at, "memory.fill")
                zero_byte("memory.fill"); need_mem()
                pop(I32); pop(I32); pop(I32)
            elif sub == 12:
                ctx.feat("bulk-memory", op_at, "table.init")
                ei, ti = r.u32(), r.u32()
                if ei >= len(ctx.m.elems):
                    raise err(Code.INVALID_INDEX, f"elem {ei}")
                if ctx.m.elems[ei].reftype != table(ti):
                    raise err(Code.TYPE_MISMATCH, "table.init reftype mismatch")
                if ti != 0:
                    ctx.feat("reference-types", op_at, "table.init on table != 0")
                pop(I32); pop(I32); pop(I32)
            elif sub == 13:
                ctx.feat("bulk-memory", op_at, "elem.drop")
                ei = r.u32()
                if ei >= len(ctx.m.elems):
                    raise err(Code.INVALID_INDEX, f"elem {ei}")
            elif sub == 14:
                ctx.feat("bulk-memory", op_at, "table.copy")
                d, s = r.u32(), r.u32()
                if table(d) != table(s):
                    raise err(Code.TYPE_MISMATCH, "table.copy reftype mismatch")
                if d or s:
                    ctx.feat("reference-types", op_at, "table.copy on table != 0")
                pop(I32); pop(I32); pop(I32)
            elif sub == 15:
                ctx.feat("reference-types", op_at, "table.grow")
                t = table(r.u32()); pop(I32); pop(t); push(I32)
            elif sub == 16:
                ctx.feat("reference-types", op_at, "table.size")
                table(r.u32()); push(I32)
            elif sub == 17:
                ctx.feat("reference-types", op_at, "table.fill")
                t = table(r.u32()); pop(I32); pop(t); pop(I32)
            else:
                raise err(Code.UNKNOWN_OPCODE, f"0xfc {sub}")
        else:
            raise err(Code.UNKNOWN_OPCODE, f"opcode 0x{op:02x}")


def _need_data(ctx: _Ctx, di: int, err) -> None:
    if ctx.m.data_count is None:
        raise err(Code.MALFORMED, "data index used without datacount section")
    if di >= ctx.m.data_count:
        raise err(Code.INVALID_INDEX, f"data {di}")


def _n(t) -> str:
    from .decoder import TYPE_NAMES
    return "?" if t is U else TYPE_NAMES.get(t, hex(t))


def _module_level(ctx: _Ctx) -> None:
    m = ctx.m
    n_imp_g = ctx.n_imported_globals
    for i, g in enumerate(m.globals):
        _check_const(ctx, g.init, g.type.valtype, "global", n_imp_g + i)
    for x in m.exports:
        if x.kind == 3 and ctx.globals[x.index].mutable:
            ctx.feat("mutable-globals-import", x.offset, "exported mutable global")
    for e in m.elems:
        if e.offset_expr is not None:
            _check_const(ctx, e.offset_expr, I32, "element", len(ctx.globals))
            if ctx.tables[e.table].elem != e.reftype:
                raise InvalidModule(Code.TYPE_MISMATCH, "element reftype != table reftype",
                                    offset=e.at, section="element")
        for ce in e.exprs or ():
            _check_const(ctx, ce, e.reftype, "element", len(ctx.globals))
    for d in m.datas:
        if d.offset_expr is not None:
            _check_const(ctx, d.offset_expr, I32, "data", len(ctx.globals))
    if m.start is not None:
        t = ctx.types[ctx.funcs[m.start]]
        if t.params or t.results:
            raise InvalidModule(Code.TYPE_MISMATCH, "start function must be [] -> []", section="start")
    for f in m.func_type_indices:
        if len(ctx.types[f].results) > 1:
            ctx.feat("multi-value", 0, "function with >1 result")
    if len(ctx.tables) and any(t.elem == EXTERNREF for t in ctx.tables):
        ctx.feat("reference-types", 0, "externref table")


@boundary
def validate_module(data: bytes, limits: Limits = DEFAULT_LIMITS) -> tuple[ParsedModule, TypedFacts]:
    """Decode (M01), type-check (M02) and derive features (M03) from raw bytes."""
    gov = Governor(limits)
    m = decode(data, limits, gov)
    ctx = _Ctx(m, gov)
    _module_level(ctx)
    n_imp = len(m.imported(0))
    for i, body in enumerate(m.bodies):
        _validate_body(ctx, n_imp + i, body)
    features = set(m.structural_features) | set(ctx.features)
    evidence = list(m.feature_evidence) + [(k, v[0], v[1]) for k, v in sorted(ctx.features.items())
                                           if k not in m.structural_features]
    facts = TypedFacts(
        features=frozenset(features),
        evidence=tuple(evidence),
        uses_float=ctx.uses_float,
        float_evidence_offset=ctx.float_at,
        imports=tuple((i.module, i.name, i.kind) for i in m.imports),
        exports=tuple((x.name, x.kind) for x in m.exports),
        function_count=len(ctx.funcs),
        instruction_count=ctx.instructions,
        section_count=len(m.sections),
        size_bytes=m.size_bytes,
    )
    return m, facts
