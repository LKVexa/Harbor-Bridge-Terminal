"""INV-55 - Secrets integration.

Reference behavior for application-scoped, versioned, leased secret resolution.
The implementation is deliberately small, but it treats secret-bearing objects as
non-string capabilities so ordinary string APIs cannot accidentally materialize
plaintext into logs or diagnostics.

This module is an executable reference model, not a secret-storage backend.  A
production deployment still needs an approved provider adapter (for example,
Vault), workload identity, transport security, durable audit export, and the
operational controls documented in the repository gap report.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import math
import re
import threading
import time
from typing import Callable, Iterable

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build


_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")


def _verify(condition: bool, message: str = "behavioural check failed") -> None:
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class SecretDenied(PermissionError):
    """The caller is not allowed to resolve or use the requested secret."""


class SecretNotFound(KeyError):
    """The requested secret reference does not exist."""


class LeaseExpired(PermissionError):
    """The lease is no longer valid."""


class LeaseRevoked(PermissionError):
    """The lease has been explicitly revoked."""


class LeaseContextMismatch(PermissionError):
    """The lease was presented by the wrong application/name/broker context."""


class VersionRetired(PermissionError):
    """The leased secret version has been retired."""


class ClockRollbackError(RuntimeError):
    """The injected monotonic clock moved backwards."""


class InvalidSecretReference(ValueError):
    """A secret/application identifier is malformed or unsafe for diagnostics."""


class _SecretValue:
    """Non-string secret container with redacted diagnostics.

    The wrapper prevents *accidental* disclosure through inherited ``str`` APIs.
    Python cannot provide a hard in-process confidentiality boundary against code
    that deliberately introspects private attributes; production isolation must be
    provided by process/runtime boundaries and the external secret provider.
    """

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("secret value must be str")
        self._value = value

    def __repr__(self) -> str:
        return "Secret(***)"

    __str__ = __repr__

    def __format__(self, spec: str) -> str:
        return format(repr(self), spec)

    def _reveal(self) -> str:
        return self._value

    def __reduce_ex__(self, protocol):
        raise TypeError("secret values must not be serialized")


@dataclass(frozen=True, slots=True)
class SecretLease:
    """Immutable lease capability bound to one broker, app, name, and version."""

    app: str
    name: str
    version: int
    issued_at: float
    expires_at: float
    _secret: _SecretValue = field(repr=True, compare=False)
    _issuer: object = field(repr=False, compare=False)
    _lease_id: int = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Structured, secret-free audit event."""

    operation: str
    app: str
    name: str
    allowed: bool
    reason: str
    version: int | None
    at: float


