"""Configuration and policy plane (G12-F067..F074).

``SCHEMA`` is the single authoritative, machine-readable schema (version
``g12-config/1.x``): every field has a type, unit, range/enum, default,
security classification, reload semantics and deprecation marker.  Prose
documentation and validation fixtures are GENERATED from it
(``render_markdown`` / ``fixtures``), so they cannot drift.

Rules:
* major version must be 1; a newer minor is accepted only for documented
  extension keys under ``x-`` (unknown non-extension fields are rejected);
* semantic validation runs before activation (cross-field timeout
  relationships, endpoint syntax, credential fields must be ``secret://``
  references, trust-sensitive fields fail closed);
* artifact defaults + environment overlay + site overlay are merged in that
  order; the effective config gets a SHA-256 fingerprint;
* ``ConfigManager.apply`` = preflight -> stage -> health check -> commit, or
  automatic rollback to last-known-good; concurrent reloads are serialised;
  every activation records provenance (source, author, version, generation,
  activation time, approval/waiver refs, digest);
* traversal mechanisms are enabled/disabled per environment/zone by policy;
  relay cost metadata per region; feature flags carry owner + expiry and an
  expired flag evaluates to its safe default.
"""
from __future__ import annotations

import copy
import hashlib
import ipaddress
import json
import threading
import time
from dataclasses import dataclass, field

SCHEMA_VERSION = "1.1"
MECHANISMS = ("direct", "hole-punch", "relay", "tcp", "tls", "quic", "pcp", "natpmp", "upnp")

SCHEMA: dict[str, dict] = {
    "strategies": {"type": "list[str]", "enum": ["direct", "hole-punch", "relay"], "default": ["direct", "hole-punch", "relay"],
                   "unit": None, "class": "operational", "reload": "hot", "doc": "escalation order; relay must be last"},
    "stun_servers": {"type": "list[endpoint]", "default": [], "min_items": 0, "max_items": 8, "class": "operational",
                     "reload": "hot", "doc": "host:port STUN servers (>= 2 independent servers recommended)"},
    "turn_servers": {"type": "list[endpoint]", "default": [], "max_items": 8, "class": "operational", "reload": "hot",
                     "doc": "host:port TURN servers"},
    "turn_credential": {"type": "secret_ref", "default": None, "class": "secret", "reload": "hot",
                        "doc": "secret:// reference to TURN credentials; literal secrets are rejected"},
    "attempt_timeout_s": {"type": "float", "min": 0.1, "max": 30.0, "default": 3.0, "unit": "s", "class": "operational",
                          "reload": "hot", "doc": "hard deadline per strategy attempt"},
    "overall_timeout_s": {"type": "float", "min": 0.5, "max": 120.0, "default": 10.0, "unit": "s", "class": "operational",
                          "reload": "hot", "doc": "deadline for a whole connect() escalation"},
    "probe_freshness_s": {"type": "int", "min": 5, "max": 600, "default": 30, "unit": "s", "class": "operational",
                          "reload": "hot", "doc": "success evidence older than this is stale"},
    "backoff_ceiling_s": {"type": "int", "min": 1, "max": 3600, "default": 60, "unit": "s", "class": "operational",
                          "reload": "hot", "doc": "retry backoff ceiling"},
    "require_attestation": {"type": "bool", "default": True, "class": "trust", "reload": "restart",
                            "doc": "trust-sensitive: may only be false in environment 'lab'"},
    "require_e2e_encryption": {"type": "bool", "default": True, "class": "trust", "reload": "restart",
                               "doc": "trust-sensitive: may only be false in environment 'lab'"},
    "egress_allow": {"type": "list[cidr_ports]", "default": [], "class": "trust", "reload": "hot",
                     "doc": "deny-by-default egress allow list: 'cidr:lo-hi'"},
    "mechanisms": {"type": "dict[mechanism,bool]", "default": {"direct": True, "hole-punch": True, "relay": True, "tcp": True,
                                                               "tls": True, "quic": False, "pcp": False, "natpmp": False,
                                                               "upnp": False},
                   "class": "operational", "reload": "hot", "doc": "per-environment enable/disable of traversal mechanisms"},
    "relay_regions": {"type": "list[region]", "default": [], "class": "operational", "reload": "hot",
                      "doc": "relay regions with jurisdiction and cost_per_gb metadata"},
    "relay_budget_gb_month": {"type": "float", "min": 0.0, "max": 1e6, "default": 100.0, "unit": "GB/month",
                              "class": "cost", "reload": "hot", "doc": "hard relay budget"},
    "feature_flags": {"type": "dict[flag]", "default": {}, "class": "operational", "reload": "hot",
                      "doc": "flags with owner, expires (unix s) and safe_default"},
    "environment": {"type": "str", "enum": ["lab", "dev", "staging", "production"], "default": "production",
                    "class": "operational", "reload": "restart", "doc": "deployment environment"},
    "legacy_probe_interval": {"type": "int", "min": 1, "max": 600, "default": 10, "unit": "s", "class": "operational",
                              "reload": "hot", "deprecated": "use health.interval (removed in 2.0)",
                              "doc": "deprecated alias"},
}


