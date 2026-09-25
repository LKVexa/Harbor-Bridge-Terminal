"""GAP-06 attestation adapter (component 01) -- verifier side.

Evidence format ``GAP09-ATT/1`` (JSON object):
  device_id, reporter, tenant, nonce, issued_at, measurements{name: sha256hex},
  level ("software"|"hardware"), root_id, endorsement (ed25519 hex over the
  CSP/1 canonical bytes of every other field).

The adapter checks, in order and fail-closed: bounded size/field counts ->
known trust root -> endorsement signature -> device/reporter binding ->
revocation -> nonce freshness (single use, window) -> measurement policy.
A real GAP-06 verifier (TPM quote / TEE report parsing) is NOT present in
this archive; the trust roots used in tests are fixtures, so component 01's
integration checks stay BLOCKED.  What is real is the policy engine the real
evidence must pass through.
"""
from __future__ import annotations

import hashlib
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Mapping

from . import ed25519
from .canonical import canonical_bytes, canonicalize
from .errors import DependencyUnavailable, Expired, Malformed, Revoked, Unverifiable

FORMAT = "GAP09-ATT/1"
MAX_EVIDENCE_BYTES = 8192
MAX_MEASUREMENTS = 32
REQUIRED = ("format", "device_id", "reporter", "tenant", "nonce", "issued_at", "measurements", "level", "root_id", "endorsement")


@dataclass(frozen=True)
class AttestationResult:
    device_id: str
    reporter: str
    tenant: str
    level: str
    root_id: str
    evidence_sha256: str
    policy_version: str

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


class AttestationPolicy:
    def __init__(self, *, version: str, approved_measurements: Mapping[str, frozenset], freshness_window: int) -> None:
        if freshness_window <= 0:
            raise Malformed("freshness window must be positive")
        self.version = version
        self.approved = {k: frozenset(v) for k, v in approved_measurements.items()}
        self.freshness_window = freshness_window


class AttestationVerifier:
    def __init__(self, *, roots: Mapping[str, bytes], policy: AttestationPolicy, revoked_devices=(),
                 nonce_capacity: int = 100_000, available=lambda: True) -> None:
        self.roots = dict(roots)
        self.policy = policy
        self.revoked = set(revoked_devices)
        self._nonces: OrderedDict[str, int] = OrderedDict()
        self._cap = nonce_capacity
        self._lock = threading.Lock()
        self._available = available
        self.decisions: list[dict[str, Any]] = []

    def revoke_device(self, device_id: str) -> None:
        self.revoked.add(device_id)

    def verify_evidence(self, evidence: Any, *, reporter: str, now: int) -> AttestationResult:
        rec: dict[str, Any] = {"reporter": reporter, "at": now, "policy_version": self.policy.version}
        try:
            res = self._verify(evidence, reporter, now, rec)
            rec["outcome"] = "accept"
            return res
        except (Malformed, Unverifiable, Revoked, Expired, DependencyUnavailable) as exc:
            rec["outcome"] = "reject"
            rec["reason"] = exc.code
            raise
        finally:
            self.decisions.append(rec)

    def _verify(self, ev: Any, reporter: str, now: int, rec: dict) -> AttestationResult:
        if not self._available():
            raise DependencyUnavailable("attestation verifier dependency unavailable")
        if not isinstance(ev, Mapping):
            raise Malformed("evidence must be an object")
        if set(ev) != set(REQUIRED):
            raise Malformed("evidence fields must be exactly the GAP09-ATT/1 set")
        try:
            body_text = canonicalize(dict(ev))
        except Exception as exc:
            raise Malformed("evidence not canonicalizable") from exc
        if len(body_text.encode()) > MAX_EVIDENCE_BYTES:
            raise Malformed("evidence exceeds size limit")
        rec["evidence_sha256"] = hashlib.sha256(body_text.encode()).hexdigest()
        if ev["format"] != FORMAT:
            raise Malformed("unsupported evidence format")
        meas = ev["measurements"]
        if not isinstance(meas, Mapping) or not meas or len(meas) > MAX_MEASUREMENTS:
            raise Malformed("measurements missing or oversized")
        root = self.roots.get(ev["root_id"])
        rec["root_id"] = ev["root_id"] if isinstance(ev["root_id"], str) else None
        if root is None:
            raise Unverifiable("unknown trust root")
        signed = {k: v for k, v in ev.items() if k != "endorsement"}
        sig = ev["endorsement"]
        if not isinstance(sig, str) or len(sig) != 128:
            raise Unverifiable("endorsement malformed")
        try:
            sigb = bytes.fromhex(sig)
        except ValueError as exc:
            raise Unverifiable("endorsement not hex") from exc
        if not ed25519.verify(root, canonical_bytes(signed), sigb):
            raise Unverifiable("endorsement signature invalid")
        if ev["reporter"] != reporter:
            raise Unverifiable("evidence bound to a different reporter")
        if ev["device_id"] in self.revoked:
            raise Revoked("device revoked")
        issued = ev["issued_at"]
        if isinstance(issued, bool) or not isinstance(issued, int):
            raise Malformed("issued_at must be an integer")
        if issued > now:
            raise Expired("evidence issued in the future")
        if now - issued >= self.policy.freshness_window:
            raise Expired("evidence is stale")
        nonce = ev["nonce"]
        if not isinstance(nonce, str) or not (16 <= len(nonce) <= 128):
            raise Malformed("nonce malformed")
        with self._lock:
            # evict nonces older than the freshness window (they could no longer pass freshness anyway)
            while self._nonces and next(iter(self._nonces.values())) <= now - self.policy.freshness_window:
                self._nonces.popitem(last=False)
            if nonce in self._nonces:
                raise Unverifiable("attestation nonce replayed")
            if len(self._nonces) >= self._cap:
                raise DependencyUnavailable("nonce cache saturated; refusing rather than forgetting")
            self._nonces[nonce] = issued
        for name, digest in meas.items():
            allowed = self.policy.approved.get(name)
            if allowed is None or digest not in allowed:
                raise Unverifiable("measurement not approved by policy", measurement=name)
        missing = set(self.policy.approved) - set(meas)
        if missing:
            raise Unverifiable("required measurement absent", measurement=sorted(missing)[0])
        if ev["level"] not in ("software", "hardware"):
            raise Malformed("level invalid")
        return AttestationResult(ev["device_id"], reporter, ev["tenant"], ev["level"], ev["root_id"],
                                 rec["evidence_sha256"], self.policy.version)


def make_evidence(root_secret: bytes, **fields) -> dict:
    """Fixture helper: build and endorse GAP09-ATT/1 evidence."""
    ev = {"format": FORMAT, **fields}
    ev["endorsement"] = ed25519.sign(root_secret, canonical_bytes(ev)).hex()
    return ev
