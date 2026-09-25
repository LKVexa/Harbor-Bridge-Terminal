"""Production SFI profile, trusted rewriter and independent verifier (C031, C046, A3).

Profile ``PK-SFI-WASM32-MVP-1`` (ADR-0001) - linear block partitioning with heap
masking over a (possibly shared) WebAssembly linear memory:

* Each tenant module is assigned one *partition* ``[base, base + 2**k)`` of the
  linear memory plus an 8-byte dead guard after it (the widest MVP access is 8
  bytes, so an access that starts at the last byte of the partition ends inside
  the guard and never inside a neighbouring partition).
* Every load/store address is rewritten to::

      addr' = ((addr + offset) mod 2**32  &  (2**k - 1))  +  base

  and the instruction's static ``offset`` immediate is folded in and set to 0.
  Out-of-partition addresses are *confined* (wrapped into the partition), which
  matches the semantics of the reference model's ``SandboxRegion.confine``.
* The verifier is independent of the rewriter: it re-parses the exact output
  bytes, re-runs full Wasm type validation, and accepts a memory instruction only
  when it is immediately preceded by the canonical sequence
  ``i32.const MASK; i32.and; i32.const BASE; i32.add`` (stores additionally by a
  single ``local.get`` of the stored value's type), or by a single ``i32.const E``
  with ``BASE <= E <= BASE + MASK`` (statically confined address, folded by the
  rewriter as a C066 optimisation).  Because validated Wasm has a
  structured, statically typed operand stack and none of those five instructions
  is a control instruction or a branch target, the value consumed as the address
  is exactly the masked value.  Anything else is ``SFI_UNMASKED_ACCESS``.
* Control flow: Wasm branches are structured and label-indexed, so a module cannot
  jump into the middle of a mask sequence; return addresses live in the engine's
  protected call stack, never in linear memory (the "shadow stack" property is
  provided by the engine and is recorded as a pinned engine requirement, not
  implemented here).  ``call_indirect`` is confined to the module's own
  non-imported, non-exported, non-growable table, whose element set is reported
  as the permitted indirect target set.
* Policy: function imports are deny-by-default against an allowlist; mutable
  imported globals, imported/exported tables, memory export, ``memory.grow`` and
  data segments outside the partition are rejected.

Native-code properties (pinned base register, code-page W^X/ASLR) are the
engine's responsibility in this profile; they are recorded in the ADR as engine
requirements with a preflight check (``engine.py``) and are NOT claimed here.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from . import wasm
from .errors import SfiError
from .wasm import I32, MEMORY_OPS, Instr, Limits, encode_body, section, split_sections, uleb

PROFILE_ID = "PK-SFI-WASM32-MVP-1"
PROOF_SCHEMA = "PK_SFI_PROOF/1"
VERIFIER_VERSION = "4.3.0"
GUARD_BYTES = wasm.MAX_ACCESS_WIDTH
PAGE = 65536
_U32 = 1 << 32


def canonical_json(obj: Any) -> bytes:
    """Canonical serialization used for every hash/signature (sorted keys, no spaces, UTF-8)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Profile:
    """Immutable SFI profile.  Its digest is bound into every proof and descriptor."""

    region_base: int
    region_log2: int
    function_import_allowlist: tuple[str, ...] = ()
    allow_memory_grow: bool = False
    allow_memory_export: bool = False
    require_imported_memory: bool = False
    profile_id: str = PROFILE_ID

    def __post_init__(self) -> None:
        for name in ("region_base", "region_log2"):
            v = getattr(self, name)
            if type(v) is not int or v < 0:
                raise SfiError("SFI_CONFIG_INVALID", f"{name} must be a non-negative int", field=name)
        if not 12 <= self.region_log2 <= 31:
            raise SfiError("SFI_CONFIG_INVALID", "region_log2 must be in [12, 31]", field="region_log2")
        if self.region_base % 8:
            raise SfiError("SFI_CONFIG_INVALID", "region_base must be 8-byte aligned", field="region_base")
        if self.region_base + self.size + GUARD_BYTES > _U32:
            raise SfiError("SFI_CONFIG_INVALID", "partition + guard exceeds 32-bit address space",
                           field="region_base")
        if self.profile_id != PROFILE_ID:
            raise SfiError("SFI_UNSUPPORTED_VERSION", "unknown SFI profile", expected_version=PROFILE_ID,
                           observed_version=self.profile_id)
        object.__setattr__(self, "function_import_allowlist",
                           tuple(sorted(set(self.function_import_allowlist))))

    @property
    def size(self) -> int:
        return 1 << self.region_log2

    @property
    def mask(self) -> int:
        return self.size - 1

    @property
    def required_memory_bytes(self) -> int:
        return self.region_base + self.size + GUARD_BYTES

    def as_dict(self) -> dict[str, Any]:
        return asdict(self) | {"function_import_allowlist": list(self.function_import_allowlist)}

    def digest(self) -> str:
        return sha256_hex(canonical_json(self.as_dict()))


