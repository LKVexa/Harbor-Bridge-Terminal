"""Declarative configuration (checklist #26-#30, #32).

* Schema: ``schemas/config.schema.json`` (JSON Schema 2020-12), validated with a
  small built-in validator so bootstrap has no third-party dependency.
* Overlays: base -> environment -> site, deep-merged; lists replace, ``null`` deletes.
* Provenance: every activated config carries a SHA-256 digest of its canonical form
  plus the digests and names of the layers it came from.
* Activation is transactional: validate -> preflight hook -> swap under a lock.  On
  any failure the previous config stays active.  ``ConfigController.rollback``
  restores the previous N generations.
* Secret material is refused in configuration (only *references* are allowed).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
import json
import pathlib
import re
import threading
from typing import Callable

SCHEMA_PATH = pathlib.Path(__file__).with_name("schemas") / "config.schema.json"
_CREDENTIAL_KEYS = re.compile(r"(?i)^(password|secret_value|token|secret_id|private_key|api_key)$")


class ConfigError(ValueError):
    pass


def canonical_digest(obj) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if v is None:
            out.pop(k, None)
        elif isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _validate(node, schema: dict, path: str, root: dict) -> list[str]:
    """Subset of JSON Schema: type, required, properties, additionalProperties,
    enum, minimum, maximum, minLength, maxLength, pattern, items, maxItems, $ref(#/$defs)."""
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            return [f"{path}: unsupported $ref"]
        schema = root["$defs"][ref.split("/")[-1]]
    errs: list[str] = []
    t = schema.get("type")
    types = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}
    if t == "integer":
        if not isinstance(node, int) or isinstance(node, bool):
            return [f"{path}: expected integer"]
    elif t == "number":
        if not isinstance(node, (int, float)) or isinstance(node, bool):
            return [f"{path}: expected number"]
    elif t and not isinstance(node, types[t]):
        return [f"{path}: expected {t}"]
    if "enum" in schema and node not in schema["enum"]:
        errs.append(f"{path}: not in enum")
    if isinstance(node, (int, float)) and not isinstance(node, bool):
        if "minimum" in schema and node < schema["minimum"]:
            errs.append(f"{path}: below minimum")
        if "maximum" in schema and node > schema["maximum"]:
            errs.append(f"{path}: above maximum")
    if isinstance(node, str):
        if len(node) < schema.get("minLength", 0) or len(node) > schema.get("maxLength", 10**9):
            errs.append(f"{path}: length out of range")
        if "pattern" in schema and not re.search(schema["pattern"], node):
            errs.append(f"{path}: pattern mismatch")
    if isinstance(node, dict):
        for req in schema.get("required", []):
            if req not in node:
                errs.append(f"{path}.{req}: required")
        props = schema.get("properties", {})
        for k, v in node.items():
            if _CREDENTIAL_KEYS.match(k):
                errs.append(f"{path}.{k}: plaintext credential fields are forbidden in config")
            elif k in props:
                errs.extend(_validate(v, props[k], f"{path}.{k}", root))
            elif schema.get("additionalProperties", True) is False:
                errs.append(f"{path}.{k}: unknown key")
            elif isinstance(schema.get("additionalProperties"), dict):
                errs.extend(_validate(v, schema["additionalProperties"], f"{path}.{k}", root))
    if isinstance(node, list):
        if len(node) > schema.get("maxItems", 10**9):
            errs.append(f"{path}: too many items")
        if "items" in schema:
            for i, item in enumerate(node):
                errs.extend(_validate(item, schema["items"], f"{path}[{i}]", root))
    return errs


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_config(cfg: dict, schema: dict | None = None) -> list[str]:
    schema = schema or load_schema()
    return _validate(cfg, schema, "$", schema)


@dataclass(frozen=True)
class ActiveConfig:
    data: dict
    digest: str
    layers: tuple[tuple[str, str], ...]    # (layer name, layer digest)
    generation: int


def compose(layers: list[tuple[str, dict]]) -> tuple[dict, tuple[tuple[str, str], ...]]:
    merged: dict = {}
    prov = []
    for name, layer in layers:
        merged = deep_merge(merged, layer)
        prov.append((name, canonical_digest(layer)))
    return merged, tuple(prov)


@dataclass
class ConfigController:
    history_limit: int = 10
    preflight: Callable[[dict], None] | None = None
    _history: list[ActiveConfig] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def active(self) -> ActiveConfig | None:
        return self._history[-1] if self._history else None

    def activate(self, layers: list[tuple[str, dict]]) -> ActiveConfig:
        data, prov = compose(layers)
        errs = validate_config(data)
        if errs:
            raise ConfigError("; ".join(errs[:20]))
        if self.preflight:
            self.preflight(copy.deepcopy(data))      # may raise -> nothing activated
        with self._lock:
            gen = (self._history[-1].generation + 1) if self._history else 1
            new = ActiveConfig(data, canonical_digest(data), prov, gen)
            self._history.append(new)
            del self._history[:-self.history_limit]
            return new

    def rollback(self, steps: int = 1) -> ActiveConfig:
        with self._lock:
            if steps < 1 or steps >= len(self._history):
                raise ConfigError("no prior generation to roll back to")
            target = self._history[-1 - steps]
            gen = self._history[-1].generation + 1
            restored = ActiveConfig(target.data, target.digest, target.layers + (("rollback", target.digest),), gen)
            self._history.append(restored)
            del self._history[:-self.history_limit]
            return restored

    def provenance(self) -> dict:
        a = self.active
        if a is None:
            return {}
        return {"digest": a.digest, "generation": a.generation,
                "layers": [{"name": n, "digest": d} for n, d in a.layers]}


def load_layers(config_dir: pathlib.Path, environment: str, site: str | None = None) -> list[tuple[str, dict]]:
    """Deterministic bootstrap order: base.json, overlays/<env>.json, overlays/<env>.<site>.json."""
    layers = [("base", json.loads((config_dir / "base.json").read_text(encoding="utf-8")))]
    env = config_dir / "overlays" / f"{environment}.json"
    if not env.exists():
        raise ConfigError(f"unknown environment overlay {environment!r}")
    layers.append((f"env:{environment}", json.loads(env.read_text(encoding="utf-8"))))
    if site:
        s = config_dir / "overlays" / f"{environment}.{site}.json"
        if not s.exists():
            raise ConfigError(f"unknown site overlay {environment}.{site}")
        layers.append((f"site:{site}", json.loads(s.read_text(encoding="utf-8"))))
    return layers
