"""Declarative configuration: schema, overlays, provenance, transactional
activation and rollback (checklist #26-#30, #32).

Configuration is plain JSON.  ``base`` + ``environment`` overlay + ``site``
overlay are deep-merged; overlays may not touch keys in ``LOCKED_KEYS`` (a
site cannot weaken transport security).  The merged document is validated,
scanned for credential material, digested, and only then staged.  ``commit``
swaps it in atomically and keeps the previous known-good document for
``rollback``.  Every step emits a provenance record.
"""
from __future__ import annotations

import copy
import hashlib
import json
import threading
import time

from .errors import INV55Error
from .telemetry import _CRED
from .wire import validate

CONFIG_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["schema", "environment", "provider", "identity", "lease", "limits", "cache", "retry", "telemetry"],
    "properties": {
        "schema": {"enum": ["inv55-config/1"]},
        "environment": {"enum": ["test", "dev", "staging", "production"]},
        "site": {"type": "string", "pattern": "^[a-z0-9-]{1,63}$"},
        "provider": {"type": "object", "additionalProperties": False, "required": ["kind"], "properties": {
            "kind": {"enum": ["memory", "vault-kv2"]},
            "address": {"type": "string", "maxLength": 512},
            "mount": {"type": "string", "pattern": "^[A-Za-z0-9._-]{1,64}$"},
            "namespace": {"type": "string", "maxLength": 128},
            "auth": {"enum": ["token-file", "approle"]},
            "ca_file": {"type": "string", "maxLength": 512},
            "allow_insecure_loopback": {"type": "boolean"}}},
        "identity": {"type": "object", "additionalProperties": False, "required": ["issuer", "audience"], "properties": {
            "issuer": {"type": "string", "maxLength": 256}, "audience": {"type": "string", "maxLength": 256},
            "max_skew_s": {"type": "number", "minimum": 0, "maximum": 300}}},
        "lease": {"type": "object", "additionalProperties": False, "required": ["ttl_s", "max_ttl_s"], "properties": {
            "ttl_s": {"type": "number", "minimum": 1, "maximum": 86400},
            "max_ttl_s": {"type": "number", "minimum": 1, "maximum": 86400}}},
        "limits": {"type": "object", "additionalProperties": False, "required": ["max_inflight", "rate_per_s", "burst"], "properties": {
            "max_inflight": {"type": "integer", "minimum": 1, "maximum": 100000},
            "rate_per_s": {"type": "number", "minimum": 0.001, "maximum": 1000000},
            "burst": {"type": "integer", "minimum": 1, "maximum": 1000000},
            "max_request_bytes": {"type": "integer", "minimum": 256, "maximum": 1048576}}},
        "cache": {"type": "object", "additionalProperties": False, "required": ["fresh_s", "max_stale_s", "allow_stale"], "properties": {
            "fresh_s": {"type": "number", "minimum": 0, "maximum": 3600},
            "max_stale_s": {"type": "number", "minimum": 0, "maximum": 86400},
            "allow_stale": {"type": "boolean"}}},
        "retry": {"type": "object", "additionalProperties": False, "required": ["attempts", "base_s", "cap_s", "deadline_s"], "properties": {
            "attempts": {"type": "integer", "minimum": 1, "maximum": 10},
            "base_s": {"type": "number", "minimum": 0, "maximum": 10},
            "cap_s": {"type": "number", "minimum": 0, "maximum": 60},
            "deadline_s": {"type": "number", "minimum": 0.001, "maximum": 60},
            "breaker_threshold": {"type": "integer", "minimum": 1, "maximum": 1000},
            "breaker_cooldown_s": {"type": "number", "minimum": 0, "maximum": 3600}}},
        "telemetry": {"type": "object", "additionalProperties": False, "required": ["max_series"], "properties": {
            "max_series": {"type": "integer", "minimum": 10, "maximum": 1000000},
            "audit_path": {"type": "string", "maxLength": 512}}},
    },
}
LOCKED_KEYS = {("provider", "allow_insecure_loopback"), ("provider", "kind"), ("schema",)}


