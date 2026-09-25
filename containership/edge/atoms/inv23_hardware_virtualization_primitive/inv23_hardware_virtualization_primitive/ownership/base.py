"""Durable, fenced, lease-based ownership for INV-23 (MC-04 / MC-05).

Semantics (documented in THREAT_MODEL.md and README):

* The claimed resource is a **project-defined policy slot** named by ``resource``
  (default ``"hw-virt"``), host-global within one provider namespace.  It is *not*
  device exclusivity: KVM, WHPX and HVF all allow concurrent legitimate users.
* Claims are non-reentrant: one live claim per resource.  A process may hold claims on
  different resources.  Claims are not inherited meaningfully across fork: the child
  holds the token but liveness is bound to the acquiring PID + start time.
* Every ownership epoch gets a strictly increasing **fencing generation**; the
  generation is persisted independently of the record so it survives release,
  takeover and repair.
* Authority is an unguessable **token** (256-bit) returned once; only its SHA-256 is
  persisted.  ``holder`` is a display name only.
* A claim is stale (and may be taken over, issuing a new generation) when its lease
  expired, its owner process is gone, its process start identity differs (PID reuse),
  or the host boot id changed.
* Corrupt or impossible records **fail closed** (``OwnershipCorrupt``); only an explicit
  ``repair()`` quarantines them.
* Lease expiry is wall-clock because it is compared across processes; local waits use
  ``time.monotonic``.  A clock jump forward can expire leases early (safe: the owner
  is fenced); a jump backward can extend a dead owner's lease up to the jump size and
  liveness checks still reclaim it if the PID is gone.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import socket
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Optional

from . import procid

RECORD_SCHEMA = "PK_VIRT_OWNERSHIP/1"
DEFAULT_LEASE_S = 30.0
MAX_LEASE_S = 3600.0
MAX_FUTURE_SKEW_S = 300.0
HISTORY_LIMIT = 16


class OwnershipError(RuntimeError):
    code = "ownership_error"


class ClaimConflict(OwnershipError):
    code = "claim_conflict"


class StaleToken(OwnershipError):
    code = "stale_token"


class LeaseLost(OwnershipError):
    code = "lease_lost"


class FencingRejected(OwnershipError):
    code = "fencing_rejected"


class OwnershipCorrupt(OwnershipError):
    code = "ownership_corrupt"


@dataclass(frozen=True)
class Claim:
    resource: str
    claim_id: str
    generation: int
    token: str = ""  # secret; excluded from repr/public
    lease_expires_at: float = 0.0
    acquired_at: float = 0.0
    holder: str = ""
    provider: str = ""

    def __repr__(self) -> str:  # never leak the token
        return f"Claim(resource={self.resource!r}, claim_id={self.claim_id!r}, generation={self.generation}, holder={self.holder!r})"

    def public(self) -> Dict[str, Any]:
        return {
            "resource": self.resource,
            "claim_id": self.claim_id,
            "generation": self.generation,
            "lease_expires_at": round(self.lease_expires_at, 6),
            "acquired_at": round(self.acquired_at, 6),
            "holder": self.holder,
            "provider": self.provider,
        }


def _h(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def validate_resource(resource: str) -> str:
    if not isinstance(resource, str):
        raise ValueError("resource must be a string")
    r = resource.strip()
    if not r or len(r) > 64 or not all(c.isalnum() or c in "-_." for c in r) or r.startswith("."):
        raise ValueError(f"invalid resource name {resource!r}")
    return r


def validate_record(rec: Any, now: float) -> Dict[str, Any]:
    """Structural + semantic validation of a persisted record; raises OwnershipCorrupt."""

    def bad(msg):
        raise OwnershipCorrupt(f"ownership record invalid: {msg}")

    if not isinstance(rec, dict):
        bad("not an object")
    if rec.get("schema") != RECORD_SCHEMA:
        bad(f"schema {rec.get('schema')!r}")
    for k, t in (("resource", str), ("state", str), ("provider", str)):
        if not isinstance(rec.get(k), t):
            bad(k)
    gen = rec.get("generation")
    if type(gen) is not int or gen < 0:
        bad("generation")
    if rec["state"] not in ("held", "released"):
        bad("state")
    if rec["state"] == "held":
        for k in ("claim_id", "token_sha256", "host", "holder"):
            if not isinstance(rec.get(k), str) or not rec[k]:
                bad(k)
        if len(rec["token_sha256"]) != 64:
            bad("token_sha256")
        if type(rec.get("pid")) is not int or rec["pid"] <= 0:
            bad("pid")
        for k in ("acquired_at", "lease_expires_at"):
            v = rec.get(k)
            if type(v) not in (int, float) or v != v:
                bad(k)
        if rec["acquired_at"] > now + MAX_FUTURE_SKEW_S:
            bad("acquired_at in the future")
        if rec["lease_expires_at"] < rec["acquired_at"] or rec["lease_expires_at"] - rec["acquired_at"] > MAX_LEASE_S + 1:
            bad("impossible lease window")
        if gen < 1:
            bad("held record with generation 0")
    return rec


class ClaimProvider:
    """Template: subclasses provide an exclusive critical section and record storage."""

    name = "abstract"

    def __init__(self, *, telemetry=None, host: Optional[str] = None, clock=time.time, liveness=None) -> None:
        from ..telemetry import Telemetry

        self.telemetry = telemetry or Telemetry()
        self.host = host or socket.gethostname() or "localhost"
        self.clock = clock
        self.liveness = liveness or procid

    # ---- storage hooks -------------------------------------------------------------
    @contextmanager
    def _critical(self, resource: str) -> Iterator[None]:
        raise NotImplementedError
        yield  # pragma: no cover

    def _load(self, resource: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def _store(self, resource: str, rec: Dict[str, Any]) -> None:
        raise NotImplementedError

    def _load_generation(self, resource: str) -> int:
        raise NotImplementedError

    def _store_generation(self, resource: str, gen: int) -> None:
        raise NotImplementedError

    def _quarantine(self, resource: str) -> None:
        raise NotImplementedError

    # ---- logic ---------------------------------------------------------------------
    def _read(self, resource: str) -> Optional[Dict[str, Any]]:
        rec = self._load(resource)
        if rec is None:
            return None
        rec = validate_record(rec, self.clock())
        if self._load_generation(resource) < rec["generation"]:
            raise OwnershipCorrupt("generation floor is behind the ownership record")
        return rec

    def _stale_reason(self, rec: Dict[str, Any], now: float) -> Optional[str]:
        if rec["lease_expires_at"] <= now:
            return "lease_expired"
        if rec.get("host") != self.host:
            return None  # cannot judge another host's process; lease governs
        boot = self.liveness.boot_id()
        if rec.get("boot_id") and boot and rec["boot_id"] != boot:
            return "reboot"
        alive = self.liveness.pid_alive(rec["pid"])
        if alive is False:
            return "owner_dead"
        start = self.liveness.start_identity(rec["pid"])
        if rec.get("process_start") is not None and start is not None and start != rec["process_start"]:
            return "pid_reused"
        return None

    def acquire(self, holder: str, *, resource: str = "hw-virt", lease_s: float = DEFAULT_LEASE_S) -> Claim:
        if not isinstance(holder, str) or not holder.strip():
            raise ValueError("holder must be a non-empty string")
        holder = holder.strip()[:128]
        resource = validate_resource(resource)
        if type(lease_s) not in (int, float) or not (0 < lease_s <= MAX_LEASE_S):
            raise ValueError("lease_s must be in (0, 3600]")
        t0 = time.monotonic()
        tel = self.telemetry
        with tel.span("inv23.claim", provider=self.name):
            with self._critical(resource):
                now = self.clock()
                rec = self._read(resource)
                gen = max(self._load_generation(resource), rec["generation"] if rec else 0)
                history = list(rec.get("history", [])) if rec else []
                if rec and rec["state"] == "held":
                    why = self._stale_reason(rec, now)
                    if why is None:
                        tel.count("inv23_claim_conflicts_total", provider=self.name)
                        tel.event("INV23-E004", provider=self.name, resource=resource)
                        raise ClaimConflict(f"{resource} held (generation {rec['generation']})")
                    tel.count("inv23_stale_owner_recoveries_total", provider=self.name)
                    tel.event("INV23-E007", provider=self.name, resource=resource, why=why, previous_generation=rec["generation"])
                    history.append(
                        {
                            "claim_id": rec["claim_id"],
                            "generation": rec["generation"],
                            "holder": rec["holder"],
                            "pid": rec["pid"],
                            "ended": why,
                            "at": now,
                        }
                    )
                token = secrets.token_urlsafe(32)
                new_gen = gen + 1
                self._store_generation(resource, new_gen)  # generation first: never reused
                new = {
                    "schema": RECORD_SCHEMA,
                    "resource": resource,
                    "state": "held",
                    "claim_id": str(uuid.uuid4()),
                    "generation": new_gen,
                    "token_sha256": _h(token),
                    "pid": os.getpid(),
                    "process_start": self.liveness.start_identity(os.getpid()),
                    "boot_id": self.liveness.boot_id(),
                    "host": self.host,
                    "holder": holder,
                    "acquired_at": now,
                    "lease_expires_at": now + lease_s,
                    "lease_s": lease_s,
                    "provider": self.name,
                    "history": history[-HISTORY_LIMIT:],
                }
                self._store(resource, new)
        tel.observe("inv23_claim_acquire_seconds", time.monotonic() - t0, provider=self.name)
        tel.event("INV23-E003", provider=self.name, resource=resource, claim_id=new["claim_id"], generation=new_gen)
        return Claim(resource, new["claim_id"], new_gen, token, new["lease_expires_at"], now, holder, self.name)

    def _check(self, rec: Optional[Dict[str, Any]], claim: Claim, now: float, *, allow_expired: bool = False) -> Dict[str, Any]:
        if not isinstance(claim, Claim) or not claim.token:
            raise StaleToken("a Claim with its token is required")
        if rec is None or rec["state"] != "held" or rec["generation"] != claim.generation or rec["claim_id"] != claim.claim_id:
            self.telemetry.count("inv23_fencing_rejections_total", provider=self.name)
            self.telemetry.event("INV23-E008", provider=self.name, resource=claim.resource, presented_generation=claim.generation)
            raise FencingRejected(f"generation {claim.generation} is not the current owner")
        if not hmac.compare_digest(rec["token_sha256"], _h(claim.token)):
            self.telemetry.event("INV23-E006", provider=self.name, resource=claim.resource)
            raise StaleToken("token does not match the current owner")
        if not allow_expired and rec["lease_expires_at"] <= now:
            raise LeaseLost(f"lease expired at {rec['lease_expires_at']:.3f}")
        return rec

    def renew(self, claim: Claim, *, lease_s: Optional[float] = None) -> Claim:
        with self.telemetry.span("inv23.lease_renew", provider=self.name):
            with self._critical(claim.resource):
                now = self.clock()
                rec = self._read(claim.resource)
                try:
                    rec = self._check(rec, claim, now)
                except OwnershipError:
                    self.telemetry.count("inv23_claim_renew_failures_total", provider=self.name)
                    self.telemetry.event("INV23-E009", provider=self.name, resource=claim.resource)
                    raise
                ls = lease_s or rec.get("lease_s", DEFAULT_LEASE_S)
                rec["lease_expires_at"] = now + ls
                self._store(claim.resource, rec)
        return Claim(
            claim.resource,
            claim.claim_id,
            claim.generation,
            claim.token,
            rec["lease_expires_at"],
            claim.acquired_at,
            claim.holder,
            self.name,
        )

    def validate(self, claim: Claim) -> int:
        """Fencing check for downstream privileged operations; returns the generation."""
        with self._critical(claim.resource):
            self._check(self._read(claim.resource), claim, self.clock())
        return claim.generation

    def release(self, claim: Claim) -> None:
        with self._critical(claim.resource):
            rec = self._read(claim.resource)
            rec = dict(self._check(rec, claim, self.clock(), allow_expired=True))
            rec.update(state="released", released_at=self.clock())
            for k in ("token_sha256",):
                rec.pop(k, None)
            self._store(claim.resource, rec)
        self.telemetry.event("INV23-E005", provider=self.name, resource=claim.resource, generation=claim.generation)

    def status(self, resource: str = "hw-virt") -> Dict[str, Any]:
        """Diagnostic snapshot without secret material."""
        resource = validate_resource(resource)
        with self._critical(resource):
            try:
                rec = self._read(resource)
            except OwnershipCorrupt as exc:
                return {"resource": resource, "state": "corrupt", "detail": str(exc)}
            gen = self._load_generation(resource)
        if rec is None:
            return {"resource": resource, "state": "free", "generation": gen}
        out = {k: v for k, v in rec.items() if k not in ("token_sha256",)}
        if rec["state"] == "held":
            out["stale_reason"] = self._stale_reason(rec, self.clock())
        return out

    def repair(self, resource: str = "hw-virt") -> int:
        """Operator action: quarantine a corrupt record; returns the preserved generation floor."""
        resource = validate_resource(resource)
        with self._critical(resource):
            gen = self._load_generation(resource)
            self._quarantine(resource)
            self._store_generation(resource, gen + 1)
            return gen + 1
