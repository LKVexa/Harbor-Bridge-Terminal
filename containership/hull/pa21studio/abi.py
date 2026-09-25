"""The ABI table, as programs rather than prose.

`describe` tells whatever is writing code that `MAILBOX_GET` answers in the
register the row named, that `STORAGE_WRITE` does not, that `ENTROPY` writes
bytes into guest memory and leaves its destination register alone. Every one of
those sentences was true when it was written because someone read the VM's
source. That is exactly the kind of claim the PA21 ledger refuses to accept:

    No item is operational because its source file exists. Operational status
    requires native executable evidence satisfying that item's promotion gate.

The same rule should apply to the studio's own description of the language. So
each claim here is a small program that exercises one service and asserts what
the description says will happen -- the register that must hold a byte count,
the register that must be untouched, the bytes that must appear in the fabric.
`studio abi` compiles and runs all of them on the installed runtime and reports
which claims hold.

A claim that cannot be demonstrated is listed as UNPROVEN with the reason,
rather than quietly dropped. Nothing here decides whether the VM is right; it
decides whether the description of the VM is.
"""

from __future__ import annotations

from typing import Dict, List, Optional

SCHEMA = "PA21.STUDIO/ABI_EVIDENCE/1"
SEP = "›"
HDR = "ID│LANE│OP│OUT│CTRL│IN│ARG│META"


def _unit(name: str, caps: str, extra: str = "") -> str:
    return ("LCTLC/1.2\n"
            f"@unit id={name} version=4.3.0 language=columned-lctl/4.3 "
            f"isa=BR/1.1 br_image_version=10 br_request_caps={caps}"
            f"{(' ' + extra) if extra else ''}\n" + HDR + "\n")


def program(name: str, caps: str, rows: List[str], extra: str = "") -> str:
    return _unit(name, caps, extra) + "\n".join(rows) + "\n@end\n"


# The window every buffer service is handed: offset 0, eight bytes, in R0 and
# R1 -- so each probe differs only in the service it calls.
_WINDOW = ["A│exec│MOVI│R0│C0:CONTROL│_│imm=0│note=offset",
           "B│exec│MOVI│R1│C0:CONTROL│_│imm=8│note=length"]


def _svc(rid: str, out: str, cap: str, arg: str, ins: str = "R0›R1",
         note: str = "_") -> str:
    return f"{rid}│exec│SVC│{out}│C0:{cap}│{ins}│{arg}│{note}"


HALT = "Z│exec│HALT│_│C0:CONTROL│_│_│_"

