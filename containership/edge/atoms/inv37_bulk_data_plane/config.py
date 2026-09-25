"""Declarative configuration, layered profiles, preflight validation, provenance
and atomic activation with rollback (INV-37-C032..C040).

Format: JSON (stdlib only; no code execution).  Schema id ``INV37_CONFIG/1`` is
versioned independently of the package.  Layer precedence (low -> high):

    built-in defaults < site profile < environment profile < node override

Keys in ``NOT_OVERRIDABLE`` may only come from defaults; keys in ``INVARIANTS``
are security invariants that no layer can weaken.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

from .errors import ConfigError

CONFIG_SCHEMA = "INV37_CONFIG/1"
PROVENANCE_SCHEMA = "INV37_CONFIG_PROVENANCE/1"

_UNITS_BYTES = {"B": 1, "KiB": 1 << 10, "MiB": 1 << 20, "GiB": 1 << 30, "TiB": 1 << 40}
_UNITS_SECONDS = {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0, "d": 86400.0}
_SECRET_KEY = re.compile(r"(secret|password|passwd|token|private|credential)$|^key$|_key$", re.I)


def parse_bytes(value: Any, field_name: str) -> int:
    if type(value) is int and value >= 0:
        return value
    if isinstance(value, str):
        m = re.fullmatch(r"\s*(\d+)\s*(B|KiB|MiB|GiB|TiB)\s*", value)
        if m:
            return int(m.group(1)) * _UNITS_BYTES[m.group(2)]
    raise ConfigError("invalid byte quantity", field=field_name, value=str(value)[:64])


def parse_seconds(value: Any, field_name: str) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
        return float(value)
    if isinstance(value, str):
        m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(ms|s|m|h|d)\s*", value)
        if m:
            return float(m.group(1)) * _UNITS_SECONDS[m.group(2)]
    raise ConfigError("invalid duration", field=field_name, value=str(value)[:64])


# field path -> (kind, default).  kind: bytes | seconds | int | float | bool | str | enum:<a|b> | list | map
SCHEMA: dict[str, tuple[str, Any]] = {
    "profile": ("enum:dev|test|stage|prod|edge", "prod"),
    "limits.max_object_bytes": ("bytes", "1GiB"),
    "limits.max_chunk_bytes": ("bytes", "16MiB"),
    "limits.max_chunks": ("int", 262_144),
    "limits.max_concurrent_transfers": ("int", 8),
    "limits.max_pending_transfers": ("int", 32),
    "limits.max_mapped_bytes": ("bytes", "4GiB"),
    "limits.max_retry_attempts": ("int", 5),
    "limits.host_memory_budget": ("bytes", "8GiB"),
    "tenancy.default_max_active_transfers": ("int", 2),
    "tenancy.default_max_bytes_in_flight": ("bytes", "2GiB"),
    "tenancy.tenants": ("map", {}),
    "timeouts.admission": ("seconds", "0s"),
    "timeouts.idle_chunk": ("seconds", "30s"),
    "timeouts.total_transfer": ("seconds", "1h"),
    "timeouts.final_verification": ("seconds", "5m"),
    "timeouts.checkpoint_flush": ("seconds", "5s"),
    "timeouts.shutdown": ("seconds", "30s"),
    "retry.base_delay": ("seconds", "100ms"),
    "retry.max_delay": ("seconds", "10s"),
    "retry.max_attempts": ("int", 5),
    "retry.budget_ratio": ("float", 0.1),
    "transport.mode": ("enum:auto|shm|copy", "auto"),
    "transport.require_zero_copy": ("bool", False),
    "checkpoint.enabled": ("bool", True),
    "checkpoint.directory": ("str", ""),
    "checkpoint.retention": ("seconds", "7d"),
    "checkpoint.max_bytes": ("bytes", "64GiB"),
    "checkpoint.fsync": ("bool", True),
    "security.require_authentication": ("bool", True),
    "security.token_ttl": ("seconds", "15m"),
    "security.clock_skew": ("seconds", "30s"),
    "security.key_file": ("str", ""),
    "security.require_encryption_at_rest": ("bool", False),
    "security.allowed_regions": ("list", []),
    "telemetry.log_level": ("enum:debug|info|warning|error", "info"),
    "telemetry.trace_sample_ratio": ("float", 0.05),
    "telemetry.export": ("enum:none|stdout|file", "none"),
    "telemetry.file": ("str", ""),
    "telemetry.retention": ("seconds", "30d"),
}

INVARIANTS = {
    # Security invariants: a layer may tighten but never weaken.
    "security.require_authentication": lambda old, new: new or not old,
    "checkpoint.fsync": lambda old, new: new or not old,
}
# Fields that must not vary by site/environment/node (only defaults decide them).
NOT_OVERRIDABLE = {"limits.max_chunks"}


def _flatten(d: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, Mapping) and not (key in SCHEMA and SCHEMA[key][0] == "map"):
            out.update(_flatten(v, key + "."))
        else:
            out[key] = v
    return out


def _coerce(path: str, kind: str, value: Any) -> Any:
    if kind == "bytes":
        return parse_bytes(value, path)
    if kind == "seconds":
        return parse_seconds(value, path)
    if kind == "int":
        if type(value) is not int or value < 0:
            raise ConfigError("expected non-negative integer", field=path)
        return value
    if kind == "float":
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
            raise ConfigError("expected number in [0,1]", field=path)
        return float(value)
    if kind == "bool":
        if type(value) is not bool:
            raise ConfigError("expected boolean", field=path)
        return value
    if kind == "str":
        if not isinstance(value, str):
            raise ConfigError("expected string", field=path)
        return value
    if kind.startswith("enum:"):
        allowed = kind[5:].split("|")
        if value not in allowed:
            raise ConfigError("value not in enum", field=path, allowed=allowed)
        return value
    if kind == "list":
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            raise ConfigError("expected list of strings", field=path)
        return list(value)
    if kind == "map":
        if not isinstance(value, Mapping):
            raise ConfigError("expected object", field=path)
        return copy.deepcopy(dict(value))
    raise ConfigError("unknown schema kind", field=path)  # pragma: no cover


def _reject_inline_secrets(raw: Any, path: str = "") -> None:
    if isinstance(raw, Mapping):
        for k, v in raw.items():
            p = f"{path}.{k}" if path else k
            if isinstance(k, str) and _SECRET_KEY.search(k) and k != "key_file" and v not in ("", None):
                raise ConfigError("inline secret material is forbidden; use a *_file reference", field=p)
            _reject_inline_secrets(v, p)


def defaults() -> dict[str, Any]:
    return {p: _coerce(p, kind, dflt) for p, (kind, dflt) in SCHEMA.items()}


def load_layer(raw: Mapping[str, Any], *, layer: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ConfigError("config layer must be an object", layer=layer)
    schema = raw.get("schema", CONFIG_SCHEMA)
    if schema != CONFIG_SCHEMA:
        raise ConfigError("unsupported config schema", layer=layer, schema=str(schema), supported=CONFIG_SCHEMA)
    _reject_inline_secrets(raw)
    body = {k: v for k, v in raw.items() if k != "schema"}
    flat = _flatten(body)
    out = {}
    for path, value in flat.items():
        if path not in SCHEMA:
            raise ConfigError("unknown configuration key", layer=layer, field=path)
        if layer != "defaults" and path in NOT_OVERRIDABLE:
            raise ConfigError("key is not overridable by site/environment/node layers", layer=layer, field=path)
        out[path] = _coerce(path, SCHEMA[path][0], value)
    return out


def load_file(path: str | os.PathLike[str], *, layer: str, root: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    p = Path(path).resolve()
    if root is not None:
        r = Path(root).resolve()
        if r != p and r not in p.parents:
            raise ConfigError("config path escapes the approved config root", layer=layer)
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError("config file unreadable or malformed", layer=layer, error=type(exc).__name__) from None
    return load_layer(raw, layer=layer)


def merge(*layers: tuple[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Merge ``(name, flat_layer)`` pairs over the defaults, enforcing invariants."""
    eff = defaults()
    for name, layer in layers:
        for k, v in layer.items():
            if k in INVARIANTS and not INVARIANTS[k](eff[k], v):
                raise ConfigError("layer attempts to weaken a security invariant", layer=name, field=k)
            eff[k] = v
    return eff


