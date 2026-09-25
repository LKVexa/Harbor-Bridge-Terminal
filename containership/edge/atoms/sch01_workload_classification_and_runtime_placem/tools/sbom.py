"""MC-60: CycloneDX-shaped SBOM from an import scan + checksum manifest.  Licence NOASSERTION."""
from _common import PKG, dump, files, sha
import ast, json, sys
STDLIB = set(sys.stdlib_module_names)

def imports():
    mods = set()
    for p in PKG.glob("*.py"):
        for n in ast.walk(ast.parse(p.read_text())):
            if isinstance(n, ast.Import): mods |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module: mods.add(n.module.split(".")[0])
    return sorted(mods - STDLIB - {"__future__"})

if __name__ == "__main__":
    third = imports()
    doc = {"bomFormat": "CycloneDX", "specVersion": "1.5", "metadata": {"component": {
        "type": "library", "name": "sch01-workload-classification-and-runtime-placement",
        "version": (PKG / "VERSION").read_text().strip(), "licenses": [{"expression": "NOASSERTION"}]}},
        "components": [{"type": "library", "name": m, "scope": "optional" if m == "pk_core" else "required",
                        "note": "external, not bundled"} for m in third]}
    dump(PKG / "sbom/sbom.cdx.json", doc)
    (PKG / "RELEASE_SHA256SUMS.txt").write_text("".join(f"{sha(p)}  ./{p.relative_to(PKG).as_posix()}\n" for p in files()))
    print(json.dumps({"third_party_imports": third})); sys.exit(0 if set(third) <= {"pk_core"} else 1)