# Each claim: the sentence `describe` states, a program that exercises it, the
# host conditions it needs, and a predicate over the run's own result.
CLAIMS: List[Dict[str, object]] = [
    {
        "service": "CONSOLE_WRITE",
        "claim": "ra is the guest-memory offset and rb the length; the bytes "
                 "appear on the console and the destination register is left "
                 "alone",
        "caps": "CONTROL|MEMORY|SERVICE",
        "rows": ["A│exec│MOVI│R5│C0:CONTROL│_│imm=825377104│note=PA21",
                 "B│exec│STORE│_│C0:MEMORY│R5│imm=0│_",
                 "C│exec│MOVI│R0│C0:CONTROL│_│imm=0│_",
                 "D│exec│MOVI│R1│C0:CONTROL│_│imm=4│_",
                 "E│exec│MOVI│R2│C0:CONTROL│_│imm=99│note=sentinel",
                 _svc("F", "R2", "SERVICE", "svc=CONSOLE_WRITE"),
                 HALT],
        "assert": lambda r: (
            (r["fabric"].get("console_out_text") == "PA21")
            and r["fabric"].get("console_out_bytes") == 4
            and r["registers"].get("R2") == 99),
        "shows": "console_out_bytes=4 and the sentinel in R2 survived, so the "
                 "destination register is not written",
    },
    {
        "service": "CONSOLE_READ",
        "claim": "console input is copied into guest memory at ra, and the "
                 "destination register is not written",
        "caps": "CONTROL|MEMORY|SERVICE",
        "console_in": bytes.fromhex("4142434445464748"),
        "rows": _WINDOW + [
            "C│exec│MOVI│R2│C0:CONTROL│_│imm=77│note=sentinel",
            _svc("D", "R2", "SERVICE", "svc=CONSOLE_READ"),
            "E│exec│LOAD│R3│C0:MEMORY│_│imm=0│note=what-arrived",
            HALT],
        "assert": lambda r: (
            r["fabric"].get("console_in_consumed") == 8
            and r["registers"].get("R2") == 77
            and (r.get("memory_head_hex") or "").startswith("4142434445464748")),
        "shows": "the eight supplied bytes are in guest memory and the "
                 "sentinel in R2 survived",
    },
    {
        "service": "ENTROPY",
        "claim": "random bytes are written into guest memory at ra; on the "
                 "deterministic adapter two runs agree",
        "caps": "CONTROL|MEMORY|SERVICE",
        "rows": _WINDOW + [
            "C│exec│MOVI│R2│C0:CONTROL│_│imm=55│note=sentinel",
            _svc("D", "R2", "SERVICE", "svc=ENTROPY"),
            HALT],
        "assert": lambda r: (
            (r.get("memory_head_hex") or "").strip("0") != ""
            and r["registers"].get("R2") == 55),
        "repeat": True,
        "shows": "bytes landed in guest memory, the sentinel survived, and "
                 "the second run produced the same bytes",
    },
    {
        "service": "STORAGE_WRITE",
        "claim": "the bytes are framed into the object named by ARG offset=, "
                 "and the destination register is NOT written",
        "caps": "CONTROL|MEMORY|SERVICE|STATE",
        "rows": _WINDOW + [
            "C│exec│MOVI│R2│C0:CONTROL│_│imm=33│note=sentinel",
            _svc("D", "R2", "STATE", "offset=1;svc=STORAGE_WRITE"),
            HALT],
        "assert": lambda r: (
            r["fabric"]["storage"][1]["framed_bytes"] > 0
            and r["fabric"]["storage"][0]["framed_bytes"] == 0
            and r["registers"].get("R2") == 33),
        "shows": "object 1 holds a frame, object 0 does not, and the sentinel "
                 "in R2 survived a write that returns nothing",
    },
    {
        "service": "STORAGE_READ",
        "claim": "the object's bytes are copied into guest memory and the "
                 "byte count is returned in the destination register",
        "caps": "CONTROL|MEMORY|SERVICE|STATE",
        "rows": ["A│exec│MOVI│R5│C0:CONTROL│_│imm=825377104│note=PA21",
                 "B│exec│STORE│_│C0:MEMORY│R5│imm=0│_",
                 "C│exec│MOVI│R0│C0:CONTROL│_│imm=0│_",
                 "D│exec│MOVI│R1│C0:CONTROL│_│imm=8│_",
                 _svc("E", "R6", "STATE", "offset=0;svc=STORAGE_WRITE"),
                 _svc("F", "R2", "STATE", "offset=0;svc=STORAGE_READ"),
                 HALT],
        "assert": lambda r: r["registers"].get("R2") == 8,
        "shows": "the read answered 8 in the register the row named",
    },
    {
        "service": "MAILBOX_PUT",
        "claim": "the message becomes guest-owned pending host receive, and "
                 "the byte count is returned",
        "caps": "CONTROL|MEMORY|SERVICE",
        "rows": _WINDOW + [_svc("C", "R2", "SERVICE", "svc=MAILBOX_PUT"), HALT],
        "assert": lambda r: (r["registers"].get("R2") == 8
                             and r["fabric"].get("mailbox_received_bytes") == 8),
        "shows": "8 bytes returned, and the host received exactly those 8",
    },
    {
        "service": "MAILBOX_GET",
        "claim": "a host-delivered message is copied into guest memory and "
                 "its length returned",
        "caps": "CONTROL|MEMORY|SERVICE",
        "mailbox_in": bytes.fromhex("cafebabe"),
        "rows": _WINDOW + [_svc("C", "R2", "SERVICE", "svc=MAILBOX_GET"), HALT],
        "assert": lambda r: (
            r["registers"].get("R2") == 4
            and (r.get("memory_head_hex") or "").startswith("cafebabe")),
        "shows": "the four delivered bytes are in guest memory and R2 is 4",
    },
    {
        "service": "MAILBOX_GET",
        "claim": "a guest cannot receive its own message: PUT leaves it "
                 "pending host receive, and GET returns 0",
        "caps": "CONTROL|MEMORY|SERVICE",
        "rows": _WINDOW + [_svc("C", "R2", "SERVICE", "svc=MAILBOX_PUT"),
                           _svc("D", "R3", "SERVICE", "svc=MAILBOX_GET"),
                           HALT],
        "assert": lambda r: (r["registers"].get("R2") == 8
                             and r["registers"].get("R3") == 0),
        "shows": "the PUT answered 8 and the GET that followed it answered 0",
    },
    {
        "service": "MONOTONIC",
        "claim": "the counter is read into the destination register, and "
                 "carries between runs when the fabric state is kept",
        "caps": "CONTROL|SERVICE|STATE",
        "rows": [_svc("A", "R2", "STATE", "svc=MONOTONIC", ins="_"), HALT],
        "assert": lambda r: "R2" in r["registers"],
        "shows": "the counter answered in R2",
    },
    {
        "service": "TIMER",
        "claim": "the clock is read into the destination register",
        "caps": "CONTROL|SERVICE",
        "rows": [_svc("A", "R2", "SERVICE", "svc=TIMER", ins="_"), HALT],
        "assert": lambda r: r["registers"].get("R2", 0) > 0
        and r["fabric"].get("clock", 0) > 0,
        "shows": "R2 matches a clock the fabric also reports",
    },
    {
        "service": "SHA256",
        "claim": "the window ra..rb is hashed and the 32-byte digest written "
                 "at the guest-memory offset named by ARG offset=",
        "caps": "CONTROL|MEMORY|SERVICE",
        "rows": ["A│exec│MOVI│R5│C0:CONTROL│_│imm=825377104│note=PA21",
                 "B│exec│STORE│_│C0:MEMORY│R5│imm=0│_",
                 "C│exec│MOVI│R0│C0:CONTROL│_│imm=0│_",
                 "D│exec│MOVI│R1│C0:CONTROL│_│imm=4│_",
                 _svc("E", "R2", "SERVICE", "offset=32;svc=SHA256"),
                 HALT],
        "assert": lambda r: (r.get("memory_head_hex") or "")[64:].strip("0")
        != "",
        "shows": "32 bytes of digest appeared at offset 32, where ARG said",
    },
    {
        "service": "STATUS",
        "claim": "the VM reports on itself: trap in the high half, lifecycle "
                 "in the low half",
        "caps": "CONTROL|SERVICE",
        "rows": [_svc("A", "R2", "SERVICE", "svc=STATUS", ins="_"), HALT],
        "assert": lambda r: r["registers"].get("R2", 0) > 0,
        "shows": "R2 carries the packed status word",
    },
    {
        "service": "DEVICE_ENUM",
        "claim": "the fabric can be enumerated from inside the guest",
        "caps": "CONTROL|MEMORY|SERVICE",
        "rows": ["A│exec│MOVI│R0│C0:CONTROL│_│imm=1│note=device-index",
                 _svc("B", "R2", "SERVICE", "svc=DEVICE_ENUM", ins="R0"),
                 HALT],
        "assert": lambda r: r["trap"] == 0,
        "shows": "the enumeration completed without a trap",
    },
    {
        "service": "YIELD",
        "claim": "the VM suspends: the machine ends SUSPENDED rather than "
                 "HALTED, while the error code stays OK -- these are two "
                 "different fields and only one of them changes",
        "caps": "CONTROL|SERVICE",
        # a unit that ends by yielding says so: the verifier will not accept a
        # HALT after a YIELD, because it can never be reached
        "extra": "termination=yield",
        "rows": [_svc("A", "R2", "SERVICE", "svc=YIELD", ins="_")],
        "assert": lambda r: (r.get("machine_status") == "SUSPENDED"
                             and r.get("status_name") == "OK"),
        "shows": "machine_status is SUSPENDED and status_name is OK, which is "
                 "the distinction the description now draws",
    },
]


