# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Artifact integrity & supply chain (GAP-024).

* ``manifest`` — SHA-256 of every shipped file (sorted, excludes generated evidence).
* ``sbom`` — CycloneDX 1.5 JSON: this package + declared runtime deps with digests.
* ``sign_manifest``/``verify_manifest`` — HMAC-SHA256 detached signature with a
  key from the secret provider. This is integrity/authenticity for a closed
  estate; public-key signing (Sigstore/cosign, in-toto/SLSA provenance) is the
  documented production path and is wired as a CI step, not faked here.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

PKG = Path(__file__).resolve().parent
EXCLUDE_DIRS = {"__pycache__", "evidence", ".pytest_cache"}
EXCLUDE_FILES = {"MANIFEST.sha256.json", "MANIFEST.sig"}


def files(root: Path = PKG) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file()
                  and not (set(p.relative_to(root).parts[:-1]) & EXCLUDE_DIRS) and p.name not in EXCLUDE_FILES
                  and p.suffix not in (".pyc",))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest(root: Path = PKG) -> dict:
    entries = {p.relative_to(root).as_posix(): sha256(p) for p in files(root)}
    tree = hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()
    return {"schema": "INV30_MANIFEST/1", "tree_digest": "sha256:" + tree, "files": entries}


def verify_tree(root: Path, recorded: dict) -> list[str]:
    now = manifest(root)["files"]
    out = [f"missing: {k}" for k in recorded["files"] if k not in now]
    out += [f"unexpected: {k}" for k in now if k not in recorded["files"]]
    out += [f"modified: {k}" for k, v in recorded["files"].items() if k in now and now[k] != v]
    return out


def sign_manifest(m: dict, key: bytes) -> str:
    return hmac.new(key, json.dumps(m, sort_keys=True).encode(), hashlib.sha256).hexdigest()


def verify_manifest(m: dict, sig: str, key: bytes) -> bool:
    return hmac.compare_digest(sign_manifest(m, key), sig)


def sbom(version: str, pk_core_version: str | None, pk_core_digest: str | None) -> dict:
    comps = [{"type": "library", "name": "inv30-capability-hardware-sandbox", "version": version,
              "licenses": [{"license": {"id": "LicenseRef-LinearFinance-Proprietary"}}],
              "hashes": [{"alg": "SHA-256", "content": manifest()["tree_digest"].split(":")[1]}]}]
    if pk_core_version:
        c = {"type": "framework", "name": "pk_core", "version": pk_core_version, "scope": "optional"}
        if pk_core_digest:
            c["hashes"] = [{"alg": "SHA-256", "content": pk_core_digest}]
        comps.append(c)
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "library", "name": "inv30-capability-hardware-sandbox",
                                       "version": version}},
            "components": comps}


def pk_core_digest() -> str | None:
    try:
        import pk_core
    except ModuleNotFoundError:
        return None
    root = Path(pk_core.__file__).resolve().parent
    entries = {p.name: sha256(p) for p in sorted(root.glob("*.py"))}
    return hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()


def license_check(allowed=("LicenseRef-LinearFinance-Proprietary", "MIT", "BSD-3-Clause", "Apache-2.0")) -> list[str]:
    """Every shipped .py must carry an SPDX header matching an allowed license."""
    bad = []
    for p in files():
        if p.suffix == ".py":
            head = p.read_text(encoding="utf-8").splitlines()[:3]
            ids = [l.split("SPDX-License-Identifier:")[1].strip() for l in head if "SPDX-License-Identifier:" in l]
            if not ids or ids[0] not in allowed:
                bad.append(p.relative_to(PKG).as_posix())
    return bad


_SECRET_PATTERNS = [
    (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "private key"),
    (r"(?i)(?:api|secret|minting|private)[_-]?key\s*[:=]\s*['\"](?!env:|file:)[^'\"]{16,}['\"]", "inline key assignment"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key id"),
    (r"ghp_[A-Za-z0-9]{36}", "GitHub token"),
]


# Only the scanner's own pattern table and its fixture test are exempt — by exact path, not by content.
_SCAN_EXEMPT = {"integrity.py", "tests/test_config_integrity.py"}


def secret_scan(root: Path = PKG) -> list[str]:
    """Repository/artifact secret scan (GAP-025). Test files may use obvious dummy keys (b"A" * 32)."""
    import re
    hits = []
    for p in files(root):
        if p.suffix not in (".py", ".json", ".md", ".toml", ".yaml", ".yml", ".txt", ".lock", ""):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for pat, label in _SECRET_PATTERNS:
            if re.search(pat, text) and p.relative_to(root).as_posix() not in _SCAN_EXEMPT:
                hits.append(f"{p.relative_to(root).as_posix()}: {label}")
    return hits
