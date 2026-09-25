"""Hardened runtime primitives for GAP-09 unified observability.

This module deliberately has no dependency on ``pk_core`` so the data-plane
logic can be tested and embedded independently.  Production trust must enter
through :meth:`SignalStore.submit_verified`; the legacy boolean trust shim is
fail-closed unless explicitly enabled for compatibility/conformance fixtures.
"""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import math
import threading
import unicodedata
from itertools import islice
from typing import Any, Iterable, Mapping, Protocol, Sequence
from types import MappingProxyType

STALENESS_BOUND = 60
ABSENT = None
MAX_TEXT = 256
MAX_SIGNATURE_SIZE = 16_384
MAX_ATTESTATION_FIELDS = 64
MAX_TIMESTAMP = (1 << 63) - 1
MAX_NUMERIC_MAGNITUDE = float.fromhex("0x1.fffffffffffffp+1023")


class SignalError(Exception):
    """Base exception carrying a stable machine-readable error code."""

    code = "signal_error"

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message)
        self.details = details

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), "details": dict(self.details)}


class ReporterUntrusted(SignalError, PermissionError):
    code = "reporter_untrusted"


class TrustUnavailable(SignalError, RuntimeError):
    code = "trust_unavailable"


class Unattributed(SignalError, ValueError):
    code = "unattributed"


class CrossTenantQuery(SignalError, PermissionError):
    code = "cross_tenant_query"


class InvalidSample(SignalError, ValueError):
    code = "invalid_sample"


class InvalidBatch(SignalError, ValueError):
    code = "invalid_batch"


class InvalidTime(SignalError, ValueError):
    code = "invalid_time"


class ReplayDetected(SignalError, PermissionError):
    code = "replay_detected"


class ScopeViolation(SignalError, PermissionError):
    code = "scope_violation"


class TimestampConflict(SignalError, ValueError):
    code = "timestamp_conflict"


class CapacityExceeded(SignalError, RuntimeError):
    code = "capacity_exceeded"


@dataclass(frozen=True, slots=True)
class Sample:
    signal: str
    value: float
    tenant: str
    environment: str
    site: str
    workload: str
    at: int


@dataclass(frozen=True, slots=True)
class StoredSample:
    """Accepted sample plus immutable ingestion provenance."""

    sample: Sample
    reporter: str
    received_at: int
    submission_id: str | None


@dataclass(frozen=True, slots=True)
class ReporterAuthority:
    """Authorization result returned by the identity/signature trust boundary.

    Wildcards are explicit.  A production verifier should construct this from
    GAP-06 attestation claims plus GAP-07 signature/provenance verification;
    callers do not get to assert these fields directly.
    """

    reporter: str
    attested_level: str
    tenants: frozenset[str]
    environments: frozenset[str] = frozenset({"*"})
    sites: frozenset[str] = frozenset({"*"})
    workloads: frozenset[str] = frozenset({"*"})
    expires_at: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.reporter, str) or not self.reporter or self.reporter != self.reporter.strip():
            raise ValueError("authority reporter must be a non-empty normalized string")
        if len(self.reporter) > MAX_TEXT:
            raise ValueError("authority reporter is too long")
        if self.attested_level not in {"software", "hardware"}:
            raise ValueError("authority attested_level must be software or hardware")
        for name, scopes in (
            ("tenants", self.tenants),
            ("environments", self.environments),
            ("sites", self.sites),
            ("workloads", self.workloads),
        ):
            if not isinstance(scopes, frozenset) or not scopes:
                raise ValueError(f"authority {name} must be a non-empty frozenset")
            for scope in scopes:
                if not isinstance(scope, str) or not scope or scope != scope.strip() or len(scope) > MAX_TEXT:
                    raise ValueError(f"authority {name} contains an invalid scope")
        if self.expires_at is not None and (isinstance(self.expires_at, bool) or not isinstance(self.expires_at, int)):
            raise ValueError("authority expires_at must be an integer timestamp or None")

    def permits(self, sample: Sample) -> bool:
        return (
            ("*" in self.tenants or sample.tenant in self.tenants)
            and ("*" in self.environments or sample.environment in self.environments)
            and ("*" in self.sites or sample.site in self.sites)
            and ("*" in self.workloads or sample.workload in self.workloads)
        )


