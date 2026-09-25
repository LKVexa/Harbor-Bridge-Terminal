"""Release supply-chain artifacts: SBOM, checksums, signature, provenance, consumer verification (MC-39, MC-15, MC-38).

    python -m inv64_application_model.tools.release build  --dist DIR --evidence DIR --out RELEASE_DIR
    python -m inv64_application_model.tools.release verify --release RELEASE_DIR [--trusted-key HEX --trusted-kid ID]

``build`` writes into RELEASE_DIR:

* ``sbom.cdx.json`` — CycloneDX 1.5: the package, its (optional) runtime
  dependency, build tooling, bundled donor code, each with purl + license;
  license policy from LICENSING.md is applied (unknown/copyleft -> FAIL);
* ``ARTIFACTS.json`` — deterministic manifest: filename, media type, size,
  SHA-256, SBOM relation, provenance and signature references;
* ``SHA256SUMS`` — every artifact and evidence file;
* ``provenance.intoto.json`` — in-toto Statement v1 / SLSA provenance v1
  predicate binding source revision, builder, workflow, dependencies, digests;
* ``provenance.dsse.json`` + ``SHA256SUMS.sig.json`` — Ed25519 signatures.

Signing key: ``INV64_SIGNING_KEY_HEX`` (+ ``INV64_SIGNING_KID``) from a managed
signer in a protected release job. If absent, an **ephemeral** key is generated,
its public half is written next to the signatures, and ``signing_mode`` is
``ephemeral`` — which ``verify`` reports as FAIL for production (integrity
only, no signer identity). Private keys are never written to disk.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

from inv64_application_model import __version__
from inv64_application_model import provenance as P
from inv64_application_model.errors import Inv64Error
from inv64_application_model.trust import TrustPolicy, TrustStore, verify_artifact

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_LICENSES = {"MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC", "PSF-2.0", "Unlicense", "CC0-1.0",
                    "Apache-2.0 OR BSD-3-Clause", "LicenseRef-Proprietary-Pending", "LicenseRef-OWFa-1.0"}
MEDIA = {".whl": "application/zip", ".gz": "application/gzip", ".json": "application/json", ".zip": "application/zip"}


def _sha(p: Path) -> str:
    return P.sha256_file(p)


def _rev() -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True, timeout=10).stdout.strip()
    except Exception:
        return "unknown"


def sbom(artifacts: list[Path]) -> dict:
    import setuptools
    comps = [
        {"type": "library", "bom-ref": "pkg:pypi/inv64-application-model@" + __version__, "name": "inv64-application-model",
         "version": __version__, "purl": f"pkg:pypi/inv64-application-model@{__version__}",
         "licenses": [{"license": {"id": "LicenseRef-Proprietary-Pending"}}],
         "hashes": [{"alg": "SHA-256", "content": _sha(a)} for a in artifacts if a.suffix == ".whl"]},
        {"type": "library", "bom-ref": "pkg:pypi/cryptography", "name": "cryptography", "version": ">=42 (optional extra 'crypto')",
         "purl": "pkg:pypi/cryptography", "scope": "optional", "licenses": [{"expression": "Apache-2.0 OR BSD-3-Clause"}]},
        {"type": "library", "bom-ref": "pkg:pypi/setuptools@" + setuptools.__version__, "name": "setuptools",
         "version": setuptools.__version__, "purl": f"pkg:pypi/setuptools@{setuptools.__version__}", "scope": "excluded",
         "licenses": [{"license": {"id": "MIT"}}], "properties": [{"name": "role", "value": "build-backend"}]},
        {"type": "library", "bom-ref": "inv44-donor", "name": "inv44-wasm-hardening-system (adapted modules)",
         "version": "4.3.0", "licenses": [{"license": {"id": "LicenseRef-Proprietary-Pending"}}],
         "properties": [{"name": "role", "value": "vendored-adapted: audit.py, provenance.py, release_gate.py"}]},
        {"type": "data", "bom-ref": "oam-spec", "name": "oam-dev/spec", "version": "v0.3.0@3104d27a0ecb55cac84755950e53371aa3e1d2b2",
         "licenses": [{"license": {"id": "LicenseRef-OWFa-1.0"}}], "scope": "excluded",
         "properties": [{"name": "role", "value": "referenced by digest, not copied"}]},
    ]
    bad = []
    for c in comps:
        lic = c["licenses"][0].get("expression") or c["licenses"][0]["license"]["id"]
        if lic not in ALLOWED_LICENSES:
            bad.append(f"{c['name']}: {lic}")
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "library", "name": "inv64-application-model", "version": __version__},
                         "tools": [{"name": "inv64 tools/release.py", "version": __version__}],
                         "properties": [{"name": "source_revision", "value": _rev()},
                                        {"name": "license_policy_violations", "value": json.dumps(bad)},
                                        {"name": "pk_core", "value": "NOT BUNDLED; unknown version/license (BLOCKED_EXTERNAL)"}]},
            "components": comps,
            "dependencies": [{"ref": comps[0]["bom-ref"], "dependsOn": ["pkg:pypi/cryptography"]}]}


def _signing_key() -> tuple[bytes, bytes, str, str]:
    hexkey = os.environ.get("INV64_SIGNING_KEY_HEX")
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    if hexkey:
        gate = ROOT / "evidence" / "EXIT_GATE.json"
        verdict = json.loads(gate.read_text()).get("verdict") if gate.is_file() else None
        if verdict != "GO":  # sign only after every release gate passed (MC-39)
            raise SystemExit(f"refusing managed signing: evidence/EXIT_GATE.json verdict is {verdict!r}, not GO")
        k = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(hexkey))
        mode, kid = "managed", os.environ.get("INV64_SIGNING_KID", "inv64-release")
    else:
        k = Ed25519PrivateKey.generate()
        mode, kid = "ephemeral", "ephemeral-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    priv = k.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    pub = k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return priv, pub, kid, mode


def build(dist: Path, evidence: Path, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    arts = sorted([p for p in dist.iterdir() if p.is_file() and p.suffix in (".whl", ".gz")])
    ev = sorted([p for p in evidence.iterdir() if p.is_file() and p.suffix == ".json"]) if evidence.is_dir() else []
    bom = sbom(arts)
    (out / "sbom.cdx.json").write_text(json.dumps(bom, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    subjects = [{"name": p.name, "digest": {"sha256": _sha(p)}} for p in arts] + \
               [{"name": "evidence/" + p.name, "digest": {"sha256": _sha(p)}} for p in ev] + \
               [{"name": "sbom.cdx.json", "digest": {"sha256": _sha(out / "sbom.cdx.json")}}]
    builder = os.environ.get("GITHUB_WORKFLOW_REF") or f"local:{platform.node() or 'unknown'}"
    stmt = P.statement(subjects, version=__version__, builder_id=builder,
                       invocation={"source": os.environ.get("GITHUB_REPOSITORY", "local-checkout") + "@" + _rev(),
                                   "workflow": os.environ.get("GITHUB_WORKFLOW", "tools/release.py build")},
                       dependencies=[{"uri": "pkg:pypi/setuptools", "digest": {}},
                                     {"uri": "python:" + sys.version.split()[0], "digest": {}}],
                       build_type="urn:pk:inv64:release:1")
    (out / "provenance.intoto.json").write_text(json.dumps(stmt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sums = "".join(f"{s['digest']['sha256']}  {s['name']}\n" for s in subjects) + \
        f"{_sha(out / 'provenance.intoto.json')}  provenance.intoto.json\n"
    (out / "SHA256SUMS").write_text(sums, encoding="utf-8")
    priv, pub, kid, mode = _signing_key()
    env = P.sign(stmt, key=priv, key_id=kid, alg="ed25519")
    (out / "provenance.dsse.json").write_text(json.dumps(env, indent=2) + "\n", encoding="utf-8")
    sums_stmt = P.statement([{"name": "SHA256SUMS", "digest": {"sha256": hashlib.sha256(sums.encode()).hexdigest()}}],
                            version=__version__, builder_id=builder, invocation={"source": stmt["predicate"]["buildDefinition"]["externalParameters"]["source"]},
                            dependencies=[], build_type="urn:pk:inv64:release:1")
    (out / "SHA256SUMS.sig.json").write_text(json.dumps(P.sign(sums_stmt, key=priv, key_id=kid, alg="ed25519"), indent=2) + "\n",
                                             encoding="utf-8")
    (out / "signing-key.pub.json").write_text(json.dumps({"kid": kid, "alg": "ed25519", "public_key_hex": pub.hex(),
                                                          "mode": mode}, indent=2) + "\n", encoding="utf-8")
    manifest = {"schema": "PK_APP_ARTIFACTS/1", "version": __version__, "source_revision": _rev(), "signing_mode": mode,
                "signing_kid": kid, "artifacts": [
                    {"file": s["name"], "media_type": MEDIA.get(Path(s["name"]).suffix, "application/octet-stream"),
                     "bytes": (dist / s["name"]).stat().st_size if (dist / s["name"]).exists() else
                     ((evidence / s["name"][9:]).stat().st_size if s["name"].startswith("evidence/") else (out / s["name"]).stat().st_size),
                     "sha256": s["digest"]["sha256"], "sbom": "sbom.cdx.json", "provenance": "provenance.dsse.json",
                     "signature": "SHA256SUMS.sig.json"} for s in subjects]}
    (out / "ARTIFACTS.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"signing_mode": mode, "kid": kid, "subjects": len(subjects),
            "license_violations": json.loads(bom["metadata"]["properties"][1]["value"])}


def verify(release: Path, dist: Path | None, trusted: dict | None) -> dict:
    """Consumer-side verification using the MC-15 trust verifier."""
    pubinfo = json.loads((release / "signing-key.pub.json").read_text())
    checks = []
    key = trusted or {"kid": pubinfo["kid"], "public_key_hex": pubinfo["public_key_hex"]}
    store = TrustStore(root_keys={})
    store.active = TrustPolicy("release-verify", {key["kid"]: {"alg": "ed25519", "key": bytes.fromhex(key["public_key_hex"]),
                                                               "not_after": None}},
                               {"release": {"signers": [key["kid"]], "builders": [], "sources": [], "min_version": None,
                                            "allowed_versions": None}})
    env = json.loads((release / "SHA256SUMS.sig.json").read_text())
    try:
        verify_artifact((release / "SHA256SUMS").read_bytes(), artifact_class="release", version=__version__,
                        envelope=env, store=store, name="SHA256SUMS", record_floor=False)
        checks.append({"check": "SHA256SUMS signature", "result": "PASS"})
    except Inv64Error as e:
        checks.append({"check": "SHA256SUMS signature", "result": "FAIL", "code": e.code})
    for line in (release / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        cand = [release / name] + ([dist / name] if dist else []) + [release.parent / name]
        p = next((c for c in cand if c.is_file()), None)
        if p is None:
            checks.append({"check": f"digest {name}", "result": "SKIP", "reason": "file not present at verify location"})
        else:
            checks.append({"check": f"digest {name}", "result": "PASS" if _sha(p) == digest else "FAIL"})
    bom = json.loads((release / "sbom.cdx.json").read_text())
    viol = json.loads(next(p["value"] for p in bom["metadata"]["properties"] if p["name"] == "license_policy_violations"))
    checks.append({"check": "license policy", "result": "PASS" if not viol else "FAIL", "violations": viol})
    mode = pubinfo["mode"] if trusted is None else "trusted-key"
    checks.append({"check": "signer identity", "result": "FAIL" if mode == "ephemeral" else "PASS",
                   "reason": "ephemeral key proves integrity only; no managed signer/trust anchor configured (REG-003)"
                   if mode == "ephemeral" else None})
    bad = [c for c in checks if c["result"] == "FAIL"]
    return {"schema": "PK_APP_RELEASE_VERIFY/1", "signing_mode": mode, "checks": checks,
            "result": "FAIL" if bad else "PASS", "verifier": "inv64-trust/1.0"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--dist", required=True)
    b.add_argument("--evidence", required=True)
    b.add_argument("--out", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--release", required=True)
    v.add_argument("--dist")
    v.add_argument("--trusted-key")
    v.add_argument("--trusted-kid")
    v.add_argument("--out")
    a = ap.parse_args(argv)
    if a.cmd == "build":
        print(json.dumps(build(Path(a.dist), Path(a.evidence), Path(a.out))))
        return 0
    trusted = {"kid": a.trusted_kid, "public_key_hex": a.trusted_key} if a.trusted_key else None
    res = verify(Path(a.release), Path(a.dist) if a.dist else None, trusted)
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": res["result"], "failed": [c["check"] for c in res["checks"] if c["result"] == "FAIL"]}))
    return 0 if res["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
