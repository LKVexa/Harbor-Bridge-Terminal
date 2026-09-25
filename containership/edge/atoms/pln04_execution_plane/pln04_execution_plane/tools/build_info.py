"""M46 - emit reproducible build/install metadata (evidence/BUILD_INFO.json).

Digest = SHA-256 over the sorted (path, sha256) list of every shipped file, so
the same tree always yields the same release digest regardless of zip order
or timestamps.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import platform
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {"__pycache__", "evidence", ".git"}


def shipped_files() -> list[pathlib.Path]:
    return sorted(p for p in ROOT.rglob("*") if p.is_file() and not (set(p.relative_to(ROOT).parts) & EXCLUDE_DIRS)
                  and p.suffix not in (".pyc",))


def tree_digest() -> tuple[str, list[dict]]:
    files = [{"path": p.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
              "bytes": p.stat().st_size} for p in shipped_files()]
    h = hashlib.sha256("".join(f"{f['path']}\0{f['sha256']}\n" for f in files).encode()).hexdigest()
    return "sha256:" + h, files


def build_info() -> dict:
    digest, files = tree_digest()
    return {"schema": "PK_PLN04_BUILD/1", "component": "PLN-04", "version": (ROOT / "VERSION").read_text().strip(),
            "tree_digest": digest, "file_count": len(files), "python_requires": ">=3.10",
            "built_with": {"python": platform.python_version(), "implementation": platform.python_implementation()},
            "runtime_dependencies": [], "lock": "requirements.lock"}


if __name__ == "__main__":
    info = build_info()
    out = ROOT / "evidence" / "BUILD_INFO.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(info, indent=2))
    print(json.dumps(info, indent=2))
