"""MC-040 - Supply-chain manifest, SBOM, provenance attestation and signing.

* manifest: sha256 of every shipped file (sorted, excludes caches/evidence);
* SBOM: CycloneDX 1.5 JSON (the package, the interpreter; zero third-party
  runtime components - declared, not assumed);
* provenance: in-toto Statement v1 with SLSA-style predicate (builder id,
  source digest, invocation) - *unsigned builder identity is a blocker*;
* release signature: Ed25519 over the canonical statement.  The release key
  is referenced (``secret://``/``env:``/``file:``), never stored in the repo.
"""
from __future__ import annotations

import hashlib
import os
import platform
import sys
import time

from . import canonical
from .identity import b64, unb64
from . import ed25519
from .errors import SchedulerError

EXCLUDE_DIRS = {"__pycache__", ".git", "evidence", ".pytest_cache", "fuzz_corpus_tmp"}
EXCLUDE_FILES = {"MANIFEST.sha256", "RELEASE.sig.json"}


def iter_files(root: str):
    for d, dirs, files in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in EXCLUDE_DIRS)
        for f in sorted(files):
            if f in EXCLUDE_FILES or f.endswith((".pyc", ".tmp")):
                continue
            p = os.path.join(d, f)
            yield os.path.relpath(p, root).replace(os.sep, "/"), p


def manifest(root: str) -> dict[str, str]:
    out = {}
    for rel, p in iter_files(root):
        with open(p, "rb") as fh:
            out[rel] = hashlib.sha256(fh.read()).hexdigest()
    return out


def manifest_text(m: dict[str, str]) -> str:
    return "".join(f"{h}  ./{rel}\n" for rel, h in sorted(m.items()))


def verify_manifest(root: str, text: str) -> list[str]:
    want = {}
    for line in text.splitlines():
        h, rel = line.split("  ", 1)
        want[rel[2:]] = h
    have = manifest(root)
    problems = [f"modified: {r}" for r in sorted(want) if r in have and have[r] != want[r]]
    problems += [f"missing: {r}" for r in sorted(set(want) - set(have))]
    problems += [f"unlisted: {r}" for r in sorted(set(have) - set(want))]
    return problems


def artifact_digest(m: dict[str, str]) -> str:
    return canonical.digest(m)


def sbom(version: str, m: dict[str, str]) -> dict:
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "library", "name": "gap03_topology_aware_scheduler", "version": version,
                                       "hashes": [{"alg": "SHA-256", "content": artifact_digest(m)}]},
                         "tools": [{"name": "gap03-supply-chain", "version": "1"}]},
            "components": [{"type": "platform", "name": "cpython", "version": platform.python_version(),
                            "scope": "required"}],
            "dependencies": [], "properties": [{"name": "gap03:third_party_runtime_components", "value": "0"}]}


def provenance(version: str, m: dict[str, str], *, builder_id: str, source_uri: str, clock=time.time) -> dict:
    return {"_type": "https://in-toto.io/Statement/v1",
            "subject": [{"name": f"gap03_topology_aware_scheduler-{version}", "digest": {"sha256": artifact_digest(m)}}],
            "predicateType": "https://slsa.dev/provenance/v1",
            "predicate": {"buildDefinition": {"buildType": "gap03/local-package@1", "externalParameters": {"source": source_uri},
                                              "internalParameters": {"python": sys.version.split()[0]}},
                          "runDetails": {"builder": {"id": builder_id}, "metadata": {"finishedOn": int(clock())}}}}


def sign_release(key, statement: dict) -> dict:
    return {"statement": statement, "kid": key.kid, "issuer": key.issuer, "alg": "Ed25519",
            "signature": b64(key.sign(canonical.dumps(statement)))}


def verify_release(envelope: dict, public: bytes, *, expected_digest: str) -> dict:
    if envelope.get("alg") != "Ed25519":
        raise SchedulerError("UNAUTHENTICATED", "release signature algorithm not allowed")
    if not ed25519.verify(public, canonical.dumps(envelope["statement"]), unb64(envelope["signature"])):
        raise SchedulerError("UNAUTHENTICATED", "release signature invalid")
    got = envelope["statement"]["subject"][0]["digest"]["sha256"]
    if got != expected_digest:
        raise SchedulerError("INTEGRITY_FAILURE", "release signature is for a different artifact")
    return envelope["statement"]


def vulnerability_scan(sbom_doc: dict, advisories: dict) -> dict:
    """Match SBOM components against a pinned advisory snapshot. An empty or unsourced
    snapshot yields INDETERMINATE, never CLEAN."""
    if not advisories.get("source") or not advisories.get("fetched_at"):
        return {"status": "INDETERMINATE", "reason": "no sourced advisory snapshot", "matches": []}
    matches = [a for a in advisories.get("items", []) for c in sbom_doc["components"]
               if a["package"] == c["name"] and c["version"] in a.get("affected", [])]
    return {"status": "VULNERABLE" if matches else "CLEAN", "matches": matches, "source": advisories["source"]}


def deterministic_zip(root: str, out_path: str, *, prefix: str = "gap03_topology_aware_scheduler/") -> str:
    """Repeatable archive: sorted entries, fixed timestamps/permissions -> identical bytes for identical trees."""
    import zipfile
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for rel, p in iter_files(root):
            zi = zipfile.ZipInfo(prefix + rel, date_time=(2026, 1, 1, 0, 0, 0))
            zi.external_attr = 0o644 << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            with open(p, "rb") as fh:
                z.writestr(zi, fh.read())
    with open(out_path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def third_party_imports(root: str) -> list[str]:
    """Every top-level import that is neither stdlib nor this package (dependency pinning applies to these)."""
    import ast
    std = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}
    found = set()
    for rel, p in iter_files(root):
        if not rel.endswith(".py"):
            continue
        with open(p, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            for n in names:
                top = n.split(".")[0]
                if top not in std and top not in ("gap03_topology_aware_scheduler", "pk_core"):
                    found.add(top)
    return sorted(found)
