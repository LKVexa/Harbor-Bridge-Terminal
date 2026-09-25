"""Multi-tenant hard isolation (21) and residency/site policy (22).

``TenantScope`` is constructed once per controller instance (one instance per
tenant x site -- the contract forbids a global singleton) and enforces:

* identity: tokens for another tenant are refused (``authz``);
* credentials: each tenant's secret refs must live under its own prefix
  (``env:INV07_<TENANT>_*`` / ``file:<secrets_root>/<tenant>/``);
* namespaces: every desired resource must target an allowed namespace;
  cluster-scoped kinds are refused unless explicitly allowed;
* storage/caches: state, mirror and audit paths are derived from
  ``<root>/<tenant>/<site>/`` and ``check_path`` refuses anything that
  escapes it (``..``, symlinks, absolute paths elsewhere);
* telemetry/audit: every record is stamped with tenant/site and the
  ``tenant`` label cardinality is exactly one per instance.

``ResidencyPolicy`` enforces region/site allowlists for the controller, its
backups, its telemetry export destinations and failover targets, binds
credentials to a site, and records time-bounded, approved exceptions.
"""
from __future__ import annotations

import os
import re

from .errors import ResidencyViolation, TenantViolation

CLUSTER_SCOPED = {"Namespace", "ClusterRole", "ClusterRoleBinding", "CustomResourceDefinition",
                  "PersistentVolume", "StorageClass", "PriorityClass", "MutatingWebhookConfiguration",
                  "ValidatingWebhookConfiguration"}


class TenantScope:
    def __init__(self, tenant: str, site: str, *, root: str, namespaces: tuple[str, ...],
                 allow_cluster_kinds: tuple[str, ...] = (), secrets_root: str = "/run/secrets/inv07") -> None:
        for v in (tenant, site):
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", v):
                raise TenantViolation("tenant/site must be DNS-label-like")
        self.tenant, self.site, self.namespaces = tenant, site, tuple(namespaces)
        self.allow_cluster = set(allow_cluster_kinds)
        self.root = os.path.realpath(os.path.join(root, tenant, site))
        self.secrets_root = secrets_root.rstrip("/")
        os.makedirs(self.root, exist_ok=True)

    def path(self, *parts: str) -> str:
        p = os.path.realpath(os.path.join(self.root, *parts))
        self.check_path(p)
        return p

    def check_path(self, p: str) -> None:
        rp = os.path.realpath(p)
        if rp != self.root and not rp.startswith(self.root + os.sep):
            raise TenantViolation("path escapes the tenant/site storage root")

    def check_secret_ref(self, ref: str) -> None:
        env_prefix = f"env:INV07_{self.tenant.upper().replace('-', '_')}_"
        file_prefix = f"file:{self.secrets_root}/{self.tenant}/"
        if not (ref.startswith(env_prefix) or ref.startswith(file_prefix)) or ".." in ref:
            raise TenantViolation("secret reference outside the tenant's credential scope")

    def check_resources(self, desired: dict) -> None:
        for rid in desired:
            kind, ns = rid[1], rid[2]
            if kind in CLUSTER_SCOPED:
                if kind not in self.allow_cluster:
                    raise TenantViolation("cluster-scoped kind not allowed for this tenant", kind=kind)
                continue
            if not ns:
                raise TenantViolation("namespaced resource must declare metadata.namespace", name=rid[3])
            if ns not in self.namespaces:
                raise TenantViolation("namespace outside the tenant's allowed set", namespace=ns)

    def stamp(self, record: dict) -> dict:
        return {**record, "tenant": self.tenant, "site": self.site}


class ResidencyPolicy:
    def __init__(self, *, region: str, allowed_regions: tuple[str, ...], site: str,
                 failover_regions: tuple[str, ...] = (), exceptions: list[dict] | None = None) -> None:
        self.region, self.allowed, self.site = region, set(allowed_regions), site
        self.failover = set(failover_regions)
        self.exceptions = exceptions or []
        if region not in self.allowed:
            raise ResidencyViolation("controller region outside allowed regions", region=region)

    def _exception(self, kind: str, region: str, now: float) -> dict | None:
        for e in self.exceptions:
            if e.get("kind") == kind and e.get("region") == region and e.get("approved_by") \
                    and now < e.get("expires", 0):
                return e
        return None

    def check(self, kind: str, region: str, *, now: float) -> dict:
        """kind in {'backup','telemetry','failover','target','credential'}."""
        allowed = self.failover if kind == "failover" else self.allowed
        if region in allowed:
            return {"kind": kind, "region": region, "decision": "allow", "basis": "allowlist"}
        e = self._exception(kind, region, now)
        if e:
            return {"kind": kind, "region": region, "decision": "allow", "basis": "exception",
                    "approved_by": e["approved_by"], "expires": e["expires"]}
        raise ResidencyViolation("destination region not permitted", kind=kind, region=region)

    def check_credential_site(self, credential_site: str) -> None:
        if credential_site != self.site:
            raise ResidencyViolation("credential is bound to a different site", site=credential_site)
