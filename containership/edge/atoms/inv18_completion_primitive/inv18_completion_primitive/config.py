"""Declarative configuration, fail-closed validation, layering, provenance and
atomic activation with rollback (C032-C039).

Only stdlib.  Configuration is data; it never rewrites package files (C032).
Secrets never appear as values: security-sensitive keys accept only
``secret://`` references (C039).
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Mapping

from .errors import ErrorRecord, Rejected

CONFIG_SCHEMA_VERSION = 1
ENV_PREFIX = "INV18_CFG_"   # distinct from operational variables (INV18_RELEASE_KEY, INV18_CONTEXT, ...)

# key: (type, min, max, enum, security_critical, description)
SCHEMA: dict[str, tuple] = {
    "schema_version": (int, 1, 1, None, True, "configuration schema version"),
    "environment": (str, None, None, ("dev", "test", "staging", "prod"), False, "deployment environment"),
    "site": (str, None, None, None, False, "site identifier (<=64 chars)"),
    "context": (str, None, None, ("cloud", "datacenter", "near-edge", "far-edge", "local"), False, "deployment context (C012)"),
    "max_outstanding": (int, 1, 10_000_000, None, True, "hard limit of live futures per process"),
    "soft_outstanding": (int, 1, 10_000_000, None, False, "soft limit; above it status is DEGRADED"),
    "max_per_tenant": (int, 1, 10_000_000, None, True, "hard limit of live futures per tenant"),
    "max_payload_bytes": (int, 1, 64 * 1024 * 1024, None, True, "max serialized payload at wire adapters"),
    "max_id_len": (int, 8, 256, None, True, "max identifier length"),
    "max_metadata_bytes": (int, 0, 65536, None, True, "max metadata/details bytes"),
    "max_diag_records": (int, 16, 1_000_000, None, False, "bounded diagnostic/decision record ring"),
    "telemetry_queue_max": (int, 16, 1_000_000, None, False, "bounded log/telemetry queue"),
    "stall_threshold_s": (float, 0.001, 86400.0, None, False, "age after which an unresolved future is 'stalled'"),
    "stall_ratio_degraded": (float, 0.0, 1.0, None, False, "fraction of stalled futures that makes status DEGRADED"),
    "log_payloads": (bool, None, None, None, True, "log raw payloads (must stay false outside privileged diagnostics)"),
    "diagnostics_privileged": (bool, None, None, None, True, "privileged high-cardinality diagnostics"),
    "network_exposure": (str, None, None, ("none", "loopback", "mtls"), True, "network exposure of adapters"),
    "auth_required": (bool, None, None, None, True, "authentication required at adapters"),
    "trace_sampling": (float, 0.0, 1.0, None, False, "trace sampling ratio"),
    "log_rate_limit_per_s": (int, 1, 1_000_000, None, False, "structured log rate limit"),
    "retry_max_attempts": (int, 0, 10, None, False, "adapter retry attempts"),
    "retry_base_delay_s": (float, 0.0, 10.0, None, False, "adapter backoff base"),
    "retry_max_total_s": (float, 0.0, 600.0, None, False, "adapter total retry budget"),
    "circuit_failure_threshold": (int, 1, 1000, None, False, "failures before circuit opens"),
    "circuit_reset_s": (float, 0.01, 3600.0, None, False, "open -> half-open delay"),
    "circuit_close_successes": (int, 1, 100, None, False, "half-open successes before close (hysteresis)"),
    "policy_max_stale_s": (float, 0.0, 86400.0, None, True, "max age of cached security policy"),
    "credential_ttl_max_s": (int, 1, 86400, None, True, "max accepted token lifetime"),
    "signing_key_ref": (str, None, None, None, True, "secret:// reference to the adapter signing key"),
}
REQUIRED = ("schema_version", "environment", "max_outstanding", "max_per_tenant")
SECRET_KEYS = ("signing_key_ref",)
NULLABLE = ("signing_key_ref", "site")

DEFAULTS: dict[str, Any] = {
    "schema_version": 1,
    "environment": "dev",
    "site": "local",
    "context": "local",
    "max_outstanding": 100_000,
    "soft_outstanding": 80_000,
    "max_per_tenant": 10_000,
    "max_payload_bytes": 1 << 20,
    "max_id_len": 128,
    "max_metadata_bytes": 4096,
    "max_diag_records": 1024,
    "telemetry_queue_max": 10_000,
    "stall_threshold_s": 30.0,
    "stall_ratio_degraded": 0.10,
    "log_payloads": False,
    "diagnostics_privileged": False,
    "network_exposure": "none",
    "auth_required": True,
    "trace_sampling": 0.1,
    "log_rate_limit_per_s": 1000,
    "retry_max_attempts": 3,
    "retry_base_delay_s": 0.05,
    "retry_max_total_s": 5.0,
    "circuit_failure_threshold": 5,
    "circuit_reset_s": 1.0,
    "circuit_close_successes": 2,
    "policy_max_stale_s": 300.0,
    "credential_ttl_max_s": 900,
    "signing_key_ref": None,
}


def _err(key: str, msg: str) -> ErrorRecord:
    return ErrorRecord("INVALID_CONFIG", msg, {"key": key})


def validate(cfg: Mapping[str, Any]) -> list[ErrorRecord]:
    """Whole-document validation; returns every error (empty list = valid)."""
    errors: list[ErrorRecord] = []
    if not isinstance(cfg, Mapping):
        return [_err("$", "configuration must be an object")]
    for k in cfg:
        if k not in SCHEMA:
            errors.append(_err(str(k), "unknown configuration key (rejected by default)"))
    for k in REQUIRED:
        if k not in cfg:
            errors.append(_err(k, "required key missing"))
    for k, v in cfg.items():
        if k not in SCHEMA:
            continue
        typ, lo, hi, enum, _sec, _d = SCHEMA[k]
        if v is None and k in NULLABLE:
            continue
        if typ is float and isinstance(v, int) and not isinstance(v, bool):
            v = float(v)
        if not isinstance(v, typ) or (typ is not bool and isinstance(v, bool)):
            errors.append(_err(k, f"expected {typ.__name__}"))
            continue
        if isinstance(v, float) and v != v:
            errors.append(_err(k, "NaN not allowed"))
            continue
        if lo is not None and v < lo:
            errors.append(_err(k, f"below minimum {lo}"))
        if hi is not None and v > hi:
            errors.append(_err(k, f"above maximum {hi}"))
        if enum is not None and v not in enum:
            errors.append(_err(k, f"must be one of {enum}"))
        if typ is str and len(v) > 256:
            errors.append(_err(k, "string too long"))
    if cfg.get("schema_version") not in (None, CONFIG_SCHEMA_VERSION) and not any(
            e.details.get("key") == "schema_version" for e in errors):
        errors.append(_err("schema_version", "unsupported schema version"))
    # cross-field (incompatible combinations)
    so, mo, mt = cfg.get("soft_outstanding"), cfg.get("max_outstanding"), cfg.get("max_per_tenant")
    if isinstance(so, int) and isinstance(mo, int) and so > mo:
        errors.append(_err("soft_outstanding", "soft limit must not exceed hard limit"))
    if isinstance(mt, int) and isinstance(mo, int) and mt > mo:
        errors.append(_err("max_per_tenant", "per-tenant limit must not exceed process limit"))
    if cfg.get("network_exposure") not in (None, "none") and cfg.get("auth_required") is False:
        errors.append(_err("auth_required", "network exposure requires authentication"))
    if cfg.get("network_exposure") == "mtls" and not cfg.get("signing_key_ref"):
        errors.append(_err("signing_key_ref", "mtls exposure requires a signing key reference"))
    if cfg.get("log_payloads") and not cfg.get("diagnostics_privileged"):
        errors.append(_err("log_payloads", "payload logging only allowed in privileged diagnostics"))
    if cfg.get("environment") == "prod" and cfg.get("log_payloads"):
        errors.append(_err("log_payloads", "payload logging forbidden in prod"))
    for k in SECRET_KEYS:
        v = cfg.get(k)
        if v is not None and isinstance(v, str) and not v.startswith("secret://"):
            errors.append(_err(k, "secret values are forbidden; use a secret:// reference"))
    return errors


def digest(cfg: Mapping[str, Any]) -> str:
    blob = json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def layer(*layers: Mapping[str, Any] | None) -> dict[str, Any]:
    """Deterministic layering: defaults -> environment -> site -> instance (later wins)."""
    out: dict[str, Any] = {}
    for lay in layers:
        if lay:
            out.update(copy.deepcopy(dict(lay)))
    return out


def from_env(environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Allow-listed ``INV18_CFG_<KEY>`` injection; unknown INV18_CFG_ variables are errors."""
    environ = os.environ if environ is None else environ
    out: dict[str, Any] = {}
    for name, raw in environ.items():
        if not name.startswith(ENV_PREFIX):
            continue
        key = name[len(ENV_PREFIX):].lower()
        if key not in SCHEMA:
            raise Rejected(f"unknown configuration variable {name}", code="INVALID_CONFIG", details={"key": name})
        typ = SCHEMA[key][0]
        try:
            if typ is bool:
                if raw.lower() not in ("true", "false"):
                    raise ValueError(raw)
                out[key] = raw.lower() == "true"
            else:
                out[key] = typ(raw)
        except ValueError:
            raise Rejected(f"{name} is not a valid {typ.__name__}", code="INVALID_CONFIG", details={"key": name}) from None
    return out


