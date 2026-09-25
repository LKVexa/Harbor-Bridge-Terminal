"""The INV-07 production reconciliation controller.

``Controller.reconcile(ref)`` executes, in order, with fail-closed exits:

 1. trusted time (``TimeAuthority``)                          -> refused
 2. freeze / kill switch (``FreezeRegistry``)                 -> frozen
 3. leadership + fencing epoch (``FileLease``)                -> not_leader
 4. fetch through retry + circuit breaker; offline policy     -> read_only / refused
 5. resolve approved ref -> OID; repository identity pin
 6. commit signature under trust roots (``signing``)          -> refused
 7. ref policy: fast-forward / signed revert / exception      -> refused
 8. freshness: generation + max age                            -> refused
 9. provenance (DSSE note, subject digest, builder)           -> refused
10. parse manifests with hardened parsers                     -> refused
11. tenant namespaces + residency                             -> refused
12. policy bundle                                             -> refused
13. read live; detect drift against the last committed digests
14. plan; preflight; journalled transaction with compensation -> failed / PartialApply => auto-freeze target
15. accept generation, cursor, audit, metrics, explain, PK_GITOPS_SYNC/1

Every exit writes an audit entry, an explain record, metrics, a structured
event and a schema-valid ``PK_GITOPS_SYNC/1`` document.  On start-up
``recover()`` reads back any pending (ambiguous) intent before the first
reconcile and aborts it -- the next plan is recomputed from live state, which
makes the ambiguous outcome safe either way.
"""
from __future__ import annotations

import os
import re
import secrets
import threading
import time

from . import provenance as prov
from .apply import Transaction, plan
from .errors import (GitOpsError, PartialApply, Quarantined, RepositoryUnavailable, TimeUntrusted, NotLeader,
                     CircuitOpen, Unsigned, Untrusted, Revoked, Expired, ProvenanceFailed, PolicyDenied,
                     RefNotApproved, NonFastForward, StaleRef, from_exception)
from .manifests import load_tree
from .schemas import check as schema_check
from .signing import verify_commit
from .target import obj_digest, rid_str

VERSION = "5.0.0"
REVERT_RE = re.compile(r"^PK-Revert-To: ([0-9a-f]{40}|[0-9a-f]{64})$", re.M)
TRUST_ERRORS = (Unsigned, Untrusted, Revoked, Expired, ProvenanceFailed)


