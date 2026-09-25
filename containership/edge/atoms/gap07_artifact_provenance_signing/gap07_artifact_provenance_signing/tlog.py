"""Transparency log: RFC 6962/9162 Merkle proofs, signed checkpoints, offline cache.

Verification never trusts a server boolean: inclusion proofs are recomputed
locally against a checkpoint whose signature verifies under a *pinned* log key
(log keys rotate via the pinned-key set, not via the server).  Consistency
proofs between the cached and a newly observed checkpoint detect equivocation
and rollback.  ``CheckpointCache`` persists the highest trusted checkpoint
per log, enforces monotonic tree size and age budgets, and is itself
integrity-protected (digest + checkpoint signature re-verified on load).

``LocalTransparencyLog`` is a complete append-only log service (used for the
audit anchoring and in tests); ``RekorClient`` is a bounded HTTP client
skeleton whose responses flow through the same local verification.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from . import algorithms as algs
from .canonical import b64u_decode, b64u_encode, canonical_bytes, exact_fields, ld_encode
from .errors import GapError, fail

CHECKPOINT_SCHEMA = "PK_CHECKPOINT/1"
ENTRY_SCHEMA = "PK_TLOG_ENTRY/1"
MAX_PROOF = 64


def leaf_hash(data: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + data).digest()


def node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def _largest_pow2_lt(n: int) -> int:
    k = 1
    while k << 1 < n:
        k <<= 1
    return k


def mth(leaves: Sequence[bytes]) -> bytes:
    n = len(leaves)
    if n == 0:
        return hashlib.sha256(b"").digest()
    if n == 1:
        return leaf_hash(leaves[0])
    k = _largest_pow2_lt(n)
    return node_hash(mth(leaves[:k]), mth(leaves[k:]))


def inclusion_path(index: int, leaves: Sequence[bytes]) -> list[bytes]:
    n = len(leaves)
    if n <= 1:
        return []
    k = _largest_pow2_lt(n)
    if index < k:
        return inclusion_path(index, leaves[:k]) + [mth(leaves[k:])]
    return inclusion_path(index - k, leaves[k:]) + [mth(leaves[:k])]


def consistency_path(m: int, leaves: Sequence[bytes]) -> list[bytes]:
    def sub(m: int, d: Sequence[bytes], complete: bool) -> list[bytes]:
        n = len(d)
        if m == n:
            return [] if complete else [mth(d)]
        k = _largest_pow2_lt(n)
        if m <= k:
            return sub(m, d[:k], complete) + [mth(d[k:])]
        return sub(m - k, d[k:], False) + [mth(d[:k])]

    return sub(m, leaves, True)


def verify_inclusion(leaf: bytes, index: int, size: int, proof: Sequence[bytes], root: bytes) -> bool:
    """RFC 9162 section 2.1.3.2."""
    if not 0 <= index < size or len(proof) > MAX_PROOF:
        return False
    fn, sn = index, size - 1
    r = leaf_hash(leaf)
    for p in proof:
        if sn == 0:
            return False
        if fn & 1 or fn == sn:
            r = node_hash(p, r)
            if not fn & 1:
                while fn and not fn & 1:
                    fn >>= 1
                    sn >>= 1
        else:
            r = node_hash(r, p)
        fn >>= 1
        sn >>= 1
    return sn == 0 and hmac.compare_digest(r, root)


def verify_consistency(size1: int, size2: int, root1: bytes, root2: bytes, proof: Sequence[bytes]) -> bool:
    """RFC 9162 section 2.1.4.2."""
    if size1 > size2 or len(proof) > MAX_PROOF:
        return False
    if size1 == size2:
        return not proof and hmac.compare_digest(root1, root2)
    if size1 == 0:
        return True
    path = list(proof)
    if size1 & (size1 - 1) == 0:  # power of two
        path = [root1] + path
    if not path:
        return False
    fn, sn = size1 - 1, size2 - 1
    while fn & 1:
        fn >>= 1
        sn >>= 1
    fr = sr = path[0]
    for c in path[1:]:
        if sn == 0:
            return False
        if fn & 1 or fn == sn:
            fr = node_hash(c, fr)
            sr = node_hash(c, sr)
            if not fn & 1:
                while fn and not fn & 1:
                    fn >>= 1
                    sn >>= 1
        else:
            sr = node_hash(sr, c)
        fn >>= 1
        sn >>= 1
    return sn == 0 and hmac.compare_digest(fr, root1) and hmac.compare_digest(sr, root2)


def _cp_message(cp: Mapping[str, Any]) -> bytes:
    return ld_encode("checkpoint/1", [(k, cp[k]) for k in ("schema", "origin", "log_key_id", "alg", "size", "root", "timestamp")])


def entry_bytes(kind: str, subject_digest: str, envelope_digest: str) -> bytes:
    """Canonical leaf content binding the exact signature/attestation evaluated."""
    return canonical_bytes({"schema": ENTRY_SCHEMA, "kind": kind, "subject_digest": subject_digest, "envelope_digest": envelope_digest})


class LocalTransparencyLog:
    """Append-only log with signed checkpoints (single-writer, thread-safe)."""

    def __init__(self, origin: str, log_key_id: str, alg: str, signer: Callable[[bytes], bytes]):
        self.origin, self.log_key_id, self.alg = origin, log_key_id, alg
        self._sign = signer
        self._leaves: list[bytes] = []
        self._index: dict[bytes, int] = {}
        self._lock = threading.Lock()
        self.available = True

    def _up(self) -> None:
        if not self.available:
            raise fail("TLOG_UNAVAILABLE", "transparency log unavailable")

    def append(self, data: bytes) -> int:
        self._up()
        with self._lock:
            lh = leaf_hash(data)
            if lh in self._index:  # idempotent: duplicate entries return existing index
                return self._index[lh]
            self._leaves.append(bytes(data))
            self._index[lh] = len(self._leaves) - 1
            return len(self._leaves) - 1

    def checkpoint(self, timestamp: int) -> dict[str, Any]:
        self._up()
        with self._lock:
            body = {"schema": CHECKPOINT_SCHEMA, "origin": self.origin, "log_key_id": self.log_key_id, "alg": self.alg,
                    "size": len(self._leaves), "root": b64u_encode(mth(self._leaves)), "timestamp": timestamp}
        return {**body, "sig": b64u_encode(self._sign(_cp_message(body)))}

    def prove_inclusion(self, index: int, size: int) -> list[str]:
        self._up()
        with self._lock:
            return [b64u_encode(h) for h in inclusion_path(index, self._leaves[:size])]

    def prove_consistency(self, size1: int, size2: int) -> list[str]:
        self._up()
        with self._lock:
            return [b64u_encode(h) for h in consistency_path(size1, self._leaves[:size2])] if size1 else []


@dataclass(frozen=True)
class LogKey:
    origin: str
    log_key_id: str
    alg: str
    spki: bytes


def verify_checkpoint(cp: Mapping[str, Any], log_keys: Mapping[str, LogKey], *, profile: str = algs.PROFILE_PRODUCTION) -> dict[str, Any]:
    cp = dict(exact_fields(cp, {"schema", "origin", "log_key_id", "alg", "size", "root", "timestamp", "sig"}, what="checkpoint"))
    if cp["schema"] != CHECKPOINT_SCHEMA:
        raise fail("TLOG_CHECKPOINT_INVALID", "unsupported checkpoint schema")
    key = log_keys.get(cp["log_key_id"])
    if key is None or key.origin != cp["origin"] or key.alg != cp["alg"]:
        raise fail("TLOG_CHECKPOINT_INVALID", "checkpoint signed by unpinned log key", log_key_id=str(cp["log_key_id"])[:128])
    for k in ("size", "timestamp"):
        if isinstance(cp[k], bool) or not isinstance(cp[k], int) or cp[k] < 0:
            raise fail("TLOG_CHECKPOINT_INVALID", f"checkpoint {k} invalid")
    if len(b64u_decode(cp["root"])) != 32:
        raise fail("TLOG_CHECKPOINT_INVALID", "checkpoint root invalid")
    try:
        algs.verify_raw(key.alg, key.spki, b64u_decode(cp["sig"]), _cp_message(cp), profile=profile)
    except GapError as exc:
        raise fail("TLOG_CHECKPOINT_INVALID", "checkpoint signature invalid") from exc
    return cp


def verify_inclusion_evidence(evidence: Mapping[str, Any], *, entry: bytes, log_keys: Mapping[str, LogKey],
                              now: int, max_checkpoint_age_s: int, profile: str = algs.PROFILE_PRODUCTION) -> dict[str, Any]:
    ev = exact_fields(evidence, {"index", "checkpoint", "proof"}, what="inclusion evidence")
    cp = verify_checkpoint(ev["checkpoint"], log_keys, profile=profile)
    if now - cp["timestamp"] > max_checkpoint_age_s:
        raise fail("TLOG_CHECKPOINT_STALE", "checkpoint too old", checkpoint_time=cp["timestamp"], now=now)
    if not isinstance(ev["proof"], list) or len(ev["proof"]) > MAX_PROOF:
        raise fail("TLOG_PROOF_INVALID", "inclusion proof malformed")
    proof = [b64u_decode(p) for p in ev["proof"]]
    if not isinstance(ev["index"], int) or isinstance(ev["index"], bool):
        raise fail("TLOG_PROOF_INVALID", "inclusion index invalid")
    if not verify_inclusion(entry, ev["index"], cp["size"], proof, b64u_decode(cp["root"])):
        raise fail("TLOG_PROOF_INVALID", "inclusion proof does not verify against checkpoint")
    return {"log_origin": cp["origin"], "log_key_id": cp["log_key_id"], "index": ev["index"], "tree_size": cp["size"],
            "checkpoint_digest": hashlib.sha256(canonical_bytes(cp)).hexdigest(),
            "proof_digest": hashlib.sha256(b"".join(proof)).hexdigest(), "entry_digest": hashlib.sha256(entry).hexdigest(),
            "verified_at": now}


class CheckpointCache:
    """Monotonic, persisted, age-bounded trusted checkpoint cache (offline sites)."""

    def __init__(self, log_keys: Mapping[str, LogKey], path: str | None = None, *, on_security_event: Callable[[str, dict], None] | None = None,
                 profile: str = algs.PROFILE_PRODUCTION):
        self._keys = dict(log_keys)
        self._path = path
        self._evt = on_security_event or (lambda e, d: None)
        self._profile = profile
        self._lock = threading.Lock()
        self._trusted: dict[str, dict[str, Any]] = {}
        if path and os.path.exists(path):
            self._load()

    def _load(self) -> None:
        try:
            with open(self._path, "rb") as fh:  # type: ignore[arg-type]
                raw = fh.read(1 << 20)
            doc = json.loads(raw)
            body, dg = doc["checkpoints"], doc["digest"]
            if hashlib.sha256(canonical_bytes(body)).hexdigest() != dg:
                raise ValueError("digest")
            for origin, cp in body.items():
                self._trusted[origin] = verify_checkpoint(cp, self._keys, profile=self._profile)
        except (OSError, ValueError, KeyError, TypeError, GapError) as exc:
            self._evt("tlog.cache_corrupt", {"path": str(self._path)})
            raise fail("TLOG_CHECKPOINT_INVALID", "checkpoint cache corrupt; refusing to trust") from exc

    def _save(self) -> None:
        if not self._path:
            return
        doc = {"checkpoints": self._trusted, "digest": hashlib.sha256(canonical_bytes(self._trusted)).hexdigest()}
        tmp = self._path + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(canonical_bytes(doc))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self._path)

    def trusted(self, origin: str) -> dict[str, Any] | None:
        return self._trusted.get(origin)

    def observe(self, cp: Mapping[str, Any], consistency_proof: Sequence[str] | None) -> dict[str, Any]:
        cp = verify_checkpoint(cp, self._keys, profile=self._profile)
        with self._lock:
            old = self._trusted.get(cp["origin"])
            if old is not None:
                if cp["size"] < old["size"] or cp["timestamp"] < old["timestamp"]:
                    self._evt("tlog.rollback", {"origin": cp["origin"], "old_size": old["size"], "new_size": cp["size"]})
                    raise fail("TLOG_ROLLBACK", "smaller/older tree head offered", old_size=old["size"], new_size=cp["size"])
                proof = [b64u_decode(p) for p in (consistency_proof or [])]
                if not verify_consistency(old["size"], cp["size"], b64u_decode(old["root"]), b64u_decode(cp["root"]), proof):
                    self._evt("tlog.inconsistent", {"origin": cp["origin"], "old_size": old["size"], "new_size": cp["size"]})
                    raise fail("TLOG_ROLLBACK", "consistency proof failed: possible equivocation/split view")
            self._trusted[cp["origin"]] = cp
            self._save()
            return cp

    def reset_anchor(self, cp: Mapping[str, Any], *, recovery_approval: Mapping[str, Any]) -> None:
        """Explicit, audited recovery path to accept a new (possibly smaller) log anchor."""
        exact_fields(recovery_approval, {"approval_id", "approvers", "reason"}, what="recovery approval")
        if len(set(recovery_approval["approvers"])) < 2:
            raise fail("BREAK_GLASS_INVALID", "log anchor reset needs two distinct approvers")
        cp = verify_checkpoint(cp, self._keys, profile=self._profile)
        with self._lock:
            self._evt("tlog.anchor_reset", {"origin": cp["origin"], "approval_id": recovery_approval["approval_id"]})
            self._trusted[cp["origin"]] = cp
            self._save()

    def check_fresh(self, origin: str, now: int, max_age_s: int) -> dict[str, Any]:
        cp = self._trusted.get(origin)
        if cp is None:
            raise fail("TLOG_REQUIRED", "no trusted checkpoint for log", origin=origin)
        if now - cp["timestamp"] > max_age_s:
            raise fail("TLOG_CHECKPOINT_STALE", "cached checkpoint exceeds offline age budget", origin=origin)
        return cp


def compare_views(site_checkpoints: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Auditor hook: report same-size/different-root checkpoints across sites (split view)."""
    by_size: dict[tuple[str, int], dict[str, str]] = {}
    alerts = []
    for site, cp in site_checkpoints.items():
        roots = by_size.setdefault((cp["origin"], cp["size"]), {})
        roots[site] = cp["root"]
    for (origin, size), roots in by_size.items():
        if len(set(roots.values())) > 1:
            alerts.append({"event": "tlog.split_view", "origin": origin, "size": size, "sites": sorted(roots)})
    return alerts


