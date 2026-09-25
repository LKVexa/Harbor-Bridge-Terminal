"""Transactional INV-25 catalogue control plane (reference implementation).

Everything a control-plane consumer needs to operate the catalogue safely:
authenticated + authorized mutation, proposal/approval/activation separation,
immutable candidates, compare-and-swap activation (no lost updates, no partial
state), PK_DEVICE_CONFIG_ACTIVATION/1 records, append-only history, rollback to
a prior known-good digest, emergency disable with break-glass, hash-chained
audit, rate limiting, health/readiness and metrics.

Concurrency model (docs/concurrency.md): one ``threading.RLock`` serializes
all writes; readers take an immutable snapshot reference, so they always see a
complete old or new state.  Cross-process sharing requires an external store
implementing the same CAS contract and is not certified here.
"""
from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable

from .audit import AuditLog, AuditUnavailable, utcnow
from .authz import Decision, Principal, Unauthenticated, Unauthorized, Verifier, authorize
from .errors import Inv25Error, to_error
from .model import (DeviceCatalogue, DeviceRejected, DeviceSpec, canonical_json, catalogue_from_export)
from .compat import SUPPORTED_SCHEMAS

ACTIVATION_SCHEMA = "PK_DEVICE_CONFIG_ACTIVATION/1"


class ConcurrentModification(Inv25Error):
    code = "INV25_CONCURRENT_MODIFICATION"


class RateLimited(Inv25Error):
    code = "INV25_RATE_LIMITED"


class DeviceDisabled(Inv25Error):
    code = "INV25_DEVICE_DISABLED"


class DependencyUnavailable(Inv25Error):
    code = "INV25_DEPENDENCY_UNAVAILABLE"


@dataclass(frozen=True)
class Snapshot:
    digest: str
    document: MappingProxyType  # read-only PK_DEVICE_CATALOGUE/1 export

    def catalogue(self) -> DeviceCatalogue:
        return catalogue_from_export(json.loads(canonical_json(dict(self.document))))


def _freeze(doc: dict[str, Any]) -> MappingProxyType:
    return MappingProxyType(json.loads(canonical_json(doc)))


class _Bucket:
    def __init__(self, rate: float, burst: int, clock: Callable[[], float]) -> None:
        self.rate, self.burst, self.clock = rate, burst, clock
        self.tokens: dict[str, tuple[float, float]] = {}

    def take(self, who: str) -> None:
        now = self.clock()
        level, last = self.tokens.get(who, (float(self.burst), now))
        level = min(self.burst, level + (now - last) * self.rate)
        if level < 1:
            raise RateLimited("mutation rate limit exceeded")
        self.tokens[who] = (level - 1, now)


