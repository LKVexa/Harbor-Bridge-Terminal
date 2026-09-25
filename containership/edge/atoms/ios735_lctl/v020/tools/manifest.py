#!/usr/bin/env python3
"""Create or verify MANIFEST.sha256 for repository release files."""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "MANIFEST.sha256"
EXCLUDED_NAMES = {"MANIFEST.sha256", ".DS_Store", "Thumbs.db"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".tmp", ".new"}


def release_files():
    files = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(ROOT)
        if path.name in EXCLUDED_NAMES or path.suffix in EXCLUDED_SUFFIXES or "__pycache__" in rel.parts or ".git" in rel.parts:
            continue
        files.append(path)
    return sorted(files, key=lambda p: p.relative_to(ROOT).as_posix())


def digest(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def render():
    return "".join(f"{digest(path)}  {path.relative_to(ROOT).as_posix()}\n" for path in release_files())


def write_manifest():
    text = render()
    fd, tmp = tempfile.mkstemp(prefix="MANIFEST.sha256.", suffix=".tmp", dir=ROOT)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, MANIFEST)
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise
    print(f"wrote {MANIFEST.name} with {len(release_files())} files")


def verify_manifest():
    if not MANIFEST.is_file():
        print("FAIL: MANIFEST.sha256 is missing")
        return 1
    expected = {}
    for lineno, line in enumerate(MANIFEST.read_text(encoding="utf-8").splitlines(), start=1):
        m = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not m:
            print(f"FAIL: malformed manifest line {lineno}")
            return 1
        rel = m.group(2)
        if rel in expected or rel.startswith("/") or ".." in Path(rel).parts:
            print(f"FAIL: unsafe/duplicate manifest path on line {lineno}: {rel}")
            return 1
        expected[rel] = m.group(1)
    actual_paths = {p.relative_to(ROOT).as_posix(): p for p in release_files()}
    missing = sorted(set(expected) - set(actual_paths))
    extra = sorted(set(actual_paths) - set(expected))
    bad = sorted(rel for rel, path in actual_paths.items() if rel in expected and digest(path) != expected[rel])
    if missing or extra or bad:
        if missing:
            print("FAIL: manifest entries missing from repository:", ", ".join(missing[:10]))
        if extra:
            print("FAIL: unmanifested release files:", ", ".join(extra[:10]))
        if bad:
            print("FAIL: digest mismatch:", ", ".join(bad[:10]))
        return 1
    print(f"PASS: MANIFEST.sha256 verified {len(expected)} release files")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="regenerate MANIFEST.sha256 instead of checking it")
    args = ap.parse_args(argv)
    if args.write:
        write_manifest()
        return 0
    return verify_manifest()


if __name__ == "__main__":
    sys.exit(main())
