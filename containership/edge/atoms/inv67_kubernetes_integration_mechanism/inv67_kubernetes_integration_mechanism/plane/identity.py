"""Application identity mapping (item 15).

Maps a Kubernetes object (cluster, namespace, name, uid) onto a stable
PLN-02-style application identity. The uid is part of the identity so a
delete-and-recreate with the same name is a *different* application instance
and cannot inherit the old runtime's state. Tenant is derived from an explicit
namespace->tenant binding, never guessed from names; unbound namespaces fail
closed.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .lifecycle import PlaneError

_DNS1123 = re.compile(r"^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?$")
_UID = re.compile(r"^[0-9a-fA-F-]{8,64}$")


@dataclass(frozen=True)
class AppIdentity:
    cluster: str
    tenant: str
    namespace: str
    name: str
    uid: str

    @property
    def app_id(self) -> str:
        h = hashlib.sha256(f"{self.cluster}\x00{self.namespace}\x00{self.name}\x00{self.uid}".encode()).hexdigest()
        return f"app-{h[:24]}"

    def to_dict(self) -> dict:
        return {"cluster": self.cluster, "tenant": self.tenant, "namespace": self.namespace,
                "name": self.name, "uid": self.uid, "appId": self.app_id}


class IdentityMapper:
    def __init__(self, cluster: str, namespace_tenants: dict[str, str]):
        if not _DNS1123.match(cluster):
            raise ValueError("cluster id must be DNS-1123")
        self.cluster = cluster
        self.bindings = dict(namespace_tenants)

    def map(self, namespace: str, name: str, uid: str) -> AppIdentity:
        for label, v in (("namespace", namespace), ("name", name)):
            if not isinstance(v, str) or not _DNS1123.match(v):
                raise PlaneError("INV67_UNAUTHORIZED", f"{label} is not DNS-1123", field=label)
        if not isinstance(uid, str) or not _UID.match(uid):
            raise PlaneError("INV67_UNAUTHORIZED", "object uid missing or malformed", field="uid")
        tenant = self.bindings.get(namespace)
        if tenant is None:
            raise PlaneError("INV67_UNAUTHORIZED", "namespace is not bound to a tenant", namespace=namespace)
        return AppIdentity(self.cluster, tenant, namespace, name, uid)
