"""Durable trust-store persistence, atomic activation, backup/restore and DR (v6).

Layout under ``root``::

    active.json            pointer: {"generation": N, "digest": ..., "file": "gen-000000N.json"}
    generations/gen-*.json signed PK_SIGNED_CONFIG/1 documents (immutable once written)
    staged/                validated-but-not-active candidates
    quarantine/            documents that failed verification (forensics only)
    floor.json             monotonic generation floor (never decreases)
    audit.jsonl            append-only hash-chained mutation log (via AuditLedger export)

Every document is signed by a *configuration-authority* key pinned separately
from artifact release signers.  Writes use write-temp + fsync + rename +
directory fsync, so a crash leaves either the prior generation or the complete
new one active.  Load performs the startup self-check (schema, signature,
digest, generation floor, referential integrity) and refuses readiness on any
failure instead of reconstructing defaults.  Readers obtain an immutable
``TrustGeneration`` snapshot through ``TrustState.current()`` (atomic reference
swap under a lock), so a verification never mixes generations.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from . import algorithms as algs
from .canonical import b64u_decode, b64u_encode, canonical_bytes, exact_fields, ld_encode, strict_loads
from .errors import GapError, fail
from .trust import Namespace, TrustGeneration

SIGNED_CONFIG = "PK_SIGNED_CONFIG/1"
MAX_CONFIG_BYTES = 8 * 1024 * 1024


# ------------------------------------------------------- config authority

@dataclass(frozen=True)
class AuthorityKey:
    kid: str
    alg: str
    spki: bytes
    purposes: frozenset[str]  # e.g. {"trust-snapshot","trust-delta","policy-bundle","waiver","break-glass"}


def _cfg_message(doc: Mapping[str, Any]) -> bytes:
    return ld_encode("signed-config/1", [("schema", doc["schema"]), ("type", doc["type"]), ("kid", doc["kid"]),
                                         ("alg", doc["alg"]), ("body_digest", doc["body_digest"])])


def sign_config(doc_type: str, body: Mapping[str, Any], *, kid: str, alg: str, signer: Callable[[bytes], bytes]) -> dict[str, Any]:
    cb = canonical_bytes(body)
    doc = {"schema": SIGNED_CONFIG, "type": doc_type, "kid": kid, "alg": alg, "body_digest": hashlib.sha256(cb).hexdigest(), "body": dict(body)}
    doc["sig"] = b64u_encode(signer(_cfg_message(doc)))
    return doc


def verify_config(doc: Mapping[str, Any], authorities: Mapping[str, AuthorityKey], *, expect_type: str,
                  profile: str = algs.PROFILE_PRODUCTION) -> Mapping[str, Any]:
    d = exact_fields(doc, {"schema", "type", "kid", "alg", "body_digest", "body", "sig"}, what="signed config")
    if d["schema"] != SIGNED_CONFIG or d["type"] != expect_type:
        raise fail("TRUST_CORRUPT", "signed config schema/type mismatch", type=str(d.get("type"))[:64])
    key = authorities.get(d["kid"])
    if key is None or key.alg != d["alg"] or expect_type not in key.purposes:
        raise fail("TRUST_CORRUPT", "config signed by an unpinned or unauthorised authority key", kid=str(d["kid"])[:128])
    if hashlib.sha256(canonical_bytes(d["body"])).hexdigest() != d["body_digest"]:
        raise fail("TRUST_CORRUPT", "config body digest mismatch")
    try:
        algs.verify_raw(key.alg, key.spki, b64u_decode(d["sig"]), _cfg_message(d), profile=profile)
    except GapError as exc:
        raise fail("TRUST_CORRUPT", "config signature invalid") from exc
    return d["body"]


# ------------------------------------------------------------- atomic IO

def atomic_write(path: str, data: bytes) -> None:
    d = os.path.dirname(path) or "."
    tmp = f"{path}.tmp-{os.getpid()}-{threading.get_ident()}"
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    try:
        dfd = os.open(d, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except OSError:  # pragma: no cover - directory fsync unsupported (Windows)
        pass


def _read_bounded(path: str) -> bytes:
    size = os.path.getsize(path)
    if size > MAX_CONFIG_BYTES:
        raise fail("INPUT_TOO_LARGE", "persisted trust document exceeds bound", path=os.path.basename(path))
    with open(path, "rb") as fh:
        return fh.read()


# ------------------------------------------------------------- state holder

class TrustState:
    """Atomic snapshot holder read by verifiers."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._current: TrustGeneration | None = None
        self._listeners: list[Callable[[TrustGeneration], None]] = []

    def current(self) -> TrustGeneration:
        cur = self._current
        if cur is None:
            raise fail("TRUST_NOT_LOADED", "no verified trust generation is active")
        return cur

    def swap(self, gen: TrustGeneration) -> None:
        with self._lock:
            if self._current is not None and gen.generation <= self._current.generation:
                raise fail("TRUST_ROLLBACK", "activation must increase generation", active=self._current.generation, offered=gen.generation)
            self._current = gen
        for cb in list(self._listeners):
            cb(gen)

    def force(self, gen: TrustGeneration) -> None:
        """Used only by the audited emergency recovery path."""
        with self._lock:
            self._current = gen
        for cb in list(self._listeners):
            cb(gen)

    def subscribe(self, cb: Callable[[TrustGeneration], None]) -> None:
        self._listeners.append(cb)


