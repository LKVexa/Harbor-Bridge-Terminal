"""C045: SBOM (CycloneDX 1.5 JSON), per-file digests and an in-toto v1 provenance statement.
The statement is UNSIGNED: no release key is available to this build (waiver WVR-003).
``--verify`` recomputes every digest against evidence/sbom.cdx.json."""
import hashlib, json, platform, sys, time, uuid
from _tools_pkg import ROOT

SKIP = {"__pycache__", "evidence", "results", ".git", "conformance", "traceability"}  # generated outputs


def files():
    for p in sorted(ROOT.rglob("*")):
        if p.is_file() and not (set(p.relative_to(ROOT).parts) & SKIP) and p.suffix != ".pyc":
            yield p


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def build():
    version = (ROOT / "VERSION").read_text().strip()
    comps = [{"type": "file", "name": str(p.relative_to(ROOT)), "hashes": [{"alg": "SHA-256", "content": sha(p)}]} for p in files()]
    pk = sorted((ROOT / "vendor" / "pk_core").glob("*.py"))
    pk_digest = hashlib.sha256(b"".join(p.read_bytes() for p in pk)).hexdigest()
    bom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "serialNumber": f"urn:uuid:{uuid.uuid4()}", "version": 1,
           "metadata": {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "component": {"type": "library", "name": "inv17-streaming-primitive", "version": version}},
           "components": [{"type": "library", "name": "pk_core", "version": "4.0.0", "scope": "optional",
                           "description": "vendored conformance framework (owner's PK estate)",
                           "hashes": [{"alg": "SHA-256", "content": pk_digest}]},
                          {"type": "platform", "name": "python", "version": ">=3.10", "description": "stdlib only; no third-party runtime deps"}] + comps}
    tree = hashlib.sha256("".join(c["hashes"][0]["content"] + c["name"] for c in comps).encode()).hexdigest()
    stmt = {"_type": "https://in-toto.io/Statement/v1",
            "subject": [{"name": f"inv17-streaming-primitive-{version}", "digest": {"sha256": tree}}],
            "predicateType": "https://slsa.dev/provenance/v1",
            "predicate": {"buildDefinition": {"buildType": "urn:pk:inv17:local-build:1", "externalParameters": {"version": version},
                                              "resolvedDependencies": [{"name": "pk_core", "digest": {"sha256": pk_digest}}]},
                          "runDetails": {"builder": {"id": f"local:{platform.node() or 'unknown'}"}}},
            "signature": None, "signature_status": "UNSIGNED -- release signing key not available (WVR-003)"}
    return bom, stmt


if __name__ == "__main__":
    ev = ROOT / "evidence"; ev.mkdir(exist_ok=True)
    if "--verify" in sys.argv:
        bom = json.loads((ev / "sbom.cdx.json").read_text()); bad = []
        for c in bom["components"]:
            if c["type"] == "file":
                p = ROOT / c["name"]
                if not p.exists() or sha(p) != c["hashes"][0]["content"]:
                    bad.append(c["name"])
        print(json.dumps({"verified": not bad, "mismatches": bad[:20]})); sys.exit(1 if bad else 0)
    bom, stmt = build()
    (ev / "sbom.cdx.json").write_text(json.dumps(bom, indent=1) + "\n")
    (ev / "provenance.intoto.json").write_text(json.dumps(stmt, indent=2) + "\n")
    print(json.dumps({"files": len(bom["components"]) - 2, "subject": stmt["subject"][0]["digest"]["sha256"][:16], "signed": False}))
