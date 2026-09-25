"""Fail if any tracked file is not covered by CODEOWNERS (component 01)."""
from __future__ import annotations

import fnmatch
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
SKIP = {"__pycache__", ".git", "evidence"}


def rules() -> list[str]:
    out = []
    for line in (PKG / "CODEOWNERS").read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            pat, *owners = line.split()
            if owners:
                out.append(pat)
    return out


def covered(rel: str, pats: list[str]) -> bool:
    for p in pats:
        if p == "*":
            return True
        p2 = p.lstrip("/")
        if p2.endswith("/") and rel.startswith(p2):
            return True
        if fnmatch.fnmatch(rel, p2):
            return True
    return False


def unowned(pats: list[str] | None = None) -> list[str]:
    pats = rules() if pats is None else pats
    bad = []
    for f in PKG.rglob("*"):
        if f.is_file() and not (set(f.relative_to(PKG).parts) & SKIP):
            rel = f.relative_to(PKG).as_posix()
            if not covered(rel, pats):
                bad.append(rel)
    return bad


def critical_uncovered_without_wildcard() -> list[str]:
    """Production-critical paths must have an explicit (non-wildcard) rule."""
    pats = [p for p in rules() if p != "*"]
    crit = ["contract.py", "security.py", "config.py", "storage.py", "ha.py", "adapters/kafka.py",
            "adapters/rabbitmq.py", "adapters/sqs.py", "schemas/config.schema.json", ".github/workflows/ci.yml"]
    return [c for c in crit if not covered(c, pats)]


if __name__ == "__main__":
    b, c = unowned(), critical_uncovered_without_wildcard()
    if b or c:
        print("unowned:", b, "critical without explicit owner:", c)
        sys.exit(1)
    print("ownership ok")
