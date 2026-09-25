"""Dependency-free runtime primitives for PLN-06 - Data plane.

This module deliberately does not import ``pk_core``.  It is the executable
reference logic used by the certification adapter in :mod:`component` and can
be unit-tested or embedded independently.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Collection, Mapping
from datetime import datetime, timezone
from threading import RLock
from types import MappingProxyType
from uuid import uuid4

from .metadata import VERSION

TRANSPORT_TIERS = (
    ("inline", 64 * 1024),
    ("local", 64 * 1024 * 1024),
    ("bulk", 64 * 1024 * 1024 * 1024),
)
CONTROL_INLINE_LIMIT = TRANSPORT_TIERS[0][1]

# ``auto`` preserves the pre-4.2 size-only behavior.  Explicit locality may
# promote a transfer to a transport that cannot accidentally use a less
# isolated path than the caller requested.
LOCALITY_FLOOR = MappingProxyType({
    "auto": 0,
    "in_process": 0,
    "vm_control": 0,  # 4.3: VM-control messages over the control transport (inline only)
    "same_node": 1,
    "same_host_vm": 1,
    "remote": 2,
})


class _StructuredError(Exception):
    """Mixin providing stable machine-readable error information."""

    code = "PK_DATA_PLANE_ERROR"
    retryable = False

    def __init__(self, message: str, *, retryable: bool | None = None, **details: object) -> None:
        super().__init__(message)
        if retryable is not None:
            self.retryable = bool(retryable)
        self.details = dict(details)

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": str(self),
            "retryable": self.retryable,
            "details": dict(self.details),
        }


class InvalidRequest(_StructuredError, ValueError):
    """Raised when transfer input is malformed."""

    code = "PK_TRANSFER_INVALID"


class InvalidCompletion(_StructuredError, ValueError):
    """Raised when a completion record conflicts with the admitted transfer."""

    code = "PK_TRANSFER_COMPLETION_INVALID"


class ResidencyViolation(_StructuredError, PermissionError):
    """Raised when a destination site may not hold the payload classification."""

    code = "PK_RESIDENCY_VIOLATION"


class NoTransportTier(_StructuredError, RuntimeError):
    """Raised when no configured tier covers the payload size."""

    code = "PK_TRANSPORT_TIER_UNAVAILABLE"


class Backpressure(_StructuredError, RuntimeError):
    """Raised when the bulk path is saturated; the caller may retry later."""

    code = "PK_BACKPRESSURE"
    retryable = True


class DataPlane:
    """Admit and route transfers under residency, locality, and capacity rules.

    The object is safe for concurrent admission/completion from threads.  The
    residency policy is copied and validated on construction so later mutation
    of the caller's object cannot silently alter an active instance.
    """

    def __init__(
        self,
        residency: Mapping[str, Collection[str]],
        *,
        inflight_limit: int = 4,
        per_tenant_inflight_limit: int | None = None,
        config_revision: str = "bootstrap",
        config_author: str = "constructor",
    ):
        if isinstance(inflight_limit, bool) or not isinstance(inflight_limit, int) or inflight_limit < 1:
            raise InvalidRequest(
                "inflight_limit must be a positive int",
                field="inflight_limit",
                value=repr(inflight_limit),
            )
        if per_tenant_inflight_limit is not None:
            if (
                isinstance(per_tenant_inflight_limit, bool)
                or not isinstance(per_tenant_inflight_limit, int)
                or per_tenant_inflight_limit < 1
            ):
                raise InvalidRequest(
                    "per_tenant_inflight_limit must be a positive int or None",
                    field="per_tenant_inflight_limit",
                    value=repr(per_tenant_inflight_limit),
                )
            if per_tenant_inflight_limit > inflight_limit:
                raise InvalidRequest(
                    "per_tenant_inflight_limit cannot exceed inflight_limit",
                    field="per_tenant_inflight_limit",
                )
        self._residency = self._normalize_residency(residency)
        self._inflight_limit = inflight_limit
        self._per_tenant_inflight_limit = per_tenant_inflight_limit
        self._open: dict[str, dict[str, object]] = {}
        self._tenant_open: Counter[str] = Counter()
        self._lock = RLock()
        self._config = {
            "revision": self._require_text("config_revision", config_revision),
            "author": self._require_text("config_author", config_author),
            "activated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._tier_bytes: Counter[str] = Counter()
        self._admitted: Counter[str] = Counter()
        self._residency_refusals: Counter[str] = Counter()
        self._backpressure_events = 0
        self._completed = 0
        self._cancelled = 0

    @staticmethod
    def _require_text(name: str, value: object) -> str:
        if not isinstance(value, str) or not value.strip():
            raise InvalidRequest(f"{name} must be a non-empty string", field=name, value=repr(value))
        return value.strip()

    @classmethod
    def _normalize_residency(cls, residency: Mapping[str, Collection[str]]) -> dict[str, frozenset[str]]:
        if not isinstance(residency, Mapping):
            raise InvalidRequest("residency must be a mapping", field="residency")
        out: dict[str, frozenset[str]] = {}
        for raw_site, raw_classes in residency.items():
            site = cls._require_text("site", raw_site)
            if isinstance(raw_classes, (str, bytes)) or not isinstance(raw_classes, Collection):
                raise InvalidRequest(
                    "residency classifications must be a collection of strings",
                    field=f"residency[{site!r}]",
                )
            if site in out:
                raise InvalidRequest(
                    "duplicate site after normalization",
                    field="residency",
                    site=site,
                )
            classes = frozenset(cls._require_text("classification", item) for item in raw_classes)
            out[site] = classes
        return out

    @property
    def inflight_limit(self) -> int:
        return self._inflight_limit

    @property
    def per_tenant_inflight_limit(self) -> int | None:
        return self._per_tenant_inflight_limit

    @property
    def inflight(self) -> int:
        with self._lock:
            return len(self._open)

    @property
    def control_bytes(self) -> int:
        with self._lock:
            return self._tier_bytes["inline"]

    @property
    def bulk_bytes(self) -> int:
        with self._lock:
            return self._tier_bytes["local"] + self._tier_bytes["bulk"]

    def residency_snapshot(self) -> dict[str, frozenset[str]]:
        """Return a detached read-only-by-convention copy of the active policy."""
        with self._lock:
            return dict(self._residency)

    def config_snapshot(self) -> dict[str, object]:
        """Return active configuration provenance without exposing policy contents."""
        with self._lock:
            return {
                **self._config,
                "inflight_limit": self._inflight_limit,
                "per_tenant_inflight_limit": self._per_tenant_inflight_limit,
                "site_count": len(self._residency),
            }

    def replace_residency(
        self,
        residency: Mapping[str, Collection[str]],
        *,
        revision: str,
        author: str,
    ) -> None:
        """Atomically replace residency policy without invalidating live transfers.

        The candidate is validated before the lock is taken.  Activation fails
        closed if any in-flight transfer would become illegal under the new
        policy; callers can retry after those transfers finish or are cancelled.
        """
        candidate = self._normalize_residency(residency)
        revision = self._require_text("revision", revision)
        author = self._require_text("author", author)
        with self._lock:
            violations = [
                transfer_id
                for transfer_id, record in self._open.items()
                if record["classification"]
                not in candidate.get(str(record["destination"]), frozenset())
            ]
            if violations:
                raise InvalidRequest(
                    "residency update would invalidate live transfers",
                    field="residency",
                    active_violations=len(violations),
                )
            self._residency = candidate
            self._config = {
                "revision": revision,
                "author": author,
                "activated_at": datetime.now(timezone.utc).isoformat(),
            }

    def permitted(self, site: str, classification: str) -> bool:
        site = self._require_text("site", site)
        classification = self._require_text("classification", classification)
        with self._lock:
            return classification in self._residency.get(site, frozenset())

    @staticmethod
    def tier_for(size: int, locality: str = "auto") -> str:
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise InvalidRequest("size must be a non-negative int", field="size", value=repr(size))
        locality = DataPlane._require_text("locality", locality)
        if locality not in LOCALITY_FLOOR:
            raise InvalidRequest(
                f"unsupported locality {locality!r}",
                field="locality",
                allowed=tuple(LOCALITY_FLOOR),
            )

        base_index = None
        for index, (_name, bound) in enumerate(TRANSPORT_TIERS):
            if size <= bound:
                base_index = index
                break
        if base_index is None:
            raise NoTransportTier(
                f"payload of {size} bytes exceeds every configured tier",
                size=size,
                maximum=TRANSPORT_TIERS[-1][1],
            )
        return TRANSPORT_TIERS[max(base_index, LOCALITY_FLOOR[locality])][0]

    def admit(
        self,
        *,
        tenant: str,
        workload: str,
        size: int,
        classification: str,
        destination: str,
        locality: str = "auto",
        digest: str | None = None,
    ) -> dict[str, object]:
        """Admit one transfer and return a versioned routing decision.

        ``locality='auto'`` retains the legacy size-only selection behavior.
        Callers that know topology should provide ``in_process``, ``same_node``,
        ``same_host_vm``, ``remote`` or (4.3) ``vm_control``.  A supplied digest must be a SHA-256
        hex value; otherwise the concrete transport remains responsible for
        calculating and validating it before delivery.
        """
        tenant = self._require_text("tenant", tenant)
        workload = self._require_text("workload", workload)
        classification = self._require_text("classification", classification)
        destination = self._require_text("destination", destination)
        locality = self._require_text("locality", locality)
        digest = self._validate_digest(digest)

        # Validate size/locality syntax before locking, but resolve the tier only
        # after residency admission so residency remains the authoritative gate.
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise InvalidRequest("size must be a non-negative int", field="size", value=repr(size))
        if locality not in LOCALITY_FLOOR:
            raise InvalidRequest(
                f"unsupported locality {locality!r}",
                field="locality",
                allowed=tuple(LOCALITY_FLOOR),
            )

        with self._lock:
            if classification not in self._residency.get(destination, frozenset()):
                self._residency_refusals[f"{classification}@{destination}"] += 1
                raise ResidencyViolation(
                    f"{destination!r} may not hold classification {classification!r}",
                    destination=destination,
                    classification=classification,
                )

            tier = self.tier_for(size, locality)
            transfer_id: str | None = None
            if tier != "inline":
                if len(self._open) >= self._inflight_limit:
                    self._backpressure_events += 1
                    raise Backpressure(
                        f"bulk path saturated at {len(self._open)} in-flight transfers",
                        scope="global",
                        inflight=len(self._open),
                        limit=self._inflight_limit,
                    )
                if (
                    self._per_tenant_inflight_limit is not None
                    and self._tenant_open[tenant] >= self._per_tenant_inflight_limit
                ):
                    self._backpressure_events += 1
                    raise Backpressure(
                        f"tenant {tenant!r} saturated at {self._tenant_open[tenant]} in-flight transfers",
                        scope="tenant",
                        inflight=self._tenant_open[tenant],
                        limit=self._per_tenant_inflight_limit,
                    )
                transfer_id = uuid4().hex

            decision: dict[str, object] = {
                "schema": "PK_TRANSFER/1",
                "tenant": tenant,
                "workload": workload,
                "tier": tier,
                "size": size,
                "classification": classification,
                "destination": destination,
                "locality": locality,
                "digest_required": True,
                "digest_algorithm": "sha256",
                "digest": digest,
                "transfer_id": transfer_id,
                "config_revision": self._config["revision"],
                "reason": f"selected {tier} for size={size} locality={locality}",
            }
            self._tier_bytes[tier] += size
            self._admitted[tier] += 1
            if transfer_id is not None:
                self._open[transfer_id] = self._completion_record(decision)
                self._tenant_open[tenant] += 1
            return decision

    @staticmethod
    def _validate_digest(digest: str | None) -> str | None:
        if digest is None:
            return None
        if not isinstance(digest, str) or len(digest) != 64:
            raise InvalidRequest("digest must be a 64-character SHA-256 hex string", field="digest")
        try:
            int(digest, 16)
        except ValueError as exc:
            raise InvalidRequest("digest must be hexadecimal", field="digest") from exc
        return digest.lower()

    @staticmethod
    def _completion_record(decision: Mapping[str, object]) -> dict[str, object]:
        keys = (
            "schema", "tenant", "workload", "tier", "size", "classification",
            "destination", "locality", "transfer_id", "config_revision",
        )
        return {key: decision.get(key) for key in keys}

    def _release(self, decision: Mapping[str, object], *, outcome: str) -> bool:
        if not isinstance(decision, Mapping):
            raise InvalidCompletion("decision must be a mapping", field="decision")
        if decision.get("tier") == "inline":
            return False
        transfer_id = decision.get("transfer_id")
        if not isinstance(transfer_id, str) or not transfer_id:
            return False
        with self._lock:
            expected = self._open.get(transfer_id)
            if expected is None:
                return False
            actual = self._completion_record(decision)
            if actual != expected:
                raise InvalidCompletion(
                    "completion metadata does not match the admitted transfer",
                    transfer_id=transfer_id,
                )
            del self._open[transfer_id]
            tenant = str(expected["tenant"])
            self._tenant_open[tenant] -= 1
            if self._tenant_open[tenant] <= 0:
                del self._tenant_open[tenant]
            if outcome == "completed":
                self._completed += 1
            else:
                self._cancelled += 1
            return True

    def complete(self, decision: Mapping[str, object]) -> bool:
        """Release capacity exactly once for a matching admitted transfer."""
        return self._release(decision, outcome="completed")

    def cancel(self, decision: Mapping[str, object]) -> bool:
        """Cancel an admitted non-inline transfer, releasing its capacity once."""
        return self._release(decision, outcome="cancelled")

    def health(self) -> dict[str, object]:
        """Return a stable health/readiness snapshot for operator integration."""
        with self._lock:
            return {
                "schema": "PK_DATA_PLANE_HEALTH/1",
                "element": "PLN-06",
                "version": VERSION,
                "healthy": True,
                "ready": True,
                "inflight": len(self._open),
                "inflight_limit": self._inflight_limit,
                "config_revision": self._config["revision"],
                "capabilities": [
                    "residency-admission",
                    "locality-tier-selection",
                    "bounded-backpressure",
                    "structured-errors",
                    "runtime-metrics",
                ],
            }

    def metrics(self) -> dict[str, object]:
        """Return a detached structured snapshot suitable for telemetry export."""
        with self._lock:
            return {
                "schema": "PK_DATA_PLANE_METRICS/1",
                "inflight": len(self._open),
                "inflight_limit": self._inflight_limit,
                "per_tenant_inflight_limit": self._per_tenant_inflight_limit,
                "admitted_by_tier": dict(self._admitted),
                "bytes_by_tier": dict(self._tier_bytes),
                "residency_refusals": dict(self._residency_refusals),
                "backpressure_events": self._backpressure_events,
                "completed": self._completed,
                "cancelled": self._cancelled,
            }
