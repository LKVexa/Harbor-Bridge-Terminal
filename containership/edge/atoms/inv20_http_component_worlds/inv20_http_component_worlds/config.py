"""Configuration subsystem (checklist component 8).

Versioned schema ``INV20_CONFIG/1`` with secure defaults (outgoing disabled, empty allow-list,
bounded limits and timeouts, no secret logging), strict validation (unknown keys rejected),
deterministic overlays that can only *narrow* authority, provenance with a canonical digest,
staged → validated → atomic activation, known-good rollback (automatic on failed readiness,
or operator-driven and audited), and secret references instead of secret values.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
import json
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from .errors import Inv20Error
from .protocol import parse_authority

SCHEMA = "INV20_CONFIG/1"
SUPPORTED_SCHEMAS = ("INV20_CONFIG/1",)
OVERLAY_ORDER = ("base", "environment", "site", "tenant", "workload")   # later = lower trust


class ConfigInvalid(Inv20Error):
    code = "E_CONFIG_INVALID"


class ConfigAuthority(Inv20Error):
    code = "E_CONFIG_AUTHORITY"


DEFAULTS: Dict[str, Any] = {
    "schema": SCHEMA,
    "outgoing_enabled": False,
    "capability_ref": None,                 # e.g. "secret://inv20/cap-signing"
    "allowed_authorities": [],              # ["api.example.com:443"]
    "allowed_address_classes": ["public"],
    "allow_ip_literals": False,
    "limits": {
        "body_bytes": 1 << 20, "header_fields": 100, "header_bytes": 16384,
        "trailer_fields": 16, "trailer_bytes": 4096,
        "max_concurrency": 64, "per_tenant_concurrency": 16, "queue_depth": 128,
        "stream_chunks_in_flight": 8, "max_fanout": 8, "max_connections": 32,
        "per_destination_connections": 8,
    },
    "timeouts_ms": {"request": 30000, "dns": 2000, "connect": 3000, "response_head": 10000,
                    "body_idle": 10000, "drain": 15000},
    "retry": {"max_attempts": 3, "base_ms": 50, "max_backoff_ms": 2000, "budget_ms": 5000,
              "retry_after_cap_ms": 5000},
    "observability": {"log_level": "info", "log_bodies": False, "trace_sample_rate": 0.01},
    "features": {},
}

_BOUNDS = {
    ("limits", "body_bytes"): (0, 1 << 30), ("limits", "header_fields"): (1, 1000),
    ("limits", "header_bytes"): (256, 1 << 20), ("limits", "trailer_fields"): (0, 256),
    ("limits", "trailer_bytes"): (0, 1 << 16), ("limits", "max_concurrency"): (1, 100000),
    ("limits", "per_tenant_concurrency"): (1, 100000), ("limits", "queue_depth"): (0, 1000000),
    ("limits", "stream_chunks_in_flight"): (1, 4096), ("limits", "max_fanout"): (0, 1024),
    ("limits", "max_connections"): (1, 100000), ("limits", "per_destination_connections"): (1, 10000),
    ("timeouts_ms", "request"): (1, 3600000), ("timeouts_ms", "dns"): (1, 60000),
    ("timeouts_ms", "connect"): (1, 60000), ("timeouts_ms", "response_head"): (1, 600000),
    ("timeouts_ms", "body_idle"): (1, 600000), ("timeouts_ms", "drain"): (0, 600000),
    ("retry", "max_attempts"): (1, 10), ("retry", "base_ms"): (1, 60000),
    ("retry", "max_backoff_ms"): (1, 600000), ("retry", "budget_ms"): (0, 3600000),
    ("retry", "retry_after_cap_ms"): (0, 600000),
}
_ADDRESS_CLASSES = {"public", "private", "loopback", "link_local", "reserved"}
_SECRET_HINTS = ("secret", "password", "token", "key", "credential")


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(obj: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(obj).encode()).hexdigest()


def _check_keys(obj: dict, ref: dict, path: str) -> None:
    for k in obj:
        if k not in ref:
            raise ConfigInvalid(f"unknown key {path}{k}")
        if isinstance(ref[k], dict) and k != "features":
            if not isinstance(obj[k], dict):
                raise ConfigInvalid(f"{path}{k} must be an object")
            _check_keys(obj[k], ref[k], f"{path}{k}.")


def _walk_secrets(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if any(h in k.lower() for h in _SECRET_HINTS) and k != "capability_ref":
                if v is not None and not (isinstance(v, str) and v.startswith("secret://")):
                    raise ConfigInvalid(f"{path}{k}: secrets must be secret:// references")
            _walk_secrets(v, f"{path}{k}.")


def validate(cfg: dict) -> dict:
    """Full validation; returns the normalised config. Never partially accepts."""
    if not isinstance(cfg, dict) or not cfg:
        raise ConfigInvalid("empty or non-object configuration")
    if cfg.get("schema") not in SUPPORTED_SCHEMAS:
        raise ConfigInvalid(f"unsupported schema {cfg.get('schema')!r}")
    _check_keys(cfg, DEFAULTS, "")
    merged = _deep_merge(copy.deepcopy(DEFAULTS), cfg)
    if not isinstance(merged["outgoing_enabled"], bool) or not isinstance(merged["allow_ip_literals"], bool):
        raise ConfigInvalid("boolean fields must be booleans")
    for (sec, key), (lo, hi) in _BOUNDS.items():
        v = merged[sec][key]
        if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
            raise ConfigInvalid(f"{sec}.{key} out of range [{lo},{hi}]")
    auths = merged["allowed_authorities"]
    if not isinstance(auths, list):
        raise ConfigInvalid("allowed_authorities must be a list")
    norm = []
    for a in auths:
        try:
            p = parse_authority(a)
        except Inv20Error:
            raise ConfigInvalid(f"bad authority {a!r}") from None
        norm.append(p.render())
    merged["allowed_authorities"] = sorted(set(norm))
    cls_ = merged["allowed_address_classes"]
    if not isinstance(cls_, list) or not set(cls_) <= _ADDRESS_CLASSES:
        raise ConfigInvalid("allowed_address_classes invalid")
    # Cross-field invariants.
    if merged["allowed_authorities"] and not merged["outgoing_enabled"]:
        raise ConfigInvalid("allowed_authorities requires outgoing_enabled")
    if merged["outgoing_enabled"] and not merged["capability_ref"]:
        raise ConfigInvalid("outgoing_enabled requires capability_ref")
    ref = merged["capability_ref"]
    if ref is not None and not (isinstance(ref, str) and ref.startswith("secret://")):
        raise ConfigInvalid("capability_ref must be a secret:// reference")
    if merged["limits"]["per_tenant_concurrency"] > merged["limits"]["max_concurrency"]:
        raise ConfigInvalid("per_tenant_concurrency exceeds max_concurrency")
    if merged["retry"]["base_ms"] > merged["retry"]["max_backoff_ms"]:
        raise ConfigInvalid("retry.base_ms exceeds max_backoff_ms")
    if merged["observability"]["log_bodies"] is not False:
        raise ConfigInvalid("log_bodies must remain false in the production profile")
    _walk_secrets(merged)
    return merged


def _deep_merge(base: dict, over: dict) -> dict:
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = _deep_merge(base[k], v)
        else:
            base[k] = copy.deepcopy(v)
    return base


def apply_overlays(base: dict, overlays: List[Tuple[str, dict]]) -> dict:
    """Deterministic precedence (OVERLAY_ORDER); lower-trust layers may only narrow authority."""
    current = validate(base)
    for level, _ in overlays:
        if level not in OVERLAY_ORDER[1:]:
            raise ConfigInvalid(f"unknown overlay level {level}")
    ranked = sorted(overlays, key=lambda o: OVERLAY_ORDER.index(o[0]))
    for level, over in ranked:
        if "schema" in over or "capability_ref" in over:
            raise ConfigAuthority(f"{level} overlay may not change schema/capability_ref")
        cand = validate(_deep_merge(copy.deepcopy(current), over))
        if cand["outgoing_enabled"] and not current["outgoing_enabled"]:
            raise ConfigAuthority(f"{level} overlay enables outgoing HTTP")
        if not set(cand["allowed_authorities"]) <= set(current["allowed_authorities"]):
            raise ConfigAuthority(f"{level} overlay widens allowed_authorities")
        if not set(cand["allowed_address_classes"]) <= set(current["allowed_address_classes"]):
            raise ConfigAuthority(f"{level} overlay widens address classes")
        if cand["allow_ip_literals"] and not current["allow_ip_literals"]:
            raise ConfigAuthority(f"{level} overlay enables IP literals")
        for (sec, key) in _BOUNDS:
            if sec == "limits" and cand[sec][key] > current[sec][key]:
                raise ConfigAuthority(f"{level} overlay raises {sec}.{key}")
        current = cand
    return current


@dataclass(frozen=True)
class Provenance:
    revision: int
    author: str
    approver: Optional[str]
    source_uri: str
    created_at: float
    activated_at: Optional[float]
    digest: str


@dataclass
class ConfigStore:
    """Stage → validate → atomic activate; known-good history; rollback; audit hook."""

    audit: Callable[[str, dict], None] = lambda action, data: None
    clock: Callable[[], float] = time.time
    require_approval: bool = True
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _active: Optional[Tuple[dict, Provenance]] = None
    _history: List[Tuple[dict, Provenance]] = field(default_factory=list)
    _staged: Optional[Tuple[dict, Provenance]] = None
    _revision: int = 0

    @property
    def active(self) -> Optional[dict]:
        return copy.deepcopy(self._active[0]) if self._active else None

    @property
    def provenance(self) -> Optional[Provenance]:
        return self._active[1] if self._active else None

    def stage(self, cfg: dict, author: str, source_uri: str, approver: Optional[str] = None) -> Provenance:
        norm = validate(cfg)
        if self.require_approval and norm["outgoing_enabled"] and not approver:
            raise ConfigInvalid("enabling outgoing HTTP requires an approver identity")
        with self._lock:
            self._revision += 1
            prov = Provenance(self._revision, author, approver, source_uri, self.clock(), None, digest(norm))
            self._staged = (norm, prov)
        self.audit("config.staged", {"revision": prov.revision, "digest": prov.digest, "author": author})
        return prov

    def activate(self, readiness: Callable[[dict], bool] = lambda c: True) -> Provenance:
        with self._lock:
            if self._staged is None:
                raise ConfigInvalid("nothing staged")
            cfg, prov = self._staged
            self._staged = None
            previous = self._active
            prov = Provenance(prov.revision, prov.author, prov.approver, prov.source_uri, prov.created_at,
                              self.clock(), prov.digest)
            self._active = (cfg, prov)      # single reference swap == atomic activation
        ok = False
        try:
            ok = bool(readiness(copy.deepcopy(cfg)))
        except Exception:
            ok = False
        if not ok:
            with self._lock:
                self._active = previous
            self.audit("config.auto_rollback", {"failed_revision": prov.revision,
                                                "restored": previous[1].revision if previous else None})
            raise ConfigInvalid(f"revision {prov.revision} failed readiness; rolled back")
        with self._lock:
            if previous:
                self._history.append(previous)
        self.audit("config.activated", {"revision": prov.revision, "digest": prov.digest})
        return prov

    def rollback(self, operator: str) -> Provenance:
        with self._lock:
            if not self._history:
                raise ConfigInvalid("no known-good revision to roll back to")
            self._active = self._history.pop()
            prov = self._active[1]
        self.audit("config.rollback", {"operator": operator, "revision": prov.revision})
        return prov

    def export(self) -> dict:
        """Operator export: never resolves secret references."""
        cfg = self.active or {}
        return {"config": cfg, "provenance": self.provenance.__dict__ if self.provenance else None}


def bootstrap_default() -> ConfigStore:
    """Deterministic known-good bootstrap: secure defaults, egress off."""
    store = ConfigStore()
    store.stage(dict(DEFAULTS), author="bootstrap", source_uri="builtin:DEFAULTS")
    store.activate()
    return store
