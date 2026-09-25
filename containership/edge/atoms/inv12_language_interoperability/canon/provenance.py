"""MC-046 artifact provenance verifier and MC-047 SBOM / dependency lock.

``ArtifactPolicy`` pins each artifact that may participate at run time (binding
generators, runtime adapters, guest fixtures, policy files) to an approved
version and sha256 digest.  ``verify`` recomputes the digest from bytes on disk
and fails closed on any mismatch, unknown artifact, or unapproved version;
nothing is loaded or executed before verification succeeds.

``sbom()`` emits a CycloneDX 1.5 JSON document listing the package files (with
sha256), the interpreter, and every toolchain used to build the conformance
fixtures (versions probed from the environment at build time).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import platform
import subprocess
import uuid

from .errors import ProvenanceError


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


class ArtifactPolicy:
    def __init__(self, entries: dict, audit=None):
        # entries: name -> {"version": str, "digest": "sha256:<hex>"}
        for name, e in entries.items():
            if set(e) != {"version", "digest"} or not str(e["digest"]).startswith("sha256:") \
                    or len(e["digest"]) != 71:
                raise ProvenanceError("malformed policy entry", path=[name])
        self.entries = {k: dict(v) for k, v in entries.items()}
        self.audit = audit

    def verify(self, name: str, version: str, path) -> str:
        e = self.entries.get(name)
        why = None
        if e is None:
            why = "artifact not in policy"
        elif e["version"] != version:
            why = "artifact version not approved"
        else:
            try:
                actual = sha256_file(path)
            except OSError:
                why = "artifact unreadable"
            else:
                if actual != e["digest"]:
                    why = "artifact digest mismatch"
        if why:
            if self.audit:
                self.audit.emit("provenance_rejected", "verifier", artifact=name, reason=why)
            raise ProvenanceError(why, path=[name])
        return e["digest"]


def _probe(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return (out.stdout or out.stderr).strip().splitlines()[0][:120]
    except Exception:  # noqa: BLE001 - absence is recorded, not fatal
        return None


def toolchains() -> dict:
    return {
        "python": platform.python_version(),
        "rustc": _probe(["rustc", "--version"]),
        "go": _probe(["go", "version"]),
        "node": _probe(["node", "--version"]),
        "os": f"{platform.system()} {platform.release()}",
        "machine": platform.machine(),
    }


def sbom(root, version: str, *, include=("*.py", "*.json", "*.md", "*.wit", "*.rs", "*.go", "*.mjs")) -> dict:
    root = pathlib.Path(root)
    files = sorted({p for pat in include for p in root.rglob(pat)
                    if "__pycache__" not in p.parts and "evidence" not in p.parts and "target" not in p.parts})
    comps = [{
        "type": "file", "name": str(p.relative_to(root)).replace("\\", "/"),
        "hashes": [{"alg": "SHA-256", "content": sha256_file(p)[7:]}],
    } for p in files]
    tc = toolchains()
    tools = [{"type": "application", "name": k, "version": v or "absent"} for k, v in tc.items()]
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.5",
        "serialNumber": "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, f"inv12/{version}/" +
                                                    "".join(c["hashes"][0]["content"] for c in comps))),
        "version": 1,
        "metadata": {"component": {"type": "library", "name": "inv12_language_interoperability",
                                   "version": version, "licenses": [{"license": {"name": "UNSPECIFIED"}}]},
                     "tools": tools},
        "components": comps,
        "dependencies": [{"ref": "inv12_language_interoperability", "dependsOn": []}],
    }


def dependency_lock(version: str) -> dict:
    """Pinned dependency metadata: stdlib only at run time; toolchains for fixtures."""
    return {"package": "inv12_language_interoperability", "version": version,
            "runtime_dependencies": [], "python_requires": ">=3.10",
            "fixture_toolchains": toolchains(),
            "third_party_crates_modules_npm": []}


def write_json(path, obj):
    pathlib.Path(path).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
