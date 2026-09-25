"""Authorization/capability enforcement integration (M08).

INV-65 does NOT own policy.  It consumes signed PK_AUTHZ_DECISION/1 records from
the external policy plane and enforces them: signature, freshness, exact subject
scope, action, contract, link name and (for calls) operation must all match, or
the request is refused (fail closed).  Deny wins.  Absence of a decision = deny.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time

from ..errors.mapping import ProviderFault
from ..identity.context import IdentityContext, same_scope
from ..schemas import SchemaError, check

MAX_DECISION_TTL_S = 900


def _canonical(d: dict) -> bytes:
    body = {k: v for k, v in d.items() if k != "signature"}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def sign_decision(key: bytes, decision: dict) -> dict:
    """Fixture signer standing in for the policy plane."""
    d = dict(decision)
    d["signature"] = hmac.new(key, _canonical(d), hashlib.sha256).hexdigest()
    return d


class AuthorizationEnforcer:
    def __init__(self, policy_keys: dict[str, bytes], *, min_policy_version: str | None = None):
        # policy_keys: key-id -> key; the decision's policy_version prefix "kid:version" selects the key
        self._keys = dict(policy_keys)
        self.min_policy_version = min_policy_version

    def enforce(self, decision: object, *, identity: IdentityContext, action: str, contract_id: str,
                link_name: str, operation: str | None = None, now: float | None = None) -> str:
        now = time.time() if now is None else now
        if not identity.authenticated:
            raise ProviderFault("PK_PROVIDER_UNAUTHENTICATED", "identity not authenticated")
        if not isinstance(decision, dict):
            raise ProviderFault("PK_PROVIDER_FORBIDDEN", "no authorization decision")
        try:
            check(decision, "authz_decision")
        except SchemaError:
            raise ProviderFault("PK_PROVIDER_FORBIDDEN", "malformed authorization decision") from None
        kid = decision["policy_version"].split(":", 1)[0]
        key = self._keys.get(kid)
        if key is None or not hmac.compare_digest(
                decision["signature"], hmac.new(key, _canonical(decision), hashlib.sha256).hexdigest()):
            raise ProviderFault("PK_PROVIDER_FORBIDDEN", "decision signature invalid")
        if self.min_policy_version and decision["policy_version"] < self.min_policy_version:
            raise ProviderFault("PK_PROVIDER_FORBIDDEN", "stale policy version")
        if not decision["issued_at"] <= now <= decision["expires_at"] or \
                decision["expires_at"] - decision["issued_at"] > MAX_DECISION_TTL_S:
            raise ProviderFault("PK_PROVIDER_FORBIDDEN", "decision expired or validity too long")
        if decision["effect"] != "allow":
            raise ProviderFault("PK_PROVIDER_FORBIDDEN", "denied by policy")
        if not same_scope(identity, decision["subject"]):
            raise ProviderFault("PK_PROVIDER_FORBIDDEN", "decision subject does not match caller scope")
        res = decision["resource"]
        if decision["action"] != action or res["contract_id"] != contract_id or res["link_name"] != link_name:
            raise ProviderFault("PK_PROVIDER_FORBIDDEN", "decision does not cover this action/resource")
        if action == "call":
            ops = res.get("operations")
            if not ops or operation not in ops:
                raise ProviderFault("PK_PROVIDER_FORBIDDEN", "operation not granted")
        return decision["decision_id"]
