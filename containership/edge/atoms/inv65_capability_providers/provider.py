"""Hardened in-memory reference provider used by INV-65 conformance checks.

This is deliberately a reference model, not a network service.  It models the
security-sensitive invariants that a real capability provider implementation
must preserve: named-link isolation, validation before activation, durable
revocation, backend health gating, and secret-reference hygiene.
"""
from __future__ import annotations

import copy
import math
import re
import threading
from collections.abc import Mapping
from typing import Any, Final

DEFAULT_LINK_NAME: Final = "default"
_MAX_IDENTIFIER: Final = 256
_MAX_CONFIG_DEPTH: Final = 8
_MAX_CONTAINER_ITEMS: Final = 256
_MAX_STRING: Final = 4096
_FORBIDDEN_SECRET_KEYS: Final = frozenset(
    {
        "password",
        "passwd",
        "token",
        "secret",
        "api_key",
        "apikey",
        "access_key",
        "private_key",
        "credential",
        "credentials",
    }
)


def _is_forbidden_secret_key(key: str) -> bool:
    # Normalize common camelCase/kebab-case spellings while allowing explicit
    # references such as ``secret_ref`` and ``token_reference``.
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key).lower().replace("-", "_")
    if normalized.endswith(("_ref", "_reference", "_id")):
        return False
    if normalized in _FORBIDDEN_SECRET_KEYS or normalized == "authorization":
        return True
    secret_suffixes = (
        "password", "passwd", "token", "secret", "api_key", "access_key",
        "private_key", "credential", "credentials",
    )
    return any(normalized.endswith("_" + suffix) for suffix in secret_suffixes)


class ProviderError(RuntimeError):
    """Base provider failure with a stable machine-readable error code."""

    code = "PK_PROVIDER_ERROR"


class NoLink(PermissionError, ProviderError):
    """The caller has no established named link to this provider."""

    code = "PK_PROVIDER_NO_LINK"


class InvalidLink(ValueError, ProviderError):
    """A link or operation failed validation before activation/use."""

    code = "PK_PROVIDER_INVALID_LINK"


class ProviderUnavailable(ConnectionError, ProviderError):
    """The provider's backing capability is unhealthy or unavailable."""

    code = "PK_PROVIDER_UNAVAILABLE"


