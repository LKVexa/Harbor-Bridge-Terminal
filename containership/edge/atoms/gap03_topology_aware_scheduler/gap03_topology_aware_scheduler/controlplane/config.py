"""MC-015 - Production configuration subsystem (GAP03-CFG/1).

Precedence (lowest -> highest): built-in defaults < signed config document <
environment overlay (``GAP03_CFG__section__key``) < command-line overrides.
The *whole* candidate is validated, then activated atomically as an immutable
snapshot with monotonic generation, digest, activation time, actor and source.
Rollback re-activates a stored known-good generation.  Secrets appear only as
``secret://`` references and are redacted from dumps.
"""
from __future__ import annotations

import copy
import threading
import time
from dataclasses import dataclass
from types import MappingProxyType

from . import canonical
from .durable import DurableStore
from .errors import SchedulerError

SCHEMA_VERSION = 2
# field: (type, default, min, max, unit, restart_required)
SCHEMA = {
    "scoring": {"weight_locality": ("int", 1000, 0, 10_000, "ppm_weight", False),
                "weight_latency": ("int", 0, 0, 10_000, "ppm_weight", False),
                "weight_gravity": ("int", 0, 0, 10_000, "ppm_weight", False),
                "weight_demand": ("int", 0, 0, 10_000, "ppm_weight", False)},
    "limits": {"max_candidates": ("int", 10_000, 1, 100_000, "candidates", False),
               "max_concurrent_commits": ("int", 16, 1, 1024, "requests", True)},
    "ttl": {"inventory_s": ("int", 300, 10, 3600, "seconds", False), "gravity_s": ("int", 900, 10, 7200, "seconds", False),
            "lease_s": ("int", 10, 2, 60, "seconds", True)},
    "safety": {"fail_open_scoring": ("bool", False, None, None, "flag", False),
               "require_attestation": ("bool", True, None, None, "flag", False)},
    "secrets": {"signing_key": ("secret", "secret://kms/gap03/signing", None, None, "ref", True)},
    "features": {"latency_refinement": ("bool", False, None, None, "gate", False),
                 "multi_objective": ("bool", False, None, None, "gate", False)},
}
DEPRECATED = {"scoring.weight_cost": "removed in v2 (use weight_latency)"}
EXCLUSIVE = [("features.latency_refinement", "safety.fail_open_scoring")]
POLICY = {"max_total_weight": 20_000}


def defaults() -> dict:
    return {s: {k: v[1] for k, v in f.items()} for s, f in SCHEMA.items()}


def migrate_v1(doc: dict) -> dict:
    doc = copy.deepcopy(doc)
    sc = doc.get("scoring", {})
    if "weight_cost" in sc:
        sc["weight_latency"] = sc.pop("weight_cost")
    doc["schema_version"] = 2
    return doc


