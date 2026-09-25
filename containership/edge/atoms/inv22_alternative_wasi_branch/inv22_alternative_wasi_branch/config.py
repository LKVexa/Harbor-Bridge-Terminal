"""Typed configuration, precedence, secret indirection and redaction (MC-20, MC-22, MC-26, MC-27, MC-61).

Precedence (lowest → highest): built-in secure defaults < config file <
site overlay < environment (``INV22__SECTION__KEY``) < CLI overrides.
Only keys listed in ``MUTABLE`` may be changed by overlays/env/CLI; baseline
and schema identities are immutable artifacts and cannot be overridden.
Secrets are references (``secret://provider/name``), never values.
"""
from __future__ import annotations

import copy
import json
import re
from typing import Any, Mapping

from . import canonical
from .errors import Inv22Error

CONTRACT = "PK_BRANCH_CONFIG/1"

DEFAULTS: dict = {
    "contract": CONTRACT,
    "site": {"id": "unset", "branch": "standards"},
    "baselines": {"manifest": "baselines/manifest.json"},
    "store": {"path": "inv22-state.sqlite3", "credential": None},
    "signing": {"key_ref": None, "trust_store": "trust/trust-store.json"},
    "listen": {"host": "127.0.0.1", "port": 0},
    "limits": {"max_payload_bytes": 65536, "max_concurrency": 8, "default_deadline_ms": 2000,
               "max_matrix_entries": 4096, "max_queue": 64},
    "freshness": {"max_revocation_age_s": 3600, "max_offline_s": 86400, "clock_skew_s": 120},
    "telemetry": {"enabled": True, "exporter": "jsonl", "path": "inv22-telemetry.jsonl", "credential": None},
    "retention": {"audit_days": 2555, "telemetry_days": 30, "drift_days": 3650, "residency": "unset"},
    "features": {"auto_classify_unknown": False, "anonymous_read": False, "unsigned_certificates": False},
}

MUTABLE = {
    "site.id", "site.branch", "store.path", "store.credential", "signing.key_ref", "signing.trust_store",
    "listen.host", "listen.port", "limits.max_payload_bytes", "limits.max_concurrency",
    "limits.default_deadline_ms", "limits.max_queue", "freshness.max_revocation_age_s",
    "freshness.max_offline_s", "telemetry.enabled", "telemetry.exporter", "telemetry.path",
    "telemetry.credential", "retention.audit_days", "retention.telemetry_days", "retention.residency",
}
RANGES = {
    "limits.max_payload_bytes": (1024, 1_048_576), "limits.max_concurrency": (1, 256),
    "limits.default_deadline_ms": (1, 60_000), "limits.max_matrix_entries": (1, 4096),
    "limits.max_queue": (1, 10_000), "freshness.max_revocation_age_s": (60, 86_400),
    "freshness.max_offline_s": (60, 604_800), "freshness.clock_skew_s": (0, 600),
    "listen.port": (0, 65_535), "retention.audit_days": (365, 3650), "retention.telemetry_days": (1, 400),
    "retention.drift_days": (365, 7300),
}
SECRET_KEYS = {"store.credential", "signing.key_ref", "telemetry.credential"}
_SECRET_REF = re.compile(r"^secret://[a-z0-9-]+/[A-Za-z0-9_./-]{1,200}$")
_REDACT_KEY = re.compile(r"(?i)(secret|token|password|passwd|credential|private|key_ref|api[_-]?key|authorization)")
_REDACT_VAL = re.compile(r"(-----BEGIN [A-Z ]*PRIVATE KEY-----|\bey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}|\bAKIA[0-9A-Z]{16}\b)")


def _cfg_err(msg: str, **d) -> Inv22Error:
    return Inv22Error("INV22.CONFIG.INVALID", msg, d)


def _flat(d: Mapping, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flat(v, key + "."))
        else:
            out[key] = v
    return out


def _set(d: dict, dotted: str, value: Any) -> None:
    *parents, leaf = dotted.split(".")
    for p in parents:
        d = d[p]
    d[leaf] = value


