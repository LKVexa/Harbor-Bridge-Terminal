"""MC-055 release evidence bundle (+ MC-046 artifact policy, MC-047 SBOM/lock).

    python tools/release.py --sbom-only   # SBOM, dependency lock, artifact policy + verify
    python tools/release.py               # seal evidence/RELEASE_EVIDENCE.json and MANIFEST.sha256

The bundle binds: version, per-file source digests and a tree digest, the
default configuration digest, mapping-profile digest, SBOM digest, every
evidence file digest, and each gate verdict from ``evidence/ci_run.json``.
It is content-addressed (sha256).  It is NOT cryptographically signed: signing
requires a release key / Sigstore identity that this environment does not hold
(recorded as a blocked control, not a pass).
"""
import argparse
import hashlib
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from canon import provenance  # noqa: E402
from canon.config import default_config, digest as cfg_digest  # noqa: E402
from canon.registry import PROFILE_DIGEST, PROFILE_ID, PROFILE_VERSION  # noqa: E402

EV = ROOT / "evidence"
EXCLUDE_DIRS = {"__pycache__", "target", "evidence", ".git"}
VERSION = (ROOT / "VERSION").read_text().strip()


def source_files():
    out = []
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if p.is_file() and not (set(rel.parts) & EXCLUDE_DIRS) and p.name != "MANIFEST.sha256" \
                and p.suffix not in (".pyc",):
            out.append(p)
    return out


def sha(p):
    return provenance.sha256_file(p)[7:]


PINNED = {  # artifacts that participate at run time / in conformance (MC-046)
    "binding.rust": "fixtures/rust/src/main.rs",
    "binding.go": "fixtures/go/main.go",
    "binding.javascript": "fixtures/js/inv12.mjs",
    "corpus.schema": "fixtures/corpus/corpus.wit",
    "corpus.vectors": "fixtures/corpus/vectors.json",
    "runtime.layout": "canon/layout.py",
    "runtime.memory": "canon/memory.py",
    "policy.registry": "canon/registry.py",
}


def sbom_only():
    EV.mkdir(exist_ok=True)
    provenance.write_json(EV / "sbom.cdx.json", provenance.sbom(ROOT, VERSION))
    provenance.write_json(EV / "deps.lock.json", provenance.dependency_lock(VERSION))
    policy = {name: {"version": VERSION, "digest": provenance.sha256_file(ROOT / rel)}
              for name, rel in PINNED.items()}
    provenance.write_json(EV / "artifact_policy.json", policy)
    pol = provenance.ArtifactPolicy(policy)
    verified = {name: pol.verify(name, VERSION, ROOT / rel) for name, rel in PINNED.items()}
    print(json.dumps({"sbom_components": len(json.loads((EV / "sbom.cdx.json").read_text())["components"]),
                      "verified_artifacts": len(verified)}))


def seal():
    files = source_files()
    manifest = "".join(f"{sha(p)}  {p.relative_to(ROOT).as_posix()}\n" for p in files)
    (ROOT / "MANIFEST.sha256").write_text(manifest)
    tree = hashlib.sha256(manifest.encode()).hexdigest()
    ci = json.loads((EV / "ci_run.json").read_text()) if (EV / "ci_run.json").exists() else {}
    evidence = {p.name: sha(p) for p in sorted(EV.glob("*.json")) if p.name != "RELEASE_EVIDENCE.json"}
    bundle = {
        "bundle": "inv12-release-evidence/1",
        "component": "INV-12 Language interoperability",
        "version": VERSION,
        "sealed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_tree_sha256": tree,
        "source_files": len(files),
        "mapping_profile": {"id": PROFILE_ID, "version": PROFILE_VERSION, "digest": PROFILE_DIGEST},
        "default_config_digest": cfg_digest(default_config()),
        "evidence": evidence,
        "gates": {r["gate"]: r["status"] for r in ci.get("results", [])},
        "ci_verdict": ci.get("verdict", "NOT_RUN"),
        "signature": {"status": "UNSIGNED", "reason": "no release signing identity available in this environment"},
    }
    body = json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode()
    bundle["bundle_sha256"] = hashlib.sha256(body).hexdigest()
    (EV / "RELEASE_EVIDENCE.json").write_text(json.dumps(bundle, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"tree": tree, "files": len(files), "ci_verdict": bundle["ci_verdict"],
                      "bundle_sha256": bundle["bundle_sha256"]}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sbom-only", action="store_true")
    a = ap.parse_args()
    sbom_only() if a.sbom_only else seal()
