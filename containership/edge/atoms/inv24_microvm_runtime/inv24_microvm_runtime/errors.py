"""Stable, machine-readable INV-24 error taxonomy (MC-001-I04, MC-013, MC-028).

Every error raised across an external boundary carries a stable ``code``, a
``category`` and an explicit ``retryable`` flag.  Runtime safety checks never
use ``assert``; they raise one of these classes so ``python -O`` cannot strip
them.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

ERROR_SCHEMA: Final[str] = "PK_MICROVM_ERROR/1"

#: code -> (category, retryable, description).  Codes are append-only.
ERROR_CODES: Final[dict[str, tuple[str, bool, str]]] = {
    "CONFIG_REJECTED": ("configuration", False, "configuration failed validation"),
    "DEVICE_OUTSIDE_MODEL": ("configuration", False, "device not in the minimal model"),
    "UNSUPPORTED_FIELD": ("configuration", False, "field not permitted by the adapter"),
    "ARTIFACT_UNPINNED": ("integrity", False, "artifact has no approved digest pin"),
    "ARTIFACT_DIGEST_MISMATCH": ("integrity", False, "artifact bytes do not match the pin"),
    "ARTIFACT_NOT_APPROVED": ("integrity", False, "artifact is not on the approved list"),
    "VERSION_MISMATCH": ("compatibility", False, "component version is not supported"),
    "HOST_KVM_UNAVAILABLE": ("host", False, "/dev/kvm is absent"),
    "HOST_KVM_PERMISSION": ("host", False, "/dev/kvm cannot be opened by this identity"),
    "HOST_KVM_INCOMPATIBLE": ("host", False, "KVM API version or capability unsupported"),
    "HOST_KVM_TRANSIENT": ("host", True, "transient KVM probe failure"),
    "GUEST_BOOT_FAILED": ("guest", False, "guest kernel did not start"),
    "BOOT_BUDGET_EXCEEDED": ("performance", False, "cold boot exceeded its budget"),
    "TIMEOUT": ("deadline", True, "operation deadline elapsed"),
    "CANCELLED": ("deadline", False, "operation was cancelled by the caller"),
    "PROCESS_CRASHED": ("process", True, "VMM process exited unexpectedly"),
    "CLEANUP_FAILED": ("process", False, "deterministic cleanup did not complete"),
    "UNAUTHENTICATED": ("security", False, "identity missing or invalid"),
    "UNAUTHORIZED": ("security", False, "capability missing, expired or insufficient"),
    "REPLAY_DETECTED": ("security", False, "token nonce was already used"),
    "TENANT_MISMATCH": ("security", False, "resource belongs to another tenant"),
    "KEY_UNAVAILABLE": ("security", False, "required key material is missing"),
    "INTEGRITY_VIOLATION": ("security", False, "hash chain or signature verification failed"),
    "QUOTA_EXCEEDED": ("capacity", False, "tenant or fleet quota would be exceeded"),
    "OVERLOADED": ("capacity", True, "admission queue full; retry with backoff"),
    "CIRCUIT_OPEN": ("dependency", True, "dependency breaker open"),
    "DEPENDENCY_UNAVAILABLE": ("dependency", True, "required dependency is unhealthy"),
    "DUPLICATE_OPERATION": ("idempotency", False, "operation key already bound to different input"),
    "STALE_EPOCH": ("ownership", False, "fencing token is older than the current lease"),
    "LEASE_HELD": ("ownership", True, "another owner holds the lease"),
    "QUARANTINED": ("operations", False, "tenant, node or instance is quarantined"),
    "ADMISSION_FROZEN": ("operations", False, "admission frozen by operator"),
    "DEGRADED_REFUSED": ("operations", True, "operation disallowed in degraded mode"),
    "SNAPSHOT_INVALID": ("snapshot", False, "snapshot metadata or artifact invalid"),
    "SNAPSHOT_INCOMPATIBLE": ("snapshot", False, "snapshot incompatible with this host/runtime"),
    "DATAPATH_UNAVAILABLE": ("io", False, "accelerated datapath absent; policy rejects fallback"),
    "DESCRIPTOR_OUT_OF_BOUNDS": ("io", False, "descriptor outside a registered guest region"),
    "SCHEMA_VIOLATION": ("schema", False, "payload does not satisfy its schema"),
    "RESOURCE_EXHAUSTED": ("capacity", True, "bounded resource pool exhausted"),
}


@dataclass(frozen=True, slots=True)
class ErrorRecord:
    code: str
    message: str
    category: str
    retryable: bool

    def to_dict(self) -> dict[str, object]:
        return {"schema": ERROR_SCHEMA, "code": self.code, "category": self.category,
                "retryable": self.retryable, "message": self.message[:512]}


class Inv24Error(Exception):
    """Base structured error; ``code`` must be registered in ERROR_CODES."""

    def __init__(self, code: str, message: str = "") -> None:
        if code not in ERROR_CODES:
            code, message = "CONFIG_REJECTED", f"unregistered error code {code!r}: {message}"
        category, retryable, desc = ERROR_CODES[code]
        self.record = ErrorRecord(code, message or desc, category, retryable)
        super().__init__(f"[{code}] {message or desc}")

    @property
    def code(self) -> str:
        return self.record.code

    @property
    def retryable(self) -> bool:
        return self.record.retryable

    def to_dict(self) -> dict[str, object]:
        return self.record.to_dict()


def require(condition: object, code: str, message: str) -> None:
    """Optimiser-proof guard used instead of ``assert`` for enforcement."""
    if not condition:
        raise Inv24Error(code, message)
