"""Declarative configuration for PLN-05 (``PLN05_CONFIG/1``).

Layers merge in the precedence recorded in ``config/schema.json``; the whole
candidate is validated before activation; activation swaps one immutable
snapshot reference (readers never see a half-applied change) and is journalled
to disk with write-temp/fsync/rename so a crash leaves either the old or the
new configuration, never a torn one.  The previous snapshot is kept as
last-known-good for explicit rollback.

Decision (MC-10): activating configuration does not reset controller hysteresis
state; only a change of the capacity envelope does (see ``controller``).
"""
from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field
import hashlib
import json
import os
import pathlib
import re
import types

from .errors import PlaneError
from .keys import KeyRing

CONFIG_DIR = pathlib.Path(__file__).resolve().parent / "config"
SCHEMA = json.loads((CONFIG_DIR / "schema.json").read_text(encoding="utf-8"))
DEFAULTS = json.loads((CONFIG_DIR / "defaults.json").read_text(encoding="utf-8"))
LAYERS = tuple(SCHEMA["precedence"])
_SECRET_KEY = re.compile(r"(secret|token|password|passwd|private_key|api_key|credential)$", re.I)
_TOP = {"schema", "revision"} | {k.split(".")[0] for k in SCHEMA["fields"]}


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def checksum(obj) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


def _merge(base: dict, over: dict, path: str = "") -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        where = f"{path}{k}"
        if v is None:
            raise PlaneError("E_CONFIG_INVALID", "null is not a valid configuration value",
                             {"field": where[:64]})
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v, where + ".")
        else:
            out[k] = copy.deepcopy(v)
    return out


def _scan_secrets(obj, path: str = "") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if _SECRET_KEY.search(str(k)) and not (isinstance(v, str) and v.startswith("secretref://")):
                raise PlaneError("E_CONFIG_SECRET", "secret-bearing key must use a secretref:// reference",
                                 {"field": f"{path}{k}"[:64]})
            _scan_secrets(v, f"{path}{k}.")
    elif isinstance(obj, list):
        for v in obj:
            _scan_secrets(v, path)


def _get(obj: dict, dotted: str):
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, Mapping) or part not in cur:
            raise PlaneError("E_CONFIG_INVALID", "missing configuration field", {"field": dotted})
        cur = cur[part]
    return cur


def validate(cfg: dict) -> None:
    if not isinstance(cfg, dict) or cfg.get("schema") != "PLN05_CONFIG/1":
        raise PlaneError("E_CONFIG_INVALID", "unsupported configuration schema")
    rev = cfg.get("revision")
    if isinstance(rev, bool) or not isinstance(rev, int) or rev < 1:
        raise PlaneError("E_CONFIG_INVALID", "revision must be a positive integer")
    _scan_secrets(cfg)
    for k in cfg:
        if k not in _TOP and not str(k).startswith("x-"):
            raise PlaneError("E_CONFIG_INVALID", "unknown critical configuration key",
                             {"field": str(k)[:64]})
    for group in {k.split(".")[0] for k in SCHEMA["fields"] if "." in k}:
        allowed = {k.split(".", 1)[1] for k in SCHEMA["fields"] if k.startswith(group + ".")}
        sub = cfg.get(group, {})
        if not isinstance(sub, dict):
            raise PlaneError("E_CONFIG_INVALID", "configuration group must be an object", {"field": group})
        for k in sub:
            if k not in allowed and not str(k).startswith("x-"):
                raise PlaneError("E_CONFIG_INVALID", "unknown critical configuration key",
                                 {"field": f"{group}.{k}"[:64]})
    for name, (typ, lo, hi, _unit) in SCHEMA["fields"].items():
        v = _get(cfg, name)
        if typ == "boolean":
            ok = isinstance(v, bool)
        elif typ == "list_str":
            ok = (isinstance(v, list) and len(v) <= hi
                  and all(isinstance(x, str) and re.fullmatch(r"[a-z_]{1,32}", x) for x in v))
        else:
            ok = (not isinstance(v, bool) and isinstance(v, int if typ == "integer" else (int, float))
                  and v == v and lo <= v <= hi)
        if not ok:
            raise PlaneError("E_CONFIG_INVALID", "configuration field out of range", {"field": name})
    if _get(cfg, "retry.base_ms") > _get(cfg, "retry.max_ms"):
        raise PlaneError("E_CONFIG_INVALID", "retry.base_ms exceeds retry.max_ms", {"field": "retry.base_ms"})
    if _get(cfg, "lease.renew_before_s") >= _get(cfg, "lease.duration_s"):
        raise PlaneError("E_CONFIG_INVALID", "lease renewal must precede expiry", {"field": "lease.renew_before_s"})
    if _get(cfg, "control_reserve") >= _get(cfg, "queue_capacity"):
        raise PlaneError("E_CONFIG_INVALID", "control reserve must be below queue capacity", {"field": "control_reserve"})
    if _get(cfg, "stale_after_s") > _get(cfg, "degraded_after_s"):
        raise PlaneError("E_CONFIG_INVALID", "stale_after_s exceeds degraded_after_s", {"field": "stale_after_s"})


@dataclass(frozen=True)
class Snapshot:
    data: types.MappingProxyType
    checksum: str
    revision: int
    provenance: tuple
    activated_at: float

    def get(self, dotted: str):
        return _get(self.data, dotted)  # type: ignore[arg-type]

    def describe(self) -> dict:
        return {"schema": "PLN05_CONFIG/1", "revision": self.revision, "checksum": self.checksum,
                "activated_at": self.activated_at, "sources": [dict(p) for p in self.provenance]}


