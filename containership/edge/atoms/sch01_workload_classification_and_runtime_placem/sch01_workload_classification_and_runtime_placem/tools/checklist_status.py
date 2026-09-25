"""Per-item status for every checkbox in the SCH-01 v4.2.0 implementation checklist.

Checkboxes are never ticked (the checklist's own backlog semantics).  Each item gets one
state.  Relevance is a lower bound: an item is EVIDENCED_UNREVIEWED only when it shares at
least two content words with the evidence actually cited for its component (test class
source + artifact text).  A coarse component binding cannot manufacture evidence.
"""
from _common import PKG, dump
import json, re, sys
from registry import R

CL = PKG / "governance/SCH-01_v4.2.0_Missing_Component_Implementation_Checklist.md"
STOP = set("""about above after again against every other which where while their there these those would could should
shall within without before under until using through including required requires release production document
component components implementation evidence verify verification define record records produce version versioned
reference automated update updated include includes explicit explicitly""".split())
HUMAN = re.compile(r"\b(approv\w*|owner|accountable|sign-?off|RACI|tabletop|on-call|escalation|drills?)\b", re.I)
EXTERNAL = re.compile(r"\b(fleet|soak|end-to-end|hardware root|TPM|HSM|KMS|multi-host|hypervisor\w*|operating systems|"
                      r"CPU architectures|hosted|provider variants|real (?:cluster|environment|site)|production environment|"
                      r"upstream|pk_core|PLN-0\d|GAP-\d+|INV-33|consensus|linearizable|etcd|raft)\b", re.I)

def words(t): return {w for w in re.findall(r"[a-z][a-z0-9]{4,}", t.lower())} - STOP

def evidence_text(comp):
    state, arts, tests, _ = R[comp]; txt = []
    for t in tests:
        f, cls = t.split("::"); src = (PKG / f).read_text()
        m = re.search(rf"class {cls}\b.*?(?=\nclass |\Z)", src, re.S); txt.append(m.group(0) if m else "")
    for a in arts:
        p = PKG / a
        for q in ([p] if p.is_file() else sorted(p.glob("*")) if p.is_dir() else []):
            if q.is_file(): txt.append(q.read_text(errors="replace")[:6000])
    return words("\n".join(txt))

def items():
    for line in CL.read_text().splitlines():
        m = re.match(r"- \[( |x)\] \*\*((MC|EXT)-\d+)\.([TVED])(\d+)\*\* — (.*)", line)
        f = re.match(r"- \[( |x)\] \*\*(FINAL-\d+)\*\* — (.*)", line)
        if f: yield {"id": f.group(2), "component": "FINAL", "kind": "F", "text": f.group(3), "ticked_in_source": f.group(1) == "x"}
        if m: yield {"id": f"{m.group(2)}.{m.group(4)}{m.group(5)}", "component": m.group(2), "kind": m.group(4),
                     "text": m.group(6), "ticked_in_source": m.group(1) == "x"}

def classify(it, ev):
    if it["component"] == "FINAL":
        return "BLOCKED_BY_EXIT_GATE", "exit gate NO_GO (evidence/EXIT_GATE.json)"
    state, _, _, blocker = R[it["component"]]
    if it["kind"] == "D" and it["id"].endswith("D01"): return "BLOCKED_HUMAN", "owner/approver UNASSIGNED"
    if HUMAN.search(it["text"]): return "BLOCKED_HUMAN", "needs an accountable human decision"
    if state == "BLOCKED_SOURCE": return "BLOCKED_SOURCE", blocker
    if EXTERNAL.search(it["text"]) or (state == "BLOCKED_EXTERNAL" and it["kind"] in "VE"):
        return "BLOCKED_EXTERNAL", blocker or "needs an element or environment not in this archive"
    ov = sorted(words(it["text"]) & ev)
    if len(ov) >= 2:
        label = {"IMPLEMENTED_TESTED": "EVIDENCED_UNREVIEWED", "DRAFTED_UNAPPROVED": "DRAFTED_UNAPPROVED",
                 "BLOCKED_EXTERNAL": "EVIDENCED_PARTIAL_EXTERNAL_OPEN"}.get(state, "NOT_EVIDENCED")
        return label, "overlap: " + ",".join(ov[:6])
    return "NOT_EVIDENCED", "no cited evidence shares >=2 content words with this item"

def main():
    ev = {c: evidence_text(c) for c in R}
    rows = []
    for it in items():
        s, why = classify(it, ev.get(it["component"], set())); rows.append(dict(it, status=s, basis=why))
    counts = {}
    for r in rows: counts[r["status"]] = counts.get(r["status"], 0) + 1
    doc = {"schema": "PK_CHECKLIST_STATUS/1", "items": len(rows), "ticked": 0, "counts": dict(sorted(counts.items())),
           "completion_claims": 0, "rows": rows}
    dump(PKG / "evidence/CHECKLIST_STATUS.json", doc)
    print(json.dumps({k: doc[k] for k in ("items", "ticked", "counts", "completion_claims")}))
    return 0 if len(rows) == 1758 and not any(r["ticked_in_source"] for r in rows) else 1

if __name__ == "__main__": sys.exit(main())
