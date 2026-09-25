"""Operator explain view (MC-075): renders a PK_UNIKERNEL_DECISION/1 record as plain text."""
from __future__ import annotations

from .errors import REGISTRY
from .redaction import redact

STEP_TITLES = {
    "A0": "image bytes received", "A1": "digest bound", "A2": "signature + provenance verified",
    "A3": "manifest parsed", "A4": "ELF parsed", "A5": "statically linked", "A6": "facts derived",
    "A7": "toolchain agreed", "A8": "no fork/exec/dlopen/debug capability", "A9": "single address space proven",
    "A10": "syscall set matches and is permitted", "A11": "architecture matches site",
    "A12": "boot contract holds", "A13": "isolation plan within policy",
}
ORDER = list(STEP_TITLES)


def render(decision: dict) -> str:
    d = redact(decision)
    lines = [f"INV-27 admission decision for {d.get('image') or '<unhashed input>'}",
             f"verifier {d.get('verifier')}  outcome {str(d.get('outcome', '?')).upper()}  "
             f"({d.get('duration_ms')} ms)"]
    done = {s["step"] for s in d.get("steps", [])}
    for s in d.get("steps", []):
        facts = ", ".join(f"{k}={v}" for k, v in s.items() if k not in ("step", "ok"))
        lines.append(f"  [ok]   {s['step']:<4} {STEP_TITLES.get(s['step'], s['step'])}: {facts[:300]}")
    if d.get("code"):
        nxt = next((x for x in ORDER if x not in done), "?")
        c = REGISTRY.get(d["code"])
        lines.append(f"  [FAIL] {nxt:<4} {STEP_TITLES.get(nxt, nxt)}: {d['code']} - {d.get('message')}")
        if c:
            lines.append(f"         class={c.outcome}; " + ("retry with backoff" if c.outcome == "retryable"
                                                           else "do not retry unchanged"))
    return "\n".join(lines) + "\n"