class Controller:
    def __init__(self, *, repo, refpolicy, trust, target, state, audit, freezes, lease, timeauth, offline,
                 tenancy, policy, metrics, events, tracer, explain, freshness, retry, breaker,
                 manifest_path: str = "", owner: str = "inv07-gitops", require_provenance: bool = True,
                 allowed_builders: tuple[str, ...] = (), prune: bool = False, limits: dict | None = None,
                 residency=None, target_name: str = "default", provenance_verifier=None) -> None:
        self.repo, self.refpolicy, self.trust, self.target, self.state = repo, refpolicy, trust, target, state
        self.audit, self.freezes, self.lease, self.time, self.offline = audit, freezes, lease, timeauth, offline
        self.tenancy, self.policy, self.m, self.events, self.tracer = tenancy, policy, metrics, events, tracer
        self.explain, self.fresh, self.retry, self.breaker = explain, freshness, retry, breaker
        self.path, self.owner, self.require_prov = manifest_path, owner, require_provenance
        self.builders, self.prune, self.limits = allowed_builders, prune, limits or {}
        self.residency, self.target_name, self.prov_verifier = residency, target_name, provenance_verifier
        self.last_sync: float | None = None
        self._run_lock = threading.Lock()   # one reconcile at a time per controller instance

    # -- startup ---------------------------------------------------------------
    def recover(self) -> dict:
        pend = self.state.pending_intents()
        live = self.target.list()
        for key, it in pend.items():
            self.state.abort(key, "ambiguous_readback")
            self.audit.append("recover.ambiguous_intent", {"key": key, "oid": it["oid"], "live_objects": len(live)},
                              actor=self.owner)
        return {"pending_resolved": len(pend)}

    # -- main loop body ---------------------------------------------------------
    def reconcile(self, ref: str, *, traceparent: str | None = None) -> dict:
        with self._run_lock:
            return self._reconcile_locked(ref, traceparent)

    def _reconcile_locked(self, ref: str, traceparent: str | None) -> dict:
        did = secrets.token_hex(8)
        audit_seq: list[int] = []
        rec = {"schema": "PK_GITOPS_SYNC/1", "decision_id": did, "ref": ref, "outcome": "failed", "at": 0.0,
               "actions": [], "drift": [], "error": None}
        explain = {"decision_id": did, "ref": ref, "oid": None, "signer": None, "provenance": None, "policy": None,
                   "actions": [], "drift": [], "overrides": [], "target": self.target_name,
                   "tenant": self.tenancy.tenant, "site": self.tenancy.site}
        t0 = time.perf_counter()
        with self.tracer.span("inv07.reconcile", traceparent=traceparent, ref=ref) as sp:
            rec["trace_id"] = sp["trace_id"]
            try:
                self._reconcile(ref, rec, explain, audit_seq)
            except GitOpsError as exc:
                rec["error"] = from_exception(exc, did)
                if rec["outcome"] not in ("frozen", "read_only"):
                    rec["outcome"] = "refused" if isinstance(exc, TRUST_ERRORS + (PolicyDenied, RefNotApproved,
                                                             NonFastForward, StaleRef, TimeUntrusted)) else "failed"
                if isinstance(exc, Quarantined):
                    rec["outcome"] = "frozen"
                if isinstance(exc, TRUST_ERRORS):
                    self.m.inc("inv07_unsigned_refusals_total", reason=exc.code)
                if isinstance(exc, PolicyDenied):
                    self.m.inc("inv07_policy_denials_total")
                if isinstance(exc, PartialApply):
                    self.freezes.freeze("target", self.target_name, reason="partial apply: " + exc.code,
                                        actor=self.owner)
                if isinstance(exc, (RepositoryUnavailable, CircuitOpen)):
                    self.m.inc("inv07_dependency_errors_total", dependency="git")
                sp["status"] = "error"
            rec["at"] = time.time()
            e = self.audit.append("sync." + rec["outcome"], {k: rec[k] for k in ("decision_id", "ref", "outcome")}
                                  | {"oid": rec.get("oid"), "error": (rec["error"] or {}).get("code")},
                                  actor=self.owner, correlation_id=did)
            audit_seq.append(e["seq"])
            dur = time.perf_counter() - t0
            self.m.inc("inv07_syncs_total", outcome=rec["outcome"])
            self.m.observe("inv07_reconcile_seconds", dur)
            if rec["outcome"] in ("applied", "no_change"):
                self.last_sync = rec["at"]
                self.m.set("inv07_last_sync_timestamp_seconds", rec["at"])
            self.explain.record({**explain, "outcome": rec["outcome"], "error": rec["error"], "at": rec["at"],
                                 "audit_seq": audit_seq, "trace_id": sp["trace_id"]})
            self.events.emit("PKG-SYNC-" + rec["outcome"].upper(), "error" if rec["error"] else "info",
                             "reconcile finished", cid=did, trace_id=sp["trace_id"], span_id=sp["span_id"],
                             ref=ref, outcome=rec["outcome"], error_code=(rec["error"] or {}).get("code"))
        schema_check("PK_GITOPS_SYNC_1", {k: v for k, v in rec.items() if v is not None or k == "error"})
        return rec

    def _reconcile(self, ref, rec, explain, audit_seq) -> None:
        now = self.time.now()
        try:
            self.freezes.check(tenant=self.tenancy.tenant, ref=ref, target=self.target_name)
        except Quarantined:
            rec["outcome"] = "frozen"
            self.m.set("inv07_frozen", 1)
            raise
        self.m.set("inv07_frozen", 0)
        epoch = self._leadership()
        rec["epoch"] = epoch
        with self.tracer.span("inv07.git.fetch"):
            decision = self._fetch(now)
        mutate = decision["mutate"]
        with self.tracer.span("inv07.git.resolve"):
            oid = self.repo.resolve(ref)
            commit = self.repo.read_commit(oid)
        rec["oid"], explain["oid"] = oid, oid
        previous = self.state.s["cursors"].get(ref)
        rec["previous"] = previous
        with self.tracer.span("inv07.verify.signature"):
            tv = time.perf_counter()
            verdict = verify_commit(commit, self.trust, ref=ref, now=int(now))
            explain["signer"] = verdict.as_dict()
            rec["trust_digest"] = verdict.trust_digest
        revert = self._signed_revert(commit)
        with self.tracer.span("inv07.verify.refpolicy"):
            adm = self.refpolicy.admit(repo_url=self.repo.url, ref=ref, oid=oid, previous=previous,
                                       is_ancestor=self.repo.is_ancestor, is_signed_revert=revert)
            rec["mode"] = adm["mode"]
            descends = previous is None or previous == oid or self.repo.is_ancestor(previous, oid)
            self.fresh.check(ref, oid, commit.commit_time, int(now), descends=descends)
        if self.require_prov:
            with self.tracer.span("inv07.verify.provenance"):
                explain["provenance"] = prov.verify(self.repo.note(oid), commit=oid, tree=commit.tree,
                                                    repo_url=self.repo.url, roots=self.trust, now=int(now),
                                                    allowed_builders=self.builders,
                                                    external_verifier=self.prov_verifier)
        self.m.observe("inv07_verify_seconds", time.perf_counter() - tv)
        with self.tracer.span("inv07.render"):
            files = [(p, self.repo.read_blob(b)) for _, b, p in self.repo.ls_tree(oid, self.path)]
            desired = load_tree(files, max_bytes=self.limits.get("max_manifest_bytes", 1 << 20),
                                max_depth=self.limits.get("max_depth", 32),
                                max_resources=self.limits.get("max_resources", 5000))
        self.tenancy.check_resources(desired)
        with self.tracer.span("inv07.policy"):
            pol = self.policy.enforce(desired, context={"ref": ref, "oid": oid, "signer": verdict.key_id},
                                      now=int(now))
            explain["policy"] = {"version": pol["bundle_version"], "digest": pol["bundle_digest"],
                                 "waived": pol["waived"]}
            rec["policy_digest"] = pol["bundle_digest"]
        with self.tracer.span("inv07.live.read"):
            live = self.target.list()
        drift = self._drift(live)
        rec["drift"], explain["drift"] = drift, drift
        acts = plan(desired, live, owner=self.owner, prune=self.prune, revision=oid)
        rec["actions"] = [{"op": a["op"], "rid": rid_str(tuple(a["rid"]))} for a in acts]
        explain["actions"] = rec["actions"]
        if not mutate:
            rec["outcome"] = "read_only"
            if drift:
                self._drift_report(ref, drift, action="reported_only", oid=oid)
            return
        if not acts:
            rec["outcome"] = "no_change"
        else:
            with self.tracer.span("inv07.apply", actions=len(acts)):
                res = Transaction(self.target, self.state, owner=self.owner, epoch=epoch, revision=oid,
                                  ref=ref).run(acts, desired, live, at=int(now))
            rec["outcome"] = "duplicate" if res["duplicate"] else "applied"
        if drift:
            self._drift_report(ref, drift, action="reverted", oid=oid)
            self.m.inc("inv07_drift_reverts_total", len(drift))
        self.fresh.accept(ref, oid, commit.commit_time, trust_digest=verdict.trust_digest,
                          policy_digest=pol["bundle_digest"], mode=adm["mode"])
        if previous != oid:
            self.state.cursor(ref, oid)
        e = self.audit.append("sync.accepted", {"ref": ref, "oid": oid, "mode": adm["mode"], "signer": verdict.key_id,
                                                "actions": len(acts), "drift": len(drift)}, actor=self.owner)
        audit_seq.append(e["seq"])

    def _leadership(self) -> int:
        try:
            epoch = self.lease.renew() if self.lease.epoch else self.lease.acquire()
        except GitOpsError:
            self.lease.epoch = None
            epoch = self.lease.acquire()
        self.m.set("inv07_leader", 1)
        return epoch

    def _fetch(self, now: float) -> dict:
        try:
            self.breaker.call(lambda: self.retry.call(self.repo.fetch))
            self.m.set("inv07_circuit_open", 0)
            return self.offline.decide(online=True, last_fetch_ok=self.repo.last_fetch_ok, now=now)
        except (RepositoryUnavailable, CircuitOpen) as exc:
            self.m.set("inv07_circuit_open", 1 if self.breaker.state == "open" else 0)
            d = self.offline.decide(online=False, last_fetch_ok=self.repo.last_fetch_ok, now=now)
            self.events.emit("PKG-REPO-OFFLINE", "warning", d["reason"], cause=exc.code)
            if d["source"] is None:
                raise
            return d

    def _signed_revert(self, commit) -> bool:
        m = REVERT_RE.search(commit.message)
        if not m:
            return False
        target = m.group(1)
        applied = {a["oid"] for a in self.state.applied()}
        if target not in applied:
            return False
        try:
            return self.repo.read_commit(target).tree == commit.tree
        except GitOpsError:
            return False

    def _drift(self, live: dict) -> list[str]:
        last = self.state.s.get("last_live") or {}
        cur = {rid_str(r): obj_digest(v[0]) for r, v in live.items()}
        out = [r for r, d in last.items() if cur.get(r) != d]
        return sorted(out)

    def _drift_report(self, ref: str, drift: list[str], *, action: str, oid: str) -> None:
        applied = self.state.applied()
        against = applied[-1]["oid"] if applied else oid
        live = {rid_str(r) for r in self.target.list()}
        rep = {"schema": "PK_GITOPS_DRIFT/1", "ref": ref, "detected_against": against, "reconciled_to": oid,
               "resources": [{"rid": r, "change": "modified" if r in live else "deleted"} for r in drift],
               "action": action, "at": time.time()}
        schema_check("PK_GITOPS_DRIFT_1", rep)
        self.state.drift(rep)
        self.audit.append("drift." + action, {"ref": ref, "count": len(drift), "resources": drift[:50]},
                          actor=self.owner)

    def status(self) -> dict:
        reasons = []
        frozen = self.freezes.active()
        if frozen:
            reasons.append("frozen")
        if self.time.degraded_reason:
            reasons.append("time:" + self.time.degraded_reason)
        if self.breaker.state != "closed":
            reasons.append("git circuit " + self.breaker.state)
        pend = len(self.state.pending_intents())
        if pend:
            reasons.append("ambiguous intents pending")
        ls = self.lease.status()
        doc = {"schema": "PK_GITOPS_STATUS/1", "tenant": self.tenancy.tenant, "site": self.tenancy.site,
               "leader": ls["is_leader"], "epoch": ls["epoch"], "refs": dict(self.state.s["cursors"]),
               "frozen": frozen, "last_sync": self.last_sync,
               "health": "blocked" if frozen or pend else ("degraded" if reasons else "healthy"),
               "reasons": reasons, "pending_intents": pend, "version": VERSION}
        schema_check("PK_GITOPS_STATUS_1", doc)
        return doc
