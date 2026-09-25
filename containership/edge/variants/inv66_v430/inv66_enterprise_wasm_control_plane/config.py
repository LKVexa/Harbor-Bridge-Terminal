"""Declarative configuration: schema, loader, provenance, atomic activation (MC-022/023/024/025/026).

A configuration document (``PK_ECP_CONFIG/1``, JSON) holds *all* runtime policy:
limits, approved registries, signer public keys, RBAC bindings and groups,
quotas, required attestations, identity issuers and secret references.

Life of a revision::

    load/parse -> schema validate -> semantic validate -> build PolicySet (pure)
      -> journal "config" entry (author, approvals, source revision, digest)
      -> atomic reference swap (readers see old or new, never partial)

Rollback re-activates a previously journalled revision by digest; the full
document of every activated revision is retained in the journal, so the
history is complete and reproducible.  Production revisions require at least
one approver distinct from the author (two-person rule).
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Any

from .canonical import digest
from .errors import fail
from .provenance import ProvenanceVerifier, SignerKey, signer_keys
from .rbac import Binding, RbacModel
from .schema import validate

CONFIG_SCHEMA_ID = "urn:inv66:schema:PK_ECP_CONFIG:1"


@dataclass(frozen=True)
class PolicySet:
    document: dict
    digest: str
    revision: int
    environment: str
    max_components: int
    max_manifest_bytes: int
    max_inflight: int
    audit_retention_records: int
    idempotency_ttl_s: int
    rbac: RbacModel
    provenance: ProvenanceVerifier
    quotas: dict[str, int] = field(default_factory=dict)

    @property
    def version(self) -> str:
        return f"r{self.revision}:{self.digest[:12]}"


def parse(text: str | bytes) -> dict:
    try:
        return json.loads(text)
    except ValueError as exc:
        raise fail("CONFIG_INVALID", f"not JSON: {exc}") from None


def load_file(path: str | pathlib.Path) -> dict:
    return parse(pathlib.Path(path).read_bytes())


def build_policy(doc: dict) -> PolicySet:
    errs = validate(doc, CONFIG_SCHEMA_ID)
    if errs:
        raise fail("CONFIG_INVALID", "schema validation failed", violations=errs)
    if doc["environment"] == "prod":
        approvers = set(doc.get("approved_by", [])) - {doc["author"]}
        if not approvers:
            raise fail("CONFIG_INVALID", "prod configuration requires an approver other than the author")
    regs = set()
    for r in doc["registries"]:
        if not isinstance(r, str) or not r or r != r.strip().lower() or "/" in r or any(c.isspace() for c in r):
            raise fail("CONFIG_INVALID", f"invalid registry {r!r}")
        regs.add(r)
    try:
        keys: dict[str, SignerKey] = signer_keys(doc["signers"])
        bindings = [Binding(b["subject"], b["role"], b["scope"], b["effect"], b.get("expires_at")) for b in doc["bindings"]]
    except (ValueError, KeyError) as exc:
        raise fail("CONFIG_INVALID", str(exc)) from None
    lim = doc["limits"]
    return PolicySet(
        document=json.loads(json.dumps(doc)),
        digest=digest(doc),
        revision=doc["revision"],
        environment=doc["environment"],
        max_components=lim["max_components"],
        max_manifest_bytes=lim["max_manifest_bytes"],
        max_inflight=lim.get("max_inflight", 256),
        audit_retention_records=lim.get("audit_retention_records", 100_000),
        idempotency_ttl_s=lim.get("idempotency_ttl_s", 86_400),
        rbac=RbacModel(bindings, doc.get("groups", {})),
        provenance=ProvenanceVerifier(frozenset(regs), keys, frozenset(doc.get("require_attestations", []))),
        quotas={k: v["admissions_per_minute"] for k, v in doc["quotas"].items()},
    )


def merge_layers(*layers: dict) -> dict:
    """Layered precedence: built-in defaults < environment/site profile < deployment override.

    Objects merge recursively; lists and scalars from a later layer replace earlier ones.  The
    merged document is what gets validated, digested and journalled, so the effective
    configuration is always reproducible from the journal alone."""
    def merge(a, b):
        if isinstance(a, dict) and isinstance(b, dict):
            out = dict(a)
            for k, v in b.items():
                out[k] = merge(a[k], v) if k in a else v
            return out
        return b
    out: dict = {}
    for layer in layers:
        out = merge(out, layer)
    return out


DEFAULTS = {"schema": "PK_ECP_CONFIG/1",
            "limits": {"max_components": 256, "max_manifest_bytes": 1_000_000, "max_inflight": 256,
                       "audit_retention_records": 100_000, "idempotency_ttl_s": 86_400},
            "require_attestations": ["slsa-provenance/v1"], "bindings": [], "quotas": {}}
