"""Render the generated sections of SEMANTICS.md from code (single source of
truth).  ``--check`` exits 1 if the committed document is out of date."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent))
pkg = __import__(HERE.name)
BEGIN, END = "<!-- BEGIN GENERATED -->", "<!-- END GENERATED -->"


def generated() -> str:
    from importlib import import_module
    lc = import_module(HERE.name + ".lifecycle")
    out = ["### Outcome and error-code registry (from `outcomes.ERROR_CODES`)", "",
           "| Code | Outcome class | Retryable | Max attempts | New transfer id | Progress | Caller obligation |",
           "|---|---|---|---|---|---|---|"]
    for c, s in sorted(pkg.ERROR_CODES.items()):
        out.append(f"| `{c}` | {s.outcome.value} | {'yes' if s.retryable else 'no'} | {s.max_attempts} | "
                   f"{'yes' if s.new_transfer_id_required else 'no'} | {s.progress.value} | {s.caller_action} |")
    out += ["", "### Lifecycle transition table (from `lifecycle.TRANSITIONS`)", "",
            "Every (state, event) pair not listed is refused with `illegal_transition`; the state is left unchanged.", "",
            "| From | Event | To |", "|---|---|---|"]
    for t in lc.transition_table():
        out.append(f"| {t['from']} | {t['event']} | {t['to']} |")
    out += ["", "Idempotent repeats (no-op): " + "; ".join(
        f"`{e.value}` in {{{', '.join(sorted(s.value for s in states))}}}" for e, states in lc.IDEMPOTENT.items())]
    return "\n".join(out)


def main() -> int:
    p = HERE / "SEMANTICS.md"
    text = p.read_text()
    a, b = text.index(BEGIN) + len(BEGIN), text.index(END)
    new = text[:a] + "\n" + generated() + "\n" + text[b:]
    if "--check" in sys.argv:
        ok = new == text
        print("SEMANTICS.md up to date" if ok else "SEMANTICS.md is stale; run tools/render_semantics.py")
        return 0 if ok else 1
    p.write_text(new)
    return 0


if __name__ == "__main__":
    sys.exit(main())
