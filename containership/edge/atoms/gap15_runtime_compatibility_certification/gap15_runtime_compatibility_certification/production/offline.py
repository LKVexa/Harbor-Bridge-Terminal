"""Offline / disconnected decision cache (component 24).

The control plane issues a signed ``GAP15_OFFLINE_BUNDLE/1`` bound to one
site/node/environment with a monotonically increasing ``counter`` (anti
rollback), a hard ``not_after`` and a revocation checkpoint age limit. Entries
are typed (certified / incompatible / untested / revoked / quarantined).
Lookup never turns absence or expiry into an allow (MC-24-04). Writes are
atomic: write temp -> fsync -> verify -> rename (MC-24-06). Eviction keeps
deny/revocation entries before positive ones (MC-24-07). Decisions made
offline are journaled for reconciliation on reconnect (MC-24-08).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from .canonical import canonical_bytes, parse
from .signing import KeyProvider, TrustStore, sign_payload, verify_payload

DENY_KINDS = {"revoked", "quarantined", "incompatible", "end-of-life"}


class OfflineError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


def build_bundle(provider: KeyProvider, key_id: str, *, site: str, node: str, environment: str, counter: int,
                 issued_at: int, not_after: int, revocation_checkpoint_at: int, policy_revision: str,
                 entries: list, max_entries: int = 10000) -> dict:
    denies = [e for e in entries if e["verdict"] in DENY_KINDS]
    others = [e for e in entries if e["verdict"] not in DENY_KINDS]
    kept = (denies + others)[:max_entries]  # deny-first retention
    body = {"schema": "GAP15_OFFLINE_BUNDLE/1", "site": site, "node": node, "environment": environment,
            "counter": counter, "issued_at": issued_at, "not_after": not_after,
            "revocation_checkpoint_at": revocation_checkpoint_at, "policy_revision": policy_revision,
            "entries": sorted(kept, key=lambda e: e["key"])}
    return {"bundle": body, "signature": sign_payload(provider, key_id, message_type="offline-bundle",
                                                      environment=environment, payload=body, signed_at=issued_at)}


@dataclass
class OfflineCache:
    path: str
    trust: TrustStore
    site: str
    node: str
    environment: str
    max_revocation_age_s: int = 3600
    bundle: Optional[dict] = None
    journal: list = field(default_factory=list)

    def _verify(self, signed: dict) -> dict:
        body = signed.get("bundle") if isinstance(signed, dict) else None
        if not isinstance(body, dict) or body.get("schema") != "GAP15_OFFLINE_BUNDLE/1":
            raise OfflineError("E_OFFLINE_SHAPE")
        res = verify_payload(self.trust, signed.get("signature"), message_type="offline-bundle",
                             environment=self.environment, payload=body, required_scope="offline:issue")
        if not res.ok:
            raise OfflineError("E_OFFLINE_SIGNATURE", res.code)
        if (body["site"], body["node"], body["environment"]) != (self.site, self.node, self.environment):
            raise OfflineError("E_OFFLINE_SCOPE", "bundle bound to a different site/node/environment")
        return body

    def install(self, signed: dict) -> None:
        body = self._verify(signed)
        if self.bundle is not None and body["counter"] <= self.bundle["counter"]:
            raise OfflineError("E_OFFLINE_ROLLBACK", "bundle counter did not advance")
        tmp = self.path + ".tmp"
        data = canonical_bytes(signed)
        with open(tmp, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        self._verify(parse(open(tmp, "rb").read(), max_bytes=64 << 20))  # re-verify what hit the disk
        os.replace(tmp, self.path)
        self.bundle = body

    def load(self) -> None:
        if not os.path.exists(self.path):
            raise OfflineError("E_OFFLINE_ABSENT")
        body = self._verify(parse(open(self.path, "rb").read(), max_bytes=64 << 20))
        if self.bundle is not None and body["counter"] < self.bundle["counter"]:
            raise OfflineError("E_OFFLINE_ROLLBACK", "on-disk bundle older than last installed")
        self.bundle = body

    def decide(self, key: str, *, now: int) -> dict:
        b = self.bundle
        if b is None:
            return self._record(key, now, "untested", "R_OFFLINE_NO_BUNDLE", False)
        if now >= b["not_after"]:
            return self._record(key, now, "untested", "R_OFFLINE_BUNDLE_EXPIRED", False)
        if now - b["revocation_checkpoint_at"] > self.max_revocation_age_s:
            return self._record(key, now, "untested", "R_OFFLINE_REVOCATION_STALE", False)
        entry = next((e for e in b["entries"] if e["key"] == key), None)
        if entry is None:
            return self._record(key, now, "untested", "R_OFFLINE_NOT_CACHED", False)
        if entry["verdict"] != "certified":
            return self._record(key, now, entry["verdict"], "R_OFFLINE_" + entry["verdict"].upper().replace("-", "_"), False)
        if now > entry["expires_at"]:
            return self._record(key, now, "expired", "R_OFFLINE_ENTRY_EXPIRED", False)
        return self._record(key, now, "certified", "R_OFFLINE_CERTIFIED", True)

    def _record(self, key: str, now: int, verdict: str, code: str, deployable: bool) -> dict:
        d = {"key": key, "at": now, "verdict": verdict, "reason_code": code, "deployable": deployable, "mode": "offline",
             "bundle_counter": self.bundle["counter"] if self.bundle else None}
        self.journal.append(d)
        return d

    def status(self, now: int) -> dict:
        b = self.bundle
        return {"mode": "offline", "bundle_counter": b["counter"] if b else None,
                "age_s": now - b["issued_at"] if b else None, "expires_in_s": b["not_after"] - now if b else None,
                "policy_revision": b["policy_revision"] if b else None}

    def reconcile(self, online_decide) -> list:
        """On reconnect: compare every offline allow with the online verdict (MC-24-08)."""
        findings = []
        for d in self.journal:
            if d["deployable"]:
                online = online_decide(d["key"], d["at"])
                if not online.get("deployable"):
                    findings.append({"key": d["key"], "offline": d["verdict"], "online": online.get("verdict")})
        return findings
