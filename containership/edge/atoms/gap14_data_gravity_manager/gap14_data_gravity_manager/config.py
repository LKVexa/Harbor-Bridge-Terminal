"""Production configuration loader/validator (G14-P0-11).

A configuration document is JSON, schema ``PK_GAP14_CONFIG/1``, signed by the
config authority.  Activation is transactional: the candidate is parsed,
verified, fully validated and only then swapped in atomically; a failure leaves
the previous revision active.  Revisions are strictly increasing, except via
explicit ``rollback()`` which re-activates a previously *verified* revision and
is itself audited.  Development/test conveniences are refused in production.
"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

from .errors import G14Error
from .resilience import DEFAULT_TTLS
from .trust import KeyRing, digest, exact_fields, ident, number

CONFIG_SCHEMA = "PK_GAP14_CONFIG/1"
CONFIG_ISSUER = "gap14-config-authority"
MODES = ("production", "staging", "development", "test")
DEV_FLAGS = ("allow_fixture_transports", "allow_fake_clock", "disable_audit_fsync")

# name: (default, minimum, maximum, reloadable, description)
KNOBS: Mapping[str, tuple[float, float, float, bool, str]] = MappingProxyType({
    "compute_relocation_cost": (25.0, 0.0, 1e6, True, "Base cost units to relocate compute"),
    "decision_deadline_s": (0.05, 0.005, 5.0, True, "End-to-end decision budget (SLO p99 50 ms)"),
    "dependency_timeout_s": (0.02, 0.001, 2.0, True, "Per-dependency call timeout cap"),
    "retry_max_attempts": (2, 1, 5, True, "Attempts for idempotent reads"),
    "breaker_failure_threshold": (5, 1, 100, False, "Consecutive failures before circuit opens"),
    "breaker_reset_s": (10.0, 0.1, 600.0, False, "Open-circuit cool-down"),
    "max_concurrent": (4, 1, 10_000, False, "Admission: concurrent decisions per process (CPU-bound; scale with processes)"),
    "max_per_tenant": (0, 0, 10_000, False, "Admission: per-tenant concurrent decisions (0 = max_concurrent)"),
    "max_payload_bytes": (262_144, 1024, 16 * 2**20, True, "Admission: request size"),
    "max_batch": (500, 1, 100_000, True, "Admission: datasets per batch/DAG"),
    "clock_skew_s": (5.0, 0.0, 60.0, True, "Allowed future-dating of artifacts"),
})


@dataclass(frozen=True)
class ActiveConfig:
    revision: int
    mode: str
    digest: str
    knobs: Mapping[str, float]
    ttls: Mapping[str, float]
    site_jurisdictions: Mapping[str, tuple[str, ...]]
    dev_flags: Mapping[str, bool]
    activated_at: float
    site_economics: Mapping[str, Any] = field(default_factory=dict)
    shadow_model: Mapping[str, float] | None = None
    canary_percent: float = 0.0

    def ref(self) -> dict[str, Any]:
        return {"revision": self.revision, "digest": self.digest, "mode": self.mode}


def _parse(body: Mapping[str, Any], at: float) -> ActiveConfig:
    exact_fields(body, "config", ["schema", "revision", "mode"], ["knobs", "ttls", "site_jurisdictions", "dev_flags", "site_economics", "shadow_model", "canary_percent"])
    if body["schema"] != CONFIG_SCHEMA:
        raise G14Error("G14_CONFIG_INVALID", "unsupported config schema")
    if body["mode"] not in MODES:
        raise G14Error("G14_CONFIG_INVALID", "invalid mode")
    revision = int(number(body["revision"], "config.revision", minimum=1, maximum=2**53))
    raw_knobs = body.get("knobs", {})
    if not isinstance(raw_knobs, Mapping) or set(raw_knobs) - set(KNOBS):
        raise G14Error("G14_CONFIG_INVALID", "unknown or malformed knobs", details={"unknown": sorted(set(raw_knobs) - set(KNOBS)) if isinstance(raw_knobs, Mapping) else None})
    knobs = {}
    for k, (default, lo, hi, _r, _d) in KNOBS.items():
        try:
            knobs[k] = number(raw_knobs.get(k, default), f"knobs.{k}", minimum=lo, maximum=hi)
        except G14Error as exc:
            raise G14Error("G14_CONFIG_INVALID", str(exc), details=exc.details) from None
    raw_ttls = body.get("ttls", {})
    if not isinstance(raw_ttls, Mapping) or set(raw_ttls) - set(DEFAULT_TTLS):
        raise G14Error("G14_CONFIG_INVALID", "unknown or malformed ttls")
    ttls = {k: number(raw_ttls.get(k, v), f"ttls.{k}", minimum=1.0, maximum=86400.0) for k, v in DEFAULT_TTLS.items()}
    sj = body.get("site_jurisdictions", {})
    if not isinstance(sj, Mapping):
        raise G14Error("G14_CONFIG_INVALID", "site_jurisdictions malformed")
    jur = {ident(s, "config.site"): tuple(sorted(ident(t, "config.jurisdiction") for t in tags)) for s, tags in sj.items()}
    flags = body.get("dev_flags", {})
    if not isinstance(flags, Mapping) or set(flags) - set(DEV_FLAGS) or any(not isinstance(v, bool) for v in flags.values()):
        raise G14Error("G14_CONFIG_INVALID", "dev_flags malformed")
    if body["mode"] == "production" and any(flags.values()):
        raise G14Error("G14_CONFIG_FORBIDDEN_IN_PRODUCTION", "dev/test flags enabled in production",
                       details={"flags": sorted(k for k, v in flags.items() if v)})
    if knobs["dependency_timeout_s"] > knobs["decision_deadline_s"]:
        raise G14Error("G14_CONFIG_INVALID", "dependency timeout exceeds decision deadline")
    from .planner import SiteEconomics
    econ_raw = body.get("site_economics", {})
    if not isinstance(econ_raw, Mapping):
        raise G14Error("G14_CONFIG_INVALID", "site_economics malformed")
    econ = {}
    for site_name, e in econ_raw.items():
        exact_fields(e, "config.site_economics", [], list(SiteEconomics.__dataclass_fields__))
        econ[ident(site_name, "config.site")] = SiteEconomics(**{k: number(v, f"site_economics.{k}", maximum=1e12) for k, v in e.items()})
    shadow = body.get("shadow_model")
    if shadow is not None:
        exact_fields(shadow, "config.shadow_model", ["revision", "compute_relocation_cost"])
        shadow = {"revision": ident(shadow["revision"], "shadow_model.revision"),
                  "compute_relocation_cost": number(shadow["compute_relocation_cost"], "shadow_model.compute_relocation_cost", maximum=1e6)}
    canary = number(body.get("canary_percent", 0.0), "config.canary_percent", maximum=100.0)
    if canary > 0 and shadow is None:
        raise G14Error("G14_CONFIG_INVALID", "canary_percent requires shadow_model")
    return ActiveConfig(revision, body["mode"], digest(body), MappingProxyType(knobs), MappingProxyType(ttls),
                        MappingProxyType(jur), MappingProxyType(dict(flags)), at, MappingProxyType(econ), shadow, canary)


class ConfigManager:
    def __init__(self, keyring: KeyRing, *, on_event: Callable[[str, Mapping[str, Any]], None] | None = None):
        self.keyring = keyring
        self._active: ActiveConfig | None = None
        self._history: dict[int, ActiveConfig] = {}
        self._lock = threading.Lock()
        self.on_event = on_event

    @property
    def active(self) -> ActiveConfig:
        if self._active is None:
            raise G14Error("G14_NOT_READY", "no configuration activated")
        return self._active

    @property
    def ready(self) -> bool:
        return self._active is not None

    def activate(self, document: Mapping[str, Any], now: float) -> ActiveConfig:
        try:
            exact_fields(document, "config.document", ["body", "sig"])
            self.keyring.verify(document["body"], document["sig"], expected_issuer=CONFIG_ISSUER, now=now)
            try:
                cfg = _parse(document["body"], now)
            except G14Error as exc:
                if exc.code == "G14_INVALID_REQUEST":
                    raise G14Error("G14_CONFIG_INVALID", str(exc), details=exc.details) from None
                raise
        except G14Error as exc:
            self._emit("config.rejected", {"code": exc.code})
            raise
        with self._lock:
            if self._history and cfg.revision <= max(self._history):
                self._emit("config.rejected", {"code": "G14_VERSION_ROLLBACK", "revision": cfg.revision})
                raise G14Error("G14_VERSION_ROLLBACK", "config revision not newer than active",
                               details={"highest": max(self._history), "candidate": cfg.revision})
            self._history[cfg.revision] = cfg
            self._active = cfg
        self._emit("config.activated", cfg.ref())
        return cfg

    def rollback(self, revision: int, now: float, actor: str) -> ActiveConfig:
        with self._lock:
            if revision not in self._history:
                raise G14Error("G14_CONFIG_INVALID", "unknown revision for rollback")
            import dataclasses
            self._active = dataclasses.replace(self._history[revision], activated_at=now)
            old = self._active
        self._emit("config.rolled_back", {**old.ref(), "actor": actor})
        return self._active

    def load_file(self, path: str | Path, now: float) -> ActiveConfig:
        raw = Path(path).read_bytes()
        if len(raw) > 1_048_576:
            raise G14Error("G14_CONFIG_INVALID", "config file too large")
        try:
            doc = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise G14Error("G14_CONFIG_INVALID", f"config is not JSON: {exc.msg}") from None
        return self.activate(doc, now)

    def _emit(self, event: str, payload: Mapping[str, Any]) -> None:
        if self.on_event:
            self.on_event(event, payload)


def knob_table() -> str:
    rows = ["| Knob | Default | Safe range | Reload | Purpose |", "|---|---|---|---|---|"]
    for k, (d, lo, hi, r, desc) in KNOBS.items():
        rows.append(f"| `{k}` | {d:g} | {lo:g} – {hi:g} | {'reloadable' if r else 'restart-bound'} | {desc} |")
    for k, v in DEFAULT_TTLS.items():
        rows.append(f"| `ttls.{k}` | {v:g} s | 1 – 86400 | reloadable | Freshness TTL |")
    return "\n".join(rows)
