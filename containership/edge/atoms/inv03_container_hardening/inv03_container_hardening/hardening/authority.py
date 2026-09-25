"""Authentication, authorization and the durable exception authority.

Checklist items served: 23 (persistent exception store), 24 (approval identity
and separation of duties), 25 (maximum TTL / renewal / stale sweep),
33 (authentication boundary), 34 (authorization/capability boundary),
62 (fleet-wide waiver registry view).

Design rule carried from the shop's Signing Desk: build the desk, bind nobody.
No principal, role or key is shipped enabled; a service principal can never
approve; a requester can never approve their own exception.
"""
from __future__ import annotations

import hashlib
import hmac
import threading
from dataclasses import dataclass
from typing import Iterable

from .core import AuditLedger, TrustedClock, digest

CAPABILITIES = frozenset({
    "evaluate", "baseline.install", "baseline.rollback", "exception.request",
    "exception.approve", "exception.revoke", "emergency.toggle", "quarantine.execute",
})
MAX_TOKEN_AGE = 300


class AuthError(Exception):
    def __init__(self, code: str, msg: str):
        super().__init__(f"{code}: {msg}")
        self.code = code


@dataclass(frozen=True)
class Principal:
    subject: str
    kind: str  # "human" | "service"
    roles: frozenset

    def __post_init__(self):
        if self.kind not in ("human", "service") or not self.subject:
            raise ValueError("principal needs a subject and kind human|service")


class Authenticator:
    """Item 33: HMAC bearer tokens ``subject.issued_at.nonce.mac`` bound to a directory.

    The directory is supplied by the host (an IdP adapter in production - that
    binding is BLOCKED). Replay is refused by nonce memory within the token age.
    """

    def __init__(self, key: bytes, directory: dict[str, Principal], clock: TrustedClock):
        if len(key) < 32:
            raise ValueError("auth key must be >= 32 bytes")
        self._key, self._dir, self._clock = key, dict(directory), clock
        self._seen: dict[str, int] = {}
        self._lock = threading.Lock()

    def issue(self, subject: str, nonce: str) -> str:
        at = self._clock.now()
        body = f"{subject}.{at}.{nonce}"
        return body + "." + hmac.new(self._key, body.encode(), hashlib.sha256).hexdigest()

    def authenticate(self, token: object) -> Principal:
        if not isinstance(token, str) or token.count(".") != 3 or len(token) > 512:
            raise AuthError("UNAUTHENTICATED", "malformed token")
        subject, at_s, nonce, mac = token.split(".")
        body = f"{subject}.{at_s}.{nonce}"
        if not hmac.compare_digest(mac, hmac.new(self._key, body.encode(), hashlib.sha256).hexdigest()):
            raise AuthError("UNAUTHENTICATED", "bad token signature")
        if not at_s.isdigit():
            raise AuthError("UNAUTHENTICATED", "bad issue time")
        now = self._clock.now()
        if not (0 <= now - int(at_s) <= MAX_TOKEN_AGE):
            raise AuthError("UNAUTHENTICATED", "token expired or from the future")
        with self._lock:
            self._seen = {n: t for n, t in self._seen.items() if now - t <= MAX_TOKEN_AGE}
            if nonce in self._seen:
                raise AuthError("UNAUTHENTICATED", "token replay")
            self._seen[nonce] = now
        p = self._dir.get(subject)
        if p is None:
            raise AuthError("UNAUTHENTICATED", "unknown subject")
        return p


class Authorizer:
    """Item 34: role -> capability map, sealed at construction; deny by default."""

    def __init__(self, role_caps: dict[str, Iterable[str]]):
        sealed = {}
        for role, caps in role_caps.items():
            caps = frozenset(caps)
            bad = caps - CAPABILITIES
            if bad:
                raise ValueError(f"unknown capabilities {sorted(bad)}")
            sealed[role] = caps
        self._map = sealed

    def require(self, p: Principal, cap: str) -> None:
        if cap not in CAPABILITIES:
            raise AuthError("UNAUTHORIZED", f"unknown capability {cap}")
        if cap in ("exception.approve", "baseline.install", "emergency.toggle") and p.kind != "human":
            raise AuthError("UNAUTHORIZED", f"{cap} requires a human principal")
        if not any(cap in self._map.get(r, ()) for r in p.roles):
            raise AuthError("UNAUTHORIZED", f"{p.subject} lacks {cap}")


