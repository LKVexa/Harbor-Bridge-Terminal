"""Render docs/REQUIREMENTS.md tail from requirements/REQUIREMENTS.json (deterministic)."""
import json
import pathlib

PKG = pathlib.Path(__file__).resolve().parents[1]
MARK = "## Requirements (generated)"


def main() -> int:
    reqs = json.loads((PKG / "requirements" / "REQUIREMENTS.json").read_text())["requirements"]
    doc = PKG / "docs" / "REQUIREMENTS.md"
    head = doc.read_text().split(MARK)[0] + MARK + "\n\n"
    rows = ["| ID | Level | Requirement | Audit | Status |", "|---|---|---|---|---|"]
    for r in reqs:
        st = r["status"] + (f" ({r['blocker']})" if r.get("blocker") else "")
        rows.append(f"| {r['id']} | {r['level']} | {r['text']} | {', '.join(r['audit_ids'])} | {st} |")
    doc.write_text(head + "\n".join(rows) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