class TrustVerifier(Protocol):
    """Boundary adapter expected from GAP-06/GAP-07 integration."""

    def verify(
        self,
        *,
        reporter: str,
        payload: bytes,
        signature: bytes | str,
        attestation: Mapping[str, Any],
        now: int,
    ) -> ReporterAuthority:
        """Return verified authority or raise :class:`ReporterUntrusted`."""


class HMACFixtureVerifier:
    """Deterministic stdlib verifier for tests and local conformance only.

    This is not a replacement for production asymmetric signatures or hardware
    attestation.  It exists so security behavior can be exercised without
    optional crypto dependencies.
    """

    def __init__(
        self,
        keys: Mapping[tuple[str, str], bytes],
        authorities: Mapping[str, ReporterAuthority],
    ) -> None:
        self._keys = dict(keys)
        self._authorities = dict(authorities)

    @staticmethod
    def sign(key: bytes, payload: bytes) -> str:
        return hmac.new(key, payload, hashlib.sha256).hexdigest()

    def verify(
        self,
        *,
        reporter: str,
        payload: bytes,
        signature: bytes | str,
        attestation: Mapping[str, Any],
        now: int,
    ) -> ReporterAuthority:
        key_id = attestation.get("key_id") if isinstance(attestation, Mapping) else None
        if not isinstance(key_id, str) or not key_id or len(key_id) > MAX_TEXT:
            raise ReporterUntrusted(f"{reporter}: attestation key_id is missing or malformed")
        authority = self._authorities.get(reporter)
        key = self._keys.get((reporter, key_id))
        if authority is None or key is None:
            raise ReporterUntrusted(f"{reporter}: no approved attestation/key binding")
        if authority.reporter != reporter or authority.attested_level not in {"software", "hardware"}:
            raise ReporterUntrusted(f"{reporter}: invalid attested authority")
        if authority.expires_at is not None and now >= authority.expires_at:
            raise ReporterUntrusted(f"{reporter}: attestation expired")
        expected = self.sign(key, payload)
        if isinstance(signature, bytes):
            try:
                supplied = signature.decode("ascii")
            except UnicodeDecodeError as exc:
                raise ReporterUntrusted(f"{reporter}: signature is not ASCII hex") from exc
        elif isinstance(signature, str):
            supplied = signature
        else:
            raise ReporterUntrusted(f"{reporter}: signature type is invalid")
        try:
            supplied.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ReporterUntrusted(f"{reporter}: signature is not ASCII hex") from exc
        if len(supplied) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in supplied):
            raise ReporterUntrusted(f"{reporter}: signature is not a SHA-256 hex digest")
        if not hmac.compare_digest(expected, supplied.lower()):
            raise ReporterUntrusted(f"{reporter}: signature verification failed")
        return authority