class ConfigError(ValueError):
    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


def defaults() -> dict:
    return {"version": SCHEMA_VERSION, **{k: copy.deepcopy(v["default"]) for k, v in SCHEMA.items()}}


def _endpoint(v) -> bool:
    if not isinstance(v, str) or v.count(":") < 1:
        return False
    host, _, port = v.rpartition(":")
    if not port.isdigit() or not 0 < int(port) < 65536 or not host or len(host) > 253:
        return False
    try:
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        return all(p and len(p) < 64 and p.replace("-", "").isalnum() for p in host.split("."))


def validate(cfg: dict) -> list[str]:
    problems: list[str] = []
    ver = str(cfg.get("version", ""))
    major, _, minor = ver.partition(".")
    if major != SCHEMA_VERSION.split(".")[0]:
        return [f"unsupported schema major version {ver!r}"]
    newer_minor = minor.isdigit() and int(minor) > int(SCHEMA_VERSION.split(".")[1])
    for k in cfg:
        if k == "version":
            continue
        if k not in SCHEMA:
            if k.startswith("x-") and newer_minor:
                continue
            problems.append(f"unknown field {k!r}")
    for k, spec in SCHEMA.items():
        if k not in cfg:
            continue
        v, t = cfg[k], spec["type"]
        if t == "float" and (isinstance(v, bool) or not isinstance(v, (int, float))):
            problems.append(f"{k}: expected number")
            continue
        if t == "int" and (isinstance(v, bool) or not isinstance(v, int)):
            problems.append(f"{k}: expected integer")
            continue
        if t == "bool" and not isinstance(v, bool):
            problems.append(f"{k}: expected boolean")
            continue
        if t in ("float", "int") and not spec["min"] <= v <= spec["max"]:
            problems.append(f"{k}: {v} outside [{spec['min']}, {spec['max']}] {spec.get('unit') or ''}".strip())
        if t == "str" and v not in spec["enum"]:
            problems.append(f"{k}: {v!r} not in {spec['enum']}")
        if t == "list[str]":
            if not isinstance(v, list) or any(x not in spec["enum"] for x in v) or len(set(v)) != len(v):
                problems.append(f"{k}: invalid list")
        if t == "list[endpoint]":
            if not isinstance(v, list) or len(v) > spec.get("max_items", 64) or not all(_endpoint(x) for x in v):
                problems.append(f"{k}: every entry must be host:port")
        if t == "secret_ref" and v is not None and not (isinstance(v, str) and v.startswith("secret://")):
            problems.append(f"{k}: literal credential rejected; use a secret:// reference")
        if t == "list[cidr_ports]":
            for e in v if isinstance(v, list) else [None]:
                try:
                    cidr, ports = str(e).rsplit(":", 1)
                    ipaddress.ip_network(cidr)
                    lo, hi = (int(x) for x in ports.split("-"))
                    if not 0 < lo <= hi < 65536:
                        raise ValueError
                except Exception:
                    problems.append(f"{k}: bad entry {e!r}")
        if t == "dict[mechanism,bool]":
            if not isinstance(v, dict) or any(m not in MECHANISMS or not isinstance(b, bool) for m, b in v.items()):
                problems.append(f"{k}: must map known mechanisms to booleans")
        if t == "list[region]":
            for r in v if isinstance(v, list) else [None]:
                if not isinstance(r, dict) or not {"name", "jurisdiction", "cost_per_gb"} <= set(r) or \
                        not isinstance(r.get("cost_per_gb"), (int, float)) or r["cost_per_gb"] < 0:
                    problems.append(f"{k}: region needs name, jurisdiction, cost_per_gb >= 0")
        if t == "dict[flag]":
            for name, f in (v.items() if isinstance(v, dict) else []):
                if not isinstance(f, dict) or not {"owner", "expires", "safe_default", "value"} <= set(f):
                    problems.append(f"{k}.{name}: flags need owner, expires, value, safe_default")
    # semantic / cross-field checks only run on a well-typed document (a type error
    # must be reported, never crash the validator - found by the config fuzzer)
    if problems:
        return problems
    eff = {**defaults(), **cfg}
    if eff["attempt_timeout_s"] * max(1, len(eff["strategies"])) > eff["overall_timeout_s"] + 1e-9:
        problems.append("attempt_timeout_s x strategies exceeds overall_timeout_s")
    if eff["strategies"] and "relay" in eff["strategies"] and eff["strategies"][-1] != "relay":
        problems.append("relay must be the last strategy")
    if eff["environment"] != "lab":
        for k in ("require_attestation", "require_e2e_encryption"):
            if eff[k] is not True:
                problems.append(f"{k}: trust-sensitive field may only be disabled in environment 'lab'")
    if eff["mechanisms"].get("relay") and "relay" in eff["strategies"] and not eff["turn_servers"] \
            and eff["environment"] == "production":
        problems.append("relay enabled in production without turn_servers")
    if eff["turn_servers"] and not eff["turn_credential"]:
        problems.append("turn_servers configured without turn_credential reference")
    if len(eff["stun_servers"]) == 1 and eff["environment"] == "production":
        problems.append("production needs >= 2 independent stun_servers")
    return problems


