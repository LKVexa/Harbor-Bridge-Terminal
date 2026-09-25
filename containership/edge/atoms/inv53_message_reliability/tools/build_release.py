"""Reproducible source release + SBOM (components 21, 32, 89, 91).

Builds ``inv53_message_reliability-<version>.tar.gz`` with sorted members, fixed
mtime/uid/gid/mode and gzip mtime 0, so two builds of the same tree are
byte-identical.  Writes a CycloneDX-1.5-shaped SBOM that lists the runtime
dependency set (the Python standard library only) and the pinned ``pk_core``
conformance dependency with its content digest.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
from inv53_message_reliability.gate import EXCLUDE_DIRS, source_digest  # noqa: E402

EPOCH = 1_700_000_000


def members(root: Path) -> list[Path]:
    out = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if p.is_file() and not any(x in EXCLUDE_DIRS or x.endswith(".egg-info") for x in rel.parts) \
                and p.suffix not in (".pyc", ".pyo"):
            out.append(p)
    return out


def build(out_dir: Path) -> dict:
    version = (PKG / "VERSION").read_text().strip()
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for p in members(PKG):
            data = p.read_bytes()
            ti = tarfile.TarInfo(f"inv53_message_reliability-{version}/inv53_message_reliability/{p.relative_to(PKG).as_posix()}")
            ti.size, ti.mtime, ti.mode, ti.uid, ti.gid, ti.uname, ti.gname = len(data), EPOCH, 0o644, 0, 0, "", ""
            tar.addfile(ti, io.BytesIO(data))
    gz = io.BytesIO()
    with gzip.GzipFile(fileobj=gz, mode="wb", mtime=0, filename="") as g:
        g.write(buf.getvalue())
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"inv53_message_reliability-{version}.tar.gz"
    (out_dir / name).write_bytes(gz.getvalue())
    lock = json.loads((PKG / "requirements" / "pk_core.lock.json").read_text())
    sbom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "library", "name": "inv53_message_reliability", "version": version,
                                       "hashes": [{"alg": "SHA-256", "content": hashlib.sha256(gz.getvalue()).hexdigest()}]}},
            "components": [
                {"type": "library", "name": "python-stdlib", "version": ">=3.10", "scope": "required",
                 "description": "Runtime uses only the CPython standard library."},
                {"type": "library", "name": "pk_core", "version": lock["version"], "scope": "optional",
                 "description": "Post-Kubernetes conformance framework; test-time only.",
                 "hashes": [{"alg": "SHA-256", "content": lock["content_sha256"]}]}]}
    (out_dir / "SBOM.cdx.json").write_text(json.dumps(sbom, indent=1, sort_keys=True) + "\n")
    return {"artifact": name, "sha256": hashlib.sha256(gz.getvalue()).hexdigest(),
            "members": len(members(PKG)), "source_digest": source_digest(PKG)}


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else PKG.parent / "dist"
    sys.stdout.write(json.dumps(build(out), indent=1) + "\n")
