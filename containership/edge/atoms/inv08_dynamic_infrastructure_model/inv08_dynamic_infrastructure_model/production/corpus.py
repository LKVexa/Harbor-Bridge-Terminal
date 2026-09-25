"""Component 06 - prompt/workflow corpus manifest and README drift detection.

Corpus manifest (PK_DYN_CORPUS/1)::

  {"schema": "PK_DYN_CORPUS/1", "version": "MAJOR.MINOR.PATCH",
   "items": [{"id": "CORPUS-NNN", "path": str, "distribution": "bundled"|"external",
              "controls": ["INV-08-C0NN", ...], "sha256": hex|null, "state": str}]}

Rules: bundled items MUST exist and match their sha256; external items MUST have
``sha256`` null and state BLOCKED/EXTERNAL (never claimed as shipped); every
control id must exist in CHECKLIST.json.  Versioning: any content-digest change
requires a version bump (``version_check``).

Drift detection scans README text for backticked file names and classifies each
mention as a *claim* (asserts presence) or *historical/negated* (e.g. "removed",
"was not", "absent").  A claimed file that is not shipped is drift.  This catches
the 4.1.0 ``MASTER.md`` defect.  MASTER.md itself is absent -> scope/ownership
BLOCKED.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .core import digest, sha256_hex

SCHEMA = "PK_DYN_CORPUS/1"
PKG_DIR = Path(__file__).resolve().parent.parent
_FILE_RE = re.compile(r"`([A-Za-z0-9_./-]+\.(?:md|json|py|txt|toml))`")
_NEG_RE = re.compile(r"\b(not|never|no longer|removed|absent|missing|nonexistent|was not|external|inaccurate)\b", re.I)

DEFAULT_MANIFEST = {
    "schema": SCHEMA, "version": "0.1.0",
    "items": [{"id": "CORPUS-001", "path": "MASTER.md", "distribution": "external",
               "controls": ["INV-08-C001", "INV-08-C011"], "sha256": None, "state": "BLOCKED",
               "owner": "UNASSIGNED"}],
}


def detect_drift(readme: str, shipped: set[str]) -> list[dict]:
    out = []
    sentences = re.split(r"(?<=[.!?])\s+|\n\s*\n|\n-\s", readme)
    for s in sentences:
        for m in _FILE_RE.finditer(s):
            name = m.group(1)
            present = name in shipped or Path(name).name in {Path(x).name for x in shipped}
            kind = "historical" if _NEG_RE.search(s) else "claim"
            if kind == "claim" and not present:
                out.append({"file": name, "kind": "DRIFT", "sentence": s.strip()[:200]})
            elif kind == "historical" and not present:
                out.append({"file": name, "kind": "NOTED_ABSENT", "sentence": s.strip()[:200]})
    return out


def shipped_files(root: Path = PKG_DIR) -> set[str]:
    return {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts}


def control_ids(root: Path = PKG_DIR) -> set[str]:
    return {i["check_id"] for i in json.loads((root / "CHECKLIST.json").read_text(encoding="utf-8"))["items"]}


def validate_manifest(man: dict, root: Path = PKG_DIR, controls: set[str] | None = None) -> list[str]:
    p = []
    if man.get("schema") != SCHEMA:
        p.append("schema mismatch")
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(man.get("version"))):
        p.append("version must be semver")
    controls = control_ids(root) if controls is None else controls
    ids = set()
    for it in man.get("items", []):
        if it.get("id") in ids:
            p.append(f"duplicate id {it.get('id')}")
        ids.add(it.get("id"))
        for c in it.get("controls", []):
            if c not in controls:
                p.append(f"{it['id']}: unknown control {c}")
        if not it.get("controls"):
            p.append(f"{it['id']}: no control linkage")
        f = root / it["path"]
        if it.get("distribution") == "bundled":
            if not f.is_file():
                p.append(f"{it['id']}: bundled file {it['path']} missing")
            elif sha256_hex(f.read_bytes()) != it.get("sha256"):
                p.append(f"{it['id']}: digest mismatch")
        elif it.get("distribution") == "external":
            if it.get("sha256") is not None or it.get("state") not in {"BLOCKED", "EXTERNAL"}:
                p.append(f"{it['id']}: external item must not claim a shipped digest")
        else:
            p.append(f"{it['id']}: distribution must be bundled|external")
    return p


def version_check(old: dict, new: dict) -> list[str]:
    def content(m):
        return digest(sorted(((i["id"], i.get("sha256"), i["path"]) for i in m["items"])))
    if content(old) != content(new):
        o = tuple(int(x) for x in old["version"].split("."))
        n = tuple(int(x) for x in new["version"].split("."))
        if n <= o:
            return ["corpus content changed without a version bump"]
    return []
