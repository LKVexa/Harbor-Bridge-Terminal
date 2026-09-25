"""Generate docs/components/*.md and docs/CONFIG_SCHEMA.md from the single
sources of truth (evidence/registry.py, wan/config.py SCHEMA) so prose cannot
drift from code.  Run: python3 -B ops/gen_docs.py"""
import os
import sys

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PKG, "evidence"))
sys.path.insert(0, os.path.dirname(PKG))
sys.dont_write_bytecode = True
from registry import REG  # noqa: E402
from evaluate import parse_checklist  # noqa: E402
from gap12_wan_resilience_and_nat_traversal.wan import config  # noqa: E402


def main():
    comps, _ = parse_checklist(os.path.join(PKG, "evidence", "GAP12_CHECKLIST_v4.2.0.md"))
    d = os.path.join(PKG, "docs", "components")
    os.makedirs(d, exist_ok=True)
    idx = ["# GAP-12 component documents", "", "_Generated from `evidence/registry.py` by `ops/gen_docs.py`; do not edit by hand._", "",
           "| Component | Title | Priority | Lifecycle | Code |", "|---|---|---|---|---|"]
    for cid, c in comps.items():
        r = REG[cid]
        txt = [f"# {cid} — {c['title']} ({c['priority']})", "", f"_Generated from `evidence/registry.py`; lifecycle **{r['lifecycle']}**._", "",
               "## Normative requirement",
               (f"- **Success:** {r['success']}." if r["success"] and r["success"] != "n/a" else "- **Success:** not defined — no implementation exists."),
               "- **Failure:** any other outcome, reported with a registered reason code (`wan/reasons.py`); failures never silently fall back to a less-trusted path.",
               "- **Degraded:** a dependency is down/stale (see `wan.state.degraded_policy`); existing trusted sessions continue until trust expiry, new ones are refused.",
               f"- **Unsupported:** {r['unsupported'] or 'nothing declared unsupported'} — reported as `UNSUPPORTED` / NOT-EVIDENCED, never emulated.",
               "- **Policy rejection:** `POLICY_*` reason codes (egress, mechanism disabled, quarantine, untrusted peer, config rejected).", "",
               "## Interfaces", *([f"- `{a}`" for a in r["api"]] or ["- none"]), "",
               "## Dependencies and trust boundaries", *([f"- {x}" for x in r["deps"]] or ["- none declared"]), "",
               "## Configurable parameters", *([f"- `{p}` (validated at construction; see module docstring for units/ranges)" for p in r["params"]] or ["- none"]), "",
               "## Protocol map", "- See the module docstring of the interfaces above for the RFC/specification sections implemented and the explicit deviations.", "",
               "## Operator diagnostics", f"- {r['diag'] or 'none'}",
               "- Escalate (do not auto-retry) on AUTH_* reasons, DNS_MISMATCH, audit-chain breaks and quota exhaustion.",
               "- Disable: kill-switch control naming the mechanism (`wan.rollout.KillSwitch`), or `mechanisms.<name>=false` in config.", ""]
        with open(os.path.join(d, f"{cid}.md"), "w") as fh:
            fh.write("\n".join(txt))
        idx.append(f"| [{cid}]({cid}.md) | {c['title']} | {c['priority']} | {r['lifecycle']} | {', '.join('`' + a + '`' for a in r['api'][:2])} |")
    with open(os.path.join(d, "README.md"), "w") as fh:
        fh.write("\n".join(idx) + "\n")
    with open(os.path.join(PKG, "docs", "CONFIG_SCHEMA.md"), "w") as fh:
        fh.write(config.render_markdown())
    print(f"{len(comps)} component documents")


if __name__ == "__main__":
    main()
