"""Component 36 - reproducible release build, digest manifest, signature and
provenance.

    python tools/build_release.py --out dist --source-revision <git sha> --key-file release.key

Reproducibility: files are sorted, timestamps fixed to 1980-01-01, permissions
normalised, caches excluded, so the same tree always yields the same ZIP
digest. Provenance (``*.provenance.json``) records the source revision, file
digests, builder, and an HMAC-SHA256 signature by a ``release.sign`` key.
Production should replace HMAC with Sigstore/cosign or an HSM-backed
asymmetric signature behind the same verify() contract (ADR-0004).
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import pathlib
import platform
import zipfile

EXCLUDE_DIRS = {"__pycache__", ".git", "dist", ".pytest_cache", "evidence_runs"}
EPOCH = (1980, 1, 1, 0, 0, 0)


def _files(root: pathlib.Path):
    for p in sorted(root.rglob("*")):
        if p.is_file() and not (set(p.relative_to(root).parts) & EXCLUDE_DIRS) and not p.name.endswith((".pyc", ".tmp")):
            yield p


def build(root, out_dir, *, signing_key: bytes, source_revision: str) -> dict:
    root, out = pathlib.Path(root).resolve(), pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    version = (root / "VERSION").read_text().strip()
    name = f"{root.name}-{version}.zip"
    zpath = out / name
    manifest = {}
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in _files(root):
            rel = f"{root.name}/{p.relative_to(root).as_posix()}"
            data = p.read_bytes()
            manifest[rel] = hashlib.sha256(data).hexdigest()
            zi = zipfile.ZipInfo(rel, EPOCH)
            zi.external_attr = 0o644 << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, data)
    digest = hashlib.sha256(zpath.read_bytes()).hexdigest()
    statement = {"_type": "gap10.provenance/v1", "subject": {"name": name, "sha256": digest},
                 "source_revision": source_revision, "version": version,
                 "builder": {"python": platform.python_version(), "tool": "tools/build_release.py"},
                 "files": manifest}
    body = json.dumps(statement, sort_keys=True, separators=(",", ":")).encode()
    signed = {"statement": statement, "signature": hmac.new(signing_key, body, hashlib.sha256).hexdigest(),
              "signature_alg": "HMAC-SHA256"}
    ppath = out / f"{name}.provenance.json"
    ppath.write_text(json.dumps(signed, indent=2, sort_keys=True))
    (out / f"{name}.sha256").write_text(f"{digest}  {name}\n")
    return {"zip": str(zpath), "sha256": digest, "provenance": str(ppath)}


def verify(zip_path, provenance_path, key: bytes) -> bool:
    doc = json.loads(pathlib.Path(provenance_path).read_text())
    body = json.dumps(doc["statement"], sort_keys=True, separators=(",", ":")).encode()
    if not hmac.compare_digest(hmac.new(key, body, hashlib.sha256).hexdigest(), doc["signature"]):
        return False
    return hashlib.sha256(pathlib.Path(zip_path).read_bytes()).hexdigest() == doc["statement"]["subject"]["sha256"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist")
    ap.add_argument("--source-revision", required=True)
    ap.add_argument("--key-file", required=True)
    a = ap.parse_args()
    key = pathlib.Path(a.key_file).read_bytes()
    print(json.dumps(build(pathlib.Path(__file__).resolve().parents[1], a.out, signing_key=key,
                           source_revision=a.source_revision), indent=2))
