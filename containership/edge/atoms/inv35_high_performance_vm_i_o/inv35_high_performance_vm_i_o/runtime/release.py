"""Release manifest, SBOM, provenance, sealed evidence and the production exit gate.

Covers INV-35-C045 (artifact digest verification), C070 (performance regression
gate input), C078 (release lineage), C090 (machine-readable sealed acceptance
evidence), C100 (formal exit gate) and REPO-006/REPO-010.

Sealing uses HMAC-SHA-256 with a key supplied through ``INV35_EVIDENCE_KEY``
(hex, >= 32 bytes).  Without it evidence is produced *unsealed* and the gate can
never report production-green.  A production pipeline replaces the HMAC with a
Sigstore/in-toto signature bound to the CI identity; see
docs/operations/RELEASE_AND_SUPPLY_CHAIN.md.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import hmac
import json
import os
from pathlib import Path
import platform
import sys
from typing import Any

from .security import canonical

PKG = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {"__pycache__", ".git", "evidence", "conformance", "release"}
EXCLUDE_SUFFIX = {".pyc"}


def iter_release_files(root: Path = PKG):
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if path.is_file() and not (set(rel.parts) & EXCLUDE_DIRS) and path.suffix not in EXCLUDE_SUFFIX:
            yield rel.as_posix(), path


def build_manifest(root: Path = PKG) -> dict[str, Any]:
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    files = {rel: hashlib.sha256(p.read_bytes()).hexdigest() for rel, p in iter_release_files(root)}
    tree = hashlib.sha256(canonical(files)).hexdigest()
    return {"schema": "INV35_RELEASE_MANIFEST/1", "version": version, "tree_digest": tree, "files": files}


def verify_manifest(manifest: dict[str, Any], root: Path = PKG) -> list[str]:
    """Return a list of problems; empty means every listed file matches and nothing is unlisted."""
    problems = []
    current = build_manifest(root)
    for rel, digest in manifest["files"].items():
        got = current["files"].get(rel)
        if got is None:
            problems.append(f"missing: {rel}")
        elif got != digest:
            problems.append(f"digest mismatch: {rel}")
    for rel in sorted(set(current["files"]) - set(manifest["files"])):
        problems.append(f"unlisted: {rel}")
    if hashlib.sha256(canonical(manifest["files"])).hexdigest() != manifest["tree_digest"]:
        problems.append("tree digest does not match file list")
    return problems


def build_sbom(manifest: dict[str, Any]) -> dict[str, Any]:
    deps = json.loads((PKG / "release" / "dependencies.json").read_text(encoding="utf-8"))
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "metadata": {"component": {"type": "library", "name": "inv35-high-performance-vm-io",
                                   "version": manifest["version"],
                                   "hashes": [{"alg": "SHA-256", "content": manifest["tree_digest"]}],
                                   "licenses": [{"license": {"name": deps["license"]}}]}},
        "components": [{"type": d["type"], "name": d["name"], "version": d["version"], "scope": d["scope"],
                        "properties": [{"name": "inv35:pin_state", "value": d["pin_state"]}]}
                       for d in deps["dependencies"]],
    }


def build_provenance(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": f"inv35_high_performance_vm_i_o-{manifest['version']}",
                     "digest": {"sha256": manifest["tree_digest"]}}],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {"buildType": "inv35/verify.py", "externalParameters": {"version": manifest["version"]}},
            "runDetails": {"builder": {"id": os.environ.get("INV35_BUILDER_ID", "local-unattested")},
                           "metadata": {"startedOn": _dt.datetime.now(_dt.timezone.utc).isoformat()}},
        },
    }


def environment_record() -> dict[str, Any]:
    return {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
            "platform": platform.platform(), "machine": platform.machine()}


def seal(document: dict[str, Any]) -> dict[str, Any]:
    body = canonical(document)
    digest = hashlib.sha256(body).hexdigest()
    key_hex = os.environ.get("INV35_EVIDENCE_KEY", "")
    try:
        key = bytes.fromhex(key_hex) if key_hex else b""
    except ValueError:
        key = b""
    if len(key) >= 32:
        return {"sha256": digest, "sealed": True, "alg": "HMAC-SHA256",
                "key_id": hashlib.sha256(key).hexdigest()[:16],
                "mac": hmac.new(key, body, hashlib.sha256).hexdigest()}
    return {"sha256": digest, "sealed": False, "reason": "INV35_EVIDENCE_KEY not provided"}


def verify_seal(document: dict[str, Any], seal_record: dict[str, Any], key: bytes | None = None) -> bool:
    body = canonical(document)
    if hashlib.sha256(body).hexdigest() != seal_record.get("sha256"):
        return False
    if not seal_record.get("sealed"):
        return False
    return key is not None and hmac.compare_digest(hmac.new(key, body, hashlib.sha256).hexdigest(), seal_record["mac"])


# ---------------------------------------------------------------------------
# Governance evaluation for the exit gate (C009, C098, C099, C100, REPO-001/011)
# ---------------------------------------------------------------------------

def _load(rel: str) -> Any:
    return json.loads((PKG / rel).read_text(encoding="utf-8"))


def governance_findings(today: _dt.date | None = None) -> list[dict[str, str]]:
    today = today or _dt.date.today()
    out: list[dict[str, str]] = []
    owners = _load("governance/OWNERS.json")
    for role, entry in owners["roles"].items():
        if entry.get("name") in (None, "", "UNASSIGNED"):
            out.append({"gate": "ownership", "severity": "blocker", "detail": f"role {role} unassigned"})
        elif entry.get("status") != "accepted":
            out.append({"gate": "ownership", "severity": "blocker", "detail": f"role {role} not accepted by {entry['name']}"})
    lic = _load("governance/LICENSE_DECISION.json")
    if lic.get("status") != "approved" or not (PKG / "LICENSE").is_file():
        out.append({"gate": "license", "severity": "blocker", "detail": "repository license not selected/approved"})
    for a in _load("governance/APPROVALS.json")["approvals"]:
        if a["status"] != "approved":
            out.append({"gate": "approval", "severity": "blocker", "detail": f"{a['artifact']} awaiting {a['required_role']}"})
    for w in _load("governance/WAIVERS.json")["waivers"]:
        if _dt.date.fromisoformat(w["expires"]) < today:
            out.append({"gate": "waiver", "severity": "blocker", "detail": f"waiver {w['id']} expired {w['expires']}"})
        if w.get("approved_by") in (None, "", "UNASSIGNED"):
            out.append({"gate": "waiver", "severity": "blocker", "detail": f"waiver {w['id']} not approved"})
    reviews = _load("governance/REVIEW_SCHEDULE.json")
    for r in reviews["reviews"]:
        if r.get("next_due") and _dt.date.fromisoformat(r["next_due"]) < today:
            out.append({"gate": "review", "severity": "blocker", "detail": f"review {r['id']} overdue"})
    deps = _load("release/dependencies.json")
    for d in deps["dependencies"]:
        if d["scope"] == "required" and d["pin_state"] != "pinned":
            out.append({"gate": "dependency", "severity": "blocker", "detail": f"{d['name']} not pinned ({d['pin_state']})"})
    return out
