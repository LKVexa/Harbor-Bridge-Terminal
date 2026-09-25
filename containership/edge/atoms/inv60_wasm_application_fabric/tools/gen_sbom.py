"""M04 - CycloneDX 1.5 SBOM for the release (files + declared deps; zero third-party runtime deps)."""
import hashlib, json, pathlib, sys, uuid
PKG = pathlib.Path(__file__).resolve().parents[1]
ver = (PKG / "VERSION").read_text().strip()
comps = []
for root, name in ((PKG, "inv60_wasm_application_fabric"), (PKG.parent / "pk_core", "pk_core")):
    for p in sorted(root.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        comps.append({"type": "file", "name": f"{name}/{p.relative_to(root).as_posix()}",
                      "hashes": [{"alg": "SHA-256", "content": hashlib.sha256(p.read_bytes()).hexdigest()}]})
bom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "serialNumber": "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, "inv60-" + ver)),
       "version": 1, "metadata": {"component": {"type": "library", "name": "inv60-wasm-application-fabric", "version": ver,
       "licenses": [{"license": {"name": "UNDECIDED (see LICENSE-DECISION.md)"}}]}},
       "components": comps + [{"type": "library", "name": "pk_core", "version": "owner-estate", "scope": "required",
                               "description": "vendored conformance runtime"}],
       "dependencies": [{"ref": "inv60-wasm-application-fabric", "dependsOn": ["pk_core"]}],
       "properties": [{"name": "inv60:third_party_runtime_dependencies", "value": "0"},
                      {"name": "inv60:vulnerability_scan", "value": "not-run: no advisory feed available offline (W-SUPPLY)"}]}
out = PKG / "release" / "sbom.cdx.json"; out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(bom, indent=1, sort_keys=True))
print(f"sbom: {len(comps)} files")
