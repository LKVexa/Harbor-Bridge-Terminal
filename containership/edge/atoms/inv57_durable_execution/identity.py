"""Workflow instance identity and namespace (SG-02).

A workflow identity is the immutable composite (tenant, environment, site,
namespace, workflow_id, run_id).  ``run_id`` changes on a restart-as-new;
``workflow_id`` never changes.  The canonical key is length-prefixed so no two
distinct identities can encode to the same key, whatever characters appear.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import re
import secrets
import unicodedata

from .errors import InvalidIdentity, Unauthorized

IDENTITY_SCHEMA = "INV57_WORKFLOW_IDENTITY/1"
MAX_FIELD_LEN = 128
_FIELD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._\-]*")
_FIELDS = ("tenant", "environment", "site", "namespace", "workflow_id", "run_id")


def _check_field(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise InvalidIdentity(f"{name} must be a string")
    if not value:
        raise InvalidIdentity(f"{name} must be non-empty")
    if unicodedata.normalize("NFC", value) != value or not value.isascii():
        raise InvalidIdentity(f"{name} must be ASCII (no unicode confusables)")
    if len(value) > MAX_FIELD_LEN:
        raise InvalidIdentity(f"{name} exceeds {MAX_FIELD_LEN} characters")
    if not _FIELD_RE.fullmatch(value):
        raise InvalidIdentity(f"{name} contains characters outside [A-Za-z0-9._-]")
    return value


@dataclass(frozen=True, slots=True)
class WorkflowIdentity:
    tenant: str
    environment: str
    site: str
    namespace: str
    workflow_id: str
    run_id: str

    def __post_init__(self) -> None:
        for field in _FIELDS:
            _check_field(field, getattr(self, field))

    @classmethod
    def new(cls, *, tenant: str, environment: str, site: str, namespace: str,
            workflow_id: str | None = None) -> "WorkflowIdentity":
        """Server-generated ids use 128 bits of randomness; caller ids are accepted as given."""
        return cls(tenant, environment, site, namespace,
                   workflow_id or f"wf-{secrets.token_hex(16)}",
                   f"run-{secrets.token_hex(8)}")

    def next_run(self) -> "WorkflowIdentity":
        """Restart-as-new keeps workflow_id and allocates a fresh run_id."""
        return replace(self, run_id=f"run-{secrets.token_hex(8)}")

    def key(self) -> str:
        return "|".join(f"{len(v)}:{v}" for v in (getattr(self, f) for f in _FIELDS))

    def to_dict(self) -> dict[str, str]:
        return {"schema": IDENTITY_SCHEMA, **{f: getattr(self, f) for f in _FIELDS}}

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowIdentity":
        if not isinstance(data, dict) or data.get("schema") != IDENTITY_SCHEMA:
            raise InvalidIdentity("identity document has wrong schema")
        extra = set(data) - set(_FIELDS) - {"schema"}
        if extra:
            raise InvalidIdentity(f"identity document has unknown fields {sorted(extra)}")
        return cls(**{f: data.get(f) for f in _FIELDS})

    def log_ref(self) -> str:
        """Short, non-reversible correlation reference safe for logs/metrics."""
        import hashlib
        return hashlib.sha256(self.key().encode()).hexdigest()[:16]


def bind_to_principal(identity: WorkflowIdentity, *, principal_tenant: str,
                      principal_environment: str) -> WorkflowIdentity:
    """Reject cross-tenant/cross-environment spoofing: the authenticated context wins."""
    if identity.tenant != principal_tenant or identity.environment != principal_environment:
        raise Unauthorized("workflow identity does not belong to the authenticated tenant/environment")
    return identity
