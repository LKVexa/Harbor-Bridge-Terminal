"""Binary-derived seal facts (MC-001 syscall surface, MC-002 SAS proof, MC-003 capability detection).

Nothing in this module reads a caller claim.  Input is a parsed ``ElfImage``; output is a
``SealFacts`` record in which every fact names the binary evidence it was derived from.

Toolchain profiles (docs/FORMATS.md):

* ``unikraft``  - marker: a *defined* ``ukplat_entry`` symbol.  Syscall surface: every defined
  ``uk_syscall_r_<name>`` / ``uk_syscall_e_<name>`` handler (Unikraft's naming convention for
  its syscall shim).  NOTE: the fixtures in tests/fixtures are built locally with gcc to follow
  this convention; they are not upstream Unikraft builds (W-TOOLCHAIN).
* ``solo5``     - marker: a *defined* ``solo5_app_main`` symbol.  Surface: every referenced
  ``solo5_<call>`` hypercall.  Modelled on the public Solo5 API names; same caveat.

An image with no recognised marker is ``UK_SEAL_UNKNOWN_TOOLCHAIN``; an image with no symbol
table at all (stripped) is ``UK_SEAL_NO_EVIDENCE`` unless a *verified* provenance attestation
supplies the facts (``from_attestation``) - the caller's metadata never does.

Known limitation (recorded in THREAT_MODEL T-11): a raw ``syscall``/``svc`` instruction inlined
without a named handler is not detected by symbol analysis.  The profiles only admit toolchains
whose syscall path is the named shim, and the VMM seccomp/hypercall filter (MC-009) is the
second, enforcing layer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..errors import UkError
from .elf import ET_DYN, PF_W, PF_X, PT_LOAD, ElfImage

FACTS_VERSION = "inv27-facts/1.0.1"

MULTIPROCESS = frozenset({"fork", "vfork", "clone", "clone3", "posix_spawn", "posix_spawnp", "execve", "execveat",
                          "execv", "execvp", "execvpe", "execl", "execlp", "execle", "fexecve", "system", "popen",
                          "wait4", "waitpid"})
DYNLOAD = frozenset({"dlopen", "dlmopen", "dlsym", "dlvsym", "__libc_dlopen_mode", "_dl_open", "_dl_map_object"})
DEBUG = frozenset({"ptrace", "process_vm_readv", "process_vm_writev", "gdb_stub_init", "uk_gdb_init",
                   "shell_main", "sh_main", "busybox_main", "uk_shell_init"})
_SC = re.compile(r"^uk_syscall_[re]_([a-z0-9_]{1,40})$")
_SOLO5 = re.compile(r"^solo5_([a-z0-9_]{1,40})$")
SYSCALL_VOCAB_NOTE = "canonical names = Linux syscall names (Unikraft) or solo5 hypercall names prefixed 'solo5.'"

PROFILES = {
    "unikraft": {"marker": "ukplat_entry", "verifier": "inv27-profile-unikraft/1.0.0"},
    "solo5": {"marker": "solo5_app_main", "verifier": "inv27-profile-solo5/1.0.0"},
}


@dataclass(frozen=True)
class Capability:
    name: str
    category: str       # multiprocess | dynload | debug
    evidence: str       # e.g. "symtab:undefined:fork"


@dataclass(frozen=True)
class SealFacts:
    facts_version: str
    source: str                 # "binary" | "attestation"
    toolchain: str
    profile_verifier: str
    architecture: str
    syscalls: frozenset
    syscall_evidence: tuple     # (canonical, raw symbol) pairs, for forensics
    capabilities: tuple         # Capability records (empty for a sealed image)
    interp: str | None
    needed: tuple
    wx_segments: int
    sas_proof: dict             # positive evidence list + verdict

    def to_dict(self) -> dict:
        return {"facts_version": self.facts_version, "source": self.source, "toolchain": self.toolchain,
                "profile_verifier": self.profile_verifier, "architecture": self.architecture,
                "syscalls": sorted(self.syscalls), "syscall_evidence": [list(x) for x in self.syscall_evidence],
                "capabilities": [c.__dict__ for c in self.capabilities], "interp": self.interp,
                "needed": list(self.needed), "wx_segments": self.wx_segments, "sas_proof": self.sas_proof}


def _canon(sym: str) -> str:
    return sym.lstrip("_").split("@", 1)[0]


def identify_toolchain(elf: ElfImage) -> str:
    if not elf.symbols:
        raise UkError("UK_SEAL_NO_EVIDENCE", "image has no symbol table; binary facts cannot be derived")
    defined = {s.name for s in elf.symbols if s.defined and s.type == "func"}
    hits = [name for name, p in PROFILES.items() if p["marker"] in defined]
    if len(hits) != 1:
        raise UkError("UK_SEAL_UNKNOWN_TOOLCHAIN", "no single toolchain marker found" if not hits
                      else f"ambiguous toolchain markers {sorted(hits)}", markers=hits)
    return hits[0]


def detect_capabilities(elf: ElfImage) -> tuple:
    caps: dict[tuple, Capability] = {}
    for s in elf.symbols:
        if not s.name:
            continue
        base = _canon(s.name)
        m = _SC.match(s.name)
        if m:
            base = m.group(1)
        for cat, vocab in (("multiprocess", MULTIPROCESS), ("dynload", DYNLOAD), ("debug", DEBUG)):
            if base in vocab:
                kind = "defined" if s.defined else "undefined"
                caps.setdefault((cat, base), Capability(base, cat, f"{s.table}:{kind}:{s.name}"))
    return tuple(sorted(caps.values(), key=lambda c: (c.category, c.name)))


def derive_syscalls(elf: ElfImage, toolchain: str) -> tuple[frozenset, tuple]:
    pairs = set()
    for s in elf.symbols:
        if toolchain == "unikraft":
            m = _SC.match(s.name)
            # any defined symbol counts, whatever its st_type: a NOTYPE/OBJECT/IFUNC handler is still code
            # (v4.3.0 review finding: a type=="func" gate let an @notype uk_syscall_r_socket evade A10)
            if m and s.defined:
                pairs.add((m.group(1), s.name))
        elif toolchain == "solo5":
            m = _SOLO5.match(s.name)
            if m and s.name != "solo5_app_main":
                pairs.add(("solo5." + m.group(1), s.name))
    ordered = tuple(sorted(pairs))
    return frozenset(p[0] for p in ordered), ordered


def prove_sas(elf: ElfImage, toolchain: str, caps: tuple) -> dict:
    """Positive single-address-space proof.  Every clause must hold; each records its evidence."""
    exec_loads = [s for s in elf.segments if s.type == PT_LOAD and s.flags & PF_X]
    clauses = [
        ("no_program_interpreter", elf.interp is None, f"PT_INTERP={elf.interp!r}"),
        ("no_shared_object_dependencies", not elf.needed, f"DT_NEEDED={list(elf.needed)}"),
        ("self_contained_executable", elf.e_type != ET_DYN or elf.interp is None,
         f"e_type={elf.e_type}"),
        ("entry_in_executable_load", any(s.vaddr <= elf.entry < s.vaddr + s.memsz for s in exec_loads),
         f"entry={elf.entry:#x}"),
        ("toolchain_marker_defined", True, f"profile={toolchain} marker={PROFILES[toolchain]['marker']}"),
        ("no_process_creation", not any(c.category == "multiprocess" for c in caps),
         [c.evidence for c in caps if c.category == "multiprocess"]),
        ("no_runtime_loader", not any(c.category == "dynload" for c in caps),
         [c.evidence for c in caps if c.category == "dynload"]),
    ]
    ok = all(c[1] for c in clauses)
    return {"proof_type": "static-structure+toolchain-profile", "verifier": PROFILES[toolchain]["verifier"],
            "confidence": "binary-derived", "proven": ok,
            "clauses": [{"clause": n, "holds": bool(h), "evidence": e} for n, h, e in clauses]}


def derive(elf: ElfImage) -> SealFacts:
    """Derive facts from the binary.  Raises only for *missing evidence*; policy is applied in admission."""
    toolchain = identify_toolchain(elf)
    caps = detect_capabilities(elf)
    syscalls, ev = derive_syscalls(elf, toolchain)
    wx = sum(1 for s in elf.segments if s.type == PT_LOAD and s.flags & PF_W and s.flags & PF_X)
    return SealFacts(FACTS_VERSION, "binary", toolchain, PROFILES[toolchain]["verifier"], elf.machine, syscalls, ev,
                     caps, elf.interp, elf.needed, wx, prove_sas(elf, toolchain, caps))


def from_attestation(elf: ElfImage, attested: dict) -> SealFacts:
    """Facts for a stripped image, taken from a provenance statement whose signature has ALREADY been
    verified against the trust root.  Structural facts are still read from the binary."""
    toolchain = attested.get("toolchain")
    if toolchain not in PROFILES:
        raise UkError("UK_SEAL_UNKNOWN_TOOLCHAIN", f"attested toolchain {toolchain!r} has no profile")
    sc = attested.get("syscalls")
    if not isinstance(sc, list) or not all(isinstance(x, str) and x for x in sc) or len(sc) > 512:
        raise UkError("UK_PROVENANCE_INVALID", "attested syscalls must be a list of names")
    wx = sum(1 for s in elf.segments if s.type == PT_LOAD and s.flags & PF_W and s.flags & PF_X)
    exec_loads = [s for s in elf.segments if s.type == PT_LOAD and s.flags & PF_X]
    structural = elf.interp is None and not elf.needed and any(
        s.vaddr <= elf.entry < s.vaddr + s.memsz for s in exec_loads)
    proof = {"proof_type": "signed-build-attestation+static-structure", "verifier": PROFILES[toolchain]["verifier"],
             "confidence": "attested", "proven": bool(structural and attested.get("single_address_space") is True),
             "clauses": [{"clause": "structural", "holds": structural, "evidence": "PT_INTERP/DT_NEEDED/entry"},
                         {"clause": "attested_sas", "holds": attested.get("single_address_space") is True,
                          "evidence": "provenance.predicate.attested_facts"}]}
    return SealFacts(FACTS_VERSION, "attestation", toolchain, PROFILES[toolchain]["verifier"], elf.machine,
                     frozenset(sc), tuple((x, "attested") for x in sorted(set(sc))), (), elf.interp, elf.needed, wx,
                     proof)
