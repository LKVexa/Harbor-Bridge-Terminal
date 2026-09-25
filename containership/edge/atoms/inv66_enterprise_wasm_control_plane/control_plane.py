"""Self-contained admission and audit engine for INV-66.

This module deliberately has no ``pk_core`` dependency so its security-critical
admission behavior can be exercised in isolation.  The surrounding component
adapter in :mod:`component` binds it to the Post-Kubernetes checklist runtime.
"""
from __future__ import annotations

import copy
import hashlib
import json
import threading
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Iterable, Mapping

_ALLOWED_ROLES = frozenset({"deployer", "admin"})
_AUDIT_DOMAIN = b"PK_ECP_AUDIT/1\0"
_ZERO_HASH = "0" * 64


def _canonical_json(value: Any) -> bytes:
    """Return a stable JSON representation or raise ``TypeError``/``ValueError``."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _hash_record(sequence: int, previous_hash: str, entry: Mapping[str, Any]) -> str:
    body = _canonical_json({"sequence": sequence, "previous_hash": previous_hash, "entry": entry})
    return hashlib.sha256(_AUDIT_DOMAIN + body).hexdigest()


def _clean_identity(value: Any, field_name: str, reasons: list[str], *, limit: int = 256) -> str | None:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > limit:
        reasons.append(f"{field_name} must be a non-empty trimmed string of at most {limit} characters")
        return None
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        reasons.append(f"{field_name} contains control characters")
        return None
    return value


@dataclass
class ControlPlane:
    """In-memory reference implementation of enterprise admission guardrails.

    The implementation intentionally models only the local decision engine.  It
    does not claim to be the durable, replicated enterprise service described by
    the full INV-66 production checklist.
    """

    roles: Mapping[tuple[str, str], str]
    registries: Iterable[str]
    signers: Iterable[str]
    max_components: int = 256
    max_manifest_bytes: int = 1_000_000

    _audit: list[dict[str, Any]] = field(default_factory=list, init=False, repr=False)
    _forwarded: list[dict[str, Any]] = field(default_factory=list, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.max_components, int) or isinstance(self.max_components, bool) or not (1 <= self.max_components <= 10_000):
            raise ValueError("max_components must be an integer in [1, 10000]")
        if not isinstance(self.max_manifest_bytes, int) or isinstance(self.max_manifest_bytes, bool) or not (1_024 <= self.max_manifest_bytes <= 100_000_000):
            raise ValueError("max_manifest_bytes must be an integer in [1024, 100000000]")

        cleaned_roles: dict[tuple[str, str], str] = {}
        for key, role in dict(self.roles).items():
            if (
                not isinstance(key, tuple)
                or len(key) != 2
                or not all(isinstance(part, str) and part and part == part.strip() for part in key)
            ):
                raise ValueError("role keys must be (user, lattice) non-empty trimmed string tuples")
            if role not in _ALLOWED_ROLES:
                raise ValueError(f"unsupported role {role!r}; expected one of {sorted(_ALLOWED_ROLES)}")
            cleaned_roles[key] = role

        if isinstance(self.registries, (str, bytes)) or isinstance(self.signers, (str, bytes)):
            raise ValueError("registries and signers must be collections, not scalar strings")
        cleaned_registries = frozenset(self._normalize_registry(v) for v in self.registries)
        cleaned_signers = frozenset(self._normalize_signer(v) for v in self.signers)
        if not cleaned_registries:
            raise ValueError("at least one approved registry is required")
        if not cleaned_signers:
            raise ValueError("at least one approved signer is required")

        # Defensive copies prevent callers from changing policy after activation.
        self.roles = MappingProxyType(cleaned_roles)
        self.registries = cleaned_registries
        self.signers = cleaned_signers

    @staticmethod
    def _normalize_registry(value: Any) -> str:
        if not isinstance(value, str) or not value or value != value.strip() or "/" in value:
            raise ValueError(f"invalid registry policy entry: {value!r}")
        if any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in value):
            raise ValueError(f"invalid registry policy entry: {value!r}")
        return value.lower()

    @staticmethod
    def _normalize_signer(value: Any) -> str:
        if not isinstance(value, str) or not value or value != value.strip() or len(value) > 512:
            raise ValueError(f"invalid signer policy entry: {value!r}")
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
            raise ValueError(f"invalid signer policy entry: {value!r}")
        return value

    @property
    def audit(self) -> tuple[dict[str, Any], ...]:
        """Return a defensive snapshot of the append-only audit history."""
        return tuple(self.export_audit())

    @property
    def forwarded(self) -> tuple[dict[str, Any], ...]:
        """Return a defensive snapshot of admitted manifests."""
        with self._lock:
            return tuple(copy.deepcopy(self._forwarded))

    def export_audit(self) -> list[dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._audit)

    def _record(self, entry: Mapping[str, Any]) -> None:
        """Append an audit record. Caller must hold ``_lock``."""
        previous_hash = self._audit[-1]["hash"] if self._audit else _ZERO_HASH
        sequence = len(self._audit) + 1
        frozen_entry = copy.deepcopy(dict(entry))
        record_hash = _hash_record(sequence, previous_hash, frozen_entry)
        self._audit.append(
            {
                "sequence": sequence,
                "entry": frozen_entry,
                "previous_hash": previous_hash,
                "hash": record_hash,
            }
        )

    def verify_audit(self, records: Iterable[Mapping[str, Any]] | None = None) -> bool:
        """Verify structural and cryptographic continuity of an audit snapshot."""
        if records is None:
            records = self.export_audit()
        try:
            snapshot = list(copy.deepcopy(records))
        except Exception:
            return False

        previous_hash = _ZERO_HASH
        for expected_sequence, record in enumerate(snapshot, start=1):
            try:
                if not isinstance(record, Mapping):
                    return False
                if record.get("sequence") != expected_sequence:
                    return False
                if record.get("previous_hash") != previous_hash:
                    return False
                entry = record["entry"]
                if not isinstance(entry, Mapping):
                    return False
                expected_hash = _hash_record(expected_sequence, previous_hash, entry)
                if record.get("hash") != expected_hash:
                    return False
                previous_hash = expected_hash
            except (KeyError, TypeError, ValueError, OverflowError):
                return False
        return True

    def _manifest_digest_and_size(self, manifest: Any, reasons: list[str]) -> tuple[str | None, int | None]:
        try:
            encoded = _canonical_json(manifest)
        except (TypeError, ValueError, OverflowError):
            reasons.append("manifest must be finite canonical JSON data")
            return None, None
        size = len(encoded)
        if size > self.max_manifest_bytes:
            reasons.append(f"manifest exceeds {self.max_manifest_bytes} byte limit")
        return hashlib.sha256(encoded).hexdigest(), size

    def admit(self, user: Any, lattice: Any, manifest: Any) -> dict[str, Any]:
        """Evaluate a manifest, append the decision, and forward only on success."""
        reasons: list[str] = []
        clean_user = _clean_identity(user, "user", reasons)
        clean_lattice = _clean_identity(lattice, "lattice", reasons)

        if clean_user is None or clean_lattice is None or self.roles.get((clean_user, clean_lattice)) not in _ALLOWED_ROLES:
            if clean_user is not None and clean_lattice is not None:
                reasons.append(f"{clean_user} may not deploy to {clean_lattice}")

        digest, manifest_size = self._manifest_digest_and_size(manifest, reasons)

        components = manifest.get("components") if isinstance(manifest, dict) else None
        if not isinstance(components, list) or not components:
            reasons.append("manifest has no components")
            components = []
        elif len(components) > self.max_components:
            reasons.append(f"manifest has {len(components)} components; limit is {self.max_components}")

        seen_names: set[str] = set()
        for index, component in enumerate(components[: self.max_components]):
            label = f"component[{index}]"
            if not isinstance(component, dict):
                reasons.append(f"{label}: component must be an object")
                continue

            name = component.get("name")
            clean_name = _clean_identity(name, f"{label}.name", reasons, limit=256)
            if clean_name is not None:
                label = clean_name
                if clean_name in seen_names:
                    reasons.append(f"{clean_name}: duplicate component name")
                seen_names.add(clean_name)

            image = component.get("image")
            if (
                not isinstance(image, str)
                or not image
                or image != image.strip()
                or len(image) > 2048
                or "/" not in image
                or any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in image)
            ):
                reasons.append(f"{label}: malformed image reference")
            else:
                registry = image.split("/", 1)[0].lower()
                if registry not in self.registries:
                    reasons.append(f"{label}: registry {registry} not approved")

            signer = component.get("signer")
            if not isinstance(signer, str) or signer not in self.signers:
                reasons.append(f"{label}: signer {signer!r} not approved")

        decision = {
            "user": clean_user,
            "lattice": clean_lattice,
            "admitted": not reasons,
            "reasons": reasons,
            "manifest_sha256": digest,
            "manifest_bytes": manifest_size,
            "component_count": len(components),
        }

        # Record before forwarding.  The lock keeps audit order and forwarded
        # state coherent under concurrent admission calls.
        with self._lock:
            self._record(decision)
            if not reasons:
                self._forwarded.append(copy.deepcopy(manifest))

        return copy.deepcopy(decision)
