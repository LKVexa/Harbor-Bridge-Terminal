"""Approved-branch/ref policy (component 02) and replay/freshness protection
(component 27).

``RefPolicy.admit`` binds a reconciliation to:

* the configured repository URL (``repo_url`` must equal the pinned URL);
* an explicitly approved ref (exact full ref names; ``refs/tags/v*`` style
  globs only when ``allow_tag_globs``);
* an optional immutable OID pin per ref (``pins``);
* ancestry: a new head must be a fast-forward of the last accepted head for
  that ref, unless it is a *signed revert* (``allow_revert``) or an audited
  rollback exception is presented;
* namespaces the rendered manifests may target (checked later by tenancy).

``FreshnessGuard`` keeps a durable per-ref generation (monotonic counter +
last accepted OID + commit time) so that:

* a ref moved back to an older commit (protected-ref rollback / replay of an
  old signed commit) is ``StaleRef`` unless it is a descendant;
* a commit older than ``max_commit_age`` is refused (stale signed state);
* a verification result is bound to (oid, trust digest, policy digest) and is
  invalidated when either digest changes.
"""
from __future__ import annotations

import fnmatch
import json
import os
import threading
from dataclasses import dataclass, field

from .fsutil import load_json, read_bytes, read_text  # noqa: F401
from .errors import Malformed, NonFastForward, RefNotApproved, StaleRef


@dataclass
class RefPolicy:
    repo_url: str
    approved: tuple[str, ...]
    pins: dict[str, str] = field(default_factory=dict)
    allow_tag_globs: bool = False

    def __post_init__(self):
        for r in self.approved:
            if not r.startswith(("refs/heads/", "refs/tags/")):
                raise Malformed("approved ref must be fully qualified", ref=r)
            if any(c in r for c in "*?[") and not (self.allow_tag_globs and r.startswith("refs/tags/")):
                raise Malformed("globs are only allowed for tags when allow_tag_globs is set", ref=r)

    def is_approved(self, ref: str) -> bool:
        return any(ref == a or (self.allow_tag_globs and any(c in a for c in "*?[") and fnmatch.fnmatchcase(ref, a))
                   for a in self.approved)

    def admit(self, *, repo_url: str, ref: str, oid: str, previous: str | None, is_ancestor,
              is_signed_revert: bool = False, exception: dict | None = None) -> dict:
        if repo_url != self.repo_url:
            raise RefNotApproved("reconciliation targets an unconfigured repository")
        if not self.is_approved(ref):
            raise RefNotApproved("ref is not approved", ref=ref)
        pin = self.pins.get(ref)
        if pin and pin != oid:
            raise RefNotApproved("ref does not resolve to its pinned OID", ref=ref)
        mode = "initial"
        if previous and previous != oid:
            if is_signed_revert:
                mode = "signed_revert"
            elif is_ancestor(previous, oid):
                mode = "fast_forward"
            elif exception and exception.get("ref") == ref and exception.get("to") == oid and exception.get("approved_by"):
                mode = "rollback_exception"
            else:
                raise NonFastForward("new head is not a descendant of the last accepted head", ref=ref)
        elif previous == oid:
            mode = "unchanged"
        return {"ref": ref, "oid": oid, "mode": mode}


class FreshnessGuard:
    """Durable per-ref generation store (JSON, atomically replaced)."""

    def __init__(self, path: str, *, max_commit_age: int) -> None:
        self.path, self.max_age = path, max_commit_age
        self._lock = threading.Lock()
        self._s = load_json(path) if os.path.exists(path) else {"schema": "PK_GITOPS_FRESHNESS/1", "refs": {}}

    def last(self, ref: str) -> dict | None:
        return self._s["refs"].get(ref)

    def check(self, ref: str, oid: str, commit_time: int, now: int, *, descends: bool) -> None:
        if now - commit_time > self.max_age:
            raise StaleRef("commit is older than max_commit_age", ref=ref, age=now - commit_time)
        if commit_time - now > 300:
            raise StaleRef("commit time is in the future beyond skew allowance", ref=ref)
        last = self.last(ref)
        if last and last["oid"] != oid and not descends:
            raise StaleRef("ref moved to a commit that does not descend from the accepted generation", ref=ref,
                           generation=last["generation"])

    def accept(self, ref: str, oid: str, commit_time: int, *, trust_digest: str, policy_digest: str,
               mode: str) -> dict:
        with self._lock:
            last = self._s["refs"].get(ref)
            gen = (last["generation"] + 1) if last and last["oid"] != oid else (last["generation"] if last else 1)
            rec = {"oid": oid, "generation": gen, "commit_time": commit_time, "trust_digest": trust_digest,
                   "policy_digest": policy_digest, "mode": mode}
            self._s["refs"][ref] = rec
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self._s, fh, sort_keys=True)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
            return rec

    def still_valid(self, ref: str, *, trust_digest: str, policy_digest: str) -> bool:
        last = self.last(ref)
        return bool(last) and last["trust_digest"] == trust_digest and last["policy_digest"] == policy_digest