class CatalogueStore:
    MAX_PENDING = 32

    def __init__(self, environment: str, verifier: Verifier, *, audit: AuditLog | None = None,
                 state_path: str | None = None, source_revision: str = "unknown",
                 mutation_rate: float = 5.0, mutation_burst: int = 20,
                 dependency_probe: Callable[[], dict[str, bool]] | None = None,
                 fault: Callable[[str], None] | None = None) -> None:
        empty = DeviceCatalogue(environment)
        self.environment = empty.environment
        self.verifier = verifier
        self.audit = audit or AuditLog()
        self.state_path = state_path
        self.source_revision = source_revision
        self._lock = threading.RLock()
        self._active = Snapshot(empty.digest(), _freeze(empty.export()))
        self._history: list[dict[str, Any]] = []
        self._known_good: list[str] = [self._active.digest]
        self._docs: dict[str, dict[str, Any]] = {self._active.digest: empty.export()}
        self._pending: dict[str, dict[str, Any]] = {}
        self._disabled: dict[str, dict[str, Any]] = {}
        self._bucket = _Bucket(mutation_rate, mutation_burst, verifier.clock)
        self._probe = dependency_probe or (lambda: {})
        self._fault = fault or (lambda point: None)
        self.metrics: dict[str, float] = {k: 0 for k in (
            "registration_accepted", "registration_rejected", "replacement_accepted", "replacement_rejected",
            "surface_growth", "authn_denied", "authz_denied", "artifact_verification_failed",
            "activations", "activation_failures", "rollbacks", "emergency_disables", "last_activation_seconds")}
        self.errors_by_code: dict[str, int] = {}
        if state_path and os.path.exists(state_path):
            self._load()

    # ------------------------------------------------------------------ reads
    @property
    def active(self) -> Snapshot:
        return self._active  # single reference read: always a complete snapshot

    def permits(self, device: str) -> bool:
        snap = self._active
        return (any(d["name"] == device for d in snap.document["devices"])
                and device not in self._disabled)

    def history(self) -> list[dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._history)

    # --------------------------------------------------------------- helpers
    def _principal(self, token: str | None, capability: str, corr: str) -> tuple[Principal, Decision]:
        try:
            p = self.verifier.verify(token)
        except Inv25Error as exc:
            self.metrics["authn_denied"] += 1
            self._count(exc)
            self.audit.emit("authn.failure", actor="unknown", result="denied", environment=self.environment,
                            correlation_id=corr, error_code=exc.code)
            raise
        try:
            d = authorize(p, capability, self.environment)
        except Inv25Error as exc:
            self.metrics["authz_denied"] += 1
            self._count(exc)
            self.audit.emit("authz.denied", actor=p.subject, result="denied", environment=self.environment,
                            correlation_id=corr, capability=capability, error_code=exc.code)
            raise
        if capability != "catalogue.read":
            self._bucket.take(p.subject)
        return p, d

    def _count(self, exc: BaseException) -> None:
        code = getattr(exc, "code", "INV25_INTERNAL")
        self.errors_by_code[code] = self.errors_by_code.get(code, 0) + 1

    # ------------------------------------------------------------ proposals
    def propose(self, token: str, op: str, spec: DeviceSpec, *, correlation_id: str = "") -> dict[str, Any]:
        """Stage an immutable candidate. Proposal never changes the active catalogue."""
        corr = correlation_id or str(uuid.uuid4())
        cap = {"register": "catalogue.register", "replace": "catalogue.replace"}.get(op)
        if cap is None:
            raise Unauthorized("unknown operation")
        p, _ = self._principal(token, cap, corr)
        with self._lock:
            if len(self._pending) >= self.MAX_PENDING:
                from .model import LimitExceeded
                raise LimitExceeded("too many pending candidates", limit=self.MAX_PENDING)
            base = self._active
            cat = base.catalogue()
            diff = None
            try:
                if op == "register":
                    cat.register(spec)
                else:
                    diff = cat.replace(spec)
                    if diff["widened"] and "catalogue.widen" not in p.capabilities:
                        raise Unauthorized("widening a guest-visible surface requires catalogue.widen")
            except Inv25Error as exc:
                self.metrics[f"{'registration' if op == 'register' else 'replacement'}_rejected"] += 1
                self._count(exc)
                forbidden = exc.code.startswith("INV25_FORBIDDEN")
                self.audit.emit("forbidden_class.attempt" if forbidden else
                                ("registration.rejected" if op == "register" else "replacement.rejected"),
                                actor=p.subject, result="rejected", environment=self.environment,
                                device=str(getattr(spec, "name", ""))[:64], correlation_id=corr,
                                error_code=exc.code)
                raise
            doc = cat.export()
            cid = "cand-" + uuid.uuid4().hex
            self._pending[cid] = {"id": cid, "op": op, "proposer": p.subject, "base": base.digest,
                                  "digest": cat.digest(), "document": doc, "diff": diff,
                                  "device": spec.name, "approvals": [], "correlation_id": corr}
            return {"candidate": cid, "digest": cat.digest(), "base": base.digest, "diff": diff}

    def approve(self, token: str, candidate: str, *, correlation_id: str = "") -> dict[str, Any]:
        p, d = self._principal(token, "catalogue.approve", correlation_id)
        with self._lock:
            c = self._pending.get(candidate)
            if c is None:
                raise DeviceRejected("unknown candidate", code="INV25_REPLACE_TARGET_ABSENT")
            if p.subject == c["proposer"]:
                raise Unauthorized("proposer may not approve their own candidate (separation of duties)")
            if p.subject not in c["approvals"]:
                c["approvals"].append(p.subject)
            return {"candidate": candidate, "approvals": list(c["approvals"]), "policy": d.policy_revision}

    def activate(self, token: str, candidate: str, *, expected_digest: str,
                 correlation_id: str = "", build_id: str = "") -> dict[str, Any]:
        """Compare-and-swap activation. Idempotent for an already-activated candidate."""
        p, d = self._principal(token, "catalogue.activate", correlation_id)
        t0 = time.perf_counter()
        with self._lock:
            done = next((r for r in self._history if r.get("candidate") == candidate), None)
            if done is not None:
                return copy.deepcopy(done)  # idempotent replay
            c = self._pending.get(candidate)
            if c is None:
                raise DeviceRejected("unknown candidate", code="INV25_REPLACE_TARGET_ABSENT")
            if not c["approvals"]:
                raise Unauthorized("candidate has no independent approval")
            if self._active.digest != expected_digest or c["base"] != expected_digest:
                self.metrics["activation_failures"] += 1
                raise ConcurrentModification("active catalogue changed since the candidate was staged",
                                             expected=expected_digest[:71])
            deps = self._probe()
            if deps and not all(deps.values()):
                self.metrics["activation_failures"] += 1
                raise DependencyUnavailable("required dependency unavailable; activation refused")
            # re-validate the complete candidate before commit
            cat = catalogue_from_export(c["document"])
            if cat.digest() != c["digest"]:
                raise DeviceRejected("candidate digest mismatch", code="INV25_ARTIFACT_VERIFICATION_FAILED")
            record = self._record(p, d, c, kind="activate", build_id=build_id)
            return self._commit(record, c["document"], c, t0)

    def rollback(self, token: str, target_digest: str, *, expected_digest: str, reason: str,
                 correlation_id: str = "") -> dict[str, Any]:
        p, d = self._principal(token, "catalogue.rollback", correlation_id)
        t0 = time.perf_counter()
        with self._lock:
            if self._active.digest != expected_digest:
                raise ConcurrentModification("active catalogue changed")
            if target_digest not in self._known_good or target_digest not in self._docs:
                raise DeviceRejected("rollback target is not a recorded known-good state",
                                     code="INV25_REPLACE_TARGET_ABSENT")
            doc = self._docs[target_digest]
            catalogue_from_export(doc)  # compatibility / validity check before activation
            c = {"id": None, "op": "rollback", "proposer": p.subject, "approvals": [p.subject],
                 "digest": target_digest, "device": "", "diff": None, "correlation_id": correlation_id,
                 "reason": reason}
            record = self._record(p, d, c, kind="rollback")
            self.metrics["rollbacks"] += 1
            return self._commit(record, doc, c, t0)

    def emergency_disable(self, token: str, device: str, *, reason: str, incident_id: str,
                          expires: str, correlation_id: str = "") -> dict[str, Any]:
        """Break-glass: stop a device being attached. Never widens authority, never deletes evidence."""
        p, _ = self._principal(token, "catalogue.emergency_disable", correlation_id)
        with self._lock:
            entry = {"device": device, "actor": p.subject, "reason": reason[:256],
                     "incident_id": incident_id[:64], "expires": expires, "at": utcnow()}
            self.audit.emit("emergency.disable", actor=p.subject, result="applied", environment=self.environment,
                            device=device, correlation_id=correlation_id, incident_id=incident_id[:64],
                            reason=reason[:256], expires=expires)
            self._disabled[device] = entry
            self.metrics["emergency_disables"] += 1
            self._persist()
            return dict(entry)

    def restore_device(self, token: str, device: str, *, correlation_id: str = "") -> None:
        p, _ = self._principal(token, "catalogue.activate", correlation_id)
        with self._lock:
            if device in self._disabled:
                self.audit.emit("emergency.restore", actor=p.subject, result="applied",
                                environment=self.environment, device=device, correlation_id=correlation_id)
                del self._disabled[device]
                self._persist()

    def verify_artifact(self, data: bytes, attestation: Any, trust: Any, *, artifact_type: str, name: str,
                        version: str, correlation_id: str = "") -> dict[str, Any]:
        """Verify an externally supplied artifact before it is parsed; audit both outcomes."""
        try:
            res = trust.verify(data, attestation, artifact_type=artifact_type, name=name, version=version)
        except Inv25Error as exc:
            self.metrics["artifact_verification_failed"] += 1
            self._count(exc)
            self.audit.emit("artifact.verification_failed", actor="system", result="rejected",
                            environment=self.environment, correlation_id=correlation_id,
                            artifact_type=artifact_type, artifact_name=name[:64], error_code=exc.code)
            raise
        self.audit.emit("artifact.verified", actor="system", result="verified", environment=self.environment,
                        correlation_id=correlation_id, artifact_type=artifact_type, artifact_name=name[:64],
                        artifact_digest=res["digest"])
        return res

    # ---------------------------------------------------------------- commit
    def _record(self, p: Principal, d: Decision, c: dict[str, Any], *, kind: str, build_id: str = "") -> dict:
        return {"schema": ACTIVATION_SCHEMA, "activation_id": str(uuid.uuid4()), "kind": kind,
                "candidate": c["id"], "digest": c["digest"], "catalogue_schema": "PK_DEVICE_CATALOGUE/1",
                "environment": self.environment, "proposer": c["proposer"], "approvers": list(c["approvals"]),
                "activated_by": p.subject, "timestamp": utcnow(), "previous_digest": self._active.digest,
                "rollback_target": self._active.digest, "source_revision": self.source_revision,
                "build_id": build_id, "policy_decision": {"capability": d.capability, "reason": d.reason,
                                                          "policy_revision": d.policy_revision},
                "surface_diff": c.get("diff"), "correlation_id": c.get("correlation_id", ""),
                "reason": c.get("reason", "")}

    def _commit(self, record: dict, doc: dict, c: dict, t0: float) -> dict:
        # 1. audit first: if the sink is down the mutation is refused and nothing changes.
        try:
            self._fault("before_audit")
            ev = "config.rolled_back" if record["kind"] == "rollback" else "config.activated"
            self.audit.emit(ev, actor=record["activated_by"], result="committed", environment=self.environment,
                            device=c.get("device", ""), correlation_id=record["correlation_id"],
                            old_digest=record["previous_digest"], new_digest=record["digest"],
                            activation_id=record["activation_id"], surface_diff=record["surface_diff"])
            if c.get("diff"):
                self.audit.emit("surface.widened" if c["diff"]["widened"] else "surface.reduced",
                                actor=record["activated_by"], result="committed", environment=self.environment,
                                device=c["device"], correlation_id=record["correlation_id"],
                                surface_diff=c["diff"])
            self._fault("before_persist")
            new_hist = self._history + [record]
            self._persist(new_hist, record["digest"], doc)   # COMMIT POINT: atomic durable replace
        except Exception as exc:
            self.metrics["activation_failures"] += 1
            self._count(exc)
            if not isinstance(exc, AuditUnavailable):
                try:  # compensate: the chain must show the attempted commit did not take effect
                    self.audit.emit("config.activation_failed", actor=record["activated_by"], result="aborted",
                                    environment=self.environment, correlation_id=record["correlation_id"],
                                    activation_id=record["activation_id"], error_code=getattr(exc, "code",
                                                                                              "INV25_INTERNAL"))
                except Exception:
                    pass
            raise
        # After the commit point nothing below can fail (pure in-memory assignment).
        # 2. single reference swap: readers see old or new, never partial
        self._docs[record["digest"]] = copy.deepcopy(doc)
        self._active = Snapshot(record["digest"], _freeze(doc))
        self._history = new_hist
        if record["digest"] not in self._known_good:
            self._known_good.append(record["digest"])
        if c.get("id"):
            self._pending.pop(c["id"], None)
            op = c["op"]
            self.metrics["registration_accepted" if op == "register" else "replacement_accepted"] += 1
            if c.get("diff") and c["diff"]["widened"]:
                self.metrics["surface_growth"] += 1
        self.metrics["activations"] += 1
        self.metrics["last_activation_seconds"] = time.perf_counter() - t0
        return copy.deepcopy(record)

    # ----------------------------------------------------------- persistence
    def _persist(self, history=None, digest=None, doc=None) -> None:
        if not self.state_path:
            return
        history = self._history if history is None else history
        digest = self._active.digest if digest is None else digest
        doc = dict(self._active.document) if doc is None else doc
        docs = dict(self._docs)
        docs[digest] = doc
        state = {"schema": "INV25_STORE_STATE/1", "active": digest, "history": history,
                 "known_good": sorted(set(self._known_good) | {digest}), "docs": docs,
                 "disabled": self._disabled}
        d = os.path.dirname(os.path.abspath(self.state_path))
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".inv25-state-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(state, sort_keys=True, default=_jsonable))
                fh.flush()
                os.fsync(fh.fileno())
            self._fault("before_rename")
            os.replace(tmp, self.state_path)  # atomic on POSIX and Windows
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def _load(self) -> None:
        with open(self.state_path, encoding="utf-8") as fh:
            st = json.load(fh)
        if st.get("schema") != "INV25_STORE_STATE/1":
            raise DependencyUnavailable("unrecognised state file")
        self._docs = {k: v for k, v in st["docs"].items()}
        for dg, doc in self._docs.items():
            if catalogue_from_export(doc).digest() != dg:
                raise DeviceRejected("persisted catalogue digest mismatch",
                                     code="INV25_ARTIFACT_VERIFICATION_FAILED")
        self._active = Snapshot(st["active"], _freeze(self._docs[st["active"]]))
        self._history = st["history"]
        self._known_good = st["known_good"]
        self._disabled = st.get("disabled", {})

    # --------------------------------------------------------- observability
    def health(self) -> dict[str, Any]:
        from . import __version__
        try:
            deps = self._probe()
            probe_ok = True
        except Exception:
            deps, probe_ok = {}, False
        audit_ok = not self.audit.fail
        ready = probe_ok and audit_ok and all(deps.values()) if deps else probe_ok and audit_ok
        return {"component": "INV-25", "version": __version__, "live": True, "ready": bool(ready),
                "environment": self.environment, "active_digest": self._active.digest,
                "active_devices": len(self._active.document["devices"]),
                "disabled_devices": sorted(self._disabled), "dependencies": deps,
                "audit_head": self.audit.head, "audit_sink_ok": audit_ok,
                "schemas": {k: v[0] for k, v in SUPPORTED_SCHEMAS.items()},
                "pending_candidates": len(self._pending)}

    def signals(self) -> dict[str, Any]:
        doc = self._active.document
        return {"catalogue_size": len(doc["devices"]),
                "surface_registers": sum(len(d["registers"]) for d in doc["devices"]),
                "unreviewed_entries": sum(1 for d in doc["devices"] if not d["reviewer"].strip()),
                **self.metrics, "errors_by_code": dict(self.errors_by_code)}

    def explain(self, activation_id: str) -> dict[str, Any]:
        """Operator view linking a decision to its inputs, policy, digests and audit evidence."""
        rec = next((r for r in self._history if r["activation_id"] == activation_id), None)
        if rec is None:
            raise DeviceRejected("unknown activation", code="INV25_REPLACE_TARGET_ABSENT")
        evs = [e["event_id"] for e in self.audit.events if e.get("activation_id") == activation_id]
        return {"activation": rec, "audit_events": evs,
                "why": f"{rec['kind']} by {rec['activated_by']} approved by {', '.join(rec['approvers'])}; "
                       f"{rec['policy_decision']['reason']} under {rec['policy_decision']['policy_revision']}; "
                       f"{rec['previous_digest'][:19]} -> {rec['digest'][:19]}"}

    def serialize_error(self, exc: BaseException, operation: str, correlation_id: str = "") -> dict[str, Any]:
        return to_error(exc, operation=operation, correlation_id=correlation_id, environment=self.environment)


def _jsonable(o: Any) -> Any:
    if isinstance(o, MappingProxyType):
        return dict(o)
    raise TypeError(type(o).__name__)
