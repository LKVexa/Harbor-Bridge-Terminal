"""MC-022 / MC-105 — reproducible release artifact, SBOM, provenance, signature.

Deterministic zip: sorted entries, fixed timestamps (SOURCE_DATE_EPOCH or 2026-01-01),
fixed permissions, no __pycache__/evidence scratch.  Emits alongside it:
  <name>.sbom.json         CycloneDX 1.5 (components: this package; stdlib-only runtime)
  <name>.provenance.json   SLSA-style statement: builder, inputs digests, source file digests
  <name>.sig               HMAC-SHA256 over the artifact digest when INV39_RELEASE_KEY is set;
                           absent otherwise -> the exit gate reports release signing BLOCKED.
Two builds of the same tree produce byte-identical artifacts (tested).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import pathlib
import platform
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {"__pycache__", "dist", ".git"}
EXCLUDE_FILES = {".DS_Store"}


def files(root: pathlib.Path):
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if p.is_file() and not (set(rel.parts) & EXCLUDE_DIRS) and p.name not in EXCLUDE_FILES \
                and not (rel.parts[0] == "evidence" and p.name.startswith("bench-")):
            yield p, rel


def build(out_dir: pathlib.Path, root: pathlib.Path = HERE) -> dict:
    version = (root / "VERSION").read_text().strip()
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "1767225600"))
    import time
    dt = time.gmtime(epoch)[:6]
    name = f"{root.name}-{version}"
    out_dir.mkdir(parents=True, exist_ok=True)
    art = out_dir / f"{name}.zip"
    digests = {}
    with zipfile.ZipFile(art, "w", zipfile.ZIP_DEFLATED) as z:
        for p, rel in files(root):
            data = p.read_bytes()
            digests[str(rel)] = hashlib.sha256(data).hexdigest()
            zi = zipfile.ZipInfo(f"{root.name}/{rel.as_posix()}", date_time=dt)
            zi.external_attr = (0o644 << 16)
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, data, compresslevel=9)
    ad = hashlib.sha256(art.read_bytes()).hexdigest()
    sbom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "library", "name": "inv39-process-sandbox-tier", "version": version,
                                       "hashes": [{"alg": "SHA-256", "content": ad}]}},
            "components": [], "dependencies": [{"ref": "inv39-process-sandbox-tier", "dependsOn": []}],
            "properties": [{"name": "runtime", "value": "python stdlib only"},
                           {"name": "optional", "value": "pk_core (internal, not bundled, unpinned: MC-021)"},
                           {"name": "build-tool", "value": "gcc (tests only: tools/escape_probes.c)"}]}
    prov = {"_type": "https://in-toto.io/Statement/v1",
            "subject": [{"name": art.name, "digest": {"sha256": ad}}],
            "predicateType": "https://slsa.dev/provenance/v1",
            "predicate": {"buildDefinition": {"buildType": "inv39/tools/build_release.py@1",
                                              "externalParameters": {"SOURCE_DATE_EPOCH": epoch},
                                              "resolvedDependencies": [{"uri": f"file:{k}", "digest": {"sha256": v}}
                                                                       for k, v in digests.items()]},
                          "runDetails": {"builder": {"id": f"local:{platform.node()}"},
                                         "metadata": {"python": platform.python_version()}}}}
    (out_dir / f"{name}.sbom.json").write_text(json.dumps(sbom, indent=1, sort_keys=True))
    (out_dir / f"{name}.provenance.json").write_text(json.dumps(prov, indent=1, sort_keys=True))
    key = os.environ.get("INV39_RELEASE_KEY", "").encode()
    signed = False
    sig = out_dir / f"{name}.sig"
    if len(key) >= 32:
        sig.write_text("hmac-sha256:" + hmac.new(key, ad.encode(), hashlib.sha256).hexdigest() + "\n")
        signed = True
    elif sig.exists():
        sig.unlink()
    return {"artifact": str(art), "sha256": ad, "files": len(digests), "signed": signed}


if __name__ == "__main__":
    print(json.dumps(build(pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "dist"), indent=1))
