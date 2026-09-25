"""Provider abstraction (checklist #14).

The broker never talks to storage directly.  A ``SecretProvider`` owns versions,
revocation state and credential lifetime; the broker owns scoping, leasing,
redaction and audit.  Providers must raise only ``ProviderError`` subclasses so
the service can map failures onto the stable error taxonomy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import threading
from typing import Protocol, runtime_checkable

from ..secretvalue import SecretValue


class ProviderError(Exception):
    """Base provider failure."""

    retryable = False


class ProviderUnavailable(ProviderError):
    retryable = True


class ProviderNotFound(ProviderError):
    pass


class ProviderDenied(ProviderError):
    pass


class ProviderConflict(ProviderError):
    """Check-and-set (CAS) conflict: someone else rotated first."""


@dataclass(frozen=True)
class ProviderSecret:
    name: str
    version: int
    value: SecretValue
    provider_lease_id: str | None = None      # dynamic-secret lease, if any
    provider_ttl_s: float | None = None
    destroyed: bool = False


@dataclass(frozen=True)
class ProviderHealth:
    reachable: bool
    sealed: bool | None = None
    version: str | None = None
    detail: str = ""


@runtime_checkable
class SecretProvider(Protocol):
    name: str

    def read(self, name: str, version: int | None = None) -> ProviderSecret: ...
    def write(self, name: str, value: SecretValue, cas: int | None = None) -> int: ...
    def metadata(self, name: str) -> dict: ...
    def destroy_version(self, name: str, version: int) -> None: ...
    def renew(self, provider_lease_id: str, increment_s: float) -> float: ...
    def revoke(self, provider_lease_id: str) -> None: ...
    def health(self) -> ProviderHealth: ...


@dataclass
class InMemoryProvider:
    """Reference/test provider.  NOT for production (see ADR-0001)."""

    name: str = "memory"
    _data: dict[str, list[SecretValue]] = field(default_factory=dict)
    _destroyed: set[tuple[str, int]] = field(default_factory=set)
    _revoked: set[str] = field(default_factory=set)
    available: bool = True
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def _up(self) -> None:
        if not self.available:
            raise ProviderUnavailable("memory provider marked unavailable")

    def read(self, name: str, version: int | None = None) -> ProviderSecret:
        self._up()
        with self._lock:
            hist = self._data.get(name)
            if not hist:
                raise ProviderNotFound(name)
            v = len(hist) if version is None else version
            if v < 1 or v > len(hist) or (name, v) in self._destroyed:
                raise ProviderNotFound(f"{name}@{v}")
            return ProviderSecret(name, v, hist[v - 1])

    def write(self, name: str, value: SecretValue, cas: int | None = None) -> int:
        self._up()
        with self._lock:
            hist = self._data.setdefault(name, [])
            if cas is not None and cas != len(hist):
                raise ProviderConflict(f"cas {cas} != current {len(hist)}")
            hist.append(value)
            return len(hist)

    def metadata(self, name: str) -> dict:
        self._up()
        with self._lock:
            hist = self._data.get(name)
            if not hist:
                raise ProviderNotFound(name)
            return {"current_version": len(hist),
                    "destroyed": sorted(v for n, v in self._destroyed if n == name)}

    def destroy_version(self, name: str, version: int) -> None:
        self._up()
        with self._lock:
            self._destroyed.add((name, version))

    def renew(self, provider_lease_id: str, increment_s: float) -> float:
        self._up()
        if provider_lease_id in self._revoked:
            raise ProviderDenied("lease revoked")
        return increment_s

    def revoke(self, provider_lease_id: str) -> None:
        self._up()
        self._revoked.add(provider_lease_id)

    def health(self) -> ProviderHealth:
        return ProviderHealth(reachable=self.available, sealed=False, version="memory")