def validate(doc: dict) -> dict:
    doc = copy.deepcopy(doc)
    ver = doc.pop("schema_version", SCHEMA_VERSION)
    if ver == 1:
        doc = migrate_v1(dict(doc, schema_version=1))
        doc.pop("schema_version")
    elif ver != SCHEMA_VERSION:
        raise SchedulerError("UNSUPPORTED_VERSION", f"config schema v{ver}")
    out = defaults()
    for section, fields in doc.items():
        if section not in SCHEMA:
            raise SchedulerError("INVALID_ARGUMENT", f"unknown config section {section}")
        for key, value in fields.items():
            if f"{section}.{key}" in DEPRECATED:
                raise SchedulerError("INVALID_ARGUMENT", f"deprecated field {section}.{key}: {DEPRECATED[f'{section}.{key}']}")
            spec = SCHEMA[section].get(key)
            if spec is None:
                raise SchedulerError("INVALID_ARGUMENT", f"unknown field {section}.{key}")
            typ, _, lo, hi, _, _ = spec
            if typ == "int":
                if isinstance(value, bool) or not isinstance(value, int) or not lo <= value <= hi:
                    raise SchedulerError("INVALID_ARGUMENT", f"{section}.{key} out of range [{lo},{hi}]")
            elif typ == "bool":
                if not isinstance(value, bool):
                    raise SchedulerError("INVALID_ARGUMENT", f"{section}.{key} must be boolean")
            elif typ == "secret":
                if not isinstance(value, str) or not value.startswith("secret://"):
                    raise SchedulerError("INVALID_ARGUMENT", f"{section}.{key} must be a secret:// reference, never plaintext")
            out[section][key] = value
    for a, b in EXCLUSIVE:
        sa, ka = a.split(".")
        sb, kb = b.split(".")
        if out[sa][ka] and out[sb][kb]:
            raise SchedulerError("INVALID_ARGUMENT", f"{a} and {b} are mutually exclusive")
    if sum(out["scoring"].values()) > POLICY["max_total_weight"]:
        raise SchedulerError("INVALID_ARGUMENT", "total scoring weight exceeds policy")
    if sum(out["scoring"].values()) == 0:
        raise SchedulerError("INVALID_ARGUMENT", "at least one scoring weight must be non-zero")
    return out


def merge(*layers: dict) -> dict:
    out: dict = {}
    for layer in layers:
        for s, f in (layer or {}).items():
            if s == "schema_version":
                out[s] = f
                continue
            out.setdefault(s, {}).update(f)
    return out


def env_overlay(environ: dict) -> dict:
    out: dict = {}
    for k, v in sorted(environ.items()):
        if not k.startswith("GAP03_CFG__"):
            continue
        parts = k[len("GAP03_CFG__"):].lower().split("__")
        if len(parts) != 2:
            raise SchedulerError("INVALID_ARGUMENT", f"malformed overlay variable {k}")
        s, key = parts
        spec = SCHEMA.get(s, {}).get(key)
        if spec is None:
            raise SchedulerError("INVALID_ARGUMENT", f"unknown overlay field {s}.{key}")
        if spec[0] == "int":
            try:
                v = int(v)
            except ValueError:
                raise SchedulerError("INVALID_ARGUMENT", f"{k} not an integer") from None
        elif spec[0] == "bool":
            if v not in ("true", "false"):
                raise SchedulerError("INVALID_ARGUMENT", f"{k} must be true/false")
            v = v == "true"
        out.setdefault(s, {})[key] = v
    return out


def redacted(cfg) -> dict:
    return {s: {k: ("<secret-ref>" if SCHEMA[s][k][0] == "secret" else v) for k, v in f.items()} for s, f in cfg.items()}


def diff(a: dict, b: dict) -> list[dict]:
    out = []
    for s in SCHEMA:
        for k in SCHEMA[s]:
            if a[s][k] != b[s][k]:
                out.append({"field": f"{s}.{k}", "from": a[s][k] if SCHEMA[s][k][0] != "secret" else "<ref>",
                            "to": b[s][k] if SCHEMA[s][k][0] != "secret" else "<ref>", "restart_required": SCHEMA[s][k][5]})
    return out


@dataclass(frozen=True)
class ConfigSnapshot:
    generation: int
    digest: str
    activated_at: int
    actor: str
    source: str
    values: MappingProxyType

    def get(self, dotted: str):
        s, k = dotted.split(".")
        return self.values[s][k]


class ConfigStore(DurableStore):
    KIND = "config"

    def initial_state(self):
        return {"generation": 0, "active": None, "history": {}}

    def apply(self, state, op):
        if op["expected_generation"] != state["generation"]:
            raise SchedulerError("STALE_STATE", "concurrent configuration update")
        validate(op["values"])
        state["generation"] += 1
        g = state["generation"]
        state["history"][str(g)] = {"values": op["values"], "digest": canonical.digest(op["values"]), "actor": op["actor"],
                                    "source": op["source"], "activated_at": op["now"], "rollback_of": op.get("rollback_of")}
        state["active"] = str(g)
        return g


