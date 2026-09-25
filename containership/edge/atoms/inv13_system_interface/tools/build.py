"""MC-025/MC-026 -- deterministic package build, manifest, SBOM, provenance.

    python -m inv13_system_interface.tools.build --out dist/

Produces ``inv13_system_interface-4.3.0.zip`` with sorted entries, fixed
timestamps (SOURCE_DATE_EPOCH or 2026-09-22T00:00:00Z), fixed permissions and
no bytecode/evidence; building twice yields identical bytes (checked by the
gate).  Also writes MANIFEST.sha256, SBOM.cdx.json (CycloneDX 1.5) and an
in-toto v1 provenance statement (unsigned -- signing is an external KMS step).
"""
from __future__ import annotations

import hashlib, json, os, sys, zipfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
VERSION = (PKG / "VERSION").read_text().strip()
EPOCH = int(os.environ.get("SOURCE_DATE_EPOCH", "1789948800"))  # 2026-09-22T00:00:00Z
EXCLUDE_DIRS = {"__pycache__", "evidence", "dist", ".git"}
EXCLUDE_FILES = {"MANIFEST.sha256", "SBOM.cdx.json", "PROVENANCE.intoto.json"}


def files() -> list[Path]:
    out = []
    for p in sorted(PKG.rglob("*")):
        rel = p.relative_to(PKG)
        if p.is_file() and not (set(rel.parts) & EXCLUDE_DIRS) and p.suffix not in (".pyc",) \
                and rel.as_posix() not in EXCLUDE_FILES:
            out.append(p)
    return out


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def manifest() -> str:
    return "".join(f"{sha(p)}  {p.relative_to(PKG).as_posix()}\n" for p in files())


def build_zip(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    z = out_dir / f"inv13_system_interface-{VERSION}.zip"
    import time
    dt = time.gmtime(EPOCH)[:6]
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in files() + [PKG / n for n in sorted(EXCLUDE_FILES) if (PKG / n).exists()]:
            info = zipfile.ZipInfo(f"inv13_system_interface/{p.relative_to(PKG).as_posix()}", date_time=dt)
            info.external_attr = (0o644 << 16)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            zf.writestr(info, p.read_bytes(), compresslevel=9)
    return z


def sbom() -> dict:
    comps = [{"type": "library", "name": "python-stdlib", "version": ">=3.10", "scope": "required",
              "description": "Only runtime dependency of the host layer"},
             {"type": "application", "name": "node", "version": ">=18", "scope": "optional",
              "description": "V8 WebAssembly engine used by host/runtime_adapter.py (not vendored)"},
             {"type": "library", "name": "pk_core", "version": "unpinned", "scope": "optional",
              "description": "External assessment framework (not vendored; version pin OPEN, see MC-025)"}]
    for p in files():
        comps.append({"type": "file", "name": p.relative_to(PKG).as_posix(),
                      "hashes": [{"alg": "SHA-256", "content": sha(p)}]})
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"timestamp": "2026-09-22T00:00:00Z",
                         "component": {"type": "library", "name": "inv13-system-interface", "version": VERSION}},
            "components": comps}


def provenance(zip_path: Path) -> dict:
    return {"_type": "https://in-toto.io/Statement/v1",
            "subject": [{"name": zip_path.name, "digest": {"sha256": sha(zip_path)}}],
            "predicateType": "https://slsa.dev/provenance/v1",
            "predicate": {"buildDefinition": {"buildType": "inv13/tools/build.py@1",
                                              "externalParameters": {"SOURCE_DATE_EPOCH": EPOCH},
                                              "resolvedDependencies": [{"name": "python", "version": sys.version.split()[0]}]},
                          "runDetails": {"builder": {"id": "UNSIGNED-LOCAL-BUILD"},
                                         "metadata": {"note": "unsigned; release signing via org KMS is an open MC-025 item"}}}}


if __name__ == "__main__":
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else PKG / "dist"
    (PKG / "SBOM.cdx.json").write_text(json.dumps(sbom(), indent=2) + "\n")
    (PKG / "MANIFEST.sha256").write_text(manifest())
    z1 = build_zip(out)
    d1 = sha(z1)
    z2 = build_zip(out / "rebuild")
    d2 = sha(z2)
    (PKG / "PROVENANCE.intoto.json").write_text(json.dumps(provenance(z1), indent=2) + "\n")
    z1 = build_zip(out)   # include provenance-less manifest set deterministically
    print(json.dumps({"zip": str(z1), "sha256": d1, "reproducible": d1 == d2}))
    sys.exit(0 if d1 == d2 else 1)