@dataclass
class Finding:
    severity: str  # fatal | degraded | warning
    code: str
    field: str
    message: str


def preflight(eff: Mapping[str, Any], *, probe: Mapping[str, Any] | None = None,
              check_fs: bool = True) -> list[Finding]:
    """Deterministic, side-effect-free validation.  Any ``fatal`` finding means
    admission must stay disabled."""
    f: list[Finding] = []
    add = lambda sev, code, fld, msg: f.append(Finding(sev, code, fld, msg))  # noqa: E731
    if eff["limits.max_chunk_bytes"] <= 0 or eff["limits.max_object_bytes"] <= 0:
        add("fatal", "limit_nonpositive", "limits", "object/chunk limits must be positive")
    if eff["limits.max_chunk_bytes"] > eff["limits.max_object_bytes"] > 0:
        add("warning", "chunk_gt_object", "limits.max_chunk_bytes", "chunk limit exceeds object limit")
    if eff["limits.max_concurrent_transfers"] < 1:
        add("fatal", "concurrency_zero", "limits.max_concurrent_transfers", "must be >= 1")
    worst = eff["limits.max_concurrent_transfers"] * eff["limits.max_object_bytes"]
    if worst > eff["limits.host_memory_budget"]:
        add("fatal", "memory_budget_exceeded", "limits",
            f"worst-case receive memory {worst} exceeds host_memory_budget {eff['limits.host_memory_budget']}")
    if eff["limits.max_mapped_bytes"] > eff["limits.host_memory_budget"]:
        add("fatal", "mapped_budget_exceeded", "limits.max_mapped_bytes", "mapped bytes exceed host budget")
    if eff["retry.base_delay"] > eff["retry.max_delay"]:
        add("fatal", "retry_inverted", "retry", "base_delay > max_delay")
    if eff["profile"] in ("prod", "stage", "edge"):
        if not eff["security.require_authentication"]:
            add("fatal", "authn_disabled", "security.require_authentication", "authentication required outside dev/test")
        if eff["security.require_authentication"] and not eff["security.key_file"]:
            add("fatal", "key_file_missing", "security.key_file", "authentication requires key_file")
        if eff["checkpoint.enabled"] and not eff["checkpoint.directory"]:
            add("fatal", "checkpoint_dir_missing", "checkpoint.directory", "durable checkpointing needs a directory")
    if eff["security.require_encryption_at_rest"]:
        from .security import encryption_provider_available

        if not encryption_provider_available():
            add("fatal", "encryption_unavailable", "security.require_encryption_at_rest",
                "no approved at-rest encryption provider is installed")
    if check_fs:
        kf = eff["security.key_file"]
        if kf:
            p = Path(kf)
            if not p.is_file():
                add("fatal", "key_file_unreadable", "security.key_file", "key file not found")
            elif os.name == "posix" and p.stat().st_mode & 0o077:
                add("fatal", "key_file_permissions", "security.key_file", "key file must not be group/world accessible")
        d = eff["checkpoint.directory"]
        if eff["checkpoint.enabled"] and d:
            p = Path(d)
            if not p.is_dir() or not os.access(p, os.W_OK):
                add("fatal", "checkpoint_dir_unwritable", "checkpoint.directory", "directory missing or not writable")
            else:
                pkg = Path(__file__).resolve().parent
                if p.resolve() == pkg or pkg in p.resolve().parents:
                    add("fatal", "state_in_package", "checkpoint.directory", "state must not live in the installed package")
    if probe is not None:
        if eff["transport.require_zero_copy"] and not probe.get("shared_memory"):
            add("fatal", "zero_copy_unavailable", "transport.require_zero_copy", "platform lacks shared memory")
        elif eff["transport.mode"] == "shm" and not probe.get("shared_memory"):
            add("fatal", "shm_unavailable", "transport.mode", "shm requested but unsupported")
        elif eff["transport.mode"] == "auto" and not probe.get("shared_memory"):
            add("degraded", "copy_fallback", "transport.mode", "falling back to copy transport")
    if eff["telemetry.export"] == "file" and not eff["telemetry.file"]:
        add("fatal", "telemetry_file_missing", "telemetry.file", "file export needs a path")
    for name, t in eff["tenancy.tenants"].items():
        if not isinstance(t, Mapping):
            add("fatal", "tenant_malformed", f"tenancy.tenants.{name}", "tenant entry must be an object")
            continue
        unknown = set(t) - {"weight", "max_active_transfers", "max_bytes_in_flight", "regions"}
        if unknown:
            add("fatal", "tenant_unknown_key", f"tenancy.tenants.{name}", f"unknown keys {sorted(unknown)}")
        w = t.get("weight", 1)
        if type(w) is not int or not 1 <= w <= 1000:
            add("fatal", "tenant_weight", f"tenancy.tenants.{name}.weight", "weight must be int 1..1000")
    return f


