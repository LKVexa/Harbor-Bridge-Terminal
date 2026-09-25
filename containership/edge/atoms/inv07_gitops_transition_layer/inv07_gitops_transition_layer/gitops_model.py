"""Deterministic, dependency-free reference model for INV-07 GitOps behavior.

This module intentionally models only the local reconciliation semantics used by
INV-07 conformance evidence.  It is not a replacement for a real Git client,
Argo CD, Flux, an asymmetric signing service, or a cluster control plane.

Security properties of this reference model:
* desired state is restricted to canonical JSON data with string object keys;
* signatures are computed over canonical UTF-8 JSON rather than ``repr``;
* commit identifiers use full SHA-256 digests;
* committed state is deep-copied so callers cannot mutate history by alias;
* signature checks use ``hmac.compare_digest``;
* state transitions are serialized with an ``RLock``;
* repeated sync of an unchanged head does not create duplicate applied-history
  entries, while drift reconciliation is still reported.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import math
import threading
from typing import Any, Mapping

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
State = dict[str, JsonValue]


class Unsigned(PermissionError):
    """Raised when a commit cannot be authenticated by an allowed key."""


class NothingToSync(LookupError):
    """Raised when there is no commit to sync or no earlier applied commit."""


class InvalidState(ValueError):
    """Raised when desired state cannot be represented canonically as JSON."""


def _validate_json_value(value: Any, path: str = "$") -> None:
    """Validate a deterministic JSON value without silently coercing types."""
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise InvalidState(f"{path}: non-finite floats are not allowed")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise InvalidState(f"{path}: object keys must be non-empty strings")
            _validate_json_value(item, f"{path}.{key}")
        return
    raise InvalidState(f"{path}: unsupported state type {type(value).__name__}")


def canonical_state_bytes(state: Mapping[str, Any]) -> bytes:
    """Return a stable UTF-8 serialization for a desired-state mapping."""
    if not isinstance(state, Mapping):
        raise InvalidState("desired state must be a mapping")
    materialized = dict(state)
    _validate_json_value(materialized)
    try:
        encoded = json.dumps(
            materialized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:  # defensive: validation should catch it
        raise InvalidState(f"desired state is not canonical JSON: {exc}") from exc
    return encoded.encode("utf-8")


def _validated_secret(key: bytes | bytearray | memoryview) -> bytes:
    if not isinstance(key, (bytes, bytearray, memoryview)):
        raise TypeError("signing key must be bytes-like")
    secret = bytes(key)
    if not secret:
        raise ValueError("signing key must not be empty")
    return secret


def sign(key: bytes | bytearray | memoryview, state: Mapping[str, Any]) -> str:
    """Sign desired state for the dependency-free test model using HMAC-SHA256.

    Production deployments should replace this model primitive with the
    approved asymmetric Git signature/provenance verifier named in the
    architecture contract.
    """
    return hmac.new(_validated_secret(key), canonical_state_bytes(state), hashlib.sha256).hexdigest()


def _copy_state(state: Mapping[str, Any]) -> State:
    canonical_state_bytes(state)  # validate before retaining caller data
    return deepcopy(dict(state))


@dataclass
class GitOps:
    """Small in-memory reference controller for deterministic conformance tests."""

    keys: Mapping[str, bytes]
    commits: list[tuple[str, State, str, str]] = field(default_factory=list)
    live: State = field(default_factory=dict)
    reports: list[dict[str, Any]] = field(default_factory=list)
    applied: list[str] = field(default_factory=list)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        normalized: dict[str, bytes] = {}
        for key_id, secret in dict(self.keys).items():
            if not isinstance(key_id, str) or not key_id.strip():
                raise ValueError("key ids must be non-empty strings")
            normalized[key_id] = _validated_secret(secret)
        self.keys = normalized
        self.live = _copy_state(self.live)

        # Preserve backward-compatible constructor fields but detach retained state.
        detached: list[tuple[str, State, str, str]] = []
        for sha, state, key_id, signature in self.commits:
            detached.append((str(sha), _copy_state(state), str(key_id), str(signature)))
        self.commits = detached
        self.reports = deepcopy(self.reports)
        self.applied = [str(sha) for sha in self.applied]

    def commit(self, state: Mapping[str, Any], key_id: str, sig: str) -> str:
        """Append a proposed commit and return its deterministic SHA-256 id."""
        if not isinstance(key_id, str) or not key_id:
            raise ValueError("key_id must be a non-empty string")
        if not isinstance(sig, str):
            raise TypeError("signature must be a string")
        frozen = _copy_state(state)
        with self._lock:
            parent = self.commits[-1][0] if self.commits else None
            envelope = {
                "index": len(self.commits),
                "key_id": key_id,
                "parent": parent,
                "signature": sig,
                "state": frozen,
            }
            sha = hashlib.sha256(
                json.dumps(
                    envelope,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    allow_nan=False,
                ).encode("utf-8")
            ).hexdigest()
            self.commits.append((sha, frozen, key_id, sig))
            return sha

    def verify_head(self) -> str:
        """Verify and return the current head commit id without mutating live state."""
        with self._lock:
            if not self.commits:
                raise NothingToSync("no commits to verify")
            sha, state, key_id, sig = self.commits[-1]
            key = self.keys.get(key_id)
            expected = sign(key, state) if key is not None else None
            if expected is None or not hmac.compare_digest(sig, expected):
                raise Unsigned(f"commit {sha} is not signed by an allowed key")
            return sha

    def sync(self) -> str:
        """Verify head, reconcile drift, and apply desired state atomically."""
        with self._lock:
            sha = self.verify_head()
            _, state, _, _ = self.commits[-1]

            # Drift is measured against the state of the last applied commit, not
            # against a new desired commit whose changes are legitimate.
            baseline_sha = self.applied[-1] if self.applied else None
            baseline = self._state_of(baseline_sha) if baseline_sha else state
            drift_keys = {
                key
                for key in set(self.live) | set(baseline)
                if self.live.get(key) != baseline.get(key) or (key in self.live) != (key in baseline)
            }
            if baseline_sha and drift_keys:
                self.reports.append(
                    {
                        "detected_against_commit": baseline_sha,
                        "reconciled_to_commit": sha,
                        "reverted": sorted(drift_keys),
                    }
                )

            self.live = deepcopy(state)
            if not self.applied or self.applied[-1] != sha:
                self.applied.append(sha)
            return sha

    def _state_of(self, sha: str) -> State:
        """Return a detached copy of committed state by commit id."""
        with self._lock:
            for commit_sha, commit_state, _, _ in reversed(self.commits):
                if commit_sha == sha:
                    return deepcopy(commit_state)
        raise NothingToSync(f"commit {sha} not found")

    def revert(self, key_id: str) -> str:
        """Create a signed revert commit targeting the prior applied revision.

        Applied history is authoritative for rollback.  Refused/unverified raw
        commits can therefore never become rollback targets.
        """
        with self._lock:
            key = self.keys.get(key_id)
            if key is None:
                raise Unsigned(f"{key_id}: not an allowed key")
            if len(self.applied) < 2:
                raise NothingToSync("no earlier applied commit to revert to")
            previous_sha = self.applied[-2]
            previous_state = self._state_of(previous_sha)
            return self.commit(previous_state, key_id, sign(key, previous_state))

    def status(self) -> dict[str, Any]:
        """Return a detached, secret-free controller status snapshot."""
        with self._lock:
            head = self.commits[-1][0] if self.commits else None
            applied = self.applied[-1] if self.applied else None
            return {
                "head": head,
                "applied": applied,
                "in_sync": head is not None and head == applied and self.live == self._state_of(applied),
                "commit_count": len(self.commits),
                "applied_count": len(self.applied),
                "report_count": len(self.reports),
                "allowed_key_ids": sorted(self.keys),
            }
