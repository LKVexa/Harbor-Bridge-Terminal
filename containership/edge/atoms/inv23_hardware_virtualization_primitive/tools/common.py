"""Shared helpers for the release tools: canonical JSON, digests, source-tree identity."""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {"evidence", "conformance", "dist", "build", "__pycache__", ".git", ".hypothesis", ".mypy_cache", ".ruff_cache"}


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def source_files():
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if (
            p.is_file()
            and not (set(rel.parts) & EXCLUDE_DIRS)
            and not rel.name.endswith((".pyc", ".egg-info"))
            and not any(part.endswith(".egg-info") for part in rel.parts)
        ):
            yield rel


def source_identity() -> dict:
    lines = [f"{sha256_file(ROOT / r)}  {r.as_posix()}" for r in source_files()]
    ident = {"tree_sha256": sha256_bytes("\n".join(lines).encode()), "file_count": len(lines), "vcs": None, "dirty": None}
    try:
        rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=5)
        if rev.returncode == 0:
            st = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, timeout=5)
            ident.update(vcs={"system": "git", "commit": rev.stdout.strip()}, dirty=bool(st.stdout.strip()))
    except (OSError, subprocess.SubprocessError):
        pass
    return ident


def version() -> str:
    return (ROOT / "VERSION").read_text().strip()