def redacted(eff: Mapping[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in eff.items():
        out[k] = "<redacted-path>" if k.endswith("key_file") and v else v
    return out


def digest(eff: Mapping[str, Any]) -> str:
    blob = json.dumps(eff, sort_keys=True, separators=(",", ":"), default=str).encode()
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def atomic_write_json(path: Path, obj: Any, *, fsync: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, sort_keys=True, indent=1)
            fh.flush()
            if fsync:
                os.fsync(fh.fileno())
        os.replace(tmp, path)
        if fsync and os.name == "posix":
            dfd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


@dataclass
class ActiveConfig:
    effective: dict[str, Any]
    digest: str
    provenance: dict[str, Any]
    findings: list[Finding]

    @property
    def admission_allowed(self) -> bool:
        return not any(x.severity == "fatal" for x in self.findings)


@dataclass
class ConfigManager:
    """Atomic activation with automatic rollback (C037, C038).

    ``activate`` validates the candidate, swaps it in under a lock, runs the
    supplied health check, and restores the previous config if the check fails.
    Every activation/rollback appends a provenance record to ``history_path``
    (written atomically) when set.
    """

    history_path: Path | None = None
    probe: Mapping[str, Any] | None = None
    check_fs: bool = True
    active: ActiveConfig | None = None
    _previous: list[ActiveConfig] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def build(self, layers: list[tuple[str, Mapping[str, Any]]], *, author: str, source: str = "") -> ActiveConfig:
        eff = merge(*layers)
        findings = preflight(eff, probe=self.probe, check_fs=self.check_fs)
        dg = digest(eff)
        prov = {
            "schema": PROVENANCE_SCHEMA,
            "config_schema": CONFIG_SCHEMA,
            "digest": dg,
            "profile": eff["profile"],
            "layers": [n for n, _ in layers],
            "author": author,
            "source": source,
            "package_version": _pkg_version(),
            "created_at": time.time(),
            "activated_at": None,
            "previous_digest": self.active.digest if self.active else None,
        }
        return ActiveConfig(eff, dg, prov, findings)

    def dry_run(self, layers, *, author: str = "dry-run") -> ActiveConfig:
        return self.build(layers, author=author)

    def activate(self, candidate: ActiveConfig, *, health_check: Callable[[ActiveConfig], bool] | None = None) -> ActiveConfig:
        if not candidate.admission_allowed:
            fatal = [x.code for x in candidate.findings if x.severity == "fatal"]
            self._record("rejected", candidate, reason=",".join(fatal))
            raise ConfigError("candidate configuration has fatal findings", findings=fatal)
        with self._lock:
            prior = self.active
            candidate.provenance["activated_at"] = time.time()
            self.active = candidate
        ok = True
        try:
            ok = health_check(candidate) if health_check else True
        except Exception:  # noqa: BLE001 - any health-check failure triggers rollback
            ok = False
        if not ok:
            with self._lock:
                self.active = prior
            self._record("auto_rollback", candidate, reason="health_check_failed")
            raise ConfigError("health check failed; previous configuration restored",
                              restored=prior.digest if prior else None)
        if prior is not None:
            self._previous.append(prior)
        self._record("activated", candidate)
        return candidate

    def rollback(self, *, author: str) -> ActiveConfig:
        """Operator-driven rollback to the previous activated configuration."""
        with self._lock:
            if not self._previous:
                raise ConfigError("no previous configuration to roll back to")
            target = self._previous.pop()
            failed = self.active
            self.active = target
        self._record("operator_rollback", target, reason=f"by {author}; from {failed.digest if failed else None}")
        return target

    def _record(self, action: str, cfg: ActiveConfig, reason: str = "") -> None:
        if self.history_path is None:
            return
        hist: list[Any] = []
        if self.history_path.exists():
            try:
                hist = json.loads(self.history_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                hist = []
        hist.append({"action": action, "reason": reason, "at": time.time(), **cfg.provenance})
        atomic_write_json(self.history_path, hist[-500:])


def _pkg_version() -> str:
    try:
        return (Path(__file__).resolve().parent / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:  # pragma: no cover
        return "unknown"


def to_limits(eff: Mapping[str, Any]):
    from .data_plane import TransferLimits

    return TransferLimits(
        max_object_bytes=eff["limits.max_object_bytes"],
        max_chunk_bytes=eff["limits.max_chunk_bytes"],
        max_chunks=eff["limits.max_chunks"],
        max_concurrent_transfers=eff["limits.max_concurrent_transfers"],
    )