@dataclass
class SecretBroker:
    """In-memory executable reference model for the INV-55 behavior.

    ``versions`` is intentionally only a test/reference store.  It must be
    replaced by a production provider adapter; this component does not claim to
    own durable secret storage.
    """

    lease_ttl: float = 300.0
    clock: Callable[[], float] = time.monotonic
    versions: dict[str, list[_SecretValue]] = field(default_factory=dict)
    scopes: dict[str, frozenset[str]] = field(default_factory=dict)
    audit_limit: int = 10_000
    max_secret_chars: int = 65_536
    max_apps_per_secret: int = 1_024
    max_secrets: int = 10_000
    max_versions_per_secret: int = 1_024
    audit: deque[AuditEvent] = field(default_factory=deque)
    retired: set[tuple[str, int]] = field(default_factory=set)
    _revoked_lease_ids: set[int] = field(default_factory=set, repr=False)
    _issuer: object = field(default_factory=object, init=False, repr=False)
    _next_lease_id: int = field(default=1, init=False, repr=False)
    _last_now: float | None = field(default=None, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.lease_ttl, (int, float)) or isinstance(self.lease_ttl, bool):
            raise TypeError("lease_ttl must be a finite positive number")
        if not math.isfinite(float(self.lease_ttl)) or self.lease_ttl <= 0:
            raise ValueError("lease_ttl must be a finite positive number")
        if not callable(self.clock):
            raise TypeError("clock must be callable")
        limits = {
            "audit_limit": self.audit_limit,
            "max_secret_chars": self.max_secret_chars,
            "max_apps_per_secret": self.max_apps_per_secret,
            "max_secrets": self.max_secrets,
            "max_versions_per_secret": self.max_versions_per_secret,
        }
        for name, value in limits.items():
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        self.audit = deque(self.audit, maxlen=self.audit_limit)

    @staticmethod
    def _identifier(value: str, field_name: str) -> str:
        if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
            raise InvalidSecretReference(
                f"{field_name} must match {_IDENTIFIER_RE.pattern!r} and be <= 256 characters"
            )
        return value

    def _now(self) -> float:
        now = float(self.clock())
        if not math.isfinite(now):
            raise ClockRollbackError("clock returned a non-finite value")
        if self._last_now is not None and now < self._last_now:
            raise ClockRollbackError("monotonic clock moved backwards")
        self._last_now = now
        return now


    def put(self, name: str, value: str, apps: Iterable[str]) -> int:
        """Add a new immutable version and atomically replace its application scope."""
        name = self._identifier(name, "name")
        if not isinstance(value, str):
            raise TypeError("secret value must be str")
        if len(value) > self.max_secret_chars:
            raise ValueError("secret value exceeds max_secret_chars")
        if isinstance(apps, (str, bytes)):
            raise TypeError("apps must be an iterable of application identifiers, not a string")
        normalized = frozenset(self._identifier(app, "app") for app in apps)
        if not normalized:
            raise InvalidSecretReference("at least one application must be authorized")
        if len(normalized) > self.max_apps_per_secret:
            raise ValueError("application scope exceeds max_apps_per_secret")

        with self._lock:
            if name not in self.versions and len(self.versions) >= self.max_secrets:
                raise OverflowError("secret capacity exhausted")
            history = self.versions.setdefault(name, [])
            if len(history) >= self.max_versions_per_secret:
                raise OverflowError("secret version capacity exhausted")
            history.append(_SecretValue(value))
            self.scopes[name] = normalized
            return len(history)

    def resolve(self, app: str, name: str) -> SecretLease:
        """Resolve the latest version to an immutable, context-bound lease.

        Missing and unauthorized references intentionally share the same external
        failure so callers cannot use this API as a secret-name existence oracle.
        """
        app = self._identifier(app, "app")
        name = self._identifier(name, "name")
        with self._lock:
            now = self._now()
            allowed = self.scopes.get(name)
            if not allowed or app not in allowed or name not in self.versions:
                self.audit.append(AuditEvent("resolve", app, name, False, "denied_or_unavailable", None, now))
                raise SecretDenied("secret is unavailable or application is not authorized")

            version = len(self.versions[name])
            if (name, version) in self.retired:
                self.audit.append(AuditEvent("resolve", app, name, False, "version_retired", version, now))
                raise VersionRetired(f"secret version {version} is retired")

            lease = SecretLease(
                app=app,
                name=name,
                version=version,
                issued_at=now,
                expires_at=now + float(self.lease_ttl),
                _secret=self.versions[name][-1],
                _issuer=self._issuer,
                _lease_id=self._next_lease_id,
            )
            self._next_lease_id += 1
            self.audit.append(AuditEvent("resolve", app, name, True, "granted", version, now))
            return lease

    def use(self, lease: SecretLease, app: str, name: str) -> str:
        """Reveal a leased value only after issuer, context, state, and time checks."""
        app = self._identifier(app, "app")
        name = self._identifier(name, "name")
        with self._lock:
            now = self._now()

            if not isinstance(lease, SecretLease) or lease._issuer is not self._issuer:
                self.audit.append(AuditEvent("use", app, name, False, "foreign_lease", None, now))
                raise LeaseContextMismatch("lease was not issued by this broker")
            if lease.app != app or lease.name != name:
                self.audit.append(AuditEvent("use", app, name, False, "context_mismatch", lease.version, now))
                raise LeaseContextMismatch("lease application/name context does not match")
            if lease._lease_id in self._revoked_lease_ids:
                self.audit.append(AuditEvent("use", app, name, False, "revoked", lease.version, now))
                raise LeaseRevoked("lease was revoked")
            if (lease.name, lease.version) in self.retired:
                self.audit.append(AuditEvent("use", app, name, False, "version_retired", lease.version, now))
                raise VersionRetired(f"secret version {lease.version} is retired")
            if now >= lease.expires_at:
                self.audit.append(AuditEvent("use", app, name, False, "expired", lease.version, now))
                raise LeaseExpired("lease ended; resolve again")

            self.audit.append(AuditEvent("use", app, name, True, "allowed", lease.version, now))
            return lease._secret._reveal()

    def revoke(self, lease: SecretLease) -> None:
        """Explicitly revoke a lease issued by this broker."""
        with self._lock:
            if not isinstance(lease, SecretLease) or lease._issuer is not self._issuer:
                raise LeaseContextMismatch("lease was not issued by this broker")
            self._revoked_lease_ids.add(lease._lease_id)

    def retire(self, name: str, version: int) -> None:
        """Retire a version so it can no longer be resolved or used."""
        name = self._identifier(name, "name")
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise ValueError("version must be a positive integer")
        with self._lock:
            if name not in self.versions or version > len(self.versions[name]):
                raise SecretNotFound(f"{name}@{version}")
            self.retired.add((name, version))


