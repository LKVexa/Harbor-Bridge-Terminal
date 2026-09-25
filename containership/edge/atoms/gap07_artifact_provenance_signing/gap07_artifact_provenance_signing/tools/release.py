"""Release tooling: manifest, SBOM, evidence bundle, signing and self-verification (#38, #39, #48).

  python tools/release.py manifest            # rewrite MANIFEST.sha256 over the package
  python tools/release.py sbom                # write SBOM.cdx.json (CycloneDX 1.5) for runtime deps
  python tools/release.py evidence [--bench]  # run gates -> RELEASE_EVIDENCE.json
  python tools/release.py sign --key-pem K    # sign RELEASE_EVIDENCE+MANIFEST (offline ceremony key / KMS export of signature)
  python tools/release.py verify --pub-spki P # verify a GAP-07 release before self-update (bootstrap policy)

The self-update bootstrap rule: a GAP-07 node only installs a new GAP-07
release whose RELEASE.sig verifies under the *pinned* release-authority SPKI
shipped with the currently running version (ops/release-authority.spki.b64),
and whose evidence bundle reports every gate passed.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import time

import _path  # noqa: F401

from gap07_artifact_provenance_signing import __version__
from gap07_artifact_provenance_signing import algorithms as algs
from gap07_artifact_provenance_signing.canonical import canonical_bytes, ld_encode

PKG = _path.ROOT
PARENT = os.path.dirname(PKG)
SKIP_DIRS = {"__pycache__", ".pytest_cache"}
SKIP_FILES = {"MANIFEST.sha256", "RELEASE.sig"}


def files():
    for base, dirs, fs in os.walk(PKG):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for f in sorted(fs):
            if f in SKIP_FILES or f.endswith((".pyc", ".tmp")):
                continue
            yield os.path.relpath(os.path.join(base, f), PKG).replace(os.sep, "/")


def manifest():
    lines = []
    for rel in files():
        with open(os.path.join(PKG, rel), "rb") as fh:
            lines.append(f"{hashlib.sha256(fh.read()).hexdigest()}  {rel}")
    with open(os.path.join(PKG, "MANIFEST.sha256"), "w", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    return len(lines)


def sbom():
    import importlib.metadata as md
    comps = []
    for dist in ("cryptography", "cffi", "pycparser"):
        try:
            v = md.version(dist)
            lic = md.metadata(dist).get("License-Expression") or md.metadata(dist).get("License") or ""
        except md.PackageNotFoundError:
            continue
        comps.append({"type": "library", "name": dist, "version": v, "purl": f"pkg:pypi/{dist}@{v}",
                      "licenses": [{"expression": lic.split("\n")[0][:120]}] if lic else []})
    doc = {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
           "metadata": {"component": {"type": "library", "name": "gap07_artifact_provenance_signing", "version": __version__}},
           "components": comps}
    with open(os.path.join(PKG, "SBOM.cdx.json"), "w") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")
    return doc


def run(cmd):
    t = time.time()
    p = subprocess.run(cmd, cwd=PARENT, capture_output=True, text=True)
    tail = (p.stdout + p.stderr).strip().splitlines()[-3:]
    return {"cmd": " ".join(cmd), "rc": p.returncode, "seconds": round(time.time() - t, 2), "tail": tail}


def evidence(bench: bool):
    gates = {
        "unit_normal": run([sys.executable, "-m", "unittest", "discover", "-s", "gap07_artifact_provenance_signing/tests", "-p", "test_*.py"]),
        "unit_optimized": run([sys.executable, "-O", "-m", "unittest", "discover", "-s", "gap07_artifact_provenance_signing/tests", "-p", "test_*.py"]),
        "fuzz_extended": run([sys.executable, "-m", "unittest", "gap07_artifact_provenance_signing.tests.test_v6_assurance.Fuzz"]),
        "compile": run([sys.executable, "-m", "compileall", "-q", "gap07_artifact_provenance_signing"]),
    }
    audit = run([sys.executable, "-m", "pip_audit", "--version"])
    gates["dependency_scan"] = run([sys.executable, "-m", "pip_audit", "-r", "gap07_artifact_provenance_signing/requirements.txt"]) if audit["rc"] == 0 else \
        {"cmd": "pip-audit", "rc": None, "tail": ["pip-audit not installed in this environment - CI runs it (ci/github-workflow.yml)"]}
    if bench:
        gates["benchmark"] = run([sys.executable, "gap07_artifact_provenance_signing/tools/benchmark.py", "--n", "200"])
    n = manifest()
    with open(os.path.join(PKG, "MANIFEST.sha256"), "rb") as fh:
        man_digest = hashlib.sha256(fh.read()).hexdigest()
    sb = sbom()
    doc = {"schema": "PK_RELEASE_EVIDENCE/1", "component": "GAP-07", "version": __version__, "generated_at": int(time.time()),
           "python": sys.version.split()[0], "manifest_sha256": man_digest, "manifest_files": n,
           "sbom_sha256": hashlib.sha256(canonical_bytes(sb)).hexdigest(), "algorithms": algs.registry_document(), "gates": gates,
           "all_required_passed": all(g.get("rc") == 0 for k, g in gates.items() if k != "dependency_scan")}
    with open(os.path.join(PKG, "RELEASE_EVIDENCE.json"), "w") as fh:
        json.dump(doc, fh, indent=2, default=str)
        fh.write("\n")
    manifest()  # include evidence file in manifest
    return doc


def _release_message():
    with open(os.path.join(PKG, "MANIFEST.sha256"), "rb") as fh:
        man = fh.read()
    return ld_encode("release/1", [("component", "GAP-07"), ("version", __version__), ("manifest_sha256", hashlib.sha256(man).hexdigest())])


def sign(key_pem: str):
    from cryptography.hazmat.primitives import serialization
    with open(key_pem, "rb") as fh:
        key = serialization.load_pem_private_key(fh.read(), password=None)
    sig = algs.software_signer("ed25519", key)(_release_message())
    doc = {"schema": "PK_RELEASE_SIGNATURE/1", "alg": "ed25519", "version": __version__, "spki": base64.b64encode(algs.spki(key.public_key())).decode(),
           "sig": base64.b64encode(sig).decode()}
    with open(os.path.join(PKG, "RELEASE.sig"), "w") as fh:
        json.dump(doc, fh, indent=2)
    return doc


def verify(pub_spki_b64_path: str):
    with open(pub_spki_b64_path) as fh:
        pinned = base64.b64decode(fh.read().strip())
    with open(os.path.join(PKG, "RELEASE.sig")) as fh:
        doc = json.load(fh)
    if base64.b64decode(doc["spki"]) != pinned:
        raise SystemExit("RELEASE.sig was produced by a key other than the pinned release authority")
    for line in open(os.path.join(PKG, "MANIFEST.sha256")):
        dg, rel = line.rstrip("\n").split("  ", 1)
        with open(os.path.join(PKG, rel), "rb") as fh:
            if hashlib.sha256(fh.read()).hexdigest() != dg:
                raise SystemExit(f"manifest mismatch: {rel}")
    algs.verify_raw("ed25519", pinned, base64.b64decode(doc["sig"]), _release_message())
    with open(os.path.join(PKG, "RELEASE_EVIDENCE.json")) as fh:
        ev = json.load(fh)
    if not ev.get("all_required_passed"):
        raise SystemExit("release evidence reports failed gates")
    print(json.dumps({"verified": True, "version": doc["version"]}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("manifest")
    sub.add_parser("sbom")
    e = sub.add_parser("evidence")
    e.add_argument("--bench", action="store_true")
    s = sub.add_parser("sign")
    s.add_argument("--key-pem", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--pub-spki", required=True)
    a = ap.parse_args()
    if a.cmd == "manifest":
        print(manifest())
    elif a.cmd == "sbom":
        print(json.dumps(sbom(), indent=2))
    elif a.cmd == "evidence":
        print(json.dumps({k: v for k, v in evidence(a.bench).items() if k != "algorithms"}, indent=2, default=str))
    elif a.cmd == "sign":
        print(json.dumps(sign(a.key_pem), indent=2))
    else:
        verify(a.pub_spki)
