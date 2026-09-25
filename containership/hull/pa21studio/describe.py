"""The contract, in machine-readable form, for whatever is writing the code.

A person can read the README and learn that source operands are separated by
U+203A. An agent should not have to discover that by compiling something and
reading a refusal -- and it certainly should not have to be told by a human who
already knows. So the studio describes itself.

Everything here that CAN be read out of the installed runtime IS read out of
it, by importing the runtime's own `tools/lctl430.py` and asking it: the
opcode list, the service table, the capability of each opcode class, the
service-to-capability map. Restating those in this file would create a second
source of truth that drifts the first time the runtime changes, and the whole
point of the description is that an agent can trust it.

What cannot be read out of the runtime -- the rules a first attempt trips over,
and what to do about each refusal -- is written here, and each rule carries a
counter-example, because a rule without one is guesswork with extra steps.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
from typing import Dict, List, Optional, Tuple

from . import repair

SCHEMA = "PA21.STUDIO/DESCRIBE/1"

# ---------------------------------------------------------------------------
# The service ABI.
#
# A program can compile, load, run to HALT with trap 0, and do nothing at all,
# because the operand convention is per-service and getting it wrong is not a
# syntax error. That is the worst thing that can happen to something writing
# code from a description, so the description carries the convention.
#
# The wording of what each device IS comes from the runtime's own
# spec/DEVICE_ABI.json. What each REGISTER means is stated here, because the
# only other place it exists is the switch in brvm.c.
# ---------------------------------------------------------------------------

_BUF = ("guest-memory offset", "length in bytes")

SERVICE_ABI: Dict[str, Dict[str, object]] = {
    "CONSOLE_WRITE": {
        "in": _BUF, "out": None,
        "effect": "those bytes appear on the console",
        "note": "SVC always takes a destination register, so name one -- but this service does not write it, and it keeps whatever it held"},
    "CONSOLE_READ": {
        "in": _BUF, "out": None,
        "effect": "console input is copied into guest memory at the offset",
        "note": "SVC always takes a destination register, but this service does not write it, so the count is not returned; supply input with --console-in HEX or nothing arrives"},
    "ENTROPY": {
        "in": _BUF, "out": None,
        "effect": "random bytes are written into guest memory at the offset",
        "note": "SVC always takes a destination register, but this service does not write it. On the deterministic adapter the bytes are a seeded replay substitute, so two runs agree"},
    "STORAGE_WRITE": {
        "in": _BUF, "out": None,
        "arg": "offset=<0..3> selects the storage object, and is NOT a "
               "memory offset",
        "effect": "the bytes are framed into that persistent block object",
        "note": "SVC always takes a destination register, but a write does "
                "not write it -- unlike STORAGE_READ, which returns the byte "
                "count. Read the run's fabric.storage to see what landed"},
    "STORAGE_READ": {
        "in": _BUF, "out": "bytes read",
        "arg": "offset=<0..3> selects the storage object",
        "effect": "the object's bytes are copied into guest memory"},
    "MAILBOX_PUT": {
        "in": _BUF, "out": "bytes put",
        "effect": "the message becomes guest-owned pending host receive",
        "note": "the mailbox is one slot, 64 bytes; putting twice without a "
                "host receive is a resource trap"},
    "MAILBOX_GET": {
        "in": _BUF, "out": "bytes received, and 0 when there is nothing",
        "effect": "a host-delivered message is copied into guest memory",
        "note": "GET reads only host-owned messages. A guest cannot PUT and "
                "then GET its own message: PUT leaves it guest-owned pending "
                "host receive, and GET returns 0 -- while still clearing the "
                "slot"},
    "MONOTONIC": {
        "in": None, "out": "the monotonic counter",
        "effect": "the counter is read and returned"},
    "TIMER": {
        "in": None, "out": "the clock reading",
        "effect": "the clock is read and returned"},
    "SHA256": {
        "in": _BUF, "out": "0 on success",
        "arg": "offset=<n> is where the 32-byte digest is WRITTEN in guest "
               "memory",
        "effect": "the named window is hashed and the digest stored"},
    "DIAG": {
        "in": ("a diagnostic code", None), "out": None,
        "effect": "a record is appended to the diagnostics ring"},
    "STATUS": {
        "in": None, "out": "trap in the high half, lifecycle in the low half",
        "effect": "the VM reports on itself"},
    "YIELD": {
        "in": None, "out": None,
        "effect": "the VM suspends: machine_status becomes SUSPENDED while "
                  "status_name stays OK -- nothing went wrong, the machine "
                  "simply did not halt. A unit that ends this way declares "
                  "termination=yield and carries no HALT, because the "
                  "verifier can see that a row after YIELD is unreachable"},
    "DEVICE_ENUM": {
        "in": ("the device index to describe", None),
        "out": "seven words describing that device",
        "effect": "the fabric is enumerated"},
    "DEVICE_CALL": {
        "in": ("the extension device index", "guest-memory offset"),
        "out": "bytes returned",
        "effect": "an extension device is called",
        "note": "requires --devices; without it there are no extension "
                "devices and the index is out of range"},
    "TRUST": {"in": None, "out": "the keystore state",
              "effect": "the trust state is read"},
    "VERIFY": {"in": _BUF, "out": "1 when the signature verifies",
               "arg": "offset=<n> is the signed payload offset",
               "effect": "a signature is checked"},
    "SAVE": {"in": None, "out": None,
             "effect": "VM state is persisted through the HAL"},
    "CONFIG": {"in": ("a configuration word", None), "out": None,
               "effect": "a VM configuration word is set"},
    "GRANT": {"in": ("target capability register", "capability bits"),
              "out": None,
              "effect": "capabilities are granted to another C register",
              "note": "you cannot grant what the calling register does not "
                      "hold"},
    "REVOKE": {"in": ("target capability register", None), "out": None,
               "effect": "that capability register is emptied"},
    "NOP": {"in": None, "out": None, "effect": "nothing, deliberately"},
}

# What counts as evidence in the fabric that a service actually did something,
# and what to say when the evidence is absent. Keyed by service name; each
# entry reads the run's own report rather than trusting the source.
_QUIET: Dict[str, Dict[str, str]] = {
    "CONSOLE_WRITE": {
        "why": "nothing reached the console",
        "do": "the length register was zero, or the offset window held no "
              "bytes; STORE the bytes into guest memory first, and check the "
              "register you passed as the length"},
    "CONSOLE_READ": {
        "why": "no console input was consumed",
        "do": "run with --console-in HEX; with no input supplied there is "
              "nothing to read"},
    "STORAGE_WRITE": {
        "why": "no storage object holds any bytes",
        "do": "check the length register, and that ARG offset= names an "
              "object in 0..3"},
    "MAILBOX_PUT": {
        "why": "the mailbox is empty at the end of the run",
        "do": "either the length was zero, or a later MAILBOX_GET consumed "
              "the slot -- GET clears it even though it returns 0 for a "
              "guest-owned message"},
    "MAILBOX_GET": {
        "why": "the receive returned no bytes",
        "do": "GET reads host-delivered messages only, so give it one: run "
              "with --mailbox-in HEX, or declare mailbox_in_hex in the "
              "container. A message this guest PUT is pending host receive "
              "and will not come back"},
    "ENTROPY": {
        "why": "no bytes are visible in the head of guest memory",
        "do": "the length register was zero, or the bytes went past the "
              "first 64 bytes, which is all a run reports; draw them at a "
              "low offset to see them"},
    "STORAGE_READ": {
        "why": "the read returned no bytes",
        "do": "the RAM-backed fabric starts empty unless the run carries the "
              "previous one's state, so either write the object first in "
              "this run, or run with --state keep"},
    "TIMER": {
        "why": "the clock reads zero",
        "do": "on the deterministic adapter the clock is a counter that "
              "starts where the replay says; this is not necessarily wrong"},
    "MONOTONIC": {
        "why": "the monotonic counter is still zero",
        "do": "this is what a fresh RAM-backed fabric reads; run with "
              "--state keep to carry the counter between runs"},
    "DEVICE_CALL": {
        "why": "no extension device was called",
        "do": "pass --devices, or the fabric has no extension devices to "
              "call"},
}

REGISTER_ROLES = {
    "arguments": "R0-R5", "returns": "R0-R1", "scratch": "R0-R7",
    "callee_preserved": "R8-R13", "frame_pointer": "R14", "reserved": "R15",
}

# Every refusal the compiler produces that a writer can act on, and the action.
# Matched as a substring of the compiler's own message, so the message stays
# the runtime's to word.
REFUSALS: List[Dict[str, str]] = [
    {"matches": "@unit version must be",
     "means": "`@unit version=` is the LANGUAGE revision, not your program's",
     "do": "set version=4.3.0 and put your own version in CONTAINER.json"},
    {"matches": "bad register",
     "means": "two source operands were separated by something other than "
              "U+203A",
     "do": "write R0›R1 (a single right-pointing angle quotation mark), "
           "not R0,R1 or R0 R1"},
    {"matches": "declared capability",
     "means": "the row's CTRL capability is not the one that opcode class "
              "requires",
     "do": "arithmetic needs ARITH, flow needs CONTROL, loads and stores need "
           "MEMORY, and a service call needs the capability of that service"},
    {"matches": "exceeds @unit declaration",
     "means": "a row uses a capability the unit never requested",
     "do": "add it to br_request_caps= on the @unit line, pipe-separated"},
    {"matches": "ARG keys must be lexically ordered",
     "means": "ARG keys are sorted",
     "do": "write offset=0;svc=STORAGE_WRITE, not svc=STORAGE_WRITE;offset=0"},
    {"matches": "META must be provenance key=value",
     "means": "the META column is structured, not prose",
     "do": "write note=something, or _ for nothing"},
    {"matches": "loop requires termination=budgeted",
     "means": "the control-flow graph has a cycle, so reaching HALT is not "
              "provable",
     "do": "add termination=budgeted to the @unit line"},
    {"matches": "source operand count violation",
     "means": "that opcode takes a different number of source registers",
     "do": "check `arity` in this description for the opcode"},
    {"matches": "destination operand contract violation",
     "means": "that opcode either requires an OUT register or forbids one",
     "do": "use _ in OUT for opcodes that produce nothing"},
    {"matches": "requires target",
     "means": "a branch needs a label",
     "do": "write target=@ID, where ID is the value in another row's ID column"},
    {"matches": "requires imm",
     "means": "that opcode needs an immediate",
     "do": "write imm=<integer>"},
    {"matches": "non-canonical constant expression",
     "means": "an immediate was not a plain canonical integer",
     "do": "write a decimal integer with no leading zeros, or 0x-prefixed hex"},
    {"matches": "row outside table",
     "means": "a row appeared before the column header line, or after @end",
     "do": "emit the three preamble lines in this description -- the magic "
           "line, the @unit line, then the literal column header row -- "
           "before any instruction row"},
    {"matches": "missing @unit/header/@end",
     "means": "one of the three structural lines is absent",
     "do": "see `preamble` and `terminator` in this description"},
    {"matches": "unsupported/missing LCTLC",
     "means": "the first line is not the magic line",
     "do": "make LCTLC/1.2 the very first line of the file"},
    {"matches": "duplicate @unit",
     "means": "a source file holds exactly one unit",
     "do": "split the second unit into its own container"},
    {"matches": "capability",
     "means": "a capability rule was broken",
     "do": "check the capability table in this description"},
]

# A program that is known to compile and to have a visible effect, so that a
# writer starting from nothing has one accepted artefact to vary rather than a
# grammar to reconstruct. Written with the separators spelled out by codepoint
# so it survives being quoted into a prompt.
EXAMPLE = {
    "what_it_does": "stores four bytes in guest memory, writes them to the "
                    "console, and reads the monotonic counter",
    "run": "printf '%s' \"$SRC\" | studio try --from - --json",
    "expect": {"status_name": "OK", "trap": 0,
               "fabric": {"console_out_text": "PA21", "console_out_bytes": 4}},
    "source": [
        "LCTLC/1.2",
        "@unit id=example version=4.3.0 language=columned-lctl/4.3 "
        "isa=BR/1.1 br_image_version=10 br_request_caps=CONTROL|MEMORY|"
        "SERVICE|STATE",
        "ID│LANE│OP│OUT│CTRL│IN│ARG│META",
        "A│exec│MOVI│R0│C0:CONTROL│_│imm=825377104│note=PA21-little-endian",
        "B│exec│STORE│_│C0:MEMORY│R0│imm=0│note=address-is-imm-not-a-register",
        "C│exec│MOVI│R1│C0:CONTROL│_│imm=0│note=window-offset",
        "D│exec│MOVI│R2│C0:CONTROL│_│imm=4│note=window-length",
        "E│exec│SVC│R4│C0:SERVICE│R1›R2│svc=CONSOLE_WRITE│note=SVC-always-names-a-destination",
        "F│exec│SVC│R3│C0:STATE│_│svc=MONOTONIC│note=counter-into-R3",
        "G│exec│HALT│_│C0:CONTROL│_│_│_",
        "@end",
    ],
}

RULES: List[Dict[str, object]] = [
    {"rule": "the unit header declares the language revision, not yours",
     "right": "@unit id=pricing version=4.3.0 language=columned-lctl/4.3 "
              "isa=BR/1.1 br_image_version=10 br_request_caps=CONTROL|ARITH",
     "wrong": "@unit id=pricing version=1.0.0 …",
     "why": "4.3.0 is the COLUMNED LCTL revision the compiler implements"},
    {"rule": "columns are separated by U+2502 and source operands by U+203A",
     "right": "C│exec│MUL│R2│C0:ARITH│R0›R1│_│_",
     "wrong": "C|exec|MUL|R2|C0:ARITH|R0,R1|_|_",
     "why": "the column and operand separators are distinct characters, and "
            "neither is ASCII"},
    {"rule": "every row names a capability register and the capability its "
             "opcode class requires",
     "right": "arithmetic on C0:ARITH, flow on C0:CONTROL, loads and stores "
              "on C0:MEMORY, a console write on C0:SERVICE, a block write on "
              "C0:STATE",
     "wrong": "C1:ARITH — a capability register other than C0, which the raw "
              "loader does not grant",
     "why": "the VM checks caps[cap_index] on every instruction; only C0 "
            "carries the image's requested capabilities under a raw load"},
    {"rule": "ARG keys are lexically ordered, and META is key=value",
     "right": "offset=0;svc=STORAGE_WRITE   and   note=read-back",
     "wrong": "svc=STORAGE_WRITE;offset=0   and   free prose in META",
     "why": "the source is canonicalised before it is hashed, so its ordering "
            "is part of its identity"},
    {"rule": "a unit whose control flow contains a cycle declares how it ends",
     "right": "@unit … termination=budgeted",
     "wrong": "a loop with no termination= attribute",
     "why": "the verifier cannot prove a cyclic unit reaches HALT, so the unit "
            "must say it terminates on the instruction budget"},
    {"rule": "a service call passes offset and length in its two source "
             "registers",
     "right": "SVC│R2│C0:STATE│R0›R1│offset=0;"
              "svc=STORAGE_WRITE — R0 is the guest-memory offset, R1 the "
              "length, offset= names the storage object",
     "wrong": "passing the object id in a source register",
     "why": "the ABI reads the transfer window from ra and rb and the object "
            "from the instruction's flags"},
]


def _load_toolchain(runtime: Optional[str]):
    """Import the runtime's own compiler module, so the tables are its own."""
    if not runtime:
        return None
    p = os.path.join(runtime, "tools", "lctl430.py")
    if not os.path.isfile(p):
        return None
    spec = importlib.util.spec_from_file_location("_lctl430_for_describe", p)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)                          # type: ignore
    except Exception:                                         # noqa: BLE001
        return None
    return mod


