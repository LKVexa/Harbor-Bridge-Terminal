"""Generate COMPATIBILITY.md from compatibility.json (the matrix is the single source).
``--check`` exits 1 if the committed markdown is stale."""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def render() -> str:
    d = json.loads((ROOT / "compatibility.json").read_text())
    out = [
        "# INV-23 compatibility matrix",
        "",
        "_Generated from `compatibility.json` by `tools/gen_compat.py`; do not edit by hand._",
        "",
        "Only rows marked **verified** carry hardware/VM evidence. No row is production-supported until it is verified.",
        "",
        "| Status | Meaning |",
        "|---|---|",
    ]
    out += [f"| {k} | {v} |" for k, v in d["statuses"].items()]
    cols = [
        "ID",
        "OS",
        "Versions",
        "Arch",
        "CPU",
        "Technology",
        "Backend",
        "Nested",
        "Claim provider",
        "Status",
        "Expected",
        "Limitations",
        "Last verified",
    ]
    out += ["", "| " + " | ".join(cols) + " |", "|" + "---|" * 13]
    for r in d["rows"]:
        e = r["expected"]
        exp = f"{e['state']}" + (f"/{e['reason']}" if e.get("reason") else "") + f", bare_metal={str(e['bare_metal']).lower()}"
        lv = f"{r['last_verified']['date']} ({r['last_verified']['environment']})" if r["last_verified"] else "—"
        cells = [
            r["id"],
            r["os"],
            r["os_versions"],
            r["architecture"],
            r["cpu_vendor"],
            r["technology"],
            r["backend"],
            r["nested"],
            r["claim_provider"],
            f"**{r['status']}**",
            exp,
            r["limitations"] or "—",
            lv,
        ]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    md = render()
    p = ROOT / "COMPATIBILITY.md"
    if "--check" in sys.argv:
        sys.exit(0 if p.exists() and p.read_text() == md else 1)
    p.write_text(md)