def validate(cfg: Any) -> dict:
    if not isinstance(cfg, dict):
        raise _cfg_err("configuration must be an object")
    if cfg.get("contract") != CONTRACT:
        raise Inv22Error("INV22.VERSION.UNSUPPORTED", "unsupported configuration contract", {"contract": cfg.get("contract")})
    want, got = _flat(DEFAULTS), _flat(cfg)
    unknown = set(got) - set(want)
    if unknown:
        raise _cfg_err("unknown configuration key", key=sorted(unknown)[0])
    missing = set(want) - set(got)
    if missing:
        raise _cfg_err("missing configuration key", key=sorted(missing)[0])
    for key, value in got.items():
        default = want[key]
        if key in SECRET_KEYS:
            if value is not None and not (isinstance(value, str) and _SECRET_REF.match(value)):
                raise _cfg_err("secrets must be secret:// references, never values", key=key)
            continue
        if isinstance(default, bool):
            if not isinstance(value, bool):
                raise _cfg_err("expected boolean", key=key)
        elif isinstance(default, int):
            if not isinstance(value, int) or isinstance(value, bool):
                raise _cfg_err("expected integer", key=key)
            lo, hi = RANGES.get(key, (0, 2**31))
            if not lo <= value <= hi:
                raise _cfg_err("value out of range", key=key, min=lo, max=hi)
        elif isinstance(default, str) and (not isinstance(value, str) or not value or len(value) > 512 or "\x00" in value):
            raise _cfg_err("expected non-empty string", key=key)
    if cfg["site"]["branch"] not in ("standards", "fork"):
        raise _cfg_err("unknown site branch", key="site.branch")
    if cfg["listen"]["host"] in ("0.0.0.0", "::", "*"):  # noqa: S104 - this line rejects wildcard binds
        raise _cfg_err("wildcard listener is not permitted", key="listen.host")
    for flag, v in cfg["features"].items():
        if v:
            raise _cfg_err("unsafe feature flag cannot be enabled in this release", key=f"features.{flag}")
    for key in ("store.path", "telemetry.path", "baselines.manifest", "signing.trust_store"):
        p = got[key]
        if ".." in p.replace("\\", "/").split("/"):
            raise _cfg_err("path traversal is not permitted", key=key)
    if cfg["telemetry"]["exporter"] not in ("jsonl", "none"):
        raise _cfg_err("unsupported telemetry exporter", key="telemetry.exporter")
    return cfg


def _parse_scalar(raw: str) -> Any:
    try:
        return canonical.loads(raw)
    except Inv22Error:
        return raw


def load(file_doc: Mapping | None = None, *, overlay: Mapping | None = None,
         env: Mapping[str, str] | None = None, cli: Mapping[str, Any] | None = None) -> tuple[dict, dict]:
    """Return (effective_config, provenance) after validation."""
    cfg = copy.deepcopy(DEFAULTS)
    prov = {k: "default" for k in _flat(DEFAULTS)}
    layers: list[tuple[str, dict, set | None]] = []
    if file_doc is not None:
        if not isinstance(file_doc, dict):
            raise _cfg_err("config file must be an object")
        layers.append(("file", _flat(file_doc), None))
    if overlay:
        layers.append(("overlay", _flat(overlay), MUTABLE))
    if env:
        vals = {}
        for k, v in env.items():
            if k.startswith("INV22__"):
                vals[k[7:].lower().replace("__", ".")] = _parse_scalar(v)
        layers.append(("env", vals, MUTABLE))
    if cli:
        layers.append(("cli", dict(cli), MUTABLE))
    for source, values, allowed in layers:
        for key, value in values.items():
            if key not in prov:
                raise _cfg_err("unknown configuration key", key=key, source=source)
            if allowed is not None and key not in allowed:
                raise _cfg_err("key is immutable for this source", key=key, source=source)
            _set(cfg, key, value)
            prov[key] = source
    validate(cfg)
    return cfg, prov


def load_file(path: str) -> dict:
    with open(path, "rb") as fh:
        return canonical.loads(fh.read())


def redact(value: Any, key: str = "") -> Any:
    """Recursively redact secret-looking keys and values."""
    if isinstance(value, dict):
        return {k: redact(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, key) for v in value]
    if key and _REDACT_KEY.search(key) and value is not None:
        return "[REDACTED]"
    if isinstance(value, str) and _REDACT_VAL.search(value):
        return "[REDACTED]"
    return value


def effective_view(cfg: dict, prov: dict) -> str:
    """Sanitised effective configuration with per-key provenance."""
    flat = _flat(redact(cfg))
    return json.dumps({k: {"value": flat[k], "source": prov[k]} for k in sorted(flat)}, indent=2)
