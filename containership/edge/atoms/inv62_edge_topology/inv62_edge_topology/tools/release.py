"""Release integrity tooling (MC-091, MC-094, MC-035).

    python inv62_edge_topology/tools/release.py build --out dist [--signing-key PEM] [--source-commit SHA]
    python inv62_edge_topology/tools/release.py verify --dir <unpacked inv62_edge_topology> [--pubkey PEM]
    python inv62_edge_topology/tools/release.py verify-zip --zip dist/<zip> --sums dist/SHA256SUMS

build produces a byte-reproducible zip (sorted entries, fixed timestamps from SOURCE_DATE_EPOCH, fixed modes)
that contains RELEASE_MANIFEST.json (per-file SHA-256 + tree digest) and RELEASE_MANIFEST.sig.json (Ed25519).
Without --signing-key an *ephemeral* key is generated and the signature is labelled NONPRODUCTION-EPHEMERAL;
the exit gate never accepts that label.  Also writes SHA256SUMS, sbom.cdx.json and provenance.intoto.json.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import platform
import sys
import zipfile

PKG = pathlib.Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {"evidence", "dist", "__pycache__", ".git", ".mypy_cache", ".ruff_cache"}
MANIFEST, SIG = "RELEASE_MANIFEST.json", "RELEASE_MANIFEST.sig.json"


def files(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(p for p in root.rglob("*") if p.is_file() and not (set(p.relative_to(root).parts) & EXCLUDE_DIRS)
                  and p.name not in (MANIFEST, SIG))


def manifest(root: pathlib.Path, version: str, commit: str) -> dict:
    entries = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files(root)}
    tree = hashlib.sha256("".join(f"{k}\0{v}\n" for k, v in sorted(entries.items())).encode()).hexdigest()
    return {"schema": "INV62_RELEASE_MANIFEST/1", "component": "INV-62", "version": version, "source_commit": commit,
            "tree_digest": tree, "files": entries}


def _ed25519():
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    except Exception:
        return None
    return serialization, Ed25519PrivateKey, Ed25519PublicKey


def sign(man_bytes: bytes, key_pem: pathlib.Path | None) -> dict:
    lib = _ed25519()
    if lib is None:
        return {"alg": "none", "label": "UNSIGNED", "reason": "cryptography not installed"}
    serialization, Priv, _ = lib
    if key_pem:
        key = serialization.load_pem_private_key(key_pem.read_bytes(), password=None)
        label = "PRODUCTION"
    else:
        key = Priv.generate()
        label = "NONPRODUCTION-EPHEMERAL"
    pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return {"alg": "Ed25519", "label": label, "public_key": base64.b64encode(pub).decode(),
            "manifest_sha256": hashlib.sha256(man_bytes).hexdigest(),
            "signature": base64.b64encode(key.sign(man_bytes)).decode()}


def verify_dir(root: pathlib.Path, pubkey: str | None = None) -> list[str]:
    problems = []
    man_path, sig_path = root / MANIFEST, root / SIG
    if not man_path.exists():
        return ["manifest missing"]
    man_bytes = man_path.read_bytes()
    man = json.loads(man_bytes)
    actual = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files(root)}
    for rel, digest in man["files"].items():
        if rel not in actual:
            problems.append(f"missing file {rel}")
        elif actual[rel] != digest:
            problems.append(f"digest mismatch {rel}")
    for rel in sorted(set(actual) - set(man["files"])):
        problems.append(f"unexpected file {rel}")
    tree = hashlib.sha256("".join(f"{k}\0{v}\n" for k, v in sorted(man["files"].items())).encode()).hexdigest()
    if tree != man["tree_digest"]:
        problems.append("tree digest mismatch")
    if not sig_path.exists():
        problems.append("signature missing")
        return problems
    sig = json.loads(sig_path.read_text())
    lib = _ed25519()
    if sig.get("alg") != "Ed25519" or lib is None:
        problems.append("signature unverifiable")
        return problems
    _, _, Pub = lib
    key_b64 = pubkey or sig["public_key"]
    try:
        Pub.from_public_bytes(base64.b64decode(key_b64)).verify(base64.b64decode(sig["signature"]), man_bytes)
    except Exception:
        problems.append("signature invalid")
    if pubkey is None and sig.get("label") != "PRODUCTION":
        problems.append(f"WARNING signature label {sig.get('label')} (not a trusted release key)")
    return problems


def sbom(version: str, zip_sha: str) -> dict:
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "library", "name": "inv62-edge-topology", "version": version,
                                       "hashes": [{"alg": "SHA-256", "content": zip_sha}]},
                         "tools": [{"name": "inv62 tools/release.py"}]},
            "components": [
                {"type": "framework", "name": "cpython", "version": platform.python_version(), "scope": "required",
                 "description": "runtime; stdlib only (json, hmac, hashlib, heapq, threading, re, secrets)"},
                {"type": "library", "name": "cryptography", "version": ">=42,<47", "scope": "optional",
                 "licenses": [{"expression": "Apache-2.0 OR BSD-3-Clause"}],
                 "description": "only for encrypt_at_rest and release signing; not bundled"}],
            "dependencies": [{"ref": "inv62-edge-topology", "dependsOn": ["cpython"]}]}


def build(out: pathlib.Path, key: pathlib.Path | None, commit: str) -> dict:
    version = (PKG / "VERSION").read_text().strip()
    out.mkdir(parents=True, exist_ok=True)
    man = manifest(PKG, version, commit)
    man_bytes = (json.dumps(man, indent=1, sort_keys=True) + "\n").encode()
    sig = sign(man_bytes, key)
    sig_bytes = (json.dumps(sig, indent=1, sort_keys=True) + "\n").encode()
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "1790121600"))  # 2026-09-23T00:00:00Z
    import time as _t
    stamp = _t.gmtime(max(epoch, 315532800))[:6]
    zpath = out / f"inv62_edge_topology_v{version}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        items = [(p.relative_to(PKG).as_posix(), p.read_bytes()) for p in files(PKG)] + [(MANIFEST, man_bytes), (SIG, sig_bytes)]
        for rel, data in sorted(items):
            info = zipfile.ZipInfo(f"inv62_edge_topology/{rel}", date_time=stamp)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    zsha = hashlib.sha256(zpath.read_bytes()).hexdigest()
    (out / "SHA256SUMS").write_text(f"{zsha}  {zpath.name}\n")
    (out / "sbom.cdx.json").write_text(json.dumps(sbom(version, zsha), indent=2) + "\n")
    prov = {"_type": "https://in-toto.io/Statement/v1",
            "subject": [{"name": zpath.name, "digest": {"sha256": zsha}}],
            "predicateType": "https://slsa.dev/provenance/v1",
            "predicate": {"buildDefinition": {"buildType": "inv62/tools/release.py@1",
                                              "externalParameters": {"version": version, "source_date_epoch": epoch},
                                              "resolvedDependencies": [{"uri": "source-tree", "digest": {"sha256": man["tree_digest"]},
                                                                        "annotations": {"source_commit": commit}}]},
                          "runDetails": {"builder": {"id": f"local:{platform.node() or 'unknown'}"},
                                         "metadata": {"python": platform.python_version(), "platform": platform.platform()}}}}
    (out / "provenance.intoto.json").write_text(json.dumps(prov, indent=2) + "\n")
    return {"zip": str(zpath), "sha256": zsha, "tree_digest": man["tree_digest"], "files": len(man["files"]), "signature": sig.get("label")}


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]
    arg = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
    if cmd == "build":
        key = arg("--signing-key")
        print(json.dumps(build(pathlib.Path(arg("--out", "dist")), pathlib.Path(key) if key else None,
                               arg("--source-commit", os.environ.get("INV62_SOURCE_COMMIT", "unknown"))), indent=2))
        return 0
    if cmd == "verify":
        problems = verify_dir(pathlib.Path(arg("--dir", str(PKG))), arg("--pubkey"))
        hard = [p for p in problems if not p.startswith("WARNING")]
        for p in problems:
            print(p)
        print("OK" if not hard else "FAILED")
        return 0 if not hard else 1
    if cmd == "verify-zip":
        z = pathlib.Path(arg("--zip"))
        want = dict(line.split()[::-1] for line in pathlib.Path(arg("--sums")).read_text().splitlines() if line.strip())
        ok = want.get(z.name) == hashlib.sha256(z.read_bytes()).hexdigest()
        print("OK" if ok else "FAILED: checksum mismatch")
        return 0 if ok else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