def load_file(path: str | os.PathLike) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    data.pop("$comment", None)
    return data


@dataclass(frozen=True)
class Revision:
    """Configuration provenance record (C036)."""
    revision_id: str
    schema_version: int
    digest: str
    author: str
    approver: str | None
    environment: str
    site: str | None
    activated_at: float
    supersedes: str | None
    rollback_of: str | None
    values: Mapping[str, Any] = field(repr=False, compare=False, default_factory=dict)

    def public(self) -> dict:
        return {k: getattr(self, k) for k in ("revision_id", "schema_version", "digest", "author",
                                              "approver", "environment", "site", "activated_at",
                                              "supersedes", "rollback_of")}


class ConfigStore:
    """Atomic, validated activation with last-known-good rollback (C034, C037, C038).

    Readers call :meth:`active` and always get one complete immutable revision:
    activation swaps a single reference under a lock, so no reader can observe a
    mix of old and new values.
    """

    def __init__(self, initial: Mapping[str, Any] | None = None, *, author: str = "bootstrap",
                 approver: str | None = None, clock=time.time, audit=None):
        self._lock = threading.Lock()
        self._clock = clock
        self._history: list[Revision] = []
        self._active: Revision | None = None
        self._audit = audit
        self.activate(layer(DEFAULTS, initial), author=author, approver=approver)

    def active(self) -> Revision:
        rev = self._active
        assert rev is not None
        return rev

    def values(self) -> Mapping[str, Any]:
        return self.active().values

    @property
    def history(self) -> tuple[Revision, ...]:
        return tuple(self._history)

    def stage(self, candidate: Mapping[str, Any]) -> dict[str, Any]:
        """Parse/validate a complete candidate without mutating anything."""
        cand = copy.deepcopy(dict(candidate))
        errs = validate(cand)
        if errs:
            raise Rejected("configuration rejected", code="INVALID_CONFIG",
                           details={"errors": "; ".join(f"{e.details.get('key')}: {e.message}" for e in errs[:8])})
        return cand

    def activate(self, candidate: Mapping[str, Any], *, author: str, approver: str | None = None,
                 _rollback_of: str | None = None, _fail_after_stage: bool = False) -> Revision:
        cand = self.stage(candidate)
        if _fail_after_stage:  # fault-injection hook: crash between stage and commit
            raise Rejected("injected activation failure", code="DEPENDENCY_UNAVAILABLE")
        d = digest(cand)
        frozen = _Frozen(cand)
        with self._lock:
            prev = self._active
            rev = Revision(revision_id="cfg-" + d[:16], schema_version=cand["schema_version"], digest=d,
                           author=author, approver=approver, environment=cand["environment"],
                           site=cand.get("site"), activated_at=self._clock(),
                           supersedes=prev.revision_id if prev else None, rollback_of=_rollback_of,
                           values=frozen)
            self._history.append(rev)
            self._active = rev          # single atomic reference swap
        if self._audit is not None:
            self._audit("config.activate", {"old": rev.supersedes, "new": rev.revision_id,
                                            "rollback_of": _rollback_of, "author": author})
        return rev

    def rollback(self, *, author: str, reason: str) -> Revision:
        """Operator/automatic rollback to the previous known-good revision."""
        with self._lock:
            if len(self._history) < 2:
                raise Rejected("no previous revision to roll back to", code="INVALID_ARGUMENT")
            cur = self._active
            prev = next(r for r in reversed(self._history[:-1]) if r.revision_id != cur.revision_id) \
                if any(r.revision_id != cur.revision_id for r in self._history[:-1]) else None
        if prev is None:
            raise Rejected("no distinct previous revision", code="INVALID_ARGUMENT")
        rev = self.activate(dict(prev.values), author=author, approver=prev.approver, _rollback_of=cur.revision_id)
        if self._audit is not None:
            self._audit("config.rollback", {"from": cur.revision_id, "to": rev.revision_id, "reason": reason})
        return rev

    def activate_or_rollback(self, candidate: Mapping[str, Any], *, author: str, health_check) -> Revision:
        """Activate, run a health check, restore last-known-good automatically on failure."""
        rev = self.activate(candidate, author=author)
        try:
            ok = bool(health_check(rev))
        except Exception:
            ok = False
        if not ok:
            return self.rollback(author="auto-rollback", reason=f"health check failed for {rev.revision_id}")
        return rev


class _Frozen(dict):
    """Read-only mapping snapshot."""

    def _ro(self, *a, **k):
        raise TypeError("configuration revisions are immutable")

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _ro  # type: ignore[assignment]
