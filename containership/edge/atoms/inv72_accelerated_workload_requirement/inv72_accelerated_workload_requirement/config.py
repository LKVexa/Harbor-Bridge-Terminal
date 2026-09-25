"""Declarative configuration for INV-72 (C012, C032-C039).

* Profiles (``config/profiles/<tier>.json``) give the per-tier behaviour for cloud, datacenter,
  near-edge and far-edge (C012); overlays (``config/overlays/*.json``) add site/environment values
  without rebuilding the immutable code (C035).  Merge order: profile -> environment -> site.
* Every candidate is validated against PK_ACCEL_CONFIG/1 plus semantic rules *before* activation;
  any error refuses activation and leaves the active generation untouched (C034, fail closed).
* Keys or values that look like credentials are refused - secrets never enter ordinary config (C039).
* Activation is atomic: a new immutable generation replaces the old one in a single reference swap
  under a lock; readers always see one complete generation (C037).
* Each generation records provenance: digest, author, reason, source files and activation time (C036).
* ``rollback()`` restores the previous generation (operator-driven); ``activate(..., probe=fn)`` runs a
  post-activation health probe and rolls back automatically when it fails (C038).
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

from .errors import AccelError
from .schema_check import check

ROOT = Path(__file__).resolve().parent
PROFILE_DIR = ROOT / "config" / "profiles"
TIERS = ("cloud", "datacenter", "near_edge", "far_edge")
_SECRET_KEY = re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|private[_-]?key|credential)")
_SECRET_VAL = re.compile(r"(?i)(-----BEGIN [A-Z ]*PRIVATE KEY-----|\bsk-[a-z0-9-]{8,}|\bghp_[A-Za-z0-9]{20,}|"
                         r"\bAKIA[0-9A-Z]{16}\b|\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.)")


def _freeze(v: Any) -> Any:
    if isinstance(v, dict):
        return MappingProxyType({k: _freeze(x) for k, x in v.items()})
    if isinstance(v, list):
        return tuple(_freeze(x) for x in v)
    return v


def _thaw(v: Any) -> Any:
    if isinstance(v, Mapping):
        return {k: _thaw(x) for k, x in v.items()}
    if isinstance(v, tuple):
        return [_thaw(x) for x in v]
    return v


def deep_merge(base: dict, over: Mapping) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, Mapping) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def find_secrets(value: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, Mapping):
        for k, v in value.items():
            if _SECRET_KEY.search(str(k)):
                hits.append(f"{path}.{k}: credential-like key")
            hits += find_secrets(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            hits += find_secrets(v, f"{path}[{i}]")
    elif isinstance(value, str) and _SECRET_VAL.search(value):
        hits.append(f"{path}: credential-like value")
    return hits


def semantic_errors(cfg: Mapping) -> list[str]:
    errs = []
    if cfg.get("profile") in ("near_edge", "far_edge") and cfg.get("inventory_max_age_s", 0) > 3600:
        errs.append("edge profiles must bound inventory age to <= 3600 s")
    if cfg.get("require_authentication") is False and cfg.get("profile") != "far_edge":
        errs.append("require_authentication may be false only on far_edge single-tenant profile")
    per = cfg.get("quotas", {}).get("per_tenant", {})
    for t, q in per.items():
        if not isinstance(q, int) or isinstance(q, bool) or q < 0:
            errs.append(f"quota for tenant {t!r} must be a non-negative integer")
    adm = cfg.get("admission", {})
    if adm and adm.get("burst", 1) < 1:
        errs.append("admission.burst must be >= 1")
    return errs


def validate(cfg: Any) -> list[str]:
    errs = check(cfg, "PK_ACCEL_CONFIG-1")
    if isinstance(cfg, Mapping):
        errs += find_secrets(cfg)
        if not errs:
            errs += semantic_errors(cfg)
    return errs


def load_profile(tier: str) -> dict:
    if tier not in TIERS:
        raise AccelError("ACCEL_CONFIG_INVALID", f"unknown tier {tier!r}")
    return json.loads((PROFILE_DIR / f"{tier}.json").read_text(encoding="utf-8"))


def compose(tier: str, *overlays: Mapping) -> dict:
    cfg = load_profile(tier)
    for o in overlays:
        cfg = deep_merge(cfg, o)
    return cfg


def digest(cfg: Mapping) -> str:
    return hashlib.sha256(json.dumps(_thaw(cfg), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class Generation:
    number: int
    config: Mapping
    digest: str
    author: str
    reason: str
    sources: tuple
    activated_at: float
    previous: int | None = None

    def provenance(self) -> dict:
        return {"generation": self.number, "digest": self.digest, "author": self.author, "reason": self.reason,
                "sources": list(self.sources), "activated_at": self.activated_at, "previous": self.previous}


@dataclass
class ConfigStore:
    """Holds the active immutable generation and the history needed for rollback."""

    history_limit: int = 16
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _active: Generation | None = None
    _history: list = field(default_factory=list)
    _counter: int = 0
    audit: Callable[[str, dict], None] | None = None

    @property
    def active(self) -> Generation | None:
        return self._active

    def get(self) -> Mapping:
        g = self._active
        if g is None:
            raise AccelError("ACCEL_CONFIG_INVALID", "no active configuration")
        return g.config

    def activate(self, candidate: Mapping, *, author: str, reason: str, sources: tuple = (),
                 probe: Callable[[Mapping], bool] | None = None, clock: Callable[[], float] = time.time) -> Generation:
        if not isinstance(author, str) or not author.strip():
            raise AccelError("ACCEL_CONFIG_INVALID", "activation requires an author")
        cand = _thaw(candidate)
        errs = validate(cand)
        if errs:
            self._emit("config.refused", {"author": author, "errors": errs[:10]})
            raise AccelError("ACCEL_CONFIG_INVALID", "; ".join(errs[:5]), errors=errs)
        with self._lock:
            self._counter += 1
            prev = self._active
            gen = Generation(self._counter, _freeze(cand), digest(cand), author, reason, tuple(sources), clock(),
                             prev.number if prev else None)
            if prev is not None:
                self._history.append(prev)
                del self._history[:-self.history_limit]
            self._active = gen  # single reference swap = atomic
        self._emit("config.activated", gen.provenance())
        if probe is not None and not probe(gen.config):
            self.rollback(author="auto-rollback", reason=f"post-activation probe failed for generation {gen.number}")
            raise AccelError("ACCEL_CONFIG_INVALID", "post-activation probe failed; rolled back",
                             generation=gen.number)
        return gen

    def rollback(self, *, author: str, reason: str) -> Generation:
        with self._lock:
            if not self._history:
                raise AccelError("ACCEL_CONFIG_INVALID", "no previous generation to roll back to")
            target = self._history.pop()
            self._counter += 1
            gen = Generation(self._counter, target.config, target.digest, author, reason,
                             target.sources + (f"rollback-of:{self._active.number if self._active else None}",),
                             time.time(), self._active.number if self._active else None)
            self._active = gen
        self._emit("config.rolled_back", gen.provenance())
        return gen

    def _emit(self, action: str, detail: dict) -> None:
        if self.audit:
            self.audit(action, detail)