def merge(*layers: dict) -> dict:
    out: dict = {}
    for layer in layers:
        for k, v in layer.items():
            if isinstance(v, dict) and isinstance(out.get(k), dict) and k != "feature_flags":
                out[k] = {**out[k], **v}
            else:
                out[k] = copy.deepcopy(v)
    return out


def fingerprint(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def flag(cfg: dict, name: str, now: float) -> bool:
    f = cfg.get("feature_flags", {}).get(name)
    if f is None:
        return False
    return f["safe_default"] if now >= f["expires"] else f["value"]


def mechanism_enabled(cfg: dict, mechanism: str, *, zone: str | None = None, zone_policy: dict | None = None) -> bool:
    base = cfg.get("mechanisms", {}).get(mechanism, False)
    if zone and zone_policy and mechanism in zone_policy.get(zone, {}):
        return base and zone_policy[zone][mechanism]
    return base


@dataclass
class Activation:
    generation: int
    digest: str
    source: str
    author: str
    version: str
    activated_wall: float
    approvals: list[str]
    waivers: list[str]
    outcome: str


@dataclass
class ConfigManager:
    artifact_defaults: dict = field(default_factory=defaults)
    health_check: object = None                 # fn(effective) -> bool
    clock: object = time.time
    active: dict | None = None
    last_known_good: dict | None = None
    generation: int = 0
    history: list[Activation] = field(default_factory=list)
    configs: dict = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def preview(self, env_overlay: dict, site_overlay: dict) -> tuple[dict, list[str]]:
        eff = merge(self.artifact_defaults, env_overlay, site_overlay)
        return eff, validate(eff)

    def apply(self, env_overlay: dict, site_overlay: dict, *, source: str, author: str,
              approvals: list[str] | None = None, waivers: list[str] | None = None) -> Activation:
        with self._lock:                                 # concurrent reloads are serialised
            eff, problems = self.preview(env_overlay, site_overlay)
            digest = fingerprint(eff)
            gen = self.generation + 1
            if problems:
                act = Activation(gen, digest, source, author, str(eff.get("version")), self.clock(),
                                 approvals or [], waivers or [], "rejected: " + "; ".join(problems))
                self.history.append(act)
                raise ConfigError(problems)
            previous = self.active
            self.active = eff                             # staged
            healthy = True
            if self.health_check is not None:
                try:
                    healthy = bool(self.health_check(eff))
                except Exception:
                    healthy = False
            if not healthy:
                self.active = previous                    # automatic rollback
                act = Activation(gen, digest, source, author, str(eff.get("version")), self.clock(),
                                 approvals or [], waivers or [], "rolled_back: health check failed")
                self.history.append(act)
                raise ConfigError(["health check failed; rolled back to last-known-good"])
            self.generation = gen
            self.last_known_good = eff
            self.configs[gen] = eff
            for old_gen in sorted(self.configs)[:-8]:
                del self.configs[old_gen]
            act = Activation(gen, digest, source, author, str(eff.get("version")), self.clock(),
                             approvals or [], waivers or [], "active")
            self.history.append(act)
            return act

    def rollback(self, *, author: str) -> Activation:
        """Re-activate the previous good generation (kept for the last 8 activations)."""
        with self._lock:
            good = [a for a in self.history if a.outcome.startswith("active") and a.generation in self.configs]
            if len(good) < 2:
                raise ConfigError(["no previous generation to roll back to"])
            target = good[-2]
            self.active = self.last_known_good = copy.deepcopy(self.configs[target.generation])
            self.generation += 1
            self.configs[self.generation] = self.active
            act = Activation(self.generation, target.digest, "rollback", author, target.version, self.clock(), [], [],
                             f"active (rollback to generation {target.generation})")
            self.history.append(act)
            return act


def render_markdown() -> str:
    """Schema documentation generated from SCHEMA (no hand-written prose to drift)."""
    lines = [f"# GAP-12 configuration schema `g12-config/{SCHEMA_VERSION}`", "",
             "_Generated by `wan.config.render_markdown()`; do not edit by hand._", "",
             "| field | type | range / enum | default | unit | class | reload | notes |",
             "|---|---|---|---|---|---|---|---|"]
    for k, s in SCHEMA.items():
        rng = f"{s['min']}..{s['max']}" if "min" in s else (", ".join(s["enum"]) if "enum" in s else "")
        note = s["doc"] + (f" **DEPRECATED:** {s['deprecated']}" if s.get("deprecated") else "")
        lines.append(f"| `{k}` | {s['type']} | {rng} | `{json.dumps(s['default'])}` | {s.get('unit') or ''} | "
                     f"{s['class']} | {s['reload']} | {note} |")
    lines += ["", "Unknown fields are rejected unless they start with `x-` and the document declares a newer "
              "minor version. A different major version is rejected."]
    return "\n".join(lines) + "\n"


def fixtures() -> dict[str, tuple[dict, bool]]:
    """Validation fixtures derived from SCHEMA: (config, expected_valid)."""
    out: dict[str, tuple[dict, bool]] = {"defaults-lab": ({**defaults(), "environment": "lab"}, True)}
    for k, s in SCHEMA.items():
        if "min" in s:
            out[f"{k}-below-min"] = ({**defaults(), "environment": "lab", k: s["min"] - (1 if s["type"] == "int" else 0.001)}, False)
            out[f"{k}-above-max"] = ({**defaults(), "environment": "lab", k: s["max"] + 1}, False)
        if "enum" in s and s["type"] == "str":
            out[f"{k}-bad-enum"] = ({**defaults(), k: "not-a-member"}, False)
    out["unknown-field"] = ({**defaults(), "environment": "lab", "surprise": 1}, False)
    out["future-major"] = ({**defaults(), "version": "2.0"}, False)
    out["newer-minor-extension"] = ({**defaults(), "environment": "lab", "version": "1.9", "x-vendor": 1}, True)
    return out
