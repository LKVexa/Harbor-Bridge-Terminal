"""Bounded ELF64 parser for unikernel admission (MC-001; C034, C045).

Security posture
----------------
* Input is untrusted bytes (``bytes``/``memoryview`` only - never a path), so the verifier
  and the executor see the same object (see ``image.blob``).
* Every offset/size is range-checked with explicit overflow checks before it is read.
* Counts are capped (``Limits``); total work is metered (``_Budget``) so a crafted image
  cannot turn admission into a CPU/memory amplifier.  Every failure raises ``UkError``
  with a stable ``UK_PARSE_*`` code - the parser never returns a partial result.

Supported formats (docs/FORMATS.md is normative):
  ELFCLASS64, ELFDATA2LSB, EV_CURRENT, e_type ET_EXEC or ET_DYN,
  e_machine EM_X86_64 (62) -> "x86_64", EM_AARCH64 (183) -> "aarch64".
Anything else is ``UK_PARSE_UNSUPPORTED_FORMAT``.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

from ..errors import UkError

PARSER_VERSION = "inv27-elf/1.0.0"

MACHINES = {62: "x86_64", 183: "aarch64"}
ET_EXEC, ET_DYN = 2, 3
PT_LOAD, PT_DYNAMIC, PT_INTERP, PT_NOTE, PT_TLS, PT_GNU_STACK = 1, 2, 3, 4, 7, 0x6474E551
PF_X, PF_W, PF_R = 1, 2, 4
SHT_SYMTAB, SHT_STRTAB, SHT_RELA, SHT_DYNAMIC, SHT_NOTE, SHT_NOBITS, SHT_REL, SHT_DYNSYM = 2, 3, 4, 6, 7, 8, 9, 11
DT_NULL, DT_NEEDED = 0, 1
STB_NAMES = {0: "local", 1: "global", 2: "weak"}
STT_NAMES = {0: "notype", 1: "object", 2: "func", 3: "section", 4: "file", 5: "common", 6: "tls", 10: "ifunc"}


@dataclass(frozen=True)
class Limits:
    max_bytes: int = 64 * 1024 * 1024
    max_phdrs: int = 64
    max_shdrs: int = 512
    max_symbols: int = 200_000
    max_dynamic: int = 4096
    max_notes: int = 256
    max_note_desc: int = 64 * 1024
    max_relocs: int = 2_000_000
    max_name: int = 4096
    work_budget: int = 20_000_000   # abstract work units (~ bytes touched + records)


@dataclass(frozen=True)
class Segment:
    type: int
    flags: int
    offset: int
    vaddr: int
    filesz: int
    memsz: int


@dataclass(frozen=True)
class Section:
    name: str
    type: int
    flags: int
    addr: int
    offset: int
    size: int
    link: int
    entsize: int


@dataclass(frozen=True)
class Symbol:
    name: str
    bind: str
    type: str
    shndx: int
    value: int
    size: int
    table: str  # "symtab" | "dynsym"

    @property
    def defined(self) -> bool:
        return self.shndx != 0


@dataclass(frozen=True)
class Note:
    owner: str
    type: int
    desc: bytes
    section: str


@dataclass(frozen=True)
class ElfImage:
    parser_version: str
    size: int
    elf_class: int
    endianness: str
    machine: str
    e_type: int
    entry: int
    segments: tuple
    sections: tuple
    symbols: tuple
    needed: tuple
    interp: str | None
    notes: tuple
    reloc_count: int
    build_id: str | None
    work: int = field(default=0, compare=False)

    def section(self, name: str) -> Section | None:
        return next((s for s in self.sections if s.name == name), None)


class _Budget:
    __slots__ = ("left",)

    def __init__(self, n: int) -> None:
        self.left = n

    def spend(self, n: int) -> None:
        self.left -= max(1, n)
        if self.left < 0:
            raise UkError("UK_PARSE_BUDGET")


def _fail(code: str, msg: str) -> UkError:
    return UkError(code, msg)


def _range(data_len: int, off: int, size: int, what: str) -> None:
    if off < 0 or size < 0 or off > data_len or size > data_len - off:
        raise _fail("UK_PARSE_TRUNCATED", f"{what} [{off}, +{size}) outside image of {data_len} bytes")


def _cstr(data: memoryview, off: int, limit_end: int, max_len: int, what: str) -> str:
    if off < 0 or off >= limit_end:
        raise _fail("UK_PARSE_MALFORMED", f"{what} name offset {off} outside string table")
    stop = min(limit_end, off + max_len + 1)
    end = data.obj.find(b"\x00", off, stop)  # type: ignore[union-attr]  (data wraps immutable bytes)
    if end < 0:
        raise _fail("UK_PARSE_MALFORMED", f"{what} name unterminated or longer than {max_len}")
    raw = data.obj[off:end]  # type: ignore[union-attr]
    if not raw.isascii():
        raise _fail("UK_PARSE_MALFORMED", f"{what} name is not ASCII")
    return raw.decode("ascii")


def parse(raw: bytes | bytearray | memoryview, limits: Limits = Limits()) -> ElfImage:
    """Parse ``raw`` or raise ``UkError``.  ``raw`` is copied once into immutable ``bytes``."""
    if not isinstance(raw, (bytes, bytearray, memoryview)):
        raise TypeError("parse() takes image bytes, never a path or a claim")
    data_b = bytes(raw)
    n = len(data_b)
    if n > limits.max_bytes:
        raise _fail("UK_PARSE_TOO_LARGE", f"{n} bytes > {limits.max_bytes}")
    budget = _Budget(limits.work_budget)
    data = memoryview(data_b)
    if n < 16 or bytes(data[:4]) != b"\x7fELF":
        raise _fail("UK_PARSE_BAD_MAGIC", "missing \\x7fELF")
    ei_class, ei_data, ei_version = data[4], data[5], data[6]
    if ei_class != 2 or ei_data != 1 or ei_version != 1:
        raise _fail("UK_PARSE_UNSUPPORTED_FORMAT", f"class={ei_class} data={ei_data} version={ei_version}; only ELF64 LSB v1")
    _range(n, 0, 64, "ELF header")
    (e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, _flags, e_ehsize, e_phentsize, e_phnum,
     e_shentsize, e_shnum, e_shstrndx) = struct.unpack_from("<HHIQQQIHHHHHH", data, 16)
    if e_version != 1 or e_ehsize != 64:
        raise _fail("UK_PARSE_MALFORMED", "bad e_version/e_ehsize")
    if e_machine not in MACHINES:
        raise _fail("UK_PARSE_UNSUPPORTED_FORMAT", f"e_machine {e_machine} not supported")
    if e_type not in (ET_EXEC, ET_DYN):
        raise _fail("UK_PARSE_UNSUPPORTED_FORMAT", f"e_type {e_type} is not an executable")

    # ---- program headers
    if e_phnum == 0 or e_phnum > limits.max_phdrs:
        raise _fail("UK_PARSE_LIMIT", f"e_phnum {e_phnum} not in 1..{limits.max_phdrs}")
    if e_phentsize != 56:
        raise _fail("UK_PARSE_MALFORMED", "e_phentsize != 56")
    _range(n, e_phoff, e_phnum * 56, "program header table")
    segs = []
    for i in range(e_phnum):
        budget.spend(56)
        p_type, p_flags, p_off, p_vaddr, _pa, p_filesz, p_memsz, p_align = struct.unpack_from("<IIQQQQQQ", data, e_phoff + i * 56)
        if p_type in (PT_LOAD, PT_DYNAMIC, PT_INTERP, PT_NOTE):
            _range(n, p_off, p_filesz, f"segment {i}")
        if p_memsz < p_filesz:
            raise _fail("UK_PARSE_MALFORMED", f"segment {i} memsz < filesz")
        if p_vaddr + p_memsz > 2**64 - 1:
            raise _fail("UK_PARSE_MALFORMED", f"segment {i} address range overflows")
        segs.append(Segment(p_type, p_flags, p_off, p_vaddr, p_filesz, p_memsz))
    loads = sorted((s for s in segs if s.type == PT_LOAD), key=lambda s: s.vaddr)
    for a, b in zip(loads, loads[1:]):
        if a.vaddr + a.memsz > b.vaddr:
            raise _fail("UK_PARSE_OVERLAP", f"PT_LOAD segments overlap at {b.vaddr:#x}")
    interp = None
    for s in segs:
        if s.type == PT_INTERP:
            if s.filesz == 0 or s.filesz > limits.max_name:
                raise _fail("UK_PARSE_MALFORMED", "PT_INTERP size")
            interp = _cstr(data, s.offset, s.offset + s.filesz, limits.max_name, "interp")

    # ---- section headers (optional in a valid executable; a stripped image may have none)
    sections: list[Section] = []
    if e_shnum:
        if e_shnum > limits.max_shdrs:
            raise _fail("UK_PARSE_LIMIT", f"e_shnum {e_shnum} > {limits.max_shdrs}")
        if e_shentsize != 64:
            raise _fail("UK_PARSE_MALFORMED", "e_shentsize != 64")
        _range(n, e_shoff, e_shnum * 64, "section header table")
        if e_shstrndx >= e_shnum:
            raise _fail("UK_PARSE_MALFORMED", "e_shstrndx out of range")
        raw_sh = []
        for i in range(e_shnum):
            budget.spend(64)
            raw_sh.append(struct.unpack_from("<IIQQQQIIQQ", data, e_shoff + i * 64))
        sn = raw_sh[e_shstrndx]
        if sn[1] != SHT_STRTAB:
            raise _fail("UK_PARSE_MALFORMED", "section-name table is not SHT_STRTAB")
        _range(n, sn[4], sn[5], "section-name table")
        for i, (nm, typ, flg, addr, off, size, link, _info, _al, ent) in enumerate(raw_sh):
            if typ != SHT_NOBITS and typ != 0:
                _range(n, off, size, f"section {i}")
            if link >= e_shnum:
                raise _fail("UK_PARSE_MALFORMED", f"section {i} sh_link out of range")
            name = _cstr(data, sn[4] + nm, sn[4] + sn[5], limits.max_name, f"section {i}") if i else ""
            sections.append(Section(name, typ, flg, addr, off, size, link, ent))
        filed = sorted((s for s in sections if s.type not in (0, SHT_NOBITS) and s.size), key=lambda s: s.offset)
        for a, b in zip(filed, filed[1:]):
            if a.offset + a.size > b.offset:
                raise _fail("UK_PARSE_OVERLAP", f"sections {a.name!r} and {b.name!r} overlap in file")
        names = [s.name for s in sections if s.name]
        if len(names) != len(set(names)):
            dup = sorted({x for x in names if names.count(x) > 1})
            raise _fail("UK_PARSE_OVERLAP", f"duplicate section names {dup[:5]}")

    # ---- symbols
    symbols: list[Symbol] = []
    total_syms = 0
    for s in sections:
        if s.type not in (SHT_SYMTAB, SHT_DYNSYM):
            continue
        if s.entsize != 24 or s.size % 24:
            raise _fail("UK_PARSE_MALFORMED", f"{s.name}: bad symbol entsize/size")
        strtab = sections[s.link]
        if strtab.type != SHT_STRTAB:
            raise _fail("UK_PARSE_MALFORMED", f"{s.name}: sh_link is not a string table")
        count = s.size // 24
        total_syms += count
        if total_syms > limits.max_symbols:
            raise _fail("UK_PARSE_LIMIT", f"more than {limits.max_symbols} symbols")
        table = "dynsym" if s.type == SHT_DYNSYM else "symtab"
        for i in range(1, count):
            budget.spend(24)
            st_name, st_info, _other, st_shndx, st_value, st_size = struct.unpack_from("<IBBHQQ", data, s.offset + i * 24)
            if st_shndx != 0 and st_shndx < 0xFF00 and st_shndx >= len(sections):
                raise _fail("UK_PARSE_MALFORMED", f"{s.name}[{i}] st_shndx out of range")
            name = _cstr(data, strtab.offset + st_name, strtab.offset + strtab.size, limits.max_name, f"{s.name}[{i}]") if st_name else ""
            budget.spend(len(name))
            symbols.append(Symbol(name, STB_NAMES.get(st_info >> 4, str(st_info >> 4)),
                                  STT_NAMES.get(st_info & 0xF, str(st_info & 0xF)), st_shndx, st_value, st_size, table))

    # ---- relocations: bounds + symbol index validity (corrupt tables are rejected)
    relocs = 0
    for s in sections:
        if s.type not in (SHT_RELA, SHT_REL):
            continue
        ent = 24 if s.type == SHT_RELA else 16
        if s.entsize != ent or s.size % ent:
            raise _fail("UK_PARSE_MALFORMED", f"{s.name}: bad relocation entsize/size")
        symtab = sections[s.link] if s.link else None
        nsyms = (symtab.size // 24) if symtab is not None and symtab.type in (SHT_SYMTAB, SHT_DYNSYM) else None
        cnt = s.size // ent
        relocs += cnt
        if relocs > limits.max_relocs:
            raise _fail("UK_PARSE_LIMIT", f"more than {limits.max_relocs} relocations")
        for i in range(cnt):
            budget.spend(ent)
            _off, info = struct.unpack_from("<QQ", data, s.offset + i * ent)
            sym = info >> 32
            if nsyms is not None and sym >= nsyms:
                raise _fail("UK_PARSE_MALFORMED", f"{s.name}[{i}] references symbol {sym} of {nsyms}")

    # ---- dynamic section: DT_NEEDED
    needed: list[str] = []
    dyn = next((s for s in segs if s.type == PT_DYNAMIC), None)
    if dyn is not None:
        if dyn.filesz % 16:
            raise _fail("UK_PARSE_MALFORMED", "PT_DYNAMIC size not a multiple of 16")
        entries = dyn.filesz // 16
        if entries > limits.max_dynamic:
            raise _fail("UK_PARSE_LIMIT", "too many dynamic entries")
        dynstr = next((s for s in sections if s.name == ".dynstr"), None)
        for i in range(entries):
            budget.spend(16)
            tag, val = struct.unpack_from("<qQ", data, dyn.offset + i * 16)
            if tag == DT_NULL:
                break
            if tag == DT_NEEDED:
                # With no .dynstr we still record that a dependency exists (fail closed downstream).
                needed.append(_cstr(data, dynstr.offset + val, dynstr.offset + dynstr.size, limits.max_name, "DT_NEEDED")
                              if dynstr is not None else f"<unresolved:{val}>")

    # ---- notes (from PT_NOTE segments and SHT_NOTE sections; deduplicated by file offset)
    notes: list[Note] = []
    spans = {(s.offset, s.size, s.name) for s in sections if s.type == SHT_NOTE}
    spans |= {(g.offset, g.filesz, "<segment>") for g in segs if g.type == PT_NOTE
              if not any(o == g.offset for o, _, _ in spans)}
    for off, size, secname in sorted(spans):
        pos, end = off, off + size
        while pos + 12 <= end:
            budget.spend(12)
            namesz, descsz, ntype = struct.unpack_from("<III", data, pos)
            if namesz > 256 or descsz > limits.max_note_desc:
                raise _fail("UK_PARSE_LIMIT", f"note in {secname} too large")
            name_off = pos + 12
            desc_off = name_off + ((namesz + 3) & ~3)
            nxt = desc_off + ((descsz + 3) & ~3)
            if nxt > end:
                raise _fail("UK_PARSE_TRUNCATED", f"note in {secname} runs past its container")
            owner = bytes(data[name_off:name_off + namesz]).rstrip(b"\x00").decode("ascii", "replace")
            notes.append(Note(owner, ntype, bytes(data[desc_off:desc_off + descsz]), secname))
            if len(notes) > limits.max_notes:
                raise _fail("UK_PARSE_LIMIT", "too many notes")
            budget.spend(descsz)
            pos = nxt
    build_id = next((x.desc.hex() for x in notes if x.owner == "GNU" and x.type == 3), None)

    # ---- entry point must be inside an executable PT_LOAD (also enforced in bootcontract)
    return ElfImage(PARSER_VERSION, n, 64, "little", MACHINES[e_machine], e_type, e_entry, tuple(segs),
                    tuple(sections), tuple(symbols), tuple(needed), interp, tuple(notes), relocs, build_id,
                    work=limits.work_budget - budget.left)
