"""Documentation / repository consistency checks (MC-02.013-.016, MC-23.012).

* MASTER.md: any mention must either point at an existing file or say it is
  missing/retired (the corpus was never supplied and is not reconstructed).
* Relative Markdown links resolve.
* Every INV-36-Cxxx reference exists in CHECKLIST.json.
* VERSION, pyproject, __init__ and the newest CHANGELOG entry agree.
* Known-stale claims from earlier releases do not reappear.
* Source corpora under docs/source match their recorded SHA-256.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
DOCS = [p for p in PKG.rglob("*.md") if not any(x in p.parts for x in ("dist", "evidence", ".git"))
        and "docs/source" not in p.as_posix()]
STALE = [
    "carried verbatim",
    "are **not** implemented by this archive",
    "No AF_VSOCK/socket/device implementation",
]
MASTER_OK = re.compile(r"(missing|absent|not (present|supplied|included)|retired|deprecat|never supplied|"
                       r"not reconstructed|not fabricated|not contained|claim)", re.I)
SOURCES = PKG / "docs" / "source" / "SOURCES.json"


def check() -> list[str]:
    problems = []
    controls = {i["check_id"] for i in json.loads((PKG / "CHECKLIST.json").read_text())["items"]}
    for p in DOCS:
        text = p.read_text()
        rel = p.relative_to(PKG).as_posix()
        generated_ledger = rel == "docs/MC_CHECKLIST_STATUS.md"  # quotes checklist item text verbatim
        for m in ([] if generated_ledger else re.finditer(r"MASTER\.md", text)):
            window = text[max(0, m.start() - 300):m.end() + 300]
            if not (PKG / "MASTER.md").exists() and not MASTER_OK.search(window):
                problems.append(f"{rel}: mentions MASTER.md as if present")
        for m in re.finditer(r"\]\(([^)#\s]+)(#[^)]*)?\)", text):
            target = m.group(1)
            if "://" in target or target.startswith("mailto:"):
                continue
            if not (p.parent / target).exists() and not (PKG / target).exists():
                problems.append(f"{rel}: broken link {target}")
        for m in re.finditer(r"INV-36-C(\d{3})", text):
            if f"INV-36-C{m.group(1)}" not in controls:
                problems.append(f"{rel}: unknown control INV-36-C{m.group(1)}")
        if rel not in ("AUDIT_REPORT.md", "CHANGELOG.md", "docs/MC_CHECKLIST_STATUS.md", "docs/MASTER_MD_STATUS.md"):
            for s in STALE:
                if s in text:
                    problems.append(f"{rel}: stale claim '{s}'")
    version = (PKG / "VERSION").read_text().strip()
    if f'version = "{version}"' not in (PKG / "pyproject.toml").read_text():
        problems.append("pyproject version differs from VERSION")
    if f'__version__ = "{version}"' not in (PKG / "__init__.py").read_text():
        problems.append("__init__ version differs from VERSION")
    top = re.search(r"^## (\S+)", (PKG / "CHANGELOG.md").read_text(), re.M)
    if not top or top.group(1) != version:
        problems.append("CHANGELOG newest entry differs from VERSION")
    if SOURCES.exists():
        for name, meta in json.loads(SOURCES.read_text()).items():
            f = PKG / "docs" / "source" / name
            if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() != meta["sha256"]:
                problems.append(f"docs/source/{name}: digest mismatch or missing")
    return problems


def main() -> int:
    p = check()
    print(json.dumps({"ok": not p, "problems": p}, indent=1))
    return 1 if p else 0


if __name__ == "__main__":
    sys.exit(main())
