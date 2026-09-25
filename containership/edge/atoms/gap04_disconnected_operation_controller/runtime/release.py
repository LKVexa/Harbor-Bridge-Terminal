"""Packaging, SBOM, provenance, signing and release verification (GAP04-C45, C46).

  python -m gap04_disconnected_operation_controller.runtime.release build <out_dir> [--key <seed.hex>]
  python -m gap04_disconnected_operation_controller.runtime.release verify <out_dir> <pubkey_b64url>

``build`` produces a reproducible zip (sorted entries, fixed timestamps, no
bytecode), MANIFEST.sha256, a CycloneDX 1.5 SBOM, an in-toto/SLSA v1
provenance statement, SHA256SUMS, and an Ed25519 detached signature over
SHA256SUMS. ``verify`` re-checks every digest, the signature, the SBOM's
declared component digest and the provenance subject, and exits non-zero on
any mismatch.
"""
from __future__ import annotations

import hashlib
import io
import json
import platform
import sys
import zipfile
from pathlib import Path

from . import crypto

PKG = Path(__file__).resolve().parents[1]
NAME = "gap04_disconnected_operation_controller"
EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", "evidence_runs"}
FIXED_TS = (2026, 9, 22, 0, 0, 0)
LOCK = {"cryptography": "46.0.7", "cffi": "2.0.0", "pycparser": "3.00"}


def _version() -> str:
    return (PKG / "VERSION").read_text().strip()


def package_files() -> list[Path]:
    out = []
    for p in sorted(PKG.rglob("*")):
        if p.is_file() and not (set(p.relative_to(PKG).parts) & EXCLUDE_DIRS) and p.suffix != ".pyc" \
                and p.name not in ("MANIFEST.sha256",):
            out.append(p)
    return out


def write_manifest() -> str:
    lines = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(PKG).as_posix()}" for p in package_files()]
    (PKG / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")
    return hashlib.sha256((PKG / "MANIFEST.sha256").read_bytes()).hexdigest()


def reproducible_zip() -> bytes:
    buf = io.BytesIO()
    files = package_files() + [PKG / "MANIFEST.sha256"]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(set(files)):
            zi = zipfile.ZipInfo(f"{NAME}/{p.relative_to(PKG).as_posix()}", FIXED_TS)
            zi.external_attr = 0o644 << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, p.read_bytes())
    return buf.getvalue()


def sbom(archive_sha: str) -> dict:
    comps = [{"type": "library", "name": k, "version": v, "purl": f"pkg:pypi/{k}@{v}", "scope": "required" if k == "cryptography" else "required"}
             for k, v in LOCK.items()]
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "application", "name": NAME, "version": _version(),
                                       "hashes": [{"alg": "SHA-256", "content": archive_sha}]},
                         "tools": [{"name": "gap04-release", "version": _version()}]},
            "components": comps + [{"type": "platform", "name": "cpython", "version": ">=3.10"}],
            "dependencies": [{"ref": NAME, "dependsOn": [f"pkg:pypi/{k}@{v}" for k, v in LOCK.items()]}]}


def provenance(archive_name: str, archive_sha: str, manifest_sha: str) -> dict:
    return {"_type": "https://in-toto.io/Statement/v1",
            "subject": [{"name": archive_name, "digest": {"sha256": archive_sha}}],
            "predicateType": "https://slsa.dev/provenance/v1",
            "predicate": {"buildDefinition": {"buildType": "https://linearfinance.org/gap04/release/v1",
                                              "externalParameters": {"version": _version()},
                                              "resolvedDependencies": [{"name": "MANIFEST.sha256", "digest": {"sha256": manifest_sha}}]},
                          "runDetails": {"builder": {"id": "local:gap04-release"},
                                         "metadata": {"python": platform.python_version(), "platform": platform.platform()}}}}


def build(out: Path, seed: bytes | None = None) -> dict:
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    manifest_sha = write_manifest()
    blob = reproducible_zip()
    name = f"{NAME}_v{_version()}.zip"
    (out / name).write_bytes(blob)
    sha = hashlib.sha256(blob).hexdigest()
    (out / "sbom.cdx.json").write_text(json.dumps(sbom(sha), indent=2, sort_keys=True))
    (out / "provenance.intoto.json").write_text(json.dumps(provenance(name, sha, manifest_sha), indent=2, sort_keys=True))
    sums = "".join(f"{hashlib.sha256((out / f).read_bytes()).hexdigest()}  {f}\n"
                   for f in sorted([name, "sbom.cdx.json", "provenance.intoto.json"]))
    (out / "SHA256SUMS").write_text(sums)
    if seed is None:
        seed, pub = crypto.generate_signing_key()
    else:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        pub = crypto.b64e(Ed25519PrivateKey.from_private_bytes(seed).public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw))
    (out / "SHA256SUMS.sig").write_text(crypto.sign(seed, sums.encode()))
    (out / "release-signing-key.pub").write_text(pub)
    return {"archive": name, "sha256": sha, "manifest_sha256": manifest_sha, "pubkey": pub}


def verify(out: Path, pub: str) -> dict:
    out = Path(out)
    sums = (out / "SHA256SUMS").read_text()
    if not crypto.verify(pub, sums.encode(), (out / "SHA256SUMS.sig").read_text().strip()):
        raise SystemExit("signature INVALID")
    got = {}
    for line in sums.splitlines():
        h, f = line.split("  ", 1)
        if hashlib.sha256((out / f).read_bytes()).hexdigest() != h:
            raise SystemExit(f"digest mismatch: {f}")
        got[f] = h
    archive = next(f for f in got if f.endswith(".zip"))
    sb = json.loads((out / "sbom.cdx.json").read_text())
    if sb["metadata"]["component"]["hashes"][0]["content"] != got[archive]:
        raise SystemExit("SBOM component digest mismatch")
    pv = json.loads((out / "provenance.intoto.json").read_text())
    if pv["subject"][0]["digest"]["sha256"] != got[archive]:
        raise SystemExit("provenance subject mismatch")
    with zipfile.ZipFile(out / archive) as z:
        man = z.read(f"{NAME}/MANIFEST.sha256").decode()
        for line in man.splitlines():
            h, f = line.split("  ", 1)
            if hashlib.sha256(z.read(f"{NAME}/{f}")).hexdigest() != h:
                raise SystemExit(f"archive member mismatch: {f}")
    return {"verified": True, "archive": archive, "sha256": got[archive]}


if __name__ == "__main__":  # pragma: no cover
    cmd = sys.argv[1]
    if cmd == "build":
        seed = bytes.fromhex(Path(sys.argv[sys.argv.index("--key") + 1]).read_text().strip()) if "--key" in sys.argv else None
        print(json.dumps(build(Path(sys.argv[2]), seed), indent=2))
    else:
        print(json.dumps(verify(Path(sys.argv[2]), sys.argv[3]), indent=2))