class ExceptionStore:
    """Item 23/24/25: the durable source of truth for waivers.

    Record lifecycle: requested -> approved -> (renewed)* -> revoked|expired.
    Every transition is an audit event; the store file is rebuilt from the
    audit ledger on load, so the ledger is the authority and the view cannot
    drift from it.
    """

    def __init__(self, ledger: AuditLedger, clock: TrustedClock, authz: Authorizer,
                 max_ttl: int = 30 * 86400, max_renewals: int = 2):
        self._ledger, self._clock, self._authz = ledger, clock, authz
        self.max_ttl, self.max_renewals = max_ttl, max_renewals
        self._lock = threading.Lock()
        self._recs: dict[str, dict] = {}
        for ev in ledger.events():
            if ev["kind"].startswith("exception."):
                self._apply(ev["kind"], ev["data"])

    def _apply(self, kind: str, d: dict) -> None:
        if kind == "exception.requested":
            self._recs[d["id"]] = dict(d, state="requested", renewals=0)
        elif kind == "exception.approved":
            self._recs[d["id"]].update(state="approved", approver=d["approver"], expires=d["expires"])
        elif kind == "exception.renewed":
            r = self._recs[d["id"]]
            r.update(expires=d["expires"], renewals=r["renewals"] + 1, approver=d["approver"])
        elif kind == "exception.revoked":
            self._recs[d["id"]].update(state="revoked", revoked_by=d["by"])

    def _emit(self, kind: str, subject: str, actor: str, data: dict) -> None:
        self._ledger.append(kind, subject, actor, self._clock.now(), data)
        self._apply(kind, data)

    def request(self, p: Principal, workload: str, control: str, reason: str, ticket: str,
                owner: str, ttl: int) -> str:
        self._authz.require(p, "exception.request")
        for f, v in (("workload", workload), ("control", control), ("reason", reason),
                     ("ticket", ticket), ("owner", owner)):
            if not isinstance(v, str) or not v.strip() or len(v) > 512:
                raise AuthError("MALFORMED_INPUT", f"{f} must be a non-blank string <= 512 chars")
        if not isinstance(ttl, int) or isinstance(ttl, bool) or not (0 < ttl <= self.max_ttl):
            raise AuthError("MALFORMED_INPUT", f"ttl must be 1..{self.max_ttl}s")
        with self._lock:
            rid = digest({"w": workload, "c": control, "t": ticket, "n": len(self._recs)})[7:23]
            self._emit("exception.requested", rid, p.subject,
                       {"id": rid, "workload": workload, "control": control, "reason": reason,
                        "ticket": ticket, "owner": owner, "ttl": ttl, "requester": p.subject})
            return rid

    def approve(self, p: Principal, rid: str) -> None:
        self._authz.require(p, "exception.approve")
        with self._lock:
            r = self._recs.get(rid)
            if r is None or r["state"] != "requested":
                raise AuthError("INVALID_STATE", "only a requested exception can be approved")
            if p.subject == r["requester"]:
                raise AuthError("SEPARATION_OF_DUTIES", "requester cannot approve own exception")
            self._emit("exception.approved", rid, p.subject,
                       {"id": rid, "approver": p.subject, "expires": self._clock.now() + r["ttl"]})

    def renew(self, p: Principal, rid: str, ttl: int) -> None:
        self._authz.require(p, "exception.approve")
        with self._lock:
            r = self._recs.get(rid)
            if r is None or r["state"] != "approved":
                raise AuthError("INVALID_STATE", "only an approved exception can be renewed")
            if p.subject == r["requester"]:
                raise AuthError("SEPARATION_OF_DUTIES", "requester cannot renew own exception")
            if r["renewals"] >= self.max_renewals:
                raise AuthError("RENEWAL_LIMIT", "renewal limit reached; escalate")
            if not isinstance(ttl, int) or isinstance(ttl, bool) or not (0 < ttl <= self.max_ttl):
                raise AuthError("MALFORMED_INPUT", "ttl out of range")
            self._emit("exception.renewed", rid, p.subject,
                       {"id": rid, "approver": p.subject, "expires": self._clock.now() + ttl})

    def revoke(self, p: Principal, rid: str) -> None:
        self._authz.require(p, "exception.revoke")
        with self._lock:
            if rid not in self._recs:
                raise AuthError("INVALID_STATE", "unknown exception")
            self._emit("exception.revoked", rid, p.subject, {"id": rid, "by": p.subject})

    def active_for(self, workload: str, control: str, now: int) -> dict | None:
        for r in self._recs.values():
            if (r["workload"] == workload and r["control"] == control and r["state"] == "approved"
                    and isinstance(r.get("expires"), int) and r["expires"] > now):
                return dict(r)
        return None

    def registry(self, now: int, warn_within: int = 7 * 86400) -> list[dict]:
        """Item 62: fleet-wide waiver inventory with expiry risk flags."""
        out = []
        for r in sorted(self._recs.values(), key=lambda x: x["id"]):
            status = r["state"]
            if status == "approved" and r["expires"] <= now:
                status = "expired"
            out.append({"id": r["id"], "workload": r["workload"], "control": r["control"],
                        "owner": r["owner"], "ticket": r["ticket"], "status": status,
                        "expires": r.get("expires"), "renewals": r["renewals"],
                        "expiring_soon": status == "approved" and r["expires"] - now <= warn_within})
        return out

    def sweep(self, now: int) -> list[str]:
        """Item 25: stale-waiver sweep - lists expired or stuck-in-request waivers."""
        return [r["id"] for r in self.registry(now) if r["status"] in ("expired", "requested")]
