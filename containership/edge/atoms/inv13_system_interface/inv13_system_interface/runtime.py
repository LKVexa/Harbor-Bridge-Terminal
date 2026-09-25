"""Hardened reference runtime model for INV-13.

This module deliberately has no ``pk_core`` dependency so the security-critical
capability and path-confinement logic can be tested in isolation.  It models
WASI-style *lexical POSIX path* confinement only; a production host must still
use descriptor/handle-relative filesystem operations to prevent symlink/race
escapes at the operating-system boundary.
"""
from __future__ import annotations

import hashlib
import json
import posixpath
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

CAPABILITIES = frozenset({
    "filesystem", "wall-clock", "monotonic-clock", "random",
    "sockets", "environment", "stdio", "http-outgoing",
})

MAX_NAME_LENGTH = 256
MAX_PATH_LENGTH = 4096
MAX_PREOPENS = 256


class CapabilityDenied(PermissionError):
    """Raised when a component asks for authority its world did not grant."""


class PathEscape(PermissionError):
    """Raised when a path would escape or ambiguously address a preopen."""


def _require_text(value: Any, field_name: str, *, max_length: int) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be str, got {type(value).__name__}")
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    if len(value) > max_length:
        raise ValueError(f"{field_name} exceeds {max_length} characters")
    if "\0" in value:
        raise ValueError(f"{field_name} must not contain NUL")
    return value


def _canonical_absolute(value: Any, field_name: str) -> str:
    value = _require_text(value, field_name, max_length=MAX_PATH_LENGTH)
    if not value.startswith("/") or value.startswith("//"):
        raise ValueError(f"{field_name} must be a single-rooted absolute POSIX path")
    canonical = posixpath.normpath(value)
    if canonical != value:
        raise ValueError(
            f"{field_name} must be canonical (expected {canonical!r}, got {value!r})")
    return canonical


@dataclass(frozen=True, slots=True)
class World:
    """Immutable capability set exposed to one component instance."""

    name: str
    capabilities: frozenset[str]

    def __post_init__(self) -> None:
        name = _require_text(self.name, "world name", max_length=MAX_NAME_LENGTH)
        try:
            snapshot = frozenset(self.capabilities)
        except TypeError as exc:
            raise TypeError("capabilities must be an iterable of hashable strings") from exc
        if any(not isinstance(cap, str) for cap in snapshot):
            raise TypeError("every capability name must be str")
        unknown = snapshot - CAPABILITIES
        if unknown:
            raise ValueError(f"unknown capabilities in world: {sorted(unknown)}")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "capabilities", snapshot)


