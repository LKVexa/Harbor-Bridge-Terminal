"""Where it stopped, in the source you wrote.

A trap code says what kind of failure happened. It does not say which row did
it, and a person or an agent looking at `trap=6` has to go and find out. The
information exists: the VM records a trap frame and a diagnostics ring, both
carrying the instruction pointer, and the compiler emits a BRIR that maps every
instruction index back to its row ID and its line in the source. Nothing here
computes anything -- it joins two records the system already keeps.

The trap names are read out of the runtime's own header, in the order the enum
declares them, so a runtime that adds a trap does not silently shift this file
into being wrong.
"""

from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional


def trap_names(runtime: Optional[str]) -> List[str]:
    """The trap enum, in its own order, from the runtime's header."""
    if not runtime:
        return []
    p = os.path.join(runtime, "src", "brvm.h")
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return []
    m = re.search(r"enum\s+br_trap\s*\{([^}]*)\}", text)
    if not m:
        return []
    out = []
    for tok in m.group(1).split(","):
        tok = tok.strip().split("=")[0].strip()
        if tok.startswith("BR_TRAP_"):
            out.append(tok[len("BR_TRAP_"):])
    return out


def opcode_names(runtime: Optional[str]) -> Dict[int, str]:
    """Opcode number to name, from the compiler's own table."""
    if not runtime:
        return {}
    p = os.path.join(runtime, "tools", "lctl430.py")
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return {}
    m = re.search(r"^OPS\s*=\s*\[([^\]]*)\]", text, re.M)
    if not m:
        return {}
    names = re.findall(r"'([A-Z0-9_]+)'", m.group(1))
    return {i: n for i, n in enumerate(names)}


def _brir(image: str) -> List[Dict[str, object]]:
    p = image[:-6] + ".brir.json" if image.endswith(".brimg") else ""
    if not p or not os.path.isfile(p):
        return []
    try:
        with open(p, encoding="utf-8") as fh:
            return list(json.load(fh).get("instructions") or [])
    except (OSError, ValueError):
        return []


def _source_lines(source: str) -> List[str]:
    try:
        with open(source, encoding="utf-8") as fh:
            return fh.read().split("\n")
    except OSError:
        return []


def locate(ip: int, brir: List[Dict[str, object]],
           lines: List[str]) -> Dict[str, object]:
    """The row an instruction index came from, and the text of it."""
    for ins in brir:
        if int(ins.get("index", -1)) == int(ip):
            ln = int(ins.get("line") or 0)
            return {"row": ins.get("id"), "op": ins.get("op"),
                    "line": ln,
                    "text": lines[ln - 1].strip() if 0 < ln <= len(lines)
                    else None,
                    "capability": ins.get("capability"),
                    "service": ins.get("service")}
    return {"row": None, "op": None, "line": None, "text": None}


def explain(result: Dict[str, object], image: str, source: str,
            runtime: Optional[str]) -> Dict[str, object]:
    """Join the VM's records to the source, and say where it stopped."""
    traps = trap_names(runtime)
    ops = opcode_names(runtime)
    brir = _brir(image)
    lines = _source_lines(source)
    raw = result.get("raw") if isinstance(result.get("raw"), dict) else result
    fault = (raw or {}).get("fault") or {}
    diag = (raw or {}).get("diagnostics") or []
    trace = (raw or {}).get("trace") or []
    trap = int(result.get("trap") or 0)

    def name(t: int) -> str:
        return traps[t] if 0 <= t < len(traps) else f"trap {t}"

    out: Dict[str, object] = {
        "schema": "PA21.STUDIO/FAULT/1",
        "trap": trap, "trap_name": name(trap),
        "machine_status": result.get("machine_status"),
        "trapped": bool(trap),
    }
    if fault.get("have_frame") and trap:
        where = locate(int(fault.get("ip") or 0), brir, lines)
        out["where"] = where
        out["opcode"] = ops.get(int(fault.get("opcode") or -1))
        out["summary"] = (
            f"{name(trap)} at row {where.get('row')} "
            f"({where.get('op') or out.get('opcode')}), source line "
            f"{where.get('line')}: {where.get('text')}"
            if where.get("row") else
            f"{name(trap)} at instruction {fault.get('ip')}")
    elif trap:
        out["summary"] = (f"{name(trap)}, but the VM kept no trap frame for "
                          f"it")
    else:
        out["summary"] = "no trap"
    out["diagnostics"] = [
        {"seq": d.get("seq"), "event": d.get("event"),
         "trap": name(int(d.get("trap") or 0)) if d.get("trap") else None,
         "where": locate(int(d.get("ip") or 0), brir, lines)}
        for d in diag]
    if trace:
        out["trace"] = [
            {"step": t.get("step"),
             **locate(int(t.get("ip") or 0), brir, lines)}
            for t in trace]
        out["traced_steps"] = len(trace)
    return out