def _brvm_constants(runtime: Optional[str]) -> Dict[str, int]:
    """Read the VM's own enum, so register counts are not restated here."""
    out: Dict[str, int] = {}
    if not runtime:
        return out
    p = os.path.join(runtime, "src", "brvm.h")
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return out
    for name, val in re.findall(r"\b(BR_[A-Z0-9_]+)\s*=\s*(\d+)u?\b", text):
        out.setdefault(name, int(val))
    return out


def _device_abi(runtime: Optional[str]) -> Dict[str, object]:
    """The runtime's own device ABI document, when it ships one."""
    if not runtime:
        return {}
    p = os.path.join(runtime, "spec", "DEVICE_ABI.json")
    try:
        with open(p, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _service_abi(services: Dict[str, object], abi: Dict[str, object]
                 ) -> Dict[str, object]:
    """Join the runtime's service table to the operand convention."""
    by_surface: Dict[str, Dict[str, object]] = {}
    for dev in abi.get("devices", []) or []:
        for s in dev.get("surface", []) or []:
            if isinstance(s, str) and s.startswith("BR_SVC_"):
                by_surface[s[len("BR_SVC_"):]] = dev
    out: Dict[str, object] = {}
    for name in services:
        row = dict(SERVICE_ABI.get(name, {}))
        ins = row.pop("in", None)
        row["ra"] = ins[0] if ins else None
        row["rb"] = ins[1] if ins else None
        row["out_register"] = row.pop("out", None)
        dev = by_surface.get(name)
        if dev:
            row["device"] = dev.get("name")
            row["device_determinism"] = dev.get("determinism")
            for k in ("depth", "packet_bytes", "objects",
                      "payload_bytes_per_object", "max_transfer_bytes"):
                if k in dev:
                    row[k] = dev[k]
        if not SERVICE_ABI.get(name):
            row["described"] = False
            row["note"] = ("the runtime offers this service but the studio "
                           "has no operand convention written down for it; "
                           "read tools/lctl430.py and src/brvm.c")
        out[name] = row
    return out


# Services whose OUT register carries a byte count, and is therefore the
# strongest evidence available about what that individual call transferred.
_COUNTS_IN_OUT = {"MAILBOX_GET", "MAILBOX_PUT", "STORAGE_READ",
                  "DEVICE_CALL"}


def effects(services: List[str], fabric: Dict[str, object],
            registers: Optional[Dict[str, int]] = None,
            memory_head_hex: Optional[str] = None,
            console_in: bool = False,
            service_calls: Optional[List[Dict[str, str]]] = None
            ) -> Dict[str, object]:
    """What the run visibly did, and which calls left no trace.

    A refusal is easy to act on. A program that compiles, runs to HALT with
    trap 0 and changes nothing is not, because nothing in the result says so
    -- the status is the same status a working program returns. So the studio
    says it: for every service the source calls, either the evidence that it
    happened, or the reason it may not have.
    """
    fabric = fabric or {}
    registers = registers or {}
    # A block object is a fixed 512-byte frame whether or not it carries a
    # payload, so the frame size cannot answer "did anything land". The
    # payload length is in the frame header (BRO1, then the length at byte
    # 12, little endian), and that is what is read here.
    storage = 0
    for o in (fabric.get("storage") or []):
        head = str(o.get("head_hex") or "")
        if len(head) >= 32 and head[:8].lower() == "42524f31":
            storage += int.from_bytes(bytes.fromhex(head[24:28]), "little")
        elif o.get("framed_bytes"):
            storage += int(o["framed_bytes"])
    mem = (memory_head_hex or "").strip("0")
    observed: Dict[str, object] = {}
    quiet: List[Dict[str, str]] = []
    seen: Dict[str, int] = {}
    # what each individual call answered, where the row named a register and
    # the service returns a count in it -- the only per-call evidence there is
    returned: Dict[str, int] = {}
    for call in service_calls or []:
        name, reg = call.get("service", ""), call.get("out", "_")
        if name in _COUNTS_IN_OUT and reg in registers:
            v = int(registers.get(reg) or 0)
            returned[name] = max(returned.get(name, 0), v)
    for name in services or []:
        seen[name] = seen.get(name, 0) + 1
        ev: object = None
        if name in returned:
            # The call's own answer, in the register the row named. For these
            # services the VM always writes it, so a zero here is evidence
            # that nothing transferred -- not an absence of evidence, and it
            # beats anything inferred from the fabric afterwards. Services
            # that never write their destination register are not in this
            # set, precisely so that their zero means nothing at all.
            ev = {"bytes_returned": returned[name]} if returned[name] else 0
        elif name == "CONSOLE_WRITE":
            ev = fabric.get("console_out_bytes") or 0
            ev = {"console_out_bytes": ev,
                  "console_out_text": fabric.get("console_out_text")} if ev \
                else 0
        elif name == "CONSOLE_READ":
            ev = fabric.get("console_in_consumed") or 0
        elif name == "STORAGE_WRITE":
            ev = {"payload_bytes_total": storage} if storage else 0
        elif name == "STORAGE_READ":
            ev = {"guest_memory_head_hex": memory_head_hex} if mem else 0
        elif name == "ENTROPY":
            ev = {"guest_memory_head_hex": memory_head_hex} if mem else 0
        elif name == "MAILBOX_PUT":
            ev = fabric.get("mailbox_bytes") or 0
        elif name == "MAILBOX_GET":
            ev = {"guest_memory_head_hex": memory_head_hex} if mem else 0
        elif name == "MONOTONIC":
            ev = fabric.get("monotonic") or 0
        elif name == "TIMER":
            ev = fabric.get("clock") or 0
        elif name in ("DEVICE_CALL", "DEVICE_ENUM"):
            ev = fabric.get("device_calls") or 0
        elif name == "DIAG":
            ev = "recorded in the diagnostics ring"
        else:
            ev = "no fabric evidence is defined for this service"
        if ev in (0, None, ""):
            q = dict(_QUIET.get(name, {
                "why": "the fabric shows no trace of this call",
                "do": "check the registers named in ARG and IN against "
                      "`service_abi` in `studio describe`"}))
            q["service"] = name
            if name == "CONSOLE_READ" and not console_in:
                q["do"] = ("no console input was supplied to this run; pass "
                           "--console-in HEX")
            quiet.append(q)
        else:
            observed[name] = ev
    return {"observed": observed, "quiet": quiet,
            "calls": seen,
            "silent": bool(quiet) and not observed,
            "note": "a service listed under `quiet` compiled and ran; it "
                    "simply left no evidence, which is usually an operand "
                    "convention, not a syntax error"}


def describe(runtime: Optional[str] = None,
             studio_version: str = "", container_format: str = "",
             templates: Optional[List[Dict[str, object]]] = None,
             fabric_devices: Optional[List[str]] = None) -> Dict[str, object]:
    """Everything a writer needs to produce a program this studio will accept."""
    tc = _load_toolchain(runtime)
    language: Dict[str, object] = {
        "name": "COLUMNED LCTL",
        "source_version_line": "LCTLC/1.2",
        "unit_version": "4.3.0",
        "language": "columned-lctl/4.3",
        "isa": "BR/1.1",
        "image_version": 10,
        "columns": ["ID", "LANE", "OP", "OUT", "CTRL", "IN", "ARG", "META"],
        "column_separator": "│",
        "column_separator_codepoint": "U+2502",
        "operand_separator": "›",
        "operand_separator_codepoint": "U+203A",
        "empty_cell": "_",
        "unit_line": "@unit id=<name> version=4.3.0 language=columned-lctl/4.3 "
                     "isa=BR/1.1 br_image_version=10 br_request_caps=<A|B>",
        "preamble": [
            getattr(tc, "MAGIC", "LCTLC/1.2"),
            "@unit id=<name> version=4.3.0 language=columned-lctl/4.3 "
            "isa=BR/1.1 br_image_version=10 br_request_caps=<A|B>",
            getattr(tc, "HDR", "ID│LANE│OP│OUT│CTRL│IN│ARG│META"),
        ],
        "preamble_note": "all three lines, in this order, before any "
                         "instruction row. The third is the literal column "
                         "header, not a comment: a row that precedes it is "
                         "refused as `row outside table`.",
        "terminator": "@end",
        "rules": RULES,
        "tables_source": "read from the installed runtime's own tools/lctl430.py"
                         if tc else "the runtime is not installed, so only the "
                                    "static rules are described",
    }
    if tc:
        language["opcodes"] = list(getattr(tc, "OPS", []))
        language["capabilities"] = dict(getattr(tc, "CAP", {}))
        svc = dict(getattr(tc, "SVC", {}))
        svc_cap = dict(getattr(tc, "SVC_CAP", {}))
        language["services"] = {
            name: {"id": sid,
                   "capability": svc_cap.get(sid),
                   "device": _device_for(name)}
            for name, sid in sorted(svc.items(), key=lambda kv: kv[1])}
        opcap = getattr(tc, "opcap", None)
        if callable(opcap):
            language["capability_of_opcode"] = {
                op: (opcap(op, 0) if op == "SVC" else opcap(op))
                for op in getattr(tc, "OPS", [])}
        language["limits"] = {
            "word_bits": getattr(tc, "WORD_BITS", None),
            "guest_memory_bytes": getattr(tc, "MEM", None),
            "stack_words": getattr(tc, "STACK", None),
            "max_instructions": getattr(tc, "MAX_CODE", None),
        }
        language["arity"] = _arity_table()
        language["service_abi"] = _service_abi(svc, _device_abi(runtime))
        k = _brvm_constants(runtime)
        language["registers"] = {
            "count": k.get("BR_REGS", 16),
            "names": [f"R{i}" for i in range(k.get("BR_REGS", 16))],
            "capability_registers": k.get("BR_CAPS", 16),
            "usable_capability_register": "C0 only, under a raw load",
            "call_abi": REGISTER_ROLES,
            "reported_after_a_run": "all of them, low limb first",
        }
    out: Dict[str, object] = {
        "schema": SCHEMA,
        "studio_version": studio_version,
        "container_format": container_format,
        "language": language,
        "fabric": {
            "backend": "RAM",
            "adapters": {
                "memory": "entropy and clock seeded per run",
                "deterministic": "replay substitutes; two runs of one image "
                                 "produce identical fabric bytes. Use this "
                                 "when comparing candidate programs.",
            },
            "devices": fabric_devices or [
                "console", "persistent block", "monotonic state", "entropy",
                "clock", "mailbox", "diagnostics"],
            "note": "every device is backed in the host process's memory; no "
                    "file is opened and no socket exists",
            "image_fabric": {
                "format": "PA21FABTIF/1",
                "what": "a container's device fabric, written as a multi-page "
                        "TIFF: the four guest storage objects are laid out as "
                        "tiles of one raster (shards = tiles, a cell's fabric "
                        "position is its pixel position), and the counters and "
                        "non-guest slots ride as private tags",
                "reversible": "the map fabric<->image is a bijection over the "
                              "guest-visible payloads, so the studio writes "
                              "the image from a run and reads it back as the "
                              "state of the next run",
                "flux": "studio fabric live reads the image, runs the "
                        "container against it, writes the mutated image back "
                        "as a new page, and reads whatever the image now says "
                        "on the next tick -- including an edit made to it from "
                        "outside, which is how a distributed fabric is driven",
                "history": "every tick is appended as an immutable page, so "
                           "the file is a frame-by-frame record of the fabric",
                "commands": ["studio fabric init NAME",
                             "studio fabric tick NAME",
                             "studio fabric live NAME [--ticks N] [--interval S]",
                             "studio fabric view NAME", "studio fabric frames NAME"],
            },
            "host_side": {
                "console_in": "--console-in HEX puts bytes where "
                              "CONSOLE_READ will find them",
                "mailbox_in": "--mailbox-in HEX leaves a host-owned message "
                              "for MAILBOX_GET, which is the only way that "
                              "service can return anything; whatever the "
                              "guest PUTs is received by the host after the "
                              "run and reported as mailbox_received_hex",
                "state": "--state keep carries the storage objects and the "
                         "monotonic and clock counters into the next run, so "
                         "STORAGE_READ can read what an earlier run wrote. "
                         "The default is fresh, because a run that silently "
                         "depends on an earlier one is not reproducible",
            },
        },
        "container": {
            "format": container_format,
            "states": {
                "SOURCE_ONLY": "written, never built",
                "SEALED": "the image on disk came from the source on disk",
                "DRAFT": "the source has been edited since the last build",
                "BROKEN": "something outside src/ no longer matches the seal",
            },
            "layout": ["CONTAINER.json", "RELEASE_CONTENTS.sha256", "README.md",
                       "src/main.lctlc", "image/<name>.brimg",
                       "image/<name>.provenance.json"],
        },
        "templates": templates or [],
        "example": EXAMPLE,
        "refusals": [dict(r, fixable=repair.fixable(r["matches"]) or False)
                     for r in REFUSALS],
        "evidence": {
            "command": "studio abi --json",
            "rule": "every statement in `service_abi` is demonstrated by a "
                    "program that exercises that service on this runtime; "
                    "run it and read the verdicts rather than trusting this "
                    "table",
        },
        "repair": repair.catalogue(),
        "writing_loop": [
            "studio describe --json  — read this",
            "studio try --from -     — send a candidate source on stdin",
            "studio try --from - --fix — the same, with the corrections that "
            "have one legal form applied first and each one reported",
            "read compiled/error/hint from the JSON and correct the source",
            "when it compiles and runs, read `effects`: `observed` is what "
            "the run visibly did, and anything under `quiet` ran without "
            "leaving a trace",
            "repeat until compiled is true and the run matches what you "
            "intended",
            "studio try --from - --keep NAME  — promote it into the registry "
            "as a container",
        ],
        "exit_codes": {"0": "it happened", "1": "it did not, and the JSON says "
                                                "why", "2": "malformed request"},
    }
    return out


def _device_for(service: str) -> Optional[str]:
    from .container import SERVICE_DEVICES
    return SERVICE_DEVICES.get(service)


def _arity_table() -> Dict[str, Dict[str, object]]:
    """Destination and source-operand counts, as the compiler enforces them."""
    a = {
        "NOP": (False, 0), "MOVI": (True, 0), "MOV": (True, 1),
        "JMP": (False, 0), "JZ": (False, 0), "JNZ": (False, 0),
        "HALT": (False, 0), "ADD": (True, 2), "SUB": (True, 2),
        "MUL": (True, 2), "DIVU": (True, 2), "MODU": (True, 2),
        "AND": (True, 2), "OR": (True, 2), "XOR": (True, 2), "NOT": (True, 1),
        "SHL": (True, 1), "SHR": (True, 1), "CMP": (False, 2),
        "LOAD": (True, 0), "STORE": (False, 1), "PUSH": (False, 1),
        "POP": (True, 0), "SVC": (True, None), "NEG": (True, 1),
        "BITTST": (False, 1), "ASHR": (True, 1), "ROL": (True, 1),
        "ROR": (True, 1), "LOADX": (True, 1), "STOREX": (False, 2),
        "BEQ": (False, 2), "CALL": (False, 0), "RET": (False, 0),
        "JMPR": (False, 1), "ENTER": (False, 0), "LEAVE": (False, 0),
        "TRAP": (False, 0), "CAPQ": (True, 1), "CHECKPOINT": (False, 0),
        "YIELD": (False, 0),
    }
    return {k: {"destination": v[0],
                "sources": v[1] if v[1] is not None else "0 to 2"}
            for k, v in a.items()}


def explain(message: str) -> Dict[str, object]:
    """Turn a compiler refusal into the rule it broke and the correction."""
    m = (message or "").strip()
    for r in REFUSALS:
        if r["matches"].lower() in m.lower():
            return {"message": m, "recognised": True, "means": r["means"],
                    "do": r["do"], "matched": r["matches"]}
    return {"message": m, "recognised": False,
            "means": "the studio has no rule mapped to this refusal",
            "do": "read the message; it is the runtime compiler's own wording"}
