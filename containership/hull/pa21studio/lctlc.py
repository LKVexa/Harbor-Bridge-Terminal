"""The COLUMNED LCTL layer: scaffolds, and a thin honest wrapper on the
runtime's own toolchain.

The studio does not reimplement the language. `tools/lctl430.py` inside the
runtime is the compiler and verifier of record, and every function here shells
out to it and returns what it said. Reimplementing the check would mean
shipping a second opinion about what the language is, and the second opinion
would eventually be wrong.

The scaffolds encode the three rules a first-time author trips over, because
the compiler enforces them and the error messages are terse:

  1. `@unit version` is the LANGUAGE revision (4.3.0), not the app's version.
  2. Source operands are separated by U+203A (a single right-angle quote),
     not a comma.
  3. Every row names a capability register and a capability, and the
     capability must be the one the opcode class requires -- ARITH for
     arithmetic, CONTROL for flow, MEMORY for loads and stores, SERVICE or
     STATE for service calls -- and it must also appear in the unit's
     `br_request_caps`.
  4. ARG keys are lexically ordered: `offset=0;svc=STORAGE_WRITE`, never the
     other way round. A service call passes the guest-memory offset and the
     transfer length in its two source registers, and names the storage
     object in `offset=`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Dict, List, Optional, Sequence

SEP = "›"                       # the source-operand separator, U+203A
LANGUAGE_VERSION = "4.3.0"
LANGUAGE = "columned-lctl/4.3"
ISA = "BR/1.1"


class ToolchainError(RuntimeError):
    """The runtime's own toolchain refused, and this carries what it said."""

    def __init__(self, message: str, stdout: str = "", stderr: str = "",
                 returncode: int = 1):
        super().__init__(message)
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


def toolchain(runtime: str) -> str:
    p = os.path.join(runtime, "tools", "lctl430.py")
    if not os.path.isfile(p):
        raise ToolchainError(f"the runtime at {runtime} has no "
                             f"tools/lctl430.py; it is not a BOTTLE ROCKET "
                             f"package")
    return p


def _tool(runtime: str, args: Sequence[str], timeout: float = 300.0
          ) -> Dict[str, object]:
    cmd = [sys.executable, "-B", toolchain(runtime), *args]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                       cwd=runtime)
    out = (r.stdout or "").strip()
    parsed = None
    if out.startswith("{"):
        try:
            parsed = json.loads(out)
        except ValueError:
            parsed = None
    if r.returncode != 0:
        raise ToolchainError((r.stderr or out or "toolchain failed").strip(),
                             out, r.stderr or "", r.returncode)
    return {"ok": True, "stdout": out, "json": parsed,
            "command": " ".join(os.path.basename(c) if i == 1 else c
                                for i, c in enumerate(cmd))}


def check(runtime: str, source: str, executable: bool = True) -> Dict[str, object]:
    args = ["check", os.path.abspath(source)]
    if executable:
        args.append("--executable")
    return _tool(runtime, args)


def compile_image(runtime: str, source: str, image: str,
                  factory: bool = True, manifest: Optional[str] = None,
                  brir: Optional[str] = None) -> Dict[str, object]:
    args = ["compile", os.path.abspath(source), os.path.abspath(image)]
    if factory:
        args.append("--factory")
    if manifest:
        args += ["--manifest", os.path.abspath(manifest)]
    if brir:
        args += ["--brir-out", os.path.abspath(brir)]
    return _tool(runtime, args)


def provenance(runtime: str, source: str, image: str, manifest: str
               ) -> Dict[str, object]:
    return _tool(runtime, ["provenance", os.path.abspath(source),
                           os.path.abspath(image), os.path.abspath(manifest)])


def disasm(runtime: str, image: str) -> Dict[str, object]:
    return _tool(runtime, ["disasm", os.path.abspath(image)])


