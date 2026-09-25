"""Declarative configuration for INV-17: schema, layered loader, provenance, atomic activation.

Controls: C032-C035 (declarative, validated, environment/site overlays, fail-closed on
invalid input), C036 (provenance), C037-C038 (atomic activation, rollback). Stdlib only;
the schema is ``config/stream-config.schema.json`` and is enforced by the small JSON
Schema subset validator below (type, required, properties, additionalProperties,
minimum, maximum, enum, pattern) -- no third-party dependency.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Mapping

from .security import canonical
from .stream import StreamConfig, StreamError

HERE = Path(__file__).resolve().parent
SCHEMA_PATH = HERE / "config" / "stream-config.schema.json"
DEFAULTS_PATH = HERE / "config" / "defaults.json"


class ConfigInvalid(StreamError, ValueError):
    code = "PK_STREAM_CONFIG_INVALID"


class ActivationFailed(StreamError):
    code = "PK_STREAM_CONFIG_ACTIVATION_FAILED"


_TYPES: dict[str, type | tuple[type, ...]] = {"object": dict, "integer": int, "number": (int, float), "string": str,
                                             "boolean": bool, "array": list}


def validate(instance: Any, schema: Mapping[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    t = schema.get("type")
    if t:
        py = _TYPES[t]
        ok = isinstance(instance, py) and not (t in ("integer", "number") and isinstance(instance, bool))
        if not ok:
            return [f"{path}: expected {t}, got {type(instance).__name__}"]
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} not in {schema['enum']}")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: {instance} < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: {instance} > maximum {schema['maximum']}")
    if isinstance(instance, str) and "pattern" in schema and not re.fullmatch(schema["pattern"], instance):
        errors.append(f"{path}: {instance!r} does not match {schema['pattern']}")
    if isinstance(instance, dict):
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in instance:
                errors.append(f"{path}: missing required '{req}'")
        for key, value in instance.items():
            if key in props:
                errors.extend(validate(value, props[key], f"{path}.{key}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unknown key '{key}'")
            elif isinstance(schema.get("additionalProperties"), dict):
                errors.extend(validate(value, schema["additionalProperties"], f"{path}.{key}"))
    if isinstance(instance, list) and "items" in schema:
        for i, item in enumerate(instance):
            errors.extend(validate(item, schema["items"], f"{path}[{i}]"))
    return errors


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def merge(base: Mapping[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    """Deep merge; overlays replace scalars and lists, recurse into objects."""
    out = copy.deepcopy(dict(base))
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_layers(*layers: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    """defaults -> environment -> site -> tenant overlays, validated after merging."""
    doc: dict[str, Any] = json.loads(DEFAULTS_PATH.read_text(encoding="utf-8"))
    for layer in layers:
        if isinstance(layer, (str, Path)):
            try:
                layer = json.loads(Path(layer).read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise ConfigInvalid("overlay unreadable", source=str(layer), error=str(exc)) from None
        if not isinstance(layer, dict):
            raise ConfigInvalid("overlay must be an object")
        doc = merge(doc, layer)
    errors = validate(doc, load_schema())
    if errors:
        raise ConfigInvalid("configuration failed schema validation", errors=errors[:20])
    if doc["stream"]["max_buffer"] > doc["stream"]["max_credit"] * 64:
        raise ConfigInvalid("max_buffer may not exceed 64x max_credit (cross-field rule CFG-X1)")
    return doc


def to_stream_config(doc: Mapping[str, Any]) -> StreamConfig:
    s = doc["stream"]
    return StreamConfig(max_credit=s["max_credit"], max_buffer=s["max_buffer"],
                        idempotency_window=s.get("idempotency_window", 1024))


@dataclass(frozen=True)
class Provenance:
    """C036 provenance envelope for an effective configuration."""

    author: str
    source_revision: str
    sources: tuple[str, ...]
    digest: str
    activated_at: float
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {"author": self.author, "source_revision": self.source_revision, "sources": list(self.sources),
                "digest": self.digest, "activated_at": self.activated_at, "reason": self.reason}


def digest(doc: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical(doc)).hexdigest()


class ConfigManager:
    """Atomic activation with validation, health check and automatic rollback.

    ``activate`` validates the candidate completely before any swap; the swap is one
    reference assignment under a lock, so readers observe either the old or the new
    configuration, never a mix. If the post-activation health probe fails, the previous
    configuration is restored and ``ActivationFailed`` is raised.
    """

    def __init__(self, initial: Mapping[str, Any] | None = None, *, audit=None,
                 clock: Callable[[], float] = time.time, history: int = 16) -> None:
        self._lock = RLock()
        self._clock = clock
        self._audit = audit
        self._history: list[tuple[dict[str, Any], Provenance]] = []
        self._max_history = history
        doc = load_layers(initial or {})
        self._current = (doc, Provenance("bootstrap", "unknown", ("defaults",), digest(doc), clock(), "bootstrap"))

    @property
    def current(self) -> dict[str, Any]:
        return copy.deepcopy(self._current[0])

    @property
    def provenance(self) -> Provenance:
        return self._current[1]

    def activate(self, *overlays: Mapping[str, Any], author: str, source_revision: str, reason: str,
                 health_probe: Callable[[dict[str, Any]], bool] | None = None) -> Provenance:
        if not author or not source_revision:
            raise ConfigInvalid("author and source_revision are mandatory provenance fields")
        candidate = load_layers(*overlays)  # raises before any state change
        to_stream_config(candidate)  # runtime-level validation too
        prov = Provenance(author, source_revision, tuple(f"overlay[{i}]" for i in range(len(overlays))),
                          digest(candidate), self._clock(), reason)
        with self._lock:
            previous = self._current
            self._current = (candidate, prov)
            self._history.append(previous)
            del self._history[:-self._max_history]
            ok = True
            if health_probe is not None:
                try:
                    ok = bool(health_probe(copy.deepcopy(candidate)))
                except Exception:  # probe crash counts as failure
                    ok = False
            if not ok:
                self._current = self._history.pop()
                if self._audit:
                    self._audit.record("config.rollback", author, prov.digest, "auto", reason="health probe failed")
                raise ActivationFailed("post-activation health probe failed; rolled back", digest=prov.digest)
            if self._audit:
                self._audit.record("config.activate", author, prov.digest, "applied", revision=source_revision)
            return prov

    def rollback(self, *, author: str, reason: str) -> Provenance:
        with self._lock:
            if not self._history:
                raise ActivationFailed("no previous configuration to roll back to")
            self._current = self._history.pop()
            if self._audit:
                self._audit.record("config.rollback", author, self._current[1].digest, "applied", reason=reason)
            return self._current[1]