class RekorClient:
    """Bounded HTTPS client adapter for a Rekor-compatible log (injected session).

    Only transport is delegated: every response is verified locally with
    ``verify_checkpoint`` / ``verify_inclusion`` before use.
    """

    def __init__(self, session: Any, base_url: str, *, timeout_s: float = 5.0, max_response: int = 1 << 20):
        if not base_url.startswith("https://"):
            raise ValueError("transparency service must use HTTPS")
        self._s, self._u, self._t, self._max = session, base_url.rstrip("/"), timeout_s, max_response

    def _get(self, path: str) -> Any:
        try:
            r = self._s.get(self._u + path, timeout=self._t, stream=True)
            body = r.raw.read(self._max + 1) if hasattr(r, "raw") else r.content
        except Exception as exc:  # noqa: BLE001
            raise fail("TLOG_UNAVAILABLE", "transparency service request failed") from exc
        if getattr(r, "status_code", 200) != 200:
            raise fail("TLOG_UNAVAILABLE", "transparency service error", status=getattr(r, "status_code", 0))
        if len(body) > self._max:
            raise fail("INPUT_TOO_LARGE", "transparency response too large")
        from .canonical import strict_loads
        return strict_loads(body)

    def entry_by_uuid(self, uuid_: str) -> Any:
        if not uuid_.isalnum() or len(uuid_) > 128:
            raise fail("ENVELOPE_MALFORMED", "invalid log entry id")
        return self._get(f"/api/v1/log/entries/{uuid_}")
