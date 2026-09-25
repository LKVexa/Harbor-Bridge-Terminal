"""Deterministic release builder: MANIFEST (per-file sha256), CycloneDX SBOM, reproducible zip (MC-015, MC-050).

The manifest covers every shipped file except the gate outputs listed in GATE_OUTPUTS (which are produced *about*
the payload and bind to ``payload_digest`` = sha256 of the canonical manifest).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import zipfile

PKG = pathlib.Path(__file__).resolve().parents[1]
NAME = PKG.name
EXCLUDE_DIRS = {"__pycache__", ".git", "dist"}
GATE_OUTPUTS = {"conformance/EXIT_GATE.json", "conformance/CLOSURE_LEDGER.json", "conformance/MANIFEST.json",
                "conformance/test_results.json", "conformance/perf_gate_result.json"}
FIXED_TIME = (2026, 9, 23, 0, 0, 0)


def files(root: pathlib.Path = PKG) -> list[pathlib.Path]:
    out = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if p.is_file() and not (set(rel.parts) & EXCLUDE_DIRS) and p.suffix not in (".pyc",):
            out.append(p)
    return out


def version(root: pathlib.Path = PKG) -> str:
    return (root / "VERSION").read_text().strip()


def manifest(root: pathlib.Path = PKG, exclude: frozenset = frozenset()) -> dict:
    entries = {}
    for p in files(root):
        rel = p.relative_to(root).as_posix()
        if rel in GATE_OUTPUTS or rel in exclude:
            continue
        entries[rel] = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
    body = {"schema": "PLN01_MANIFEST/1", "component": "PLN-01", "version": version(root), "files": entries,
            "runtime_dependencies": [], "optional_dependencies": {"pk-core": "pk_core>=4.0,<5"},
            "specifications": sorted(p.name for p in (root / "schemas").glob("*.json"))}
    body["payload_digest"] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return body


def sbom(man: dict) -> dict:
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "library", "name": "pln01-intent-plane", "version": man["version"],
                                       "hashes": [{"alg": "SHA-256", "content": man["payload_digest"]}],
                                       "description": "hash = payload digest of all files except this SBOM and gate outputs",
                                       "licenses": [{"license": {"name": "LicenseRef-LinearFinance-AllRightsReserved"}}]}},
            "components": [{"type": "library", "name": "pk_core", "version": ">=4.0,<5", "scope": "optional"}],
            "dependencies": [{"ref": "pln01-intent-plane", "dependsOn": []}]}


def build(out_dir: pathlib.Path, root: pathlib.Path = PKG) -> dict:
    (root / "conformance" / "sbom.cdx.json").write_text(json.dumps(sbom(manifest(root, frozenset({"conformance/sbom.cdx.json"}))), indent=2))
    man = manifest(root)   # sbom now included in the payload
    (root / "conformance" / "MANIFEST.json").write_text(json.dumps(man, indent=1))
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / f"{NAME}_v{man['version']}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files(root):
            info = zipfile.ZipInfo(f"{NAME}/{p.relative_to(root).as_posix()}", FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, p.read_bytes())
    return {"archive": str(archive), "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "payload_digest": man["payload_digest"], "files": len(man["files"])}


def verify_tree(root: pathlib.Path) -> list[str]:
    stored = json.loads((root / "conformance" / "MANIFEST.json").read_text())
    fresh = manifest(root)
    problems = [f"changed: {k}" for k, v in stored["files"].items() if fresh["files"].get(k) != v]
    problems += [f"unlisted: {k}" for k in fresh["files"] if k not in stored["files"]]
    if fresh["payload_digest"] != stored["payload_digest"]:
        problems.append("payload digest mismatch")
    return problems


if __name__ == "__main__":
    print(json.dumps(build(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else PKG.parent / "dist")), indent=2))
