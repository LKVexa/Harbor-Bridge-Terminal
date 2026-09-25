"""Declarative configuration with secure defaults, overlays, provenance and atomic generations.

C032-C040.  Separation (C032):

* **immutable artifacts** - rewritten modules, proofs and release files, addressed by SHA-256;
* **configuration** - this module: versioned JSON generations, activated atomically;
* **durable operational state** - quarantine state, anti-rollback floors, audit log;
* **ephemeral state** - loaded instances, replay cache, verifier cache (rebuildable);
* **secrets** - only ``SecretRef`` strings (``*_ref`` keys) appear in configuration.

Overlay precedence (C035): ``base < environment < site``.  Security-*weakening*
switches (``profile.allow_*``) may be set only in the base (release-reviewed)
layer; an overlay touching them is rejected.  Secure bounds prevent operators from
disabling protections accidentally (e.g. a 0-second deadline or a 1 GiB module cap).
"""
from __future__ import annotations

import copy
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Optional

from .errors import SfiError
from .sfi import Profile, canonical_json, sha256_hex
from .wasm import Limits

CONFIG_SCHEMA = "PK_SFI_CONFIG/1"
GENERATION_SCHEMA = "PK_SFI_CONFIG_GENERATION/1"

DEFAULTS: dict[str, Any] = {
    "schema": CONFIG_SCHEMA,
    "environment": "dev",
    "site": "default",
    "profile": {
        "region_base": 65536,
        "region_log2": 16,
        "function_import_allowlist": [],
        "allow_memory_grow": False,
        "allow_memory_export": False,
        "require_imported_memory": False,
    },
    "limits": {
        "max_module_bytes": 16 * 1024 * 1024,
        "max_functions": 100_000,
        "max_function_body_bytes": 1_048_576,
        "max_total_instructions": 5_000_000,
        "deadline_seconds": 10.0,
    },
    "admission": {"max_concurrent": 4, "max_per_tenant": 2, "max_queue": 64},
    "trust": {
        "descriptor_ttl_seconds": 900.0,
        "trust_max_age_seconds": 3600.0,
        "seal_key_ref": "env:INV45_SEAL_KEY",
        "idp_key_ref": "env:INV45_IDP_KEY",
    },
    "engine": {"kind": "node-v8", "node_major": 22, "call_timeout_seconds": 5.0},
    "telemetry": {"log_level": "info", "trace_sample_rate": 1.0, "retention_days": 30},
}

# (min, max) secure bounds for numeric keys
BOUNDS: dict[tuple[str, str], tuple[float, float]] = {
    ("profile", "region_log2"): (12, 31),
    ("profile", "region_base"): (0, 2**32 - 1),
    ("limits", "max_module_bytes"): (1024, 64 * 1024 * 1024),
    ("limits", "max_functions"): (1, 1_000_000),
    ("limits", "max_function_body_bytes"): (16, 16 * 1024 * 1024),
    ("limits", "max_total_instructions"): (16, 50_000_000),
    ("limits", "deadline_seconds"): (0.05, 60.0),
    ("admission", "max_concurrent"): (1, 256),
    ("admission", "max_per_tenant"): (1, 256),
    ("admission", "max_queue"): (0, 10_000),
    ("trust", "descriptor_ttl_seconds"): (1, 3600),
    ("trust", "trust_max_age_seconds"): (1, 86400),
    ("engine", "node_major"): (18, 99),
    ("engine", "call_timeout_seconds"): (0.1, 120),
    ("telemetry", "trace_sample_rate"): (0.0, 1.0),
    ("telemetry", "retention_days"): (1, 400),
}
BASE_ONLY = {("profile", "allow_memory_grow"), ("profile", "allow_memory_export"),
             ("profile", "function_import_allowlist")}
SECRETISH = ("secret", "password", "passwd", "token", "private", "apikey", "api_key")


def _err(msg: str, field: str) -> SfiError:
    return SfiError("SFI_CONFIG_INVALID", msg, field=field)


def _walk_keys(tmpl: dict[str, Any], cfg: dict[str, Any], path: str = "") -> None:
    for k, v in cfg.items():
        p = f"{path}.{k}" if path else k
        if k not in tmpl:
            raise _err("unknown configuration key", p)
        lk = k.lower()
        if any(s in lk for s in SECRETISH) or (("key" in lk) and not lk.endswith("_ref")):
            raise _err("secret-looking key outside a *_ref field", p)
        if isinstance(tmpl[k], dict):
            if not isinstance(v, dict):
                raise _err("expected object", p)
            _walk_keys(tmpl[k], v, p)