def compose(layers: dict[str, dict]) -> dict:
    """Merge named layers onto package defaults in declared precedence."""
    unknown = set(layers) - set(LAYERS)
    if unknown:
        raise PlaneError("E_CONFIG_INVALID", "unknown configuration layer")
    cfg = copy.deepcopy(DEFAULTS)
    for name in LAYERS[1:]:
        if name in layers:
            if not isinstance(layers[name], dict):
                raise PlaneError("E_CONFIG_INVALID", "layer must be an object", {"field": name})
            cfg = _merge(cfg, layers[name])
    return cfg


def _freeze(obj):
    if isinstance(obj, dict):
        return types.MappingProxyType({k: _freeze(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return tuple(_freeze(v) for v in obj)
    return obj


def _thaw(obj):
    if isinstance(obj, types.MappingProxyType):
        return {k: _thaw(v) for k, v in obj.items()}
    if isinstance(obj, tuple):
        return [_thaw(v) for v in obj]
    return obj


def diff(old: dict, new: dict, path: str = "") -> list[dict]:
    out = []
    for k in sorted(set(old) | set(new)):
        a, b = old.get(k, "<absent>"), new.get(k, "<absent>")
        if isinstance(a, dict) and isinstance(b, dict):
            out += diff(a, b, f"{path}{k}.")
        elif a != b:
            out.append({"field": f"{path}{k}", "from": a, "to": b})
    return out


def _atomic_write(path: pathlib.Path, data: bytes, crash_hook=None) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    if crash_hook:
        crash_hook("after-temp-write")
    os.replace(tmp, path)
    if crash_hook:
        crash_hook("after-rename")


class ConfigStore:
    """Holds the active snapshot and the last-known-good; optionally journals to ``directory``."""

    def __init__(self, ring: KeyRing, now: float, directory: str | os.PathLike | None = None) -> None:
        self.ring = ring
        self.dir = pathlib.Path(directory) if directory else None
        self.lkg: Snapshot | None = None
        self.active = self._build(copy.deepcopy(DEFAULTS),
                                  ({"layer": "package-defaults", "issuer": "package", "revision": 1},), now)
        if self.dir is not None:
            self.dir.mkdir(parents=True, exist_ok=True)
            recovered = self._recover(now)
            if recovered is not None:
                self.active = recovered

    def _build(self, cfg: dict, provenance: tuple, now: float) -> Snapshot:
        validate(cfg)
        return Snapshot(_freeze(cfg), checksum(cfg), cfg["revision"], provenance, now)

    def dry_run(self, layers: dict[str, dict]) -> dict:
        cand = compose(layers)
        validate(cand)
        return {"valid": True, "checksum": checksum(cand), "diff": diff(_thaw(self.active.data), cand)}

    def activate(self, layers: dict[str, dict], *, issuer: str, now: float, crash_hook=None) -> Snapshot:
        cand = compose(layers)
        validate(cand)
        if cand["revision"] <= self.active.revision:
            raise PlaneError("E_CONFIG_INVALID", "revision must increase", {"active": self.active.revision})
        prov = tuple({"layer": n, "issuer": issuer, "revision": cand["revision"]} for n in LAYERS if n in layers)
        snap = self._build(cand, ({"layer": "package-defaults", "issuer": "package", "revision": 1},) + prov, now)
        if self.dir is not None:
            self._persist(snap, crash_hook)
        self.lkg, self.active = self.active, snap  # single reference swap
        return snap

    def rollback(self, *, now: float) -> Snapshot:
        if self.lkg is None:
            raise PlaneError("E_CONFIG_NO_ROLLBACK", "no last-known-good configuration")
        restored = Snapshot(self.lkg.data, self.lkg.checksum, self.lkg.revision,
                            self.lkg.provenance + ({"layer": "rollback", "issuer": "rollback",
                                                    "revision": self.lkg.revision},), now)
        if self.dir is not None:
            self._persist(restored, None)
        self.lkg, self.active = None, restored
        return restored

    # -- journal ---------------------------------------------------------
    def _envelope(self, snap: Snapshot) -> bytes:
        body = {"config": _thaw(snap.data), "provenance": [dict(p) for p in snap.provenance],
                "activated_at": snap.activated_at, "checksum": snap.checksum}
        raw = canonical(body)
        kid, mac = self.ring.sign(raw, snap.activated_at)
        return canonical({"body": body, "kid": kid, "mac": mac})

    def _persist(self, snap: Snapshot, crash_hook) -> None:
        if self.dir is None:
            return
        _atomic_write(self.dir / "active.json", self._envelope(snap), crash_hook)
        with open(self.dir / "journal.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"revision": snap.revision, "checksum": snap.checksum,
                                 "at": snap.activated_at}) + "\n")

    def _recover(self, now: float) -> Snapshot | None:
        path = self.dir / "active.json"  # type: ignore[operator]
        stray = path.with_name("active.json.tmp")
        if stray.exists():
            stray.unlink()  # an interrupted write never becomes active
        if not path.exists():
            return None
        try:
            env = json.loads(path.read_bytes())
            self.ring.verify(env["kid"], canonical(env["body"]), env["mac"], now)
            body = env["body"]
            cfg = body["config"]
            if checksum(cfg) != body["checksum"]:
                raise ValueError("checksum")
            validate(cfg)
        except (ValueError, KeyError, TypeError, PlaneError):
            raise PlaneError("E_STATE_CORRUPT", "persisted configuration failed integrity check") from None
        return Snapshot(_freeze(cfg), body["checksum"], cfg["revision"],
                        tuple(body["provenance"]), body["activated_at"])