class SecretsIntegrationComponent(Component):
    """Master-applied component for INV-55."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        t = [0.0]
        b = SecretBroker(lease_ttl=60, clock=lambda: t[0])
        b.put("db-password", "hunter2-prod", apps=["orders"])
        lease = b.resolve("orders", "db-password")

        denied = False
        try:
            b.resolve("marketing", "db-password")
        except SecretDenied:
            denied = True

        diagnostic_text = " ".join(map(repr, b.audit)) + repr(lease) + f"{lease._secret}"
        _verify(
            denied
            and "hunter2" not in diagnostic_text
            and not isinstance(lease._secret, str)
            and b.use(lease, "orders", "db-password") == "hunter2-prod",
            "authorization/redaction behavior failed",
        )
        findings[0] = self.satisfied(
            items[0],
            "A secret resolves only for applications in scope. Secret-bearing objects are not str "
            "subclasses, diagnostics are redacted, audit events never carry values, and plaintext is "
            "returned only through an explicit broker use after context and lease checks.",
            *self._evidence(
                "component.py::_SecretValue",
                "component.py::SecretBroker.resolve",
                "component.py::SecretBroker.use",
            ),
        )

        t[0] = 61.0
        expired = False
        try:
            b.use(lease, "orders", "db-password")
        except LeaseExpired:
            expired = True
        _verify(expired, "lease expiry check failed")
        findings[1] = self.satisfied(
            items[1],
            "Broker-mediated use is time-bounded and rejects an expired lease. A production provider "
            "must additionally revoke or expire the underlying credential because plaintext already "
            "delivered to application code cannot be retroactively erased by this broker.",
            *self._evidence("component.py::SecretBroker.use"),
        )
        return findings

    def assess_operations(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_operations(items)
        t = [0.0]
        b = SecretBroker(clock=lambda: t[0])
        b.put("api-key", "v1-key", ["svc"])
        old = b.resolve("svc", "api-key")
        t[0] = 1.0
        b.put("api-key", "v2-key", ["svc"])
        new = b.resolve("svc", "api-key")
        t[0] = 2.0
        _verify(
            old.version == 1
            and new.version == 2
            and b.use(old, "svc", "api-key") == "v1-key"
            and b.use(new, "svc", "api-key") == "v2-key",
            "versioned rotation behavior failed",
        )
        findings[0] = self.satisfied(
            items[0],
            "Rotation adds a version rather than overwriting: existing leases remain bound to v1 until "
            "expiry/revocation/retirement while new resolutions receive v2.",
            *self._evidence("component.py::SecretBroker.put", "component.py::SecretBroker.use"),
        )
        return findings


COMPONENT = SecretsIntegrationComponent
