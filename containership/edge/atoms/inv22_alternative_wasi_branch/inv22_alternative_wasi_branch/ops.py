"""Authenticated, authorized, audited operator API (MC-18, MC-19, MC-21, MC-23, MC-45).

Every mutating call: authenticate token → authorize capability at this
boundary → enforce separation of duties → perform the transactional store
change (which appends the audit event in the same transaction).
"""
from __future__ import annotations

import time

from . import config as cfgmod
from .auth import Authenticator, Authorizer
from .errors import Inv22Error


class Ops:
    def __init__(self, store, authn: Authenticator, authz: Authorizer, *, clock=lambda: int(time.time())) -> None:
        self.store, self.authn, self.authz, self.clock = store, authn, authz, clock

    def _who(self, token: str, action: str, scope: str):
        now = self.clock()
        principal = self.authn.authenticate(token, now=now)
        self.authz.authorize(principal, action, scope, now=now)
        return principal

    def issue_cert(self, token: str, envelope: dict, *, matrix_publisher: str | None, reason: str) -> None:
        p = envelope["payload"]
        who = self._who(token, "cert.issue", f"branch:{p['branch']}/component:{p['component']['id']}")
        self.authz.check_separation(who.subject, "cert.issue", {"matrix.publish": matrix_publisher} if matrix_publisher else {})
        if who.subject == p["issuer"] and who.kind != "ci":
            raise Inv22Error("INV22.AUTH.SEPARATION_OF_DUTIES", "operators cannot self-issue as the signing issuer")
        self.store.issue_cert(envelope, actor=who.subject, reason=reason)

    def revoke_cert(self, token: str, cert_id: str, *, reason: str, expected_rev: int | None = None) -> None:
        who = self._who(token, "cert.revoke", f"cert:{cert_id}")
        self.store.revoke(cert_id, actor=who.subject, reason=reason, expected_rev=expected_rev)

    def activate_config(self, token: str, doc: dict, *, expected_active: int | None, reason: str) -> int:
        who = self._who(token, "config.activate", f"site:{doc.get('site', {}).get('id', 'unknown')}")
        return self.store.activate_config(doc, actor=who.subject, expected_active=expected_active, reason=reason,
                                          validator=cfgmod.validate)

    def rollback_config(self, token: str, *, site: str, reason: str) -> int:
        who = self._who(token, "config.activate", f"site:{site}")
        return self.store.rollback_config(actor=who.subject, reason=reason, validator=cfgmod.validate)

    def set_site_branch(self, token: str, site: str, branch: str, baseline: str, *, fence: int, plan: dict, reason: str) -> int:
        who = self._who(token, "site.branch", f"site:{site}")
        if not plan.get("ok") or plan.get("site") != site or plan.get("target_branch") != branch:
            raise Inv22Error("INV22.POLICY.DENIED", "branch change requires a passing impact plan for this site/branch")
        return self.store.set_site_branch(site, branch, baseline, actor=who.subject, fence=fence, reason=reason)

    def freeze_site(self, token: str, site: str, frozen: bool, *, reason: str) -> None:
        who = self._who(token, "site.freeze", f"site:{site}")
        self.store.set_frozen(site, frozen, actor=who.subject, reason=reason)

    def read_audit(self, token: str, limit: int = 100) -> list[dict]:
        self._who(token, "audit.read", "audit:all")
        return self.store.audit_events(limit)
