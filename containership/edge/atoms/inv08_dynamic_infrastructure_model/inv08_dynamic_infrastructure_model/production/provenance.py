"""Component 04 - release provenance and artifact signing.

* ``sbom``: CycloneDX 1.5 JSON for the package files (stdlib only; the project has
  zero third-party runtime dependencies, recorded as such).  Deterministic: the
  serial number is a UUIDv5 of the component digests, no wall-clock timestamp
  unless injected.
* ``statement``: in-toto Statement v1 with a SLSA provenance v1 predicate.
* ``sign_envelope`` / ``VerificationPolicy``: HMAC-SHA256 via ``core.TrustRoot``.
  Keys are NONPRODUCTION by construction; a policy with ``require_production=True``
  (the release default) therefore REJECTS every signature produced here.  Real
  asymmetric signing / trusted publisher identity / trust-root distribution are
  BLOCKED on an external KMS/Sigstore-style signer.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path

from .core import TrustRoot, canonical, digest, sha256_hex

PKG_DIR = Path(__file__).resolve().parent.parent
STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
SLSA_PREDICATE = "https://slsa.dev/provenance/v1"
BUILD_TYPE = "https://inv08.invalid/buildtypes/local-sdist@v1"
EXCLUDE_PARTS = {"__pycache__", ".git"}


def package_files(root: Path = PKG_DIR) -> list[str]:
    root = Path(root)
    return sorted(str(p.relative_to(root)) for p in root.rglob("*")
                  if p.is_file() and not (set(p.relative_to(root).parts) & EXCLUDE_PARTS)
                  and p.suffix not in {".pyc"})


def file_digests(root: Path, files: list[str]) -> dict[str, str]:
    return {f: sha256_hex((Path(root) / f).read_bytes()) for f in files}


def sbom(root: Path = PKG_DIR, files: list[str] | None = None, *, name: str = "inv08-dynamic-infrastructure-model",
         version: str = "4.3.0.dev1", timestamp: str | None = None) -> dict:
    files = package_files(root) if files is None else sorted(files)
    dig = file_digests(root, files)
    serial = uuid.uuid5(uuid.NAMESPACE_URL, "inv08:" + digest(dig))
    meta = {"component": {"type": "library", "bom-ref": f"pkg:pypi/{name}@{version}",
                          "name": name, "version": version,
                          "purl": f"pkg:pypi/{name}@{version}"},
            "properties": [{"name": "inv08:runtime-third-party-deps", "value": "0"}]}
    if timestamp:
        meta["timestamp"] = timestamp
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "serialNumber": f"urn:uuid:{serial}",
        "version": 1, "metadata": meta,
        "components": [{"type": "file", "bom-ref": f"file:{f}", "name": f,
                        "hashes": [{"alg": "SHA-256", "content": dig[f]}]} for f in files],
        "dependencies": [{"ref": meta["component"]["bom-ref"], "dependsOn": []}],
    }


def validate_sbom(doc: dict) -> list[str]:
    p = []
    if doc.get("bomFormat") != "CycloneDX" or doc.get("specVersion") != "1.5":
        p.append("not CycloneDX 1.5")
    if not str(doc.get("serialNumber", "")).startswith("urn:uuid:"):
        p.append("serialNumber must be urn:uuid")
    for c in doc.get("components", []):
        hs = c.get("hashes") or []
        if not hs or hs[0].get("alg") != "SHA-256" or len(hs[0].get("content", "")) != 64:
            p.append(f"component {c.get('name')} lacks SHA-256")
    return p


def statement(subjects: dict[str, str], *, sbom_doc: dict, builder_id: str, invocation_id: str,
              source_digest: str | None = None) -> dict:
    return {
        "_type": STATEMENT_TYPE,
        "subject": [{"name": n, "digest": {"sha256": d}} for n, d in sorted(subjects.items())],
        "predicateType": SLSA_PREDICATE,
        "predicate": {
            "buildDefinition": {"buildType": BUILD_TYPE,
                                "externalParameters": {"source_digest": source_digest},
                                "internalParameters": {"sbom_digest": digest(sbom_doc)},
                                "resolvedDependencies": []},
            "runDetails": {"builder": {"id": builder_id},
                           "metadata": {"invocationId": invocation_id}},
        },
    }


def sign_envelope(stmt: dict, trust: TrustRoot, kid: str) -> dict:
    return {"payloadType": "application/vnd.in-toto+json", "payload": stmt,
            "signatures": [trust.sign(kid, stmt)]}


@dataclass
class VerificationPolicy:
    trusted_kids: set = field(default_factory=set)
    trusted_builders: set = field(default_factory=set)
    require_production: bool = True   # release default: nonproduction keys never pass

    def verify(self, env: dict, trust: TrustRoot, artifacts: dict[str, str] | None = None) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        stmt = env.get("payload") if isinstance(env, dict) else None
        if not isinstance(stmt, dict) or stmt.get("_type") != STATEMENT_TYPE:
            return False, ["not an in-toto v1 statement"]
        if stmt.get("predicateType") != SLSA_PREDICATE:
            reasons.append("predicate is not SLSA provenance v1")
        sigs = env.get("signatures") or []
        if not sigs:
            reasons.append("unsigned")
        good = [s for s in sigs if s.get("kid") in self.trusted_kids
                and trust.verify(stmt, s, require_production=self.require_production)]
        if sigs and not good:
            if self.require_production and any(not s.get("production") for s in sigs):
                reasons.append("nonproduction signature rejected by production policy")
            else:
                reasons.append("no signature from a trusted key verifies")
        builder = stmt.get("predicate", {}).get("runDetails", {}).get("builder", {}).get("id")
        if self.trusted_builders and builder not in self.trusted_builders:
            reasons.append(f"untrusted builder {builder!r}")
        if artifacts is not None:
            subj = {s["name"]: s["digest"].get("sha256") for s in stmt.get("subject", [])}
            for name, d in sorted(artifacts.items()):
                if name not in subj:
                    reasons.append(f"artifact {name} not in provenance")
                elif subj[name] != d:
                    reasons.append(f"artifact {name} digest mismatch")
            for name in sorted(set(subj) - set(artifacts)):
                reasons.append(f"provenance subject {name} missing from release")
        return not reasons, reasons


def envelope_digest(env: dict) -> str:
    return sha256_hex(canonical(env))
