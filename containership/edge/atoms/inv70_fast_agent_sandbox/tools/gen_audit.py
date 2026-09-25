"""Generate AUDIT_MATRIX_4.3.0.json, the report tables and the annotated checklist."""
import collections
import json
import pathlib
import re
import sys

from .remediation_status import S

ROOT = pathlib.Path(__file__).resolve().parents[1]


def matrix():
    base = json.loads((ROOT / "AUDIT_MATRIX_4.2.0.json").read_text())
    items = []
    for it in base["items"]:
        it = dict(it)
        if it["check_id"] in S:
            st, impl, tests, gap = S[it["check_id"]]
            it.update(status=st, evidence="; ".join(impl + tests), remaining_gap=gap or "None within repository scope.",
                      previous_status="MISSING")
        items.append(it)
    counts = collections.Counter(i["status"] for i in items)
    return {"element": "INV-70", "version": "4.3.0", "scope": "post-remediation local repository audit",
            "counts": dict(sorted(counts.items())), "items": items}


def annotate(checklist_path: pathlib.Path) -> str:
    text = checklist_path.read_text()
    out = []
    for line in text.splitlines():
        out.append(line)
        m = re.match(r"^## (INV-70-C\d{3}) — ", line)
        if m and m.group(1) in S:
            st, impl, tests, gap = S[m.group(1)]
            out += ["", f"> **4.3.0 remediation status: {st}**  ",
                    f"> Implementation: {', '.join('`'+x+'`' for x in impl)}  ",
                    f"> Tests/evidence: {', '.join('`'+x+'`' for x in tests) or '—'}  "]
            if gap:
                out.append(f"> Remaining: {gap}")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    m = matrix()
    (ROOT / "AUDIT_MATRIX_4.3.0.json").write_text(json.dumps(m, indent=2))
    print(m["counts"])
    if len(sys.argv) > 1:
        src = pathlib.Path(sys.argv[1])
        (ROOT / "INV70_REMEDIATION_CHECKLIST_4.3.0_STATUS.md").write_text(annotate(src))
        print("annotated checklist written")
