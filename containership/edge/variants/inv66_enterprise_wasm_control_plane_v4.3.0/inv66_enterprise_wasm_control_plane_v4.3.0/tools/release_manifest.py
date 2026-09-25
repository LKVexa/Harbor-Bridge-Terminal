#!/usr/bin/env python3
"""Write/verify RELEASE_MANIFEST.sha256 over every shipped file (MC-001-T06, MC-060)."""
import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "RELEASE_MANIFEST.sha256"
EXCLUDE_DIRS = {"__pycache__", ".git", "dist", "build"}
EXCLUDE = {"RELEASE_MANIFEST.sha256", "perf/results.json"}


def files():
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT).as_posix()
        if p.is_file() and not (set(p.relative_to(ROOT).parts) & EXCLUDE_DIRS) and rel not in EXCLUDE and not rel.endswith(".pyc"):
            yield rel, p


def main():
    if "--write" in sys.argv:
        MANIFEST.write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  ./{rel}\n" for rel, p in files()))
    listed = {}
    for line in MANIFEST.read_text().splitlines():
        h, rel = line.split("  ./", 1)
        listed[rel] = h
    actual = {rel: hashlib.sha256(p.read_bytes()).hexdigest() for rel, p in files()}
    bad = sorted(set(listed) ^ set(actual)) + sorted(r for r in listed if r in actual and listed[r] != actual[r])
    print({"files": len(listed), "mismatches": bad[:20]})
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
