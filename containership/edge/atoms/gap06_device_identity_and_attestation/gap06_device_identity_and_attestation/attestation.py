"""Security-focused reference primitives for GAP-06 device attestation.

This module deliberately depends only on the Python standard library so the
trust-boundary behaviour can be tested even when the surrounding ``pk_core``
framework is not installed.

It is still a reference implementation, not a production TPM/TEE verifier.
Production-grade quote/signature/certificate verification is called out in
``MISSING_COMPONENTS.md``.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import threading
from dataclasses import dataclass, field
from typing import Final, Iterable

LEVELS: Final[tuple[str, ...]] = ("untrusted", "software", "hardware")
VERDICT_TTL: Final[int] = 100
CHALLENGE_TTL: Final[int] = 20
MAX_OUTSTANDING_CHALLENGES: Final[int] = 10_000
MAX_NODE_LENGTH: Final[int] = 255
MAX_MEASUREMENTS: Final[int] = 64
MAX_MEASUREMENT_LENGTH: Final[int] = 256
MAX_IDENTITY_LENGTH: Final[int] = 512


class AttestationFailed(PermissionError):
    """Base class for evidence that cannot establish the requested trust."""


class ReplayDetected(AttestationFailed):
    """Evidence reused a nonce that has already been consumed or expired."""


class UnissuedChallenge(AttestationFailed):
    """Evidence answered a nonce this attestor did not issue to that node."""


class ChallengeExpired(AttestationFailed):
    """Evidence answered a challenge after its validity window closed."""


class UnknownNode(AttestationFailed):
    """The node has not been enrolled with this attestor."""


class IdentityBindingFailed(AttestationFailed):
    """The claimed hardware-root identity does not match enrollment state."""


class InvalidEvidence(ValueError):
    """Evidence is malformed or non-canonical."""


class ClockRollback(ValueError):
    """A state operation supplied a logical time older than one already seen."""


class ChallengeCapacityExceeded(RuntimeError):
    """Outstanding challenge capacity has been exhausted."""


def _validate_text(value: str, name: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str")
    if not value or value.strip() != value:
        raise ValueError(f"{name} must be non-empty and have no surrounding whitespace")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds maximum length {maximum}")
    return value


def _validate_tick(now: int) -> int:
    if isinstance(now, bool) or not isinstance(now, int):
        raise TypeError("now must be an integer logical tick")
    if now < 0:
        raise ValueError("now must be non-negative")
    return now


@dataclass(frozen=True, slots=True)
class Challenge:
    node: str
    nonce: str
    issued_at: int
    expires_at: int


@dataclass(frozen=True, slots=True)
class Evidence:
    """Attestation evidence measured under a specific challenge.

    ``hardware_identity`` is an enrollment identifier used by this reference
    model to prevent a bare boolean from elevating an unenrolled node.  It is
    not a substitute for production verification of a signed TPM/TEE quote.
    """

    node: str
    measurements: tuple[str, ...]
    nonce: str
    hardware_rooted: bool
    hardware_identity: str | None = None

    def validate(self) -> None:
        _validate_text(self.node, "node", MAX_NODE_LENGTH)
        _validate_text(self.nonce, "nonce", 256)
        if not isinstance(self.hardware_rooted, bool):
            raise InvalidEvidence("hardware_rooted must be bool")
        if not isinstance(self.measurements, tuple):
            raise InvalidEvidence("measurements must be a tuple")
        if len(self.measurements) > MAX_MEASUREMENTS:
            raise InvalidEvidence(f"too many measurements; maximum is {MAX_MEASUREMENTS}")
        for measurement in self.measurements:
            try:
                _validate_text(measurement, "measurement", MAX_MEASUREMENT_LENGTH)
            except (TypeError, ValueError) as exc:
                raise InvalidEvidence(str(exc)) from exc
        if tuple(sorted(self.measurements)) != self.measurements:
            raise InvalidEvidence("measurements must be sorted for canonical binding")
        if len(set(self.measurements)) != len(self.measurements):
            raise InvalidEvidence("measurements must not contain duplicates")
        if self.hardware_identity is not None:
            try:
                _validate_text(self.hardware_identity, "hardware_identity", MAX_IDENTITY_LENGTH)
            except (TypeError, ValueError) as exc:
                raise InvalidEvidence(str(exc)) from exc
        if not self.hardware_rooted and self.hardware_identity is not None:
            raise InvalidEvidence("software-rooted evidence must not claim a hardware identity")

    def bind(self, *, environment: str = "") -> str:
        """Return a canonical SHA-256 binding for audit/equality use.

        This digest is a binding/fingerprint, not an authenticity proof.
        """
        self.validate()
        payload = {
            "environment": environment,
            "hardware_identity": self.hardware_identity,
            "hardware_rooted": self.hardware_rooted,
            "measurements": list(self.measurements),
            "node": self.node,
            "nonce": self.nonce,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class Verdict:
    node: str
    level: str
    issued_at: int
    expires_at: int
    binding: str
    measurement_set_version: str

    def __post_init__(self) -> None:
        if self.level not in LEVELS:
            raise ValueError(f"unknown attestation level: {self.level}")
        if self.expires_at <= self.issued_at:
            raise ValueError("verdict expiry must be after issuance")

    def valid_at(self, now: int) -> bool:
        _validate_tick(now)
        return self.issued_at <= now < self.expires_at

    def level_at(self, now: int) -> str:
        """Trust is untrusted before issuance and at/after expiry."""
        return self.level if self.valid_at(now) else "untrusted"


@dataclass
class Attestor:
    """In-memory reference verifier for node evidence.

    Security invariants:
    * only enrolled nodes receive challenges;
    * challenges use cryptographic randomness and expire;
    * a challenge is bound to one node and cannot be burned by another node;
    * a valid challenge is single-use, even when subsequent evidence fails;
    * malformed/unissued evidence cannot quarantine a node;
    * hardware trust additionally requires a matching enrolled identity;
    * verdicts expire and time rollback is refused for state operations.
    """

    environment: str
    accepted: set[str] = field(default_factory=set)
    measurement_set_version: str = "bootstrap-v1"
    enrolled_nodes: set[str] = field(default_factory=set)
    hardware_identities: dict[str, str] = field(default_factory=dict)
    spent_nonces: set[str] = field(default_factory=set)
    quarantined: set[str] = field(default_factory=set)
    quarantine_reasons: dict[str, str] = field(default_factory=dict)
    verdicts: dict[str, Verdict] = field(default_factory=dict)
    issued: dict[str, Challenge] = field(default_factory=dict)
    _last_tick: int = field(default=0, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        _validate_text(self.environment, "environment", 255)
        _validate_text(self.measurement_set_version, "measurement_set_version", 128)
        normalized: set[str] = set()
        for digest in self.accepted:
            normalized.add(_validate_text(digest, "measurement", MAX_MEASUREMENT_LENGTH))
        self.accepted = normalized

    def _advance(self, now: int) -> None:
        now = _validate_tick(now)
        if now < self._last_tick:
            raise ClockRollback(f"logical time moved backwards: {now} < {self._last_tick}")
        self._last_tick = now

    def _prune_expired_challenges(self, now: int) -> None:
        expired = [nonce for nonce, ch in self.issued.items() if now >= ch.expires_at]
        for nonce in expired:
            self.issued.pop(nonce, None)
            self.spent_nonces.add(nonce)

    def enrol(self, node: str, *, hardware_identity: str | None = None) -> None:
        node = _validate_text(node, "node", MAX_NODE_LENGTH)
        if hardware_identity is not None:
            hardware_identity = _validate_text(hardware_identity, "hardware_identity", MAX_IDENTITY_LENGTH)
        with self._lock:
            self.enrolled_nodes.add(node)
            if hardware_identity is None:
                self.hardware_identities.pop(node, None)
            else:
                self.hardware_identities[node] = hardware_identity

    def revoke(self, node: str, *, reason: str = "identity revoked") -> None:
        node = _validate_text(node, "node", MAX_NODE_LENGTH)
        reason = _validate_text(reason, "reason", 512)
        with self._lock:
            self.enrolled_nodes.discard(node)
            self.hardware_identities.pop(node, None)
            self.quarantined.add(node)
            self.quarantine_reasons[node] = reason
            self.verdicts.pop(node, None)
            for nonce, challenge in list(self.issued.items()):
                if challenge.node == node:
                    self.issued.pop(nonce, None)
                    self.spent_nonces.add(nonce)

    def challenge(self, node: str, now: int) -> str:
        node = _validate_text(node, "node", MAX_NODE_LENGTH)
        with self._lock:
            self._advance(now)
            if node not in self.enrolled_nodes:
                raise UnknownNode(f"{node}: node is not enrolled")
            self._prune_expired_challenges(now)
            if len(self.issued) >= MAX_OUTSTANDING_CHALLENGES:
                raise ChallengeCapacityExceeded("too many outstanding attestation challenges")
            while True:
                nonce = secrets.token_hex(32)
                if nonce not in self.issued and nonce not in self.spent_nonces:
                    break
            self.issued[nonce] = Challenge(node=node, nonce=nonce, issued_at=now, expires_at=now + CHALLENGE_TTL)
            return nonce

    def attest(self, evidence: Evidence, now: int) -> Verdict:
        if not isinstance(evidence, Evidence):
            raise TypeError("evidence must be an Evidence instance")
        evidence.validate()
        with self._lock:
            self._advance(now)

            if evidence.nonce in self.spent_nonces:
                raise ReplayDetected(f"{evidence.node}: nonce {evidence.nonce} was already spent or expired")

            challenge = self.issued.get(evidence.nonce)
            if challenge is None or challenge.node != evidence.node:
                # Do not consume another node's challenge and do not mutate node
                # trust state from unauthenticated/unbound evidence.
                raise UnissuedChallenge(
                    f"{evidence.node}: nonce {evidence.nonce} was not issued to this node by this attestor")

            if now >= challenge.expires_at:
                self.issued.pop(evidence.nonce, None)
                self.spent_nonces.add(evidence.nonce)
                raise ChallengeExpired(f"{evidence.node}: challenge expired")

            # The challenge is single-use once the correct node presents it,
            # regardless of whether later measurement/identity checks succeed.
            self.issued.pop(evidence.nonce, None)
            self.spent_nonces.add(evidence.nonce)

            if evidence.node not in self.enrolled_nodes:
                raise UnknownNode(f"{evidence.node}: node is not enrolled")
            if not evidence.measurements:
                self._quarantine(evidence.node, "evidence carries no measurements")
                raise AttestationFailed(f"{evidence.node}: evidence carries no measurements")

            unknown = [m for m in evidence.measurements if m not in self.accepted]
            if unknown:
                self._quarantine(evidence.node, f"measurements outside accepted set: {unknown}")
                raise AttestationFailed(
                    f"{evidence.node}: measurements outside the accepted set: {unknown}")

            if evidence.hardware_rooted:
                expected = self.hardware_identities.get(evidence.node)
                if expected is None or evidence.hardware_identity != expected:
                    self._quarantine(evidence.node, "hardware identity does not match enrollment")
                    raise IdentityBindingFailed(
                        f"{evidence.node}: hardware identity does not match enrolled identity")
                level = "hardware"
            else:
                level = "software"

            self.quarantined.discard(evidence.node)
            self.quarantine_reasons.pop(evidence.node, None)
            verdict = Verdict(
                node=evidence.node,
                level=level,
                issued_at=now,
                expires_at=now + VERDICT_TTL,
                binding=evidence.bind(environment=self.environment),
                measurement_set_version=self.measurement_set_version,
            )
            self.verdicts[evidence.node] = verdict
            return verdict

    def _quarantine(self, node: str, reason: str) -> None:
        self.quarantined.add(node)
        self.quarantine_reasons[node] = reason

    def level_of(self, node: str, now: int) -> str:
        node = _validate_text(node, "node", MAX_NODE_LENGTH)
        with self._lock:
            self._advance(now)
            verdict = self.verdicts.get(node)
            if verdict is None or node in self.quarantined or node not in self.enrolled_nodes:
                return "untrusted"
            return verdict.level_at(now)

    def replace_accepted_measurements(self, digests: Iterable[str], *, version: str) -> None:
        version = _validate_text(version, "version", 128)
        new_set = {_validate_text(d, "measurement", MAX_MEASUREMENT_LENGTH) for d in digests}
        if not new_set:
            raise ValueError("accepted measurement set must not be empty")
        with self._lock:
            self.accepted = new_set
            self.measurement_set_version = version

    def accept_measurement(self, digest: str, *, version: str) -> None:
        """Add one measurement with an explicit new set version.

        Production systems should normally use an authenticated, atomic policy
        publication path rather than this convenience method.
        """
        digest = _validate_text(digest, "measurement", MAX_MEASUREMENT_LENGTH)
        version = _validate_text(version, "version", 128)
        with self._lock:
            self.accepted.add(digest)
            self.measurement_set_version = version