# ------------------------------------------------------------- repository

class FileTrustRepository:
    def __init__(self, root: str, namespace: Namespace, authorities: Mapping[str, AuthorityKey], state: TrustState | None = None,
                 *, audit: Any = None, profile: str = algs.PROFILE_PRODUCTION):
        self.root = root
        self.namespace = namespace
        self._auth = dict(authorities)
        self.state = state or TrustState()
        self._audit = audit
        self._profile = profile
        self._lock = threading.RLock()
        for sub in ("generations", "staged", "quarantine", "backups"):
            os.makedirs(os.path.join(root, sub), exist_ok=True)

    # helpers ------------------------------------------------------------
    def _p(self, *parts: str) -> str:
        return os.path.join(self.root, *parts)

    def _event(self, event: str, **details: Any) -> None:
        if self._audit is not None:
            self._audit.append(event, {"namespace": self.namespace.as_dict(), **details})

    def floor(self) -> int:
        try:
            return int(json.loads(_read_bounded(self._p("floor.json")))["floor"])
        except FileNotFoundError:
            return 0
        except (ValueError, KeyError, TypeError) as exc:
            raise fail("TRUST_CORRUPT", "generation floor file corrupt") from exc

    def _raise_floor(self, gen: int) -> None:
        if gen > self.floor():
            atomic_write(self._p("floor.json"), canonical_bytes({"floor": gen}))

    def _parse_doc(self, raw: bytes) -> tuple[Mapping[str, Any], TrustGeneration]:
        doc = strict_loads(raw, max_bytes=MAX_CONFIG_BYTES)
        body = verify_config(doc, self._auth, expect_type="trust-snapshot", profile=self._profile)
        gen = TrustGeneration.from_dict(body)
        if gen.namespace != self.namespace:
            raise fail("TRUST_SCOPE", "trust snapshot scoped to another namespace")
        return doc, gen

    def _quarantine(self, name: str, raw: bytes, reason: str) -> None:
        atomic_write(self._p("quarantine", f"{name}.{hashlib.sha256(raw).hexdigest()[:12]}"), raw)
        self._event("trust.quarantine", file=name, reason=reason)

    # stage / validate / commit / rollback (#24) -------------------------
    def stage(self, signed_doc: Mapping[str, Any], *, actor: str, reason: str) -> TrustGeneration:
        raw = canonical_bytes(signed_doc)
        try:
            _, gen = self._parse_doc(raw)
        except GapError as exc:
            self._quarantine("staged-rejected", raw, exc.code)
            raise
        with self._lock:
            if gen.generation <= max(self.floor(), self._active_generation()):
                self._quarantine("staged-rollback", raw, "TRUST_ROLLBACK")
                raise fail("TRUST_ROLLBACK", "staged generation not above active/floor", offered=gen.generation, floor=self.floor())
            atomic_write(self._p("staged", f"gen-{gen.generation:010d}.json"), raw)
        self._event("trust.stage", actor=actor, reason=reason, generation=gen.generation, digest=gen.digest)
        return gen

    def _active_generation(self) -> int:
        try:
            return int(json.loads(_read_bounded(self._p("active.json")))["generation"])
        except FileNotFoundError:
            return 0

    def commit(self, generation: int, *, actor: str, reason: str) -> TrustGeneration:
        with self._lock:
            staged = self._p("staged", f"gen-{generation:010d}.json")
            raw = _read_bounded(staged)
            _, gen = self._parse_doc(raw)  # re-validate at commit time
            prev = self._active_generation()
            if gen.generation <= max(prev, self.floor()):
                raise fail("TRUST_ROLLBACK", "commit would not advance generation", offered=gen.generation, active=prev)
            name = f"gen-{gen.generation:010d}.json"
            atomic_write(self._p("generations", name), raw)
            atomic_write(self._p("active.json"), canonical_bytes({"generation": gen.generation, "digest": hashlib.sha256(raw).hexdigest(), "file": name}))
            self._raise_floor(gen.generation)
            os.remove(staged)
            self.state.swap(gen)
        self._event("trust.commit", actor=actor, reason=reason, previous_generation=prev, generation=gen.generation, config_digest=gen.digest)
        return gen

    def discard_staged(self, generation: int, *, actor: str, reason: str) -> None:
        path = self._p("staged", f"gen-{generation:010d}.json")
        if os.path.exists(path):
            os.remove(path)
        self._event("trust.discard_staged", actor=actor, reason=reason, generation=generation)

    def activate(self, signed_doc: Mapping[str, Any], *, actor: str, reason: str) -> TrustGeneration:
        gen = self.stage(signed_doc, actor=actor, reason=reason)
        return self.commit(gen.generation, actor=actor, reason=reason)

    # startup self-check -------------------------------------------------
    def load(self) -> TrustGeneration:
        with self._lock:
            try:
                ptr = strict_loads(_read_bounded(self._p("active.json")))
            except FileNotFoundError as exc:
                raise fail("TRUST_NOT_LOADED", "no active trust generation persisted") from exc
            ptr = exact_fields(ptr, {"generation", "digest", "file"}, what="active pointer")
            if os.path.basename(ptr["file"]) != ptr["file"]:
                raise fail("TRUST_CORRUPT", "active pointer path traversal")
            raw = _read_bounded(self._p("generations", ptr["file"]))
            if hashlib.sha256(raw).hexdigest() != ptr["digest"]:
                self._quarantine(ptr["file"], raw, "digest")
                raise fail("TRUST_CORRUPT", "active generation digest mismatch")
            _, gen = self._parse_doc(raw)
            if gen.generation != ptr["generation"]:
                raise fail("TRUST_CORRUPT", "active pointer/generation mismatch")
            if gen.generation < self.floor():
                raise fail("TRUST_ROLLBACK", "persisted active generation is below the monotonic floor", generation=gen.generation, floor=self.floor())
            # referential integrity: every signer must have at least one leaf certificate
            identities = {c["subject"] for c in gen.certs if "ca" not in c["usages"]}
            missing = sorted(s.identity for s in gen.signers if s.identity not in identities)
            if missing:
                raise fail("TRUST_CORRUPT", "signer authorisations reference identities with no certificate", identities=missing[:8])
            cur = self._current_gen()
            if cur is None:
                self.state.force(gen)
            elif gen.generation > cur:
                self.state.swap(gen)
            self._event("trust.load", generation=gen.generation, digest=gen.digest)
            return gen

    def _current_gen(self) -> int | None:
        try:
            return self.state.current().generation
        except GapError:
            return None

    # export / import (byte preserving) ----------------------------------
    def export_active(self) -> bytes:
        ptr = json.loads(_read_bounded(self._p("active.json")))
        return _read_bounded(self._p("generations", ptr["file"]))

    # backup / restore / DR (#6, #35) ------------------------------------
    def backup(self, label: str) -> str:
        if not label.replace("-", "").isalnum():
            raise ValueError("backup label must be alphanumeric/dash")
        dest = self._p("backups", label)
        if os.path.exists(dest):
            raise FileExistsError(dest)
        os.makedirs(dest)
        for name in ("active.json", "floor.json"):
            if os.path.exists(self._p(name)):
                shutil.copy2(self._p(name), os.path.join(dest, name))
        shutil.copytree(self._p("generations"), os.path.join(dest, "generations"))
        manifest = {}
        for base, _, files in os.walk(dest):
            for f in files:
                p = os.path.join(base, f)
                manifest[os.path.relpath(p, dest)] = hashlib.sha256(_read_bounded(p)).hexdigest()
        atomic_write(os.path.join(dest, "MANIFEST.json"), canonical_bytes({"label": label, "files": manifest, "floor": self.floor()}))
        self._event("trust.backup", label=label, floor=self.floor())
        return dest

    def verify_backup(self, path: str) -> dict[str, Any]:
        man = strict_loads(_read_bounded(os.path.join(path, "MANIFEST.json")))
        for rel, dg in man["files"].items():
            p = os.path.join(path, rel)
            if not os.path.exists(p) or hashlib.sha256(_read_bounded(p)).hexdigest() != dg:
                raise fail("TRUST_CORRUPT", "backup file missing or modified", file=rel)
        ptr = strict_loads(_read_bounded(os.path.join(path, "active.json")))
        _, gen = self._parse_doc(_read_bounded(os.path.join(path, "generations", ptr["file"])))
        return {"generation": gen.generation, "digest": gen.digest, "files": len(man["files"])}

    def restore(self, path: str, *, actor: str, recovery_approval: Mapping[str, Any] | None = None) -> TrustGeneration:
        """Restore a verified backup.  A backup older than the floor needs a 2-party recovery approval."""
        info = self.verify_backup(path)
        with self._lock:
            stale = info["generation"] < self.floor()
            if stale:
                if recovery_approval is None:
                    raise fail("TRUST_ROLLBACK", "backup generation is below monotonic floor; emergency recovery approval required",
                               backup_generation=info["generation"], floor=self.floor())
                ap = exact_fields(recovery_approval, {"approval_id", "approvers", "reason", "compromise_ruled_out"}, what="recovery approval")
                if len(set(ap["approvers"])) < 2 or ap["compromise_ruled_out"] is not True:
                    raise fail("BREAK_GLASS_INVALID", "recovery approval needs two approvers and compromise review")
            for f in os.listdir(os.path.join(path, "generations")):
                src = os.path.join(path, "generations", f)
                dst = self._p("generations", f)
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
            atomic_write(self._p("active.json"), _read_bounded(os.path.join(path, "active.json")))
            if stale:
                atomic_write(self._p("floor.json"), canonical_bytes({"floor": info["generation"]}))
            gen = self._parse_doc(self.export_active())[1]
            self.state.force(gen)
        self._event("trust.restore", actor=actor, generation=gen.generation, stale_recovery=stale,
                    approval_id=(recovery_approval or {}).get("approval_id"))
        return gen
