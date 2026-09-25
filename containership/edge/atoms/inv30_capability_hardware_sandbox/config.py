# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Declarative configuration (GAP-023): secure defaults, validation, overlays, provenance,
atomic activation and rollback. Immutable code vs mutable config is enforced: config
cannot change code paths beyond the schema's enumerated knobs.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import threading
import time
from pathlib import Path

from . import schema
from .errors import ConfigInvalid, SchemaInvalid
from .limits import Limits

CONFIG_DIR = Path(__file__).resolve().parent / "config"


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out


def digest(cfg: dict) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate(cfg: dict) -> dict:
    try:
        schema.validate("config", cfg)
    except SchemaInvalid as exc:
        raise ConfigInvalid(f"config schema: {exc}") from None
    lim = Limits(**cfg["limits"]) if cfg["limits"] else Limits()
    bad = lim.validate()
    if bad:
        raise ConfigInvalid("; ".join(bad))
    for k, v in (cfg.get("auth") or {}).items():
        if not k.endswith("_ref") and isinstance(v, str) and len(v) >= 16:
            raise ConfigInvalid(f"auth.{k}: inline secret material is forbidden; use a *_ref")
    for k, v in (cfg.get("secret_refs") or {}).items():
        if not (isinstance(v, str) and (v.startswith("env:") or v.startswith("file:"))):
            raise ConfigInvalid(f"secret_refs.{k} must be env:/file: reference")
    if cfg["mode"] == "production":
        if cfg["telemetry"].get("log_level") == "debug":
            raise ConfigInvalid("production forbids debug logging")
        if not cfg.get("secret_refs", {}).get("minting_key"):
            raise ConfigInvalid("production requires secret_refs.minting_key")
        if cfg["rollout"].get("allow_model_for_hardware_workloads"):
            raise ConfigInvalid("allow_model_for_hardware_workloads is forbidden (zero-budget invariant)")
    return cfg


def load(context: str = "datacenter", *, mode: str | None = None, extra: dict | None = None) -> dict:
    base = json.loads((CONFIG_DIR / "default.json").read_text(encoding="utf-8"))
    ov_path = CONFIG_DIR / "overlays" / f"{context}.json"
    if not ov_path.exists():
        raise ConfigInvalid(f"unknown deployment context {context!r}")
    cfg = _merge(base, json.loads(ov_path.read_text(encoding="utf-8")))
    if mode:
        cfg["mode"] = mode
    if extra:
        cfg = _merge(cfg, extra)
    return validate(cfg)


class ConfigStore:
    """Atomic activation with provenance history and rollback. Persisted via write-rename."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self._lock = threading.Lock()
        self.history: list[dict] = []
        if self.path and self.path.exists():
            self.history = json.loads(self.path.read_text(encoding="utf-8"))["history"]

    @property
    def active(self) -> dict | None:
        return self.history[-1]["config"] if self.history else None

    def activate(self, cfg: dict, *, author: str, reason: str) -> dict:
        validate(cfg)  # fail closed before anything changes
        with self._lock:
            entry = {"version": len(self.history) + 1, "digest": digest(cfg), "author": author, "reason": reason,
                     "activated_at": round(time.time(), 6), "config": copy.deepcopy(cfg)}
            self._persist(self.history + [entry])
            self.history.append(entry)
            return {k: v for k, v in entry.items() if k != "config"}

    def rollback(self, *, author: str, reason: str) -> dict:
        with self._lock:
            if len(self.history) < 2:
                raise ConfigInvalid("no previous configuration to roll back to")
            prev = self.history[-2]["config"]
        return self.activate(prev, author=author, reason=f"rollback: {reason}")

    def _persist(self, history):
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".cfg-")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"schema": "INV30_CONFIG_STORE/1", "history": history}, fh, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)
