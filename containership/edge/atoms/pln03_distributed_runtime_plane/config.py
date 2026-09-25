"""Declarative, schema-validated runtime configuration with provenance ledger,
atomic activation, rollback and secret-safe redaction (MC-021..MC-025, MC-010).

Configuration is data, separate from code.  A candidate is validated in full
before activation; activation is a single reference swap; every revision is
recorded with author, source, digest and activation time; rollback re-activates
a previously validated revision.  Secret-looking values are refused in config
and redacted in any diagnostic rendering.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import time
from dataclasses import dataclass, fields
from threading import RLock
from typing import Any, Callable

from .resilience import Limits
from .runtime import RuntimePlaneError

CONFIG_SCHEMA = "pk.pln03.config/1"
SITE_CLASSES = ("cloud", "datacenter", "near-edge", "far-edge")
CONSISTENCY = ("strong", "read-your-writes", "eventual")
# MC-010 constraint precedence: earlier wins on conflict. Fixed by policy; not configurable.
CONSTRAINT_PRECEDENCE = ("security", "residency", "data-integrity", "slo", "cost")

SECRET_KEY_RE = re.compile(r"(secret|password|passwd|token|api[_-]?key|private[_-]?key|credential)", re.I)
SECRET_VALUE_RE = re.compile(r"(-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{10,}\.)")
REDACTED = "***REDACTED***"


class ConfigInvalid(RuntimePlaneError):
    code = "PK_CONFIG_INVALID"


DEFAULT: dict[str, Any] = {
    "schema": CONFIG_SCHEMA,
    "site": {"id": "unset", "class": "cloud", "region": "unset", "residency_zones": []},
    "consistency": "read-your-writes",
    "limits": {f.name: f.default for f in fields(Limits)},
    "degraded": {"allow_local_buffer": False, "read_only_on_partition": True},
    "tokens": {"required": True},
    "adapters": {},  # capability -> {"name": str, "residency_zone": str}
}


def canonical(cfg: dict) -> bytes:
    return json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()


def digest(cfg: dict) -> str:
    return "sha256:" + hashlib.sha256(canonical(cfg)).hexdigest()


def _walk(obj: Any, path: str = ""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, f"{path}[{i}]")
    else:
        yield path, obj


def validate(cfg: dict) -> Limits:
    """Full pre-activation validation.  Returns the typed Limits on success."""
    if not isinstance(cfg, dict) or cfg.get("schema") != CONFIG_SCHEMA:
        raise ConfigInvalid("config schema identifier missing or unsupported")
    unknown = set(cfg) - set(DEFAULT)
    if unknown:
        raise ConfigInvalid("unknown top-level config keys", keys=",".join(sorted(unknown)))
    for path, value in _walk(cfg):
        leaf = path.rsplit(".", 1)[-1]
        if SECRET_KEY_RE.search(leaf) and leaf != "required" and not path.startswith("tokens."):
            raise ConfigInvalid("config may not carry secret-named fields; use PK_SECRET references", path=path)
        if isinstance(value, str) and SECRET_VALUE_RE.search(value):
            raise ConfigInvalid("config value looks like secret material", path=path)
    site = cfg.get("site", {})
    if site.get("class") not in SITE_CLASSES:
        raise ConfigInvalid("site.class must be one of " + ",".join(SITE_CLASSES))
    if not isinstance(site.get("residency_zones", []), list):
        raise ConfigInvalid("site.residency_zones must be a list")
    if cfg.get("consistency") not in CONSISTENCY:
        raise ConfigInvalid("consistency must be one of " + ",".join(CONSISTENCY))
    lim = cfg.get("limits", {})
    known = {f.name: f for f in fields(Limits)}
    if set(lim) - set(known):
        raise ConfigInvalid("unknown limit keys", keys=",".join(sorted(set(lim) - set(known))))
    values = {}
    for name, f in known.items():
        v = lim.get(name, f.default)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0:
            raise ConfigInvalid("limits must be positive numbers", field=name)
        values[name] = type(f.default)(v)
    limits = Limits(**values)
    if limits.max_concurrency_per_tenant > limits.max_concurrency_global:
        raise ConfigInvalid("per-tenant concurrency exceeds global ceiling")
    if limits.default_deadline_s > limits.max_deadline_s:
        raise ConfigInvalid("default deadline exceeds max deadline")
    if not 0 < limits.retry_budget_ratio <= 1:
        raise ConfigInvalid("retry_budget_ratio must be in (0,1]")
    if site.get("class") == "far-edge" and not cfg.get("degraded", {}).get("allow_local_buffer"):
        pass  # permitted: far-edge without buffering simply runs read-only during partitions
    if cfg.get("tokens", {}).get("required") is not True:
        raise ConfigInvalid("capability tokens may not be disabled (security precedes all other constraints)")
    zones = set(site.get("residency_zones", []))
    for cap, ad in (cfg.get("adapters") or {}).items():
        if cap not in {"state", "messaging", "secrets", "invoke"}:
            raise ConfigInvalid("adapter binding for unknown capability", capability=cap)
        z = (ad or {}).get("residency_zone")
        if zones and z not in zones:
            raise ConfigInvalid("adapter residency zone outside site residency (residency precedes SLO/cost)",
                                capability=cap)
    return limits


def redact(obj: Any) -> Any:
    """Deep copy with secret-looking keys/values replaced (MC-025)."""
    if isinstance(obj, dict):
        return {k: (REDACTED if SECRET_KEY_RE.search(str(k)) and not isinstance(v, bool) else redact(v))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    if isinstance(obj, (bytes, bytearray)):
        return f"<{len(obj)} bytes>"
    if isinstance(obj, str) and SECRET_VALUE_RE.search(obj):
        return REDACTED
    return obj


@dataclass(frozen=True)
class Revision:
    number: int
    digest: str
    author: str
    source: str
    reason: str
    activated_at: float
    config: dict
    limits: Limits


class ConfigStore:
    """Revision store + provenance ledger + atomic activate/rollback."""

    def __init__(self, clock: Callable[[], float] = time.time,
                 on_change: Callable[[Revision, Revision | None], None] | None = None, max_revisions: int = 256):
        self._lock = RLock()
        self._revisions: list[Revision] = []
        self._active: Revision | None = None
        self.clock, self.on_change, self.max_revisions = clock, on_change, max_revisions

    @property
    def active(self) -> Revision:
        if self._active is None:
            raise ConfigInvalid("no configuration activated")
        return self._active

    def ledger(self) -> list[dict]:
        with self._lock:
            return [{"revision": r.number, "digest": r.digest, "author": r.author, "source": r.source,
                     "reason": r.reason, "activated_at": r.activated_at,
                     "active": r is self._active} for r in self._revisions]

    def activate(self, candidate: dict, *, author: str, source: str, reason: str) -> Revision:
        if not author or not source or not reason:
            raise ConfigInvalid("activation requires author, source and reason")
        cfg = copy.deepcopy(candidate)
        limits = validate(cfg)           # fail before any state changes
        with self._lock:
            number = (self._revisions[-1].number + 1) if self._revisions else 1
            rev = Revision(number, digest(cfg), author, source, reason, self.clock(), cfg, limits)
            prev = self._active
            self._revisions.append(rev)
            if len(self._revisions) > self.max_revisions:
                self._revisions = [r for r in self._revisions[-self.max_revisions:]]
            self._active = rev            # single atomic reference swap
        if self.on_change:
            self.on_change(rev, prev)
        return rev

    def rollback(self, *, to: int | None = None, author: str, reason: str) -> Revision:
        with self._lock:
            if self._active is None:
                raise ConfigInvalid("nothing to roll back")
            if to is None:
                earlier = [r for r in self._revisions if r.number < self._active.number]
                if not earlier:
                    raise ConfigInvalid("no earlier revision")
                target = earlier[-1]
            else:
                match = [r for r in self._revisions if r.number == to]
                if not match:
                    raise ConfigInvalid("unknown revision", revision=to)
                target = match[0]
        return self.activate(target.config, author=author, source=f"rollback:{target.number}:{target.digest}",
                             reason=reason)
