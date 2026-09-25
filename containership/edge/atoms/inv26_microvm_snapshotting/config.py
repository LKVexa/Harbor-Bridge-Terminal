"""Declarative configuration: schema, secure defaults, overlays, validation,
atomic activation, provenance and rollback (C033-C039, C035, C038).

Document ``PK_SNAPSHOT_CONFIG/1`` (JSON). Merge order is fixed and explicit —
``base -> environment -> site -> emergency`` — with no environment-variable
precedence at all. Keys in :data:`LOCKED` are global security invariants:
an overlay may restate them with the same value but can never weaken them
(``SNAP_CONFIG_INVALID`` with the field path). Units are in the field names
(``_ms``, ``_bytes``, ``_mib``, ``_per_s``).

Activation (C037) is stage -> validate -> prepare -> compare-and-swap commit of
``config/active`` in the durable :class:`~.metastore.MetaStore`. Readers see
either the old or the new revision, never a mix; a failed validation keeps the
last-known-good revision; every activation writes a provenance record
(revision, digest, author, source, approval reference, activation time,
previous revision) and a fail-closed audit event.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from .errors import SnapshotServiceError
from .metastore import MetaStore
from .redaction import find_secrets

CONFIG_SCHEMA = "PK_SNAPSHOT_CONFIG/1"
TIERS = ("cloud", "datacenter", "near-edge", "far-edge")

DEFAULTS: dict[str, Any] = {
    "schema": CONFIG_SCHEMA,
    "profile": "production",
    "tier": "cloud",
    "environment": None,
    "site": None,
    "region": None,
    "runtime": {"adapter": "firecracker", "version": "1.9", "arch": "x86_64"},
    "storage": {"kind": "filesystem", "root": "/var/lib/inv26/blobs", "quota_bytes": 1 << 40},
    "metadata": {"root": "/var/lib/inv26/meta"},
    "kms": {"key_id": None},
    "auth": {"audience": None},
    "security": {"deny_cross_boundary_restore": True, "require_encryption": True,
                 "require_entropy_ack": True, "require_restore_grant": True,
                 "allow_hs256": False},
    "quotas": {"max_snapshots_per_tenant": 1000, "max_bytes_per_tenant": 256 << 30,
               "max_memory_mib": 65536, "max_devices": 64},
    "admission": {"max_inflight": 64, "max_queue": 128, "per_tenant": 16,
                  "tenant_rate_per_s": 50.0, "tenant_burst": 100.0},
    "timeouts_ms": {"capture": 120000, "restore": 2000, "kms": 300, "storage": 1000,
                    "hypervisor": 1000, "entropy": 200},
    "retry": {"attempts": 3, "base_ms": 10, "cap_ms": 200, "budget_ratio": 0.2},
    "breaker": {"threshold": 5, "cooldown_ms": 5000},
    "residency": {"allowed_sites": [], "allowed_regions": []},
    "telemetry": {"log_level": "info", "trace_sample_ratio": 0.1},
    "restore_budget_ms": 10.0,
}

LOCKED = {
    "security.deny_cross_boundary_restore": True,
    "security.require_encryption": True,
    "security.require_entropy_ack": True,
    "security.require_restore_grant": True,
}

_NUM_BOUNDS = {
    "storage.quota_bytes": (1 << 20, 1 << 50),
    "quotas.max_snapshots_per_tenant": (1, 1_000_000),
    "quotas.max_bytes_per_tenant": (1 << 20, 1 << 50),
    "quotas.max_memory_mib": (1, 1 << 20),
    "quotas.max_devices": (1, 64),
    "admission.max_inflight": (1, 10_000),
    "admission.max_queue": (0, 100_000),
    "admission.per_tenant": (1, 10_000),
    "admission.tenant_rate_per_s": (0.01, 1e6),
    "admission.tenant_burst": (1, 1e6),
    "timeouts_ms.capture": (100, 600_000),
    "timeouts_ms.restore": (10, 60_000),
    "timeouts_ms.kms": (10, 30_000),
    "timeouts_ms.storage": (10, 60_000),
    "timeouts_ms.hypervisor": (10, 60_000),
    "timeouts_ms.entropy": (10, 10_000),
    "retry.attempts": (1, 10),
    "retry.base_ms": (1, 10_000),
    "retry.cap_ms": (1, 60_000),
    "retry.budget_ratio": (0.0, 1.0),
    "breaker.threshold": (1, 1000),
    "breaker.cooldown_ms": (100, 600_000),
    "telemetry.trace_sample_ratio": (0.0, 1.0),
    "restore_budget_ms": (0.1, 60_000),
}
_ID = __import__("re").compile(r"^[a-z0-9][a-z0-9._-]{0,62}$")


def _get(doc: dict, path: str) -> Any:
    cur: Any = doc
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _merge(base: dict, over: dict, path: str, errors: list[str], layer: str) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        p = f"{path}{k}"
        if k not in base and path != "" and not p.startswith("residency"):
            errors.append(f"{p}: unknown field (layer {layer})")
            continue
        if k not in base and path == "":
            errors.append(f"{p}: unknown field (layer {layer})")
            continue
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            out[k] = _merge(base[k], v, p + ".", errors, layer)
        else:
            if p in LOCKED and v != LOCKED[p]:
                errors.append(f"{p}: locked security invariant cannot be changed (layer {layer})")
                continue
            out[k] = copy.deepcopy(v)
    return out


def compose(*layers: tuple[str, dict]) -> dict:
    """Merge ``(name, overlay)`` layers onto DEFAULTS in the given order."""
    order = [n for n, _ in layers]
    allowed = ["base", "environment", "site", "emergency"]
    if [n for n in allowed if n in order] != order or len(set(order)) != len(order):
        raise SnapshotServiceError("SNAP_CONFIG_INVALID", f"overlay order must follow {allowed}, got {order}")
    errors: list[str] = []
    doc = copy.deepcopy(DEFAULTS)
    for name, layer in layers:
        if not isinstance(layer, dict):
            errors.append(f"$: layer {name} is not an object")
            continue
        if name == "emergency":  # the emergency layer may only tighten admission / disable
            extra = set(layer) - {"admission", "quotas"}
            if extra:
                errors.append(f"$: emergency overlay may only set admission/quotas, not {sorted(extra)}")
                continue
        doc = _merge(doc, layer, "", errors, name)
    if errors:
        raise SnapshotServiceError("SNAP_CONFIG_INVALID", "; ".join(errors), fields=errors)
    return doc


def validate(doc: dict) -> list[str]:
    """Syntactic + semantic validation; returns field-path errors (never secret values)."""
    e: list[str] = []
    if not isinstance(doc, dict):
        return ["$: not an object"]
    if doc.get("schema") != CONFIG_SCHEMA:
        e.append("schema: must be PK_SNAPSHOT_CONFIG/1")
    for k in doc:
        if k not in DEFAULTS:
            e.append(f"{str(k)[:40]}: unknown field")
    for k, v in DEFAULTS.items():  # structural shape first: later checks may assume it
        if isinstance(v, dict):
            sect = doc.get(k)
            if not isinstance(sect, dict):
                e.append(f"{k}: must be an object")
                continue
            for sub in v:  # FZ-3: a missing nested key crashed the semantic checks (KeyError)
                if sub not in sect:
                    e.append(f"{k}.{sub}: required")
            for sub in sect:
                if sub not in v:
                    e.append(f"{k}.{str(sub)[:40]}: unknown field")
    if e:
        return e
    for hit, why in find_secrets(doc):
        e.append(f"{hit or '$'}: ({why}) inline secret material is forbidden (use secretref:// via the secret provider)")
    if doc.get("profile") not in ("production", "reference"):
        e.append("profile: must be production|reference")
    if doc.get("tier") not in TIERS:
        e.append(f"tier: must be one of {list(TIERS)}")
    for f in ("environment", "site", "region"):
        if not isinstance(doc.get(f), str) or not _ID.fullmatch(doc[f]):
            e.append(f"{f}: required identifier")
    if not isinstance(_get(doc, "kms.key_id"), str) or not _ID.fullmatch(_get(doc, "kms.key_id") or ""):
        e.append("kms.key_id: required key alias (not key material)")
    if not isinstance(_get(doc, "auth.audience"), str) or not _get(doc, "auth.audience"):
        e.append("auth.audience: required (no anonymous endpoints)")
    rt = doc.get("runtime") or {}
    if rt.get("adapter") not in ("firecracker", "cloud-hypervisor", "reference"):
        e.append("runtime.adapter: unsupported")
    if rt.get("arch") not in ("x86_64", "aarch64"):
        e.append("runtime.arch: unsupported")
    if doc.get("profile") == "production":
        if rt.get("adapter") == "reference":
            e.append("runtime.adapter: reference adapter is not permitted in production")
        if (doc.get("storage") or {}).get("kind") == "memory":
            e.append("storage.kind: memory store is not permitted in production")
        if _get(doc, "security.allow_hs256"):
            e.append("security.allow_hs256: shared-secret credentials are not permitted in production")
    if (doc.get("storage") or {}).get("kind") not in ("filesystem", "memory"):
        e.append("storage.kind: unsupported")
    for path, want in LOCKED.items():
        if _get(doc, path) is not want:
            e.append(f"{path}: locked security invariant must be {want}")
    for path, (lo, hi) in _NUM_BOUNDS.items():
        v = _get(doc, path)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or not lo <= v <= hi:
            e.append(f"{path}: must be a number in [{lo}, {hi}]")
    if not e:
        t = doc["timeouts_ms"]
        if t["restore"] < t["kms"] + t["storage"] // 4 + t["entropy"]:
            e.append("timeouts_ms.restore: must exceed kms + storage/4 + entropy dependency budget")
        if doc["retry"]["cap_ms"] < doc["retry"]["base_ms"]:
            e.append("retry.cap_ms: must be >= retry.base_ms")
        a = doc["admission"]
        if a["per_tenant"] > a["max_inflight"]:
            e.append("admission.per_tenant: must be <= admission.max_inflight")
        if a["tenant_burst"] < 1:
            e.append("admission.tenant_burst: must be >= 1")
        r = doc["residency"]
        if not isinstance(r.get("allowed_sites"), list) or not isinstance(r.get("allowed_regions"), list):
            e.append("residency: allowed_sites/allowed_regions must be lists")
        elif doc["site"] not in r["allowed_sites"] or doc["region"] not in r["allowed_regions"]:
            e.append("residency: this node's site/region must be listed as allowed")
        if doc["tier"] == "far-edge" and doc["runtime"]["arch"] not in ("x86_64", "aarch64"):
            e.append("tier: far-edge runtime arch unsupported")
        if doc["telemetry"]["log_level"] not in ("debug", "info", "warning", "error"):
            e.append("telemetry.log_level: invalid")
        if doc["profile"] == "production" and doc["telemetry"]["log_level"] == "debug":
            e.append("telemetry.log_level: debug logging is not permitted in production")
    return e


def digest(doc: dict) -> str:
    return hashlib.sha256(json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class ConfigStore:
    """Atomic, audited activation with last-known-good and rollback (C036-C038)."""

    KEY = "config/active"

    def __init__(self, meta: MetaStore, audit=None, clock=None):
        self.meta, self.audit = meta, audit
        self.clock = clock or meta.clock
        self._cache: tuple[int, dict] | None = None

    def active(self) -> tuple[int, dict] | None:
        cur = self.meta.get(self.KEY)
        if cur is None:
            return None
        return cur[1]["revision"], cur[1]["doc"]

    def activate(self, doc: dict, *, author: str, source: str, approval_ref: str | None,
                 expect_revision: int | None, scope: str = "node") -> dict:
        errs = validate(doc)
        if errs:
            if self.audit is not None:
                self.audit.append("config.rejected", actor=author, outcome="refused",
                                  reason="SNAP_CONFIG_INVALID", fields=errs[:20])
            raise SnapshotServiceError("SNAP_CONFIG_INVALID", "; ".join(errs[:20]), fields=errs)
        cur = self.meta.get(self.KEY)
        cur_gen, cur_val = (cur[0], cur[1]) if cur else (0, None)
        prev_rev = cur_val["revision"] if cur_val else 0
        if expect_revision is not None and expect_revision != prev_rev:
            raise SnapshotServiceError("SNAP_STALE_GENERATION", f"active revision is {prev_rev}")
        rev = prev_rev + 1
        prov = {"revision": rev, "digest": digest(doc), "author": str(author)[:128], "source": str(source)[:256],
                "approval_ref": approval_ref, "activated_at": int(self.clock() * 1000), "scope": scope,
                "previous_revision": prev_rev}
        if self.audit is not None:  # fail-closed: no unaudited activation
            self.audit.append("config.activate", actor=author, outcome="committing", fail_closed=True,
                              reason=None, revision=rev, digest=prov["digest"], previous=prev_rev)
        self.meta.transact({
            self.KEY: (cur_gen, {"revision": rev, "doc": doc, "provenance": prov}),
            f"config/rev/{rev:08d}": (0, {"doc": doc, "provenance": prov}),
        })
        return prov

    def rollback(self, *, to_revision: int, author: str, reason: str, breakglass: bool = False) -> dict:
        old = self.meta.get(f"config/rev/{to_revision:08d}")
        if old is None:
            raise SnapshotServiceError("SNAP_NOT_FOUND", f"config revision {to_revision}")
        doc = old[1]["doc"]
        return self.activate(doc, author=author, source=f"rollback-to:{to_revision} ({reason[:120]})",
                             approval_ref="breakglass" if breakglass else None, expect_revision=None)

    def history(self) -> list[dict]:
        return [v[1]["provenance"] for _, v in sorted(self.meta.scan("config/rev/").items())]

    def governing(self, revision: int) -> dict | None:
        r = self.meta.get(f"config/rev/{revision:08d}")
        return r[1] if r else None


def example(profile: str = "production", **over) -> dict:
    doc = copy.deepcopy(DEFAULTS)
    doc.update({"environment": "prod", "site": "site-a", "region": "eu-west",
                "kms": {"key_id": "inv26-kek"}, "auth": {"audience": "inv26.site-a.prod"},
                "residency": {"allowed_sites": ["site-a"], "allowed_regions": ["eu-west"]}})
    if profile == "reference":
        doc.update({"profile": "reference", "environment": "test", "auth": {"audience": "inv26.site-a.test"},
                    "runtime": {"adapter": "reference", "version": "1", "arch": "x86_64"},
                    "storage": {"kind": "memory", "root": "", "quota_bytes": 1 << 34},
                    "metadata": {"root": ""}})
        doc["security"] = dict(doc["security"], allow_hs256=True)
    for k, v in over.items():
        doc[k] = v
    return doc
