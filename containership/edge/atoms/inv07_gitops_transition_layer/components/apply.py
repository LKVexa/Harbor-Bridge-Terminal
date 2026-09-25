"""Atomic apply / transaction strategy (component 07).

``plan`` diffs desired resources against live resources and emits a
deterministic, dependency-ordered action list:

* creates/updates ordered by ``KIND_ORDER`` (Namespace, CRDs, identities,
  RBAC, config, services, workloads, then everything else), ties broken by
  resource id -- the same inputs always give the same plan bytes;
* deletes (prune; only objects we own) in exact reverse order;
* no-op when the live object's normalised digest equals desired.

``Transaction.run`` executes a plan as one unit:

1. **preflight** -- every apply is dry-run first; any failure aborts before a
   single mutation (nothing to compensate);
2. **intent** -- the plan is journalled with an idempotency key before any
   effect (``state.ControllerState.begin``);
3. **effects** -- actions run in order; each outcome is journalled;
4. on failure, **compensation** restores recorded pre-images in reverse
   order (re-apply previous object / delete what we created); if
   compensation itself fails the result is ``PartialApply`` and the caller
   must quarantine the target (component 20) -- no automatic retry on a
   half-applied estate.
"""
from __future__ import annotations

import copy
import hashlib
import json

from .errors import ApplyFailed, Conflict, GitOpsError, PartialApply
from .target import OWNER_ANN, REV_ANN, obj_digest, rid_str

KIND_ORDER = ["Namespace", "CustomResourceDefinition", "ServiceAccount", "ClusterRole", "ClusterRoleBinding",
              "Role", "RoleBinding", "NetworkPolicy", "ConfigMap", "Secret", "Service", "StatefulSet",
              "Deployment", "DaemonSet", "Job", "CronJob", "Ingress"]


def _rank(rid: tuple) -> tuple:
    k = rid[1]
    return (KIND_ORDER.index(k) if k in KIND_ORDER else len(KIND_ORDER), rid)


def plan(desired: dict, live: dict, *, owner: str, prune: bool, revision: str) -> list[dict]:
    acts = []
    for rid in sorted(desired, key=_rank):
        want = copy.deepcopy(desired[rid])
        want.setdefault("metadata", {}).setdefault("annotations", {})[OWNER_ANN] = owner
        cur = live.get(rid)
        if cur is None:
            acts.append({"op": "create", "rid": list(rid), "version": None})
        elif obj_digest(cur[0]) != obj_digest(want):
            acts.append({"op": "update", "rid": list(rid), "version": cur[1]})
    if prune:
        for rid in sorted((r for r in live if r not in desired), key=_rank, reverse=True):
            cur = live[rid]
            if cur[0].get("metadata", {}).get("annotations", {}).get(OWNER_ANN) == owner:
                acts.append({"op": "delete", "rid": list(rid), "version": cur[1]})
    return acts


def plan_digest(acts: list[dict], revision: str) -> str:
    return hashlib.sha256(json.dumps({"rev": revision, "acts": acts}, sort_keys=True).encode()).hexdigest()


class Transaction:
    def __init__(self, target, state, *, owner: str, epoch: int, revision: str, ref: str) -> None:
        self.t, self.state, self.owner, self.epoch, self.rev, self.ref = target, state, owner, epoch, revision, ref

    def _obj(self, desired: dict, rid: tuple) -> dict:
        o = copy.deepcopy(desired[rid])
        o.setdefault("metadata", {}).setdefault("annotations", {})[REV_ANN] = self.rev
        return o

    def run(self, acts: list[dict], desired: dict, live: dict, *, at: int) -> dict:
        key = plan_digest(acts, self.rev)
        # 1. preflight
        for a in acts:
            rid = tuple(a["rid"])
            if a["op"] != "delete":
                try:
                    self.t.apply(rid, self._obj(desired, rid), expected_version=a["version"], epoch=self.epoch,
                                 owner=self.owner, dry_run=True)
                except GitOpsError as exc:
                    raise ApplyFailed("preflight rejected plan; nothing applied", rid=rid_str(rid),
                                      cause=exc.code) from exc
        # 2. intent
        if not self.state.begin(key, oid=self.rev, ref=self.ref, plan=acts, fence=self.epoch):
            return {"key": key, "duplicate": True, "applied": 0}
        done: list[tuple[dict, str | None]] = []
        try:
            for a in acts:
                rid = tuple(a["rid"])
                if a["op"] == "delete":
                    self.t.delete(rid, expected_version=a["version"], epoch=self.epoch, owner=self.owner)
                    done.append((a, None))
                else:
                    nv = self.t.apply(rid, self._obj(desired, rid), expected_version=a["version"],
                                      epoch=self.epoch, owner=self.owner)
                    done.append((a, nv))
                self.state.effect(key, rid_str(rid), a["op"], True)
        except GitOpsError as exc:
            self.state.effect(key, rid_str(tuple(a["rid"])), a["op"], False)
            comp_errors = self._compensate(done, live)
            if comp_errors:
                self.state.abort(key, "partial")
                raise PartialApply("apply failed and compensation failed; quarantine required",
                                   failed=rid_str(tuple(a["rid"])), compensation_errors=comp_errors[:5],
                                   cause=exc.code) from exc
            self.state.abort(key, "compensated")
            raise ApplyFailed("apply failed; all completed actions compensated", failed=rid_str(tuple(a["rid"])),
                              cause=exc.code) from exc
        after = self.t.list()
        self.state.commit(key, oid=self.rev, ref=self.ref, at=at,
                          live_digest_map={rid_str(r): obj_digest(after[r][0]) for r in desired if r in after})
        return {"key": key, "duplicate": False, "applied": len(done)}

    def _compensate(self, done, live) -> list[str]:
        errs = []
        for a, nv in reversed(done):
            rid = tuple(a["rid"])
            try:
                if a["op"] == "create":
                    self.t.delete(rid, expected_version=nv, epoch=self.epoch, owner=self.owner, compensate=True)
                elif a["op"] == "update":
                    self.t.apply(rid, live[rid][0], expected_version=nv, epoch=self.epoch, owner=self.owner)
                else:  # delete -> recreate pre-image
                    pre = copy.deepcopy(live[rid][0])
                    self.t.apply(rid, pre, expected_version=None, epoch=self.epoch, owner=self.owner)
            except (GitOpsError, Conflict) as exc:
                errs.append(f"{rid_str(rid)}:{exc.code}")
        return errs
