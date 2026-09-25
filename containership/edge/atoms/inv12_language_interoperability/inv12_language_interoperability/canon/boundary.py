"""Integrated reference boundary: MC-019 runtime-adapter seam and MC-023 Python binding.

:class:`Instance` models one component instance (its own linear memory, own
resource table, guest language and exported functions).  :class:`Boundary`
performs a complete cross-component call through the real canonical ABI path::

    authorize (MC-048) -> config snapshot (MC-044) -> mapping check (MC-007)
    -> admission (MC-042) -> recursive validation + limits (MC-006/018)
    -> lower args into *callee* memory via checked realloc (MC-010/011/012)
       (own handles move, borrows are lent for the call scope; MC-004/005)
    -> lift args from callee memory -> invoke export
    -> validate result -> lower into callee memory -> lift into caller
    -> post-return exactly once (MC-012) -> metrics/trace (MC-037/038)

Any failure before the export runs rolls back every allocation made for the
call, revokes every borrow, and moves every already-transferred own handle back
to the caller (documented recoverable state: the caller receives *new* handle
identities for compensated resources; the old Handle objects are stale).

The ``Instance`` memory/realloc/table triple is the seam a production Component
Model runtime (e.g. Wasmtime's component API) must implement; this module ships
the in-process reference adapter.  A production runtime binding is **not** part of this
package (see ``docs/COMPATIBILITY.md``).
"""
from __future__ import annotations

import time

from . import layout
from .config import require
from .errors import InteropError
from .layout import HandleCodec
from .limits import LimitPolicy
from .memory import Allocator, CallLifecycle, CheckedRealloc, GuestMemory
from .registry import check_type
from .resources import CallScope, ResourceTable
from .types import HandleT, Interface
from .validate import validate


class Instance:
    def __init__(self, name: str, language: str, exports: dict | None = None,
                 *, memory_bytes: int = 64 * 1024 * 1024):
        self.name = name
        self.language = language
        self.exports = dict(exports or {})
        self.memory = GuestMemory(max_bytes=memory_bytes)
        self._alloc = Allocator(self.memory, base=8)   # keep 0..7 unused (null page)
        self.realloc = CheckedRealloc(self.memory, self._alloc)
        self.table = ResourceTable(name)


class _TableCodec(HandleCodec):
    def __init__(self, src: ResourceTable, dst: ResourceTable, scope: CallScope):
        self.src, self.dst, self.scope = src, dst, scope
        self.moved = []

    def lower(self, value, t):
        if t.kind == "own":
            h = self.src.transfer_own(value, self.dst)
            self.moved.append(h)
            return h.index
        if t.kind == "borrow":
            return self.src.lend(value, self.dst, self.scope).index
        raise InteropError("future/stream handles are not supported over this adapter",
                           code="PK_INTEROP_ASYNC")

    def undo(self):
        """Compensate own-handle moves of a failed lowering (new source handles)."""
        restored = []
        for h in reversed(self.moved):
            try:
                restored.append(self.dst.transfer_own(h, self.src))
            except InteropError:
                pass
        self.moved.clear()
        return restored

    def lift(self, index, t):
        return self.dst.at(index, "own" if t.kind == "own" else "borrow", t.resource)


