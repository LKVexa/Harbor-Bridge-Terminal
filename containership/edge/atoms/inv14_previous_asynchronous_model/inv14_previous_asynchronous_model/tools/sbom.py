"""SBOM + provenance + dependency scan (component P2-28; C045, C094).

Writes, deterministically from the tree:
  sbom/inv14.cdx.json        CycloneDX 1.5 -- the package, every shipped file (sha256),
                             and every third-party import found (expected: none)
  sbom/provenance.intoto.json in-toto Statement v1 / SLSA provenance v1 predicate,
                             UNSIGNED (a builder identity must sign it -- see sign.py)
  sbom/dependency_scan.json   stdlib-only proof: every import in shipped .py files
                             resolved against sys.stdlib_module_names + local modules;
                             pk_core recorded as an UNRESOLVED declared dependency
Vulnerability policy: with zero third-party runtime dependencies there is nothing
to match; pk_core cannot be scanned until pinned, so the scan result is
INDETERMINATE for it, which the release gate treats as not-passing.
"""
import ast, hashlib, json, pathlib, sys
import _path  # noqa

PKG = _path.PKG
EXCL = {"MANIFEST.sha256", "MANIFEST.sha256.sig.json"}
OUT = PKG / "sbom"


def files():
    for p in sorted(PKG.rglob("*")):
        rel = p.relative_to(PKG).as_posix()
        if p.is_file() and "__pycache__" not in p.parts and not rel.startswith(("sbom/", "evidence/")) and rel not in EXCL and p.suffix != ".pyc":
            yield rel, p


def imports():
    local = {p.stem for p in PKG.glob("*.py")} | {p.stem for p in (PKG / "tools").glob("*.py")} | {p.stem for p in (PKG / "tests").glob("*.py")}
    local |= {"pk_core", PKG.name}
    std = set(sys.stdlib_module_names)
    third, found = {}, set()
    for rel, p in files():
        if p.suffix != ".py":
            continue
        for node in ast.walk(ast.parse(p.read_text())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                    [node.module] if isinstance(node, ast.ImportFrom) and node.module and node.level == 0 else []
            for n in names:
                top = n.split(".")[0]; found.add(top)
                if top not in std and top not in local:
                    third.setdefault(top, []).append(rel)
    return sorted(found), third


def main():
    OUT.mkdir(exist_ok=True)
    comps = [{"type": "file", "name": rel, "hashes": [{"alg": "SHA-256", "content": hashlib.sha256(p.read_bytes()).hexdigest()}]}
             for rel, p in files()]
    found, third = imports()
    optional = {"cryptography": "optional signing backend (tools/sign.py); openssl CLI fallback"}
    runtime_third = {k: v for k, v in third.items() if k not in optional}
    sbom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "library", "name": "inv14_previous_asynchronous_model", "version": "4.3.0"}},
            "components": comps + [{"type": "library", "name": "pk_core", "version": "UNRESOLVED", "scope": "required",
                                    "description": "framework core; not pinned (deps/pk_core.lock.json)"}]
            + [{"type": "library", "name": k, "scope": "optional", "description": v} for k, v in optional.items() if k in third]}
    digest = hashlib.sha256(json.dumps(comps, sort_keys=True).encode()).hexdigest()
    prov = {"_type": "https://in-toto.io/Statement/v1",
            "subject": [{"name": "inv14_previous_asynchronous_model-4.3.0", "digest": {"sha256": digest}}],
            "predicateType": "https://slsa.dev/provenance/v1",
            "predicate": {"buildDefinition": {"buildType": "inv14/release-zip/v1", "externalParameters": {"version": "4.3.0"},
                                              "resolvedDependencies": []},
                          "runDetails": {"builder": {"id": "UNSIGNED:local-build"}, "metadata": {"note": "unsigned; not a trusted builder attestation"}}}}
    scan = {"schema": "PK_POLL_DEP_SCAN/1", "imports_found": found, "third_party_runtime": runtime_third,
            "third_party_optional": {k: third[k] for k in optional if k in third},
            "stdlib_only_runtime": not runtime_third, "pk_core": "UNRESOLVED -> vulnerability/license scan INDETERMINATE",
            "vulnerability_policy": "block release on any unwaived critical/high finding; INDETERMINATE is not a pass"}
    for n, d in (("inv14.cdx.json", sbom), ("provenance.intoto.json", prov), ("dependency_scan.json", scan)):
        (OUT / n).write_text(json.dumps(d, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"files": len(comps), "stdlib_only_runtime": scan["stdlib_only_runtime"], "third_party": sorted(third)}))
    return 0 if scan["stdlib_only_runtime"] else 1


if __name__ == "__main__":
    sys.exit(main())