def deep_merge(base: dict, overlay: dict, path=()) -> dict:
    out = copy.deepcopy(base)
    for k, v in overlay.items():
        p = path + (k,)
        if p in LOCKED_KEYS and k in out and out[k] != v:
            raise INV55Error("INV55-E-CONFIG", f"overlay may not change locked key {'.'.join(p)}")
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v, p)
        else:
            out[k] = copy.deepcopy(v)
    return out


def digest(doc: dict) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def check(doc: dict) -> list[str]:
    errs = validate(doc, CONFIG_SCHEMA)
    if errs:
        return errs
    if _CRED.search(json.dumps(doc)):
        errs.append("configuration contains credential-shaped material; reference a file/secret instead")
    p = doc["provider"]
    if p.get("allow_insecure_loopback") and doc["environment"] != "test":
        errs.append("allow_insecure_loopback is only permitted in environment=test")
    if doc["environment"] == "production" and p["kind"] == "memory":
        errs.append("memory provider is not permitted in production")
    if p["kind"] == "vault-kv2" and not str(p.get("address", "")).startswith(("https://", "http://127.", "http://[::1]")):
        errs.append("vault address must be https")
    if doc["lease"]["ttl_s"] > doc["lease"]["max_ttl_s"]:
        errs.append("lease.ttl_s exceeds lease.max_ttl_s")
    if doc["cache"]["max_stale_s"] < doc["cache"]["fresh_s"]:
        errs.append("cache.max_stale_s < cache.fresh_s")
    if doc["environment"] == "production" and doc["cache"]["allow_stale"]:
        errs.append("stale serving requires a waiver in production (WAIVERS.md) and is refused by default")
    return errs


class ConfigController:
    """validate -> stage -> commit, with previous-known-good rollback."""

    def __init__(self, clock=time.time):
        self.active: dict | None = None
        self.active_digest: str | None = None
        self.previous: tuple[dict, str] | None = None
        self.staged: tuple[dict, dict] | None = None
        self.provenance: list[dict] = []
        self.clock = clock
        self._lock = threading.Lock()

    def stage(self, base: dict, *overlays: dict, author: str, source: str) -> dict:
        doc = base
        for o in overlays:
            doc = deep_merge(doc, o)
        errs = check(doc)
        rec = {"event": "stage", "author": author, "source": source, "digest": digest(doc),
               "at": self.clock(), "valid": not errs, "errors": errs}
        self.provenance.append(rec)
        if errs:
            raise INV55Error("INV55-E-CONFIG", "; ".join(errs))
        with self._lock:
            self.staged = (doc, rec)
        return rec

    def commit(self, *, approved_by: str | None, require_approval: bool) -> str:
        with self._lock:
            if not self.staged:
                raise INV55Error("INV55-E-CONFIG", "nothing staged")
            doc, rec = self.staged
            if require_approval and not approved_by:
                raise INV55Error("INV55-E-CONFIG", "commit requires an approver")
            if approved_by and approved_by == rec["author"]:
                raise INV55Error("INV55-E-CONFIG", "author cannot approve own configuration")
            if self.active is not None:
                self.previous = (self.active, self.active_digest)
            self.active, self.active_digest = doc, rec["digest"]
            self.staged = None
            self.provenance.append({"event": "commit", "digest": rec["digest"], "approved_by": approved_by, "at": self.clock()})
            return rec["digest"]

    def rollback(self, *, actor: str, reason: str) -> str:
        with self._lock:
            if not self.previous:
                raise INV55Error("INV55-E-CONFIG", "no previous known-good configuration")
            bad = self.active_digest
            self.active, self.active_digest = self.previous
            self.previous = None
            self.provenance.append({"event": "rollback", "from": bad, "to": self.active_digest,
                                    "actor": actor, "reason": reason, "at": self.clock()})
            return self.active_digest
