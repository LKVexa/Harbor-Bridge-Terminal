"""MC-023..MC-028 — declarative configuration: load, overlay, validate, activate, roll back.

* ``load()``      parses JSON, rejects unknown keys, validates types/bounds, applies
                  secure defaults (MC-023).
* ``overlay()``   merges base <- site <- environment documents without rebuilding
                  the artifact; overlays may only *tighten* security keys (MC-024).
* ``ConfigStore`` keeps an append-only history with provenance (version, actor,
                  source, digest, activation time) (MC-025), activates atomically
                  with write-temp + fsync + rename and a validation-before-swap
                  (MC-026), and rolls back automatically on a failed health check
                  or by operator command (MC-027).
* ``redact()``    removes secrets from anything that leaves the process (MC-028).
"""
from __future__ import annotations

import copy
import json
import os
import re
import tempfile
import time
from typing import Any, Callable

from .attestation import digest
from .errors import SandboxError

DEFAULTS: dict[str, Any] = {
    "backend": "native",                 # native | bwrap | seatbelt
    "deny_action": "errno",              # errno | kill
    "syscall_budget": 60,
    "require_landlock": False,
    "require_userns": True,
    "max_concurrent": 256,
    "max_per_tenant": 32,
    "max_queue": 64,
    "default_timeout_s": 30.0,
    "rlimits": {"core": 0, "nofile": 256, "nproc": 256, "fsize": 64 << 20},
    "evidence_max_age_s": 300,
    "offline_mode": "refuse",            # refuse | cached-profiles-only (MC-009)
    "telemetry": {"sample_rate": 1.0, "retention_days": 30, "export": "none"},
    "node_key_ref": "",                  # reference to a secret, never the secret itself
}
SCHEMA: dict[str, tuple[type | tuple, Callable[[Any], bool] | None]] = {
    "backend": (str, lambda v: v in ("native", "bwrap", "seatbelt")),
    "deny_action": (str, lambda v: v in ("errno", "kill")),
    "syscall_budget": (int, lambda v: 1 <= v <= 400),
    "require_landlock": (bool, None),
    "require_userns": (bool, None),
    "max_concurrent": (int, lambda v: 1 <= v <= 100_000),
    "max_per_tenant": (int, lambda v: 1 <= v <= 100_000),
    "max_queue": (int, lambda v: 0 <= v <= 100_000),
    "default_timeout_s": ((int, float), lambda v: 0 < v <= 86400),
    "rlimits": (dict, lambda v: set(v) <= {"core", "nofile", "nproc", "fsize", "as", "cpu"}
                and all(isinstance(x, int) and x >= 0 for x in v.values())),
    "evidence_max_age_s": (int, lambda v: 1 <= v <= 3600),
    "offline_mode": (str, lambda v: v in ("refuse", "cached-profiles-only")),
    "telemetry": (dict, lambda v: set(v) <= {"sample_rate", "retention_days", "export"}),
    "node_key_ref": (str, lambda v: v == "" or v.startswith(("env:", "file:", "vault:"))),
}
# for these keys an overlay may only move in the "safer" direction
TIGHTEN_ONLY = {
    "deny_action": lambda old, new: not (old == "kill" and new == "errno"),
    "require_landlock": lambda old, new: not (old and not new),
    "require_userns": lambda old, new: not (old and not new),
    "syscall_budget": lambda old, new: new <= old,
}
SECRET_KEY_RE = re.compile(r"(secret|password|token|key|credential)(?!_ref)", re.I)
MAX_CONFIG_BYTES = 256 * 1024


def validate(cfg: dict[str, Any]) -> dict[str, Any]:
    unknown = set(cfg) - set(SCHEMA)
    if unknown:
        raise SandboxError("E_CONFIG_INVALID", f"unknown keys {sorted(unknown)}")
    out = copy.deepcopy(DEFAULTS)
    for k, v in cfg.items():
        typ, check = SCHEMA[k]
        if isinstance(v, bool) and typ in (int, (int, float)):
            raise SandboxError("E_CONFIG_INVALID", f"{k}: bool is not a number")
        if not isinstance(v, typ) or (check and not check(v)):
            raise SandboxError("E_CONFIG_INVALID", f"{k}: invalid value {v!r}")
        out[k] = copy.deepcopy(v)
    return out


