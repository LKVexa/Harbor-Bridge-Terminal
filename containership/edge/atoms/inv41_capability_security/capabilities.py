"""Standalone capability primitives for INV-41.

This module intentionally has no dependency on ``pk_core`` so the security
properties can be tested even when the estate integration package is absent.

Security boundary
-----------------
The primitives eliminate *API-level* ambient authority: a Holder receives an
immutable set of sealed references from an explicit Authority domain, and a
reference can only be attenuated.  They are not a sandbox against arbitrary
hostile Python/native code executing in the same interpreter.  Such code can
use introspection or memory-corruption techniques outside Python's object model;
run adversarial workloads behind a language/runtime, process, VM, or hardware
isolation boundary.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import weakref
from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Final

REFERENCE_SCHEMA: Final[str] = "PK_REFERENCE/1"
MEMBRANE_SCHEMA: Final[str] = "PK_MEMBRANE/1"


# Hard limits (REQ-LIM-*).  Violations are rejected before any seal/HMAC work.
MAX_IDENTIFIER_LENGTH: Final[int] = 256
MAX_OPERATIONS: Final[int] = 256
MAX_POLICY_RESOURCES: Final[int] = 4096
MAX_HOLDER_ENTRIES: Final[int] = 1024
MAX_MEMBRANE_DEPTH: Final[int] = 32


class CapabilityError(PermissionError):
    """Base class for capability-security refusals."""

    code = "INV41-E000"
    outcome = "denied"


class Forged(CapabilityError):
    """Raised when a reference is untrusted, malformed, or was not held."""

    code = "INV41-E001"


class Widening(CapabilityError):
    """Raised when an attenuation or grant asks for authority not available."""

    code = "INV41-E002"


class Revoked(CapabilityError):
    """Raised when a reference behind a revoked membrane is used or delegated."""

    code = "INV41-E003"
    outcome = "revoked"


class InvalidGrant(CapabilityError):
    """Raised when an authority is asked to grant an unknown resource."""

    code = "INV41-E004"


class CrossAuthority(CapabilityError):
    """Raised when a reference is introduced into another authority domain."""

    code = "INV41-E005"


class LimitExceeded(CapabilityError, ValueError):
    """Raised when a request exceeds a documented hard limit (fails closed)."""

    code = "INV41-E006"
    outcome = "invalid"


def _no_serialize(self, *_args):
    raise TypeError(f"{type(self).__name__} objects are process-local and intentionally non-serializable")


def _validate_identifier(value, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{what} must be a non-empty string")
    if len(value) > MAX_IDENTIFIER_LENGTH:
        raise LimitExceeded(f"{what} exceeds {MAX_IDENTIFIER_LENGTH} characters")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError(f"{what} must not contain control characters")
    return value


_MINT_GUARD = object()


def _normalize_operations(operations: Iterable[str], *, allow_empty: bool = True) -> frozenset[str]:
    if isinstance(operations, (str, bytes)):
        raise TypeError("operations must be an iterable of operation names, not a string")
    items = []
    try:
        for op in operations:
            if len(items) >= MAX_OPERATIONS:
                raise LimitExceeded(f"operation set exceeds {MAX_OPERATIONS} entries")
            # Type-check before hashing so hostile __hash__/__eq__ objects never enter a set.
            if type(op) is not str:
                raise ValueError("operation names must be non-empty strings")
            items.append(op)
    except TypeError as exc:
        raise TypeError("operations must be an iterable of hashable strings") from exc
    result = frozenset(items)
    if not allow_empty and not result:
        raise ValueError("at least one operation is required")
    for op in result:
        _validate_identifier(op, "operation name")
    return result


def _validate_resource(resource: str) -> str:
    if type(resource) is not str:
        raise ValueError("resource must be a non-empty string")
    return _validate_identifier(resource, "resource")


def _signature(seal: bytes, authority_id: str, token: str, resource: str, operations: frozenset[str]) -> str:
    # Length-prefix every field to avoid delimiter ambiguity.
    parts = [authority_id, token, resource, *sorted(operations)]
    payload = b"".join(len(part.encode("utf-8")).to_bytes(4, "big") + part.encode("utf-8") for part in parts)
    return hmac.new(seal, payload, hashlib.sha256).hexdigest()


class Reference:
    """Opaque, sealed, process-local authority to one resource.

    Direct construction is rejected.  References are minted only by an
    :class:`Authority` or by attenuation of an already authentic reference.
    """

    __slots__ = (
        "_authority_id", "_authority_seal", "_resource", "_operations", "_token", "_signature",
        "_membranes", "_sealed", "__weakref__",
    )

    def __init__(
        self,
        authority_id: str,
        authority_seal: bytes,
        resource: str,
        operations: frozenset[str],
        token: str,
        signature: str,
        membranes: tuple["Membrane", ...] = (),
        *,
        _guard=None,
    ) -> None:
        if _guard is not _MINT_GUARD:
            raise Forged("Reference objects cannot be constructed directly; obtain one from Authority.grant()")
        object.__setattr__(self, "_authority_id", authority_id)
        object.__setattr__(self, "_authority_seal", authority_seal)
        object.__setattr__(self, "_resource", resource)
        object.__setattr__(self, "_operations", operations)
        object.__setattr__(self, "_token", token)
        object.__setattr__(self, "_signature", signature)
        object.__setattr__(self, "_membranes", membranes)
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name, value) -> None:  # pragma: no cover - defensive path
        if getattr(self, "_sealed", False):
            raise AttributeError("Reference objects are immutable")
        object.__setattr__(self, name, value)

    @property
    def authority_id(self) -> str:
        return self._authority_id

    @property
    def resource(self) -> str:
        return self._resource

    @property
    def operations(self) -> frozenset[str]:
        return self._operations

    @property
    def token(self) -> str:
        """Opaque identifier for correlation; it is not sufficient to mint authority."""
        return self._token

    @property
    def membranes(self) -> tuple["Membrane", ...]:
        return self._membranes

    def _assert_authentic(self) -> None:
        expected = _signature(self._authority_seal, self._authority_id, self._token, self._resource, self._operations)
        if not hmac.compare_digest(self._signature, expected):
            raise Forged(f"{self._resource}: reference seal verification failed")

    def _assert_authority(self, authority_id: str, authority_seal: bytes) -> None:
        self._assert_authentic()
        if self._authority_id != authority_id or not hmac.compare_digest(self._authority_seal, authority_seal):
            raise CrossAuthority(f"{self._resource}: reference belongs to a different authority domain")

    def _assert_live(self) -> None:
        for membrane in self._membranes:
            membrane._assert_live(self._resource)

    def attenuate(self, operations: Iterable[str]) -> "Reference":
        self._assert_authentic()
        self._assert_live()
        requested = _normalize_operations(operations)
        if not requested <= self._operations:
            raise Widening(
                f"{self._resource}: {sorted(requested - self._operations)} exceeds the held authority"
            )
        return _mint_reference(self._authority_id, self._authority_seal, self._resource, requested, self._membranes)

    def invoke(self, operation: str) -> dict:
        self._assert_authentic()
        self._assert_live()
        if not isinstance(operation, str) or not operation.strip():
            raise ValueError("operation must be a non-empty string")
        if operation not in self._operations:
            raise Forged(f"{self._resource}: {operation!r} is not in this reference's authority")
        return {
            "schema": REFERENCE_SCHEMA,
            "authority": self._authority_id,
            "resource": self._resource,
            "operation": operation,
            "permitted": True,
        }

    def __reduce__(self):
        raise TypeError("capability references are process-local and intentionally non-serializable")

    __reduce_ex__ = _no_serialize
    __copy__ = _no_serialize
    __deepcopy__ = _no_serialize

    def __repr__(self) -> str:
        return (
            f"Reference(authority_id={self._authority_id!r}, resource={self._resource!r}, "
            f"operations={sorted(self._operations)!r}, token='<redacted>', membranes={len(self._membranes)})"
        )


class Membrane:
    """Revocable membrane shared by every wrapped/derived reference behind it."""

    __slots__ = ("name", "_revoked", "_refs", "_lock")

    def __init__(self, name: str) -> None:
        self.name = _validate_identifier(name, "membrane name")
        self._revoked = False
        self._refs: weakref.WeakSet[Reference] = weakref.WeakSet()
        self._lock = threading.RLock()

    @property
    def revoked(self) -> bool:
        with self._lock:
            return self._revoked

    @property
    def live_reference_count(self) -> int:
        with self._lock:
            return len(self._refs)

    def _register(self, reference: Reference) -> None:
        with self._lock:
            if self._revoked:
                raise Revoked(f"membrane {self.name} has been revoked")
            self._refs.add(reference)

    def _assert_live(self, resource: str) -> None:
        with self._lock:
            if self._revoked:
                raise Revoked(f"{resource}: membrane {self.name} has been revoked")

    def wrap(self, reference: Reference) -> Reference:
        if not isinstance(reference, Reference):
            raise TypeError("wrap expects a Reference")
        reference._assert_authentic()
        reference._assert_live()
        self._assert_live(reference.resource)
        # Identity de-duplication prevents accidental double wrapping by the same membrane.
        chain = (self,) + tuple(m for m in reference.membranes if m is not self)
        if len(chain) > MAX_MEMBRANE_DEPTH:
            raise LimitExceeded(f"membrane nesting exceeds {MAX_MEMBRANE_DEPTH}")
        return _mint_reference(reference.authority_id, reference._authority_seal, reference.resource, reference.operations, chain)

    def revoke(self) -> dict:
        with self._lock:
            self._revoked = True
            killed = len(self._refs)
        return {
            "schema": MEMBRANE_SCHEMA,
            "membrane": self.name,
            "revoked": True,
            "references_killed": killed,
        }

    __reduce__ = _no_serialize
    __reduce_ex__ = _no_serialize
    __copy__ = _no_serialize
    __deepcopy__ = _no_serialize

    def __repr__(self) -> str:
        return f"Membrane(name={self.name!r}, revoked={self.revoked})"


class Authority:
    """Explicit root minting capability for one isolated authority domain.

    Constructing an Authority creates a *new* independent trust domain; it does
    not grant access to resources controlled by another Authority.  The policy is
    immutable after construction.
    """

    __slots__ = ("_authority_id", "_authority_seal", "_policy", "_sealed")

    def __init__(self, policy: Mapping[str, Iterable[str]], *, authority_id: str | None = None) -> None:
        if not isinstance(policy, Mapping) or not policy:
            raise ValueError("policy must be a non-empty mapping of resource -> operations")
        if len(policy) > MAX_POLICY_RESOURCES:
            raise LimitExceeded(f"policy exceeds {MAX_POLICY_RESOURCES} resources")
        normalized: dict[str, frozenset[str]] = {}
        for resource, operations in policy.items():
            resource = _validate_resource(resource)
            normalized[resource] = _normalize_operations(operations, allow_empty=False)
        aid = secrets.token_urlsafe(18) if authority_id is None else authority_id
        _validate_identifier(aid, "authority_id")
        object.__setattr__(self, "_authority_id", aid)
        object.__setattr__(self, "_authority_seal", secrets.token_bytes(32))
        object.__setattr__(self, "_policy", MappingProxyType(normalized))
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name, value) -> None:  # pragma: no cover - defensive path
        if getattr(self, "_sealed", False):
            raise AttributeError("Authority bootstrap policy and domain identity are immutable")
        object.__setattr__(self, name, value)

    __reduce__ = _no_serialize
    __reduce_ex__ = _no_serialize
    __copy__ = _no_serialize
    __deepcopy__ = _no_serialize

    def __repr__(self) -> str:
        return f"Authority(authority_id={self._authority_id!r}, resources={len(self._policy)}, seal='<redacted>')"

    @property
    def authority_id(self) -> str:
        return self._authority_id

    @property
    def policy(self) -> Mapping[str, frozenset[str]]:
        return self._policy

    def grant(self, resource: str, operations: Iterable[str] | None = None) -> Reference:
        resource = _validate_resource(resource)
        allowed = self._policy.get(resource)
        if allowed is None:
            raise InvalidGrant(f"{resource}: not declared in this authority domain")
        requested = allowed if operations is None else _normalize_operations(operations)
        if not requested <= allowed:
            raise Widening(f"{resource}: {sorted(requested - allowed)} exceeds bootstrap policy")
        return _mint_reference(self._authority_id, self._authority_seal, resource, requested, ())

    def bind_holder(self, name: str, held: Mapping[str, Reference] | None = None) -> "Holder":
        _validate_identifier(name, "holder name")
        if held is not None and not isinstance(held, Mapping):
            raise TypeError("held must be a mapping of alias -> Reference")
        entries = dict(held or {})
        if len(entries) > MAX_HOLDER_ENTRIES:
            raise LimitExceeded(f"holder exceeds {MAX_HOLDER_ENTRIES} entries")
        for alias, reference in entries.items():
            _validate_identifier(alias, "holder alias")
            if not isinstance(reference, Reference):
                raise TypeError(f"{alias}: holder entries must be Reference objects")
            reference._assert_authority(self._authority_id, self._authority_seal)
            reference._assert_live()
        return Holder(name, self._authority_id, self._authority_seal, entries, _guard=_MINT_GUARD)


class Holder:
    """Immutable set of explicitly supplied capabilities for one component."""

    __slots__ = ("_name", "_authority_id", "_authority_seal", "_held", "_sealed")

    def __init__(self, name: str, authority_id: str, authority_seal: bytes, held: Mapping[str, Reference], *, _guard=None) -> None:
        if _guard is not _MINT_GUARD:
            raise Forged("Holder objects must be bound by Authority.bind_holder()")
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_authority_id", authority_id)
        object.__setattr__(self, "_authority_seal", authority_seal)
        object.__setattr__(self, "_held", MappingProxyType(dict(held)))
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name, value) -> None:  # pragma: no cover - defensive path
        if getattr(self, "_sealed", False):
            raise AttributeError("Holder objects are immutable")
        object.__setattr__(self, name, value)

    __reduce__ = _no_serialize
    __reduce_ex__ = _no_serialize
    __copy__ = _no_serialize
    __deepcopy__ = _no_serialize

    def __repr__(self) -> str:
        return f"Holder(name={self._name!r}, aliases={sorted(self._held)!r})"

    @property
    def name(self) -> str:
        return self._name

    @property
    def held(self) -> Mapping[str, Reference]:
        return self._held

    def _get(self, alias: str) -> Reference:
        if type(alias) is not str:
            raise Forged(f"{self._name}: holds no reference named {alias!r}")
        reference = self._held.get(alias)
        if reference is None:
            raise Forged(f"{self._name}: holds no reference named {alias!r}")
        reference._assert_authority(self._authority_id, self._authority_seal)
        return reference

    def use(self, alias: str, operation: str) -> dict:
        return self._get(alias).invoke(operation)

    def delegate(self, alias: str, operations: Iterable[str]) -> Reference:
        return self._get(alias).attenuate(operations)


def _mint_reference(
    authority_id: str,
    authority_seal: bytes,
    resource: str,
    operations: frozenset[str],
    membranes: tuple[Membrane, ...],
) -> Reference:
    token = secrets.token_urlsafe(32)
    signature = _signature(authority_seal, authority_id, token, resource, operations)
    reference = Reference(
        authority_id,
        authority_seal,
        resource,
        operations,
        token,
        signature,
        membranes,
        _guard=_MINT_GUARD,
    )
    # Every derived/wrapped reference is a live descendant of every membrane in its chain.
    for membrane in membranes:
        membrane._register(reference)
    return reference