def _i32(v: int) -> int:
    """Signed 32-bit encoding of an unsigned constant (as i32.const stores it)."""
    v &= _U32 - 1
    return v - _U32 if v >= 1 << 31 else v


def _mask_seq(p: Profile, off: int) -> list[Instr]:
    seq = []
    if off:
        seq += [Instr(0x41, _i32(off), -1), Instr(0x6A, None, -1)]
    return seq + [Instr(0x41, _i32(p.mask), -1), Instr(0x71, None, -1),
                  Instr(0x41, _i32(p.region_base), -1), Instr(0x6A, None, -1)]


# ------------------------------------------------------------------------------ rewriter

@dataclass
class RewriteResult:
    artifact: bytes
    input_sha256: str
    output_sha256: str
    rewritten_accesses: int
    stripped_custom_sections: list[str] = field(default_factory=list)
    constant_folded_accesses: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {"schema": "PK_SFI_REWRITE/1", "input_sha256": self.input_sha256,
                "output_sha256": self.output_sha256, "rewritten_accesses": self.rewritten_accesses,
                "stripped_custom_sections": list(self.stripped_custom_sections), "profile": PROFILE_ID,
                "constant_folded_accesses": self.constant_folded_accesses}


def rewrite(data: bytes, profile: Profile, limits: Limits = Limits()) -> RewriteResult:
    """Insert the canonical mask sequence before every memory access.

    The rewriter is trusted to be *useful*, not to be *correct*: its output is only
    accepted after :func:`verify` independently checks it.
    """
    m = wasm.parse(data, limits)
    ftypes = m.types
    new_bodies = []
    count = 0
    folded = 0
    for fn in m.functions:
        ft = ftypes[fn.type_index]
        nlocals = len(fn.local_types(ft))
        scratch: dict[int, int] = {}
        runs = list(fn.locals)
        out: list[Instr] = []
        for ins in fn.body:
            if ins.op in MEMORY_OPS:
                vt, _, is_store = MEMORY_OPS[ins.op]
                align, off = ins.imm
                count += 1
                # C066 optimisation: a statically known address is confined at rewrite time
                # (one i32.const instead of a 4-instruction mask sequence).  The verifier
                # re-checks the folded constant independently (_check_access).
                ci = len(out) - (2 if is_store else 1)
                if ci >= 0 and out[ci].op == 0x41 and (not is_store or _is_value_push(out[-1], vt, None)):
                    eff = ((out[ci].imm + off) & profile.mask) + profile.region_base
                    out[ci] = Instr(0x41, _i32(eff), -1)
                    out.append(Instr(ins.op, (align, 0), -1))
                    folded += 1
                    continue
                if is_store:
                    if vt not in scratch:
                        scratch[vt] = nlocals + len(scratch)
                        runs.append((1, vt))
                    out.append(Instr(0x21, scratch[vt], -1))
                    out += _mask_seq(profile, off)
                    out.append(Instr(0x20, scratch[vt], -1))
                else:
                    out += _mask_seq(profile, off)
                out.append(Instr(ins.op, (align, 0), -1))
            else:
                out.append(ins)
        if sum(n for n, _ in runs) > limits.max_locals_per_function:
            raise SfiError("SFI_RESOURCE_LIMIT", "rewriting exceeds local limit",
                           limit=limits.max_locals_per_function)
        new_bodies.append(encode_body(runs, out))
    stripped: list[str] = []
    parts = [b"\x00asm\x01\x00\x00\x00"]
    for sid, payload in split_sections(data):
        if sid == 10:
            payload = uleb(len(new_bodies)) + b"".join(new_bodies)
        elif sid == 0:
            name = wasm.Reader(payload).name(limits)
            if name != "name":  # offsets in other custom sections (DWARF, source maps) go stale
                stripped.append(name)
                continue
        parts.append(section(sid, payload))
    out_bytes = b"".join(parts)
    _limit_out(out_bytes, limits)
    return RewriteResult(out_bytes, sha256_hex(data), sha256_hex(out_bytes), count, stripped, folded)


