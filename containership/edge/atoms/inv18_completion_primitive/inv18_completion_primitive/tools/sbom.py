"""Generate conformance/SBOM.json (CycloneDX-shaped, stdlib only) (C045)."""
import hashlib, json, pathlib, sys
pkg = pathlib.Path(__file__).resolve().parents[1]
version = (pkg / "VERSION").read_text().strip()
lock = json.loads((pkg / "requirements.lock.json").read_text())
files = sorted(p for p in pkg.glob("*.py"))
sbom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "metadata": {"component": {"type": "library", "name": "inv18-completion-primitive", "version": version}},
        "components": [{"type": "library", "name": d["name"], "version": d.get("version"), "scope": d.get("scope", "required"),
                        "licenses": [{"license": {"name": d.get("license", "unknown")}}],
                        "hashes": ([{"alg": "SHA-256", "content": d["sha256"]}] if d.get("sha256") else []),
                        "properties": [{"name": "inv18:status", "value": d.get("status", "ok")}]} for d in lock["dependencies"]]
        + [{"type": "file", "name": p.name, "hashes": [{"alg": "SHA-256", "content": hashlib.sha256(p.read_bytes()).hexdigest()}]} for p in files]}
out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pkg / "conformance/SBOM.json"
out.write_text(json.dumps(sbom, indent=1))
print("SBOM:", len(sbom["components"]), "components")
