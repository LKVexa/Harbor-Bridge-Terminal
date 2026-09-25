"""Hardened in-memory container image identity and integrity primitives.

This module is intentionally stdlib-only so its integrity model can be tested even
when the surrounding ``pk_core`` conformance framework is not installed.  It is a
reference/content-addressed registry model, not an OCI registry or container runtime.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
from dataclasses import dataclass, field
from typing import Iterable

DIGEST_ALGORITHM = "sha256"
MANIFEST_MEDIA_TYPE = "application/vnd.pk.image.manifest.v1+json"
_DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
_TAG_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}\Z")
_ENV_RE = re.compile(r"[a-z0-9][a-z0-9_.-]{0,63}\Z")


class RegistryError(Exception):
    """Base class for registry-model failures."""


class ValidationError(RegistryError, ValueError):
    """Raised when a caller supplies an invalid name, tag, environment, or payload."""


class IntegrityError(RegistryError, ValueError):
    """Raised when stored bytes do not match their content identity or manifest."""


class MutableTagRefused(RegistryError, ValueError):
    """Raised when a mutable tag is used in an immutable-tag environment."""


class UnknownReference(RegistryError, LookupError):
    """Raised when a tag or digest is not present in the registry."""


class LimitExceeded(RegistryError, ValueError):
    """Raised when a configured resource limit is exceeded."""


class QuarantinedDigest(RegistryError, PermissionError):
    """Raised when a quarantined manifest or layer is selected."""


@dataclass(frozen=True)
class Limits:
    """Resource ceilings for untrusted registry inputs.

    Defaults are deliberately generous for a reference model while still preventing
    accidental/unbounded list and metadata growth.  Deployments should supply values
    appropriate to their actual registry and runtime.
    """

    max_layers_per_image: int = 512
    max_layer_bytes: int = 4 * 1024 * 1024 * 1024
    max_image_bytes: int = 32 * 1024 * 1024 * 1024
    max_manifest_bytes: int = 4 * 1024 * 1024
    max_reference_length: int = 2048
    max_resolution_records: int = 4096
    max_provenance_records: int = 4096

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValidationError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class ProvenanceRecord:
    """A bounded, in-memory record of a tag update performed by ``push``."""

    sequence: int
    name: str
    tag: str
    manifest_digest: str
    layer_digests: tuple[str, ...]
    previous_manifest_digest: str | None


@dataclass(frozen=True)
class ParsedReference:
    """Normalized representation of an image reference."""

    kind: str  # "tag" or "digest"
    name: str | None
    tag: str | None
    digest: str | None


def digest(data: bytes | bytearray | memoryview) -> str:
    """Return the canonical SHA-256 content digest for bytes-like input."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise ValidationError("digest input must be bytes-like")
    return f"{DIGEST_ALGORITHM}:" + hashlib.sha256(bytes(data)).hexdigest()


