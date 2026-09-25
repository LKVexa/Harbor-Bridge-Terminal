"""G13-MC-005 trusted attribute/context provider and G13-MC-006 request
attribute allowlist/type system.

Protected attributes (tenant, workload, site, environment, identity.*,
attestation.*, residency, classification) can *only* come from a
:class:`TrustedContextProvider`; a caller that supplies one is refused, so a
request can never self-assert privileged policy inputs.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

from .config import Limits
from .errors import AttributeRejected, ContextUnavailable, RequestTooLarge

_NAME = re.compile(r"^[a-z][a-z0-9_]{0,62}(\.[a-z][a-z0-9_]{0,62}){0,3}$")


@dataclass(frozen=True)
class AttrSpec:
    type: str                                   # str | int | bool | list[str]
    protected: bool = False
    max_length: int = 256
    enum: tuple[Any, ...] | None = None
    lowercase: bool = False


DEFAULT_SCHEMA: dict[str, AttrSpec] = {
    "action": AttrSpec("str", lowercase=True, max_length=64),
    "resource": AttrSpec("str", max_length=512),
    "resource_type": AttrSpec("str", lowercase=True, max_length=64),
    "labels": AttrSpec("list[str]", max_length=64),
    "operation_count": AttrSpec("int"),
    "tenant": AttrSpec("str", protected=True, max_length=128),
    "workload": AttrSpec("str", protected=True, max_length=256),
    "site": AttrSpec("str", protected=True, max_length=128),
    "environment": AttrSpec("str", protected=True, max_length=64),
    "residency": AttrSpec("str", protected=True, max_length=32),
    "classification": AttrSpec("str", protected=True, enum=("public", "internal", "confidential", "pii", "secret")),
    "identity.subject": AttrSpec("str", protected=True, max_length=256),
    "identity.kind": AttrSpec("str", protected=True, enum=("human", "service")),
    "attestation.level": AttrSpec("str", protected=True, enum=("none", "software", "hardware")),
}
PROTECTED_PREFIXES = ("identity.", "attestation.")


@dataclass(frozen=True)
class AttributeSchema:
    specs: Mapping[str, AttrSpec] = field(default_factory=lambda: dict(DEFAULT_SCHEMA))
    unknown: str = "reject"

    def is_protected(self, name: str) -> bool:
        spec = self.specs.get(name)
        return (spec is not None and spec.protected) or name.startswith(PROTECTED_PREFIXES)

    def normalise(self, name: str, value: Any) -> Any:
        spec = self.specs[name]
        if spec.type == "str":
            if not isinstance(value, str):
                raise AttributeRejected(f"{name}: expected string")
            value = unicodedata.normalize("NFC", value)
            if any(unicodedata.category(c) in ("Cc", "Cf", "Cs", "Co") for c in value):
                raise AttributeRejected(f"{name}: control/format characters not permitted")
            if spec.lowercase:
                value = value.lower()
            if not value or len(value) > spec.max_length:
                raise AttributeRejected(f"{name}: length out of range")
        elif spec.type == "int":
            if isinstance(value, bool) or not isinstance(value, int) or abs(value) > 2**53 - 1:
                raise AttributeRejected(f"{name}: expected bounded integer")
        elif spec.type == "bool":
            if not isinstance(value, bool):
                raise AttributeRejected(f"{name}: expected boolean")
        elif spec.type == "list[str]":
            if not isinstance(value, list) or len(value) > spec.max_length or \
                    any(not isinstance(v, str) or len(v) > 256 for v in value):
                raise AttributeRejected(f"{name}: expected list of strings")
            value = [unicodedata.normalize("NFC", v) for v in value]
        else:  # pragma: no cover - schema construction error
            raise AttributeRejected(f"{name}: unknown spec type")
        if spec.enum is not None and value not in spec.enum:
            raise AttributeRejected(f"{name}: value not in allowed domain")
        return value


class TrustedContextProvider(Protocol):
    """Adapter contract ``PK_POLICY_CONTEXT/1`` (EXT-03 identity/attestation, EXT-05 topology)."""
    def context(self, principal_subject: str) -> Mapping[str, Any]: ...


@dataclass
class StaticContextProvider:
    """Reference provider: attributes established out-of-band per authenticated subject."""
    table: Mapping[str, Mapping[str, Any]]
    available: bool = True

    def context(self, principal_subject: str) -> Mapping[str, Any]:
        if not self.available:
            raise ContextUnavailable("trusted context provider unavailable")
        ctx = self.table.get(principal_subject)
        if ctx is None:
            raise ContextUnavailable(f"no trusted context for subject")
        return ctx


def build_request(caller: Mapping[str, Any], trusted: Mapping[str, Any], schema: AttributeSchema,
                  limits: Limits) -> dict[str, Any]:
    """Merge caller-supplied and trusted attributes into a validated request."""
    if not isinstance(caller, Mapping):
        raise AttributeRejected("request must be a mapping")
    if len(caller) + len(trusted) > limits.max_request_attributes:
        raise RequestTooLarge("too many request attributes")
    out: dict[str, Any] = {}
    for name, value in caller.items():
        if not isinstance(name, str) or not _NAME.match(name):
            raise AttributeRejected("attribute name invalid")
        if schema.is_protected(name):
            raise AttributeRejected(f"{name}: protected attribute cannot be caller-supplied",
                                    details={"attribute": name})
        if name not in schema.specs:
            if schema.unknown == "reject":
                raise AttributeRejected(f"{name}: unknown attribute", details={"attribute": name})
            continue
        out[name] = schema.normalise(name, value)
    for name, value in trusted.items():
        if name not in schema.specs or not schema.is_protected(name):
            raise AttributeRejected(f"{name}: provider may only supply declared protected attributes")
        out[name] = schema.normalise(name, value)
    size = sum(len(k) + len(repr(v)) for k, v in out.items())
    if size > limits.max_request_bytes:
        raise RequestTooLarge("request too large")
    return out
