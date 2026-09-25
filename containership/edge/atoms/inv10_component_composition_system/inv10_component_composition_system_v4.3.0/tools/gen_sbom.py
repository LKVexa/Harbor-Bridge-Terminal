"""MC-42: CycloneDX 1.5 SBOM + dependency/license inventory with per-file hashes."""
import hashlib, json, uuid
import _path  # noqa: F401
from _path import ROOT
from inv10_component_composition_system import __version__

PKG = ROOT / "inv10_component_composition_system"


def build():
    files = sorted(p for p in PKG.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, 'inv10-' + __version__)}", "version": 1,
        "metadata": {"component": {"type": "library", "name": "inv10-component-composition-system",
                                   "version": __version__,
                                   "licenses": [{"license": {"name": "UNDECLARED - owner decision pending"}}]}},
        "components": [
            {"type": "framework", "name": "python-stdlib", "version": ">=3.10,<3.14", "scope": "required",
             "licenses": [{"license": {"id": "PSF-2.0"}}]},
            {"type": "library", "name": "pk_core", "version": ">=1.0.0,<2.0.0", "scope": "optional",
             "description": "checklist adapter only; not bundled; license unknown",
             "licenses": [{"license": {"name": "UNKNOWN"}}]},
            {"type": "library", "name": "setuptools", "version": "75.8.0", "scope": "excluded",
             "description": "build-time only", "licenses": [{"license": {"id": "MIT"}}]},
            {"type": "library", "name": "wheel", "version": "0.45.1", "scope": "excluded",
             "description": "build-time only", "licenses": [{"license": {"id": "MIT"}}]},
        ],
        "properties": [{"name": "inv10:third-party-code-copied", "value": "none"}],
        "files": [{"path": str(p.relative_to(ROOT)).replace("\\", "/"),
                   "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],
    }


if __name__ == "__main__":
    (ROOT / "sbom.cdx.json").write_text(json.dumps(build(), indent=1) + "\n")
    print("wrote sbom.cdx.json")
