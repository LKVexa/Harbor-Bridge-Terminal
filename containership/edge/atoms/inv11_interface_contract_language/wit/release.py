"""Release engineering: SBOM, reproducible archive, Ed25519 signing (INV11-MC-31/32).

Reproducibility rules: file list sorted by posix path; every entry dated
1980-01-01 00:00:00 (or SOURCE_DATE_EPOCH); permissions 0644; deflate level 9;
no extra fields; __pycache__/*.pyc/evidence runtime files excluded.  Building
twice from the same tree must produce byte-identical archives.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import time
import zipfile
from typing import Any

from . import TOOL_VERSION

EXCLUDE_DIRS = {"__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache", "build", "dist"}
EXCLUDE_SUFFIX = (".pyc", ".pyo")


def _date_time() -> tuple[int, int, int, int, int, int]:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        t = time.gmtime(max(int(epoch), 315532800))
        return (t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec - t.tm_sec % 2)
    return (1980, 1, 1, 0, 0, 0)


def tree_files(root: str, prefix: str) -> list[tuple[str, str]]:
    out = []
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if d not in EXCLUDE_DIRS)
        for f in fns:
            if f.endswith(EXCLUDE_SUFFIX):
                continue
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if rel.startswith("release/"):
                continue
            out.append((f"{prefix}/{rel}", full))
    return sorted(out)


def build_archive(root: str, out_path: str, prefix: str) -> str:
    dt = _date_time()
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for arc, full in tree_files(root, prefix):
            zi = zipfile.ZipInfo(arc, dt)
            zi.external_attr = (0o100644 & 0xFFFF) << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.create_system = 3
            with open(full, "rb") as fh:
                z.writestr(zi, fh.read(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return hashlib.sha256(open(out_path, "rb").read()).hexdigest()


def verify_reproducible(root: str, prefix: str, workdir: str) -> dict[str, Any]:
    a, b = os.path.join(workdir, "a.zip"), os.path.join(workdir, "b.zip")
    ha = build_archive(root, a, prefix)
    hb = build_archive(root, b, prefix)
    return {"reproducible": ha == hb, "sha256_a": ha, "sha256_b": hb,
            "nondeterministic_fields": [] if ha == hb else ["unknown — investigate"]}


def sbom(root: str, name: str = "inv11-interface-contract-language") -> dict[str, Any]:
    """CycloneDX 1.5 JSON.  Runtime dependencies: none (stdlib only); pk_core is
    an optional estate dependency; wasm-tools is a test-only reference tool."""
    files = [{"type": "file", "name": rel.split("/", 1)[1],
              "hashes": [{"alg": "SHA-256", "content": hashlib.sha256(open(full, "rb").read()).hexdigest()}]}
             for rel, full in tree_files(root, "x")]
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "metadata": {"component": {"type": "library", "name": name, "version": TOOL_VERSION,
                                   "licenses": [{"license": {"name": "UNDECLARED — owner decision pending"}}]},
                     "tools": [{"name": "inv11.release", "version": TOOL_VERSION}]},
        "components": [
            {"type": "library", "name": "pk-core", "version": ">=4.0,<5", "scope": "optional",
             "description": "estate conformance runtime (not bundled)"},
            {"type": "application", "name": "wasm-tools", "version": "1.219.1", "scope": "excluded",
             "description": "differential-testing reference tool (test-only, not bundled)",
             "licenses": [{"expression": "Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT"}]},
        ] + files,
    }


def sign(path: str, key_pem_path: str, sig_out: str) -> None:
    exe = shutil.which("openssl")
    if exe is None:
        raise RuntimeError("BLOCKED: openssl unavailable; cannot sign")
    subprocess.run([exe, "pkeyutl", "-sign", "-inkey", key_pem_path, "-rawin", "-in", path, "-out", sig_out],
                   check=True, capture_output=True, timeout=30)


def provenance_statement(archive_sha: str, sbom_sha: str, builder: str, source_digest: str) -> dict[str, Any]:
    """in-toto v1 / SLSA-provenance-shaped statement (unsigned body)."""
    return {"_type": "https://in-toto.io/Statement/v1",
            "subject": [{"name": f"inv11_interface_contract_language-{TOOL_VERSION}.zip", "digest": {"sha256": archive_sha}}],
            "predicateType": "https://slsa.dev/provenance/v1",
            "predicate": {"buildDefinition": {"buildType": "urn:inv11:release:reproducible-zip/1",
                                              "externalParameters": {"version": TOOL_VERSION},
                                              "resolvedDependencies": [{"name": "source-tree", "digest": {"sha256": source_digest}}]},
                          "runDetails": {"builder": {"id": builder}, "byproducts": [{"name": "sbom.cdx.json", "digest": {"sha256": sbom_sha}}]}}}


def source_digest(root: str) -> str:
    h = hashlib.sha256()
    for rel, full in tree_files(root, "x"):
        h.update(rel.encode() + b"\0" + hashlib.sha256(open(full, "rb").read()).digest())
    return h.hexdigest()
