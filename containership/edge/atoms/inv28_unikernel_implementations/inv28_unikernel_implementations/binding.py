"""Selection-to-build anti-substitution binding (MC-021, MC-041, MC-098).

The contract names the threat "toolchain substitution between selection and build".  A selection
therefore ends in a signed ``PK_TOOLCHAIN_TICKET/1`` that binds the decision to one immutable
toolchain identity: ``name@version`` + register-entry digest + release-artifact SHA-256 + registry
revision + policy digest, valid for a short window.

``Inv27Adapter.verify`` is the check INV-27 (unikernel execution) runs before it builds or boots
anything: signature, expiry, and that the artifact it actually holds hashes to the bound digest and
the register still holds the same entry digest and is not disabled.  Any mismatch is a
``BIND_*`` refusal - never a warning.
"""
from __future__ import annotations

import datetime as dt
import hashlib

from .errors import BindingError, Reason, RegistryError
from .model import fmt_utc, parse_utc
from .trust import KeyRing

SCHEMA = "PK_TOOLCHAIN_TICKET/1"


class Binder:
    def __init__(self, ring: KeyRing, ttl: dt.timedelta = dt.timedelta(minutes=15)):
        self._ring = ring
        self._ttl = ttl

    def issue(self, result, now: dt.datetime) -> dict:
        body = {"schema": SCHEMA, "decision_id": result.decision_id, "toolchain_ref": result.ref,
                "record_digest": result.record_digest, "artifact_sha256": result.artifact_sha256,
                "registry_revision": result.registry_revision, "policy_digest": result.policy_digest,
                "certification_id": result.certification_id,
                "issued_at": fmt_utc(now), "expires_at": fmt_utc(now + self._ttl)}
        return {**body, "signature": self._ring.sign("ticket", body)}


class Inv27Adapter:
    """The verification INV-27 performs; shipped here so both sides test against one implementation."""

    def __init__(self, ring: KeyRing, registry):
        self._ring = ring
        self._registry = registry

    def verify(self, ticket: dict, artifact_bytes: bytes, *, now: dt.datetime) -> dict:
        if not isinstance(ticket, dict) or ticket.get("schema") != SCHEMA:
            raise BindingError(Reason.BINDING_TAMPERED, "not a toolchain ticket")
        body = {k: v for k, v in ticket.items() if k != "signature"}
        if not self._ring.verify("ticket", body, ticket.get("signature")):
            raise BindingError(Reason.BINDING_TAMPERED, "ticket signature invalid")
        if not parse_utc(body["issued_at"], "issued_at") <= now <= parse_utc(body["expires_at"], "expires_at"):
            raise BindingError(Reason.BINDING_EXPIRED, "ticket outside its validity window")
        if not body["artifact_sha256"]:
            raise BindingError(Reason.BINDING_MISMATCH, "ticket binds no artifact digest")
        actual = hashlib.sha256(artifact_bytes).hexdigest()
        if actual != body["artifact_sha256"]:
            raise BindingError(Reason.BINDING_MISMATCH, "artifact does not match the selected toolchain",
                               expected=body["artifact_sha256"], actual=actual)
        try:
            rec = self._registry.get(body["toolchain_ref"])
        except RegistryError:
            raise BindingError(Reason.BINDING_MISMATCH, "selected toolchain no longer registered") from None
        if rec.digest != body["record_digest"]:
            raise BindingError(Reason.BINDING_MISMATCH, "register entry changed since selection")
        if rec.lifecycle in ("disabled", "quarantined", "retired"):
            raise BindingError(Reason.BINDING_MISMATCH, f"toolchain is {rec.lifecycle}")
        return {"verified": True, "toolchain_ref": body["toolchain_ref"], "artifact_sha256": actual}