class ConfigManager:
    def __init__(self, store: ConfigStore, *, audit=None, clock=time.time, trust=None, metrics=None):
        self.store, self.audit, self.clock, self.trust, self.metrics = store, audit, clock, trust, metrics
        self._lock = threading.Lock()
        self._snap = None
        if store.state["active"] is None:
            self.activate(defaults(), actor="bootstrap", source="builtin-defaults", expected_generation=0)
        else:
            self._refresh()

    def _refresh(self):
        h = self.store.state["history"][self.store.state["active"]]
        vals = MappingProxyType({s: MappingProxyType(dict(f)) for s, f in h["values"].items()})
        self._snap = ConfigSnapshot(int(self.store.state["active"]), h["digest"], h["activated_at"], h["actor"], h["source"], vals)

    @property
    def current(self) -> ConfigSnapshot:
        return self._snap  # single reference swap: workers always see a whole, coherent snapshot

    def build(self, *, document: dict | None = None, envelope: dict | None = None, environ: dict | None = None,
              cli: dict | None = None) -> dict:
        if document is not None and self.trust is not None:
            from .identity import verify_artifact
            verify_artifact(self.trust, envelope or {}, document, kind="config")
        return validate(merge(defaults(), document or {}, env_overlay(environ or {}), cli or {}))

    def dry_run(self, candidate: dict) -> dict:
        new = validate(candidate)
        cur = {s: dict(f) for s, f in self._snap.values.items()}
        d = diff(cur, new)
        risky = [x for x in d if x["field"].startswith(("safety.", "ttl.")) or x["restart_required"]]
        return {"valid": True, "diff": d, "risky": risky, "digest": canonical.digest(new)}

    def activate(self, values: dict, *, actor: str, source: str, expected_generation: int | None = None,
                 rollback_of: int | None = None, acknowledge_risk: bool = False, principal: dict | None = None) -> ConfigSnapshot:
        """Privileged: requires ``config.write`` once bootstrapped (principal None only for the bootstrap default)."""
        if self._snap is not None:
            if principal is None or "config.write" not in principal.get("perms", set()):
                if self.audit:
                    self.audit.append(actor=actor, action="config.activate", target="config", result="denied")
                raise SchedulerError("PERMISSION_DENIED", "config.write required")
            actor = principal["sub"]
        with self._lock:
            values = validate(values)
            if self._snap is not None:
                risky = self.dry_run(values)["risky"]
                if any(x["field"].startswith("safety.") for x in risky) and not acknowledge_risk:
                    raise SchedulerError("PERMISSION_DENIED", "safety-setting change requires explicit risk acknowledgement")
            gen = self.store.state["generation"] if expected_generation is None else expected_generation
            before = self._snap.digest if self._snap else None
            g = self.store.submit({"type": "activate", "values": values, "actor": actor, "source": source,
                                   "expected_generation": gen, "now": int(self.clock()), "rollback_of": rollback_of})
            self._refresh()
            if self.metrics:
                self.metrics.inc("gap03_config_activations_total", kind="rollback" if rollback_of else "activate")
            if self.audit:
                self.audit.append(actor=actor, action="config.rollback" if rollback_of else "config.activate", target="config",
                                  result="ok", generation=g, detail={"before_digest": before, "after_digest": self._snap.digest,
                                                                     "source": source})
            return self._snap

    def rollback(self, generation: int, *, actor: str = "", principal: dict | None = None) -> ConfigSnapshot:
        h = self.store.state["history"].get(str(generation))
        if h is None:
            raise SchedulerError("INVALID_ARGUMENT", "unknown generation")
        return self.activate(h["values"], actor=actor, source=f"rollback:{generation}", rollback_of=generation,
                             acknowledge_risk=True, principal=principal)
