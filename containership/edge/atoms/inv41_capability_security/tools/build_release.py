"""Deterministic release build: archive (built twice and compared), CycloneDX
SBOM, SHA-256 manifest, SLSA-style provenance, development signature
(Sections 7, 24; REQ-SUP-001/002).

Outputs under dist/:
  inv41_capability_security-<ver>.zip   (fixed timestamps, sorted entries, fixed perms)
  SBOM.cdx.json                         (CycloneDX 1.5: no third-party runtime components)
  RELEASE_MANIFEST.json                 (every file + archive + SBOM + spec/schema hashes)
  PROVENANCE.json                       (builder, toolchain, inputs, outputs)
The manifest signature is HMAC with a *development* key and is marked
UNAPPROVED_DEV; production needs B-SIGN-01.
"""
from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
import pathlib
import platform
import sys
import zipfile

PKG = pathlib.Path(__file__).resolve().parents[1]
DIST = PKG / "dist"
EXCLUDE_DIRS = {"__pycache__", "dist", "evidence", ".git"}
FIXED_TIME = (2026, 9, 22, 0, 0, 0)


def files() -> list:
    out = []
    for p in sorted(PKG.rglob("*")):
        rel = p.relative_to(PKG)
        if p.is_file() and not (set(rel.parts) & EXCLUDE_DIRS) and p.suffix != ".pyc":
            out.append(rel.as_posix())
    return out


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def build_zip(listing: list) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in listing:
            info = zipfile.ZipInfo(f"{PKG.name}/{rel}", FIXED_TIME)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, (PKG / rel).read_bytes())
    return buf.getvalue()


def sbom(version: str, archive_sha: str) -> dict:
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "serialNumber": "urn:uuid:" + sha(f"inv41-{version}-{archive_sha}".encode())[:32],
            "metadata": {"component": {"type": "library", "name": "inv41_capability_security", "version": version,
                                       "hashes": [{"alg": "SHA-256", "content": archive_sha}],
                                       "licenses": [{"license": {"name": "UNDECIDED (B-LIC-01)"}}]},
                         "tools": [{"name": "tools/build_release.py"}]},
            "components": [{"type": "platform", "name": "CPython", "version": ">=3.10,<3.14",
                            "scope": "required", "description": "runtime; standard library only"}],
            "dependencies": [{"ref": "inv41_capability_security", "dependsOn": []}],
            "properties": [{"name": "inv41:runtime_third_party_dependencies", "value": "0"},
                           {"name": "inv41:dev_third_party_dependencies", "value": "0"},
                           {"name": "inv41:optional", "value": "pk_core (unpinned, B-EST-01)"},
                           {"name": "inv41:vulnerability_scan", "value": "no third-party components to scan; CPython itself must be tracked by the platform"}]}


def sign_manifest(manifest: dict) -> dict:
    key = os.environ.get("INV41_DEV_SIGNING_KEY", "inv41-development-key-not-for-production").encode()
    body = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return {"alg": "HMAC-SHA256", "key_id": "dev-local", "status": "UNAPPROVED_DEV (B-SIGN-01)",
            "mac": hmac.new(key, body, hashlib.sha256).hexdigest()}


def main() -> int:
    version = (PKG / "VERSION").read_text().strip()
    listing = [f for f in files() if f != "RELEASE_MANIFEST.json"]
    a, b = build_zip(listing), build_zip(listing)
    reproducible = a == b
    DIST.mkdir(exist_ok=True)
    arc = DIST / f"{PKG.name}-{version}.zip"
    arc.write_bytes(a)
    asha = sha(a)
    bom = sbom(version, asha)
    (DIST / "SBOM.cdx.json").write_text(json.dumps(bom, indent=1, sort_keys=True))
    entries = [{"path": f, "bytes": (PKG / f).stat().st_size, "sha256": sha((PKG / f).read_bytes())} for f in listing]
    spec = {k: sha((PKG / k).read_bytes()) for k in listing
            if k.startswith(("schemas/", "requirements/", "contracts/", "docs/ADR", "docs/THREAT", "docs/threats"))}
    manifest = {"schema": "INV41_RELEASE_MANIFEST/2", "element": "INV-41", "version": version,
                "source_revision": os.environ.get("INV41_SOURCE_REVISION", "UNVERSIONED-TREE (no VCS in archive)"),
                "algorithm": "sha256", "archive": {"path": arc.name, "sha256": asha, "bytes": len(a)},
                "reproducible_double_build": reproducible,
                "sbom_sha256": sha((DIST / "SBOM.cdx.json").read_bytes()),
                "spec_hashes": spec, "files": entries,
                "evidence": {p.name: sha(p.read_bytes()) for p in sorted((PKG / "evidence").glob("*.json"))} if (PKG / "evidence").exists() else {},
                "provenance": "dist/PROVENANCE.json",
                "verify": "python tools/build_release.py --verify dist/RELEASE_MANIFEST.json"}
    manifest["signature"] = sign_manifest(manifest)
    (DIST / "RELEASE_MANIFEST.json").write_text(json.dumps(manifest, indent=1))
    prov = {"_type": "https://in-toto.io/Statement/v1", "predicateType": "https://slsa.dev/provenance/v1",
            "subject": [{"name": arc.name, "digest": {"sha256": asha}}],
            "predicate": {"buildDefinition": {"buildType": "inv41/build_release@1", "externalParameters": {"version": version},
                                              "resolvedDependencies": [{"uri": "python-stdlib", "digest": {}}]},
                          "runDetails": {"builder": {"id": os.environ.get("INV41_BUILDER_ID", f"local:{platform.node() or 'unknown'}")},
                                         "metadata": {"python": platform.python_version(), "platform": platform.platform(),
                                                      "timestamp_policy": "archive entries fixed to 2026-09-22T00:00:00",
                                                      "slsa_level": "none (unsigned, local builder)"}}}}
    (DIST / "PROVENANCE.json").write_text(json.dumps(prov, indent=1))
    print(json.dumps({"archive": arc.name, "sha256": asha, "reproducible": reproducible, "files": len(entries)}))
    return 0 if reproducible else 1


def verify(path: str) -> int:
    m = json.loads(pathlib.Path(path).read_text())
    sig = m.pop("signature")
    ok = hmac.compare_digest(sign_manifest(m)["mac"], sig["mac"])
    bad = [e["path"] for e in m["files"] if not (PKG / e["path"]).exists() or sha((PKG / e["path"]).read_bytes()) != e["sha256"]]
    print(json.dumps({"signature_valid_dev": ok, "mismatched_files": bad, "production_trusted": False}))
    return 0 if ok and not bad else 1


if __name__ == "__main__":
    if "--verify" in sys.argv:
        raise SystemExit(verify(sys.argv[sys.argv.index("--verify") + 1]))
    raise SystemExit(main())