def _validate_time(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidTime(f"{name} must be an integer timestamp", field=name)
    if value < 0 or value > MAX_TIMESTAMP:
        raise InvalidTime(
            f"{name} must be between 0 and {MAX_TIMESTAMP}",
            field=name,
            maximum=MAX_TIMESTAMP,
        )
    return value


def _validate_text(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise InvalidSample(f"{name} must be a string", field=name)
    if not value or not value.strip():
        raise InvalidSample(f"{name} must not be empty", field=name)
    if value != value.strip():
        raise InvalidSample(f"{name} must not contain leading/trailing whitespace", field=name)
    if unicodedata.normalize("NFC", value) != value:
        raise InvalidSample(f"{name} must use NFC Unicode normalization", field=name)
    if any(unicodedata.category(ch).startswith("C") for ch in value):
        raise InvalidSample(f"{name} must not contain control/format characters", field=name)
    if len(value) > MAX_TEXT:
        raise InvalidSample(f"{name} exceeds {MAX_TEXT} characters", field=name, limit=MAX_TEXT)
    return value


def _canonical_payload(reporter: str, submission_id: str, issued_at: int, samples: Sequence[Sample]) -> bytes:
    obj = {
        "schema": "PK_SIGNAL_SUBMISSION/2",
        "reporter": reporter,
        "submission_id": submission_id,
        "issued_at": issued_at,
        "samples": [
            {
                "signal": s.signal,
                "value": s.value,
                "tenant": s.tenant,
                "environment": s.environment,
                "site": s.site,
                "workload": s.workload,
                "at": s.at,
            }
            for s in samples
        ],
    }
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


@dataclass
class SignalStore:
    """In-memory, tenant-attributed latest-value store with fail-closed trust.

    The store is intentionally bounded and thread-safe.  It is a reference
    runtime, not a durable telemetry database; persistence, replication and
    long-term retention belong to adjacent production components.
    """

    staleness_bound: int = STALENESS_BOUND
    reporters_silent_after: int = STALENESS_BOUND
    max_batch_size: int = 1_000
    max_signals: int = 100_000
    max_reporters: int = 10_000
    max_rejections: int = 1_000
    max_replay_ids: int = 100_000
    max_signature_size: int = MAX_SIGNATURE_SIZE
    max_attestation_fields: int = MAX_ATTESTATION_FIELDS
    trust_verifier: TrustVerifier | None = None
    allow_legacy_trust: bool = False
    _latest: dict[tuple[str, str, str, str, str], StoredSample] = field(default_factory=dict, init=False, repr=False)
    _last_submission: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _rejected: deque[dict[str, Any]] = field(default_factory=deque, init=False, repr=False)
    _seen_submission_ids: set[tuple[str, str]] = field(default_factory=set, init=False, repr=False)
    _replay_fifo: deque[tuple[str, str]] = field(default_factory=deque, init=False, repr=False)
    _metrics: Counter[str] = field(default_factory=Counter, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    def __post_init__(self) -> None:
        for name in (
            "staleness_bound",
            "reporters_silent_after",
            "max_batch_size",
            "max_signals",
            "max_reporters",
            "max_rejections",
            "max_replay_ids",
            "max_signature_size",
            "max_attestation_fields",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")

    def canonical_submission_payload(
        self, *, reporter: str, submission_id: str, issued_at: int, samples: Sequence[Sample]
    ) -> bytes:
        """Return deterministic bytes that production signature adapters verify."""
        reporter_s, sample_tuple, issued_i = self._prepare(reporter, samples, issued_at)
        submission_s = _validate_text(submission_id, "submission_id")
        return _canonical_payload(reporter_s, submission_s, issued_i, sample_tuple)

    @property
    def latest(self) -> Mapping[tuple[str, str, str, str, str], StoredSample]:
        """Immutable snapshot of latest signal state."""
        with self._lock:
            return MappingProxyType(dict(self._latest))

    @property
    def last_submission(self) -> Mapping[str, int]:
        """Immutable snapshot of reporter liveness state."""
        with self._lock:
            return MappingProxyType(dict(self._last_submission))

    @property
    def rejected(self) -> tuple[dict[str, Any], ...]:
        """Immutable snapshot of the bounded rejection audit buffer."""
        with self._lock:
            return tuple(dict(item) for item in self._rejected)

    def _record_rejection(self, reporter: Any, error: SignalError, now: Any) -> None:
        if isinstance(reporter, str):
            reporter_label = reporter[:MAX_TEXT]
        else:
            reporter_label = f"<{type(reporter).__name__}>"
        event = {
            "reporter": reporter_label,
            "reason": error.code,
            "at": now if isinstance(now, int) and not isinstance(now, bool) else None,
        }
        with self._lock:
            self._rejected.append(event)
            while len(self._rejected) > self.max_rejections:
                self._rejected.popleft()
            self._metrics["rejected_submissions"] += 1
            self._metrics[f"rejected.{error.code}"] += 1

    def _prepare(self, reporter: Any, samples: Iterable[Sample], now: Any) -> tuple[str, tuple[Sample, ...], int]:
        now_i = _validate_time(now, "now")
        reporter_s = _validate_text(reporter, "reporter")
        if isinstance(samples, (str, bytes, bytearray)):
            raise InvalidBatch("samples must be an iterable of Sample objects")
        try:
            iterator = iter(samples)
        except TypeError as exc:
            raise InvalidBatch("samples must be iterable") from exc
        batch = tuple(islice(iterator, self.max_batch_size + 1))
        if not batch:
            raise InvalidBatch("empty submissions are refused")
        if len(batch) > self.max_batch_size:
            raise CapacityExceeded(
                f"batch exceeds limit {self.max_batch_size}",
                limit=self.max_batch_size,
            )
        for sample in batch:
            if not isinstance(sample, Sample):
                raise InvalidSample("every batch member must be a Sample")
            for name in ("signal", "tenant", "environment", "site", "workload"):
                try:
                    _validate_text(getattr(sample, name), name)
                except InvalidSample as exc:
                    if name in {"tenant", "environment", "site", "workload"}:
                        raise Unattributed(str(exc), field=name) from exc
                    raise
            at = _validate_time(sample.at, "sample.at")
            if at > now_i:
                raise InvalidTime(
                    f"{sample.signal}: sample dated {at} is in the future (now {now_i})",
                    signal=sample.signal,
                )
            if isinstance(sample.value, bool) or not isinstance(sample.value, (int, float)):
                raise InvalidSample(
                    f"{sample.signal}: value must be a finite binary64-range number",
                    signal=sample.signal,
                    value_type=type(sample.value).__name__,
                )
            if isinstance(sample.value, float) and not math.isfinite(sample.value):
                raise InvalidSample(
                    f"{sample.signal}: value must be finite",
                    signal=sample.signal,
                    value_type=type(sample.value).__name__,
                )
            if abs(sample.value) > MAX_NUMERIC_MAGNITUDE:
                raise InvalidSample(
                    f"{sample.signal}: value exceeds the supported binary64 magnitude",
                    signal=sample.signal,
                    value_type=type(sample.value).__name__,
                )
        return reporter_s, batch, now_i

    def _authorize(self, authority: ReporterAuthority, samples: Sequence[Sample], now: int) -> None:
        if authority.attested_level not in {"software", "hardware"}:
            raise ReporterUntrusted(f"{authority.reporter}: unsupported attestation level")
        if authority.expires_at is not None and now >= authority.expires_at:
            raise ReporterUntrusted(f"{authority.reporter}: attestation expired")
        for sample in samples:
            if not authority.permits(sample):
                raise ScopeViolation(
                    f"{authority.reporter}: not authorized for "
                    f"{sample.tenant}/{sample.environment}/{sample.site}/{sample.workload}",
                    tenant=sample.tenant,
                    environment=sample.environment,
                    site=sample.site,
                    workload=sample.workload,
                )

    def _commit(
        self,
        reporter: str,
        samples: Sequence[Sample],
        now: int,
        *,
        submission_id: str | None,
    ) -> int:
        with self._lock:
            updates: dict[tuple[str, str, str, str, str], StoredSample] = {}
            new_keys: set[tuple[str, str, str, str, str]] = set()
            changed = 0
            ignored = 0
            for sample in samples:
                key = (sample.tenant, sample.environment, sample.site, sample.workload, sample.signal)
                existing = updates.get(key, self._latest.get(key))
                candidate = StoredSample(
                    sample=sample, reporter=reporter, received_at=now, submission_id=submission_id
                )
                if existing is None:
                    updates[key] = candidate
                    if key not in self._latest:
                        new_keys.add(key)
                    changed += 1
                elif sample.at > existing.sample.at:
                    updates[key] = candidate
                    changed += 1
                elif sample.at == existing.sample.at:
                    if sample == existing.sample and reporter == existing.reporter:
                        ignored += 1
                    else:
                        raise TimestampConflict(
                            f"{sample.signal}: conflicting observation at timestamp {sample.at}",
                            signal=sample.signal,
                            at=sample.at,
                            existing_reporter=existing.reporter,
                            incoming_reporter=reporter,
                        )
                else:
                    ignored += 1
            if len(self._latest) + len(new_keys) > self.max_signals:
                raise CapacityExceeded(
                    f"signal cardinality would exceed {self.max_signals}",
                    limit=self.max_signals,
                )
            if reporter not in self._last_submission and len(self._last_submission) >= self.max_reporters:
                raise CapacityExceeded(
                    f"reporter cardinality would exceed {self.max_reporters}",
                    limit=self.max_reporters,
                )
            self._latest.update(updates)
            self._last_submission[reporter] = now
            self._metrics["ingested_signals"] += len(samples)
            self._metrics["updated_signals"] += changed
            self._metrics["ignored_out_of_order_or_duplicate"] += ignored
            return len(samples)

    def submit_verified(
        self,
        reporter: str,
        samples: Iterable[Sample],
        *,
        submission_id: str,
        issued_at: int,
        signature: bytes | str,
        attestation: Mapping[str, Any],
        now: int,
    ) -> int:
        """Authenticate, authorize and atomically ingest a signed submission.

        ``trust_verifier`` must be wired to the real GAP-06/GAP-07 trust path in
        production.  A unique ``submission_id`` provides explicit replay
        detection within this reference store's bounded replay cache.
        """
        try:
            reporter_s, batch, now_i = self._prepare(reporter, samples, now)
            submission_s = _validate_text(submission_id, "submission_id")
            issued_i = _validate_time(issued_at, "issued_at")
            if issued_i > now_i:
                raise InvalidTime("issued_at may not be in the future")
            if any(sample.at > issued_i for sample in batch):
                raise InvalidTime("sample timestamp may not be later than issued_at")
            if not isinstance(signature, (str, bytes)) or not signature or len(signature) > self.max_signature_size:
                raise ReporterUntrusted("signature is missing, malformed, or exceeds the configured size limit")
            if not isinstance(attestation, Mapping):
                raise ReporterUntrusted("attestation evidence must be a mapping")
            try:
                attestation_fields = len(attestation)
            except Exception as exc:
                raise ReporterUntrusted("attestation evidence has no bounded size") from exc
            if attestation_fields == 0 or attestation_fields > self.max_attestation_fields:
                raise ReporterUntrusted("attestation evidence exceeds configured field limits")
            verifier = self.trust_verifier
            if verifier is None:
                raise ReporterUntrusted("no production trust verifier is configured")
            payload = _canonical_payload(reporter_s, submission_s, issued_i, batch)
            try:
                authority = verifier.verify(
                    reporter=reporter_s,
                    payload=payload,
                    signature=signature,
                    attestation=attestation,
                    now=now_i,
                )
            except SignalError:
                raise
            except Exception as exc:
                raise TrustUnavailable("trust verifier failed closed") from exc
            if not isinstance(authority, ReporterAuthority):
                raise ReporterUntrusted("trust verifier returned an invalid authority object")
            if authority.reporter != reporter_s:
                raise ReporterUntrusted("verified reporter does not match submission reporter")
            self._authorize(authority, batch, now_i)
            replay_key = (reporter_s, submission_s)
            with self._lock:
                if replay_key in self._seen_submission_ids:
                    raise ReplayDetected(f"{reporter_s}: submission {submission_s!r} was already accepted")
                result = self._commit(
                    reporter_s, batch, now_i, submission_id=submission_s
                )
                self._seen_submission_ids.add(replay_key)
                self._replay_fifo.append(replay_key)
                while len(self._replay_fifo) > self.max_replay_ids:
                    evicted = self._replay_fifo.popleft()
                    self._seen_submission_ids.discard(evicted)
                return result
        except SignalError as exc:
            self._record_rejection(reporter, exc, now)
            raise

    def submit(
        self,
        reporter: str,
        samples: Iterable[Sample],
        *,
        attested_level: str,
        signed: bool,
        now: int,
    ) -> int:
        """Compatibility shim for pre-5.0 callers.

        Disabled by default because booleans and caller-asserted attestation are
        not proof.  Set ``allow_legacy_trust=True`` only for controlled fixtures
        while migrating to :meth:`submit_verified`.
        """
        try:
            if not self.allow_legacy_trust:
                raise ReporterUntrusted(
                    "legacy trust assertions are disabled; use submit_verified with a trust verifier"
                )
            reporter_s, batch, now_i = self._prepare(reporter, samples, now)
            if attested_level not in {"software", "hardware"} or signed is not True:
                raise ReporterUntrusted(
                    f"{reporter_s}: submissions require an attested identity and a signature"
                )
            return self._commit(reporter_s, batch, now_i, submission_id=None)
        except SignalError as exc:
            self._record_rejection(reporter, exc, now)
            raise

    def read(
        self,
        *,
        caller_tenant: str,
        tenant: str,
        environment: str,
        site: str,
        workload: str,
        signal: str,
        now: int,
    ) -> dict[str, Any]:
        caller = _validate_text(caller_tenant, "caller_tenant")
        tenant_s = _validate_text(tenant, "tenant")
        environment_s = _validate_text(environment, "environment")
        site_s = _validate_text(site, "site")
        workload_s = _validate_text(workload, "workload")
        signal_s = _validate_text(signal, "signal")
        now_i = _validate_time(now, "now")
        if caller != tenant_s:
            with self._lock:
                self._metrics["cross_tenant_denials"] += 1
            raise CrossTenantQuery(f"{caller} may not read signals for {tenant_s}")
        with self._lock:
            stored = self._latest.get((tenant_s, environment_s, site_s, workload_s, signal_s))
        if stored is None:
            return {
                "schema": "PK_SIGNAL_QUERY/2",
                "tenant": tenant_s,
                "environment": environment_s,
                "site": site_s,
                "workload": workload_s,
                "signal": signal_s,
                "value": ABSENT,
                "present": False,
                "stale": True,
                "age": None,
                "sample_at": None,
                "reporter": None,
                "received_at": None,
                "submission_id": None,
            }
        sample = stored.sample
        if now_i < sample.at:
            raise InvalidTime(
                f"query time {now_i} precedes stored sample time {sample.at}",
                signal=signal_s,
            )
        age = now_i - sample.at
        return {
            "schema": "PK_SIGNAL_QUERY/2",
            "tenant": tenant_s,
            "environment": environment_s,
            "site": site_s,
            "workload": workload_s,
            "signal": signal_s,
            "value": sample.value,
            "present": True,
            "stale": age > self.staleness_bound,
            "age": age,
            "sample_at": sample.at,
            "reporter": stored.reporter,
            "received_at": stored.received_at,
            "submission_id": stored.submission_id,
        }

    def silent_reporters(self, attested: Iterable[str], now: int) -> list[str]:
        now_i = _validate_time(now, "now")
        reporters = {_validate_text(r, "reporter") for r in attested}
        with self._lock:
            result = []
            for reporter in reporters:
                last = self._last_submission.get(reporter)
                if last is not None and now_i < last:
                    raise InvalidTime(f"now {now_i} precedes last submission time {last} for {reporter}")
                if last is None or now_i - last > self.reporters_silent_after:
                    result.append(reporter)
            self._metrics["silent_reporters"] = len(result)
        return sorted(result)

    def metrics(self) -> dict[str, int]:
        """Return a safe snapshot of internal counters/gauges."""
        with self._lock:
            out = dict(self._metrics)
            out["active_signals"] = len(self._latest)
            out["known_reporters"] = len(self._last_submission)
            out["replay_cache_entries"] = len(self._seen_submission_ids)
            out["rejection_log_entries"] = len(self._rejected)
            return out
