"""Render evidence/out/STATUS.md (human-readable view of evaluation.json)."""
import json
import os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evidence", "out")


def main():
    with open(os.path.join(OUT, "evaluation.json")) as fh:
        ev = json.load(fh)
    s = ev["summary"]
    L = ["# GAP-12 v4.3.0 checklist status", "",
         f"Items: **{s['items_total']}** — " + ", ".join(f"{k} {v}" for k, v in sorted(s["by_status"].items())), "",
         f"Production gate: **{s['completion_summary']['production_gate_decision']}** · P0 exit gates passed "
         f"{s['completion_summary']['P0_completion']} · P1 {s['completion_summary']['P1_completion']} · P2 {s['completion_summary']['P2_completion']}", "",
         "| Component | Title | Prio | Lifecycle | PASS | NOT-EV | FAIL | Exit gate |", "|---|---|---|---|---|---|---|---|"]
    for c in ev["components"]:
        n = c["counts"]
        L.append(f"| {c['component']} | {c['title']} | {c['priority']} | {c['lifecycle']} | {n.get('PASS', 0)} | "
                 f"{n.get('NOT-EVIDENCED', 0)} | {n.get('FAIL', 0)} | {c['items'][-1]['status']} |")
    L += ["", "## Global definition of done", ""] + [f"- **{g['id']}** {g['status']} — {g['reason']}" for g in s["global_definition_of_done"]]
    L += ["", "## Checklist defects found", ""] + [f"- {d}" for d in s["checklist_defects"]]
    with open(os.path.join(OUT, "STATUS.md"), "w") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
