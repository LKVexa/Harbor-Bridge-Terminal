"""Build a reproducible release (M30/M31): wheel, SHA256SUMS, CycloneDX SBOM,
SLSA-style provenance statement and a release manifest.

    python tools/make_release.py [--out dist]

SOURCE_DATE_EPOCH is pinned so the wheel is byte-reproducible.  Signing is
NOT performed (no signing identity in scope, W-011); the provenance is an
unsigned in-toto statement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import time

PKG = pathlib.Path(__file__).resolve().parents[1]
EPOCH = "1790035200"  # 2026-09-22T00:00:00Z
EXCLUDE_DIRS = {"dist", "build", "__pycache__", ".git", "evidence"}


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sources() -> list[pathlib.Path]:
    out = []
    for p in sorted(PKG.rglob("*")):
        if p.is_file() and not (set(p.relative_to(PKG).parts) & EXCLUDE_DIRS) and not p.name.endswith((".pyc", ".egg-info")) \
                and ".egg-info" not in str(p):
            out.append(p)
    return out


NAME, DIST = "inv61_distributed_wit_rpc", "inv61_distributed_wit_rpc"
DATA = ["VERSION", "CHECKLIST.json", "COMPAT_MATRIX.json", "TRACEABILITY.json", "wit/kv.wit"]


def build_wheel(out: pathlib.Path) -> pathlib.Path:
    """Stdlib-only PEP 427 wheel builder: byte-reproducible (fixed timestamps,
    sorted entries, fixed permissions) and independent of setuptools/pip."""
    import base64, zipfile
    version = (PKG / "VERSION").read_text().strip()
    files = sorted(p.name for p in PKG.glob("*.py")) + DATA
    di = f"{DIST}-{version}.dist-info"
    meta = (f"Metadata-Version: 2.1\nName: inv61-distributed-wit-rpc\nVersion: {version}\n"
            "Summary: INV-61 Distributed WIT RPC: authenticated, typed, cross-host WIT invocation (stdlib only)\n"
            "Requires-Python: >=3.10\nLicense: UNSPECIFIED\nProvides-Extra: gate\n"
            "Requires-Dist: pk_core==4.0.*; extra == \"gate\"\n\n" + (PKG / "README.md").read_text())
    wheel_txt = "Wheel-Version: 1.0\nGenerator: inv61-make_release\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
    eps = ("[console_scripts]\ninv61-node = inv61_distributed_wit_rpc.demo_node:main\n"
           "inv61-selfcheck = inv61_distributed_wit_rpc.selfcheck:main\n")
    entries = [(f"{NAME}/{f}", (PKG / f).read_bytes()) for f in files]
    entries += [(f"{di}/METADATA", meta.encode()), (f"{di}/WHEEL", wheel_txt.encode()),
                (f"{di}/entry_points.txt", eps.encode())]
    rec = []
    for n, b in entries:
        d = base64.urlsafe_b64encode(hashlib.sha256(b).digest()).rstrip(b"=").decode()
        rec.append(f"{n},sha256={d},{len(b)}")
    rec.append(f"{di}/RECORD,,")
    entries.append((f"{di}/RECORD", ("\n".join(rec) + "\n").encode()))
    path = out / f"{DIST}-{version}-py3-none-any.whl"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in entries:
            zi = zipfile.ZipInfo(n, date_time=(2026, 9, 22, 0, 0, 0))
            zi.external_attr = 0o644 << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, b)
    return path


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(PKG / "dist"))
    out = pathlib.Path(ap.parse_args().out)
    shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True)
    for junk in PKG.glob("*.egg-info"):
        shutil.rmtree(junk)
    shutil.rmtree(PKG / "build", ignore_errors=True)
    wheel = build_wheel(out)
    version = (PKG / "VERSION").read_text().strip()
    srcs = sources()
    sbom = {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "metadata": {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(EPOCH))),
                     "component": {"type": "library", "name": "inv61-distributed-wit-rpc", "version": version,
                                   "hashes": [{"alg": "SHA-256", "content": sha(wheel)}],
                                   "licenses": [{"license": {"name": "UNSPECIFIED"}}]}},
        "components": [
            {"type": "platform", "name": "cpython", "version": ">=3.10", "scope": "required",
             "description": "Runtime; stdlib only (ssl links the host OpenSSL)"},
            {"type": "library", "name": "pk_core", "version": "4.0.*", "scope": "optional",
             "description": "gate extra; artifact and hash not supplied (W-002)"},
        ],
        "dependencies": [{"ref": "inv61-distributed-wit-rpc", "dependsOn": []}],
    }
    (out / "sbom.cdx.json").write_text(json.dumps(sbom, indent=2) + "\n")
    manifest = {"schema": "inv61-release/1", "name": "inv61-distributed-wit-rpc", "version": version,
                "wheel": {"file": wheel.name, "sha256": sha(wheel)},
                "checklist_sha256": sha(PKG / "CHECKLIST.json"),
                "traceability_sha256": sha(PKG / "TRACEABILITY.json"),
                "interface_wit_sha256": sha(PKG / "wit" / "kv.wit"),
                "sources": {str(p.relative_to(PKG)): sha(p) for p in srcs}}
    (out / "release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    prov = {"_type": "https://in-toto.io/Statement/v1",
            "subject": [{"name": wheel.name, "digest": {"sha256": sha(wheel)}}],
            "predicateType": "https://slsa.dev/provenance/v1",
            "predicate": {"buildDefinition": {
                "buildType": "inv61/tools/make_release.py@1",
                "externalParameters": {"SOURCE_DATE_EPOCH": EPOCH},
                "resolvedDependencies": [{"name": k, "digest": {"sha256": v}} for k, v in manifest["sources"].items()]},
                "runDetails": {"builder": {"id": f"local:{platform.node() or 'builder'}"},
                               "metadata": {"python": platform.python_version(), "platform": platform.platform(),
                                            "signed": False}}}}
    (out / "provenance.intoto.json").write_text(json.dumps(prov, indent=2) + "\n")
    lines = [f"{sha(p)}  {p.name}" for p in sorted(out.iterdir()) if p.name != "SHA256SUMS"]
    (out / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    print(json.dumps({"wheel": wheel.name, "sha256": sha(wheel)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