def merge(base: dict[str, Any], *overlays: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for layer_no, ov in enumerate(overlays, 1):
        _walk_keys(DEFAULTS, ov)
        for sec, val in ov.items():
            if sec == "schema":
                raise _err("overlays may not change schema", "schema")
            if isinstance(val, dict):
                for k, v in val.items():
                    if (sec, k) in BASE_ONLY:
                        raise _err("security-weakening switch may only be set in the base layer", f"{sec}.{k}")
                    out.setdefault(sec, {})[k] = copy.deepcopy(v)
            else:
                out[sec] = val
    return out


def validate(cfg: Any) -> dict[str, Any]:
    """Validate a complete effective configuration; return the normalized copy."""
    if not isinstance(cfg, dict):
        raise _err("configuration must be an object", "")
    if cfg.get("schema") != CONFIG_SCHEMA:
        raise SfiError("SFI_UNSUPPORTED_VERSION", "unsupported configuration schema",
                       expected_version=CONFIG_SCHEMA, observed_version=str(cfg.get("schema"))[:64])
    _walk_keys(DEFAULTS, cfg)
    full = copy.deepcopy(DEFAULTS)
    for sec, val in cfg.items():
        if isinstance(val, dict):
            full[sec].update(copy.deepcopy(val))
        else:
            full[sec] = val
    for sec, tmpl in DEFAULTS.items():
        if isinstance(tmpl, dict):
            for k, dv in tmpl.items():
                v = full[sec][k]
                p = f"{sec}.{k}"
                if isinstance(dv, bool):
                    if type(v) is not bool:
                        raise _err("expected boolean", p)
                elif isinstance(dv, (int, float)):
                    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v in (float("inf"), float("-inf")):
                        raise _err("expected finite number", p)
                    if isinstance(dv, int) and not isinstance(v, int):
                        raise _err("expected integer", p)
                    lo, hi = BOUNDS.get((sec, k), (float("-inf"), float("inf")))
                    if not lo <= v <= hi:
                        raise _err(f"value outside secure bounds [{lo}, {hi}]", p)
                elif isinstance(dv, str):
                    if not isinstance(v, str) or not v or len(v) > 256:
                        raise _err("expected non-empty string", p)
                elif isinstance(dv, list):
                    if not isinstance(v, list) or not all(isinstance(x, str) and "." in x for x in v):
                        raise _err("expected list of 'module.name' strings", p)
        else:
            if not isinstance(full[sec], str):
                raise _err("expected string", sec)
    for k in ("seal_key_ref", "idp_key_ref"):
        if not full["trust"][k].startswith(("env:", "file:")):
            raise _err("secret must be a reference (env:/file:)", f"trust.{k}")
    if full["telemetry"]["log_level"] not in ("debug", "info", "warning", "error"):
        raise _err("unknown log level", "telemetry.log_level")
    if full["engine"]["kind"] != "node-v8":
        raise _err("unsupported engine kind", "engine.kind")
    if full["admission"]["max_per_tenant"] > full["admission"]["max_concurrent"]:
        raise _err("per-tenant concurrency cannot exceed global concurrency", "admission.max_per_tenant")
    profile(full)  # semantic check of the profile (alignment, address space)
    return full


def profile(cfg: dict[str, Any]) -> Profile:
    p = cfg["profile"]
    return Profile(region_base=p["region_base"], region_log2=p["region_log2"],
                   function_import_allowlist=tuple(p["function_import_allowlist"]),
                   allow_memory_grow=p["allow_memory_grow"], allow_memory_export=p["allow_memory_export"],
                   require_imported_memory=p["require_imported_memory"])


def limits(cfg: dict[str, Any]) -> Limits:
    lim = cfg["limits"]
    return Limits(max_module_bytes=lim["max_module_bytes"], max_functions=lim["max_functions"],
                  max_function_body_bytes=lim["max_function_body_bytes"],
                  max_total_instructions=lim["max_total_instructions"],
                  deadline_seconds=float(lim["deadline_seconds"]))


def digest(cfg: dict[str, Any]) -> str:
    return sha256_hex(canonical_json(cfg))


def load_json_strict(text: str) -> Any:
    """JSON parse that rejects duplicate keys and NaN/Infinity (parser-differential guard)."""
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        d: dict[str, Any] = {}
        for k, v in items:
            if k in d:
                raise _err("duplicate key", k)
            d[k] = v
        return d

    def bad_const(c: str) -> Any:
        raise _err("NaN/Infinity not permitted", c)

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=bad_const)
    except ValueError as exc:
        if isinstance(exc, SfiError):
            raise
        raise SfiError("SFI_SCHEMA_INVALID", "invalid JSON", reason=type(exc).__name__) from None


