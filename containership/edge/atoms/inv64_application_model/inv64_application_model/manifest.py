"""Pure-Python application-manifest validation and canonicalization for INV-64.

This module deliberately has no dependency on ``pk_core`` so the security-
critical parser/validator can be unit-tested in isolation.  Integration with
``pk_core`` remains in :mod:`component` and :mod:`contract`.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Iterable, Mapping

try:
    from .redaction import classify_text, find_secrets
except ImportError:  # loaded by file path (standalone tests): load the sibling module the same way
    import importlib.util as _ilu
    import pathlib as _pl
    import sys as _sys

    _spec = _ilu.spec_from_file_location("inv64_redaction_standalone", _pl.Path(__file__).with_name("redaction.py"))
    _mod = _ilu.module_from_spec(_spec)
    _sys.modules[_spec.name] = _mod
    _spec.loader.exec_module(_mod)
    find_secrets = _mod.find_secrets
    classify_text = _mod.classify_text


def _show(value: Any) -> str:
    """repr() for messages, except credential-like values are never echoed (MC-14)."""
    return "'[REDACTED]'" if isinstance(value, str) and classify_text(value) else repr(value)

SCHEMAS = frozenset({"app/v1"})
SECTION_NAMES = ("components", "providers", "links", "traits")

# Defensive limits.  They bound parser/validator work and make resource
# exhaustion deterministic.  The limits are implementation ceilings, not
# business quotas; callers may impose tighter policy upstream.
MAX_MANIFEST_BYTES = 1_048_576  # 1 MiB encoded JSON
MAX_COMPONENTS = 10_000
MAX_PROVIDERS = 10_000
MAX_LINKS = 50_000
MAX_TRAITS = 50_000
MAX_NAME_LENGTH = 128
MAX_TRAIT_TYPE_LENGTH = 128
MAX_DEPTH = 64  # JSON nesting ceiling; deeper input would reach interpreter recursion limits

_NAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,127})$")


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """Machine-readable validation result."""

    code: str
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}" if self.path else self.message


class ManifestValidationError(ValueError):
    """Raised when an operation requires a valid manifest but validation fails."""

    def __init__(self, issues: Iterable[ValidationIssue]):
        self.issues = tuple(issues)
        super().__init__("; ".join(str(issue) for issue in self.issues))


class DuplicateKeyError(ValueError):
    """Raised when raw JSON contains a duplicate object key."""

    code = "manifest.duplicate_key"


class ManifestTooLargeError(ValueError):
    """Raised when raw JSON exceeds :data:`MAX_MANIFEST_BYTES`."""

    code = "manifest.too_large"


class ManifestDepthError(ValueError):
    """Raised when JSON nesting exceeds :data:`MAX_DEPTH` (4.3.0: previously a RecursionError)."""

    code = "manifest.too_deep"


def _raw_depth_exceeds(text: str, limit: int) -> bool:
    """Linear scan of bracket depth outside string literals (no recursion)."""
    depth = 0
    in_str = False
    esc = False
    for ch in text:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in "[{":
            depth += 1
            if depth > limit:
                return True
        elif ch in "]}":
            depth -= 1
    return False


def _value_depth_exceeds(value: Any, limit: int) -> bool:
    stack = [(value, 1)]
    while stack:
        v, d = stack.pop()
        if isinstance(v, (dict, list)):
            if d > limit:
                return True
            children = v.values() if isinstance(v, dict) else v
            stack.extend((c, d + 1) for c in children if isinstance(c, (dict, list)))
    return False


def _pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise DuplicateKeyError(f"duplicate JSON object key {key!r}")
        out[key] = value
    return out


def _is_valid_name(value: Any) -> bool:
    return isinstance(value, str) and len(value) <= MAX_NAME_LENGTH and bool(_NAME_RE.fullmatch(value))


def _is_valid_trait_type(value: Any) -> bool:
    return isinstance(value, str) and 0 < len(value) <= MAX_TRAIT_TYPE_LENGTH and bool(_NAME_RE.fullmatch(value))


def _safe_sections(manifest: Mapping[str, Any], issues: list[ValidationIssue]) -> dict[str, list[dict[str, Any]]]:
    """Return well-typed sections while collecting every top-level section error."""
    limits = {
        "components": MAX_COMPONENTS,
        "providers": MAX_PROVIDERS,
        "links": MAX_LINKS,
        "traits": MAX_TRAITS,
    }
    sections: dict[str, list[dict[str, Any]]] = {}
    for key in SECTION_NAMES:
        value = manifest.get(key, [])
        if not isinstance(value, list):
            issues.append(ValidationIssue("section.type", key, "must be a list of mappings"))
            sections[key] = []
            continue
        if len(value) > limits[key]:
            issues.append(
                ValidationIssue(
                    "section.limit",
                    key,
                    f"contains {len(value)} entries; limit is {limits[key]}",
                )
            )
        typed: list[dict[str, Any]] = []
        # Cap work for callers that hand us an already-decoded object. Raw JSON
        # callers are additionally protected by MAX_MANIFEST_BYTES.
        for index, item in enumerate(value[: limits[key]]):
            if not isinstance(item, dict):
                issues.append(ValidationIssue("entry.type", f"{key}[{index}]", "must be a mapping"))
                continue
            typed.append(item)
        sections[key] = typed
    return sections


def validate_issues(manifest: Any) -> list[ValidationIssue]:
    """Validate a decoded manifest and return all detectable issues.

    Validation is intentionally non-throwing for ordinary malformed input so a
    submitter receives the complete refusal set in one response.
    """
    issues: list[ValidationIssue] = []
    if not isinstance(manifest, dict):
        return [
            ValidationIssue(
                "manifest.type",
                "",
                f"manifest must be a mapping, got {type(manifest).__name__}",
            )
        ]

    if _value_depth_exceeds(manifest, MAX_DEPTH):
        return [ValidationIssue("manifest.too_deep", "", f"nesting exceeds {MAX_DEPTH} levels")]

    schema = manifest.get("schema")
    if not isinstance(schema, str):
        issues.append(ValidationIssue("schema.type", "schema", "must be a string"))
    elif schema not in SCHEMAS:
        issues.append(ValidationIssue("schema.unsupported", "schema", f"unsupported schema {_show(schema)}"))

    sections = _safe_sections(manifest, issues)

    components: list[str] = []
    providers: list[str] = []
    for key, sink in (("components", components), ("providers", providers)):
        for index, item in enumerate(sections[key]):
            name = item.get("name")
            if not _is_valid_name(name):
                issues.append(
                    ValidationIssue(
                        "name.invalid",
                        f"{key}[{index}].name",
                        f"must match {_NAME_RE.pattern!r} and be at most {MAX_NAME_LENGTH} characters",
                    )
                )
                continue
            sink.append(name)

    all_names = components + providers
    for name, count in sorted(Counter(all_names).items()):
        if count > 1:
            issues.append(ValidationIssue("name.duplicate", "", f"duplicate name {_show(name)}"))

    component_set = set(components)
    target_set = set(all_names)

    for index, link in enumerate(sections["links"]):
        source = link.get("from")
        target = link.get("to")
        if not _is_valid_name(source):
            issues.append(ValidationIssue("link.from.invalid", f"links[{index}].from", "must be a valid component name"))
        elif source not in component_set:
            issues.append(
                ValidationIssue(
                    "link.from.undeclared",
                    f"links[{index}].from",
                    f"undeclared component {_show(source)}",
                )
            )
        if not _is_valid_name(target):
            issues.append(ValidationIssue("link.to.invalid", f"links[{index}].to", "must be a valid component or provider name"))
        elif target not in target_set:
            issues.append(
                ValidationIssue(
                    "link.to.undeclared",
                    f"links[{index}].to",
                    f"undeclared target {_show(target)}",
                )
            )

    for index, trait in enumerate(sections["traits"]):
        component = trait.get("component")
        trait_type = trait.get("type")
        if not _is_valid_trait_type(trait_type):
            issues.append(
                ValidationIssue(
                    "trait.type.invalid",
                    f"traits[{index}].type",
                    "must be a non-empty identifier",
                )
            )
        if not _is_valid_name(component):
            issues.append(
                ValidationIssue(
                    "trait.component.invalid",
                    f"traits[{index}].component",
                    "must be a valid component name",
                )
            )
        elif component not in component_set:
            issues.append(
                ValidationIssue(
                    "trait.component.undeclared",
                    f"traits[{index}].component",
                    f"undeclared component {_show(component)}",
                )
            )

    # MC-14: inline secret material is refused wherever it appears, including
    # extension fields. Only the path and a pattern class are reported, never the value.
    for path, reason in find_secrets(manifest):
        issues.append(ValidationIssue("secret.inline", path, f"inline secret material ({reason}); use secretref://"))

    return issues


def validate(manifest: Any) -> list[str]:
    """Backward-compatible string error API."""
    return [str(issue) for issue in validate_issues(manifest)]


def parse_manifest_json(raw: str | bytes | bytearray) -> dict[str, Any]:
    """Decode untrusted JSON, reject duplicate keys, and validate it.

    A :class:`ManifestValidationError` carries all semantic issues.  Syntax,
    duplicate-key, encoding and resource-limit errors are raised directly as
    ``ValueError`` subclasses.
    """
    if isinstance(raw, str):
        encoded = raw.encode("utf-8")
        text = raw
    elif isinstance(raw, (bytes, bytearray)):
        encoded = bytes(raw)
        text = encoded.decode("utf-8")
    else:
        raise TypeError("raw manifest must be str, bytes, or bytearray")

    if len(encoded) > MAX_MANIFEST_BYTES:
        raise ManifestTooLargeError(f"manifest is {len(encoded)} bytes; limit is {MAX_MANIFEST_BYTES}")
    if _raw_depth_exceeds(text, MAX_DEPTH):
        raise ManifestDepthError(f"manifest nesting exceeds {MAX_DEPTH} levels")

    value = json.loads(
        text,
        object_pairs_hook=_pairs_without_duplicates,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON number {value!r} is not allowed")),
    )
    issues = validate_issues(value)
    if issues:
        raise ManifestValidationError(issues)
    return value


def _json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_document(manifest: Any) -> bytes:
    """Return deterministic canonical JSON bytes for a valid manifest.

    The input object is never mutated.  Ordering of the four set-like manifest
    sections is normalized; ordering inside arbitrary extension values remains
    meaningful unless their defining schema says otherwise.
    """
    issues = validate_issues(manifest)
    if issues:
        raise ManifestValidationError(issues)

    # JSON round-trip creates a deep copy while also refusing non-serializable
    # objects and non-finite floats.  It preserves all extension fields.
    copied = json.loads(_json_bytes(manifest).decode("utf-8"))
    for key in SECTION_NAMES:
        copied[key] = sorted(copied.get(key, []), key=_json_bytes)
    return _json_bytes(copied)


def canonical(manifest: Any) -> str:
    """Return the SHA-256 digest of :func:`canonical_document`."""
    return hashlib.sha256(canonical_document(manifest)).hexdigest()
