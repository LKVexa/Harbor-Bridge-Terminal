"""Identity-bound, attested, replay-protected admission for INV-29.

Closes the in-archive parts of INV29-MC043..MC058:

* tenant binding (MC045) and a tenant allow-list (MC044, local policy engine)
* host-image and module digest binding (MC047, MC048)
* cryptographic verification of the ``sealed`` / ``hardened`` claims (MC049, MC050)
  and optional measured-boot evidence (MC051) - an unsigned boolean is no
  longer trusted on the admission path
* capability provenance (MC052), dangerous-capability denylist (MC053),
  per-workload cardinality limit (MC054)
* replay protection / freshness (MC055) and record signatures (MC056)

Signatures here are HMAC-SHA256 over canonical JSON, because the archive is
stdlib-only.  ``Keyring`` is the narrow boundary a production deployment
replaces with an asymmetric verifier (Sigstore / Ed25519 / TPM quote) supplied
by INV-27 / INV-44; that replacement is recorded as BLOCKED_EXTERNAL in
``MISSING_COMPONENTS_STATUS.json`` rather than claimed here.

Every uncertainty fails closed: unknown key, revoked key, stale evidence,
wrong subject digest, replayed nonce, full replay cache, unknown tenant, or a
typed interface mismatch is a refusal, never an allow.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, FrozenSet, Iterable, Mapping, Optional, Tuple

from . import interfaces as _ifc
from .model import HostImage, ImportUnsatisfied, LayerMissing, WasmModule, compose
from .records import canonical, validate

DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
TENANT = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
NONCE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")

#: Capabilities that are never admitted on the hybrid tier regardless of host exposure.
DEFAULT_DENYLIST: FrozenSet[str] = frozenset({
    "raw-socket", "host-fs-root", "ptrace", "kernel-module", "hypervisor-call",
    "dma", "device-passthrough", "unrestricted-exec", "setuid",
})


class AdmissionRefused(PermissionError):
    """Base class; ``code`` is a stable machine-readable refusal reason."""

    code = "INV29-E-REFUSED"

    def __init__(self, message: str):
        super().__init__(f"{self.code}: {message}")


class IdentityInvalid(AdmissionRefused):
    code = "INV29-E-IDENTITY"


class AttestationInvalid(AdmissionRefused):
    code = "INV29-E-ATTESTATION"


class PolicyDenied(AdmissionRefused):
    code = "INV29-E-POLICY"


class ReplayDetected(AdmissionRefused):
    code = "INV29-E-REPLAY"


class InterfaceRefused(AdmissionRefused):
    code = "INV29-E-INTERFACE"


class ComponentDisabled(AdmissionRefused):
    code = "INV29-E-DISABLED"


ERROR_CODES = {
    LayerMissing: "INV29-E-LAYER",
    ImportUnsatisfied: "INV29-E-IMPORT",
}


def error_code(exc: BaseException) -> str:
    if isinstance(exc, AdmissionRefused):
        return exc.code
    for cls, code in ERROR_CODES.items():
        if isinstance(exc, cls):
            return code
    if isinstance(exc, (TypeError, ValueError)):
        return "INV29-E-INPUT"
    return "INV29-E-INTERNAL"


def digest_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- keys


class Keyring:
    """Thread-safe key store with revocation.  Key material is never logged or exported."""

    def __init__(self, keys: Optional[Mapping[str, bytes]] = None):
        self._lock = threading.Lock()
        self._keys: Dict[str, bytes] = {}
        self._revoked: set = set()
        for k, v in (keys or {}).items():
            self.add(k, v)

    def add(self, key_id: str, key: bytes) -> None:
        if not type(key_id) is str or not re.fullmatch(r"^[A-Za-z0-9._:-]{1,128}$", key_id):
            raise ValueError("invalid key id")
        if not isinstance(key, (bytes, bytearray)) or len(key) < 32:
            raise ValueError("key material must be at least 32 bytes")
        with self._lock:
            self._keys[key_id] = bytes(key)

    def revoke(self, key_id: str) -> None:
        with self._lock:
            self._revoked.add(key_id)

    def is_revoked(self, key_id: str) -> bool:
        if type(key_id) is not str:
            return True
        with self._lock:
            return key_id in self._revoked

    def _get(self, key_id: str) -> bytes:
        if type(key_id) is not str:
            raise AttestationInvalid("key id must be a plain string")
        with self._lock:
            if key_id in self._revoked:
                raise AttestationInvalid(f"key {key_id!r} is revoked")
            key = self._keys.get(key_id)
        if key is None:
            raise AttestationInvalid(f"unknown key {key_id!r}")
        return key

    def mac(self, key_id: str, payload: dict) -> str:
        return hmac.new(self._get(key_id), canonical(payload), hashlib.sha256).hexdigest()

    def check(self, key_id: str, payload: dict, value: str) -> bool:
        if not type(value) is str or not re.fullmatch(r"^[0-9a-f]{64}$", value):
            return False
        return hmac.compare_digest(self.mac(key_id, payload), value)

    def key_ids(self) -> list:
        with self._lock:
            return sorted(self._keys)

    def __repr__(self) -> str:  # never leak key material
        return f"Keyring(keys={self.key_ids()}, revoked={sorted(self._revoked)})"


def issue_attestation(keyring: Keyring, key_id: str, claim: str, subject: str, *, now: Optional[int] = None) -> dict:
    """Issue an attestation (used by test fixtures / the INV-27 & INV-44 test doubles)."""
    body = {"claim": claim, "subject": subject, "key_id": key_id,
            "issued_at": int(time.time() if now is None else now)}
    return {**body, "mac": keyring.mac(key_id, body)}


# --------------------------------------------------------------------------- policy


@dataclass(frozen=True)
class AdmissionPolicy:
    generation: int = 1
    allowed_tenants: FrozenSet[str] = frozenset()
    denylist: FrozenSet[str] = DEFAULT_DENYLIST
    max_imports_per_workload: int = 64
    required_layers: int = 2
    max_attestation_age_s: int = 3600
    record_ttl_s: int = 300
    clock_skew_s: int = 30
    require_measured_boot: bool = False
    require_typed_interfaces: bool = False
    #: capability -> set of issuers allowed to grant it (provenance); empty = any trusted issuer
    capability_issuers: Mapping[str, FrozenSet[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if type(self.generation) is not int or self.generation < 0:
            raise ValueError("generation must be a non-negative int")
        for t in self.allowed_tenants:
            if not TENANT.fullmatch(t):
                raise ValueError(f"invalid tenant id {t!r}")
        if type(self.max_imports_per_workload) is not int or not 0 <= self.max_imports_per_workload <= 4096:
            raise ValueError("max_imports_per_workload must be an int in [0, 4096]")
        if type(self.required_layers) is not int or self.required_layers < 2:
            raise ValueError("required_layers must be an int >= 2")
        for name in ("max_attestation_age_s", "record_ttl_s", "clock_skew_s"):
            v = getattr(self, name)
            if type(v) is not int or v < 0:
                raise ValueError(f"{name} must be a non-negative int")


class ReplayGuard:
    """Bounded, thread-safe nonce cache.  A full cache refuses rather than evicting live nonces."""

    def __init__(self, capacity: int = 100_000):
        self._lock = threading.Lock()
        self._seen: Dict[str, int] = {}
        self.capacity = capacity

    def consume(self, nonce: str, expires_at: int, now: int) -> None:
        if not type(nonce) is str or not NONCE.fullmatch(nonce):
            raise ReplayDetected("nonce missing or malformed")
        with self._lock:
            if len(self._seen) >= self.capacity:
                for k in [k for k, exp in self._seen.items() if exp < now]:
                    del self._seen[k]
            if nonce in self._seen:
                raise ReplayDetected(f"nonce {nonce[:8]}... already used")
            if len(self._seen) >= self.capacity:
                raise ReplayDetected("replay cache saturated; refusing rather than forgetting nonces")
            self._seen[nonce] = expires_at

    def __len__(self) -> int:
        with self._lock:
            return len(self._seen)


# --------------------------------------------------------------------------- admission


@dataclass(frozen=True)
class AdmissionRequest:
    tenant: str
    module: WasmModule
    host: HostImage
    module_digest: str
    host_digest: str
    attestations: Tuple[dict, ...]
    nonce: str
    host_interfaces: Tuple[_ifc.Interface, ...] = ()
    guest_interfaces: Tuple[_ifc.Interface, ...] = ()
    #: capability -> issuer id that granted it to the host image (provenance)
    capability_grants: Mapping[str, str] = field(default_factory=dict)


def _verify_attestation(keyring: Keyring, att: object, claim: str, subject: str,
                        policy: AdmissionPolicy, now: int) -> dict:
    if type(att) is not dict or set(att) != {"claim", "subject", "key_id", "issued_at", "mac"}:
        raise AttestationInvalid(f"{claim}: malformed attestation")
    # exact built-in types: a str subclass can override __eq__/__ne__ while canonical()
    # still serialises the original bytes, which would let a valid MAC cover a lie
    if any(type(att[k]) is not str for k in ("claim", "subject", "key_id", "mac")):
        raise AttestationInvalid(f"{claim}: attestation fields must be plain strings")
    body = {k: att[k] for k in ("claim", "subject", "key_id", "issued_at")}
    if att["claim"] != claim:
        raise AttestationInvalid(f"expected claim {claim!r}, got {att['claim']!r}")
    if att["subject"] != subject:
        raise AttestationInvalid(f"{claim}: attestation subject does not match the admitted digest")
    if type(att["issued_at"]) is not int:
        raise AttestationInvalid(f"{claim}: issued_at must be an int")
    if att["issued_at"] > now + policy.clock_skew_s:
        raise AttestationInvalid(f"{claim}: attestation issued in the future")
    if now - att["issued_at"] > policy.max_attestation_age_s:
        raise AttestationInvalid(f"{claim}: attestation is stale")
    if not keyring.check(att["key_id"], body, att["mac"]):
        raise AttestationInvalid(f"{claim}: signature does not verify")
    return {"claim": claim, "subject": subject, "key_id": att["key_id"], "verified": True}


class Admitter:
    """Stateful admission controller.  Thread-safe; one instance per process."""

    def __init__(self, keyring: Keyring, policy: AdmissionPolicy, *, signing_key_id: str,
                 replay: Optional[ReplayGuard] = None, clock: Callable[[], float] = time.time,
                 on_decision: Optional[Callable[[dict], None]] = None):
        self.keyring = keyring
        self._policy = policy
        self._policy_lock = threading.Lock()
        self.signing_key_id = signing_key_id
        self.replay = replay if replay is not None else ReplayGuard()
        self.clock = clock
        self.on_decision = on_decision
        self._disabled: Optional[str] = None
        keyring._get(signing_key_id)  # fail at construction if the signing key is absent

    # -- operational controls ------------------------------------------------
    @property
    def policy(self) -> AdmissionPolicy:
        with self._policy_lock:
            return self._policy

    def set_policy(self, policy: AdmissionPolicy) -> None:
        with self._policy_lock:
            if policy.generation < self._policy.generation:
                raise PolicyDenied("policy generation may not move backwards; use rollback()")
            self._policy = policy

    def rollback_policy(self, policy: AdmissionPolicy) -> None:
        """Explicit, audited rollback to an earlier policy generation."""
        with self._policy_lock:
            self._policy = policy
        self._emit({"event": "policy_rollback", "generation": policy.generation})

    def disable(self, reason: str) -> None:
        self._disabled = reason or "unspecified"
        self._emit({"event": "emergency_disable", "reason": self._disabled})

    def enable(self) -> None:
        self._disabled = None
        self._emit({"event": "emergency_enable"})

    @property
    def disabled(self) -> Optional[str]:
        return self._disabled

    def _emit(self, event: dict) -> None:
        if self.on_decision is not None:
            try:
                self.on_decision(event)
            except Exception:  # telemetry must never change a decision
                pass

    # -- the decision --------------------------------------------------------
    def admit(self, req: AdmissionRequest) -> dict:
        now = int(self.clock())
        try:
            record = self._admit(req, now)
        except Exception as exc:
            self._emit({"event": "decision", "outcome": "refused", "code": error_code(exc),
                        "tenant": getattr(req, "tenant", None), "module": getattr(getattr(req, "module", None), "name", None),
                        "reason": str(exc)[:512]})
            raise
        self._emit({"event": "decision", "outcome": "admitted", "code": "INV29-OK",
                    "tenant": req.tenant, "module": req.module.name, "layer_count": record["layer_count"],
                    "policy_generation": record["admission"]["policy_generation"]})
        return record

    def _admit(self, req: AdmissionRequest, now: int) -> dict:
        if self._disabled is not None:
            raise ComponentDisabled(f"hybrid tier disabled: {self._disabled}")
        if type(req) is not AdmissionRequest:
            raise TypeError("req must be AdmissionRequest")
        policy = self.policy

        # identity
        if not type(req.tenant) is str or not TENANT.fullmatch(req.tenant):
            raise IdentityInvalid("tenant id missing or malformed")
        if req.tenant not in policy.allowed_tenants:
            raise PolicyDenied(f"tenant {req.tenant!r} is not authorised for the hybrid tier")
        for label, d in (("module", req.module_digest), ("host", req.host_digest)):
            if not type(d) is str or not DIGEST.fullmatch(d):
                raise IdentityInvalid(f"{label} digest missing or not sha256")

        # layers + import closure (unchanged 4.2.0 core, now with the policy's layer bar)
        base = compose(req.module, req.host, required_layers=2)
        if policy.required_layers > base["layer_count"]:
            raise LayerMissing(f"{req.module.name}: {base['layer_count']} sound layer(s), "
                               f"{policy.required_layers} required by policy generation {policy.generation}")

        # capability policy
        imports = req.module.imports
        denied = sorted(imports & policy.denylist)
        if denied:
            raise PolicyDenied(f"dangerous capabilities requested: {denied}")
        exposed_denied = sorted(req.host.exposes & policy.denylist)
        if exposed_denied:
            raise PolicyDenied(f"host image exposes denylisted capabilities: {exposed_denied}")
        if len(imports) > policy.max_imports_per_workload:
            raise PolicyDenied(f"{len(imports)} imports exceed the per-workload limit "
                               f"{policy.max_imports_per_workload}")
        for cap in sorted(imports):
            allowed = policy.capability_issuers.get(cap)
            if allowed is not None:
                issuer = req.capability_grants.get(cap)
                if issuer is None or issuer not in allowed:
                    raise PolicyDenied(f"capability {cap!r} lacks provenance from an authorised issuer")

        # attestations: the booleans on HostImage/WasmModule are not trusted by themselves
        atts = list(req.attestations)
        if not isinstance(req.attestations, tuple) or len(atts) > 8:
            raise AttestationInvalid("attestations must be a tuple of at most 8")
        by_claim: Dict[str, object] = {}
        for a in atts:
            c = a.get("claim") if type(a) is dict else None
            if type(c) is not str:
                raise AttestationInvalid("attestation claim must be a plain string")
            if c in by_claim:
                raise AttestationInvalid(f"duplicate {c!r} attestation")
            by_claim[c] = a
        needed = [("sealed", req.host_digest), ("hardened", req.module_digest)]
        if policy.require_measured_boot:
            needed.append(("measured-boot", req.host_digest))
        verified = []
        for claim, subject in needed:
            if claim not in by_claim:
                raise AttestationInvalid(f"missing {claim!r} attestation")
            verified.append(_verify_attestation(self.keyring, by_claim[claim], claim, subject, policy, now))

        # typed interfaces
        iface_results = []
        if req.guest_interfaces or policy.require_typed_interfaces:
            if policy.require_typed_interfaces and not req.guest_interfaces:
                raise InterfaceRefused("policy requires typed interface metadata; none supplied")
            try:
                iface_results = _ifc.check_all(req.host_interfaces, req.guest_interfaces)
            except _ifc.InterfaceIncompatible as exc:
                raise InterfaceRefused(str(exc)) from exc

        # freshness / replay
        expires_at = now + policy.record_ttl_s
        self.replay.consume(req.nonce, expires_at, now)

        record = dict(base)
        record["admission"] = {
            "tenant": req.tenant,
            "module_digest": req.module_digest,
            "host_digest": req.host_digest,
            "nonce": req.nonce,
            "issued_at": now,
            "expires_at": expires_at,
            "policy_generation": policy.generation,
            "attestations": verified,
            "interfaces": iface_results,
        }
        record["verification"] = _jsonable(record["verification"])
        record["signature"] = {"alg": "HMAC-SHA256", "key_id": self.signing_key_id,
                               "value": self.keyring.mac(self.signing_key_id, _unsigned(record))}
        validate(record, "PK_HYBRID_COMPOSITION/1")
        return record


def _jsonable(obj):
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return obj


def _unsigned(record: dict) -> dict:
    return {k: v for k, v in record.items() if k != "signature"}


def verify_record(keyring: Keyring, record: object, *, expected_key_id: str, now: Optional[int] = None,
                  clock_skew_s: int = 30, max_ttl_s: int = 3600) -> dict:
    """Verify an admitted composition record: schema, pinned signer, signature, freshness.

    ``expected_key_id`` is mandatory: accepting whatever key the record names would let
    any key in the consumer's keyring (e.g. an attestation key) sign records.
    """
    if type(record) is not dict:
        raise AttestationInvalid("record must be an object")
    validate(record, "PK_HYBRID_COMPOSITION/1")
    sig = record.get("signature")
    adm = record.get("admission")
    if sig is None or adm is None:
        raise AttestationInvalid("unsigned or unadmitted record is not trusted")
    if sig["key_id"] != expected_key_id:
        raise AttestationInvalid("record signed by an unexpected key")
    if not keyring.check(sig["key_id"], _unsigned(record), sig["value"]):
        raise AttestationInvalid("record signature does not verify")
    t = int(time.time() if now is None else now)
    if adm["issued_at"] > t + clock_skew_s:
        raise AttestationInvalid("record issued in the future")
    if not 0 <= adm["expires_at"] - adm["issued_at"] <= max_ttl_s:
        raise AttestationInvalid("record validity window is invalid")
    if t > adm["expires_at"]:
        raise ReplayDetected("record has expired")
    return {"verified": True, "key_id": sig["key_id"], "expires_at": adm["expires_at"]}


def new_nonce() -> str:
    return secrets.token_urlsafe(24)
