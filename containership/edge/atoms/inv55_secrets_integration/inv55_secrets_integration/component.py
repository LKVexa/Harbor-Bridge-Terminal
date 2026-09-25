"""INV-55 - Secrets integration: pk_core conformance binding.

The reference primitives live in :mod:`reference` (importable without pk_core);
they are re-exported here so the 4.2.0 import surface is unchanged.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .reference import (  # noqa: F401  (re-exported API)
    AuditEvent, ClockRollbackError, InvalidSecretReference, LeaseContextMismatch, LeaseExpired,
    LeaseRevoked, SecretBroker, SecretDenied, SecretLease, SecretNotFound, VersionRetired,
    _SecretValue, _verify,
)


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