def brim_verify(runtime: str, image: str, manifest: Optional[str] = None
                ) -> Dict[str, object]:
    tool = os.path.join(runtime, "tools", "brim_verify.py")
    if not os.path.isfile(tool):
        raise ToolchainError("the runtime has no tools/brim_verify.py")
    cmd = [sys.executable, "-B", tool, os.path.abspath(image)]
    if manifest:
        cmd += ["--manifest", os.path.abspath(manifest)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                       cwd=runtime)
    out = (r.stdout or "").strip()
    if r.returncode != 0:
        raise ToolchainError((r.stderr or out or "image verification failed")
                             .strip(), out, r.stderr or "", r.returncode)
    try:
        parsed = json.loads(out) if out.startswith("{") else None
    except ValueError:
        parsed = None
    return {"ok": True, "stdout": out, "json": parsed}


# ==========================================================================
# Scaffolds
# ==========================================================================

_HEADER = ("LCTLC/1.2\n"
           "@unit id={unit} version=" + LANGUAGE_VERSION +
           " language=" + LANGUAGE + " isa=" + ISA +
           " br_image_version=10 br_request_caps={caps}{extra}\n"
           "ID│LANE│OP│OUT│CTRL│IN│ARG│META\n")

# The console payload is derived from the bytes, not typed as a magic number:
# a store is little-endian, so the immediate and the text a reader expects on
# the console cannot drift apart if only one of them is ever written down.
CONSOLE_WORD = b"PA21"
CONSOLE_IMM = int.from_bytes(CONSOLE_WORD, "little")

