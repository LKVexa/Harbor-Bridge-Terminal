"""Declarative configuration: schema, loader, provenance, staged approval, atomic activation, rollback.

MC-022 (schema/loader, env/site overrides), MC-023 (provenance/history),
MC-024 (atomic activation/rollback), MC-025 (persistent RBAC store), MC-026
(registry/signer administration store).  All of RBAC, registries, signers,
provenance policy, rules, quotas and limits live in one versioned document,
``PK_ECP_CONFIG/1``, so a policy change is a single reviewed, digested,
journaled generation — there is no second path that mutates policy.

Lifecycle of a generation::

    stage(doc, author, source)          -> validated, digested, journaled "config.stage"
    approve(gen, approver)              -> journaled "config.approve" (approver != author)
    activate(gen, expected_active=...)  -> CAS on the active generation; needs N distinct
                                           approvals (dual_authorization.config_activate);
                                           journaled "config.activate", then swapped in
                                           one reference assignment under the lock
    rollback(to_gen, ...)               -> activate() of an earlier, still-valid generation

Because every step is journaled, restart replays the journal and ends on exactly
the generation that was last activated (MC-038).
"""
from __future__ import annotations

import copy
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from . import schema
from .errors import EcpError
from .rbac import Binding, Rbac
from .util import canonical_json, digest_of

DEFAULT_LIMITS = {"max_components": 256, "max_manifest_bytes": 1_000_000, "default_deadline_ms": 2000,
                  "max_inflight": 256, "audit_segment_records": 10_000, "retention_days": 400}


