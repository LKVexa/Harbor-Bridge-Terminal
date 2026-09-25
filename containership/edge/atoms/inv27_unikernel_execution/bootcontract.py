"""Entry-point / boot-contract enforcement (MC-008; owns "Image entry-point and boot contract").

Checks, all against the parsed binary (never the manifest alone):
  B1 the ELF entry address lies inside exactly one executable PT_LOAD segment
  B2 no PT_LOAD is both writable and executable (W^X)
  B3 if the manifest names ``entry_symbol``, that symbol is a defined function whose value == e_entry
  B4 the guest memory budget covers every PT_LOAD's memsz plus a fixed 4 MiB boot reserve
  B5 the image has at least one PT_LOAD and the loadable span fits inside the requested memory
"""
from __future__ import annotations

from .errors import UkError
from .image.elf import PF_W, PF_X, PT_LOAD, ElfImage
from .manifest import SealManifest

BOOT_RESERVE_MIB = 4


def enforce(elf: ElfImage, m: SealManifest) -> dict:
    loads = [s for s in elf.segments if s.type == PT_LOAD]
    if not loads:
        raise UkError("UK_BOOT_CONTRACT", "B5: no loadable segment")
    exec_hits = [s for s in loads if s.flags & PF_X and s.vaddr <= elf.entry < s.vaddr + s.memsz]
    if len(exec_hits) != 1:
        raise UkError("UK_BOOT_CONTRACT", f"B1: entry {elf.entry:#x} not in exactly one executable segment")
    if any(s.flags & PF_W and s.flags & PF_X for s in loads):
        raise UkError("UK_SEAL_WX", "B2: writable+executable PT_LOAD")
    if m.boot.entry_symbol:
        syms = [s for s in elf.symbols if s.name == m.boot.entry_symbol and s.defined and s.type == "func"]
        if len(syms) != 1 or syms[0].value != elf.entry:
            raise UkError("UK_BOOT_CONTRACT", f"B3: entry_symbol {m.boot.entry_symbol!r} is not the ELF entry point")
    need = sum(s.memsz for s in loads)
    budget = m.boot.memory_mib * 1024 * 1024
    if need + BOOT_RESERVE_MIB * 1024 * 1024 > budget:
        raise UkError("UK_BOOT_CONTRACT", f"B4: image needs {need} bytes + reserve, memory_mib={m.boot.memory_mib}")
    span = max(s.vaddr + s.memsz for s in loads) - min(s.vaddr for s in loads)
    if span > budget:
        raise UkError("UK_BOOT_CONTRACT", f"B5: loadable span {span} exceeds guest memory")
    return {"entry": f"{elf.entry:#x}", "load_bytes": need, "span": span, "memory_mib": m.boot.memory_mib,
            "vcpus": m.boot.vcpus, "clauses": ["B1", "B2", "B3" if m.boot.entry_symbol else "B3:n/a", "B4", "B5"]}
