"""Release metadata (components 46, 65): MANIFEST.sha256, SBOM, provenance.

Writes an UNSIGNED provenance statement. Signing requires a key held by an
accountable person; none exists here, so ``signature`` is null and the
statement says so. Sorted, timestamp-free outputs (reproducible)."""
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKIP = {"MANIFEST.sha256", "certification/provenance.json", "certification/sbom.cdx.json"}


def files():
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT).as_posix()
        if p.is_file() and "__pycache__" not in rel and not rel.endswith(".pyc") and rel not in SKIP:
            yield rel, hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    fl = list(files())
    (ROOT / "MANIFEST.sha256").write_text("".join(f"{d}  ./{r}\n" for r, d in fl))
    ver = (ROOT / "VERSION").read_text().strip()
    sbom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "library", "name": "inv15-new-asynchronous-abi", "version": ver}},
            "components": [], "dependencies": [],
            "note": "stdlib-only: zero third-party runtime or build dependencies (checked by tests/test_ops.py)"}
    (ROOT / "certification" / "sbom.cdx.json").write_text(json.dumps(sbom, indent=1, sort_keys=True) + "\n")
    tree = hashlib.sha256("".join(f"{r}:{d}\n" for r, d in fl).encode()).hexdigest()
    prov = {"_type": "https://in-toto.io/Statement/v1", "predicateType": "https://slsa.dev/provenance/v1",
            "subject": [{"name": "inv15_new_asynchronous_abi", "digest": {"sha256-tree": tree}}],
            "predicate": {"buildDefinition": {"buildType": "tools/release.py", "externalParameters": {"version": ver}},
                          "runDetails": {"builder": {"id": "unattested: cloud session build"}}},
            "signature": None, "status": "UNSIGNED - no signing key or accountable signer bound"}
    (ROOT / "certification" / "provenance.json").write_text(json.dumps(prov, indent=1, sort_keys=True) + "\n")
    print(f"manifest {len(fl)} files, tree {tree[:16]}")


if __name__ == "__main__":
    main()
