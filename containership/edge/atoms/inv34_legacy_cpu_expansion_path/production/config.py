"""Declarative configuration, provenance, atomic activation and rollback (MC-015..MC-018).

SPDX-License-Identifier: NOASSERTION

A configuration is one JSON document validated as a whole.  Activation is a
single atomic pointer swap (``ACTIVE`` file replaced with ``os.replace``) to an
immutable, content-addressed version file, so readers see either the old or the
new policy, never a mix.  Every activation writes a provenance record (version,
author, approver, activation time, source digest).  Rollback re-activates a
prior version; it never rolls CPU state backwards (that would be hot-unplug).
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

CONFIG_SCHEMA = "INV34_CONFIG/1"
ALLOWED_ADAPTERS = ("cloud-hypervisor-rest", "emulator")
ALLOWED_ENVIRONMENTS = ("dev", "test", "staging", "production")


class ConfigError(ValueError):
    code = "CONFIG_INVALID"


def validate_config(cfg: Any) -> dict:
    if not isinstance(cfg, dict):
        raise ConfigError("config must be an object")
    allowed = {"schema", "version", "environment", "site", "expansion_enabled", "adapter",
               "max_vcpus_default", "host_reserve_vcpus", "stall_after_s", "observation_max_age_s",
               "tenant_quotas", "site_ceiling", "fleet_ceiling", "precedence"}
    extra = set(cfg) - allowed
    if extra:
        raise ConfigError(f"unknown keys {sorted(extra)}")
    if cfg.get("schema") != CONFIG_SCHEMA:
        raise ConfigError("schema must be INV34_CONFIG/1")
    for k in ("version", "site"):
        if not isinstance(cfg.get(k), str) or not cfg[k]:
            raise ConfigError(f"{k} required")
    if cfg.get("environment") not in ALLOWED_ENVIRONMENTS:
        raise ConfigError("environment invalid")
    if cfg.get("adapter") not in ALLOWED_ADAPTERS:
        raise ConfigError("adapter not approved")
    if cfg["environment"] == "production" and cfg["adapter"] == "emulator":
        raise ConfigError("emulator adapter is forbidden in production")
    if not isinstance(cfg.get("expansion_enabled"), bool):
        raise ConfigError("expansion_enabled must be boolean")
    for k, lo in (("max_vcpus_default", 1), ("host_reserve_vcpus", 0), ("site_ceiling", 1), ("fleet_ceiling", 1)):
        v = cfg.get(k)
        if isinstance(v, bool) or not isinstance(v, int) or v < lo:
            raise ConfigError(f"{k} must be int >= {lo}")
    for k in ("stall_after_s", "observation_max_age_s"):
        v = cfg.get(k)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0:
            raise ConfigError(f"{k} must be > 0")
    tq = cfg.get("tenant_quotas")
    if not isinstance(tq, dict) or not all(isinstance(t, str) and isinstance(q, int) and q >= 0 for t, q in tq.items()):
        raise ConfigError("tenant_quotas must map tenant -> int")
    if sum(tq.values()) > cfg["fleet_ceiling"] * 4:
        raise ConfigError("tenant quotas oversubscribe fleet ceiling more than 4x")
    if cfg["site_ceiling"] > cfg["fleet_ceiling"]:
        raise ConfigError("site ceiling above fleet ceiling")
    prec = cfg.get("precedence")
    from .policy import CONSTRAINTS
    if not isinstance(prec, list) or sorted(prec) != sorted(CONSTRAINTS):
        raise ConfigError(f"precedence must be a permutation of {CONSTRAINTS}")
    return cfg


def digest(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class ConfigRepository:
    def __init__(self, root: str | os.PathLike) -> None:
        self.root = Path(root)
        (self.root / "versions").mkdir(parents=True, exist_ok=True)
        self.provenance = self.root / "PROVENANCE.jsonl"

    def _atomic(self, path: Path, data: bytes) -> None:
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)

    def stage(self, cfg: dict) -> str:
        validate_config(cfg)
        d = digest(cfg)
        p = self.root / "versions" / f"{d}.json"
        if not p.exists():
            self._atomic(p, json.dumps(cfg, sort_keys=True, indent=1).encode())
        return d

    def activate(self, d: str, *, author: str, approver: str | None, reason: str) -> dict:
        p = self.root / "versions" / f"{d}.json"
        cfg = json.loads(p.read_text())
        if digest(cfg) != d:
            raise ConfigError("stored version does not match its digest")
        validate_config(cfg)
        if cfg["environment"] == "production":
            if not approver:
                raise ConfigError("production activation requires an approver")
            if approver == author:
                raise ConfigError("author cannot approve their own production config")
        prev = self.active_digest()
        self._atomic(self.root / "ACTIVE", d.encode())
        rec = {"schema": "INV34_CONFIG_PROVENANCE/1", "digest": d, "version": cfg["version"],
               "previous": prev, "author": author, "approver": approver, "reason": reason,
               "activated_at": time.time()}
        with open(self.provenance, "a") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
        return rec

    def active_digest(self) -> str | None:
        p = self.root / "ACTIVE"
        return p.read_text().strip() if p.exists() else None

    def active(self) -> dict:
        d = self.active_digest()
        if d is None:
            raise ConfigError("no active configuration (fail closed)")
        cfg = json.loads((self.root / "versions" / f"{d}.json").read_text())
        if digest(cfg) != d:
            raise ConfigError("active config tampered")
        return cfg

    def history(self) -> list[dict]:
        if not self.provenance.exists():
            return []
        return [json.loads(line) for line in self.provenance.read_text().splitlines() if line.strip()]

    def rollback(self, *, author: str, approver: str | None, reason: str) -> dict:
        """Re-activate the configuration that was active before the current one."""
        hist = self.history()
        cur = self.active_digest()
        prevs = [h["previous"] for h in hist if h["digest"] == cur and h["previous"]]
        if not prevs:
            raise ConfigError("no previous configuration to roll back to")
        return self.activate(prevs[-1], author=author, approver=approver, reason="ROLLBACK: " + reason)