def _validate_identifier(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise InvalidLink(f"{field} must be a string")
    if not value or value != value.strip():
        raise InvalidLink(f"{field} must be a non-empty trimmed string")
    if len(value) > _MAX_IDENTIFIER:
        raise InvalidLink(f"{field} exceeds {_MAX_IDENTIFIER} characters")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise InvalidLink(f"{field} contains control characters")
    return value


def _copy_plain_data(value: Any, *, path: str = "config", depth: int = 0) -> Any:
    """Validate and copy bounded JSON-like data without invoking user hooks.

    Only ordinary JSON-shaped values are accepted.  This prevents configuration
    objects with executable ``__deepcopy__``/descriptor behaviour from entering
    the provider and also places simple bounds on attacker-controlled structures.
    """
    if depth > _MAX_CONFIG_DEPTH:
        raise InvalidLink(f"{path} exceeds maximum nesting depth {_MAX_CONFIG_DEPTH}")

    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise InvalidLink(f"{path} contains a non-finite float")
        return value
    if isinstance(value, str):
        if len(value) > _MAX_STRING:
            raise InvalidLink(f"{path} string exceeds {_MAX_STRING} characters")
        return value
    if isinstance(value, Mapping):
        if len(value) > _MAX_CONTAINER_ITEMS:
            raise InvalidLink(f"{path} has too many keys")
        result: dict[str, Any] = {}
        for key, child in value.items():
            if not isinstance(key, str) or not key:
                raise InvalidLink(f"{path} keys must be non-empty strings")
            if _is_forbidden_secret_key(key):
                raise InvalidLink(
                    f"{path}.{key} contains inline secret material; use a secret reference instead"
                )
            result[key] = _copy_plain_data(child, path=f"{path}.{key}", depth=depth + 1)
        return result
    if isinstance(value, (list, tuple)):
        if len(value) > _MAX_CONTAINER_ITEMS:
            raise InvalidLink(f"{path} has too many items")
        return [_copy_plain_data(v, path=f"{path}[]", depth=depth + 1) for v in value]
    raise InvalidLink(f"{path} contains unsupported value type {type(value).__name__}")


def _validated_config(component: str, config: object) -> dict[str, Any]:
    if not isinstance(config, Mapping):
        raise InvalidLink(f"{component}: link config must be a mapping")
    safe = _copy_plain_data(config)
    if not isinstance(safe, dict):  # defensive internal invariant
        raise RuntimeError("validated configuration did not produce a mapping")
    for key in ("bucket", "user"):
        value = safe.get(key)
        if not isinstance(value, str) or not value.strip():
            raise InvalidLink(f"{component}: link config needs non-empty string '{key}'")
    return safe


class Provider:
    """Thread-safe reference model for a multi-link capability provider.

    ``link(component, config)`` and ``call(component, op)`` remain compatible
    with the 4.1 API by using the implicit link name ``"default"``.  Callers can
    additionally use ``link_name=...`` to maintain multiple isolated links for
    one component.
    """

    def __init__(self, contract: str) -> None:
        self.contract = _validate_identifier(contract, "contract id")
        self._links: dict[tuple[str, str], dict[str, Any]] = {}
        self._snapshot: dict[tuple[str, str], dict[str, Any]] = {}
        self._backend_ok = True
        self._restarts = 0
        self._lock = threading.RLock()

    @property
    def backend_ok(self) -> bool:
        with self._lock:
            return self._backend_ok

    @backend_ok.setter
    def backend_ok(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise TypeError("backend_ok must be bool")
        with self._lock:
            self._backend_ok = value

    @property
    def restarts(self) -> int:
        with self._lock:
            return self._restarts

    @property
    def link_count(self) -> int:
        with self._lock:
            return len(self._links)

    def link(self, component: str, config: Mapping[str, object], link_name: str = DEFAULT_LINK_NAME) -> None:
        component = _validate_identifier(component, "component id")
        link_name = _validate_identifier(link_name, "link name")
        safe_config = _validated_config(component, config)
        key = (component, link_name)
        # The active table and restart snapshot are committed together under one
        # lock, preventing restart from observing a half-applied link update.
        with self._lock:
            self._links[key] = safe_config
            self._snapshot[key] = copy.deepcopy(safe_config)

    def unlink(self, component: str, link_name: str = DEFAULT_LINK_NAME) -> bool:
        """Revoke a named link and persist the revocation across restart."""
        component = _validate_identifier(component, "component id")
        link_name = _validate_identifier(link_name, "link name")
        key = (component, link_name)
        with self._lock:
            existed = key in self._links or key in self._snapshot
            self._links.pop(key, None)
            self._snapshot.pop(key, None)
            return existed

    def link_names(self, component: str) -> tuple[str, ...]:
        """Return names only; configuration and credential references stay private."""
        component = _validate_identifier(component, "component id")
        with self._lock:
            return tuple(sorted(name for owner, name in self._links if owner == component))

    def call(self, component: str, op: str, link_name: str = DEFAULT_LINK_NAME) -> dict[str, str]:
        component = _validate_identifier(component, "component id")
        link_name = _validate_identifier(link_name, "link name")
        op = _validate_identifier(op, "operation")
        key = (component, link_name)
        with self._lock:
            cfg = self._links.get(key)
            if cfg is None:
                raise NoLink(f"{component}:{link_name} has no link to {self.contract}")
            if not self._backend_ok:
                raise ProviderUnavailable(f"{self.contract} backend unavailable")
            # Copy only the non-secret values required by this reference call;
            # never return the stored configuration object itself.
            bucket = str(cfg["bucket"])
            user = str(cfg["user"])
        return {"op": op, "bucket": bucket, "as": user, "link": link_name}

    def health(self) -> str:
        with self._lock:
            return "healthy" if self._backend_ok else "unhealthy"

    def checkpoint(self) -> None:
        with self._lock:
            self._snapshot = copy.deepcopy(self._links)

    def restart(self) -> int:
        with self._lock:
            restored = copy.deepcopy(self._snapshot)
            self._links = restored
            self._restarts += 1
            return len(self._links)