def _validate_digest(value: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValidationError(f"invalid digest: {value!r}")
    return value


def _validate_name(name: str) -> str:
    if not isinstance(name, str):
        raise ValidationError("image name must be a string")
    if not name or len(name) > 1024:
        raise ValidationError("image name must contain 1..1024 characters")
    if name != name.strip() or "@" in name:
        raise ValidationError("image name contains forbidden whitespace or '@'")
    if name.startswith("/") or name.endswith("/") or "//" in name:
        raise ValidationError("image name has an invalid path shape")
    if any(ord(ch) < 33 or ord(ch) == 127 for ch in name):
        raise ValidationError("image name contains control or whitespace characters")
    return name


def _validate_tag(tag: str) -> str:
    if not isinstance(tag, str) or not _TAG_RE.fullmatch(tag):
        raise ValidationError(f"invalid image tag: {tag!r}")
    return tag


def _normalize_environment(environment: str) -> str:
    if not isinstance(environment, str):
        raise ValidationError("environment must be a string")
    normalized = environment.strip().lower()
    if not _ENV_RE.fullmatch(normalized):
        raise ValidationError(f"invalid environment: {environment!r}")
    return normalized


def parse_reference(reference: str, *, max_length: int = 2048) -> ParsedReference:
    """Parse a tag, named digest, or bare digest reference without ambiguity."""
    if not isinstance(reference, str):
        raise ValidationError("reference must be a string")
    if not reference or reference != reference.strip() or len(reference) > max_length:
        raise ValidationError("reference is empty, padded with whitespace, or too long")

    if _DIGEST_RE.fullmatch(reference):
        return ParsedReference("digest", None, None, reference)

    if "@" in reference:
        if reference.count("@") != 1:
            raise ValidationError(f"invalid digest reference: {reference!r}")
        name, manifest_digest = reference.split("@", 1)
        _validate_name(name)
        _validate_digest(manifest_digest)
        return ParsedReference("digest", name, None, manifest_digest)

    # The final ':' is the tag separator only when it occurs after the final '/'.
    # This keeps registry ports such as registry.example:5000/team/image valid.
    colon = reference.rfind(":")
    slash = reference.rfind("/")
    if colon <= slash:
        raise ValidationError(f"tagged reference required: {reference!r}")
    name, tag = reference[:colon], reference[colon + 1 :]
    _validate_name(name)
    _validate_tag(tag)
    return ParsedReference("tag", name, tag, None)


@dataclass
class Registry:
    """Thread-safe, content-addressed in-memory registry reference model.

    Public ``blobs`` and ``tags`` mappings are intentionally retained for compatibility
    with the original test fixture.  Production code should not expose mutable backing
    stores this way; see ``MISSING_COMPONENTS.md``.
    """

    blobs: dict[str, bytes] = field(default_factory=dict)
    tags: dict[str, str] = field(default_factory=dict)
    resolutions: list[tuple[str, str, str]] = field(default_factory=list)
    provenance: list[ProvenanceRecord] = field(default_factory=list)
    quarantined: dict[str, str] = field(default_factory=dict)
    limits: Limits = field(default_factory=Limits)
    immutable_tag_environments: frozenset[str] = field(
        default_factory=lambda: frozenset({"prod", "production"})
    )
    _manifest_digests: set[str] = field(default_factory=set, init=False, repr=False)
    _sequence: int = field(default=0, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    def __post_init__(self) -> None:
        normalized: set[str] = set()
        for env in self.immutable_tag_environments:
            normalized.add(_normalize_environment(env))
        self.immutable_tag_environments = frozenset(normalized)
        if not isinstance(self.limits, Limits):
            raise ValidationError("limits must be a Limits instance")

    def _bounded_append(self, target: list, value: object, maximum: int) -> None:
        target.append(value)
        overflow = len(target) - maximum
        if overflow > 0:
            del target[:overflow]

    def _assert_not_quarantined(self, manifest_or_layer_digest: str) -> None:
        if manifest_or_layer_digest in self.quarantined:
            reason = self.quarantined[manifest_or_layer_digest]
            raise QuarantinedDigest(
                f"{manifest_or_layer_digest}: quarantined ({reason})"
            )

    def push(self, name: str, tag: str, layers: Iterable[bytes | bytearray | memoryview]) -> str:
        """Store an image manifest and atomically move ``name:tag`` to it.

        Layers are content-addressed and de-duplicated.  Re-pushing valid bytes heals a
        backing blob that has been corrupted under the same digest key in this model.
        """
        _validate_name(name)
        _validate_tag(tag)
        if isinstance(layers, (bytes, bytearray, memoryview, str)):
            raise ValidationError("layers must be an iterable of bytes-like layer payloads")

        materialized: list[bytes] = []
        total_bytes = 0
        for index, layer in enumerate(layers):
            if index >= self.limits.max_layers_per_image:
                raise LimitExceeded(
                    f"image exceeds {self.limits.max_layers_per_image} layers"
                )
            if not isinstance(layer, (bytes, bytearray, memoryview)):
                raise ValidationError(f"layer {index} is not bytes-like")
            payload = bytes(layer)
            if len(payload) > self.limits.max_layer_bytes:
                raise LimitExceeded(
                    f"layer {index} exceeds {self.limits.max_layer_bytes} bytes"
                )
            total_bytes += len(payload)
            if total_bytes > self.limits.max_image_bytes:
                raise LimitExceeded(
                    f"image exceeds {self.limits.max_image_bytes} bytes"
                )
            materialized.append(payload)

        if not materialized:
            raise ValidationError("an image must contain at least one layer")

        layer_entries: list[dict[str, object]] = []
        layer_digests: list[str] = []
        for payload in materialized:
            layer_digest = digest(payload)
            layer_entries.append({"digest": layer_digest, "size": len(payload)})
            layer_digests.append(layer_digest)

        manifest = json.dumps(
            {
                "schemaVersion": 1,
                "mediaType": MANIFEST_MEDIA_TYPE,
                "layers": layer_entries,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(manifest) > self.limits.max_manifest_bytes:
            raise LimitExceeded(
                f"manifest exceeds {self.limits.max_manifest_bytes} bytes"
            )
        manifest_digest = digest(manifest)
        tag_ref = f"{name}:{tag}"

        with self._lock:
            for layer_digest, payload in zip(layer_digests, materialized, strict=True):
                existing = self.blobs.get(layer_digest)
                if (
                    existing is None
                    or not isinstance(existing, bytes)
                    or digest(existing) != layer_digest
                ):
                    self.blobs[layer_digest] = payload
            self.blobs[manifest_digest] = manifest
            self._manifest_digests.add(manifest_digest)

            previous = self.tags.get(tag_ref)
            self.tags[tag_ref] = manifest_digest
            self._sequence += 1
            self._bounded_append(
                self.provenance,
                ProvenanceRecord(
                    sequence=self._sequence,
                    name=name,
                    tag=tag,
                    manifest_digest=manifest_digest,
                    layer_digests=tuple(layer_digests),
                    previous_manifest_digest=previous,
                ),
                self.limits.max_provenance_records,
            )
        return manifest_digest

    def resolve(self, ref: str, env: str) -> str:
        """Resolve a reference to a known, non-quarantined manifest digest.

        Mutable tags are rejected for protected environments after normalized matching,
        closing case/whitespace/``prod`` bypasses in the prior implementation.
        """
        environment = _normalize_environment(env)
        parsed = parse_reference(ref, max_length=self.limits.max_reference_length)

        with self._lock:
            if parsed.kind == "digest":
                resolved = parsed.digest
                if resolved is None:  # defensive invariant; parser guarantees a digest here
                    raise IntegrityError("parsed digest reference has no digest")
            else:
                if environment in self.immutable_tag_environments:
                    raise MutableTagRefused(
                        f"{ref}: {environment} requires a digest reference"
                    )
                tag_ref = f"{parsed.name}:{parsed.tag}"
                resolved = self.tags.get(tag_ref)
                if resolved is None:
                    raise UnknownReference(f"{ref}: no such tag")

            if resolved not in self.blobs:
                raise UnknownReference(f"{resolved}: no such manifest")
            self._assert_not_quarantined(resolved)
            manifest = self.blobs[resolved]
            if not isinstance(manifest, bytes):
                raise IntegrityError("resolved manifest backing value is not bytes")
            if digest(manifest) != resolved:
                raise IntegrityError("resolved manifest does not match its digest")
            self._parse_manifest(manifest)
            self._bounded_append(
                self.resolutions,
                (ref, environment, resolved),
                self.limits.max_resolution_records,
            )
            return resolved

    def _parse_manifest(self, manifest: bytes) -> list[tuple[str, int | None]]:
        if len(manifest) > self.limits.max_manifest_bytes:
            raise IntegrityError("manifest exceeds configured size limit")
        try:
            doc = json.loads(manifest.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise IntegrityError("manifest is not valid UTF-8 JSON") from exc
        if not isinstance(doc, dict):
            raise IntegrityError("manifest root must be an object")

        entries = doc.get("layers")
        if not isinstance(entries, list) or not entries:
            raise IntegrityError("manifest must contain a non-empty layers array")
        if len(entries) > self.limits.max_layers_per_image:
            raise IntegrityError("manifest exceeds configured layer-count limit")

        # Backward-compatible parsing for v4.1.0 manifests: {"layers": ["sha256:..."]}.
        legacy = all(isinstance(entry, str) for entry in entries)
        if not legacy:
            if doc.get("schemaVersion") != 1 or doc.get("mediaType") != MANIFEST_MEDIA_TYPE:
                raise IntegrityError("manifest schemaVersion/mediaType is unsupported")

        parsed: list[tuple[str, int | None]] = []
        for index, entry in enumerate(entries):
            if legacy:
                layer_digest = entry
                size = None
            else:
                if not isinstance(entry, dict):
                    raise IntegrityError(f"layer descriptor {index} must be an object")
                layer_digest = entry.get("digest")
                size = entry.get("size")
                if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                    raise IntegrityError(f"layer descriptor {index} has invalid size")
                if size > self.limits.max_layer_bytes:
                    raise IntegrityError(f"layer descriptor {index} exceeds layer-size limit")
            try:
                _validate_digest(layer_digest)
            except ValidationError as exc:
                raise IntegrityError(f"layer descriptor {index} has invalid digest") from exc
            parsed.append((layer_digest, size))
        return parsed

    def pull(self, manifest_digest: str) -> list[bytes]:
        """Verify a manifest and every referenced layer before returning payloads."""
        try:
            _validate_digest(manifest_digest)
        except ValidationError as exc:
            raise UnknownReference(str(exc)) from exc

        with self._lock:
            if manifest_digest not in self.blobs:
                raise UnknownReference(f"{manifest_digest}: no such manifest")
            self._assert_not_quarantined(manifest_digest)
            manifest = self.blobs[manifest_digest]
            if not isinstance(manifest, bytes):
                raise IntegrityError("manifest backing value is not bytes")
            if digest(manifest) != manifest_digest:
                raise IntegrityError("manifest does not match its digest")

            descriptors = self._parse_manifest(manifest)
            out: list[bytes] = []
            total_bytes = 0
            for layer_digest, expected_size in descriptors:
                self._assert_not_quarantined(layer_digest)
                payload = self.blobs.get(layer_digest)
                if payload is None:
                    raise IntegrityError(f"layer {layer_digest[:19]} missing")
                if not isinstance(payload, bytes):
                    raise IntegrityError(f"layer {layer_digest[:19]} backing value is not bytes")
                if digest(payload) != layer_digest:
                    raise IntegrityError(f"layer {layer_digest[:19]} corrupted")
                if expected_size is not None and len(payload) != expected_size:
                    raise IntegrityError(f"layer {layer_digest[:19]} size mismatch")
                total_bytes += len(payload)
                if total_bytes > self.limits.max_image_bytes:
                    raise IntegrityError("image exceeds configured total-size limit")
                out.append(payload)
            return out

    def quarantine(self, content_digest: str, reason: str) -> None:
        """Fail closed for a known manifest/layer until explicitly released."""
        _validate_digest(content_digest)
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 1024:
            raise ValidationError("quarantine reason must contain 1..1024 characters")
        with self._lock:
            if content_digest not in self.blobs:
                raise UnknownReference(f"{content_digest}: no such content")
            self.quarantined[content_digest] = reason.strip()

    def release_quarantine(self, content_digest: str) -> None:
        """Remove a quarantine marker for known content."""
        _validate_digest(content_digest)
        with self._lock:
            if content_digest not in self.blobs:
                raise UnknownReference(f"{content_digest}: no such content")
            self.quarantined.pop(content_digest, None)

    def stats(self) -> dict[str, int]:
        """Return bounded operational counters for the in-memory model."""
        with self._lock:
            manifest_digests = self._manifest_digests.intersection(self.blobs)
            return {
                "blob_count": len(self.blobs),
                "manifest_count": len(manifest_digests),
                "layer_blob_count": len(self.blobs) - len(manifest_digests),
                "tag_count": len(self.tags),
                "resolution_records": len(self.resolutions),
                "provenance_records": len(self.provenance),
                "quarantined_count": len(self.quarantined),
                "stored_bytes": sum(len(value) for value in self.blobs.values() if isinstance(value, bytes)),
            }
