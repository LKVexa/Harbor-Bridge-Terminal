"""Documentation consistency check (GAP04-C56-017): broken relative links/anchors, stale
version references, required MASTER.md sections, and files claimed in docs that do not exist.
Exit 0 when clean; prints problems otherwise."""
import re, sys
from pathlib import Path
PKG = Path(__file__).resolve().parents[1]
REQUIRED = ["Normative", "Architecture", "Trust boundaries", "State machine", "Lease lifecycle", "Partition lifecycle",
            "Reconciliation lifecycle", "Failure model", "Adjacent contracts", "Security", "Persistence", "Verification",
            "Operations", "Missing-component register", "Non-goals", "Artifact manifest"]


def check() -> list[str]:
    problems = []
    version = (PKG / "VERSION").read_text().strip()
    docs = [PKG / "MASTER.md", PKG / "README.md", *sorted((PKG / "docs").rglob("*.md"))]
    for d in docs:
        text = d.read_text()
        for m in re.finditer(r"\]\(([^)#\s]+)?(#[^)\s]+)?\)", text):
            target, anchor = m.group(1), m.group(2)
            if target and re.match(r"^[a-z]+://", target):
                continue
            tp = (d.parent / target).resolve() if target else d
            if target and not tp.exists():
                problems.append(f"{d.relative_to(PKG)}: broken link {target}")
                continue
            if anchor and tp.suffix == ".md":
                if f'id="{anchor[1:]}"' not in tp.read_text() and anchor[1:] not in {
                        re.sub(r"[^a-z0-9 -]", "", h.lower()).replace(" ", "-") for h in re.findall(r"^#+ (.+)$", tp.read_text(), re.M)}:
                    problems.append(f"{d.relative_to(PKG)}: broken anchor {target or ''}{anchor}")
        for v in re.findall(r"GAP-04 v?(\d+\.\d+\.\d+)", text):
            if v not in (version, "4.2.0"):
                problems.append(f"{d.relative_to(PKG)}: stale version reference {v}")
        for f in re.findall(r"`((?:runtime|tests|docs|ops|schemas|evidence|tools)/[A-Za-z0-9_./-]+\.(?:py|md|json|yml))`", text):
            if not (PKG / f).exists():
                problems.append(f"{d.relative_to(PKG)}: references missing file {f}")
    master = (PKG / "MASTER.md").read_text()
    for s in REQUIRED:
        if not re.search(rf"^#+ .*{re.escape(s)}", master, re.M | re.I):
            problems.append(f"MASTER.md missing required section: {s}")
    if f"**Document version:** {version}" not in master:
        problems.append("MASTER.md document version does not match VERSION")
    return problems


if __name__ == "__main__":
    p = check()
    print("\n".join(p) or "docs OK")
    sys.exit(1 if p else 0)
