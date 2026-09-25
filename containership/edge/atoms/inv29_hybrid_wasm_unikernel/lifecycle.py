"""Persistence, lifecycle, idempotency, reconciliation, revocation, rollback,
emergency disable and backup/restore for INV-29 (MC059..MC066).

Storage is a directory of canonical-JSON documents written atomically
(temp file + fsync + rename).  It is the reference implementation of the
persistence model; a production deployment may back ``Store`` with another
system as long as the same contract holds (see docs/PERSISTENCE.md).
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import tempfile
import threading
import time
from typing import Callable, Dict, Iterable, Optional

from .admission import AdmissionRequest, Admitter, AttestationInvalid, ReplayDetected, verify_record
from .records import canonical, parse

# ------------------------------------------------------------------ state machine
PENDING, ADMITTED, RUNNING, REVOKED, EXPIRED, RETIRED, REFUSED = (
    "PENDING", "ADMITTED", "RUNNING", "REVOKED", "EXPIRED", "RETIRED", "REFUSED")
TRANSITIONS = {
    PENDING: {ADMITTED, REFUSED},
    ADMITTED: {RUNNING, REVOKED, EXPIRED, RETIRED},
    RUNNING: {REVOKED, RETIRED, EXPIRED},
    REVOKED: set(), EXPIRED: set(), RETIRED: set(), REFUSED: set(),
}
TERMINAL = {REVOKED, EXPIRED, RETIRED, REFUSED}


class IllegalTransition(RuntimeError):
    code = "INV29-E-LIFECYCLE"


class StoreCorrupt(RuntimeError):
    code = "INV29-E-STORE"


def _atomic_write(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


class Store:
    """Directory-backed document store keyed by composition id."""

    def __init__(self, root: os.PathLike):
        self.root = pathlib.Path(root)
        (self.root / "compositions").mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _p(self, cid: str) -> pathlib.Path:
        if not cid or any(c not in "0123456789abcdef" for c in cid) or len(cid) != 64:
            raise ValueError("composition id must be a sha256 hex string")
        return self.root / "compositions" / f"{cid}.json"

    def put(self, cid: str, doc: dict) -> None:
        body = dict(doc)
        body.pop("_digest", None)
        body["_digest"] = hashlib.sha256(canonical(body)).hexdigest()
        with self._lock:
            _atomic_write(self._p(cid), canonical(body))

    def get(self, cid: str) -> Optional[dict]:
        p = self._p(cid)
        with self._lock:
            if not p.exists():
                return None
            doc = parse(p.read_bytes())
        digest = doc.pop("_digest", None)
        if digest != hashlib.sha256(canonical(doc)).hexdigest():
            raise StoreCorrupt(f"{cid}: stored document failed its integrity check")
        return doc

    def ids(self) -> list:
        with self._lock:
            return sorted(p.stem for p in (self.root / "compositions").glob("*.json"))

    # ---------------------------------------------------------- backup/restore
    def backup(self, dest: os.PathLike) -> dict:
        """Write a self-verifying backup (one JSON file with a manifest digest)."""
        with self._lock:
            docs = {cid: self.get(cid) for cid in self.ids()}
        payload = {"format": "inv29-backup/1", "created_at": int(time.time()), "documents": docs}
        payload["manifest_sha256"] = hashlib.sha256(canonical(payload["documents"])).hexdigest()
        _atomic_write(pathlib.Path(dest), canonical(payload))
        return {"documents": len(docs), "manifest_sha256": payload["manifest_sha256"]}

    def restore(self, src: os.PathLike) -> dict:
        payload = parse(pathlib.Path(src).read_bytes())
        if payload.get("format") != "inv29-backup/1":
            raise StoreCorrupt("unknown backup format")
        if hashlib.sha256(canonical(payload["documents"])).hexdigest() != payload.get("manifest_sha256"):
            raise StoreCorrupt("backup manifest digest mismatch; refusing to restore")
        restored = kept = 0
        with self._lock:
            for cid, doc in payload["documents"].items():
                try:
                    current = self.get(cid)
                except StoreCorrupt:
                    current = None
                # never resurrect: a terminal state already recorded here (revoked, retired...)
                # outranks whatever an older backup says
                if current is not None and current.get("state") in TERMINAL and doc.get("state") != current["state"]:
                    kept += 1
                    continue
                self.put(cid, doc)
                restored += 1
        return {"restored": restored, "terminal_states_kept": kept}


def request_key(req: AdmissionRequest) -> str:
    """Idempotency key: identical logical requests map to the same composition id."""
    ident = {"tenant": req.tenant, "module": req.module.name, "host": req.host.name,
             "module_digest": req.module_digest, "host_digest": req.host_digest,
             "imports": sorted(req.module.imports), "nonce": req.nonce}
    return hashlib.sha256(canonical(ident)).hexdigest()


class Lifecycle:
    """Owns composition state; the only writer of the store."""

    def __init__(self, admitter: Admitter, store: Store, clock: Callable[[], float] = time.time):
        self.admitter, self.store, self.clock = admitter, store, clock
        self._lock = threading.RLock()

    def _transition(self, cid: str, doc: dict, to: str, reason: str) -> dict:
        frm = doc["state"]
        if to not in TRANSITIONS[frm]:
            raise IllegalTransition(f"{cid[:12]}: {frm} -> {to} is not allowed")
        doc["state"] = to
        doc.setdefault("history", []).append({"at": int(self.clock()), "from": frm, "to": to, "reason": reason[:256]})
        self.store.put(cid, doc)
        return doc

    def submit(self, req: AdmissionRequest) -> dict:
        """Idempotent: re-submitting the same request returns the stored outcome."""
        cid = request_key(req)
        with self._lock:
            existing = self.store.get(cid)
            if existing is not None:
                return existing
            doc = {"id": cid, "state": PENDING, "tenant": req.tenant, "history": []}
            try:
                record = self.admitter.admit(req)
            except Exception as exc:
                from .admission import error_code
                doc["error"] = {"code": error_code(exc), "message": str(exc)[:512]}
                return self._transition(cid, doc, REFUSED, doc["error"]["code"])
            doc["record"] = record
            return self._transition(cid, doc, ADMITTED, "admitted")

    def mark_running(self, cid: str) -> dict:
        with self._lock:
            return self._transition(cid, self._must(cid), RUNNING, "execution plane started")

    def retire(self, cid: str, reason: str = "retired") -> dict:
        with self._lock:
            return self._transition(cid, self._must(cid), RETIRED, reason)

    def revoke(self, cid: str, reason: str) -> dict:
        with self._lock:
            return self._transition(cid, self._must(cid), REVOKED, reason)

    def _must(self, cid: str) -> dict:
        doc = self.store.get(cid)
        if doc is None:
            raise KeyError(cid)
        return doc

    def reconcile(self) -> dict:
        """Re-verify every live composition against current keys, policy and time.

        Revokes a live composition whose signature/attestation key was revoked,
        whose tenant lost authorisation, whose policy generation fell behind a
        revocation floor, or which is disabled; expires records past TTL.
        Idempotent: running it twice changes nothing the second time.
        """
        now = int(self.clock())
        summary = {"checked": 0, "revoked": 0, "expired": 0, "ok": 0, "corrupt": 0}
        policy = self.admitter.policy
        for cid in self.store.ids():
            with self._lock:
                try:
                    doc = self.store.get(cid)
                except StoreCorrupt:
                    summary["corrupt"] += 1
                    continue
                if doc is None or doc["state"] in TERMINAL:
                    continue
                summary["checked"] += 1
                rec, adm = doc["record"], doc["record"]["admission"]
                reason = None
                if self.admitter.disabled is not None:
                    reason = f"emergency disable: {self.admitter.disabled}"
                elif doc["tenant"] not in policy.allowed_tenants:
                    reason = "tenant no longer authorised"
                elif any(self.admitter.keyring.is_revoked(a["key_id"]) for a in adm["attestations"]):
                    reason = "attestation key revoked"
                else:
                    try:
                        verify_record(self.admitter.keyring, rec, expected_key_id=self.admitter.signing_key_id, now=now)
                    except ReplayDetected:
                        if doc["state"] == ADMITTED:
                            self._transition(cid, doc, EXPIRED, "record TTL elapsed before start")
                            summary["expired"] += 1
                            continue
                        # a RUNNING composition outlives its admission TTL by design
                    except (AttestationInvalid, Exception) as exc:  # noqa: B014
                        reason = f"record no longer verifies: {type(exc).__name__}"
                if reason:
                    self._transition(cid, doc, REVOKED, reason)
                    summary["revoked"] += 1
                else:
                    summary["ok"] += 1
        return summary

    def counts(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for cid in self.store.ids():
            try:
                s = self.store.get(cid)["state"]
            except StoreCorrupt:
                s = "CORRUPT"
            out[s] = out.get(s, 0) + 1
        return out


# ------------------------------------------------------------------ operator control file
class ControlFile:
    """Durable operator switch for emergency disable (MC065), read on every reconcile/startup.

    ``tools/inv29ctl.py disable --reason ...`` writes it; ``apply()`` makes the
    running admitter honour it.  A corrupt control file is treated as *disabled*
    (fail closed).
    """

    def __init__(self, path: os.PathLike):
        self.path = pathlib.Path(path)

    def read(self) -> dict:
        if not self.path.exists():
            return {"disabled": None}
        try:
            data = parse(self.path.read_bytes())
            if set(data) != {"disabled", "at", "actor"}:
                raise ValueError("control file must have exactly disabled, at, actor")
            d = data["disabled"]
            if not (d is None or (type(d) is str and d.strip())):
                raise ValueError("disabled must be null or a non-empty reason")
            return data
        except Exception:
            return {"disabled": "control file unreadable; failing closed"}

    def write(self, disabled: Optional[str], actor: str) -> dict:
        data = {"disabled": disabled, "at": int(time.time()), "actor": actor[:128]}
        _atomic_write(self.path, canonical(data))
        return data

    def apply(self, admitter: Admitter) -> Optional[str]:
        reason = self.read().get("disabled")
        if reason:
            admitter.disable(reason)
        elif admitter.disabled is not None:
            admitter.enable()
        return reason
