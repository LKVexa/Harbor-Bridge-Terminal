"""Machine-readable error model (GAP04-C19).

Every failure the runtime can surface carries a stable ``code`` from the
registry below, a category, a retryability flag, and a JSON-safe ``details``
mapping. Codes are append-only: a code is never reused or renumbered, and the
registry is versioned by ``ERROR_MODEL_VERSION``. Messages are informative;
callers must branch on ``code`` only.
"""
from __future__ import annotations

from typing import Any, Final, Mapping

ERROR_MODEL_VERSION: Final = "PK_GAP04_ERROR/1"

# code -> (category, retryable, http_status, description)
REGISTRY: Final[dict[str, tuple[str, bool, int, str]]] = {
    # lifecycle / state machine
    "GAP04-E0001": ("lifecycle", False, 409, "operation requires an active partition"),
    "GAP04-E0002": ("lifecycle", False, 409, "reconciliation required before this operation"),
    "GAP04-E0003": ("lifecycle", False, 400, "timestamp predates last state-changing event"),
    "GAP04-E0004": ("validation", False, 400, "input failed validation"),
    # authority
    "GAP04-E0100": ("authority", False, 403, "autonomy lease expired or absent"),
    "GAP04-E0101": ("authority", False, 403, "action not permitted at current tier"),
    "GAP04-E0102": ("authority", False, 403, "cached policy exceeds staleness bound"),
    "GAP04-E0103": ("authority", False, 403, "controller quarantined / emergency disabled"),
    "GAP04-E0104": ("authority", False, 403, "caller not authorized for this boundary"),
    "GAP04-E0105": ("authority", False, 403, "capability grant missing, revoked, or insufficient"),
    # crypto / lease / policy
    "GAP04-E0200": ("crypto", False, 401, "lease envelope malformed or non-canonical"),
    "GAP04-E0201": ("crypto", False, 401, "lease signature invalid"),
    "GAP04-E0202": ("crypto", False, 401, "unknown or revoked issuer / key id"),
    "GAP04-E0203": ("crypto", False, 401, "algorithm not in allow-list"),
    "GAP04-E0204": ("crypto", False, 401, "lease scope/binding mismatch"),
    "GAP04-E0205": ("crypto", False, 401, "lease time validity failure"),
    "GAP04-E0206": ("crypto", False, 401, "lease authority epoch stale or revoked"),
    "GAP04-E0207": ("crypto", False, 401, "lease policy digest mismatch"),
    "GAP04-E0208": ("crypto", False, 503, "trust store unavailable or crypto backend missing"),
    "GAP04-E0209": ("crypto", False, 401, "unsupported envelope version"),
    "GAP04-E0210": ("crypto", False, 401, "lease replay (nonce / lease id reused)"),
    "GAP04-E0220": ("policy", False, 401, "policy bundle signature/digest invalid"),
    "GAP04-E0221": ("policy", False, 409, "policy rollback / version not monotonic"),
    # time
    "GAP04-E0300": ("time", False, 503, "trusted time unavailable or rollback detected"),
    # durability
    "GAP04-E0400": ("storage", False, 507, "durable journal cannot append (capacity)"),
    "GAP04-E0401": ("storage", False, 500, "journal corruption detected"),
    "GAP04-E0402": ("storage", False, 500, "audit chain integrity failure"),
    "GAP04-E0403": ("storage", False, 500, "state store integrity / decryption failure"),
    "GAP04-E0404": ("storage", False, 409, "state schema version unsupported"),
    # fencing
    "GAP04-E0500": ("fencing", False, 409, "stale controller generation (fenced)"),
    "GAP04-E0501": ("fencing", True, 409, "another controller instance holds the ownership lock"),
    # reconciliation
    "GAP04-E0600": ("reconcile", True, 502, "reconciliation peer failure"),
    "GAP04-E0601": ("reconcile", False, 409, "reconciliation transaction id conflict"),
    # load
    "GAP04-E0700": ("overload", True, 429, "admission rejected: queue or concurrency limit"),
    "GAP04-E0701": ("overload", True, 503, "circuit open for dependency"),
    # config
    "GAP04-E0800": ("config", False, 400, "configuration invalid"),
    "GAP04-E0801": ("config", False, 409, "configuration activation conflict / rollback unavailable"),
    "GAP04-E0802": ("config", False, 403, "override lacks required approvals"),
    # adapters
    "GAP04-E0900": ("adapter", True, 502, "adjacent-layer adapter failure"),
    "GAP04-E0901": ("adapter", False, 409, "adjacent-layer contract version unsupported"),
}


class Gap04Error(Exception):
    """Base runtime error with a stable machine-readable code."""

    code: str = "GAP04-E0004"

    def __init__(self, message: str = "", *, code: str | None = None, details: Mapping[str, Any] | None = None):
        if code is not None:
            self.code = code
        if self.code not in REGISTRY:
            raise ValueError(f"unregistered error code {self.code}")
        self.details = dict(details or {})
        super().__init__(message or REGISTRY[self.code][3])

    @property
    def category(self) -> str:
        return REGISTRY[self.code][0]

    @property
    def retryable(self) -> bool:
        return REGISTRY[self.code][1]

    def to_dict(self) -> dict[str, Any]:
        cat, retry, status, desc = REGISTRY[self.code]
        return {
            "schema": ERROR_MODEL_VERSION,
            "code": self.code,
            "category": cat,
            "retryable": retry,
            "http_status": status,
            "summary": desc,
            "message": str(self),
            "details": self.details,
        }


def _mk(name: str, code: str) -> type[Gap04Error]:
    return type(name, (Gap04Error,), {"code": code, "__doc__": REGISTRY[code][3]})


LeaseInvalid = _mk("LeaseInvalid", "GAP04-E0200")
PolicyInvalid = _mk("PolicyInvalid", "GAP04-E0220")
TrustedTimeError = _mk("TrustedTimeError", "GAP04-E0300")
StorageFull = _mk("StorageFull", "GAP04-E0400")
JournalCorrupt = _mk("JournalCorrupt", "GAP04-E0401")
AuditIntegrityError = _mk("AuditIntegrityError", "GAP04-E0402")
StateIntegrityError = _mk("StateIntegrityError", "GAP04-E0403")
Fenced = _mk("Fenced", "GAP04-E0500")
Quarantined = _mk("Quarantined", "GAP04-E0103")
Unauthorized = _mk("Unauthorized", "GAP04-E0104")
Overloaded = _mk("Overloaded", "GAP04-E0700")
ConfigInvalid = _mk("ConfigInvalid", "GAP04-E0800")
AdapterError = _mk("AdapterError", "GAP04-E0900")
ReconcileError = _mk("ReconcileError", "GAP04-E0600")

# Mapping from the reference state-machine exception types to stable codes.
CONTROLLER_CODES: Final = {
    "NotPartitioned": "GAP04-E0001",
    "ReconciliationRequired": "GAP04-E0002",
    "LeaseExpired": "GAP04-E0100",
    "NotPermittedAtTier": "GAP04-E0101",
    "PolicyStale": "GAP04-E0102",
    "DecisionJournalFull": "GAP04-E0400",
}


def to_error(exc: BaseException) -> dict[str, Any]:
    """Convert any exception into the machine-readable error document."""
    if isinstance(exc, Gap04Error):
        return exc.to_dict()
    code = CONTROLLER_CODES.get(type(exc).__name__)
    if code is None:
        msg = str(exc)
        code = "GAP04-E0003" if "predates" in msg else "GAP04-E0004"
    return Gap04Error(str(exc), code=code, details={"exception": type(exc).__name__}).to_dict()
