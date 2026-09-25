"""M06/M07/M08/M09/M13 - identity, authorization, envelope integrity, replay
defence and the tamper-evident audit pipeline.

* ``KeyRing``      - versioned HMAC keys with validity windows, rotation and
                     revocation (M06, M08 key lifecycle).
* ``sign``/``verify_mac`` - HMAC-SHA256 over the canonical request envelope
                     minus its ``mac`` field (M09 tamper resistance).
* ``ReplayGuard``  - bounded (sender, nonce) cache + clock-skew window (M09).
* ``Policy``       - default-deny capability grants per principal/tenant,
                     interface and function (M07).
* ``AuditLog``     - append-only JSONL, each record HMAC-chained to its
                     predecessor; ``verify`` detects edits, deletions,
                     reordering and truncation of the tail (M13).

The 64-bit signature fingerprint in rpc.py remains a drift detector only; all
authentication and integrity guarantees come from this module plus TLS
(transport.py).
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
import fnmatch
import hashlib
import hmac
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Iterable

from . import codec


class SecurityError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


# ------------------------------------------------------------------ keys (M06/M08)
@dataclass
class Key:
    key_id: str
    principal: str
    secret: bytes
    not_before: float = 0.0
    not_after: float = float("inf")
    revoked: bool = False

    def __repr__(self) -> str:  # never print secrets
        return f"Key({self.key_id!r}, principal={self.principal!r}, revoked={self.revoked})"


class KeyRing:
    """Thread-safe store of peer keys. Secrets never leave through repr/logs."""

    MIN_SECRET = 32

    def __init__(self) -> None:
        self._keys: dict[str, Key] = {}
        self._lock = threading.Lock()

    def add(self, key: Key) -> None:
        if len(key.secret) < self.MIN_SECRET:
            raise SecurityError("weak-key")
        with self._lock:
            if key.key_id in self._keys:
                raise SecurityError("duplicate-key-id")
            self._keys[key.key_id] = key

    def rotate(self, principal: str, new: Key, overlap_s: float, now: float) -> None:
        """Add ``new`` and end every older key of ``principal`` after ``overlap_s``."""
        self.add(new)
        with self._lock:
            for k in self._keys.values():
                if k.principal == principal and k.key_id != new.key_id and k.not_after > now + overlap_s:
                    k.not_after = now + overlap_s

    def revoke(self, key_id: str) -> None:
        with self._lock:
            if key_id in self._keys:
                self._keys[key_id].revoked = True

    def lookup(self, key_id: str, now: float) -> Key:
        with self._lock:
            k = self._keys.get(key_id)
        if k is None:
            raise SecurityError("unknown-key")
        if k.revoked:
            raise SecurityError("revoked-key")
        if not (k.not_before <= now < k.not_after):
            raise SecurityError("expired-key")
        return k

    @staticmethod
    def from_env_file(path: str | os.PathLike) -> "KeyRing":
        """Load keys from a JSON file of {key_id, principal, secret_hex,...}.

        Secrets are read from a file reference only (never inline config).
        """
        ring = KeyRing()
        for row in json.loads(Path(path).read_text(encoding="utf-8")):
            ring.add(Key(row["key_id"], row["principal"], bytes.fromhex(row["secret_hex"]),
                         float(row.get("not_before", 0)), float(row.get("not_after", float("inf")))))
        return ring


# ------------------------------------------------------------ envelope MAC (M09)
_MAC_DOMAIN = b"INV61-REQ\x00"


def _mac_input(env: dict[str, Any]) -> bytes:
    unsigned = dict(env)
    unsigned["mac"] = b""
    return _MAC_DOMAIN + codec.encode(codec.REQUEST_ENVELOPE, unsigned)


def sign(env: dict[str, Any], key: Key) -> dict[str, Any]:
    env = dict(env)
    env["key_id"] = key.key_id
    env["sender"] = key.principal
    env["mac"] = hmac.new(key.secret, _mac_input(env), hashlib.sha256).digest()
    return env


def verify_mac(env: dict[str, Any], ring: KeyRing, now: float) -> Key:
    key = ring.lookup(env["key_id"], now)
    if key.principal != env["sender"]:
        raise SecurityError("sender-key-mismatch")  # spoofed sender
    expect = hmac.new(key.secret, _mac_input(env), hashlib.sha256).digest()
    if not hmac.compare_digest(expect, env["mac"]):
        raise SecurityError("bad-mac")
    return key


# ------------------------------------------------------------ replay guard (M09)
class ReplayGuard:
    """Reject reused (sender, nonce) pairs and requests outside the time window.

    A request is fresh when ``now - window <= issued <= now + future_skew``.
    Each seen nonce is kept until ``issued + window`` (after that the freshness
    check alone rejects it), so the cache needs roughly
    ``peak_rate x (window + future_skew)`` entries.  Memory is bounded by
    ``capacity``; when full, new requests are refused with
    ``replay-cache-full`` (surfaced to callers as retryable ``overloaded``)
    rather than evicting still-valid nonces.
    """

    def __init__(self, window_ms: int = 30_000, capacity: int = 250_000, not_before_ms: int | None = None,
                 future_skew_ms: int = 5_000) -> None:
        # not_before_ms = process boot time: the cache is memory-only, so any
        # frame issued before this process started is refused, which closes the
        # replay-across-restart gap without persisting nonces.
        self.not_before_ms = not_before_ms
        self.window_ms = window_ms
        self.future_skew_ms = future_skew_ms
        self.capacity = capacity
        self._seen: "OrderedDict[tuple[str, str], int]" = OrderedDict()  # key -> expiry_ms
        self._lock = threading.Lock()

    def check(self, sender: str, nonce: str, issued_ms: int, now_ms: int) -> None:
        if len(nonce) < 16:
            raise SecurityError("weak-nonce")
        if now_ms - issued_ms > self.window_ms or issued_ms - now_ms > self.future_skew_ms:
            raise SecurityError("stale-or-future")
        if self.not_before_ms is not None and issued_ms <= self.not_before_ms:  # same-millisecond-as-boot is ambiguous: refuse
            raise SecurityError("issued-before-boot")
        with self._lock:
            seen = self._seen
            while seen:
                k, expiry = next(iter(seen.items()))
                if expiry < now_ms:
                    seen.popitem(last=False)
                else:
                    break
            key = (sender, nonce)
            if key in seen:
                raise SecurityError("replay")
            if len(seen) >= self.capacity:
                raise SecurityError("replay-cache-full")
            seen[key] = issued_ms + self.window_ms

    def __len__(self) -> int:
        return len(self._seen)


# ------------------------------------------------------------ authorization (M07)
@dataclass(frozen=True)
class Grant:
    principal: str
    tenant: str
    interface: str      # exact or fnmatch pattern
    function: str       # exact or fnmatch pattern
    expires: float = float("inf")


@dataclass
class Decision:
    allowed: bool
    reason: str
    grant: Grant | None = None


class Policy:
    """Default-deny capability policy. Deny grants always win over allows."""

    def __init__(self, grants: Iterable[Grant] = (), denies: Iterable[Grant] = (), version: str = "1") -> None:
        self.grants = list(grants)
        self.denies = list(denies)
        self.version = version

    @staticmethod
    def _match(g: Grant, principal: str, tenant: str, interface: str, function: str) -> bool:
        return (g.principal == principal and g.tenant == tenant
                and fnmatch.fnmatchcase(interface, g.interface)
                and fnmatch.fnmatchcase(function, g.function))

    def decide(self, principal: str, tenant: str, interface: str, function: str, now: float) -> Decision:
        for d in self.denies:
            if self._match(d, principal, tenant, interface, function):
                return Decision(False, "explicit-deny", d)
        for g in self.grants:
            if self._match(g, principal, tenant, interface, function):
                if now >= g.expires:
                    return Decision(False, "grant-expired", g)
                return Decision(True, "granted", g)
        return Decision(False, "no-grant")

    @staticmethod
    def from_dict(doc: dict[str, Any]) -> "Policy":
        def mk(rows):
            return [Grant(r["principal"], r["tenant"], r["interface"], r["function"],
                          float(r.get("expires", float("inf")))) for r in rows]
        return Policy(mk(doc.get("grants", [])), mk(doc.get("denies", [])), str(doc.get("version", "1")))


# ------------------------------------------------------------ audit (M13)
AUDIT_EVENTS = frozenset({
    "authn-failure", "authz-deny", "authz-allow", "replay-rejected", "version-drift",
    "signature-mismatch", "config-activated", "config-rolled-back", "emergency-disable",
    "emergency-enable", "key-rotated", "key-revoked", "negotiation-failure", "fence-rejected",
})


class AuditLog:
    """Append-only HMAC-chained audit ledger (JSONL)."""

    GENESIS = "0" * 64

    def __init__(self, path: str | os.PathLike, key: bytes, fsync: bool = True) -> None:
        if len(key) < 32:
            raise SecurityError("weak-audit-key")
        self.path = Path(path)
        self._key = key
        self._fsync = fsync
        self._lock = threading.Lock()
        self.head, self.seq = self.GENESIS, 0
        if self.path.exists():
            ok, n, head = self.verify(self.path, key)
            if not ok:
                raise SecurityError("audit-chain-broken")
            self.head, self.seq = head, n

    def _mac(self, prev: str, body: str) -> str:
        return hmac.new(self._key, (prev + "\n" + body).encode(), hashlib.sha256).hexdigest()

    def append(self, event: str, **fields: Any) -> str:
        if event not in AUDIT_EVENTS:
            raise SecurityError("unknown-audit-event")
        with self._lock:
            rec = {"seq": self.seq + 1, "ts": round(time.time(), 6), "event": event, **fields}
            body = json.dumps(rec, sort_keys=True, separators=(",", ":"), default=str)
            mac = self._mac(self.head, body)
            line = json.dumps({"body": body, "prev": self.head, "mac": mac}, separators=(",", ":"))
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
                fh.flush()
                if self._fsync:
                    os.fsync(fh.fileno())
            self.head, self.seq = mac, self.seq + 1
            return mac

    @classmethod
    def verify(cls, path: str | os.PathLike, key: bytes, expected_head: str | None = None) -> tuple[bool, int, str]:
        prev, n = cls.GENESIS, 0
        try:
            lines = Path(path).read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return (expected_head in (None, cls.GENESIS), 0, cls.GENESIS)
        for line in lines:
            try:
                row = json.loads(line)
                body = row["body"]
                seq = json.loads(body)["seq"]
            except (ValueError, KeyError, TypeError):
                return False, n, prev
            if row["prev"] != prev or seq != n + 1:
                return False, n, prev
            mac = hmac.new(key, (prev + "\n" + body).encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(mac, row["mac"]):
                return False, n, prev
            prev, n = mac, n + 1
        if expected_head is not None and prev != expected_head:
            return False, n, prev  # tail truncation detected against an anchored head
        return True, n, prev