def load(raw: bytes | str) -> dict[str, Any]:
    if isinstance(raw, str):
        raw = raw.encode()
    if len(raw) > MAX_CONFIG_BYTES:
        raise SandboxError("E_CONFIG_INVALID", "configuration too large")
    try:
        doc = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise SandboxError("E_CONFIG_INVALID", f"not JSON: {e}") from None
    if not isinstance(doc, dict):
        raise SandboxError("E_CONFIG_INVALID", "configuration must be an object")
    return validate(doc)


def overlay(base: dict[str, Any], *layers: dict[str, Any]) -> dict[str, Any]:
    cfg = validate(base)
    for layer in layers:
        layer_valid = {k: v for k, v in validate(layer).items() if k in layer}
        for k, v in layer_valid.items():
            rule = TIGHTEN_ONLY.get(k)
            if rule and not rule(cfg[k], v):
                raise SandboxError("E_CONFIG_INVALID", f"overlay may not loosen {k}: {cfg[k]!r} -> {v!r}")
            cfg[k] = v
    return cfg


def redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: ("[REDACTED]" if SECRET_KEY_RE.search(str(k)) else redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    if isinstance(obj, str) and re.search(r"(hmac-sha256:[0-9a-f]{16,}|-----BEGIN [A-Z ]*PRIVATE KEY)", obj):
        return "[REDACTED]"
    return obj


class ConfigStore:
    """Atomic activation + history + rollback. ``directory`` holds active.json and history.jsonl."""

    MAX_HISTORY = 100

    def __init__(self, directory: str, clock=time.time):
        self.dir, self.clock = directory, clock
        os.makedirs(directory, exist_ok=True)
        self.history: list[dict[str, Any]] = []
        hp = os.path.join(directory, "history.jsonl")
        if os.path.exists(hp):
            with open(hp) as f:
                self.history = [json.loads(l) for l in f if l.strip()][-self.MAX_HISTORY:]

    @property
    def active(self) -> dict[str, Any] | None:
        return self.history[-1] if self.history else None

    def _write_atomic(self, name: str, data: bytes) -> None:
        fd, tmp = tempfile.mkstemp(dir=self.dir, prefix=".tmp-")
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp, os.path.join(self.dir, name))
        dfd = os.open(self.dir, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)

    def activate(self, cfg: dict[str, Any], *, actor: str, source: str,
                 health_check: Callable[[dict[str, Any]], bool] | None = None) -> dict[str, Any]:
        valid = validate(cfg)                         # validate before touching disk
        prev = self.active
        rec = {"version": (prev["version"] + 1) if prev else 1, "actor": actor, "source": source,
               "digest": digest(valid), "activated_at": self.clock(), "config": valid}
        self._write_atomic("active.json", json.dumps(rec, sort_keys=True).encode())
        with open(os.path.join(self.dir, "history.jsonl"), "a") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())
        self.history.append(rec)
        if health_check is not None:
            ok = False
            try:
                ok = bool(health_check(valid))
            except Exception:  # noqa: BLE001
                ok = False
            if not ok:
                self.rollback(actor="auto-rollback", reason=f"health check failed for v{rec['version']}")
                raise SandboxError("E_CONFIG_INVALID", f"v{rec['version']} failed health check; rolled back")
        return rec

    def rollback(self, *, actor: str, reason: str, to_version: int | None = None) -> dict[str, Any]:
        if len(self.history) < 2 and to_version is None:
            raise SandboxError("E_CONFIG_INVALID", "no previous configuration to roll back to")
        target = (next((h for h in self.history if h["version"] == to_version), None)
                  if to_version is not None else self.history[-2])
        if target is None:
            raise SandboxError("E_CONFIG_INVALID", f"version {to_version} not in history")
        return self.activate(target["config"], actor=actor, source=f"rollback:v{target['version']}:{reason}")