class Boundary:
    def __init__(self, interface: Interface, config, *, gate=None, capacity=None,
                 metrics=None, tracer=None, limit_policy: LimitPolicy | None = None):
        self.iface = interface
        self.config = config            # ConfigManager
        self.gate = gate
        self.capacity = capacity
        self.metrics = metrics
        self.tracer = tracer
        self.limit_policy = limit_policy

    def _limits(self, snap, type_name):
        if self.limit_policy is not None:
            return self.limit_policy.resolve(self.iface.name, type_name)
        return snap.limits

    def call(self, caller: Instance, callee: Instance, func: str, args: tuple,
             *, token=None, tenant: str = "default"):
        span_cm = (self.tracer.span("inv12.call", interface=self.iface.name,
                                    source_language=caller.language,
                                    target_language=callee.language)
                   if self.tracer else _Null())
        t0 = time.perf_counter()
        with span_cm:
            try:
                result = self._call(caller, callee, func, args, token, tenant)
            except InteropError as e:
                e.interface = e.interface or self.iface.name
                e.source_language = e.source_language or caller.language
                e.target_language = e.target_language or callee.language
                self._count_refusal(e, callee.language)
                raise
            finally:
                if self.metrics:
                    self.metrics.inc("boundary_calls", source_language=caller.language,
                                     target_language=callee.language)
                    self.metrics.observe_us("boundary_latency", (time.perf_counter() - t0) * 1e6,
                                            source_language=caller.language,
                                            target_language=callee.language)
            return result

    def _count_refusal(self, e, lang):
        if not self.metrics:
            return
        m = {"PK_INTEROP_UNREPRESENTABLE": "mapping_refusals",
             "PK_INTEROP_OUT_OF_RANGE": "range_violations",
             "PK_INTEROP_ENCODING": "encoding_refusals"}.get(e.code, "canonicalization_refusals")
        self.metrics.inc(m, code=e.code, language=lang)

    def _call(self, caller, callee, func, args, token, tenant):
        snap = self.config.current                       # one consistent snapshot
        if self.gate is not None:
            self.gate.authorize(token, f"interop.call:{self.iface.name}")
        f = self.iface.functions.get(func)
        if f is None or func not in callee.exports:
            raise InteropError("function not exported", code="PK_INTEROP_UNREPRESENTABLE")
        for inst in (caller, callee):
            require(snap, inst.language)
            for _, pt in f.params:
                check_type(pt, inst.language)
            if f.result is not None:
                check_type(f.result, inst.language)
        if type(args) is not tuple or len(args) != len(f.params):
            raise InteropError("argument count mismatch", code="PK_INTEROP_TYPE_MISMATCH")
        # 1. validate everything before any allocation or handle movement
        vals = []
        for (pn, pt), a in zip(f.params, args, strict=True):
            try:
                vals.append(validate(a, pt, limits=self._limits(snap, pn), table=caller.table))
            except InteropError as e:
                raise e.at(pn)
        admit = self.capacity.admit(tenant) if self.capacity else _Null()
        with admit, CallScope() as scope:
            life = CallLifecycle(callee.realloc)
            life.begin()
            codec = _TableCodec(caller.table, callee.table, scope)
            try:
                ptrs = [layout.lower_to_memory(v, pt, callee.memory, life.alloc, codec)
                        for v, (_, pt) in zip(vals, f.params, strict=True)]
                lifted = tuple(layout.load(callee.memory, p, pt, codec)
                               for p, (_, pt) in zip(ptrs, f.params, strict=True))
            except Exception:
                life.rollback()
                codec.undo()
                raise
            life.called()
            if self.metrics:
                for _, pt in f.params:
                    if isinstance(pt, HandleT):
                        self.metrics.inc("ownership_transfers", direction="in")
            out = callee.exports[func](callee, *lifted)
            life.returned()
            try:
                if f.result is None:
                    if out is not None:
                        raise InteropError("export returned a value for a void function",
                                           code="PK_INTEROP_TYPE_MISMATCH")
                    return None
                rv = validate(out, f.result, limits=self._limits(snap, "result"), table=callee.table)
                back = _TableCodec(callee.table, caller.table, scope)
                rlife = CallLifecycle(caller.realloc)
                rlife.begin()
                try:
                    rp = layout.lower_to_memory(rv, f.result, caller.memory, rlife.alloc, back)
                    res = layout.load(caller.memory, rp, f.result, back)
                except Exception:
                    rlife.rollback()
                    raise
                rlife.called()
                rlife.returned()
                rlife.post_return()
                return res
            finally:
                life.post_return()


class _Null:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False
