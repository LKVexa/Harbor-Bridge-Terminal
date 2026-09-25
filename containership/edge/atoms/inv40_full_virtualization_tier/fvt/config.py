"""Declarative configuration with secure defaults, layering, provenance,
fail-closed validation, atomic activation and rollback (INV-40-C032..C040).

Immutable artifact = the package + schemas (digest in MANIFEST.sha256).
Mutable configuration = JSON documents layered base -> site -> environment,
activated by a ConfigStore that writes each generation atomically
(write temp + fsync + os.replace) and keeps an append-only history so the
previous generation can be restored automatically or by an operator.
"""
from __future__ import annotations

import copy
import datetime as _dt
import hashlib
import json
import os
import pathlib
import re
import tempfile

from . import schema
from .errors import OpError

SECURE_DEFAULTS: dict = {
    "schema": "PK_FULL_VM_CONFIG/1",
    "config_version": "1.0.0",
    "boot_budget_ms": 8000,
    "footprint_ceiling_mib": 2048,
    "max_concurrent_ops": 16,
    "max_queue": 64,
    "tenant_guest_quota": 32,
    "tenant_memory_quota_mib": 65536,
    "op_timeout_ms": 30000,
    "retry_max_attempts": 3,
    "breaker_failure_threshold": 5,
    "breaker_reset_ms": 30000,
    "require_hardware_primitive": True,
    "allow_software_emulation": False,
    "allow_nested_virtualization": False,
    "allow_gpu_passthrough": False,
    "allow_live_migration": False,
    "telemetry_export": "stdout",
    "log_retention_days": 30,
    "trace_sample_ratio": 0.1,
    "site": "unassigned-site",
    "environment": "dev",
    "approved_image_digests": [],
    "qemu_binary": "qemu-system-x86_64",
    "offline_mode": "fail_closed",
}

#: keys whose *values* look like secret material are refused outright (C039)
_SECRET_KEY = re.compile(r"(^|[_-])(password|passwd|passphrase|secret|token|private[_-]?key|api[_-]?key|credentials?)($|[_-])", re.I)
_SECRET_VAL = re.compile(r"(-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|xox[baprs]-[A-Za-z0-9-]{10,})")

#: fields whose change is security-critical: invalid => fail closed, never partial
SECURITY_CRITICAL = {"require_hardware_primitive", "allow_software_emulation",
                     "approved_image_digests", "allow_gpu_passthrough", "allow_nested_virtualization"}


def canonical(doc: dict) -> bytes:
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(doc: dict) -> str:
    return "sha256:" + hashlib.sha256(canonical(doc)).hexdigest()


def _scan_secrets(doc, path="") -> list[str]:
    hits = []
    if isinstance(doc, dict):
        for k, v in doc.items():
            if _SECRET_KEY.search(str(k)):
                hits.append(f"{path}.{k}")
            hits += _scan_secrets(v, f"{path}.{k}")
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            hits += _scan_secrets(v, f"{path}[{i}]")
    elif isinstance(doc, str) and _SECRET_VAL.search(doc):
        hits.append(path)
    return hits


def layer(*docs: dict) -> dict:
    """Merge base -> site -> env overlays; later layers win key-by-key (C035)."""
    out = copy.deepcopy(SECURE_DEFAULTS)
    for d in docs:
        for k, v in (d or {}).items():
            out[k] = copy.deepcopy(v)
    return out


