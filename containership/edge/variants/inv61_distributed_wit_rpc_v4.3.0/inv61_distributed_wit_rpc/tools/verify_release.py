"""Verify a release directory: checksums, SBOM/provenance subject digests,
and that the manifest's source digests match the tree (M30 / C045)."""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def verify(dist: pathlib.Path, check_sources: bool = True) -> list[str]:
    errs = []
    sums = {}
    for line in (dist / "SHA256SUMS").read_text().splitlines():
        h, name = line.split("  ", 1)
        sums[name] = h
        if not (dist / name).exists() or sha(dist / name) != h:
            errs.append(f"checksum mismatch: {name}")
    man = json.loads((dist / "release-manifest.json").read_text())
    wheel = dist / man["wheel"]["file"]
    if sha(wheel) != man["wheel"]["sha256"]:
        errs.append("manifest wheel digest mismatch")
    prov = json.loads((dist / "provenance.intoto.json").read_text())
    if prov["subject"][0]["digest"]["sha256"] != man["wheel"]["sha256"]:
        errs.append("provenance subject mismatch")
    sbom = json.loads((dist / "sbom.cdx.json").read_text())
    if sbom["metadata"]["component"]["hashes"][0]["content"] != man["wheel"]["sha256"]:
        errs.append("sbom hash mismatch")
    if check_sources:
        for rel, h in man["sources"].items():
            p = PKG / rel
            if not p.exists() or sha(p) != h:
                errs.append(f"source drift: {rel}")
    return errs


if __name__ == "__main__":
    d = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else PKG / "dist")
    e = verify(d)
    print("\n".join(e) or "release verified")
    sys.exit(1 if e else 0)
