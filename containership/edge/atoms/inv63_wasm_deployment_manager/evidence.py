"""Evidence helpers shared by audit.py, gate.py and perf/bench.py (INV-63-C090, C100).

``source_digest`` binds evidence to the exact package contents: sha256 over the
sorted (path, sha256) list of every source file, excluding generated evidence.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

PKG_DIR = pathlib.Path(__file__).resolve().parent

GENERATED = {
    "AUDIT_RESULTS.json", "AUDIT_REPORT.md", "MISSING_COMPONENTS.md", "MANIFEST.sha256",
    "docs/requirements/TRACEABILITY.md", "docs/requirements/REQUIREMENTS.json", "docs/requirements/REQUIREMENTS.md",
    "perf/results.json", "release/GATE_RESULT.json", "SBOM.json",
    "governance/APPROVALS.json",   # approvals sign the digest, so they cannot be part of it
}
GENERATED_DIRS = ("evidence/", "__pycache__/", ".git/")


def source_files(root: pathlib.Path = PKG_DIR) -> list[str]:
    out = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if rel in GENERATED or any(seg in rel for seg in GENERATED_DIRS) or rel.endswith(".pyc"):
            continue
        out.append(rel)
    return out


def source_digest(root: pathlib.Path = PKG_DIR) -> str:
    h = hashlib.sha256()
    for rel in source_files(root):
        h.update(rel.encode() + b"\0" + hashlib.sha256((root / rel).read_bytes()).hexdigest().encode() + b"\n")
    return "sha256:" + h.hexdigest()


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def write_manifest(root: pathlib.Path = PKG_DIR) -> str:
    files = [p.relative_to(root).as_posix() for p in sorted(root.rglob("*"))
             if p.is_file() and "__pycache__" not in p.parts and p.name != "MANIFEST.sha256"
             and not p.relative_to(root).as_posix().startswith("evidence/")]
    lines = [f"{hashlib.sha256((root / f).read_bytes()).hexdigest()}  {f}" for f in files]
    (root / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")
    return hashlib.sha256((root / "MANIFEST.sha256").read_bytes()).hexdigest()


def verify_manifest(root: pathlib.Path = PKG_DIR) -> list[str]:
    bad = []
    for line in (root / "MANIFEST.sha256").read_text().splitlines():
        digest, rel = line.split("  ", 1)
        p = root / rel
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            bad.append(rel)
    return bad
