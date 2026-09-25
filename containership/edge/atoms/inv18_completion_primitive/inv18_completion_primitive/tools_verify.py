"""SHA256SUMS generation and verification for the shipped tree (C045)."""
from __future__ import annotations

import hashlib
import pathlib

# produced by the release pipeline *after* SHA256SUMS is written (would be circular)
GENERATED = {"conformance/RTM.json", "conformance/RTM.md", "conformance/RELEASE_EVIDENCE.json",
             "conformance/TEST_RESULTS.json", "conformance/BENCH_RESULTS.json", "conformance/LINEAGE.json",
             "conformance/COMPAT_RESULTS.json",
             "SHA256SUMS"}
SKIP_DIRS = {"__pycache__", "evidence", ".git"}


def shipped_files(root: pathlib.Path) -> list[str]:
    out = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        rel = p.relative_to(root).as_posix()
        if rel in GENERATED or rel.endswith((".pyc", ".pyo")):
            continue
        out.append(rel)
    return out


def write_sums(root: pathlib.Path) -> str:
    lines = [f"{hashlib.sha256((root / r).read_bytes()).hexdigest()}  {r}" for r in shipped_files(root)]
    text = "\n".join(lines) + "\n"
    (root / "SHA256SUMS").write_text(text)
    return text


def verify_tree(root: pathlib.Path) -> list[str]:
    """Return problems: changed, missing and unlisted files (empty = intact)."""
    sums = root / "SHA256SUMS"
    if not sums.exists():
        return ["SHA256SUMS missing"]
    listed = {}
    for line in sums.read_text().splitlines():
        if line.strip():
            d, rel = line.split(None, 1)
            listed[rel.strip()] = d
    problems = []
    for rel, d in listed.items():
        f = root / rel
        if not f.exists():
            problems.append(f"missing: {rel}")
        elif hashlib.sha256(f.read_bytes()).hexdigest() != d:
            problems.append(f"changed: {rel}")
    for rel in shipped_files(root):
        if rel not in listed:
            problems.append(f"unlisted: {rel}")
    return problems