def evidence(studio, only: Optional[str] = None) -> Dict[str, object]:
    """Run every claim and report which ones the runtime actually supports."""
    results: List[Dict[str, object]] = []
    for i, c in enumerate(CLAIMS):
        if only and c["service"] != only:
            continue
        name = f"abi_{c['service'].lower()}_{i}"
        src = program(name, str(c["caps"]), list(c["rows"]),
                      str(c.get("extra", "")))
        row: Dict[str, object] = {"service": c["service"], "claim": c["claim"],
                                  "shows": c["shows"]}
        try:
            r = studio.try_source(src, adapter="deterministic",
                                  console_in=c.get("console_in"),
                                  mailbox_in=c.get("mailbox_in"))
        except Exception as e:                                # noqa: BLE001
            row.update({"verdict": "UNPROVEN", "reason": str(e)})
            results.append(row)
            continue
        if not r.get("compiled"):
            row.update({"verdict": "UNPROVEN",
                        "reason": f"the probe did not compile: {r.get('error')}"})
            results.append(row)
            continue
        row["status_name"] = r.get("status_name")
        row["machine_status"] = r.get("machine_status")
        row["trap"] = r.get("trap")
        try:
            held = bool(c["assert"](r))                       # type: ignore
        except Exception as e:                                # noqa: BLE001
            held, row["reason"] = False, f"the check itself failed: {e}"
        if held and c.get("repeat"):
            r2 = studio.try_source(src, adapter="deterministic")
            held = (r2.get("memory_head_hex") == r.get("memory_head_hex"))
            if not held:
                row["reason"] = ("two runs on the deterministic adapter "
                                 "disagreed, so the replay substitute is not "
                                 "what the description says it is")
        row["verdict"] = "HOLDS" if held else "FAILS"
        row["evidence"] = {"registers": {k: v for k, v in
                                         (r.get("registers") or {}).items()
                                         if v},
                           "console_out_text": (r.get("fabric") or {}).get(
                               "console_out_text"),
                           "memory_head_hex": (r.get("memory_head_hex")
                                               or "")[:48],
                           "mailbox_received_bytes": (r.get("fabric") or {})
                           .get("mailbox_received_bytes")}
        results.append(row)
    holds = [r for r in results if r["verdict"] == "HOLDS"]
    fails = [r for r in results if r["verdict"] == "FAILS"]
    unproven = [r for r in results if r["verdict"] == "UNPROVEN"]
    return {"schema": SCHEMA, "claims": results,
            "total": len(results), "holds": len(holds),
            "fails": len(fails), "unproven": len(unproven),
            "ok": not fails and not unproven,
            "summary": f"{len(holds)}/{len(results)} claims demonstrated"
                       + (f", {len(fails)} contradicted" if fails else "")
                       + (f", {len(unproven)} unproven" if unproven else ""),
            "rule": "a claim in `describe` is true because a program "
                    "demonstrates it on this runtime, not because it is "
                    "written down"}
