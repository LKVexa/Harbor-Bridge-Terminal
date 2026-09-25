"""Artifact provenance binding (component 04).

Certification keys use a cryptographic artifact identity
``sha256:<64 hex>`` plus a media type (MC-04-01). A provenance statement is an
in-toto-style ``Statement`` (``_type``/``subject``/``predicateType``/
``predicate``) signed with the GAP-15 envelope; accepted predicate types are
an explicit allow-list and unknown top-level fields are rejected rather than
trusted (MC-04-04). The SBOM must name the same digest (MC-04-03). Mutable
tags are resolved through a ``TagResolver`` before any decision, and a tag
that moves between resolve and use is refused (MC-04-08).

The *real* GAP-07 provenance service and its builder trust roots are an
external dependency; this module verifies against whatever trust store the
deployment configures (integration is a recorded blocker, MC-04-02).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .canonical import digest
from .signing import TrustStore, verify_payload

DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
MEDIA_TYPES = {"application/wasm", "application/vnd.wasm.component.v1+wasm", "application/vnd.oci.image.index.v1+json",
               "application/vnd.oci.image.manifest.v1+json", "application/octet-stream+firmware",
               "application/vnd.gap15.config-bundle+json"}
PREDICATE_TYPES = {"https://slsa.dev/provenance/v1"}
STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
STATEMENT_FIELDS = {"_type", "subject", "predicateType", "predicate"}


class ProvenanceError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


@dataclass(frozen=True)
class ArtifactId:
    digest: str
    media_type: str

    def __post_init__(self) -> None:
        if not isinstance(self.digest, str) or not DIGEST_RE.match(self.digest):
            raise ProvenanceError("E_ARTIFACT_DIGEST", "artifact identity must be sha256:<64 lowercase hex>")
        if self.media_type not in MEDIA_TYPES:
            raise ProvenanceError("E_ARTIFACT_MEDIA_TYPE", self.media_type)


@dataclass
class TagResolver:
    """Registry view: mutable tag -> immutable digest, with a monotonic generation per tag."""

    tags: dict = field(default_factory=dict)  # tag -> (digest, generation)

    def resolve(self, tag: str) -> tuple:
        if DIGEST_RE.match(tag):
            return tag, 0
        if tag not in self.tags:
            raise ProvenanceError("E_TAG_UNKNOWN", tag)
        return self.tags[tag]

    def confirm(self, tag: str, resolved: tuple) -> str:
        """Re-resolve at use time; refuse if the tag moved (TOCTOU guard)."""
        now = self.resolve(tag)
        if now != resolved:
            raise ProvenanceError("E_TAG_MOVED", f"{tag} moved from {resolved[0]} to {now[0]}")
        return now[0]


@dataclass(frozen=True)
class ProvenanceResult:
    ok: bool
    code: str
    artifact: Optional[str] = None
    statement_digest: Optional[str] = None
    builder: Optional[str] = None
    source: Optional[str] = None
    children: tuple = ()

    def as_dict(self) -> dict:
        return dict(ok=self.ok, code=self.code, artifact=self.artifact, statement_digest=self.statement_digest,
                    builder=self.builder, source=self.source, children=list(self.children))


def verify_provenance(trust: TrustStore, artifact: ArtifactId, statement: dict, signature: dict, *, sbom: Optional[dict],
                      environment: str, revoked_builders: frozenset = frozenset(),
                      revoked_sources: frozenset = frozenset(), require_sbom: bool = True) -> ProvenanceResult:
    if not isinstance(statement, dict) or set(statement) != STATEMENT_FIELDS:
        return ProvenanceResult(False, "E_PROV_SHAPE")
    if statement["_type"] != STATEMENT_TYPE or statement["predicateType"] not in PREDICATE_TYPES:
        return ProvenanceResult(False, "E_PROV_TYPE")
    sig = verify_payload(trust, signature, message_type="provenance", environment=environment, payload=statement,
                         required_scope="provenance:attest")
    if not sig.ok:
        return ProvenanceResult(False, "E_PROV_" + sig.code[2:])
    subjects = statement["subject"]
    if not isinstance(subjects, list) or not subjects:
        return ProvenanceResult(False, "E_PROV_SUBJECT")
    subject_digests = []
    for s in subjects:
        d = (s.get("digest") or {}).get("sha256") if isinstance(s, dict) else None
        if not isinstance(d, str) or not re.fullmatch(r"[0-9a-f]{64}", d):
            return ProvenanceResult(False, "E_PROV_SUBJECT")
        subject_digests.append("sha256:" + d)
    if len(set(subject_digests)) != len(subject_digests):
        return ProvenanceResult(False, "E_PROV_SUBJECT_AMBIGUOUS")
    if artifact.digest not in subject_digests:
        return ProvenanceResult(False, "E_PROV_DIGEST_MISMATCH")
    pred = statement["predicate"] if isinstance(statement["predicate"], dict) else {}
    builder = ((pred.get("runDetails") or {}).get("builder") or {}).get("id")
    source = ((pred.get("buildDefinition") or {}).get("resolvedDependencies") or [{}])[0].get("uri") if isinstance(
        (pred.get("buildDefinition") or {}).get("resolvedDependencies"), list) else None
    if not builder:
        return ProvenanceResult(False, "E_PROV_BUILDER")
    if builder in revoked_builders:
        return ProvenanceResult(False, "E_PROV_BUILDER_REVOKED", artifact.digest, builder=builder)
    if source and source in revoked_sources:
        return ProvenanceResult(False, "E_PROV_SOURCE_REVOKED", artifact.digest, builder=builder, source=source)
    # multi-artifact releases: every child must be listed as its own subject (MC-04-06)
    children = tuple(sorted(d for d in subject_digests if d != artifact.digest))
    if artifact.media_type == "application/vnd.oci.image.index.v1+json":
        declared = sorted(pred.get("gap15_children", []))
        if declared != list(children):
            return ProvenanceResult(False, "E_PROV_INDEX_MISMATCH")
    if require_sbom:
        if not isinstance(sbom, dict):
            return ProvenanceResult(False, "E_PROV_SBOM_MISSING")
        if sbom.get("subject") != artifact.digest:
            return ProvenanceResult(False, "E_PROV_SBOM_SUBJECT")
    return ProvenanceResult(True, "OK", artifact.digest, digest(statement), builder, source, children)
