"""Verify the repository's local SHA-256 integrity manifest."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "CHECKSUMS.sha256"
IGNORED_NAMES = {"CHECKSUMS.sha256"}
IGNORED_PARTS = {"__pycache__", ".git", ".pytest_cache", ".mypy_cache", ".ruff_cache", "evidence"}  # evidence is regenerated per run


def tracked_files() -> set[str]:
    result: set[str] = set()
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in IGNORED_PARTS for part in path.relative_to(ROOT).parts):
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel not in IGNORED_NAMES and not rel.endswith(".pyc"):
            result.add(rel)
    return result


def main() -> int:
    if not MANIFEST.is_file():
        print("missing CHECKSUMS.sha256", file=sys.stderr)
        return 2
    expected: dict[str, str] = {}
    for line_no, raw in enumerate(MANIFEST.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            digest, rel = raw.split("  ", 1)
        except ValueError:
            print(f"invalid manifest line {line_no}", file=sys.stderr)
            return 2
        rel_path = Path(rel)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            print(f"unsafe manifest path: {rel}", file=sys.stderr)
            return 2
        expected[rel] = digest

    actual_names = tracked_files()
    if actual_names != set(expected):
        missing = sorted(set(expected) - actual_names)
        untracked = sorted(actual_names - set(expected))
        if missing:
            print("missing files: " + ", ".join(missing), file=sys.stderr)
        if untracked:
            print("untracked files: " + ", ".join(untracked), file=sys.stderr)
        return 1

    failed = False
    for rel, expected_digest in sorted(expected.items()):
        actual = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        if actual != expected_digest:
            print(f"checksum mismatch: {rel}", file=sys.stderr)
            failed = True
    if failed:
        return 1
    print(f"integrity OK: {len(expected)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
