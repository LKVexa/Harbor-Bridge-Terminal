"""MC-16 - SBOM, release manifest, signing, verification and vulnerability gate.

    python tools/supply_chain.py sbom      -> evidence/sbom.cdx.json (CycloneDX 1.5)
    python tools/supply_chain.py manifest  -> evidence/release_manifest.json (+ .sig)
    python tools/supply_chain.py verify    -> exit 0 only if every artifact digest and the signature match
    python tools/supply_chain.py vulns     -> evidence/vuln_scan.json

Signing: Ed25519 via ``cryptography`` when installed.  The signing key is
generated per run into ``--key`` (default: evidence/.release_signing_key,
excluded from the manifest and never committed); the manifest carries the
public key.  In production the key must come from the release KMS - that
binding is recorded as a BLOCKED item until a KMS reference is configured.

Vulnerability scanning: the runtime dependency set is stdlib + optional
``cryptography``.  With no advisory feed reachable/configured, the scan
reports INDETERMINATE (never PASS) - see governance/VULN_POLICY.md.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import platform
import subprocess
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
EVID = PKG / "evidence"
EXCLUDE_DIRS = {"__pycache__", "evidence", ".git"}
VERSION = (PKG / "VERSION").read_text().strip()


def artifacts() -> list[pathlib.Path]:
    out = []
    for p in sorted(PKG.rglob("*")):
        if p.is_file() and not (set(p.relative_to(PKG).parts) & EXCLUDE_DIRS) and not p.name.endswith(".pyc"):
            out.append(p)
    return out


def sha256(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def source_revision() -> str:
    """Content-addressed source revision (no VCS in the archive): sha256 over
    (path, digest) of every source artifact."""
    h = hashlib.sha256()
    for p in artifacts():
        h.update(p.relative_to(PKG).as_posix().encode() + b"\0" + sha256(p).encode() + b"\n")
    return "srcrev:" + h.hexdigest()


def _crypto_version() -> str | None:
    try:
        import cryptography
        return cryptography.__version__
    except ImportError:
        return None


def sbom() -> dict:
    lock = json.loads((PKG / "deps" / "pk_core.lock.json").read_text())
    comps = [
        {"type": "application", "name": "inv19_os_asynchronous_analogues", "version": VERSION,
         "licenses": [{"license": {"name": "UNDECLARED - owner to record (see governance/EXCEPTIONS.md EX-003)"}}],
         "hashes": [{"alg": "SHA-256", "content": source_revision().split(":")[1]}]},
        {"type": "platform", "name": "cpython", "version": platform.python_version(),
         "licenses": [{"license": {"id": "PSF-2.0"}}]},
        {"type": "library", "name": "pk_core", "version": lock.get("version") or "UNRESOLVED",
         "scope": "required", "licenses": [{"license": {"name": lock.get("license") or "UNKNOWN"}}],
         "properties": [{"name": "inv19:lock_status", "value": lock["status"]}]},
        {"type": "operating-system", "name": "linux-kernel-io_uring-abi", "version": "5.6+",
         "description": "raw syscall ABI (no liburing / no compiled shim)"},
    ]
    cv = _crypto_version()
    comps.append({"type": "library", "name": "cryptography", "version": cv or "NOT_INSTALLED",
                  "scope": "optional", "purl": f"pkg:pypi/cryptography@{cv}" if cv else None,
                  "licenses": [{"expression": "Apache-2.0 OR BSD-3-Clause"}]})
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                         "component": {"name": "inv19_os_asynchronous_analogues", "version": VERSION},
                         "tools": [{"name": "tools/supply_chain.py", "version": "1.0"}]},
            "components": comps,
            "compositions": [{"aggregate": "incomplete_first_party_only",
                              "note": "pk_core transitive dependencies unknown until pk_core is pinned"}]}


def build_env() -> dict:
    return {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
            "os": platform.system(), "kernel": platform.release(), "machine": platform.machine(),
            "toolchain": "none (pure Python + ctypes; no compilation step)"}


def _key(path: pathlib.Path):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    if path.exists():
        return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(path.read_text().strip()))
    k = Ed25519PrivateKey.generate()
    path.write_text(k.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                                    serialization.NoEncryption()).hex())
    os.chmod(path, 0o600)
    return k


def manifest(key_path: pathlib.Path) -> dict:
    from cryptography.hazmat.primitives import serialization
    arts = [{"path": p.relative_to(PKG).as_posix(), "sha256": sha256(p), "bytes": p.stat().st_size}
            for p in artifacts()]
    m = {"schema": "PK_RELEASE_MANIFEST/1", "release": VERSION, "source_revision": source_revision(),
         "build_env": build_env(), "artifacts": arts,
         "slsa": {"buildType": "inv19/archive-build@v1", "level": "L1-equivalent (scripted, provenance generated; no hosted builder)"}}
    k = _key(key_path)
    body = json.dumps(m, sort_keys=True, separators=(",", ":")).encode()
    m_signed = {"manifest": m, "signature": {"alg": "ed25519", "sig": k.sign(body).hex(),
                "public_key": k.public_key().public_bytes(serialization.Encoding.Raw,
                                                           serialization.PublicFormat.Raw).hex(),
                "key_binding": "EPHEMERAL (release KMS binding BLOCKED - see EXCEPTIONS.md EX-004)"}}
    return m_signed


def verify(signed: dict, expected_public: str | None = None) -> tuple[bool, list[str]]:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    probs = []
    m, s = signed["manifest"], signed["signature"]
    if expected_public and s["public_key"] != expected_public:
        probs.append("public key does not match the trusted release key")
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(s["public_key"])).verify(
            bytes.fromhex(s["sig"]), json.dumps(m, sort_keys=True, separators=(",", ":")).encode())
    except (InvalidSignature, ValueError):
        probs.append("manifest signature invalid")
    listed = {a["path"] for a in m["artifacts"]}
    for a in m["artifacts"]:
        p = PKG / a["path"]
        if not p.exists():
            probs.append(f"missing artifact {a['path']}")
        elif sha256(p) != a["sha256"]:
            probs.append(f"digest mismatch {a['path']}")
    for p in artifacts():
        if p.relative_to(PKG).as_posix() not in listed:
            probs.append(f"unlisted artifact {p.relative_to(PKG).as_posix()}")
    if m["source_revision"] != source_revision():
        probs.append("source revision mismatch (evidence from another revision)")
    return (not probs), probs


def vulns() -> dict:
    cv = _crypto_version()
    res = {"schema": "PK_VULN_SCAN/1", "scanned": [{"name": "cryptography", "version": cv}] if cv else [],
           "advisory_feed": None, "result": "INDETERMINATE",
           "reason": "no pinned advisory snapshot configured; a scan with no feed can never PASS",
           "eol": {"python": platform.python_version(),
                   "python_eol": platform.python_version_tuple()[:2] < ("3", "10")}}
    try:
        r = subprocess.run([sys.executable, "-m", "pip_audit", "--version"], capture_output=True, timeout=20)
        res["pip_audit_available"] = r.returncode == 0
    except Exception:
        res["pip_audit_available"] = False
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sbom", "manifest", "verify", "vulns", "all"])
    ap.add_argument("--key", default=str(EVID / ".release_signing_key"))
    a = ap.parse_args()
    EVID.mkdir(exist_ok=True)
    rc = 0
    if a.cmd in ("sbom", "all"):
        (EVID / "sbom.cdx.json").write_text(json.dumps(sbom(), indent=1))
    if a.cmd in ("vulns", "all"):
        (EVID / "vuln_scan.json").write_text(json.dumps(vulns(), indent=1))
    if a.cmd in ("manifest", "all"):
        (EVID / "release_manifest.json").write_text(json.dumps(manifest(pathlib.Path(a.key)), indent=1))
    if a.cmd in ("verify", "all"):
        ok, probs = verify(json.loads((EVID / "release_manifest.json").read_text()))
        print(json.dumps({"verified": ok, "problems": probs[:20]}))
        rc = 0 if ok else 3
    return rc


if __name__ == "__main__":
    sys.exit(main())
