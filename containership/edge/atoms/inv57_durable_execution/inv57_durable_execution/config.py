"""Declarative configuration: schema, secure defaults, overlays, provenance,
atomic activation and rollback (MC-21, MC-22, MC-23, MC-24, MC-25, MC-26 partial).

Configuration is JSON.  Unknown keys are rejected.  Secret values are never
accepted inline: a field whose name ends in ``_secret_ref`` must be a
``secretref://provider/path`` reference.  Every activation appends a
hash-chained provenance record; rollback re-activates a prior generation by
digest and is itself recorded.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import time
from typing import Any, Mapping

from .errors import ConfigRejected

CONFIG_SCHEMA = "INV57_CONFIG/1"

# name -> (type, default, (min, max) | allowed set | None)
SCHEMA: dict[str, tuple[type, Any, Any]] = {
    "max_history_events": (int, 100_000, (2, 10_000_000)),
    "lease_ttl_seconds": (float, 30.0, (1.0, 3600.0)),
    "activity_timeout_seconds": (float, 60.0, (0.1, 86_400.0)),
    "retry_max_attempts": (int, 3, (1, 20)),
    "retry_base_delay_seconds": (float, 0.2, (0.001, 60.0)),
    "retry_max_delay_seconds": (float, 10.0, (0.01, 600.0)),
    "admission_max_inflight": (int, 256, (1, 1_000_000)),
    "admission_per_tenant_inflight": (int, 64, (1, 1_000_000)),
    "circuit_failure_threshold": (int, 5, (1, 1000)),
    "circuit_reset_seconds": (float, 30.0, (0.1, 3600.0)),
    "in_doubt_policy": (str, "halt", {"halt"}),  # the only safe policy; no auto-retry option exists
    "telemetry_payload_capture": (bool, False, None),  # secure default: never capture payloads
    "state_backend": (str, "sqlite", {"sqlite", "inv50"}),
    "state_path": (str, "inv57-history.db", None),
    "state_encryption_key_secret_ref": (str, "", None),
    "environment": (str, "dev", {"dev", "test", "staging", "prod"}),
    "site": (str, "default", None),
}

_PROD_REQUIRED = {"state_encryption_key_secret_ref"}


def defaults() -> dict[str, Any]:
    return {k: v[1] for k, v in SCHEMA.items()}


def validate(doc: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(doc, Mapping):
        raise ConfigRejected("configuration root must be an object")
    unknown = set(doc) - set(SCHEMA)
    if unknown:
        raise ConfigRejected(f"unknown configuration keys: {sorted(unknown)}")
    out = defaults()
    for key, value in doc.items():
        typ, _, rule = SCHEMA[key]
        if typ is float and isinstance(value, int) and not isinstance(value, bool):
            value = float(value)
        if type(value) is not typ:
            raise ConfigRejected(f"{key} must be {typ.__name__}")
        if isinstance(rule, tuple) and not (rule[0] <= value <= rule[1]):
            raise ConfigRejected(f"{key}={value} outside [{rule[0]}, {rule[1]}]")
        if isinstance(rule, set) and value not in rule:
            raise ConfigRejected(f"{key} must be one of {sorted(rule)}")
        if key.endswith("_secret_ref") and value and not value.startswith("secretref://"):
            raise ConfigRejected(f"{key} must be a secretref:// reference, never an inline secret")
        out[key] = value
    if out["retry_base_delay_seconds"] > out["retry_max_delay_seconds"]:
        raise ConfigRejected("retry_base_delay_seconds exceeds retry_max_delay_seconds")
    if out["admission_per_tenant_inflight"] > out["admission_max_inflight"]:
        raise ConfigRejected("per-tenant inflight exceeds global inflight")
    if out["environment"] == "prod":
        missing = [k for k in _PROD_REQUIRED if not out[k]]
        if missing:
            raise ConfigRejected(f"prod requires {missing}")
        if out["telemetry_payload_capture"]:
            raise ConfigRejected("payload capture is forbidden in prod")
    return out


def merge_overlays(base: Mapping[str, Any], *overlays: Mapping[str, Any]) -> dict[str, Any]:
    """Later overlays win key-by-key; the result is validated as a whole."""
    merged = dict(base)
    for ov in overlays:
        merged.update(ov)
    return validate(merged)


def digest(cfg: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class ConfigManager:
    """Atomic activation with a hash-chained provenance ledger persisted to disk."""

    def __init__(self, directory: str) -> None:
        self.dir = directory
        os.makedirs(directory, exist_ok=True)
        self._ledger_path = os.path.join(directory, "config-ledger.jsonl")
        self._active_path = os.path.join(directory, "active.json")
        self.ledger = self._read_ledger()

    def _read_ledger(self) -> list[dict]:
        if not os.path.exists(self._ledger_path):
            return []
        rows, prev = [], "0" * 64
        with open(self._ledger_path, encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                body = {k: v for k, v in row.items() if k != "record_digest"}
                if row["prev"] != prev or row["record_digest"] != digest(body):
                    raise ConfigRejected("configuration provenance ledger is corrupted")
                prev = row["record_digest"]
                rows.append(row)
        return rows

    @property
    def generation(self) -> int:
        return self.ledger[-1]["generation"] if self.ledger else 0

    def active(self) -> dict[str, Any]:
        if not os.path.exists(self._active_path):
            return defaults()
        with open(self._active_path, encoding="utf-8") as fh:
            doc = json.load(fh)
        cfg = validate(doc["config"])
        if digest(cfg) != doc["digest"]:
            raise ConfigRejected("active configuration digest mismatch")
        return cfg

    def _snapshot(self, cfg_digest: str) -> str:
        return os.path.join(self.dir, f"gen-{cfg_digest[:16]}.json")

    def activate(self, doc: Mapping[str, Any], *, actor: str, reason: str,
                 action: str = "activate") -> dict[str, Any]:
        cfg = validate(doc)                                  # validate BEFORE any write
        d = digest(cfg)
        payload = json.dumps({"schema": CONFIG_SCHEMA, "config": cfg, "digest": d},
                             sort_keys=True, indent=1)
        with open(self._snapshot(d), "w", encoding="utf-8") as fh:
            fh.write(payload)
        fd, tmp = tempfile.mkstemp(dir=self.dir)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self._active_path)                  # atomic swap
        body = {"generation": self.generation + 1, "action": action, "config_digest": d,
                "actor": actor, "reason": reason[:256], "at": round(time.time(), 3),
                "prev": self.ledger[-1]["record_digest"] if self.ledger else "0" * 64}
        row = {**body, "record_digest": digest(body)}
        with open(self._ledger_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        self.ledger.append(row)
        return cfg

    def rollback(self, to_digest: str, *, actor: str, reason: str) -> dict[str, Any]:
        if not any(r["config_digest"] == to_digest for r in self.ledger):
            raise ConfigRejected("rollback target was never activated")
        with open(self._snapshot(to_digest), encoding="utf-8") as fh:
            doc = json.load(fh)
        return self.activate(copy.deepcopy(doc["config"]), actor=actor, reason=reason,
                             action="rollback")
