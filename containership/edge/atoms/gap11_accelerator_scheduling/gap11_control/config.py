"""GAP11-P1-29 declarative configuration + GAP11-P1-32 privileged-change audit hook.

Precedence (lowest -> highest): built-in defaults < site file < environment overlay
< explicit operator override. Each effective key records its provenance. The whole
candidate is validated before activation; activation swaps one immutable object
(atomic for all readers); the previous good config is kept for rollback.
"""
from __future__ import annotations

import copy
import threading
from typing import Any, Callable

from .common import ControlError, digest

SCHEMA: dict[str, dict[str, Any]] = {
    "lease_ttl_s":            {"type": float, "min": 5.0, "max": 3600.0, "default": 30.0},
    "lease_grace_s":          {"type": float, "min": 0.0, "max": 3600.0, "default": 15.0},
    "leader_ttl_s":           {"type": float, "min": 2.0, "max": 120.0, "default": 10.0},
    "leader_safety_margin_s": {"type": float, "min": 0.5, "max": 60.0, "default": 2.0},
    "idempotency_retention_s": {"type": float, "min": 60.0, "max": 30 * 86400.0, "default": 86400.0},
    "queue_capacity":         {"type": int, "min": 1, "max": 100_000, "default": 256},
    "max_inflight":           {"type": int, "min": 1, "max": 4096, "default": 32},
    "scrub_deadline_s":       {"type": float, "min": 1.0, "max": 3600.0, "default": 120.0},
    "thermal_max_age_s":      {"type": float, "min": 0.5, "max": 600.0, "default": 5.0},
    "allow_same_tenant_dirty_reuse": {"type": bool, "default": True},
    "dangerous_allow_unattested_devices": {"type": bool, "default": False, "dangerous": True},
    "dangerous_skip_scrub": {"type": bool, "default": False, "dangerous": True, "forbidden": True},
    "audit_signing_key_ref":  {"type": str, "default": "secretref://gap11-audit", "secret_ref": True},
    "authn_key_ref":          {"type": str, "default": "secretref://gap11-authn", "secret_ref": True},
    "feature_gates":          {"type": dict, "default": {"gang_allocation": False, "preemption": False}},
}
LAYERS = ("default", "site", "environment", "override")


def validate(candidate: dict[str, Any], *, opt_in_dangerous: set[str] = frozenset()) -> list[str]:
    errs = []
    for k, v in candidate.items():
        spec = SCHEMA.get(k)
        if spec is None:
            errs.append(f"{k}: unknown key")
            continue
        t = spec["type"]
        if t is float and isinstance(v, int) and not isinstance(v, bool):
            v = float(v)
        if not isinstance(v, t) or (t in (int, float) and isinstance(v, bool)):
            errs.append(f"{k}: expected {t.__name__}")
            continue
        if "min" in spec and v < spec["min"] or "max" in spec and v > spec["max"]:
            errs.append(f"{k}: out of range [{spec.get('min')}, {spec.get('max')}]")
        if spec.get("secret_ref") and not v.startswith("secretref://"):
            errs.append(f"{k}: secrets must be references (secretref://...), never inline values")
        if spec.get("forbidden") and v:
            errs.append(f"{k}: forbidden in every environment")
        if spec.get("dangerous") and v and k not in opt_in_dangerous:
            errs.append(f"{k}: dangerous setting requires explicit opt-in")
        if k == "feature_gates" and any(not isinstance(x, bool) for x in v.values()):
            errs.append("feature_gates: values must be bool")
    merged = {**{k: s["default"] for k, s in SCHEMA.items()}, **candidate}
    if not errs and merged["leader_safety_margin_s"] >= merged["leader_ttl_s"]:
        errs.append("leader_safety_margin_s must be < leader_ttl_s")
    return errs


class ConfigManager:
    def __init__(self, *, audit: Callable[[dict[str, Any]], None] | None = None) -> None:
        self._lock = threading.Lock()
        self.audit = audit or (lambda e: None)
        self.layers: dict[str, dict[str, Any]] = {"default": {k: s["default"] for k, s in SCHEMA.items()}}
        self.active, self.provenance = self._effective(self.layers)
        self.last_good = (copy.deepcopy(self.active), dict(self.provenance), copy.deepcopy(self.layers))
        self.generation = 1

    @staticmethod
    def _effective(layers: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], dict[str, str]]:
        eff, prov = {}, {}
        for name in LAYERS:
            for k, v in layers.get(name, {}).items():
                eff[k] = float(v) if SCHEMA.get(k, {}).get("type") is float and isinstance(v, int) and not isinstance(v, bool) else v
                prov[k] = name
        return eff, prov

    def digest(self) -> str:
        return digest(self.active)

    def apply(self, layer: str, values: dict[str, Any], *, actor: str, opt_in_dangerous: set[str] = frozenset(),
              activate_hook: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
        if layer not in LAYERS or layer == "default":
            raise ControlError("CONFIG_INVALID", f"cannot write layer {layer!r}")
        with self._lock:
            cand_layers = copy.deepcopy(self.layers)
            cand_layers[layer] = {**cand_layers.get(layer, {}), **values}
            eff, prov = self._effective(cand_layers)
            errs = validate({k: v for k, v in eff.items()}, opt_in_dangerous=opt_in_dangerous)
            if errs:
                self.audit({"action": "CONFIG_REJECTED", "actor": actor, "layer": layer, "errors": errs})
                raise ControlError("CONFIG_INVALID", "; ".join(errs))
            previous = (self.active, self.provenance, self.layers)
            try:
                if activate_hook:
                    activate_hook(eff)  # dependent subsystems; any failure -> rollback
            except Exception as exc:
                self.audit({"action": "CONFIG_ROLLBACK", "actor": actor, "layer": layer, "error": type(exc).__name__})
                raise ControlError("CONFIG_INVALID", "activation failed; previous configuration kept") from exc
            self.last_good = (copy.deepcopy(previous[0]), dict(previous[1]), copy.deepcopy(previous[2]))
            self.active, self.provenance, self.layers = eff, prov, cand_layers
            self.generation += 1
            self.audit({"action": "CONFIG_APPLIED", "actor": actor, "layer": layer, "keys": sorted(values),
                        "digest": self.digest(), "generation": self.generation})
            return {"digest": self.digest(), "generation": self.generation}

    def rollback(self, *, actor: str) -> dict[str, Any]:
        with self._lock:
            self.active, self.provenance, self.layers = copy.deepcopy(self.last_good[0]), dict(self.last_good[1]), copy.deepcopy(self.last_good[2])
            self.generation += 1
            self.audit({"action": "CONFIG_ROLLBACK", "actor": actor, "digest": self.digest()})
            return {"digest": self.digest(), "generation": self.generation}
