"""Shared helpers for INV-34 tools. SPDX-License-Identifier: NOASSERTION"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

EXCLUDE_DIRS = {"__pycache__", ".git", "dist", "evidence_runs"}
GENERATED = {"governance/RTM.json", "governance/RTM.md", "governance/SBOM.cdx.json", "governance/MANIFEST.sha256",
             "governance/CHECKLIST_STATUS.json", "governance/CHECKLIST_STATUS.md", "governance/PERF_BASELINE.json",
             "governance/CI_RESULT.json", "governance/PK_CORE_GATE.json", "governance/EXIT_GATE_RESULT.json",
             "governance/BUILD_RESULT.json"}


def source_files() -> list[pathlib.Path]:
    out = []
    for p in sorted(PKG.rglob("*")):
        if p.is_file() and not (set(p.relative_to(PKG).parts) & EXCLUDE_DIRS):
            rel = p.relative_to(PKG).as_posix()
            if rel not in GENERATED and not rel.endswith(".pyc"):
                out.append(p)
    return out


def source_digest() -> str:
    h = hashlib.sha256()
    for p in source_files():
        h.update(p.relative_to(PKG).as_posix().encode() + b"\0" + hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def write_json(rel: str, obj) -> None:
    (PKG / rel).write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n")
