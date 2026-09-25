"""MC-17 - Declarative configuration, overlays, provenance, atomic activation, rollback.

``PK_PLANE_CONFIG/1``::

    {"schema": "PK_PLANE_CONFIG/1",
     "provenance": {"author": "...", "source": "git:...@sha", "version": "2026.09.23-1"},
     "admission": {...AdmissionPolicy fields...},
     "catalogue": {"max_age_seconds": 300, "max_offline_seconds": 3600},
     "constraints": {"platform": {...}, "tenants": {"acme": {...}}},
     "entitlements": {"acme": ["state", "tracing"]}}

Overlays (base -> environment -> site) deep-merge mappings; lists replace.
Activation validates first, then atomically writes ``active.json`` and moves the
previous active config to ``lkg.json`` (last known good). ``rollback()``
restores LKG. Secure defaults: every unspecified value comes from
``DEFAULTS``; unknown keys are refused; inline secrets are refused.
"""
from __future__ import annotations

import copy
import json
import os
import pathlib
import time
from typing import Any, Mapping

from .admission import AdmissionPolicy
from .errors import PlaneError
from .policy import Constraints
from .resolver import _digest
from .secret_refs import check_no_inline_secrets
from .store import _atomic_write

CONFIG_SCHEMA = "PK_PLANE_CONFIG/1"
DEFAULTS: dict[str, Any] = {
    "schema": CONFIG_SCHEMA,
    "provenance": {"author": "unset", "source": "unset", "version": "0"},
    "admission": dict(AdmissionPolicy().__dict__),
    "catalogue": {"max_age_seconds": 300.0, "max_offline_seconds": 3600.0},
    "constraints": {"platform": {"min_tier": "standard"}, "tenants": {}},
    "entitlements": {},
}
_BOUNDS = {
    "admission.max_payload_bytes": (1024, 16 * 1024 * 1024),
    "admission.tenant_rate_per_second": (0.1, 10_000),
    "admission.tenant_burst": (1, 100_000),
    "admission.tenant_max_concurrency": (1, 1024),
    "admission.global_max_concurrency": (1, 65_536),
    "admission.shed_threshold": (0.1, 1.0),
    "admission.max_tenants_tracked": (1, 1_000_000),
    "catalogue.max_age_seconds": (1, 86_400),
    "catalogue.max_offline_seconds": (0, 7 * 86_400),
}


def deep_merge(base: Mapping[str, Any], overlay: Mapping[str, Any], path: str = "$") -> dict:
    out = copy.deepcopy(dict(base))
    for k, v in overlay.items():
        if isinstance(v, Mapping) and isinstance(out.get(k), Mapping):
            out[k] = deep_merge(out[k], v, f"{path}.{k}")
        else:
            out[k] = copy.deepcopy(v)
    return out


def validate(doc: Mapping[str, Any]) -> dict:
    def bad(field: str, msg: str = "invalid configuration") -> PlaneError:
        return PlaneError(msg, code="CONFIG_INVALID", details={"field": field})
    if not isinstance(doc, Mapping):
        raise bad("$")
    if set(doc) - set(DEFAULTS):
        raise bad(sorted(set(doc) - set(DEFAULTS))[0], "unknown configuration key")
    cfg = deep_merge(DEFAULTS, doc)
    if cfg["schema"] != CONFIG_SCHEMA:
        raise bad("schema")
    check_no_inline_secrets(cfg)
    prov = cfg["provenance"]
    if set(prov) != {"author", "source", "version"} or not all(isinstance(v, str) and v for v in prov.values()):
        raise bad("provenance")
    if set(cfg["admission"]) != set(DEFAULTS["admission"]):
        raise bad("admission")
    if set(cfg["catalogue"]) != set(DEFAULTS["catalogue"]):
        raise bad("catalogue")
    for dotted, (lo, hi) in _BOUNDS.items():
        sect, key = dotted.split(".")
        v = cfg[sect][key]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
            raise bad(dotted)
    if cfg["admission"]["tenant_max_concurrency"] > cfg["admission"]["global_max_concurrency"]:
        raise bad("admission.tenant_max_concurrency")
    if set(cfg["constraints"]) != {"platform", "tenants"}:
        raise bad("constraints")
    Constraints.from_doc(cfg["constraints"]["platform"])
    for t, c in cfg["constraints"]["tenants"].items():
        Constraints.from_doc(c)
    for t, caps in cfg["entitlements"].items():
        if not isinstance(caps, list) or not all(isinstance(c, str) for c in caps):
            raise bad(f"entitlements.{t}")
    return cfg


def compose(base: Mapping[str, Any], *overlays: Mapping[str, Any]) -> dict:
    cfg = dict(base)
    for o in overlays:
        cfg = deep_merge(cfg, o)
    return validate(cfg)


class ConfigManager:
    def __init__(self, root: str | os.PathLike, clock=time.time) -> None:
        self.root = pathlib.Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._clock = clock

    @property
    def active_path(self) -> pathlib.Path:
        return self.root / "active.json"

    @property
    def lkg_path(self) -> pathlib.Path:
        return self.root / "lkg.json"

    def active(self) -> dict:
        if not self.active_path.exists():
            return {"config": validate({}), "digest": _digest(validate({})), "activated_at": None}
        rec = json.loads(self.active_path.read_text("utf-8"))
        if _digest(rec["config"]) != rec["digest"]:
            raise PlaneError("active configuration digest mismatch", code="CONFIG_INVALID", details={"field": "active"})
        return rec

    def activate(self, doc: Mapping[str, Any]) -> dict:
        cfg = validate(doc)  # pre-activation validation: nothing is written on failure
        rec = {"config": cfg, "digest": _digest(cfg), "activated_at": self._clock()}
        if self.active_path.exists():
            _atomic_write(self.lkg_path, json.loads(self.active_path.read_text("utf-8")))
        _atomic_write(self.active_path, rec)
        return rec

    def rollback(self) -> dict:
        if not self.lkg_path.exists():
            raise PlaneError("no last-known-good configuration", code="CONFIG_INVALID", details={"field": "lkg"})
        lkg = json.loads(self.lkg_path.read_text("utf-8"))
        validate(lkg["config"])
        _atomic_write(self.active_path, lkg)
        return lkg
