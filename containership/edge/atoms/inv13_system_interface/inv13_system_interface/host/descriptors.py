"""MC-004 -- capability-descriptor integration (INV-42 binding).

A ``Descriptor`` is the authoritative record of one grant: stable content-derived
ID, owner (tenant/workload), capability, scope (e.g. logical preopen + host root
+ rights), parent, and provenance (which policy decision and which actor minted
it).  Children may only *attenuate* (subset rights, same capability, narrower
or equal scope); revoking a descriptor revokes its whole subtree.  The
``DescriptorTable`` interface is what the real INV-42 system implements; the
in-process implementation here is the reference used by tests.
"""
from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from typing import Any

from .errors import ErrorCode, Inv13Error

RIGHTS = frozenset({"read", "write", "create", "delete", "list", "stat",
                    "connect", "bind", "listen", "resolve", "get", "invoke"})


@dataclass(frozen=True, slots=True)
class Descriptor:
    id: str
    tenant: str
    workload: str
    capability: str
    scope: tuple[tuple[str, str], ...]
    rights: frozenset[str]
    parent: str | None
    provenance: tuple[tuple[str, str], ...]
    epoch: int

    def scope_dict(self) -> dict[str, str]:
        return dict(self.scope)


def _digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _scope_within(child: dict[str, str], parent: dict[str, str]) -> bool:
    for key, pval in parent.items():
        cval = child.get(key)
        if cval is None:
            return False
        if key in ("logical", "host_root", "prefix"):
            if not (cval == pval or cval.startswith(pval.rstrip("/") + "/")):
                return False
        elif cval != pval:
            return False
    return True


class DescriptorTable:
    def __init__(self) -> None:
        self._d: dict[str, Descriptor] = {}
        self._children: dict[str, set[str]] = {}
        self._revoked: set[str] = set()
        self._epoch = 0
        self._lock = threading.RLock()

    def mint(self, *, tenant: str, workload: str, capability: str, scope: dict[str, str],
             rights: set[str] | frozenset[str], provenance: dict[str, str]) -> Descriptor:
        rights = frozenset(rights)
        if not rights or not rights <= RIGHTS:
            raise Inv13Error(ErrorCode.INVALID_ARGUMENT, sorted(rights - RIGHTS))
        for req in ("decision", "actor"):
            if not provenance.get(req):
                raise Inv13Error(ErrorCode.INVALID_ARGUMENT, f"provenance.{req} required")
        return self._insert(tenant, workload, capability, scope, rights, None, provenance)

    def derive(self, parent_id: str, *, scope: dict[str, str] | None = None,
               rights: set[str] | None = None, workload: str | None = None,
               provenance: dict[str, str]) -> Descriptor:
        with self._lock:
            parent = self.check(parent_id)
            new_scope = scope if scope is not None else parent.scope_dict()
            new_rights = frozenset(rights) if rights is not None else parent.rights
            if not new_rights <= parent.rights:
                raise Inv13Error(ErrorCode.POLICY_DENIED, "rights amplification")
            if not _scope_within(new_scope, parent.scope_dict()):
                raise Inv13Error(ErrorCode.POLICY_DENIED, "scope widening")
            return self._insert(parent.tenant, workload or parent.workload, parent.capability,
                                new_scope, new_rights, parent_id, provenance)

    def _insert(self, tenant, workload, capability, scope, rights, parent, provenance) -> Descriptor:
        with self._lock:
            self._epoch += 1
            body = {"tenant": tenant, "workload": workload, "capability": capability,
                    "scope": sorted(scope.items()), "rights": sorted(rights), "parent": parent,
                    "provenance": sorted(provenance.items()), "epoch": self._epoch}
            d = Descriptor("cd-" + _digest(body)[:32], tenant, workload, capability,
                           tuple(sorted(scope.items())), rights, parent,
                           tuple(sorted(provenance.items())), self._epoch)
            self._d[d.id] = d
            if parent:
                self._children.setdefault(parent, set()).add(d.id)
            return d

    def check(self, desc_id: str, *, tenant: str | None = None, right: str | None = None) -> Descriptor:
        with self._lock:
            d = self._d.get(desc_id)
            if d is None:
                raise Inv13Error(ErrorCode.INVALID_HANDLE)
            if desc_id in self._revoked:
                raise Inv13Error(ErrorCode.STALE_HANDLE, "revoked")
            if tenant is not None and d.tenant != tenant:
                raise Inv13Error(ErrorCode.POLICY_DENIED, "cross-tenant")
            if right is not None and right not in d.rights:
                raise Inv13Error(ErrorCode.POLICY_DENIED, f"right {right}")
            return d

    def revoke(self, desc_id: str) -> list[str]:
        with self._lock:
            if desc_id not in self._d:
                raise Inv13Error(ErrorCode.INVALID_HANDLE)
            out, stack = [], [desc_id]
            while stack:
                cur = stack.pop()
                if cur not in self._revoked:
                    self._revoked.add(cur)
                    out.append(cur)
                stack.extend(self._children.get(cur, ()))
            return out

    def live(self, tenant: str | None = None) -> list[Descriptor]:
        with self._lock:
            return [d for k, d in self._d.items() if k not in self._revoked
                    and (tenant is None or d.tenant == tenant)]
