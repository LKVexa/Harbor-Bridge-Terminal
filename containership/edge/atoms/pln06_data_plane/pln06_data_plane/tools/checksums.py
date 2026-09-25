"""Regenerate SHA256SUMS.txt for the source tree (evidence/ and caches excluded)."""
from __future__ import annotations

import hashlib
import pathlib

PKG = pathlib.Path(__file__).resolve().parents[1]
SKIP = {"__pycache__", "evidence", ".mypy_cache", ".ruff_cache", ".git"}


def main() -> int:
    files = sorted(p for p in PKG.rglob("*") if p.is_file() and not (SKIP & set(p.relative_to(PKG).parts))
                   and p.name != "SHA256SUMS.txt")
    (PKG / "SHA256SUMS.txt").write_text("".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  ./{p.relative_to(PKG).as_posix()}\n" for p in files))
    print(len(files))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
