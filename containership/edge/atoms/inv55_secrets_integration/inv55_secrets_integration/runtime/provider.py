"""Provider abstraction (checklist #14).

A provider owns secret versions and revocation state.  The service never talks
to storage except through this interface, and every provider failure is mapped
onto a stable :mod:`errors` code before it crosses the boundary.
"""
from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..reference import _SecretValue
from .errors import INV55Error


@dataclass(frozen=True)
class ProviderSecret:
    name: str
    version: int
    value: _SecretValue           # never a str
    provider_lease_id: str | None = None
    provider_ttl_s: float | None = None


@dataclass(frozen=True)
class ProviderHealth:
    healthy: bool
    sealed: bool | None
    detail: str
    version: str | None = None


class SecretProvider(ABC):
    """Contract every storage adapter implements."""

    name = "abstract"

    @abstractmethod
    def read(self, name: str, version: int | None = None, *, timeout_s: float) -> ProviderSecret: ...

    @abstractmethod
    def write(self, name: str, value: str, *, cas: int | None, timeout_s: float) -> int: ...

    @abstractmethod
    def metadata(self, name: str, *, timeout_s: float) -> dict: ...

    @abstractmethod
    def destroy_version(self, name: str, version: int, *, timeout_s: float) -> None: ...

    @abstractmethod
    def revoke_lease(self, provider_lease_id: str, *, timeout_s: float) -> None: ...

    @abstractmethod
    def health(self, *, timeout_s: float) -> ProviderHealth: ...


class InMemoryProvider(SecretProvider):
    """Test/reference provider.  Supports fault injection hooks for resilience tests."""

    name = "memory"

    def __init__(self):
        self._data: dict[str, list[_SecretValue | None]] = {}
        self._lock = threading.Lock()
        self.fail_next: list[str] = []      # queue of error codes to raise on the next calls
        self.available = True
        self.calls = 0

    def _fault(self):
        self.calls += 1
        if not self.available:
            raise INV55Error("INV55-E-PROVIDER-UNAVAILABLE", "memory provider marked unavailable")
        if self.fail_next:
            raise INV55Error(self.fail_next.pop(0), "injected fault")

    def read(self, name, version=None, *, timeout_s):
        self._fault()
        with self._lock:
            hist = self._data.get(name)
            if not hist:
                raise INV55Error("INV55-E-DENIED", "not found")
            v = len(hist) if version is None else version
            if v < 1 or v > len(hist) or hist[v - 1] is None:
                raise INV55Error("INV55-E-DENIED", "version not found")
            return ProviderSecret(name, v, hist[v - 1])

    def write(self, name, value, *, cas, timeout_s):
        self._fault()
        with self._lock:
            hist = self._data.setdefault(name, [])
            if cas is not None and cas != len(hist):
                raise INV55Error("INV55-E-CONFLICT", "check-and-set mismatch")
            hist.append(_SecretValue(value))
            return len(hist)

    def metadata(self, name, *, timeout_s):
        self._fault()
        with self._lock:
            hist = self._data.get(name) or []
            return {"current_version": len(hist), "destroyed": [i + 1 for i, v in enumerate(hist) if v is None]}

    def destroy_version(self, name, version, *, timeout_s):
        self._fault()
        with self._lock:
            self._data[name][version - 1] = None

    def revoke_lease(self, provider_lease_id, *, timeout_s):
        self._fault()

    def health(self, *, timeout_s):
        return ProviderHealth(self.available, False, "in-memory", "memory/1")
