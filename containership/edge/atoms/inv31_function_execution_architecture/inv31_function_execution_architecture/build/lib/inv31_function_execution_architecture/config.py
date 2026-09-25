"""Declarative, transactional configuration for INV-31 (C033/C036/C037/C038).

A configuration document (``PK_INV31_CONFIG/1``) is validated in full before
anything changes.  Activation builds a fresh pool generation with the new
limits and swaps it in under the gateway lock, so there is no state in which
half of a configuration is active.  Every activation records provenance
(digest, version, author, activating principal, activation tick) in the
hash-chained audit log, and the previous generation is kept for rollback.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from .boundary import CAP_CONFIG, Gateway, TenantQuota, canonical
from .errors import AuthorizationDenied, ConfigurationRejected, Inv31Error, to_error
from .runtime import FunctionPool, _validate_identifier, _validate_tick

CONFIG_SCHEMA = "PK_INV31_CONFIG/1"
_TOP = {"schema", "config_version", "author", "environment", "pool",
        "tenant_quotas", "max_tenant_share"}
_POOL = {"concurrency_limit", "max_age", "max_instances"}
_LIMITS = {"concurrency_limit": (1, 1024), "max_age": (1, 10_000_000),
           "max_instances": (1, 1_000_000)}
ENVIRONMENTS = ("cloud", "datacenter", "near-edge", "far-edge", "test")


def _int(v: Any, name: str, lo: int, hi: int) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
        raise ConfigurationRejected(f"{name} must be an integer in [{lo}, {hi}]", field=name)
    return v


def validate(doc: Mapping[str, Any]) -> dict[str, Any]:
    """Return a normalised copy of ``doc`` or raise ConfigurationRejected."""
    if not isinstance(doc, Mapping):
        raise ConfigurationRejected("configuration must be an object")
    unknown = set(doc) - _TOP
    if unknown:
        raise ConfigurationRejected(f"unknown fields {sorted(unknown)}", field="(root)")
    if doc.get("schema") != CONFIG_SCHEMA:
        raise ConfigurationRejected("unsupported configuration schema", field="schema")
    try:
        author = _validate_identifier(doc.get("author"), "author")
        env = doc.get("environment")
    except (TypeError, ValueError) as exc:
        raise ConfigurationRejected(str(exc), field="author") from None
    if env not in ENVIRONMENTS:
        raise ConfigurationRejected(f"environment must be one of {ENVIRONMENTS}", field="environment")
    version = _int(doc.get("config_version"), "config_version", 1, 2**31)
    pool = doc.get("pool")
    if not isinstance(pool, Mapping) or set(pool) != _POOL:
        raise ConfigurationRejected(f"pool must contain exactly {sorted(_POOL)}", field="pool")
    pool_n = {k: _int(pool[k], f"pool.{k}", *_LIMITS[k]) for k in sorted(_POOL)}
    share = doc.get("max_tenant_share", 0.5)
    if isinstance(share, bool) or not isinstance(share, (int, float)) or not 0 < share <= 1:
        raise ConfigurationRejected("max_tenant_share must be in (0, 1]", field="max_tenant_share")
    quotas_in = doc.get("tenant_quotas", {})
    if not isinstance(quotas_in, Mapping) or len(quotas_in) > 10_000:
        raise ConfigurationRejected("tenant_quotas must be an object", field="tenant_quotas")
    quotas: dict[str, int] = {}
    for tenant, q in quotas_in.items():
        try:
            _validate_identifier(tenant, "tenant")
        except (TypeError, ValueError) as exc:
            raise ConfigurationRejected(str(exc), field="tenant_quotas") from None
        quotas[tenant] = _int(q, f"tenant_quotas.{tenant}", 1, pool_n["max_instances"])
    return {"schema": CONFIG_SCHEMA, "config_version": version, "author": author,
            "environment": env, "pool": pool_n, "tenant_quotas": quotas,
            "max_tenant_share": float(share)}


def digest(doc: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical(doc)).hexdigest()


def load_file(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return validate(json.load(fh))


@dataclass
class ConfigManager:
    gateway: Gateway
    post_apply_check: Callable[[Gateway], bool] | None = None
    history: list[dict[str, Any]] = field(default_factory=list)

    @property
    def active(self) -> dict[str, Any] | None:
        return self.history[-1] if self.history else None

    def _activate_locked(self, doc: dict[str, Any]) -> tuple[FunctionPool, dict, float, TenantQuota]:
        gw = self.gateway
        previous = (gw.pool, dict(gw.quotas), gw.max_tenant_share, gw.default_quota)
        busy = [i.name for i in gw.pool.instances if i.snapshot(i.last_used_at)["in_flight"]]
        if busy:
            raise ConfigurationRejected("cannot activate while invocations are in flight")
        new_pool = FunctionPool(**doc["pool"])
        gw.pool.destroy_idle()  # old generation holds no reusable state after the swap
        gw.pool = new_pool
        gw.max_tenant_share = doc["max_tenant_share"]
        gw.default_quota = TenantQuota(max(1, int(new_pool.max_instances * gw.max_tenant_share)))
        gw.quotas = {t: TenantQuota(q) for t, q in doc["tenant_quotas"].items()}
        return previous  # type: ignore[return-value]

    def apply(self, assertion: Mapping[str, Any], doc: Mapping[str, Any], *, now: int) -> dict[str, Any]:
        gw = self.gateway
        try:
            now = _validate_tick(now)
            principal = gw.authenticator.authenticate(assertion, now)
            if CAP_CONFIG not in principal.capabilities:
                raise AuthorizationDenied("capability not granted", capability=CAP_CONFIG)
            if principal.kind == "service":
                raise AuthorizationDenied("configuration activation requires a human or operator",
                                          capability=CAP_CONFIG)
            normal = validate(doc)
            if self.active and normal["config_version"] <= self.active["doc"]["config_version"]:
                raise ConfigurationRejected("config_version must increase monotonically",
                                            field="config_version")
            with gw._lock:
                previous = self._activate_locked(normal)
                ok = True
                if self.post_apply_check is not None:
                    try:
                        ok = bool(self.post_apply_check(gw))
                    except Exception:  # noqa: BLE001
                        ok = False
                if not ok:
                    gw.pool, gw.quotas, gw.max_tenant_share, gw.default_quota = previous
                    gw.audit.append("config.auto_rollback", subject=principal.subject, tick=now,
                                    digest=digest(normal), config_version=normal["config_version"])
                    raise ConfigurationRejected("post-activation check failed; previous "
                                                "configuration restored automatically")
                record = {"doc": normal, "digest": digest(normal), "activated_at": now,
                          "activated_by": principal.subject, "author": normal["author"],
                          "config_version": normal["config_version"]}
                self.history.append(record)
                gw.audit.append("config.activate", subject=principal.subject, tick=now,
                                digest=record["digest"], config_version=normal["config_version"],
                                author=normal["author"])
            return {"ok": True, "provenance": {k: v for k, v in record.items() if k != "doc"}}
        except (Inv31Error, RuntimeError, TypeError, ValueError) as exc:
            return {"ok": False, "error": to_error(exc)}

    def rollback(self, assertion: Mapping[str, Any], *, now: int) -> dict[str, Any]:
        """Operator-driven rollback to the previous activated configuration."""
        gw = self.gateway
        try:
            now = _validate_tick(now)
            principal = gw.authenticator.authenticate(assertion, now)
            if CAP_CONFIG not in principal.capabilities or principal.kind == "service":
                raise AuthorizationDenied("rollback requires config:apply as human/operator",
                                          capability=CAP_CONFIG)
            if len(self.history) < 2:
                raise ConfigurationRejected("no previous configuration to roll back to")
            with gw._lock:
                target = self.history[-2]
                self._activate_locked(target["doc"])
                self.history.pop()
                gw.audit.append("config.rollback", subject=principal.subject, tick=now,
                                digest=target["digest"], config_version=target["config_version"])
            return {"ok": True, "active_digest": target["digest"]}
        except (Inv31Error, RuntimeError, TypeError, ValueError) as exc:
            return {"ok": False, "error": to_error(exc)}