TEMPLATES: Dict[str, Dict[str, object]] = {
    "hello": {
        "title": "arithmetic",
        "summary": "multiplies two immediates and halts with the product in R2",
        "caps": "CONTROL|ARITH",
        "expect": {"status_name": "OK", "trap": 0, "registers": {"R2": 42}},
        "rows": [
            "A│exec│MOVI│R0│C0:CONTROL│_│imm=7│_",
            "B│exec│MOVI│R1│C0:CONTROL│_│imm=6│_",
            f"C│exec│MUL│R2│C0:ARITH│R0{SEP}R1│_│note=product-in-R2",
            "D│exec│HALT│_│C0:CONTROL│_│_│_",
        ],
    },
    "loop": {
        "title": "counted loop",
        # a unit whose control-flow graph has a cycle must declare that it
        # terminates on the instruction budget rather than by reaching HALT.
        # The compiler enforces this, and it is the right way round: a loop
        # that claims to halt is claiming something the verifier cannot see.
        "unit_attrs": "termination=budgeted",
        "summary": "accumulates 1..10 in R2 with a compare-and-branch loop",
        "caps": "CONTROL|ARITH",
        "expect": {"status_name": "OK", "trap": 0, "registers": {"R2": 55}},
        "rows": [
            "A│exec│MOVI│R0│C0:CONTROL│_│imm=10│note=loop-counter",
            "B│exec│MOVI│R1│C0:CONTROL│_│imm=1│note=decrement",
            "C│exec│MOVI│R2│C0:CONTROL│_│imm=0│note=accumulator",
            "D│exec│MOVI│R3│C0:CONTROL│_│imm=0│note=zero-sentinel",
            f"E│exec│CMP│_│C0:ARITH│R0{SEP}R3│_│note=sets-zero-flag",
            "F│exec│JZ│_│C0:CONTROL│_│target=@J│_",
            f"G│exec│ADD│R2│C0:ARITH│R2{SEP}R0│_│_",
            f"H│exec│SUB│R0│C0:ARITH│R0{SEP}R1│_│_",
            "I│exec│JMP│_│C0:CONTROL│_│target=@E│_",
            "J│exec│HALT│_│C0:CONTROL│_│_│_",
        ],
    },
    "fabric": {
        "title": "device fabric",
        "summary": "writes to the console, through the persistent block "
                   "device and back, and reads the monotonic counter -- the "
                   "services the container's RAM backend provides",
        "caps": "CONTROL|MEMORY|SERVICE|STATE",
        "expect": {"status_name": "OK", "trap": 0,
                   "fabric": {"console_out_text": CONSOLE_WORD.decode(),
                              "console_out_bytes": len(CONSOLE_WORD)}},
        "rows": [
            f"A│exec│MOVI│R3│C0:CONTROL│_│imm={CONSOLE_IMM}│note=console-word-le",
            "B│exec│STORE│_│C0:MEMORY│R3│imm=0│note=into-guest-memory",
            "C│exec│MOVI│R0│C0:CONTROL│_│imm=0│note=transfer-offset",
            f"D│exec│MOVI│R1│C0:CONTROL│_│imm={len(CONSOLE_WORD)}│note=transfer-length",
            f"E│exec│SVC│R2│C0:SERVICE│R0{SEP}R1│svc=CONSOLE_WRITE│note=device-1",
            f"F│exec│SVC│R2│C0:STATE│R0{SEP}R1│offset=0;svc=STORAGE_WRITE│note=device-2",
            f"G│exec│SVC│R2│C0:STATE│R0{SEP}R1│offset=0;svc=STORAGE_READ│note=read-back",
            "H│exec│SVC│R2│C0:STATE│_│svc=MONOTONIC│note=device-3",
            "I│exec│HALT│_│C0:CONTROL│_│_│_",
        ],
    },
    "field": {
        "title": "distributed fabric cell",
        "summary": "reads storage object 0, advances a counter cell and mirrors "
                   "it into a second cell, then writes the shard back -- state "
                   "that changes every tick, so its fabric image is in flux",
        "caps": "CONTROL|MEMORY|ARITH|STATE",
        "state": "keep",
        "expect": {"status_name": "OK", "trap": 0},
        "rows": [
            "A│exec│MOVI│R0│C0:CONTROL│_│imm=0│note=shard-window-offset",
            "B│exec│MOVI│R1│C0:CONTROL│_│imm=64│note=window-length",
            f"C│exec│SVC│R2│C0:STATE│R0{SEP}R1│offset=0;svc=STORAGE_READ│note=read-shard-0",
            "D│exec│LOAD│R3│C0:MEMORY│_│imm=0│note=the-counter-cell",
            "E│exec│MOVI│R4│C0:CONTROL│_│imm=1│_",
            f"F│exec│ADD│R3│C0:ARITH│R3{SEP}R4│_│note=advance-it",
            "G│exec│STORE│_│C0:MEMORY│R3│imm=0│note=counter-back-to-cell-0",
            "H│exec│MOVI│R5│C0:CONTROL│_│imm=7│_",
            f"I│exec│MUL│R6│C0:ARITH│R3{SEP}R5│_│note=a-second-derived-cell",
            "J│exec│STORE│_│C0:MEMORY│R6│imm=16│note=mirror-into-cell-16",
            f"K│exec│SVC│R7│C0:STATE│R0{SEP}R1│offset=0;svc=STORAGE_WRITE│note=shard-0-back",
            "L│exec│HALT│_│C0:CONTROL│_│_│_",
        ],
    },
    "memory": {
        "title": "memory round trip",
        "summary": "stores a value to guest memory, reads it back, and halts "
                   "with it in R2",
        "caps": "CONTROL|ARITH|MEMORY",
        "expect": {"status_name": "OK", "trap": 0, "registers": {"R2": 2026}},
        "rows": [
            "A│exec│MOVI│R0│C0:CONTROL│_│imm=2026│_",
            "B│exec│STORE│_│C0:MEMORY│R0│imm=64│note=guest-memory-4096-bytes",
            "C│exec│LOAD│R2│C0:MEMORY│_│imm=64│_",
            "D│exec│HALT│_│C0:CONTROL│_│_│_",
        ],
    },
}


def render(template: str, unit: str) -> str:
    """The source text for a scaffold, ready to compile."""
    if template not in TEMPLATES:
        raise ToolchainError(f"{template!r} is not a template; choose from "
                             f"{sorted(TEMPLATES)}")
    t = TEMPLATES[template]
    extra = t.get("unit_attrs", "")
    body = _HEADER.format(unit=unit, caps=t["caps"],
                          extra=(" " + extra) if extra else "")
    body += "\n".join(t["rows"]) + "\n@end\n"
    return body


def template_list() -> List[Dict[str, object]]:
    return [{"name": k, "title": v["title"], "summary": v["summary"],
             "capabilities": v["caps"], "expect": v["expect"]}
            for k, v in sorted(TEMPLATES.items())]
