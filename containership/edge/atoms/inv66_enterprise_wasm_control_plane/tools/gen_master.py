"""Generate MASTER.md (MC-001) from CHECKLIST.json, with provenance and a reconciliation check.

    python tools/gen_master.py [--check]

The upstream authority, the Post-Kubernetes Master Prompt & Workflow Series v4.0.0 archive, was not
supplied with this component, so MASTER.md is a *derived, informative* rendering of the bundled
CHECKLIST.json. It is not a copy of the upstream master. --check fails if the file is missing, its
recorded source digest no longer matches CHECKLIST.json, or the ID reconciliation (exactly
C001..C100, in order, once each) fails.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_ID = "INV66-MASTER-DERIVED"
DOC_VERSION = "1.0.0"
GENERATED = "2026-09-22T00:00:00Z"  # fixed so regeneration is byte-identical


def render() -> str:
    raw = (ROOT / "CHECKLIST.json").read_bytes()
    data = json.loads(raw)
    items = data["items"]
    ids = [i["check_id"] for i in items]
    expect = [f"INV-66-C{n:03d}" for n in range(1, 101)]
    if ids != expect:
        raise SystemExit(f"reconciliation failed: {len(ids)} ids, first mismatch "
                         f"{next((a, b) for a, b in zip(ids, expect, strict=False) if a != b)}")
    out = ["# INV-66 master prompt/workflow requirements (derived)", "",
           "| Field | Value |", "|---|---|",
           f"| Document ID | `{DOC_ID}` |", f"| Version | {DOC_VERSION} |",
           "| Status | **Informative.** `CHECKLIST.json` is the machine source; the upstream series is the authority |",
           "| Upstream authority | Post-Kubernetes Master Prompt & Workflow Series **v4.0.0**, element INV-66. The series archive was **not supplied** with this component |",
           "| Source file | `CHECKLIST.json` |",
           f"| Source SHA-256 | `{hashlib.sha256(raw).hexdigest()}` |",
           f"| Item count | {len(items)} (C001..C100, reconciled in order) |",
           f"| Generator | `tools/gen_master.py` {DOC_VERSION} |",
           f"| Generated | {GENERATED} |",
           "| Transformation | identity: one row per item, dimension headings in source order, requirement text verbatim |",
           "",
           "**Change control:** CHECKLIST.json may change only when the upstream series is re-released. Regenerate "
           "with `tools/gen_master.py`; CI lane `master` fails on any drift. To make this document normative, "
           "the owner must supply the upstream archive and record its digest here (MC-001-T01, OPEN_HUMAN).",
           "",
           "**Offline retrieval:** get the series archive `Post_Kubernetes_Master_Prompt_Workflow_Series_v4.0.0.zip` "
           "from the owner's distribution point and compare its INV-66 checklist with the Source SHA-256 above.", ""]
    dim = None
    for it in items:
        if it["dimension"] != dim:
            dim = it["dimension"]
            out += ["", f"## {dim}", ""]
        out.append(f"- **{it['check_id']}** — {it['requirement']}")
    return "\n".join(out) + "\n"


def main() -> int:
    text = render()
    p = ROOT / "MASTER.md"
    if "--check" in sys.argv:
        ok = p.exists() and p.read_text() == text
        print("MASTER.md reconciled (100 ids, digest matches)" if ok else "MASTER.md missing or drifted")
        return 0 if ok else 1
    p.write_text(text)
    print("wrote MASTER.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
