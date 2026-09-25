"""Durable state: certifications, audit chain, drift history, config revisions, site branch
(MC-09, MC-21, MC-23, MC-41, MC-43, MC-48, MC-49, MC-60).

Reference backend: transactional SQLite (WAL, immediate transactions).  Every
mutation and its audit event commit in the same transaction, so no state
change can bypass the audit chain.  Signed certificate bytes are stored
verbatim and re-hashed on every read; enforcement never reconstructs a signed
object from index columns.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Callable, Iterator

from . import canonical, lifecycle
from .errors import Inv22Error

SCHEMA_VERSION = 1
_GENESIS = "sha256:" + "0" * 64

MIGRATIONS: dict[int, list[str]] = {
    1: [
        """CREATE TABLE certs(cert_id TEXT PRIMARY KEY, component TEXT NOT NULL, branch TEXT NOT NULL,
               issuer TEXT NOT NULL, not_after INTEGER NOT NULL, status TEXT NOT NULL,
               successor TEXT, envelope BLOB NOT NULL, envelope_digest TEXT NOT NULL, rev INTEGER NOT NULL)""",
        "CREATE TABLE cert_artifacts(cert_id TEXT NOT NULL, artifact_digest TEXT NOT NULL, PRIMARY KEY(cert_id, artifact_digest))",
        "CREATE INDEX ix_cert_art ON cert_artifacts(artifact_digest)",
        "CREATE INDEX ix_cert_comp ON certs(component, branch, status)",
        """CREATE TABLE audit(seq INTEGER PRIMARY KEY, ts INTEGER NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
               object TEXT NOT NULL, before TEXT, after TEXT, reason TEXT, prev_hash TEXT NOT NULL, hash TEXT NOT NULL)""",
        """CREATE TABLE drift(release TEXT PRIMARY KEY, seq INTEGER UNIQUE NOT NULL, matrix_digest TEXT NOT NULL,
               divergent INTEGER NOT NULL, per_interface TEXT NOT NULL, recorded_at INTEGER NOT NULL, actor TEXT NOT NULL)""",
        """CREATE TABLE config_revisions(rev INTEGER PRIMARY KEY, digest TEXT NOT NULL, doc TEXT NOT NULL,
               actor TEXT NOT NULL, created INTEGER NOT NULL, state TEXT NOT NULL, prev_active INTEGER)""",
        """CREATE TABLE site(site TEXT PRIMARY KEY, branch TEXT NOT NULL, baseline TEXT NOT NULL, epoch INTEGER NOT NULL,
               actor TEXT NOT NULL, ts INTEGER NOT NULL, frozen INTEGER NOT NULL DEFAULT 0)""",
        "CREATE TABLE kv(k TEXT PRIMARY KEY, v TEXT NOT NULL)",
        # append-only guarantees enforced by the database itself
        "CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT, 'audit is append-only'); END",
        "CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT, 'audit is append-only'); END",
        "CREATE TRIGGER drift_no_update BEFORE UPDATE ON drift BEGIN SELECT RAISE(ABORT, 'drift history is immutable'); END",
        "CREATE TRIGGER drift_no_delete BEFORE DELETE ON drift BEGIN SELECT RAISE(ABORT, 'drift history is immutable'); END",
    ],
}


def _h(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def _blob(v) -> bytes | None:
    """Stored envelopes must be BLOBs; any other storage class is treated as corruption."""
    return bytes(v) if isinstance(v, (bytes, bytearray, memoryview)) else None


class Store:
    def __init__(self, path: str, *, clock: Callable[[], int] = lambda: int(time.time()), read_only: bool = False) -> None:
        self.path, self.clock, self.read_only = path, clock, read_only
        uri = f"file:{path}?mode=ro" if read_only else f"file:{path}"
        try:
            self.db = sqlite3.connect(uri, uri=True, isolation_level=None, timeout=5, check_same_thread=False)
        except sqlite3.Error as e:
            raise Inv22Error("INV22.STORAGE.FAILURE", "cannot open store") from e
        self.db.execute("PRAGMA foreign_keys=ON")
        if not read_only:
            self.db.execute("PRAGMA journal_mode=WAL")
            self.migrate()
        self._check_version()

    # -- schema / migrations (MC-49) -------------------------------------
    def schema_version(self) -> int:
        try:
            row = self.db.execute("SELECT v FROM kv WHERE k='schema_version'").fetchone()
        except sqlite3.OperationalError:
            return 0
        return int(row[0]) if row else 0

    def _check_version(self) -> None:
        v = self.schema_version()
        if v != SCHEMA_VERSION:
            raise Inv22Error("INV22.VERSION.UNSUPPORTED", "store schema version not supported by this release",
                             {"store": v, "supported": SCHEMA_VERSION})

    def migrate(self) -> list[int]:
        applied = []
        cur = self.schema_version()
        if cur > SCHEMA_VERSION:
            raise Inv22Error("INV22.VERSION.UNSUPPORTED", "store is newer than this release; refusing to start",
                             {"store": cur, "supported": SCHEMA_VERSION})
        for v in range(cur + 1, SCHEMA_VERSION + 1):
            with self._tx() as c:           # each step atomic, so migration is resumable
                for stmt in MIGRATIONS[v]:
                    c.execute(stmt)
                c.execute("INSERT OR REPLACE INTO kv VALUES('schema_version', ?)", (str(v),))
            applied.append(v)
        return applied

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        if self.read_only:
            raise Inv22Error("INV22.AUTH.FORBIDDEN", "store opened read-only")
        try:
            self.db.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as e:
            raise Inv22Error("INV22.STORAGE.CONFLICT", "store busy") from e
        try:
            yield self.db
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    # -- audit chain (MC-41) ---------------------------------------------
    def _audit(self, c, actor: str, action: str, obj: str, before: Any, after: Any, reason: str) -> int:
        row = c.execute("SELECT seq, hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        seq, prev = (row[0] + 1, row[1]) if row else (1, _GENESIS)
        ts = self.clock()
        body = {"seq": seq, "ts": ts, "actor": actor, "action": action, "object": obj,
                "before": before, "after": after, "reason": reason, "prev_hash": prev}
        h = _h(canonical.dumps(body))
        c.execute("INSERT INTO audit VALUES(?,?,?,?,?,?,?,?,?,?)",
                  (seq, ts, actor, action, obj, json.dumps(before), json.dumps(after), reason, prev, h))
        return seq

    def audit_events(self, limit: int = 1000) -> list[dict]:
        rows = self.db.execute("SELECT seq,ts,actor,action,object,before,after,reason,prev_hash,hash FROM audit ORDER BY seq LIMIT ?", (limit,))
        return [{"seq": r[0], "ts": r[1], "actor": r[2], "action": r[3], "object": r[4],
                 "before": json.loads(r[5]), "after": json.loads(r[6]), "reason": r[7], "prev_hash": r[8], "hash": r[9]} for r in rows]

    def verify_audit_chain(self) -> dict:
        prev, n = _GENESIS, 0
        for ev in self.audit_events(limit=10**9):
            body = {k: ev[k] for k in ("seq", "ts", "actor", "action", "object", "before", "after", "reason", "prev_hash")}
            if ev["prev_hash"] != prev or _h(canonical.dumps(body)) != ev["hash"] or ev["seq"] != n + 1:
                return {"ok": False, "broken_at": ev["seq"], "events": n}
            prev, n = ev["hash"], n + 1
        return {"ok": True, "events": n, "head": prev}

    # -- certifications (MC-09) ------------------------------------------
    def issue_cert(self, envelope: dict, *, actor: str, reason: str = "issued") -> None:
        p = envelope["payload"]
        raw = canonical.dumps(envelope)
        with self._tx() as c:
            if c.execute("SELECT 1 FROM certs WHERE cert_id=?", (p["cert_id"],)).fetchone():
                raise Inv22Error("INV22.STORAGE.CONFLICT", "certificate id already exists (no resurrection)",
                                 {"cert_id": p["cert_id"]})
            c.execute("INSERT INTO certs VALUES(?,?,?,?,?,?,?,?,?,1)",
                      (p["cert_id"], p["component"]["id"], p["branch"], p["issuer"], p["not_after"], "valid",
                       None, raw, _h(raw)))
            c.executemany("INSERT INTO cert_artifacts VALUES(?,?)", [(p["cert_id"], d) for d in p["artifact_digests"]])
            self._audit(c, actor, "cert.issue", p["cert_id"], None, "valid", reason)

    def _transition(self, cert_id: str, target: str, *, actor: str, reason: str, expected_rev: int | None,
                    successor: str | None = None) -> None:
        with self._tx() as c:
            row = c.execute("SELECT status, rev FROM certs WHERE cert_id=?", (cert_id,)).fetchone()
            if row is None:
                raise Inv22Error("INV22.VALIDATION.INVALID_INPUT", "unknown certificate", {"cert_id": cert_id})
            status, rev = row
            if expected_rev is not None and expected_rev != rev:
                raise Inv22Error("INV22.STORAGE.CONFLICT", "stale revision", {"expected": expected_rev, "actual": rev})
            lifecycle.check("cert", status, target)
            if successor is not None:
                srow = c.execute("SELECT status FROM certs WHERE cert_id=?", (successor,)).fetchone()
                if srow is None or srow[0] != "valid":
                    raise Inv22Error("INV22.VALIDATION.INVALID_INPUT", "successor must exist and be valid")
            c.execute("UPDATE certs SET status=?, successor=COALESCE(?, successor), rev=rev+1 WHERE cert_id=?",
                      (target, successor, cert_id))
            self._audit(c, actor, f"cert.{target}", cert_id, status, target, reason)

    def revoke(self, cert_id, *, actor, reason, expected_rev=None):
        self._transition(cert_id, "revoked", actor=actor, reason=reason, expected_rev=expected_rev)

    def suspend(self, cert_id, *, actor, reason, expected_rev=None):
        self._transition(cert_id, "suspended", actor=actor, reason=reason, expected_rev=expected_rev)

    def reinstate(self, cert_id, *, actor, reason, expected_rev=None):
        self._transition(cert_id, "valid", actor=actor, reason=reason, expected_rev=expected_rev)

    def supersede(self, cert_id, successor, *, actor, reason, expected_rev=None):
        self._transition(cert_id, "superseded", actor=actor, reason=reason, expected_rev=expected_rev, successor=successor)

    def expire_due(self, *, actor: str = "system:expiry") -> list[str]:
        now = self.clock()
        due = [r[0] for r in self.db.execute("SELECT cert_id FROM certs WHERE status IN ('valid','suspended') AND not_after<=?", (now,))]
        for cid in due:
            self._transition(cid, "expired", actor=actor, reason="validity window ended", expected_rev=None)
        return due

    def get_cert(self, cert_id: str) -> dict:
        row = self.db.execute("SELECT envelope, envelope_digest, status, rev, successor FROM certs WHERE cert_id=?", (cert_id,)).fetchone()
        if row is None:
            raise Inv22Error("INV22.VALIDATION.INVALID_INPUT", "unknown certificate", {"cert_id": cert_id})
        raw, dig, status, rev, succ = row
        raw = _blob(raw)
        if raw is None or _h(raw) != dig:
            raise Inv22Error("INV22.INTEGRITY.CORRUPT", "stored certificate bytes fail integrity check", {"cert_id": cert_id})
        env = canonical.loads(raw)
        if env["payload"]["cert_id"] != cert_id:
            raise Inv22Error("INV22.INTEGRITY.CORRUPT", "certificate index does not match signed payload")
        return {"envelope": env, "status": status, "rev": rev, "successor": succ}

    def certs_for_artifact(self, artifact_digest: str) -> list[str]:
        return [r[0] for r in self.db.execute(
            "SELECT c.cert_id FROM certs c JOIN cert_artifacts a USING(cert_id) WHERE a.artifact_digest=? ORDER BY c.cert_id",
            (artifact_digest,))]

    def revocation_snapshot(self):
        from .cert import RevocationView
        rows = self.db.execute("SELECT cert_id, status FROM certs").fetchall()
        seq = self.db.execute("SELECT COALESCE(MAX(seq),0) FROM audit").fetchone()[0]
        pick = lambda s: frozenset(r[0] for r in rows if r[1] == s)  # noqa: E731
        return RevocationView(sequence=seq, fetched_at=self.clock(), revoked=pick("revoked"),
                              superseded=pick("superseded"), suspended=pick("suspended") | pick("expired"))

    # -- drift history (MC-43) -------------------------------------------
    def record_drift(self, release: str, matrix, *, actor: str) -> dict:
        per = {e.interface: e.classification for e in matrix.entries}
        divergent = sum(1 for v in per.values() if v == "divergent")
        with self._tx() as c:
            if c.execute("SELECT 1 FROM drift WHERE release=?", (release,)).fetchone():
                raise Inv22Error("INV22.STORAGE.CONFLICT", "release already recorded; history is immutable", {"release": release})
            seq = c.execute("SELECT COALESCE(MAX(seq),0)+1 FROM drift").fetchone()[0]
            c.execute("INSERT INTO drift VALUES(?,?,?,?,?,?,?)",
                      (release, seq, matrix.digest, divergent, json.dumps(per, sort_keys=True), self.clock(), actor))
            self._audit(c, actor, "drift.record", release, None, divergent, "release drift snapshot")
        return {"release": release, "seq": seq, "divergent": divergent}

    def drift_history(self) -> list[dict]:
        return [{"release": r[0], "seq": r[1], "matrix_digest": r[2], "divergent": r[3], "per_interface": json.loads(r[4])}
                for r in self.db.execute("SELECT release, seq, matrix_digest, divergent, per_interface FROM drift ORDER BY seq")]

    # -- config revisions (MC-21, MC-48) ---------------------------------
    def active_config(self) -> tuple[int, dict] | None:
        row = self.db.execute("SELECT rev, doc FROM config_revisions WHERE state='active'").fetchone()
        return (row[0], json.loads(row[1])) if row else None

    def activate_config(self, doc: dict, *, actor: str, expected_active: int | None, reason: str,
                        validator: Callable[[dict], None], fault: Callable[[str], None] | None = None) -> int:
        """Stage → validate → commit atomically.  Readers see old or new, never mixed."""
        fault = fault or (lambda _stage: None)
        validator(doc)                         # full validation before any write
        fault("validated")
        digest = canonical.digest(doc)
        with self._tx() as c:
            cur = c.execute("SELECT rev FROM config_revisions WHERE state='active'").fetchone()
            cur_rev = cur[0] if cur else None
            if cur_rev != expected_active:
                raise Inv22Error("INV22.STORAGE.CONFLICT", "stale writer: active revision changed",
                                 {"expected": expected_active, "actual": cur_rev})
            rev = c.execute("SELECT COALESCE(MAX(rev),0)+1 FROM config_revisions").fetchone()[0]
            c.execute("INSERT INTO config_revisions VALUES(?,?,?,?,?,?,?)",
                      (rev, digest, json.dumps(doc, sort_keys=True), actor, self.clock(), "prepared", cur_rev))
            fault("prepared")
            if cur_rev is not None:
                c.execute("UPDATE config_revisions SET state='superseded' WHERE rev=?", (cur_rev,))
            c.execute("UPDATE config_revisions SET state='active' WHERE rev=?", (rev,))
            fault("committing")
            self._audit(c, actor, "config.activate", f"config:{rev}", cur_rev, rev, reason)
        return rev

    def rollback_config(self, *, actor: str, reason: str, validator: Callable[[dict], None]) -> int:
        with self._tx() as c:
            row = c.execute("SELECT rev, prev_active FROM config_revisions WHERE state='active'").fetchone()
            if row is None or row[1] is None:
                raise Inv22Error("INV22.STATE.ILLEGAL_TRANSITION", "no previous known-good revision")
            cur, prev = row
            doc = json.loads(c.execute("SELECT doc FROM config_revisions WHERE rev=?", (prev,)).fetchone()[0])
            validator(doc)                    # rollback target must still pass current validation
            c.execute("UPDATE config_revisions SET state='superseded' WHERE rev=?", (cur,))
            c.execute("UPDATE config_revisions SET state='active', prev_active=? WHERE rev=?", (cur, prev))
            self._audit(c, actor, "config.rollback", f"config:{prev}", cur, prev, reason)
        return prev

    # -- site branch (MC-23) ---------------------------------------------
    def site_state(self, site: str) -> dict | None:
        r = self.db.execute("SELECT branch, baseline, epoch, actor, ts, frozen FROM site WHERE site=?", (site,)).fetchone()
        return None if r is None else {"site": site, "branch": r[0], "baseline": r[1], "epoch": r[2],
                                       "actor": r[3], "ts": r[4], "frozen": bool(r[5])}

    def set_site_branch(self, site: str, branch: str, baseline: str, *, actor: str, fence: int, reason: str) -> int:
        """Compare-and-swap on the epoch fencing token; returns the new epoch."""
        with self._tx() as c:
            r = c.execute("SELECT branch, epoch, frozen FROM site WHERE site=?", (site,)).fetchone()
            cur_epoch = r[1] if r else 0
            if fence != cur_epoch:
                raise Inv22Error("INV22.STATE.STALE_FENCE", "stale controller fencing token",
                                 {"expected": cur_epoch, "presented": fence})
            if r and r[2]:
                raise Inv22Error("INV22.SITE.FROZEN", "site is frozen")
            new = cur_epoch + 1
            c.execute("INSERT OR REPLACE INTO site VALUES(?,?,?,?,?,?,0)", (site, branch, baseline, new, actor, self.clock()))
            self._audit(c, actor, "site.branch", site, r[0] if r else None, branch, reason)
        return new

    def set_frozen(self, site: str, frozen: bool, *, actor: str, reason: str) -> None:
        with self._tx() as c:
            if c.execute("UPDATE site SET frozen=? WHERE site=?", (int(frozen), site)).rowcount != 1:
                raise Inv22Error("INV22.VALIDATION.INVALID_INPUT", "unknown site")
            self._audit(c, actor, "site.freeze" if frozen else "site.unfreeze", site, None, frozen, reason)

    # -- generic audited note (used by waivers/policy decisions) ----------
    def record_event(self, *, actor: str, action: str, obj: str, after: Any, reason: str) -> int:
        with self._tx() as c:
            return self._audit(c, actor, action, obj, None, after, reason)

    # -- backup / restore / integrity (MC-60) -----------------------------
    def integrity_check(self) -> dict:
        ok = self.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        bad = []
        for cid, raw, dig in self.db.execute("SELECT cert_id, envelope, envelope_digest FROM certs"):
            b = _blob(raw)
            if b is None or _h(b) != dig:
                bad.append(cid)
        chain = self.verify_audit_chain()
        return {"sqlite_ok": ok, "corrupt_certs": bad, "audit_chain": chain,
                "ok": ok and not bad and chain["ok"]}

    def backup(self, dest_path: str) -> dict:
        dst = sqlite3.connect(dest_path)
        try:
            self.db.backup(dst)
        finally:
            dst.close()
        restored = Store(dest_path, read_only=True)
        report = restored.integrity_check()
        restored.close()
        if not report["ok"]:
            raise Inv22Error("INV22.INTEGRITY.CORRUPT", "backup failed verification")
        return report

    def close(self) -> None:
        self.db.close()
