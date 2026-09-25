"""Declarative configuration subsystem (MC-015).

Layering: base -> environment overlay -> site overlay (a site may *narrow*
but never widen: fewer devices, lower budgets, smaller quotas).  Every
revision is schema-validated, secret-free, carries author/activation
provenance, and is applied transactionally with atomic persistence and
rollback to the previous revision.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import pathlib
import threading
import time
from typing import Callable

from ..errors import Inv24Error
from ..schemas import validate
from ..security.secrets import forbid_inline_secrets

NARROW_ONLY = {"boot_budget_ms", "max_instances", "max_instances_per_tenant",
               "admission_queue_depth", "per_tenant_queue_depth"}


def merge_overlay(base: dict, overlay: dict, *, layer: str) -> dict:
    out = copy.deepcopy(base)
    for k, v in overlay.items():
        if k in NARROW_ONLY and k in out and isinstance(v, int) and v > out[k]:
            raise Inv24Error("CONFIG_REJECTED", f"{layer} overlay may not widen {k} ({out[k]} -> {v})")
        if k == "permitted_devices" and "permitted_devices" in out and not set(v) <= set(out[k]):
            raise Inv24Error("CONFIG_REJECTED", f"{layer} overlay may not add devices")
        out[k] = copy.deepcopy(v)
    return out


def digest(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class ConfigStore:
    """Transactional, versioned config with on-disk history and rollback."""

    def __init__(self, directory: str, *, clock=time.time) -> None:
        self.dir = pathlib.Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.clock = clock
        self._lock = threading.Lock()
        self._listeners: list[Callable[[dict], None]] = []
        self.active: dict | None = self._load_current()

    def _path(self, rev: int) -> pathlib.Path:
        return self.dir / f"config.r{rev:06d}.json"

    def _load_current(self) -> dict | None:
        cur = self.dir / "CURRENT"
        if not cur.exists():
            return None
        cfg = json.loads(self._path(int(cur.read_text().strip())).read_text())
        validate(cfg, "PK_MICROVM_CONFIG/1")
        return cfg

    def subscribe(self, fn: Callable[[dict], None]) -> None:
        self._listeners.append(fn)

    def _write_atomic(self, path: pathlib.Path, text: str) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)

    def propose(self, base: dict, *, environment: dict | None = None, site: dict | None = None,
                author: str) -> dict:
        cfg = merge_overlay(base, environment or {}, layer="environment")
        cfg = merge_overlay(cfg, site or {}, layer="site")
        cfg["author"] = author
        cfg["schema"] = "PK_MICROVM_CONFIG/1"
        cfg["revision"] = (self.active["revision"] + 1) if self.active else 1
        cfg["activated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.clock()))
        forbid_inline_secrets(cfg)
        validate(cfg, "PK_MICROVM_CONFIG/1")
        return cfg

    def activate(self, cfg: dict) -> dict:
        """Persist + switch atomically; listeners that raise roll the switch back."""
        validate(cfg, "PK_MICROVM_CONFIG/1")
        forbid_inline_secrets(cfg)
        with self._lock:
            expected = (self.active["revision"] + 1) if self.active else 1
            if cfg["revision"] != expected:
                raise Inv24Error("STALE_EPOCH", f"revision {cfg['revision']} != expected {expected}")
            previous = self.active
            self._write_atomic(self._path(cfg["revision"]), json.dumps(cfg, indent=2, sort_keys=True))
            self.active = cfg
            try:
                for fn in self._listeners:
                    fn(cfg)
            except Exception as exc:
                self.active = previous
                self._path(cfg["revision"]).unlink(missing_ok=True)
                raise Inv24Error("CONFIG_REJECTED", f"activation rolled back: {exc}") from None
            self._write_atomic(self.dir / "CURRENT", str(cfg["revision"]))
            return {"revision": cfg["revision"], "digest": digest(cfg), "author": cfg["author"]}

    def rollback(self, *, author: str) -> dict:
        with self._lock:
            if not self.active or self.active["revision"] < 2:
                raise Inv24Error("CONFIG_REJECTED", "no previous revision to roll back to")
            prev = json.loads(self._path(self.active["revision"] - 1).read_text())
        restored = dict(prev, revision=self.active["revision"] + 1, author=author,
                        activated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.clock())))
        return self.activate(restored)

    def history(self) -> list[int]:
        return sorted(int(p.stem.split(".r")[1]) for p in self.dir.glob("config.r*.json"))
