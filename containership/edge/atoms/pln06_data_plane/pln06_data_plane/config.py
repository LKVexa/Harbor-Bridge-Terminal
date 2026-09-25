"""#4 deployment contexts, #16 declarative configuration, #17 durable history/rollback/canary."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import threading
import time
from collections.abc import Callable, Mapping
from pathlib import Path

from .data_plane import InvalidRequest

CONFIG_SCHEMA = "PK_DATA_PLANE_CONFIG/1"

# #4 behaviour per deployment context, including intermittent/offline semantics.
ALL_LOC = ["in_process", "same_node", "same_host_vm", "remote"]
DEPLOYMENT_CONTEXTS: dict[str, dict[str, object]] = {
    "cloud": {"offline_ok": False, "max_policy_age_s": 300, "allowed_localities": ALL_LOC,
              "bulk_adapters": ["rdma", "network-rpc", "shared-memory"], "store_and_forward": False},
    "datacenter": {"offline_ok": False, "max_policy_age_s": 300, "allowed_localities": ALL_LOC,
                   "bulk_adapters": ["rdma", "network-rpc", "shared-memory"], "store_and_forward": False},
    "near_edge": {"offline_ok": True, "max_policy_age_s": 3600, "allowed_localities": ALL_LOC,
                  "bulk_adapters": ["network-rpc", "shared-memory"], "store_and_forward": True},
    "far_edge": {"offline_ok": True, "max_policy_age_s": 86400, "allowed_localities": ["in_process", "same_node", "same_host_vm"],
                 "bulk_adapters": ["shared-memory"], "store_and_forward": True,
                 "note": "remote transfers queue locally (bounded) until connectivity; residency still enforced offline"},
}

SECURE_DEFAULTS: dict[str, object] = {
    "schema": CONFIG_SCHEMA,
    "context": "datacenter",
    "inflight_limit": 4,
    "per_tenant_inflight_limit": 2,
    "require_authentication": True,
    "require_signed_labels": True,
    "require_digest": True,
    "tls_required_for_remote": True,
    "audit_required": True,
    "retry": {"max_attempts": 4, "base_delay": 0.05, "max_delay": 2.0, "deadline_s": 30.0},
    "stall_timeout_s": 60.0,
    "telemetry": {"log_level": "INFO", "trace_sample_rate": 0.1, "max_label_cardinality": 1000},
    "residency": {},
}

_TYPES: dict[str, type | tuple[type, ...]] = {
    "schema": str, "context": str, "inflight_limit": int, "per_tenant_inflight_limit": int,
    "require_authentication": bool, "require_signed_labels": bool, "require_digest": bool,
    "tls_required_for_remote": bool, "audit_required": bool, "retry": dict, "stall_timeout_s": (int, float),
    "telemetry": dict, "residency": dict,
}
# Security switches that an environment overlay may never weaken outside "dev".
_NO_WEAKEN = ("require_authentication", "require_signed_labels", "require_digest",
              "tls_required_for_remote", "audit_required")


def _merge(base: dict[str, object], overlay: Mapping[str, object]) -> dict[str, object]:
    out = copy.deepcopy(base)
    for k, v in overlay.items():
        if isinstance(v, Mapping) and isinstance(out.get(k), dict) and k != "residency":
            out[k] = _merge(out[k], v)  # type: ignore[arg-type]
        else:
            out[k] = copy.deepcopy(v)
    return out


def validate(cfg: Mapping[str, object], *, environment: str = "prod") -> dict[str, object]:
    unknown = set(cfg) - set(_TYPES)
    if unknown:
        raise InvalidRequest("unknown configuration keys", keys=sorted(unknown))
    for key, typ in _TYPES.items():
        if key not in cfg:
            raise InvalidRequest("missing configuration key", key=key)
        val = cfg[key]
        if isinstance(val, bool) and typ is not bool:
            raise InvalidRequest("wrong type", key=key)
        if not isinstance(val, typ):
            raise InvalidRequest("wrong type", key=key, expected=str(typ))
    if cfg["schema"] != CONFIG_SCHEMA:
        raise InvalidRequest("unsupported config schema", schema=cfg["schema"])
    if cfg["context"] not in DEPLOYMENT_CONTEXTS:
        raise InvalidRequest("unknown deployment context", context=cfg["context"])
    if not 1 <= int(cfg["inflight_limit"]) <= 100_000:  # type: ignore[call-overload]
        raise InvalidRequest("inflight_limit out of range")
    if not 1 <= int(cfg["per_tenant_inflight_limit"]) <= int(cfg["inflight_limit"]):  # type: ignore[call-overload]
        raise InvalidRequest("per_tenant_inflight_limit out of range")
    if environment != "dev":
        weakened = [k for k in _NO_WEAKEN if cfg[k] is not True]
        if weakened:
            raise InvalidRequest("security controls may not be disabled outside dev", keys=weakened)
    for site, classes in cfg["residency"].items():  # type: ignore[attr-defined, union-attr]
        if not isinstance(site, str) or not isinstance(classes, list) or not all(isinstance(c, str) for c in classes):
            raise InvalidRequest("residency must map site -> list[str]", site=site)
    return dict(cfg)


def load(base: Mapping[str, object] | str | os.PathLike[str], overlays: list[Mapping[str, object]] = (),  # type: ignore[assignment]
         *, environment: str = "prod") -> dict[str, object]:
    """Load secure defaults <- base <- overlays (in order), then validate."""
    if not isinstance(base, Mapping):
        base = json.loads(Path(base).read_text(encoding="utf-8"))
    cfg = _merge(SECURE_DEFAULTS, base)  # type: ignore[arg-type]
    for ov in overlays:
        cfg = _merge(cfg, ov)
    return validate(cfg, environment=environment)


def fingerprint(cfg: Mapping[str, object]) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()


class ConfigController:
    """Durable revision history, staged rollout (canary -> full), rollback and emergency disable.

    ``apply_fn(cfg)`` activates a config on the target (e.g. ``DataPlane.replace_residency``);
    ``probe()`` returns True if the canary is healthy.  Failure rolls back automatically.
    """

    def __init__(self, history_path: str | os.PathLike[str], apply_fn: Callable[[Mapping[str, object]], None],
                 *, environment: str = "prod", clock: Callable[[], float] = time.time):
        self._path = Path(history_path)
        self._apply = apply_fn
        self._env = environment
        self._clock = clock
        self._lock = threading.Lock()
        self.history: list[dict[str, object]] = []
        if self._path.exists():
            self.history = [json.loads(line) for line in self._path.read_text(encoding="utf-8").splitlines() if line]
        self.emergency_disabled = False

    def _record(self, entry: dict[str, object]) -> None:
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        self.history.append(entry)

    @property
    def active(self) -> dict[str, object] | None:
        for entry in reversed(self.history):
            if entry["status"] in ("active", "rolled_back_to"):
                return entry
        return None

    def propose(self, cfg: Mapping[str, object], *, revision: str, author: str, approver: str,
                canary: Callable[[Mapping[str, object]], None] | None = None,
                probe: Callable[[], bool] = lambda: True) -> dict[str, object]:
        if author == approver:
            raise InvalidRequest("config change requires an independent approver")
        valid = validate(cfg, environment=self._env)
        if any(e["revision"] == revision for e in self.history):
            raise InvalidRequest("revision already used", revision=revision)
        with self._lock:
            base = {"revision": revision, "author": author, "approver": approver, "ts": self._clock(),
                    "sha256": fingerprint(valid), "config": valid}
            if canary is not None:
                canary(valid)
                if not probe():
                    self._record({**base, "status": "canary_failed"})
                    prev = self.active
                    if prev is not None:
                        canary(prev["config"])  # type: ignore[arg-type]
                    raise InvalidRequest("canary probe failed; change not promoted", revision=revision)
            self._apply(valid)
            self._record({**base, "status": "active"})
            return base

    def rollback(self, *, to_revision: str | None = None, author: str) -> dict[str, object]:
        with self._lock:
            candidates = [e for e in self.history if e["status"] in ("active", "rolled_back_to")]
            if to_revision is None:
                if len(candidates) < 2:
                    raise InvalidRequest("no previous revision to roll back to")
                target = candidates[-2]
            else:
                found = [e for e in candidates if e["revision"] == to_revision]
                if not found:
                    raise InvalidRequest("unknown revision", revision=to_revision)
                target = found[-1]
            self._apply(target["config"])  # type: ignore[arg-type]
            entry = {**target, "status": "rolled_back_to", "author": author, "ts": self._clock()}
            self._record(entry)
            return entry

    def emergency_disable(self, *, author: str, reason: str) -> None:
        self.emergency_disabled = True
        self._record({"revision": f"EMERGENCY-{int(self._clock())}", "author": author, "status": "emergency_disable",
                      "reason": reason, "ts": self._clock(), "config": {}, "sha256": ""})
