"""Reproducible source artifact + manifest + SBOM (MC-001, MC-032, MC-033, MC-071).

Builds ``dist/inv34_legacy_cpu_expansion_path-<ver>.tar.gz`` twice with fixed
mtimes/owners/ordering and gzip mtime 0, and requires both digests to match.
Signing is NOT performed: no signing key is bound to this package (BLOCKED).
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import platform
import sys
import tarfile

from _common import PKG, source_digest, source_files, write_json

EPOCH = 1_788_000_000   # fixed SOURCE_DATE_EPOCH for reproducibility


def build_once() -> bytes:
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tf:
        for p in source_files():
            data = p.read_bytes()
            ti = tarfile.TarInfo(f"inv34_legacy_cpu_expansion_path/{p.relative_to(PKG).as_posix()}")
            ti.size, ti.mtime, ti.uid, ti.gid, ti.uname, ti.gname = len(data), EPOCH, 0, 0, "", ""
            ti.mode = 0o644
            tf.addfile(ti, io.BytesIO(data))
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb", mtime=0) as gz:
        gz.write(raw.getvalue())
    return out.getvalue()


def sbom(version: str, artifact_sha: str) -> dict:
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "library", "name": "inv34-legacy-cpu-expansion-path",
                                       "version": version, "hashes": [{"alg": "SHA-256", "content": artifact_sha}],
                                       "licenses": [{"expression": "NOASSERTION"}]},
                         "properties": [{"name": "inv34:license_status", "value": "UNDECLARED — rights holder has not chosen a licence (MC-074)"}]},
            "components": [
                {"type": "library", "name": "pk_core", "version": "UNRESOLVED", "scope": "optional",
                 "properties": [{"name": "inv34:status", "value": "not supplied; certification gate fails closed"}]}],
            "dependencies": [],
            "properties": [{"name": "inv34:runtime_third_party_imports", "value": "0 (stdlib only)"},
                           {"name": "inv34:python", "value": ">=3.10"},
                           {"name": "inv34:pattern_sources", "value": "cloud-hypervisor OpenAPI 0.3.0 (Apache-2.0 AND BSD-3-Clause), pattern only, no code copied"}]}


def main() -> int:
    version = (PKG / "VERSION").read_text().strip()
    a, b = build_once(), build_once()
    da, db = hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest()
    (PKG.parent / "dist").mkdir(exist_ok=True)
    name = f"inv34_legacy_cpu_expansion_path-{version}.tar.gz"
    (PKG.parent / "dist" / name).write_bytes(a)
    manifest = "\n".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(PKG).as_posix()}"
                         for p in source_files()) + "\n"
    (PKG / "governance/MANIFEST.sha256").write_text(manifest)
    write_json("governance/SBOM.cdx.json", sbom(version, da))
    result = {"schema": "INV34_BUILD/1", "version": version, "artifact": name, "sha256": da,
              "reproducible": da == db, "source_digest": source_digest(), "files": len(source_files()),
              "builder": {"python": platform.python_version(), "implementation": platform.python_implementation()},
              "signature": "NOT_SIGNED (no signing key bound — MC-032 BLOCKED)"}
    write_json("governance/BUILD_RESULT.json", result)
    print(json.dumps(result, indent=1))
    return 0 if da == db else 1


if __name__ == "__main__":
    sys.exit(main())