def _limit_out(b: bytes, limits: Limits) -> None:
    if len(b) > limits.max_module_bytes:
        raise SfiError("SFI_RESOURCE_LIMIT", "rewritten module exceeds size limit",
                       limit=limits.max_module_bytes, observed=len(b))


# ------------------------------------------------------------------------------ verifier

def _is_const(ins: Instr, value: int) -> bool:
    return ins.op == 0x41 and (ins.imm & (_U32 - 1)) == (value & (_U32 - 1))


_PUSH_CONST = {0x41: I32, 0x42: wasm.I64, 0x43: wasm.F32, 0x44: wasm.F64}


def _is_value_push(ins: Instr, vt: int, locals_: Optional[list[int]]) -> bool:
    """A single instruction that pushes exactly one value of type ``vt`` and pops nothing."""
    if ins.op in _PUSH_CONST:
        return _PUSH_CONST[ins.op] == vt
    if ins.op == 0x20:
        return locals_ is None or (ins.imm < len(locals_) and locals_[ins.imm] == vt)
    return False


def _check_access(body: list[Instr], p: int, profile: Profile, locals_: list[int]) -> bool:
    ins = body[p]
    vt, width, is_store = MEMORY_OPS[ins.op]
    if ins.imm[1] != 0:
        return False
    k = p
    if is_store:
        k -= 1
        if k < 0 or not _is_value_push(body[k], vt, locals_):
            return False
    # form 1: statically confined constant address
    if k >= 1 and body[k - 1].op == 0x41:
        e = body[k - 1].imm & (_U32 - 1)
        if profile.region_base <= e <= profile.region_base + profile.mask:
            return True  # [e, e+width) lies inside partition + 8-byte guard
    # form 2: canonical dynamic mask sequence (stores: value pushed by local.get only)
    if is_store and body[k].op != 0x20:
        return False
    if k < 4:
        return False
    a, b, c, d = body[k - 4:k]
    return (_is_const(a, profile.mask) and b.op == 0x71 and _is_const(c, profile.region_base)
            and d.op == 0x6A)


def _const_value(expr: list[Instr]) -> Optional[int]:
    return expr[0].imm & (_U32 - 1) if expr and expr[0].op == 0x41 else None


