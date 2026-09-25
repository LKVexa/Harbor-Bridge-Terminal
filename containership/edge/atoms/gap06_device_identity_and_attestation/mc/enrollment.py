"""MC-03 / MC-33: cryptographic node-identity enrollment ceremony.

1. ``begin(node, ek_cert, ak_public, operator)`` -- operator must hold the
   ``enroll`` role; EK certificate chain validated against the TrustStore;
   returns a random 32-byte enrollment challenge bound to (node, EK fp, AK name).
2. ``complete(ticket, pop_signature)`` -- AK proves possession by signing
   ``b"GAP06-ENROLL/1" || challenge || ak_name``.  (A real TPM ceremony uses
   MakeCredential/ActivateCredential to bind AK to EK; that step is BLOCKED
   without a TPM and is recorded as such.)
Anti-cloning: one active AK per EK and one active node per EK; re-enrolling an
EK under a new node is refused until the old binding is revoked.  Rotation
requires a PoP by the *old* AK over the new AK name.  State lives in DurableStore.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

from . import algorithms as alg
from . import certchain
from .errors import fail

ENROLL_TTL = 300.0
DOMAIN = b"GAP06-ENROLL/1"
ROTATE = b"GAP06-ROTATE/1"


def ak_name(ak_public_pem: bytes) -> bytes:
    from cryptography.hazmat.primitives import serialization
    der = alg.load_public_key(ak_public_pem).public_bytes(serialization.Encoding.DER,
                                                          serialization.PublicFormat.SubjectPublicKeyInfo)
    return b"\x00\x0b" + hashlib.sha256(der).digest()


@dataclass
class Enrollment:
    store: object
    trust: certchain.TrustStore
    authz: object
    clock: object
    audit: object | None = None

    def _audit(self, etype, **kw):
        if self.audit is not None:
            self.audit.append(etype, self.clock.now(), **kw)

    def begin(self, node: str, ek_cert_pem: bytes, ak_public_pem: bytes, *, operator) -> dict:
        self.authz.require(operator, "enroll")
        import datetime as dt
        now = self.clock.now()
        ek = certchain.load(ek_cert_pem)
        certchain.validate(ek, self.trust, dt.datetime.fromtimestamp(now, dt.timezone.utc), leaf_usage="ek")
        from cryptography.hazmat.primitives import hashes
        ek_fp = ek.fingerprint(hashes.SHA256()).hex()
        bound = self.store.get("ek_binding", ek_fp)
        if bound and bound["node"] != node and bound["status"] == "active":
            raise fail("E_DUPLICATE_IDENTITY", "EK already bound to another active node (possible clone)")
        ticket = secrets.token_hex(16)
        chal = secrets.token_bytes(32)
        name = ak_name(ak_public_pem)
        self.store.put("enroll_pending", ticket, {"node": node, "ek_fp": ek_fp, "ak_pem": ak_public_pem.decode(),
                                                  "ak_name": name.hex(), "challenge": chal.hex(),
                                                  "expires": now + ENROLL_TTL, "operator": operator.id})
        return {"ticket": ticket, "challenge": chal, "ak_name": name}

    def complete(self, ticket: str, pop_signature: bytes) -> dict:
        now = self.clock.now()
        p = self.store.get("enroll_pending", ticket)
        if p is None:
            raise fail("E_UNISSUED_CHALLENGE", "unknown or consumed enrollment ticket")
        with self.store.transaction() as tx:
            tx.delete("enroll_pending", ticket)  # single-use regardless of outcome
        if now >= p["expires"]:
            raise fail("E_CHALLENGE_EXPIRED", "enrollment ticket expired")
        key = alg.load_public_key(p["ak_pem"].encode())
        msg = DOMAIN + bytes.fromhex(p["challenge"]) + bytes.fromhex(p["ak_name"])
        try:
            alg.verify(key, alg.profile_of(key), pop_signature, msg)
        except Exception as exc:
            self._audit("reject", node=p["node"], code="E_POP_FAILED")
            raise fail("E_POP_FAILED", "proof of possession failed") from exc
        dup = [n for n, r in self.store.items("nodes").items()
               if r["status"] == "active" and r["ak_name"] == p["ak_name"] and n != p["node"]]
        if dup:
            raise fail("E_DUPLICATE_IDENTITY", "AK already active on another node")
        rec = {"node": p["node"], "ek_fp": p["ek_fp"], "ak_pem": p["ak_pem"], "ak_name": p["ak_name"],
               "status": "active", "enrolled_at": now, "generation": 1}
        with self.store.transaction() as tx:
            tx.put("nodes", p["node"], rec)
            tx.put("ek_binding", p["ek_fp"], {"node": p["node"], "status": "active"})
        self._audit("enroll", node=p["node"], ek=p["ek_fp"], ak=p["ak_name"])
        return rec

    def rotate(self, node: str, new_ak_pem: bytes, old_ak_signature: bytes) -> dict:
        rec = self.store.get("nodes", node)
        if rec is None or rec["status"] != "active":
            raise fail("E_UNKNOWN_NODE", "node not active")
        new_name = ak_name(new_ak_pem)
        old = alg.load_public_key(rec["ak_pem"].encode())
        try:
            alg.verify(old, alg.profile_of(old), old_ak_signature, ROTATE + new_name)
        except Exception as exc:
            raise fail("E_POP_FAILED", "rotation not authorised by current AK") from exc
        rec.update(ak_pem=new_ak_pem.decode(), ak_name=new_name.hex(), generation=rec["generation"] + 1)
        self.store.put("nodes", node, rec)
        self._audit("key_rotation", node=node, ak=new_name.hex())
        return rec

    def revoke(self, node: str, *, operator, reason: str) -> None:
        self.authz.require(operator, "revoke")
        rec = self.store.get("nodes", node)
        if rec is None:
            raise fail("E_UNKNOWN_NODE", node)
        rec["status"] = "revoked"
        with self.store.transaction() as tx:
            tx.put("nodes", node, rec)
            tx.put("ek_binding", rec["ek_fp"], {"node": node, "status": "revoked"})
        self._audit("revocation", node=node, reason=reason)

    def replace(self, old_node: str, new_node: str, ek_cert_pem: bytes, ak_public_pem: bytes, *, operator) -> dict:
        """Hardware replacement / recovery: revoke then begin a fresh ceremony."""
        self.revoke(old_node, operator=operator, reason=f"replaced by {new_node}")
        return self.begin(new_node, ek_cert_pem, ak_public_pem, operator=operator)
