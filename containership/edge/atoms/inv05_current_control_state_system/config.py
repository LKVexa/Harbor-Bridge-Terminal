"""Declarative, typed configuration (MC-028).

* Every setting has a type, default, constraint, description, sensitivity and
  whether changing it requires a restart (MC-028-01, -06).
* Secrets are never values: sensitive settings only accept ``secret://name``
  references resolved by :class:`security.SecretProvider` (MC-028-02).
* Overlays merge deterministically: ``defaults < base < environment < site <
  overrides`` (MC-028-03).  Unknown keys are errors.
* The whole effective config is validated before activation, then frozen with a
  SHA-256 content hash and a provenance list of which layer set each key
  (MC-028-04/05).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from .errors import InvalidArgument
from .limits import Limits


@dataclass(frozen=True)
class Setting:
    type: type
    default: Any
    description: str
    min: float | None = None
    max: float | None = None
    choices: tuple[Any, ...] | None = None
    sensitive: bool = False
    restart_required: bool = False


SCHEMA: dict[str, Setting] = {
    "node.name": Setting(str, "inv05-0", "Member name; stable across restarts", restart_required=True),
    "node.site": Setting(str, "site-a", "Site this instance serves", restart_required=True),
    "node.site_epoch": Setting(int, 1, "Fencing epoch for this site's authority (GAP-05)", min=1),
    "listen.host": Setting(str, "127.0.0.1", "Bind address", restart_required=True),
    "listen.port": Setting(int, 2479, "Bind port", min=0, max=65535, restart_required=True),
    "tls.enabled": Setting(bool, True, "Require mTLS on the listener", restart_required=True),
    "tls.cert_file": Setting(str, "", "Server certificate chain (PEM)", restart_required=True),
    "tls.key_file": Setting(str, "secret://tls-key-path", "Server private key path reference", sensitive=True,
                            restart_required=True),
    "tls.ca_file": Setting(str, "", "Trust bundle for client certs", restart_required=True),
    "auth.trust_domain": Setting(str, "inv05.local", "SPIFFE trust domain accepted"),
    "auth.token_key": Setting(str, "secret://token-key", "HMAC key ref for bearer tokens", sensitive=True),
    "auth.allow_tokens": Setting(bool, False, "Accept bearer tokens (loopback/break-glass only)"),
    "auth.role_map_file": Setting(str, "", "JSON {spiffe-uri|purpose: [roles]}; empty = client->writer, admin->operator"),
    "storage.data_dir": Setting(str, "./data", "WAL/snapshot directory", restart_required=True),
    "storage.durability": Setting(str, "fsync", "fsync|group", choices=("fsync", "group"), restart_required=True),
    "storage.group_commit": Setting(int, 32, "Records per fsync in group mode", min=1, max=4096),
    "storage.checkpoint_every_records": Setting(int, 50_000, "WAL records between snapshots", min=100),
    "storage.encrypt_at_rest": Setting(bool, True, "AES-256-GCM seal WAL/snapshots", restart_required=True),
    "storage.data_key": Setting(str, "secret://data-key", "Data-key ref (unwrapped by KMS)", sensitive=True,
                                restart_required=True),
    "audit.path": Setting(str, "./data/audit.log", "Audit log path", restart_required=True),
    "audit.key": Setting(str, "secret://audit-key", "Audit HMAC key ref", sensitive=True, restart_required=True),
    "compaction.retain_revisions": Setting(int, 100_000, "Revisions retained behind head", min=100),
    "compaction.min_interval_s": Setting(float, 300.0, "Minimum seconds between compactions", min=1),
    "compaction.safety_margin_revisions": Setting(int, 1_000, "Extra retained revisions for lagging watchers", min=0),
    "watch.progress_interval_s": Setting(float, 5.0, "Progress frame interval", min=0.1, max=60),
    "watch.idle_timeout_s": Setting(float, 300.0, "Close idle streams after", min=5),
    "limits.max_inflight_requests": Setting(int, 512, "Concurrency limit", min=1),
    "limits.rate_per_identity_rps": Setting(float, 1000.0, "Per-identity rate", min=1),
    "limits.max_watches_per_identity": Setting(int, 64, "Watches per identity", min=1),
    "limits.max_watch_queue_events": Setting(int, 10_000, "Per-watch queue bound", min=10),
    "deadlines.default_ms": Setting(int, 5_000, "Default request deadline", min=10, max=120_000),
    "deadlines.max_ms": Setting(int, 60_000, "Maximum accepted deadline", min=100, max=600_000),
    "telemetry.trace_ratio": Setting(float, 0.05, "Head sampling ratio", min=0, max=1),
    "telemetry.log_level": Setting(str, "INFO", "Log level", choices=("DEBUG", "INFO", "WARN", "ERROR")),
    "telemetry.max_series_per_metric": Setting(int, 64, "Cardinality cap", min=1, max=10_000),
    "lease.max_ttl_s": Setting(int, 3600, "Maximum lease TTL", min=2),
}

LAYERS = ("defaults", "base", "environment", "site", "overrides")


@dataclass(frozen=True)
class EffectiveConfig:
    values: Mapping[str, Any]
    provenance: Mapping[str, str]
    sha256: str

    def __getitem__(self, k: str) -> Any:
        return self.values[k]

    def redacted(self) -> dict[str, Any]:
        return {k: ("[REF]" if SCHEMA[k].sensitive else v) for k, v in self.values.items()}

    def limits(self) -> Limits:
        return Limits(max_inflight_requests=self["limits.max_inflight_requests"],
                      rate_per_identity_rps=self["limits.rate_per_identity_rps"],
                      max_watches_per_identity=self["limits.max_watches_per_identity"],
                      max_watch_queue_events=self["limits.max_watch_queue_events"],
                      max_lease_ttl_s=self["lease.max_ttl_s"])

    def restart_required_diff(self, other: "EffectiveConfig") -> list[str]:
        return sorted(k for k in self.values if SCHEMA[k].restart_required and self.values[k] != other.values[k])


def _check(key: str, val: Any) -> Any:
    s = SCHEMA[key]
    if s.type is float and isinstance(val, int) and not isinstance(val, bool):
        val = float(val)
    if not isinstance(val, s.type) or (s.type is int and isinstance(val, bool)):
        raise InvalidArgument(f"{key}: expected {s.type.__name__}", field=key)
    if s.min is not None and val < s.min or s.max is not None and val > s.max:
        raise InvalidArgument(f"{key}: out of range [{s.min}, {s.max}]", field=key)
    if s.choices and val not in s.choices:
        raise InvalidArgument(f"{key}: must be one of {s.choices}", field=key)
    if s.sensitive and not (isinstance(val, str) and val.startswith("secret://")):
        raise InvalidArgument(f"{key}: sensitive settings accept only secret:// references", field=key)
    return val


def build(**layers: Mapping[str, Any]) -> EffectiveConfig:
    unknown_layers = set(layers) - set(LAYERS[1:])
    if unknown_layers:
        raise InvalidArgument(f"unknown config layers {sorted(unknown_layers)}", field="layers")
    values = {k: s.default for k, s in SCHEMA.items()}
    prov = {k: "defaults" for k in SCHEMA}
    for layer in LAYERS[1:]:
        for k, v in (layers.get(layer) or {}).items():
            if k not in SCHEMA:
                raise InvalidArgument(f"unknown setting {k!r} in {layer}", field=k)
            values[k] = v
            prov[k] = layer
    values = {k: _check(k, v) for k, v in values.items()}
    # cross-field validation
    if values["deadlines.default_ms"] > values["deadlines.max_ms"]:
        raise InvalidArgument("deadlines.default_ms exceeds deadlines.max_ms", field="deadlines.default_ms")
    if values["tls.enabled"] and values["listen.host"] not in ("127.0.0.1", "::1", "localhost") and \
            not (values["tls.cert_file"] and values["tls.ca_file"]):
        raise InvalidArgument("non-loopback listener requires tls.cert_file and tls.ca_file", field="tls")
    if not values["tls.enabled"] and values["listen.host"] not in ("127.0.0.1", "::1", "localhost"):
        raise InvalidArgument("TLS may only be disabled on loopback", field="tls.enabled")
    digest = hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()
    return EffectiveConfig(values, prov, digest)


def load_layers(paths: Mapping[str, str]) -> EffectiveConfig:
    """Load JSON overlay files ``{layer: path}`` and build the effective config."""
    layers = {}
    for layer, path in paths.items():
        with open(path, encoding="utf-8") as fh:
            layers[layer] = json.load(fh)
    return build(**layers)


def schema_document() -> dict[str, Any]:
    return {k: {"type": s.type.__name__, "default": s.default, "description": s.description, "min": s.min,
                "max": s.max, "choices": list(s.choices) if s.choices else None, "sensitive": s.sensitive,
                "restart_required": s.restart_required} for k, s in SCHEMA.items()}