def verify(data: bytes, profile: Profile, limits: Limits = Limits(), *, cancel=None) -> dict[str, Any]:
    """Verify the exact ``data`` bytes against ``profile``; return a deterministic proof."""
    m = wasm.parse(data, limits, cancel=cancel)
    # --- import / export / table / memory policy -------------------------------------
    imports = []
    for imp in m.imports:
        key = f"{imp.module}.{imp.name}"
        if imp.kind == 0:
            if key not in profile.function_import_allowlist:
                raise SfiError("SFI_POLICY_REJECTED", "function import not in allowlist",
                               reason="import not allowlisted", target=key)
            imports.append(key)
        elif imp.kind == 1:
            raise SfiError("SFI_POLICY_REJECTED", "imported tables are not permitted", target=key,
                           reason="imported table")
        elif imp.kind == 3 and imp.desc[1]:
            raise SfiError("SFI_POLICY_REJECTED", "mutable imported globals are not permitted", target=key,
                           reason="mutable imported global")
    for nm, kind, _ in m.exports:
        if kind == 1:
            raise SfiError("SFI_POLICY_REJECTED", "exported tables are not permitted", target=nm,
                           reason="exported table")
        if kind == 2 and not profile.allow_memory_export:
            raise SfiError("SFI_POLICY_REJECTED", "memory export not permitted by profile", target=nm,
                           reason="exported memory")
    mems = m.all_memories()
    imported_mem = any(i.kind == 2 for i in m.imports)
    if profile.require_imported_memory and mems and not imported_mem:
        raise SfiError("SFI_POLICY_REJECTED", "profile requires the shared memory to be imported",
                       reason="memory not imported")
    mem_info = None
    if mems:
        mn, mx = mems[0]
        if mn * PAGE < profile.required_memory_bytes:
            raise SfiError("SFI_POLICY_REJECTED", "declared minimum memory smaller than partition + guard",
                           reason="memory too small", limit=profile.required_memory_bytes, observed=mn * PAGE)
        mem_info = {"min_pages": mn, "max_pages": mx, "imported": imported_mem}
    for off, blob in m.data:
        start = _const_value(off)
        if start is None:
            raise SfiError("SFI_POLICY_REJECTED", "data segment offset must be i32.const",
                           reason="non-constant data offset")
        if start < profile.region_base or start + len(blob) > profile.region_base + profile.size:
            raise SfiError("SFI_POLICY_REJECTED", "data segment outside the tenant partition",
                           reason="data outside partition", observed=start)
    targets: set[int] = set()
    for off, funcs in m.elements:
        if _const_value(off) is None:
            raise SfiError("SFI_POLICY_REJECTED", "element offset must be i32.const",
                           reason="non-constant element offset")
        targets.update(funcs)
    tables = m.all_tables()
    if tables and tables[0][1] != tables[0][0]:  # max absent (growable) or max != min
        raise SfiError("SFI_POLICY_REJECTED", "table must be non-growable (max == min)", reason="growable table")
    # --- per-instruction confinement proof --------------------------------------------
    loads = stores = indirect_sites = 0
    unmasked: list[int] = []
    for fi, fn in enumerate(m.functions):
        locals_ = fn.local_types(m.types[fn.type_index])
        for p, ins in enumerate(fn.body):
            if ins.op in MEMORY_OPS:
                if MEMORY_OPS[ins.op][2]:
                    stores += 1
                else:
                    loads += 1
                if not _check_access(fn.body, p, profile, locals_):
                    unmasked.append(ins.offset)
            elif ins.op == 0x40 and not profile.allow_memory_grow:
                raise SfiError("SFI_POLICY_REJECTED", "memory.grow not permitted by profile",
                               reason="memory.grow", instruction_offset=ins.offset)
            elif ins.op == 0x11:
                indirect_sites += 1
    if unmasked:
        raise SfiError("SFI_UNMASKED_ACCESS", f"{len(unmasked)} memory access(es) not confined",
                       unmasked_count=len(unmasked), sample_offsets=unmasked[:5])
    return {
        "schema": PROOF_SCHEMA,
        "result": "VERIFIED",
        "profile_id": profile.profile_id,
        "profile_sha256": profile.digest(),
        "verifier_version": VERIFIER_VERSION,
        "artifact_sha256": sha256_hex(bytes(data)),
        "artifact_bytes": len(data),
        "region": {"base": profile.region_base, "size": profile.size, "guard": GUARD_BYTES},
        "memory": mem_info,
        "functions": len(m.functions),
        "instructions": m.instruction_count,
        "memory_accesses": {"loads": loads, "stores": stores, "confined": loads + stores},
        "indirect_call_sites": indirect_sites,
        "permitted_indirect_targets": sorted(targets),
        "function_imports": sorted(imports),
        "exports": sorted(nm for nm, _, _ in m.exports),
    }


def proof_digest(proof: dict[str, Any]) -> str:
    return sha256_hex(canonical_json(proof))


def reference_crosscheck(proof: dict[str, Any], address_samples: list[int]) -> list[tuple[int, int]]:
    """Differential check against the Python reference model (``sfi_core``).

    Returns (address, confined) pairs computed by the reference ``SandboxRegion``
    for the proof's partition.  The production validator stays authoritative for
    binary completeness; this only detects semantic divergence of the mask formula.
    """
    from ..sfi_core import SandboxRegion

    region = SandboxRegion(proof["region"]["base"], proof["region"]["size"])
    return [(a, region.confine(a & (_U32 - 1))) for a in address_samples]


def check_partitions(profiles: list[Profile]) -> None:
    """Refuse co-resident profiles whose partitions (including the 8-byte guard) overlap.

    Adversarial review (2026-09-22) confirmed the guard is load-bearing: an 8-byte store masked to the
    last partition byte writes up to 7 bytes past ``base + size``.  Any tenant placement that shares one
    linear memory MUST pass this check (W-04: a central allocator that calls it is still open).
    """
    spans = sorted((p.region_base, p.region_base + p.size + GUARD_BYTES) for p in profiles)
    for (a0, a1), (b0, _) in zip(spans, spans[1:]):
        if b0 < a1:
            raise SfiError("SFI_POLICY_REJECTED", "tenant partitions overlap (guard included)",
                           reason="partition overlap", observed=b0, limit=a1)