def merge_overrides(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge dicts; lists and scalars replace. Used for environment/site overlays."""
    out = copy.deepcopy(base)
    for k, v in overrides.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge_overrides(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_layers(*paths: Path) -> dict[str, Any]:
    """base.json [+ env.json [+ site.json]] -> one document (later layers win)."""
    doc: dict[str, Any] = {}
    for p in paths:
        doc = merge_overrides(doc, json.loads(Path(p).read_text()))
    return doc


@dataclass(frozen=True)
class Signer:
    id: str
    public_key: str
    scope: tuple[str, ...]
    revoked: bool = False
    not_after: Optional[float] = None


@dataclass(frozen=True)
class Policy:
    """Immutable, fully-validated view of one config generation."""
    generation: str
    doc: dict[str, Any]
    rbac: Rbac
    registries: tuple[tuple[str, tuple[str, ...]], ...]
    signers: dict[str, Signer]
    limits: dict[str, int]

    @property
    def environment(self) -> str:
        return self.doc["environment"]

    def registry_allowed(self, host: str, target: tuple[str, ...]) -> bool:
        return any(h == host and target[: len(s)] == s for h, s in self.registries)

    def signer_for(self, signer_id: str, target: tuple[str, ...], t: float) -> Optional[Signer]:
        s = self.signers.get(signer_id)
        if s is None or s.revoked or (s.not_after is not None and t > s.not_after):
            return None
        return s if target[: len(s.scope)] == s.scope else None


def build_policy(doc: dict[str, Any]) -> Policy:
    schema.validate(doc, "PK_ECP_CONFIG_1")
    org = doc["org"]
    from .rbac import parse_scope
    for part in ("bindings", "registries", "signers"):
        for item in doc[part]:
            sc = parse_scope(item["scope"])
            if sc[0] != org:
                raise EcpError("ECP_CONFIG_INVALID", f"{part} scope outside organisation", field=part, scope=item["scope"])
    ids = [s["id"] for s in doc["signers"]]
    if len(ids) != len(set(ids)):
        raise EcpError("ECP_CONFIG_INVALID", "duplicate signer id", field="signers")
    for s in doc["signers"]:
        try:
            from .keys import public_key
            public_key(s["public_key"])
        except Exception:
            raise EcpError("ECP_CONFIG_INVALID", "signer public key is not Ed25519", field="signers", signer=s["id"]) from None
    rule_ids = [r["id"] for r in doc["policy"]["rules"]]
    if len(rule_ids) != len(set(rule_ids)):
        raise EcpError("ECP_CONFIG_INVALID", "duplicate policy rule id", field="policy")
    if doc["policy"]["engine"] == "external" and not doc["policy"].get("external_endpoint"):
        raise EcpError("ECP_CONFIG_INVALID", "external policy engine requires an endpoint", field="policy")
    if doc["environment"] == "prod" and not doc["provenance"].get("require_signature", True):
        raise EcpError("ECP_CONFIG_INVALID", "prod may not disable signature verification", field="provenance")
    rbac = Rbac(doc["roles"], [Binding.from_doc(b) for b in doc["bindings"]])
    return Policy(
        generation=digest_of(doc), doc=copy.deepcopy(doc), rbac=rbac,
        registries=tuple((r["host"].lower(), parse_scope(r["scope"])) for r in doc["registries"]),
        signers={s["id"]: Signer(s["id"], s["public_key"], parse_scope(s["scope"]), bool(s.get("revoked", False)),
                                 s.get("not_after")) for s in doc["signers"]},
        limits={**DEFAULT_LIMITS, **doc["limits"]})


class ConfigManager:
    def __init__(self, journal, *, required_approvals: Optional[int] = None):
        self.journal = journal
        self._lock = threading.RLock()
        self._staged: dict[str, dict[str, Any]] = {}
        self._approvals: dict[str, set[str]] = {}
        self._history: list[dict[str, Any]] = []
        self._active: Optional[Policy] = None
        self._forced_approvals = required_approvals

    # -- replay (called by the service while rebuilding from the journal)
    def apply_record(self, kind: str, body: dict[str, Any], rec: dict[str, Any]) -> None:
        if kind == "config.stage":
            self._staged[body["generation"]] = body
            self._approvals.setdefault(body["generation"], set())
        elif kind == "config.approve":
            self._approvals.setdefault(body["generation"], set()).add(body["approver"])
        elif kind == "config.activate":
            staged = self._staged[body["generation"]]
            self._active = build_policy(staged["doc"])
            self._history.append({**{k: v for k, v in body.items()}, "seq": rec["seq"], "ts": rec["ts"]})

    def checkpoint(self) -> dict[str, Any]:
        """Everything replay needs, so compaction may drop the original stage/approve records."""
        with self._lock:
            keep = {h["generation"] for h in self._history}
            if self._active:
                keep.add(self._active.generation)
            return {"staged": {g: self._staged[g] for g in keep if g in self._staged},
                    "approvals": {g: sorted(self._approvals.get(g, ())) for g in keep},
                    "history": copy.deepcopy(self._history),
                    "active": self._active.generation if self._active else None}

    def load_checkpoint(self, cp: dict[str, Any]) -> None:
        with self._lock:
            self._staged = copy.deepcopy(cp["staged"])
            self._approvals = {g: set(v) for g, v in cp["approvals"].items()}
            self._history = copy.deepcopy(cp["history"])
            self._active = build_policy(self._staged[cp["active"]]["doc"]) if cp["active"] else None

    @property
    def active(self) -> Optional[Policy]:
        return self._active

    def _required(self, doc: dict[str, Any]) -> int:
        if self._forced_approvals is not None:
            return self._forced_approvals
        return int(doc.get("dual_authorization", {}).get("config_activate", 2 if doc["environment"] == "prod" else 1))

    def stage(self, doc: dict[str, Any], *, author: str, source_repo: str, source_rev: str,
              change_ticket: str = "") -> str:
        policy = build_policy(doc)  # validation happens before anything is recorded
        gen = policy.generation
        with self._lock:
            if gen not in self._staged:
                body = {"generation": gen, "doc": policy.doc, "author": author, "source_repo": source_repo[:2048],
                        "source_rev": source_rev[:128], "change_ticket": change_ticket[:128]}
                self.journal.append("config.stage", body)
                self._staged[gen] = body
                self._approvals[gen] = set()
        return gen

    def approve(self, gen: str, approver: str) -> int:
        with self._lock:
            if gen not in self._staged:
                raise EcpError("ECP_NOT_FOUND", "unknown generation", generation=gen)
            if approver == self._staged[gen]["author"]:
                raise EcpError("ECP_DUAL_AUTH_REQUIRED", "author may not approve own change", generation=gen)
            if approver not in self._approvals[gen]:
                self.journal.append("config.approve", {"generation": gen, "approver": approver})
                self._approvals[gen].add(approver)
            return len(self._approvals[gen])

    def activate(self, gen: str, *, activated_by: str, expected_active: Optional[str], reason: str = "",
                 bootstrap: bool = False, _rollback: bool = False) -> Policy:
        with self._lock:
            current = self._active.generation if self._active else None
            if expected_active != current:
                raise EcpError("ECP_CONFIG_CONFLICT", "active generation changed", generation=str(current))
            if gen not in self._staged:
                raise EcpError("ECP_NOT_FOUND", "unknown generation", generation=gen)
            doc = self._staged[gen]["doc"]
            # The proposed generation may not lower its own approval bar: the stricter of the
            # active and proposed requirements applies (review finding R1).
            need = max(self._required(doc), self._required(self._active.doc) if self._active else 0)
            have = len(self._approvals[gen])
            # rollback skips new approvals only when the target is not weaker than the active bar
            previously_active = _rollback and any(h["generation"] == gen for h in self._history) and \
                (self._active is None or self._required(doc) >= self._required(self._active.doc))
            if not bootstrap and not previously_active and have < need:
                raise EcpError("ECP_DUAL_AUTH_REQUIRED", "insufficient distinct approvals", count=have, limit=need,
                               generation=gen)
            if bootstrap and current is not None:
                raise EcpError("ECP_FORBIDDEN", "bootstrap activation only allowed on an empty store", generation=gen)
            policy = build_policy(doc)  # re-validate at activation (schema may have tightened)
            body = {"generation": gen, "previous": current, "activated_by": activated_by, "reason": reason[:256],
                    "rollback": bool(previously_active),
                    "approvers": sorted(self._approvals[gen]), "bootstrap": bootstrap,
                    "author": self._staged[gen]["author"], "source_rev": self._staged[gen]["source_rev"]}
            self.journal.append("config.activate", body)  # durable before visible
            self._active = policy
            self._history.append(body)
            return policy

    def rollback(self, to_gen: str, *, activated_by: str, reason: str) -> Policy:
        with self._lock:
            if not any(h["generation"] == to_gen for h in self._history):
                raise EcpError("ECP_NOT_FOUND", "rollback target was never active", generation=to_gen)
            cur = self._active.generation if self._active else None
            # a rollback target already passed its approval (or bootstrap) gate when it was first
            # activated; rolling back to it is the emergency path and must not wait for new approvals
            return self.activate(to_gen, activated_by=activated_by, expected_active=cur, reason=f"rollback: {reason}",
                                 _rollback=True)

    def history(self) -> list[dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._history)

    def staged(self, gen: str) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._staged[gen])

    def diff(self, a: str, b: str) -> dict[str, Any]:
        da, db = self._staged[a]["doc"], self._staged[b]["doc"]
        return {k: {"from": da.get(k), "to": db.get(k)} for k in sorted(set(da) | set(db))
                if canonical_json(da.get(k)) != canonical_json(db.get(k))}
