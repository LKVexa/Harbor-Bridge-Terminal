"""Trusted caller identity binding (M06).

An ``IdentityContext`` is only ever produced by an authenticator (authn) from
verified credentials -- never from caller-supplied names.  Link keys include the
full identity tuple, so the same component/link name in another tenant,
environment, site or workload is a different link.
"""
from __future__ import annotations

from dataclasses import dataclass, fields

from ..provider import _validate_identifier

FIELDS = ("tenant", "environment", "site", "workload", "component")


@dataclass(frozen=True)
class IdentityContext:
    tenant: str
    environment: str
    site: str
    workload: str
    component: str
    authenticated: bool = False  # only authn sets True
    principal: str = ""

    def __post_init__(self):
        for f in FIELDS:
            _validate_identifier(getattr(self, f), f)

    def scope(self) -> tuple[str, str, str, str, str]:
        return tuple(getattr(self, f) for f in FIELDS)  # type: ignore[return-value]

    def as_dict(self) -> dict:
        return {f: getattr(self, f) for f in FIELDS}

    def label(self) -> str:
        return "/".join(self.scope())


def same_scope(a: IdentityContext, b: dict | IdentityContext) -> bool:
    other = b.scope() if isinstance(b, IdentityContext) else tuple(b.get(f) for f in FIELDS)
    return a.scope() == other
