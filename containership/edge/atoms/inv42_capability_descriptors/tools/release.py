#!/usr/bin/env python3
"""MC-014 - reproducible release build, SBOM, provenance, signing, verification.

    python tools/release.py build  --out dist [--key signing.pem]
    python tools/release.py verify --dist dist --pubkey release-pub.pem

build: deterministic source archive (sorted entries, fixed mtime/uid/gid/mode),
CycloneDX 1.5 SBOM, in-toto/SLSA v1 provenance statement, per-file SHA-256
manifest, and an Ed25519 signature over the canonical release manifest.

Signing key: ``--key`` or $INV42_SIGNING_KEY (PEM, Ed25519).  Production keys
must live in an HSM/KMS signing service (KEY_MANAGEMENT.md); a raw key on a CI
runner is not acceptable.  Without a key an ephemeral key is generated and the
manifest is marked ``"channel": "dev-only"`` - the exit gate refuses it.
verify: re-hashes every artifact, checks the signature, SBOM/provenance digests,
and that the archive rebuilds byte-identically from its own contents.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import pathlib
import platform
import subprocess
import sys
import tarfile
import time

PKG = pathlib.Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {"__pycache__", "dist", "evidence", ".git", ".pytest_cache"}
EPOCH = 1_789_000_000  # fixed SOURCE_DATE_EPOCH for reproducibility


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canon(o) -> bytes:
    return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()


def source_files(root=PKG):
    out = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if p.is_file() and not (set(rel.parts) & EXCLUDE_DIRS) and not p.name.endswith((".pyc", ".pem")):
            out.append(rel)
    return out


def build_archive(files, root=PKG) -> bytes:
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for rel in files:
            data = (root / rel).read_bytes()
            ti = tarfile.TarInfo(f"inv42_capability_descriptors/{rel.as_posix()}")
            ti.size, ti.mtime, ti.mode, ti.uid, ti.gid, ti.uname, ti.gname = len(data), EPOCH, 0o644, 0, 0, "", ""
            tar.addfile(ti, io.BytesIO(data))
    gz = io.BytesIO()
    with gzip.GzipFile(fileobj=gz, mode="wb", mtime=EPOCH, filename="") as g:
        g.write(raw.getvalue())
    return gz.getvalue()


def git_info():
    try:
        commit = subprocess.run(["git", "-C", str(PKG), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "-C", str(PKG), "status", "--porcelain"], capture_output=True, text=True).stdout.strip())
        return commit, dirty
    except Exception:  # noqa: BLE001
        return None, None


def load_key(path):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    if path:
        return serialization.load_pem_private_key(pathlib.Path(path).read_bytes(), None), "provided"
    return Ed25519PrivateKey.generate(), "ephemeral"


def cmd_build(a):
    from cryptography.hazmat.primitives import serialization
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    version = (PKG / "VERSION").read_text().strip()
    files = source_files()
    archive = build_archive(files)
    name = f"inv42_capability_descriptors-{version}.tar.gz"
    (out / name).write_bytes(archive)
    file_hashes = {f.as_posix(): sha256((PKG / f).read_bytes()) for f in files}
    spec = json.loads((PKG / "SPEC_MANIFEST.json").read_text())
    sbom = {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "serialNumber": "urn:uuid:" + sha256(archive)[:8] + "-" + sha256(archive)[8:12] + "-4" + sha256(archive)[13:16]
                        + "-8" + sha256(archive)[17:20] + "-" + sha256(archive)[20:32],
        "metadata": {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(EPOCH)),
                     "component": {"type": "library", "name": "inv42-capability-descriptors", "version": version,
                                   "hashes": [{"alg": "SHA-256", "content": sha256(archive)}]}},
        "components": [
            {"type": "platform", "name": "cpython", "version": spec["runtime"]["python"], "scope": "required"},
            {"type": "library", "name": "pk_core", "version": spec["dependencies"]["pk_core"]["requirement"],
             "scope": "optional", "description": "certification framework; unpinned (W-001)"},
            {"type": "library", "name": "cryptography", "version": ">=42", "scope": "excluded",
             "description": "release tooling only"},
        ] + [{"type": "file", "name": k, "hashes": [{"alg": "SHA-256", "content": v}]} for k, v in file_hashes.items()],
    }
    sbom_b = json.dumps(sbom, indent=1, sort_keys=True).encode()
    (out / "sbom.cdx.json").write_bytes(sbom_b)
    commit, dirty = git_info()
    prov = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": name, "digest": {"sha256": sha256(archive)}}],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {"buildType": "urn:inv42:tools/release.py@1", "externalParameters": {"version": version},
                                "resolvedDependencies": [{"uri": "git+local", "digest": {"gitCommit": commit}} if commit else
                                                         {"uri": "archive:unversioned", "digest": {"sha256": sha256(canon(file_hashes))}}]},
            "runDetails": {"builder": {"id": os.environ.get("INV42_BUILDER_ID", f"local:{platform.node()}")},
                           "metadata": {"invocationId": os.environ.get("GITHUB_RUN_ID", "local"), "dirty": dirty,
                                        "python": platform.python_version(), "platform": platform.platform()}},
        },
    }
    prov_b = json.dumps(prov, indent=1, sort_keys=True).encode()
    (out / "provenance.intoto.json").write_bytes(prov_b)
    key, origin = load_key(a.key or os.environ.get("INV42_SIGNING_KEY"))
    pub = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    manifest = {
        "schema": "INV42_RELEASE_MANIFEST/1", "version": version, "protocol": "PK_DESCRIPTOR/2",
        "channel": "production-candidate" if origin == "provided" else "dev-only",
        "artifacts": {name: sha256(archive), "sbom.cdx.json": sha256(sbom_b), "provenance.intoto.json": sha256(prov_b)},
        "source_files": file_hashes, "spec_manifest_sha256": sha256((PKG / "SPEC_MANIFEST.json").read_bytes()),
        "signing_key_sha256": sha256(pub), "created": int(time.time()),
    }
    man_b = canon(manifest)
    (out / "release-manifest.json").write_bytes(man_b)
    (out / "release-manifest.sig").write_text(key.sign(man_b).hex() + "\n")
    (out / "release-pub.pem").write_bytes(pub)
    print(f"built {name} sha256={sha256(archive)} channel={manifest['channel']}")
    return 0


def cmd_verify(a):
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    dist = pathlib.Path(a.dist)
    problems = []
    man_b = (dist / "release-manifest.json").read_bytes()
    man = json.loads(man_b)
    pub_b = pathlib.Path(a.pubkey).read_bytes()
    pub = serialization.load_pem_public_key(pub_b)
    try:
        pub.verify(bytes.fromhex((dist / "release-manifest.sig").read_text().strip()), man_b)
    except (InvalidSignature, ValueError):
        problems.append("manifest signature invalid")
    if man["signing_key_sha256"] != sha256(pub_b):
        problems.append("manifest names a different signing key")
    for name, digest in man["artifacts"].items():
        p = dist / name
        if not p.exists() or sha256(p.read_bytes()) != digest:
            problems.append(f"artifact hash mismatch: {name}")
    archive_name = next(n for n in man["artifacts"] if n.endswith(".tar.gz"))
    prov = json.loads((dist / "provenance.intoto.json").read_text())
    if prov["subject"][0]["digest"]["sha256"] != man["artifacts"][archive_name]:
        problems.append("provenance subject does not match archive")
    try:
        sbom = json.loads((dist / "sbom.cdx.json").read_text())
        if sbom["metadata"]["component"]["hashes"][0]["content"] != man["artifacts"][archive_name]:
            problems.append("SBOM does not describe archive")
    except (ValueError, KeyError, IndexError):
        problems.append("SBOM unparseable")
    # reproducibility: rebuild from the archive's own contents
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(dist / archive_name) as tar:
            try:
                tar.extractall(tmp, filter="data")
            except TypeError:  # Python without extraction filters
                for m in tar.getmembers():
                    if m.name.startswith(("/", "..")) or ".." in m.name.split("/") or not m.isfile():
                        raise ValueError(f"unsafe archive member {m.name}")
                tar.extractall(tmp)  # noqa: S202 - members validated above
        root = pathlib.Path(tmp) / "inv42_capability_descriptors"
        files = source_files(root)
        if sha256(build_archive(files, root)) != man["artifacts"][archive_name]:
            problems.append("archive is not reproducible")
        for f in files:
            if man["source_files"].get(f.as_posix()) != sha256((root / f).read_bytes()):
                problems.append(f"source hash mismatch {f}")
    if man["channel"] != "production-candidate":
        problems.append("dev-only channel: signed with an ephemeral key; not eligible for production")
    result = {"schema": "INV42_RELEASE_VERIFY/1", "ok": not [p for p in problems if not p.startswith("dev-only")],
              "production_eligible": not problems, "problems": problems, "archive_sha256": man["artifacts"][archive_name]}
    print(json.dumps(result, indent=1))
    (PKG / "evidence").mkdir(exist_ok=True)
    (PKG / "evidence" / "release_verify.json").write_text(json.dumps(result, indent=2) + "\n")
    return 0 if result["ok"] else 5


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("--out", default="dist"); b.add_argument("--key")
    v = sub.add_parser("verify"); v.add_argument("--dist", default="dist"); v.add_argument("--pubkey", required=True)
    a = ap.parse_args()
    return cmd_build(a) if a.cmd == "build" else cmd_verify(a)


if __name__ == "__main__":
    sys.exit(main())
