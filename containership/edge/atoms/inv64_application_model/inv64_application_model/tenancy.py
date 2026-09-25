"""Tenant/workload isolation at the integration boundary (MC-16; C046).

Isolation profile ``inv64-process-v1`` (recorded in status and release evidence):
one Python process, logical isolation by tenant key. It does **not** provide
memory/kernel isolation between tenants; hosts needing that run one process
(or Wasm/container sandbox) per tenant — a residual risk stated in
SPECIFICATION.md §8.

Rules enforced:

* the tenant comes from the authenticated :class:`auth.Principal`; a manifest
  or request that *claims* a different tenant is ``tenant.mismatch``;
* declarations carrying a ``tenant`` field for another tenant are
  ``tenant.cross_reference`` unless that provider is listed in the
  :class:`SharedResources` contract for the requesting tenant;
* every store/cache/idempotency key is ``(tenant, ...)``; storage paths are
  derived from a SHA-256 of the key, so tenant-controlled strings never form
  filesystem paths, metric labels or endpoints;
* reads are filtered by tenant; a platform operator view is a distinct capability.
"""
from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass, field
from typing import Any, Mapping

from .errors import Inv64Error

ISOLATION_PROFILE = "inv64-process-v1"


@dataclass
class SharedResources:
    """Explicit shared-provider contract: provider name -> tenants allowed to link it."""

    providers: Mapping[str, frozenset] = field(default_factory=dict)

    def allows(self, provider: str, tenant: str) -> bool:
        return tenant in self.providers.get(provider, frozenset())


def storage_key(*parts: str) -> str:
    return hashlib.sha256("\x00".join(parts).encode()).hexdigest()


def check_manifest_tenancy(manifest: Mapping[str, Any], tenant: str, shared: SharedResources) -> None:
    claimed = manifest.get("tenant")
    if claimed is not None and claimed != tenant:
        raise Inv64Error("tenant.mismatch", details={"field": "tenant"})
    for section in ("components", "providers"):
        for i, item in enumerate(manifest.get(section, []) or []):
            if not isinstance(item, Mapping):
                continue
            owner = item.get("tenant")
            if owner is None or owner == tenant:
                continue
            if section == "providers" and shared.allows(str(item.get("name")), tenant):
                continue
            raise Inv64Error("tenant.cross_reference", details={"path": f"{section}[{i}].tenant"})


class TenantRegistry:
    """Tenant-partitioned store of accepted canonical manifests."""

    def __init__(self, *, per_tenant_limit: int = 10_000):
        self._data: dict[str, dict[str, dict]] = {}
        self._lock = threading.Lock()
        self._limit = per_tenant_limit

    def put(self, tenant: str, environment: str, app: str, record: dict) -> str:
        key = storage_key(tenant, environment, app)
        with self._lock:
            bucket = self._data.setdefault(tenant, {})
            if key not in bucket and len(bucket) >= self._limit:
                raise Inv64Error("admission.tenant_quota", details={"reason": "registry quota"})
            bucket[key] = dict(record, tenant=tenant, environment=environment, app=app)
        return key

    def get(self, tenant: str, environment: str, app: str) -> dict | None:
        with self._lock:
            return self._data.get(tenant, {}).get(storage_key(tenant, environment, app))

    def list(self, tenant: str) -> list[dict]:
        with self._lock:
            return list(self._data.get(tenant, {}).values())

    def restore(self, tenant: str, records: list[dict]) -> int:
        """Restore records, refusing any whose embedded tenant differs (no cross-scope restore)."""
        n = 0
        for r in records:
            if r.get("tenant") != tenant:
                raise Inv64Error("tenant.mismatch", details={"reason": "restore into wrong tenant"})
            self.put(tenant, r["environment"], r["app"], r)
            n += 1
        return n
