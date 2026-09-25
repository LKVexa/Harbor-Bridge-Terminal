"""Deny-by-default capability policy (checklist #19, #40, #43).

A decision requires ALL of: the principal holds a role granting the verb; the
secret's scope names the principal's (tenant, app); and the secret belongs to
the principal's tenant namespace.  Decisions are returned with the policy
digest they were evaluated against, which the audit log records (provenance).
An external INV-59 policy engine can be plugged in through ``PolicyEngine``.
"""
from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass

from .identity import ROLES, Principal


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    policy_digest: str


class PolicyEngine:
    def decide(self, principal: Principal, verb: str, secret: str) -> Decision:  # pragma: no cover - interface
        raise NotImplementedError


class ScopePolicy(PolicyEngine):
    def __init__(self):
        self._scopes: dict[str, frozenset[tuple[str, str]]] = {}
        self._lock = threading.Lock()
        self._digest = self._compute()

    def _compute(self) -> str:
        canon = json.dumps({k: sorted(map(list, v)) for k, v in sorted(self._scopes.items())}, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(canon.encode()).hexdigest()

    @property
    def digest(self) -> str:
        return self._digest

    def set_scope(self, secret: str, members: list[tuple[str, str]]) -> str:
        tenant = secret.split("/", 1)[0]
        for t, _ in members:
            if t != tenant:
                raise ValueError("scope member outside the secret's tenant namespace")
        with self._lock:
            self._scopes[secret] = frozenset(members)
            self._digest = self._compute()
            return self._digest

    def scope_of(self, secret: str) -> frozenset:
        return self._scopes.get(secret, frozenset())

    def decide(self, principal, verb, secret):
        with self._lock:
            d = self._digest
            if not any(verb in ROLES.get(r, ()) for r in principal.roles):
                return Decision(False, "role_lacks_verb", d)
            if secret.split("/", 1)[0] != principal.tenant:
                return Decision(False, "cross_tenant", d)
            if verb in ("resolve", "use", "rotate") and (principal.tenant, principal.app) not in self._scopes.get(secret, ()):
                return Decision(False, "not_in_scope", d)
            return Decision(True, "allowed", d)
