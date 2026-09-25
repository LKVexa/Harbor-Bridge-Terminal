"""Documentation link check (A1): every repository path referenced in backticks or markdown links from
MASTER.md, README.md, SECURITY.md and docs/**/*.md must exist."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH_RE = re.compile(r"(?:`|\]\()((?:docs|schemas|fixtures|tests|benchmarks|ops|release|tools|production|requirements)"
                     r"/[A-Za-z0-9_./*-]*|[A-Z_]+\.md|[a-z_]+\.py)(?:[#`)])")


def main() -> int:
    missing = []
    files = [ROOT / "MASTER.md", ROOT / "README.md", ROOT / "SECURITY.md"] + sorted((ROOT / "docs").rglob("*.md"))
    for f in files:
        for m in PATH_RE.finditer(f.read_text(encoding="utf-8")):
            ref = m.group(1).rstrip("/.")
            if "*" in ref or "<" in ref:
                continue
            cands = [ROOT / ref, f.parent / ref, ROOT / "docs" / ref, ROOT / "production" / ref]
            if not any(c.exists() for c in cands):
                missing.append(f"{f.relative_to(ROOT)} -> {ref}")
    for x in missing:
        print("DOC LINK MISSING:", x)
    print("doc links OK" if not missing else f"{len(missing)} missing")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
