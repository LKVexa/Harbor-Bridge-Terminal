"""INV-38-C036 — Configuration provenance with redaction and drift detection."""
from __future__ import annotations
import hashlib, json
from dataclasses import dataclass, field

_SECRET_KEYS = frozenset({"key", "secret", "token", "credential", "password"})

def content_digest(content: dict) -> str:
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()

def redact(content: dict) -> dict:
    return {k: ("<redacted>" if k in _SECRET_KEYS else v) for k, v in content.items()}

@dataclass
class ProvenanceRecord:
    config_id: str
    schema_version: str
    semver: str
    author: str
    created_at: str
    environment: str
    source_revision: str
    content: dict
    activated_by: str = ""
    activated_at: str = ""
    previous_revision: str = ""
    runtime_generation: int = 0

    @property
    def digest(self) -> str:
        return content_digest(self.content)

    def to_history_entry(self) -> dict:
        # Provenance captures identity/intent WITHOUT copying secrets (C036-T05).
        return {
            "config_id": self.config_id, "schema_version": self.schema_version,
            "semver": self.semver, "author": self.author, "created_at": self.created_at,
            "environment": self.environment, "source_revision": self.source_revision,
            "digest": self.digest, "activated_by": self.activated_by,
            "activated_at": self.activated_at, "previous_revision": self.previous_revision,
            "runtime_generation": self.runtime_generation,
            "content_redacted": redact(self.content),
        }

def detect_drift(desired: dict, active: dict) -> bool:
    return content_digest(desired) != content_digest(active)
