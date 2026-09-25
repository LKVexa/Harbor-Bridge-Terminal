"""Build/release manifest (42), SBOM (66) and checksums (19).
Writes RELEASE_MANIFEST.json, sbom.cdx.json and CHECKSUMS.sha256 for the tree.
If GAP01_RELEASE_KEY_FILE is set, the manifest's file map is HMAC-signed
(verify with security.verify_artifacts)."""
from __future__ import annotations

import datetime
import hashlib
import hmac
import json
import os
import pathlib
import platform
import sys
import uuid

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
from gap01_edge_node_supervisor.config import canonical  # noqa: E402

SKIP_PREFIX = ("evidence/", "__pycache__")
GENERATED = {"RELEASE_MANIFEST.json", "CHECKSUMS.sha256"}


def files() -> dict[str, str]:
    out = {}
    for p in sorted(PKG.rglob("*")):
        rel = p.relative_to(PKG).as_posix()
        if not p.is_file() or rel in GENERATED or "__pycache__" in rel or rel.endswith(".pyc") \
                or rel.startswith(SKIP_PREFIX):
            continue
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def main() -> None:
    version = (PKG / "VERSION").read_text().strip()
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    sbom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "serialNumber": f"urn:uuid:{uuid.uuid4()}",
            "version": 1, "metadata": {"timestamp": now, "component": {
                "type": "application", "name": "gap01-edge-node-supervisor", "version": version,
                "bom-ref": "gap01"}},
            "components": [
                {"type": "platform", "name": "cpython", "version": ">=3.10", "bom-ref": "cpython",
                 "licenses": [{"license": {"id": "PSF-2.0"}}], "scope": "required"},
                {"type": "library", "name": "pk_core", "version": "unpinned", "bom-ref": "pk_core",
                 "scope": "optional", "description": "external Post-Kubernetes conformance framework"},
                *[{"type": "library", "name": n, "version": v, "bom-ref": n, "scope": "excluded",
                   "description": "development/CI tool, not shipped"}
                  for n, v in (("ruff", "0.15.11"), ("mypy", "1.20.2"), ("coverage", "7.13.1"))]],
            "dependencies": [{"ref": "gap01", "dependsOn": ["cpython"]}]}
    (PKG / "sbom.cdx.json").write_text(json.dumps(sbom, indent=2) + "\n")
    fmap = files()
    manifest = {"schema": "GAP01_RELEASE/1", "name": "gap01-edge-node-supervisor", "version": version,
                "built": now, "builder": {"python": platform.python_version(), "system": platform.system(),
                                          "machine": platform.machine()},
                "requires_python": ">=3.10", "runtime_dependencies": [],
                "evidence": {rel: hashlib.sha256((PKG / rel).read_bytes()).hexdigest()
                             for rel in ("evidence/evidence.json", "evidence/bench.json", "evidence/soak.json",
                                         "evidence/coverage.json", "evidence/exit_gate.json")
                             if (PKG / rel).exists()},
                "files": fmap}
    key_file = os.environ.get("GAP01_RELEASE_KEY_FILE")
    manifest["signature"] = (hmac.new(pathlib.Path(key_file).read_bytes().strip(), canonical(fmap),
                                      hashlib.sha256).hexdigest() if key_file else None)
    (PKG / "RELEASE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (PKG / "CHECKSUMS.sha256").write_text("".join(f"{h}  {r}\n" for r, h in fmap.items()))
    print(f"{len(fmap)} files; signed={bool(key_file)}")


if __name__ == "__main__":
    main()
