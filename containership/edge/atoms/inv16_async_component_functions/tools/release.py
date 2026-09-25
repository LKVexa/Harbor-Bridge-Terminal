"""Reproducible release builder + SBOM + provenance + checksums + signing hook (closures #29, #30, #36).

    python tools/release.py build  [--out dist]      # wheel + sdist + SBOM + provenance + SHA256SUMS
    python tools/release.py verify [--out dist]      # recompute digests, rebuild and compare bytes
    python tools/release.py sign   --key <ed25519.pem>   # openssl Ed25519 signature over SHA256SUMS
    python tools/release.py verify --pub <ed25519.pub.pem> # also checks SHA256SUMS.sig

The wheel is assembled directly (stdlib zipfile) rather than via a build
backend so that byte-for-byte reproducibility does not depend on the host's
setuptools/wheel versions.  All timestamps come from SOURCE_DATE_EPOCH
(default: the release date below); entries are sorted; permissions fixed.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tarfile
import zipfile

PKG = pathlib.Path(__file__).resolve().parents[1]
NAME = "inv16_async_component_functions"
DIST_NAME = "inv16-async-component-functions"
RELEASE_EPOCH = 1790121600          # 2026-09-23T00:00:00Z
WHEEL_FILES = ["__init__.py", "runtime.py", "bridge.py", "abi.py", "declare.py", "lowering.py", "observability.py",
               "preflight.py", "component.py", "contract.py", "VERSION", "CHECKLIST.json",
               "fixtures/__init__.py", "fixtures/inv15.py", "fixtures/composition.py", "fixtures/streams.py",
               "fixtures/http.py", "fixtures/interfaces/demo.pkif", "fixtures/interfaces/bad_duplicate.pkif",
               "fixtures/golden_demo_descriptor.json", "compat/__init__.py", "compat/runtime_4_2_0.py"]
SDIST_EXCLUDE = {"__pycache__", "dist", "evidence", ".git", "build"}


def version() -> str:
    return (PKG / "VERSION").read_text().strip()


def epoch() -> int:
    return int(os.environ.get("SOURCE_DATE_EPOCH", RELEASE_EPOCH))


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _zinfo(name: str) -> zipfile.ZipInfo:
    import time
    zi = zipfile.ZipInfo(name, time.gmtime(max(epoch(), 315532800))[:6])
    zi.external_attr = 0o644 << 16
    zi.compress_type = zipfile.ZIP_DEFLATED
    return zi


def build_wheel(out: pathlib.Path) -> pathlib.Path:
    v = version()
    di = f"{NAME}-{v}.dist-info"
    files: list[tuple[str, bytes]] = [(f"{NAME}/{p}", (PKG / p).read_bytes()) for p in WHEEL_FILES]
    meta = (f"Metadata-Version: 2.1\nName: {DIST_NAME}\nVersion: {v}\nRequires-Python: >=3.10,<3.14\n"
            f"Author: David Paul Russell\nLicense: LicenseRef-Proprietary\n"
            f"Summary: INV-16 async component functions\n").encode()
    files += [(f"{di}/METADATA", meta),
              (f"{di}/WHEEL", b"Wheel-Version: 1.0\nGenerator: inv16-tools-release\nRoot-Is-Purelib: true\n"
                              b"Tag: py3-none-any\n"),
              (f"{di}/LICENSE", (PKG / "LICENSE").read_bytes()),
              (f"{di}/NOTICE", (PKG / "NOTICE").read_bytes()),
              (f"{di}/top_level.txt", f"{NAME}\n".encode())]
    record = io.StringIO()
    for n, b in sorted(files):
        h = base64.urlsafe_b64encode(hashlib.sha256(b).digest()).rstrip(b"=").decode()
        record.write(f"{n},sha256={h},{len(b)}\n")
    record.write(f"{di}/RECORD,,\n")
    files.append((f"{di}/RECORD", record.getvalue().encode()))
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{NAME}-{v}-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as z:
        for n, b in sorted(files):
            z.writestr(_zinfo(n), b)
    return path


def source_files() -> list[pathlib.Path]:
    out = []
    for p in sorted(PKG.rglob("*")):
        rel = p.relative_to(PKG)
        if p.is_file() and not (set(rel.parts) & SDIST_EXCLUDE) and p.suffix not in (".pyc",):
            out.append(rel)
    return out


def build_sdist(out: pathlib.Path) -> pathlib.Path:
    v = version()
    root = f"{DIST_NAME}-{v}"
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tf:
        for rel in source_files():
            data = (PKG / rel).read_bytes()
            ti = tarfile.TarInfo(f"{root}/{rel.as_posix()}")
            ti.size, ti.mtime, ti.mode, ti.uid, ti.gid, ti.uname, ti.gname = len(data), epoch(), 0o644, 0, 0, "", ""
            tf.addfile(ti, io.BytesIO(data))
    path = out / f"{DIST_NAME}-{v}.tar.gz"
    with open(path, "wb") as fh, gzip.GzipFile(filename="", mode="wb", fileobj=fh, mtime=epoch()) as gz:
        gz.write(buf.getvalue())
    return path


def source_digest() -> str:
    h = hashlib.sha256()
    for rel in source_files():
        h.update(rel.as_posix().encode() + b"\0" + hashlib.sha256((PKG / rel).read_bytes()).digest())
    return h.hexdigest()


def sbom(wheel: pathlib.Path) -> dict:
    v = version()
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "serialNumber": "urn:uuid:" + sha256(f"inv16-{v}-{source_digest()}".encode())[:32],
        "metadata": {"timestamp": "2026-09-23T00:00:00Z",
                     "component": {"type": "library", "name": DIST_NAME, "version": v,
                                   "hashes": [{"alg": "SHA-256", "content": sha256(wheel.read_bytes())}],
                                   "licenses": [{"license": {"name": "LicenseRef-Proprietary"}}]},
                     "properties": [{"name": "runtime-dependencies", "value": "none (CPython stdlib only)"},
                                    {"name": "python-requires", "value": ">=3.10,<3.14"}]},
        "components": [
            {"type": "library", "name": "pk_core", "version": "UNRESOLVED",
             "scope": "optional", "description": "certification framework; required only for the 100-item gate; "
                                                  "not bundled and not pinned (closure #1 BLOCKED)"},
        ],
        "dependencies": [{"ref": DIST_NAME, "dependsOn": []}],
    }


def provenance(artifacts: list[pathlib.Path]) -> dict:
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": a.name, "digest": {"sha256": sha256(a.read_bytes())}} for a in artifacts],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": "https://linearfinance.org/inv16/release/v1",
                "externalParameters": {"command": "python tools/release.py build", "SOURCE_DATE_EPOCH": epoch()},
                "internalParameters": {"python": sys.version.split()[0]},
                "resolvedDependencies": [{"uri": "source-tree", "digest": {"sha256": source_digest()}}],
            },
            "runDetails": {"builder": {"id": "local:tools/release.py (unattested local builder; SLSA L1)"},
                           "metadata": {"invocationId": sha256(f"{source_digest()}{epoch()}".encode())[:16]}},
        },
    }


def build(out: pathlib.Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    whl, sd = build_wheel(out), build_sdist(out)
    (out / "sbom.cdx.json").write_text(json.dumps(sbom(whl), indent=2, sort_keys=True) + "\n")
    arts = [whl, sd, out / "sbom.cdx.json"]
    (out / "provenance.intoto.json").write_text(json.dumps(provenance(arts), indent=2, sort_keys=True) + "\n")
    arts.append(out / "provenance.intoto.json")
    sums = "".join(f"{sha256(a.read_bytes())}  {a.name}\n" for a in sorted(arts))
    (out / "SHA256SUMS").write_text(sums)
    return {"artifacts": [a.name for a in arts], "sha256sums": sums, "source_digest": source_digest()}


def verify(out: pathlib.Path, pub: str | None = None) -> dict:
    problems = []
    for line in (out / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        if sha256((out / name).read_bytes()) != digest:
            problems.append(f"digest mismatch: {name}")
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        again = build(pathlib.Path(d))
        if again["sha256sums"] != (out / "SHA256SUMS").read_text():
            problems.append("rebuild is not byte-identical")
    sig = out / "SHA256SUMS.sig"
    signed = sig.exists()
    sig_ok = None
    if signed and pub:
        r = subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", pub, "-rawin",
                            "-in", str(out / "SHA256SUMS"), "-sigfile", str(sig)], capture_output=True)
        sig_ok = r.returncode == 0
        if not sig_ok:
            problems.append("signature verification failed")
    return {"ok": not problems, "problems": problems, "signed": signed, "signature_verified": sig_ok,
            "reproducible": "rebuild is not byte-identical" not in problems}


def sign(out: pathlib.Path, key: str) -> None:
    subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", key, "-rawin", "-in", str(out / "SHA256SUMS"),
                    "-out", str(out / "SHA256SUMS.sig")], check=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "verify", "sign"])
    ap.add_argument("--out", default=str(PKG / "dist"))
    ap.add_argument("--key")
    ap.add_argument("--pub")
    a = ap.parse_args(argv)
    out = pathlib.Path(a.out)
    if a.cmd == "build":
        print(json.dumps(build(out), indent=2))
        return 0
    if a.cmd == "sign":
        if not a.key:
            print("sign requires --key (owner-controlled release key)", file=sys.stderr)
            return 2
        sign(out, a.key)
        return 0
    r = verify(out, a.pub)
    print(json.dumps(r, indent=2))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
