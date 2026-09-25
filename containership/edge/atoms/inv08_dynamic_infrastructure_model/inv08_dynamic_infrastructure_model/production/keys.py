"""Component 38 - key hierarchy bookkeeping, rotation, revocation, compromise (``PK_DYN_KEYS/1``).

Hierarchy: ROOT (supplied bytes; stands in for a KMS/HSM-held root) -> KEK
(per domain, versioned) -> DEK (per purpose, versioned, bound to a KEK version).
Derivation is HKDF-SHA256 (RFC 5869) with ``info = "inv08/<level>/<name>/v<n>"``;
key bytes never appear in ``describe()``/``repr``.

States: ACTIVE (encrypt+decrypt) -> DECRYPT_ONLY (until overlap window ends) ->
RETIRED; any -> REVOKED (terminal).  Revoking a KEK revokes its DEKs.

Out of scope, not implemented, and BLOCKED:
  * transport mTLS - needs a certificate authority / workload identity issuer;
  * at-rest encryption - stdlib has no vetted AEAD cipher; needs a vetted library
    or KMS envelope encryption.  ``AT_REST_BOUNDARIES`` only records *where* it applies;
  * KMS/HSM custody of ROOT - no KMS binding exists (``core.TrustRoot`` refuses production keys).
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from typing import Callable

from .core import Inv08Error, Outcome

SCHEMA = "PK_DYN_KEYS/1"
STATES = ("ACTIVE", "DECRYPT_ONLY", "RETIRED", "REVOKED")

TRANSPORT_POLICY = {
    "status": "BLOCKED", "blocker": "workload CA / SPIFFE issuer and TLS termination config",
    "required": {"min_tls": "1.3", "mutual": True, "identity": "spiffe://inv08/<tenant>/<workload>"},
}
AT_REST_BOUNDARIES = [
    {"store": "pool_state snapshot", "key": "DEK state/v*", "status": "BLOCKED"},
    {"store": "decision journal", "key": "DEK journal/v*", "status": "BLOCKED"},
    {"store": "tenant state", "key": "DEK tenant-<id>/v*", "status": "BLOCKED"},
    {"store": "audit log", "key": "none - integrity only (hash chain + HMAC checkpoint)", "status": "N/A"},
]
AT_REST_BLOCKER = "vetted AEAD implementation (e.g. AES-GCM via audited library) or KMS envelope encryption"


def hkdf_sha256(ikm: bytes, *, salt: bytes = b"", info: bytes = b"", length: int = 32) -> bytes:
    if not 0 < length <= 255 * 32:
        raise ValueError("bad HKDF length")
    prk = hmac.new(salt or b"\x00" * 32, ikm, hashlib.sha256).digest()
    okm, t, i = b"", b"", 0
    while len(okm) < length:
        i += 1
        t = hmac.new(prk, t + info + bytes([i]), hashlib.sha256).digest()
        okm += t
    return okm[:length]


def _err(name: str, msg: str) -> Inv08Error:
    return Inv08Error(f"INV08.KEYS.{name}", msg, outcome=Outcome.OPERATOR_REQUIRED, severity="critical")


@dataclass
class KeyVersion:
    level: str      # KEK|DEK
    name: str
    version: int
    parent: tuple | None   # (kek_name, kek_version) for DEKs
    created: float
    state: str = "ACTIVE"
    decrypt_until: float | None = None
    _material: bytes = field(default=b"", repr=False)

    def describe(self) -> dict:
        return {"level": self.level, "name": self.name, "version": self.version,
                "parent": list(self.parent) if self.parent else None, "state": self.state,
                "created": self.created, "decrypt_until": self.decrypt_until,
                "fingerprint": hashlib.sha256(b"fp" + self._material).hexdigest()[:16]}


class KeyHierarchy:
    def __init__(self, root: bytes, clock: Callable[[], float], *, overlap: float = 86400.0, audit=None) -> None:
        if len(root) < 32:
            raise ValueError("root key must be >= 32 bytes")
        self._root, self.clock, self.overlap, self.audit = root, clock, overlap, audit
        self.keys: dict[tuple, KeyVersion] = {}   # (level, name, version)

    def __repr__(self) -> str:
        return f"KeyHierarchy({len(self.keys)} versions)"

    def _log(self, action: str, res: str, details: dict) -> None:
        if self.audit is not None:
            self.audit.append("key-manager", action, res, "SUCCESS", details)

    def _latest(self, level: str, name: str) -> KeyVersion | None:
        vs = [k for (l, n, _), k in self.keys.items() if l == level and n == name]
        return max(vs, key=lambda k: k.version) if vs else None

    def _new(self, level: str, name: str, parent: KeyVersion | None) -> KeyVersion:
        prev = self._latest(level, name)
        ver = prev.version + 1 if prev else 1
        ikm = self._root if parent is None else parent._material
        mat = hkdf_sha256(ikm, salt=SCHEMA.encode(), info=f"inv08/{level}/{name}/v{ver}".encode())
        now = self.clock()
        if prev and prev.state == "ACTIVE":
            prev.state, prev.decrypt_until = "DECRYPT_ONLY", now + self.overlap
        kv = KeyVersion(level, name, ver, (parent.name, parent.version) if parent else None, now,
                        _material=mat)
        self.keys[(level, name, ver)] = kv
        self._log("key.create", f"{level}:{name}:v{ver}", kv.describe())
        return kv

    def create_kek(self, name: str) -> KeyVersion:
        return self._new("KEK", name, None)

    def create_dek(self, name: str, kek: str) -> KeyVersion:
        parent = self.active("KEK", kek)
        return self._new("DEK", name, parent)

    rotate_kek = create_kek

    def rotate_dek(self, name: str) -> KeyVersion:
        cur = self._latest("DEK", name)
        if cur is None:
            raise _err("UNKNOWN_KEY", name)
        return self.create_dek(name, cur.parent[0])

    def tick(self) -> list[str]:
        """Retire DECRYPT_ONLY versions whose overlap window has ended."""
        now, out = self.clock(), []
        for kv in self.keys.values():
            if kv.state == "DECRYPT_ONLY" and kv.decrypt_until is not None and now >= kv.decrypt_until:
                kv.state = "RETIRED"
                out.append(f"{kv.level}:{kv.name}:v{kv.version}")
        return out

    def active(self, level: str, name: str) -> KeyVersion:
        kv = self._latest(level, name)
        if kv is None or kv.state != "ACTIVE":
            raise _err("NO_ACTIVE_KEY", f"no active {level} {name}")
        return kv

    def usable_for_decrypt(self, level: str, name: str, version: int) -> bool:
        self.tick()
        kv = self.keys.get((level, name, version))
        return kv is not None and kv.state in ("ACTIVE", "DECRYPT_ONLY")

    def material_for(self, level: str, name: str, version: int, *, purpose: str) -> bytes:
        """Return key bytes for a caller-side operation (e.g. HMAC).  Fails closed."""
        kv = self.keys.get((level, name, version))
        if kv is None:
            raise _err("UNKNOWN_KEY", f"{level}:{name}:v{version}")
        if purpose == "encrypt" and kv.state != "ACTIVE":
            raise _err("KEY_NOT_ACTIVE", f"{level}:{name}:v{version} is {kv.state}")
        if purpose == "decrypt" and not self.usable_for_decrypt(level, name, version):
            raise _err("KEY_NOT_USABLE", f"{level}:{name}:v{version} is {kv.state}")
        if purpose not in ("encrypt", "decrypt"):
            raise ValueError("purpose must be encrypt|decrypt")
        return kv._material

    def revoke(self, level: str, name: str, version: int, reason: str) -> list[str]:
        kv = self.keys.get((level, name, version))
        if kv is None:
            raise _err("UNKNOWN_KEY", f"{level}:{name}:v{version}")
        hit = [kv]
        if level == "KEK":
            hit += [d for d in self.keys.values() if d.level == "DEK" and d.parent == (name, version)]
        ids = []
        for k in hit:
            k.state, k.decrypt_until = "REVOKED", None
            ids.append(f"{k.level}:{k.name}:v{k.version}")
        self._log("key.revoke", ids[0], {"revoked": ids, "reason": reason})
        return ids

    def compromise(self, kek: str) -> dict:
        """Compromise procedure for a KEK: revoke every version + child DEKs, mint a new
        KEK and fresh DEKs, and return the re-wrap work list (data under revoked DEKs)."""
        versions = [kv.version for (l, n, _), kv in self.keys.items() if l == "KEK" and n == kek]
        if not versions:
            raise _err("UNKNOWN_KEY", kek)
        dek_names = sorted({d.name for d in self.keys.values() if d.level == "DEK" and d.parent[0] == kek})
        revoked: list[str] = []
        for v in versions:
            if self.keys[("KEK", kek, v)].state != "REVOKED":
                revoked += self.revoke("KEK", kek, v, "compromise")
        new_kek = self._new("KEK", kek, None)
        new_deks = [self.create_dek(d, kek).describe() for d in dek_names]
        report = {"kek": kek, "revoked": revoked, "new_kek": new_kek.describe(), "new_deks": new_deks,
                  "rewrap_required": [r for r in revoked if r.startswith("DEK:")],
                  "manual_steps": ["rotate ROOT in KMS if ROOT exposure cannot be excluded (BLOCKED: no KMS)",
                                   "re-encrypt data under rewrap_required (BLOCKED: no cipher)",
                                   "incident owner sign-off (UNASSIGNED)"]}
        self._log("key.compromise", kek, {k: report[k] for k in ("revoked", "rewrap_required")})
        return report
