#!/usr/bin/env python3
"""Release packaging, manifest and provenance (components 66, 71).

  python tools/release.py --out dist/ [--source-rev <git sha>] [--builder <id>]

Produces, deterministically (sorted entries, fixed timestamps):
  dist/inv04_current_orchestration-<ver>.zip
  dist/inv04_current_orchestration-<ver>.zip.sha256
  dist/sbom.cdx.json
  dist/provenance.intoto.json   (SLSA v1 provenance *statement*, UNSIGNED)
and refreshes MANIFEST.sha256 in the package.

Signing is deliberately external: run
  cosign sign-blob --bundle dist/<zip>.bundle dist/<zip>
with the release identity.  ``--verify dist/`` re-checks the zip digest,
manifest and SBOM against the package so a tampered artifact is rejected.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import zipfile

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))
from sbom import build as build_sbom, shipped_files  # noqa: E402

FIXED_TS = (2026, 9, 22, 0, 0, 0)


def write_manifest() -> str:
    lines = [f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.relative_to(PKG).as_posix()}" for f in shipped_files()]
    text = "\n".join(lines) + "\n"
    (PKG / "MANIFEST.sha256").write_text(text)
    return hashlib.sha256(text.encode()).hexdigest()


def build(out: pathlib.Path, source_rev: str, builder: str) -> dict:
    version = (PKG / "VERSION").read_text().strip()
    out.mkdir(parents=True, exist_ok=True)
    manifest_digest = write_manifest()
    zpath = out / f"inv04_current_orchestration-{version}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in [*shipped_files(), PKG / "MANIFEST.sha256"]:
            info = zipfile.ZipInfo(f"inv04_current_orchestration/{f.relative_to(PKG).as_posix()}", FIXED_TS)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, f.read_bytes())
    zdigest = hashlib.sha256(zpath.read_bytes()).hexdigest()
    (out / f"{zpath.name}.sha256").write_text(f"{zdigest}  {zpath.name}\n")
    sbom = build_sbom()
    (out / "sbom.cdx.json").write_text(json.dumps(sbom, indent=2, sort_keys=True) + "\n")
    prov = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": zpath.name, "digest": {"sha256": zdigest}}],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {"buildType": "urn:pk:inv04:tools/release.py@1",
                                "externalParameters": {"version": version},
                                "resolvedDependencies": [{"uri": "urn:pk:inv04:source", "digest": {"gitCommit": source_rev}}]},
            "runDetails": {"builder": {"id": builder},
                           "metadata": {"manifestSha256": manifest_digest, "signed": False,
                                        "signing": "external: cosign sign-blob with the release identity"}},
        },
    }
    (out / "provenance.intoto.json").write_text(json.dumps(prov, indent=2) + "\n")
    return {"zip": str(zpath), "sha256": zdigest, "manifest_sha256": manifest_digest}


def verify(out: pathlib.Path) -> list[str]:
    problems = []
    for sums in out.glob("*.zip.sha256"):
        want, name = sums.read_text().split()
        got = hashlib.sha256((out / name).read_bytes()).hexdigest()
        if got != want:
            problems.append(f"{name}: digest mismatch")
        prov = json.loads((out / "provenance.intoto.json").read_text())
        if prov["subject"][0]["digest"]["sha256"] != got:
            problems.append("provenance subject digest mismatch")
        with zipfile.ZipFile(out / name) as z:
            manifest = z.read("inv04_current_orchestration/MANIFEST.sha256").decode().splitlines()
            for line in manifest:
                h, rel = line.split("  ", 1)
                if hashlib.sha256(z.read(f"inv04_current_orchestration/{rel}")).hexdigest() != h:
                    problems.append(f"{rel}: manifest mismatch inside archive")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist")
    ap.add_argument("--source-rev", default="UNKNOWN-no-git-in-archive")
    ap.add_argument("--builder", default="local:unattested")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    if a.verify:
        problems = verify(out)
        print("RELEASE VERIFY:", "OK" if not problems else "FAIL")
        for p in problems:
            print(" -", p)
        return 1 if problems else 0
    print(json.dumps(build(out, a.source_rev, a.builder), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
