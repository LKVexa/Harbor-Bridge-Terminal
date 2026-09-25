"""Declarative configuration for INV-52 (C032-C039, C035, C040).

A configuration is a JSON document ``PK_MSG_CONFIG/1``.  It is layered
(base -> environment -> site overlays, so one immutable artifact serves every
site), validated before activation, rejected on any secret material, and
activated atomically: a fresh ``PubSub`` policy is built completely and only
then swapped in under the manager lock.  Every activation records provenance
(version, author, time, digest, source layers) and the previous generation is
kept for operator or automatic rollback.
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import threading
from typing import Any, Callable, Iterable, Mapping

from .runtime import ACTIVE, TOPIC_STATES, InvalidArgument, MessagingError, PubSub
from .security import find_secrets

SCHEMA = "PK_MSG_CONFIG/1"

# Secure defaults: nothing is published without an explicit allow-list entry,
# every bound is finite, de-duplication is on, predicates see a read-only view.
DEFAULTS: dict[str, Any] = {
    "schema": SCHEMA,
    "metadata": {"name": "inv52", "version": "0", "author": "unknown"},
    "limits": {
        "max_routes_per_topic": 256,
        "max_dead_letters": 10_000,
        "max_payload_bytes": 1_048_576,
        "max_json_depth": 32,
        "max_decisions": 10_000,
        "max_topics": 10_000,
        "dedup_window": 4096,
    },
    "predicate_view": "frozen",
    "admission": {"per_app_rate": 1000.0, "per_app_burst": 2000},
    "topics": [],
    "telemetry": {"sample_rate": 1.0, "log_retention_events": 10_000, "export": ["metrics", "decisions"]},
}
LIMIT_RANGES = {
    "max_routes_per_topic": (1, 4096),
    "max_dead_letters": (1, 1_000_000),
    "max_payload_bytes": (256, 16 * 1_048_576),
    "max_json_depth": (2, 256),
    "max_decisions": (1, 1_000_000),
    "max_topics": (1, 1_000_000),
    "dedup_window": (0, 10_000_000),
}
TOP_KEYS = set(DEFAULTS)
EXPORTS = {"metrics", "decisions", "logs", "audit"}


class ConfigInvalid(MessagingError, ValueError):
    code = "PK_MSG_CONFIG_INVALID"


class ConfigRollbackUnavailable(MessagingError, RuntimeError):
    code = "PK_MSG_CONFIG_NO_PREVIOUS"


def merge(base: Mapping[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    """Deep merge; lists replace (so a site cannot silently append publishers)."""
    out = copy.deepcopy(dict(base))
    for k, v in overlay.items():
        if isinstance(v, Mapping) and isinstance(out.get(k), Mapping):
            out[k] = merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def layered(*layers: Mapping[str, Any]) -> dict[str, Any]:
    cfg: dict[str, Any] = copy.deepcopy(DEFAULTS)
    for layer in layers:
        cfg = merge(cfg, layer)
    return cfg


def digest(cfg: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate(cfg: Any) -> list[str]:
    """Return every problem found (empty list = valid).  Never raises."""
    p: list[str] = []
    if not isinstance(cfg, Mapping):
        return ["config must be an object"]
    if cfg.get("schema") != SCHEMA:
        p.append(f"schema must be {SCHEMA}")
    extra = set(cfg) - TOP_KEYS
    if extra:
        p.append("unknown top-level keys: " + ", ".join(sorted(map(str, extra))))
    secrets = find_secrets(cfg)
    if secrets:
        p.append("secret material is not allowed in configuration: " + ", ".join(secrets))
    md = cfg.get("metadata")
    if not isinstance(md, Mapping) or not all(isinstance(md.get(k), str) and md.get(k) for k in
                                              ("name", "version", "author")):
        p.append("metadata.name/version/author are required strings")
    lim = cfg.get("limits")
    if not isinstance(lim, Mapping):
        p.append("limits must be an object")
    else:
        for k, v in lim.items():
            if k not in LIMIT_RANGES:
                p.append(f"unknown limit {k}")
            elif isinstance(v, bool) or not isinstance(v, int) or not LIMIT_RANGES[k][0] <= v <= LIMIT_RANGES[k][1]:
                p.append(f"limit {k} must be an integer in {LIMIT_RANGES[k]}")
    if cfg.get("predicate_view") not in ("copy", "frozen"):
        p.append("predicate_view must be copy or frozen")
    adm = cfg.get("admission")
    if adm is not None:
        if not isinstance(adm, Mapping) or set(adm) - {"per_app_rate", "per_app_burst", "per_topic_rate",
                                                         "per_topic_burst"}:
            p.append("admission has unknown keys")
        else:
            r, b = adm.get("per_app_rate"), adm.get("per_app_burst")
            if isinstance(r, bool) or not isinstance(r, (int, float)) or not 0 < r <= 1e7:
                p.append("admission.per_app_rate must be in (0, 1e7]")
            if isinstance(b, bool) or not isinstance(b, int) or not 1 <= b <= 1e8:
                p.append("admission.per_app_burst must be an integer >= 1")
    topics = cfg.get("topics")
    if not isinstance(topics, list):
        p.append("topics must be a list")
    else:
        seen = set()
        for i, t in enumerate(topics):
            if not isinstance(t, Mapping) or not isinstance(t.get("name"), str) or not t.get("name"):
                p.append(f"topics[{i}].name required")
                continue
            if t["name"] in seen:
                p.append(f"duplicate topic {t['name']}")
            seen.add(t["name"])
            if set(t) - {"name", "publishers", "state", "owner", "residency"}:
                p.append(f"topics[{i}] has unknown keys")
            pubs = t.get("publishers", [])
            if not isinstance(pubs, list) or not all(isinstance(x, str) and x for x in pubs):
                p.append(f"topics[{i}].publishers must be a list of app ids")
            if "*" in pubs:
                p.append(f"topics[{i}]: wildcard publishers are not allowed (least privilege)")
            if t.get("state", ACTIVE) not in TOPIC_STATES:
                p.append(f"topics[{i}].state invalid")
    tel = cfg.get("telemetry")
    if not isinstance(tel, Mapping):
        p.append("telemetry must be an object")
    else:
        sr = tel.get("sample_rate")
        if isinstance(sr, bool) or not isinstance(sr, (int, float)) or not 0 <= sr <= 1:
            p.append("telemetry.sample_rate must be in [0, 1]")
        lr = tel.get("log_retention_events")
        if isinstance(lr, bool) or not isinstance(lr, int) or not 1 <= lr <= 1_000_000:
            p.append("telemetry.log_retention_events must be 1..1e6")
        ex = tel.get("export", [])
        if not isinstance(ex, list) or set(ex) - EXPORTS:
            p.append(f"telemetry.export must be a subset of {sorted(EXPORTS)}")
    return p


def build_bus(cfg: Mapping[str, Any], **runtime_kw: Any) -> PubSub:
    """Construct a fully-configured bus from a *validated* config (no partial state)."""
    from .resilience import QuotaAdmission

    lim = cfg["limits"]
    adm = cfg.get("admission")
    admission = QuotaAdmission(**adm, **({"clock": runtime_kw.pop("admission_clock")}
                                          if "admission_clock" in runtime_kw else {})) if adm else None
    bus = PubSub(predicate_view=cfg["predicate_view"], admission=admission, **lim, **runtime_kw)
    for t in cfg["topics"]:
        bus.allow(t["name"], *t.get("publishers", []))
        if t.get("state", ACTIVE) != ACTIVE:
            bus.set_topic_state(t["name"], t["state"], reason="configuration")
    return bus


class ConfigManager:
    """Atomic activation, provenance and rollback for the declarative policy.

    Subscriptions are application-owned runtime state: on activation they are
    carried over to the new bus so a policy change never silently drops a
    consumer.  Dead letters and counters stay with the generation that
    produced them (``generations`` keeps them reachable).
    """

    def __init__(self, *, health_check: Callable[[PubSub], bool] | None = None, history: int = 10,
                 clock: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.timezone.utc), **runtime_kw: Any):
        self._lock = threading.RLock()
        self.health_check = health_check
        self.history = history
        self.clock = clock
        self.runtime_kw = runtime_kw
        self.generations: list[dict[str, Any]] = []
        self.bus: PubSub | None = None

    @property
    def active(self) -> dict[str, Any] | None:
        with self._lock:
            return self.generations[-1] if self.generations else None

    def activate(self, *layers: Mapping[str, Any], author: str, change_ref: str | None = None,
                 layer_names: Iterable[str] | None = None) -> dict[str, Any]:
        cfg = layered(*layers)
        problems = validate(cfg)
        if problems:
            raise ConfigInvalid("configuration rejected", details={"problems": problems})
        if not isinstance(author, str) or not author.strip():
            raise InvalidArgument("author is required for provenance", details={"field": "author"})
        new_bus = build_bus(cfg, **dict(self.runtime_kw))  # fully built before any swap
        with self._lock:
            old = self.bus
            if old is not None:
                with old._lock:
                    for topic, routes in old.routes.items():
                        ids = old._route_ids_for(topic, len(routes))
                        for (pred, sink), _sid in zip(routes, ids):
                            new_bus.subscribe(topic, pred, sink)
            if self.health_check is not None and not self.health_check(new_bus):
                raise ConfigInvalid("post-build health check failed; previous configuration kept",
                                    details={"digest": digest(cfg)})
            record = {"digest": digest(cfg), "version": cfg["metadata"]["version"], "author": author,
                      "declared_author": cfg["metadata"]["author"], "activated_at": self.clock().isoformat(),
                      "change_ref": change_ref, "layers": list(layer_names or []), "config": cfg,
                      "bus": new_bus}
            self.bus = new_bus
            self.generations.append(record)
            if len(self.generations) > self.history:
                self.generations.pop(0)
            return self.provenance(record)

    def rollback(self, *, author: str, reason: str) -> dict[str, Any]:
        with self._lock:
            if len(self.generations) < 2:
                raise ConfigRollbackUnavailable("no previous configuration generation")
            failed = self.generations.pop()
            prev = self.generations[-1]
            out = self.activate(prev["config"], author=author, change_ref=f"rollback of {failed['digest'][:12]}: "
                                f"{reason}"[:512], layer_names=["rollback"])
            # activation appended a new generation equal to prev; drop the duplicate prev entry
            self.generations.remove(prev)
            return out

    @staticmethod
    def provenance(record: Mapping[str, Any]) -> dict[str, Any]:
        return {k: record[k] for k in ("digest", "version", "author", "declared_author", "activated_at",
                                       "change_ref", "layers")}


def load_json(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ConfigInvalid("configuration file must contain an object")
    return data