def validate(doc: dict) -> dict:
    """Validate a full config; raise PK_FULL_VM_CONFIG_INVALID (fail closed, C034)."""
    secrets = _scan_secrets(doc)
    if secrets:
        raise OpError("PK_FULL_VM_CONFIG_INVALID", "secret material in ordinary configuration",
                      paths=secrets)
    try:
        schema.validate(doc, schema.load("PK_FULL_VM_CONFIG.v1"))
    except schema.SchemaError as exc:
        raise OpError("PK_FULL_VM_CONFIG_INVALID", str(exc), path=exc.path) from None
    if doc["max_queue"] < 0 or doc["tenant_memory_quota_mib"] < doc["footprint_ceiling_mib"] // 16:
        raise OpError("PK_FULL_VM_CONFIG_INVALID", "tenant memory quota implausibly small")
    if doc["environment"] == "prod" and doc["telemetry_export"] == "none":
        raise OpError("PK_FULL_VM_CONFIG_INVALID", "prod requires telemetry export")
    if doc["environment"] == "prod" and not doc["approved_image_digests"]:
        raise OpError("PK_FULL_VM_CONFIG_INVALID", "prod requires an approved image allow-list")
    return doc


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _atomic_write(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


class ConfigStore:
    """Transactional config activation with provenance and rollback (C036-C038)."""

    def __init__(self, root: str | os.PathLike):
        self.root = pathlib.Path(root)
        self.active_path = self.root / "active.json"
        self.history_path = self.root / "history.jsonl"

    def active(self) -> dict | None:
        if not self.active_path.exists():
            return None
        rec = json.loads(self.active_path.read_text(encoding="utf-8"))
        if digest(rec["config"]) != rec["provenance"]["digest"]:
            raise OpError("PK_FULL_VM_CONFIG_INVALID", "active config digest mismatch (tampered)")
        return rec

    def history(self) -> list[dict]:
        if not self.history_path.exists():
            return []
        return [json.loads(l) for l in self.history_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    def activate(self, doc: dict, *, author: str, reason: str, health_check=None) -> dict:
        """Validate, then atomically activate.  If ``health_check`` rejects the
        new generation it is rolled back automatically and the error re-raised."""
        if not author or not isinstance(author, str):
            raise OpError("PK_FULL_VM_CONFIG_INVALID", "author required for provenance")
        validate(doc)
        prev = self.active()
        gen = (prev["provenance"]["generation"] + 1) if prev else 1
        rec = {"config": doc, "provenance": {
            "generation": gen, "digest": digest(doc), "config_version": doc["config_version"],
            "author": author, "reason": reason, "activated_at": _now(),
            "previous_digest": prev["provenance"]["digest"] if prev else None}}
        _atomic_write(self.active_path, json.dumps(rec, sort_keys=True, indent=1).encode())
        with open(self.history_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        if health_check is not None:
            try:
                ok = health_check(doc)
            except Exception:  # noqa: BLE001 - any failure means unhealthy
                ok = False
            if not ok:
                self.rollback(author="auto-rollback", reason=f"health check failed for gen {gen}")
                raise OpError("PK_FULL_VM_CONFIG_INVALID", f"generation {gen} failed health check; rolled back")
        return rec["provenance"]

    def rollback(self, *, author: str, reason: str) -> dict | None:
        """Restore the generation that preceded the active one (operator or automatic)."""
        cur = self.active()
        if cur is None or cur["provenance"]["previous_digest"] is None:
            if self.active_path.exists():
                os.replace(self.active_path, self.root / f"retired-{int(_dt.datetime.now().timestamp())}.json")
            return None
        target = cur["provenance"]["previous_digest"]
        for rec in reversed(self.history()):
            if rec["provenance"]["digest"] == target:
                new = {"config": rec["config"], "provenance": dict(rec["provenance"],
                       generation=cur["provenance"]["generation"] + 1, author=author, reason=reason,
                       activated_at=_now(), rolled_back_from=cur["provenance"]["digest"],
                       previous_digest=self._previous_of(target))}
                _atomic_write(self.active_path, json.dumps(new, sort_keys=True, indent=1).encode())
                with open(self.history_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(new, sort_keys=True) + "\n")
                return new["provenance"]
        raise OpError("PK_FULL_VM_CONFIG_INVALID", "rollback target not found in history")

    def _previous_of(self, dig: str) -> str | None:
        for rec in self.history():
            if rec["provenance"]["digest"] == dig:
                return rec["provenance"].get("previous_digest")
        return None