def _atomic_write(path: Path, data: bytes, *, exclusive: bool = False) -> None:
    """Write-temp + fsync + rename.  ``exclusive`` refuses to replace an existing file
    (immutable generations are never overwritten)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=path.suffix)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        if exclusive:
            try:
                os.link(tmp, path)
            except FileExistsError:
                raise SfiError("SFI_CONFIG_CONFLICT", "immutable file already exists", field=path.name) from None
            finally:
                os.unlink(tmp)
        else:
            os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


class GenerationStore:
    """Numbered, immutable config generations + an atomically swapped CURRENT pointer."""

    def __init__(self, root: Path, *, clock: Callable[[], float] = time.time,
                 fault: Optional[Callable[[str], None]] = None):
        self.root = Path(root)
        self.clock = clock
        self._fault = fault or (lambda stage: None)
        (self.root / "generations").mkdir(parents=True, exist_ok=True)

    def _gen_path(self, n: int) -> Path:
        return self.root / "generations" / f"gen-{n:06d}.json"

    def current_number(self) -> int:
        p = self.root / "CURRENT"
        if not p.exists():
            return 0
        try:
            return int(p.read_text().strip())
        except ValueError:
            raise _err("CURRENT pointer corrupted", "CURRENT") from None

    def read(self, n: int) -> dict[str, Any]:
        rec = load_json_strict(self._gen_path(n).read_text(encoding="utf-8"))
        cfg = validate(rec["config"])
        if rec.get("schema") != GENERATION_SCHEMA or rec["provenance"]["config_sha256"] != digest(cfg):
            raise _err("generation integrity check failed", f"gen-{n}")
        return rec

    def active(self) -> tuple[int, dict[str, Any]]:
        n = self.current_number()
        if n == 0:
            return 0, validate(dict(DEFAULTS))
        return n, self.read(n)["config"]

    def activate(self, cfg: dict[str, Any], *, author: str, source: str, approval: Optional[str],
                 expected_current: int) -> int:
        full = validate(cfg)  # stage + semantic checks before anything is written
        lock = self.root / ".activate.lock"
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise SfiError("SFI_CONFIG_CONFLICT", "another activation in progress",
                           generation=expected_current) from None
        try:
            cur = self.current_number()
            if cur != expected_current:
                raise SfiError("SFI_CONFIG_CONFLICT", "generation changed concurrently", generation=cur)
            n = max([cur] + self._numbers()) + 1
            rec = {"schema": GENERATION_SCHEMA, "generation": n, "config": full, "provenance": {
                "config_sha256": digest(full), "schema_version": CONFIG_SCHEMA, "author": author,
                "source": source, "approval": approval, "created_at": self.clock(), "supersedes": cur}}
            _atomic_write(self._gen_path(n), json.dumps(rec, sort_keys=True, indent=1).encode(), exclusive=True)
            self._fault("after-generation-write")
            _atomic_write(self.root / "CURRENT", f"{n}\n".encode())
            self._fault("after-pointer-swap")
            _atomic_write(self.root / "activations" / f"act-{n:06d}.json", canonical_json(
                {"generation": n, "activated_at": self.clock(), "author": author, "supersedes": cur}))
        finally:
            os.close(fd)
            os.unlink(lock)
        return n

    def rollback(self, to_generation: int, *, author: str, reason: str) -> int:
        rec = self.read(to_generation)  # target must itself be a complete valid generation
        return self.activate(rec["config"], author=author, source=f"rollback:{to_generation}:{reason}",
                             approval=rec["provenance"].get("approval"), expected_current=self.current_number())

    def _numbers(self) -> list[int]:
        return sorted(int(p.stem.split("-")[1]) for p in (self.root / "generations").glob("gen-*.json"))

    def recover(self) -> tuple[int, str]:
        """Startup: if the active generation is unreadable, fall back to the newest valid prior one."""
        try:
            n = self.current_number()
            if n:
                self.read(n)
            return n, "active-ok"
        except SfiError:
            for g in reversed(self._numbers()):
                try:
                    self.read(g)
                except SfiError:
                    continue
                _atomic_write(self.root / "CURRENT", f"{g}\n".encode())
                return g, "auto-rollback"
            return 0, "defaults"
