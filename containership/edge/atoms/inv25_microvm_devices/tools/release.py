"""Deterministic source archive, release manifest and CycloneDX SBOM (items 4 and 28D).

    python tools/release.py build [--dist dist]    # builds twice, asserts byte-identical, writes manifest + SBOM
"""
from __future__ import annotations

import argparse, gzip, hashlib, io, json, os, pathlib, platform, subprocess, sys, tarfile

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))
from gate import git_commit, source_files, source_tree_digest  # noqa: E402

EXTRA = ["README.md", "CHANGELOG.md", "AUDIT_REPORT.md", "SECURITY.md", "SUPPORT.md", "CODEOWNERS",
         "requirements.lock", "THIRD-PARTY-NOTICES.md"]


def release_files():
    fs = set(source_files())
    for pat in EXTRA + ["docs/*.md", "ADR/*.md", "governance/*", ".github/workflows/*.yml"]:
        for p in PKG.glob(pat):
            if p.is_file():
                fs.add(p.relative_to(PKG).as_posix())
    return sorted(fs)


def build_archive(version: str) -> bytes:
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tf:
        for rel in release_files():
            data = (PKG / rel).read_bytes().replace(b"\r\n", b"\n")
            ti = tarfile.TarInfo(f"inv25_microvm_devices-{version}/{rel}")
            ti.size, ti.mtime, ti.mode, ti.uid, ti.gid, ti.uname, ti.gname = len(data), 0, 0o644, 0, 0, "", ""
            tf.addfile(ti, io.BytesIO(data))
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb", mtime=0, compresslevel=9) as gz:
        gz.write(raw.getvalue())
    return out.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build"])
    ap.add_argument("--dist", default=str(PKG / "dist"))
    a = ap.parse_args()
    version = (PKG / "VERSION").read_text().strip()
    init = (PKG / "__init__.py").read_text()
    pyproj = (PKG / "pyproject.toml").read_text()
    errs = []
    if f'__version__ = "{version}"' not in init:
        errs.append("__init__.__version__ != VERSION")
    if f'version = "{version}"' not in pyproj:
        errs.append("pyproject version != VERSION")
    for rel in release_files():
        if rel.endswith((".py", ".json", ".md", ".toml")):
            t = (PKG / rel).read_text(errors="replace")
            for needle in ("/home/", "C:\\Users\\", "/Users/"):
                if needle in t and rel not in ("tools/release.py",):
                    errs.append(f"developer-local path in {rel}")
    a1, a2 = build_archive(version), build_archive(version)
    if a1 != a2:
        errs.append("archive build is not reproducible")
    dist = pathlib.Path(a.dist)
    dist.mkdir(parents=True, exist_ok=True)
    name = f"inv25_microvm_devices-{version}.tar.gz"
    (dist / name).write_bytes(a1)
    adig = "sha256:" + hashlib.sha256(a1).hexdigest()
    sbom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "library", "name": "inv25-microvm-devices", "version": version,
                                       "hashes": [{"alg": "SHA-256", "content": adig[7:]}],
                                       "licenses": [{"license": {"name": "PENDING - no licence chosen"}}]}},
            "components": [
                {"type": "framework", "name": "CPython standard library", "version": platform.python_version(),
                 "scope": "required"},
                {"type": "library", "name": "pk_core", "version": ">=4.0,<5.0 (PROPOSED)", "scope": "optional",
                 "description": "not distributed; source and digest PENDING (W-0006)"},
                {"type": "library", "name": "setuptools", "version": "75.8.0", "scope": "excluded",
                 "description": "build backend only"}]}
    (dist / "sbom.cdx.json").write_text(json.dumps(sbom, indent=1, sort_keys=True) + "\n")
    manifest = {"schema": "INV25_RELEASE_MANIFEST/1", "version": version, "git_commit": git_commit(),
                "source_tree": source_tree_digest(), "archive": {"name": name, "sha256": adig,
                                                                "reproducible": a1 == a2},
                "python": {"implementation": platform.python_implementation(), "version": platform.python_version()},
                "platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
                "dependencies": {"runtime": [], "optional": {"pk_core": ">=4.0,<5.0 (PROPOSED, unverified)"},
                                 "build": {"setuptools": "75.8.0"}},
                "checklist_sha256": "sha256:" + hashlib.sha256((PKG / "CHECKLIST.json").read_bytes()).hexdigest(),
                "master_md": "absent - classified archival-only pending approval (docs/master-corpus.md)",
                "schemas": {p.name: "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sorted((PKG / "schemas").glob("*.json"))},
                "sbom": {"path": "sbom.cdx.json",
                         "sha256": "sha256:" + hashlib.sha256((dist / "sbom.cdx.json").read_bytes()).hexdigest()},
                "provenance": {"builder": os.environ.get("INV25_BUILDER", "local"),
                               "attestation": "PENDING organisational signing (W-0005)"},
                "files": {rel: "sha256:" + hashlib.sha256((PKG / rel).read_bytes()).hexdigest()
                          for rel in release_files()},
                "errors": errs}
    (dist / "release-manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"archive": name, "sha256": adig, "reproducible": a1 == a2, "errors": errs}, indent=1))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