class Instance:
    """A component instantiated against a world with explicit preopens.

    Mutable authority is retained privately.  Public ``preopens``, ``denials``
    and ``audit_events`` views cannot be mutated to bypass validation.
    """

    __slots__ = (
        "component", "world", "_preopens", "_denials", "_audit_events",
        "_audit_head", "_audit_seq",
    )

    def __init__(
        self,
        component: str,
        world: World,
        preopens: Mapping[str, str] | None = None,
        denials: Iterable[str] | None = None,
    ) -> None:
        self.component = _require_text(component, "component", max_length=MAX_NAME_LENGTH)
        if not isinstance(world, World):
            raise TypeError(f"world must be World, got {type(world).__name__}")
        self.world = world
        self._preopens: dict[str, str] = {}
        self._denials: list[str] = []
        self._audit_events: list[dict[str, Any]] = []
        self._audit_head = ""
        self._audit_seq = 0

        if denials is not None:
            for denial in denials:
                self._denials.append(_require_text(denial, "denial", max_length=MAX_PATH_LENGTH))
        if preopens is not None:
            if not isinstance(preopens, Mapping):
                raise TypeError("preopens must be a mapping of logical root to host root")
            for logical, host_root in preopens.items():
                self.grant_preopen(logical, host_root)

        self._record("instance", "created", {"world": self.world.name})

    @property
    def preopens(self):
        """Read-only live view of logical root -> host root mappings."""
        return MappingProxyType(self._preopens)

    @property
    def denials(self) -> tuple[str, ...]:
        """Immutable snapshot of denial reason tokens."""
        return tuple(self._denials)

    @property
    def audit_events(self) -> tuple[Mapping[str, Any], ...]:
        """Immutable snapshots of deterministic, hash-chained security events."""
        snapshots = []
        for event in self._audit_events:
            snapshot = dict(event)
            snapshot["detail"] = MappingProxyType(dict(event["detail"]))
            snapshots.append(MappingProxyType(snapshot))
        return tuple(snapshots)

    @property
    def audit_head(self) -> str:
        return self._audit_head

    def _record(self, action: str, outcome: str, detail: Mapping[str, Any]) -> None:
        self._audit_seq += 1
        body = {
            "seq": self._audit_seq,
            "action": action,
            "outcome": outcome,
            "detail": dict(detail),
            "prev": self._audit_head,
        }
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        event = dict(body)
        event["digest"] = digest
        self._audit_events.append(event)
        self._audit_head = digest

    def _deny(self, token: str, action: str, detail: Mapping[str, Any]) -> None:
        self._denials.append(token)
        self._record(action, "denied", {**dict(detail), "reason": token})

    def verify_audit_chain(self) -> bool:
        previous = ""
        for expected_seq, event in enumerate(self._audit_events, start=1):
            if event.get("seq") != expected_seq or event.get("prev") != previous:
                return False
            body = {key: event[key] for key in ("seq", "action", "outcome", "detail", "prev")}
            encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
            if event.get("digest") != digest:
                return False
            previous = digest
        return previous == self._audit_head

    def grant_preopen(self, logical: str, host_root: str, *, replace: bool = False) -> dict[str, Any]:
        if "filesystem" not in self.world.capabilities:
            self._deny("filesystem-not-granted", "preopen.grant", {"logical": repr(logical)})
            raise CapabilityDenied(
                f"{self.component}: world {self.world.name!r} grants no filesystem")

        logical = _canonical_absolute(logical, "logical preopen root")
        host_root = _canonical_absolute(host_root, "host preopen root")
        current = self._preopens.get(logical)
        if current is not None and current != host_root and not replace:
            self._deny("preopen-replacement-requires-explicit-replace", "preopen.grant", {"logical": logical})
            raise ValueError(
                f"preopen {logical!r} already maps to {current!r}; pass replace=True to change it")
        if current is None and len(self._preopens) >= MAX_PREOPENS:
            self._deny("preopen-limit-exceeded", "preopen.grant", {"logical": logical})
            raise ValueError(f"preopen limit {MAX_PREOPENS} exceeded")

        self._preopens[logical] = host_root
        self._record(
            "preopen.grant",
            "replaced" if current is not None and current != host_root else "granted",
            {"logical": logical, "host_root": host_root},
        )
        return {"schema": "PK_PREOPEN/1", "logical": logical, "host_root": host_root}

    def revoke_preopen(self, logical: str) -> None:
        logical = _canonical_absolute(logical, "logical preopen root")
        if logical not in self._preopens:
            self._deny("preopen-not-found", "preopen.revoke", {"logical": logical})
            raise CapabilityDenied(f"{self.component}: no preopen for root {logical!r}")
        del self._preopens[logical]
        self._record("preopen.revoke", "revoked", {"logical": logical})

    def use(self, capability: str) -> dict[str, Any]:
        """Return explicit authority or deny it; there is no ambient fallback."""
        capability = _require_text(capability, "capability", max_length=MAX_NAME_LENGTH)
        if capability not in self.world.capabilities:
            self._deny("capability-not-granted", "capability.use", {"capability": capability})
            raise CapabilityDenied(
                f"{self.component}: {capability!r} is not in world {self.world.name!r}")
        self._record("capability.use", "granted", {"capability": capability})
        return {
            "schema": "PK_WORLD/1",
            "component": self.component,
            "capability": capability,
            "granted": True,
        }

    def resolve(self, logical_root: str, path: str) -> dict[str, Any]:
        """Lexically resolve a relative POSIX path inside a preopen.

        This is intentionally *not* a host filesystem open.  Production hosts
        must resolve through already-open directory descriptors/handles so
        symlinks and TOCTOU races cannot escape the authority represented by the
        preopen.
        """
        self.use("filesystem")
        logical_root = _canonical_absolute(logical_root, "logical preopen root")
        if logical_root not in self._preopens:
            self._deny("preopen-not-found", "path.resolve", {"logical": logical_root})
            raise CapabilityDenied(
                f"{self.component}: no preopen for root {logical_root!r}")
        if not isinstance(path, str):
            raise TypeError(f"path must be str, got {type(path).__name__}")
        if len(path) > MAX_PATH_LENGTH:
            self._deny("path-too-long", "path.resolve", {"logical": logical_root})
            raise PathEscape(f"path exceeds {MAX_PATH_LENGTH} characters")
        if "\0" in path:
            self._deny("path-contains-nul", "path.resolve", {"logical": logical_root})
            raise PathEscape("path contains NUL")
        if path.startswith("/"):
            self._deny("absolute-path", "path.resolve", {"logical": logical_root})
            raise PathEscape(f"{path!r}: absolute paths are never resolved")

        host_root = self._preopens[logical_root]
        normalized_relative = posixpath.normpath(path)
        candidate = posixpath.normpath(posixpath.join(host_root, normalized_relative))
        root = host_root
        prefix = root if root.endswith("/") else root + "/"
        if candidate != root and not candidate.startswith(prefix):
            self._deny("path-escape", "path.resolve", {"logical": logical_root, "requested": path})
            raise PathEscape(f"{path!r} escapes preopen {logical_root!r} ({candidate})")

        self._record(
            "path.resolve",
            "resolved",
            {"logical": logical_root, "requested": path, "normalized": normalized_relative},
        )
        return {
            "schema": "PK_PATH_RESOLVE/1",
            "root": logical_root,
            "requested": path,
            "normalized_relative": normalized_relative,
            "resolved": candidate,
            "inside_preopen": True,
            "resolution_semantics": "lexical-posix",
        }
