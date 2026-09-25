"""Atomic configuration activation, rollback and crash recovery (MC-13; C037-C038, C092).

Atomicity scope: **one ConfigStore directory = one (tenant, environment, site)
target on one node**. Fleet-wide atomicity is explicitly out of scope; fleets
converge through staged rollout (``rollout.py``), one target at a time.

Persistence: ``journal.jsonl`` (append-only, fsync per record) is the source
of truth for transactions; ``state.json`` is a snapshot replaced atomically
(``os.replace``). Transaction phases: ``PREPARE`` -> ``COMMIT`` | ``ABORT``.

Crash recovery on open (REQ-LC-7, deterministic):

* last txn has ``PREPARE`` but no outcome -> journal ``ABORT(recovered)``; the
  active revision is unchanged;
* last txn has ``COMMIT`` but the snapshot still shows the old revision ->
  roll the snapshot *forward* to the committed revision (the commit record is
  the linearization point).

Other guarantees: compare-and-swap on ``expected_active`` (``activation.conflict``);
a candidate failing its post-commit health probe is rolled back automatically
and **quarantined**; a quarantined digest needs :meth:`reapprove` by someone
other than the original actor before it may be activated again; rollback is
idempotent and only targets revisions that were once healthy-active
(known-good); every transition is audited with ``fail_closed=True``.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Callable

from .errors import Inv64Error

STATES = ("proposed", "validated", "prepared", "active", "superseded", "rejected", "aborted",
          "rolled_back", "quarantined")
# legal lifecycle transitions (SPECIFICATION.md §5); anything else is activation.state
TRANSITIONS: dict[str, frozenset] = {
    "proposed": frozenset({"validated", "rejected"}),
    "validated": frozenset({"prepared", "rejected"}),
    "prepared": frozenset({"active", "aborted"}),
    "active": frozenset({"superseded", "rolled_back", "quarantined"}),
    "superseded": frozenset({"active"}),           # rollback target (known-good only)
    "rolled_back": frozenset({"active"}),          # operator may re-activate a known-good one
    "quarantined": frozenset({"validated"}),       # only via reapprove()
    "rejected": frozenset(),
    "aborted": frozenset({"validated"}),           # a fresh attempt re-validates
}
PHASES = ("prepare", "commit")


class SimulatedCrash(Exception):
    """Raised by fault injection to emulate process death at a phase boundary."""


class ConfigStore:
    def __init__(self, root: str | os.PathLike, *, audit=None, clock=time.time, metrics=None,
                 activation_deadline_s: float = 30.0, crash_at: str | None = None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._journal = self.root / "journal.jsonl"
        self._state_path = self.root / "state.json"
        self._audit = audit
        self._clock = clock
        self._metrics = metrics
        self._deadline_s = activation_deadline_s
        self.crash_at = crash_at
        self._lock = threading.RLock()
        self.state = self._load()
        self.recovery = self._recover()

    # ------------------------------------------------------------ persistence
    def _load(self) -> dict:
        if self._state_path.exists():
            return json.loads(self._state_path.read_text(encoding="utf-8"))
        return {"format": "PK_APP_CONFIG_STATE/1", "next_rev": 1, "active": None, "previous_known_good": None,
                "pending": None, "revisions": {}, "quarantine": {}, "history": []}

    def _save(self) -> None:
        tmp = self._state_path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(self.state, fh, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self._state_path)

    def _log(self, rec: dict) -> None:
        with self._journal.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def _journal_records(self) -> list[dict]:
        if not self._journal.exists():
            return []
        out = []
        for line in self._journal.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    out.append({"phase": "torn"})  # torn final write from a crash
        return out

    def _recover(self) -> dict | None:
        txs: dict[str, dict] = {}
        order: list[str] = []
        for r in self._journal_records():
            if r.get("phase") == "torn":
                continue
            t = r["txid"]
            if t not in txs:
                order.append(t)
            txs.setdefault(t, {})[r["phase"]] = r
        if not order:
            return None
        last = order[-1]
        phases = txs[last]
        if "PREPARE" in phases and not ({"COMMIT", "ABORT"} & set(phases)):
            rev = phases["PREPARE"]["rev"]
            self._log({"txid": last, "phase": "ABORT", "rev": rev, "reason": "recovered-interrupted-prepare",
                       "ts": self._clock()})
            if rev in self.state["revisions"]:
                self.state["revisions"][rev]["state"] = "aborted"
            self.state["pending"] = None
            self._save()
            self._audit_event("activation.recover", rev, "aborted", "interrupted prepare")
            return {"txid": last, "action": "aborted", "rev": rev}
        if "COMMIT" in phases and self.state.get("active") != phases["COMMIT"]["rev"]:
            rec = phases["COMMIT"]
            if rec.get("kind") == "rollback":
                frm = rec.get("from")
                if frm in self.state["revisions"]:
                    self.state["revisions"][frm]["state"] = "rolled_back"
                self.state["revisions"][rec["rev"]]["state"] = "active"
                self.state["active"] = rec["rev"]
                self.state["pending"] = None
            else:
                self._apply_commit(rec["rev"], rec.get("from"))
            self._save()
            self._audit_event("activation.recover", rec["rev"], "active", "rolled forward committed txn")
            return {"txid": last, "action": "rolled_forward", "rev": rec["rev"]}
        return None

    # ----------------------------------------------------------------- helpers
    def _audit_event(self, op: str, rev: str | None, outcome: str, reason: str, actor: str = "inv64",
                     **detail) -> None:
        if self._audit is not None:
            info = self.state["revisions"].get(rev, {}) if rev else {}
            self._audit.append(op, actor=actor, tenant=info.get("scope", {}).get("tenant"), outcome=outcome,
                               resource=rev, reason=reason, fail_closed=True,
                               digest=info.get("digest"), **detail)

    def _transition(self, rev: str, to: str) -> None:
        cur = self.state["revisions"][rev]["state"]
        if to not in TRANSITIONS[cur]:
            raise Inv64Error("activation.state", details={"rev": rev, "from": cur, "to": to})
        self.state["revisions"][rev]["state"] = to

    def _apply_commit(self, rev: str, frm: str | None) -> None:
        if frm and frm in self.state["revisions"] and self.state["revisions"][frm]["state"] == "active":
            self.state["revisions"][frm]["state"] = "superseded"
            if self.state["revisions"][frm].get("healthy"):
                self.state["previous_known_good"] = frm
        self.state["revisions"][rev]["state"] = "active"
        self.state["active"] = rev
        self.state["pending"] = None

    def _crash(self, phase: str) -> None:
        if self.crash_at == phase:
            raise SimulatedCrash(phase)

    # ---------------------------------------------------------------- queries
    def status(self) -> dict:
        s = self.state
        failed = [r for r, v in s["revisions"].items() if v["state"] in ("rejected", "aborted", "quarantined")]
        return {"active": s["active"], "active_digest": s["revisions"].get(s["active"], {}).get("digest"),
                "previous_known_good": s["previous_known_good"], "pending": s["pending"],
                "failed": failed[-10:], "quarantined_digests": sorted(s["quarantine"]),
                "recovery": self.recovery}

    def effective(self, rev: str | None = None) -> dict | None:
        rev = rev or self.state["active"]
        return self.state["revisions"].get(rev, {}).get("effective") if rev else None

    # --------------------------------------------------------------- mutations
    def propose(self, effective: dict, *, actor: str, release: str, validator: Callable[[dict], list]) -> str:
        """Record a candidate and validate it (proposed -> validated | rejected)."""
        with self._lock:
            rev = f"rev-{self.state['next_rev']:06d}"
            self.state["next_rev"] += 1
            digest = effective["digest"]
            self.state["revisions"][rev] = {"state": "proposed", "digest": digest, "effective": effective,
                                            "scope": effective.get("scope", {}), "actor": actor,
                                            "release": release, "created": self._clock(), "healthy": False}
            problems = validator(effective["manifest"])
            if digest in self.state["quarantine"]:
                problems = list(problems) + ["quarantined"]
            if problems:
                self._transition(rev, "rejected")
                self._save()
                self._audit_event("activation.propose", rev, "rejected", "validation", actor=actor)
                if digest in self.state["quarantine"]:
                    raise Inv64Error("activation.quarantined", details={"rev": rev})
                raise Inv64Error("manifest.invalid", details={"rev": rev, "problems": len(problems)})
            self._transition(rev, "validated")
            self._save()
            self._audit_event("activation.propose", rev, "validated", "ok", actor=actor)
            return rev

    def activate(self, rev: str, *, actor: str, expected_active: str | None,
                 health_probe: Callable[[dict], bool] | None = None) -> dict:
        with self._lock:
            start = self._clock()
            if self.state["active"] != expected_active:
                raise Inv64Error("activation.conflict", details={"expected": expected_active, "actual": self.state["active"]})
            info = self.state["revisions"].get(rev)
            if info is None:
                raise Inv64Error("activation.state", details={"rev": rev, "reason": "unknown"})
            if info["digest"] in self.state["quarantine"]:
                raise Inv64Error("activation.quarantined", details={"rev": rev})
            self._transition(rev, "prepared")
            txid = str(uuid.uuid4())
            frm = self.state["active"]
            self._log({"txid": txid, "phase": "PREPARE", "rev": rev, "from": frm, "actor": actor, "ts": start})
            self.state["pending"] = rev
            self._save()
            self._crash("prepare")
            if self._clock() - start > self._deadline_s:
                self._log({"txid": txid, "phase": "ABORT", "rev": rev, "reason": "deadline", "ts": self._clock()})
                self._transition(rev, "aborted")
                self.state["pending"] = None
                self._save()
                self._audit_event("activation.commit", rev, "aborted", "deadline", actor=actor)
                raise Inv64Error("deadline.exceeded", details={"rev": rev})
            self._log({"txid": txid, "phase": "COMMIT", "kind": "activate", "rev": rev, "from": frm, "ts": self._clock()})
            self._crash("commit")
            self._apply_commit(rev, frm)
            self._save()
            self._audit_event("activation.commit", rev, "active", "committed", actor=actor, from_rev=frm, txid=txid)
            if self._metrics:
                self._metrics.inc("inv64_activation_total", result="committed")
            healthy = True if health_probe is None else bool(_safe_probe(health_probe, info["effective"]))
            if not healthy:
                self._rollback_locked(actor="inv64-auto", reason="health-probe-failed", quarantine=True)
                return {"rev": rev, "result": "rolled_back", "active": self.state["active"]}
            info["healthy"] = True
            self._save()
            return {"rev": rev, "result": "active", "active": rev, "txid": txid}

    def rollback(self, *, actor: str, reason: str, to: str | None = None) -> dict:
        with self._lock:
            return self._rollback_locked(actor=actor, reason=reason, to=to, quarantine=False)

    def _rollback_locked(self, *, actor: str, reason: str, to: str | None = None, quarantine: bool) -> dict:
        cur = self.state["active"]
        target = to or self.state["previous_known_good"]
        if target is None:
            if cur is None:
                raise Inv64Error("activation.no_known_good")
            # nothing known-good: roll back to "no configuration" is not allowed; freeze instead
            if quarantine:
                self.state["quarantine"][self.state["revisions"][cur]["digest"]] = {"rev": cur, "reason": reason}
                self._transition(cur, "quarantined")
                self.state["active"] = None
                self._save()
                self._audit_event("activation.rollback", cur, "quarantined", reason + "; no known-good", actor=actor)
            raise Inv64Error("activation.no_known_good")
        tinfo = self.state["revisions"].get(target)
        if tinfo is None or not tinfo.get("healthy") or tinfo["digest"] in self.state["quarantine"]:
            raise Inv64Error("activation.no_known_good", details={"target": target})
        if cur == target:  # idempotent
            return {"result": "noop", "active": cur}
        txid = str(uuid.uuid4())
        self._log({"txid": txid, "phase": "PREPARE", "rev": target, "from": cur, "actor": actor, "ts": self._clock(),
                   "kind": "rollback"})
        self._log({"txid": txid, "phase": "COMMIT", "kind": "rollback", "rev": target, "from": cur, "ts": self._clock()})
        if cur is not None:
            if quarantine:
                self.state["quarantine"][self.state["revisions"][cur]["digest"]] = {"rev": cur, "reason": reason}
                self._transition(cur, "quarantined")
            else:
                self._transition(cur, "rolled_back")
        self.state["revisions"][target]["state"] = "active"
        self.state["active"] = target
        # previous_known_good now points to the next-older healthy superseded revision, if any
        older = [r for r, v in sorted(self.state["revisions"].items())
                 if r < target and v.get("healthy") and v["state"] == "superseded"]
        self.state["previous_known_good"] = older[-1] if older else None
        self.state["history"].append({"rollback": txid, "from": cur, "to": target, "reason": reason, "ts": self._clock()})
        self._save()
        self._audit_event("activation.rollback", target, "active", reason, actor=actor, from_rev=cur, txid=txid)
        if self._metrics:
            self._metrics.inc("inv64_rollback_total", trigger="auto" if quarantine else "operator")
        return {"result": "rolled_back", "active": target, "from": cur}

    def reapprove(self, digest: str, *, approver: str) -> None:
        with self._lock:
            q = self.state["quarantine"].get(digest)
            if q is None:
                return
            original = self.state["revisions"][q["rev"]]["actor"]
            if approver == original:
                raise Inv64Error("authz.denied", details={"reason": "re-approval must come from a different actor"})
            del self.state["quarantine"][digest]
            self._save()
            self._audit_event("activation.reapprove", q["rev"], "released", "quarantine lifted", actor=approver)


def _safe_probe(probe, effective) -> bool:
    try:
        return probe(effective)
    except Exception:
        return False
