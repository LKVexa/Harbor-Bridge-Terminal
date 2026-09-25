"""Declarative, versioned packing configuration with transactional lifecycle.

INV-68 MC-10 (C032-C038), MC-11 (C039), MC-19 (C056/C058), MC-37 (C095).

* ``PK_PACK_CONFIG/1`` (``schemas/PK_PACK_CONFIG_1.schema.json``) moves the
  policy that 4.2.0 kept in code and call arguments -- headroom, the CPU
  overcommit ratio, payload/concurrency/queue/timeout limits, capacity staleness
  and tenant quotas -- into one validated, immutable document.  Memory
  overcommit is deliberately *not* configurable: the key does not exist and any
  attempt to add it is an unknown-key error.
* :data:`DEFAULTS` are the secure defaults (fail closed, conservative limits).
* :func:`compose` applies ``base -> environment -> site`` overlays (RFC 7386
  merge-patch semantics on an allow-listed key set) and records which layers
  contributed.
* :func:`validate` rejects unknown keys, out-of-range values, non-finite numbers
  and inline secret material (``SECRET_IN_CONFIG``); configuration may only
  hold ``secretref://`` references.
* :class:`ConfigStore` is the only mutable state INV-68 owns.  Activation is a
  compare-and-swap on the active digest plus a monotonic controller *epoch*
  (split-brain fence): snapshot written, fsynced, journal appended, then the
  ``ACTIVE`` pointer swapped with ``os.replace``.  A crash at any point leaves
  either the old or the new configuration active, never a mixture; restart
  re-verifies every digest and falls back to the last intact journal entry.
  ``rollback()`` re-activates the previous snapshot as a new, audited
  activation.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

from .errors import PackError
from .packing import MAX_CPU_OVERCOMMIT
from .redaction import find_secrets

CONFIG_SCHEMA = "PK_PACK_CONFIG/1"

DEFAULTS: Mapping[str, Any] = MappingProxyType({
    "schema": CONFIG_SCHEMA,
    "config_version": "0.0.0-defaults",
    "headroom": 0.1,
    "cpu_overcommit": 1.5,
    "limits": {
        "max_workloads": 10_000,
        "max_payload_bytes": 4 * 1024 * 1024,
        "max_name_length": 253,
        "max_concurrency": 8,
        "max_queue": 32,
        "request_timeout_ms": 2_000,
        "capacity_staleness_s": 60,
    },
    "tenants": {
        "default_quota": {"max_workloads_per_request": 2_000, "max_requests_per_minute": 120},
        "overrides": {},
    },
    "provenance": {"author": "defaults", "change_ref": "none", "created": "1970-01-01T00:00:00Z"},
})

# key -> (type, min, max); ints are inclusive ranges
_LIMIT_RULES: Mapping[str, tuple[type, float, float]] = {
    "max_workloads": (int, 1, 1_000_000),
    "max_payload_bytes": (int, 1_024, 256 * 1024 * 1024),
    "max_name_length": (int, 1, 4_096),
    "max_concurrency": (int, 1, 1_024),
    "max_queue": (int, 0, 100_000),
    "request_timeout_ms": (int, 1, 600_000),
    "capacity_staleness_s": (int, 1, 86_400),
}
_QUOTA_RULES: Mapping[str, tuple[type, float, float]] = {
    "max_workloads_per_request": (int, 1, 1_000_000),
    "max_requests_per_minute": (int, 1, 1_000_000),
}
_TOP_KEYS = {"schema", "config_version", "headroom", "cpu_overcommit", "limits", "tenants", "provenance"}
_PROV_KEYS = {"author", "change_ref", "created", "layers"}


def canonical(doc: Mapping[str, Any]) -> bytes:
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False,
                      default=_plain).encode()


def _plain(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        return dict(obj)
    raise TypeError(f"{type(obj).__name__} is not JSON serialisable")


def _freeze(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        return MappingProxyType({k: _freeze(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return tuple(_freeze(v) for v in obj)
    return obj


def digest(doc: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical(doc)).hexdigest()


def _merge(base: Any, patch: Any) -> Any:
    """RFC 7386 JSON merge patch."""
    if not isinstance(patch, Mapping):
        return copy.deepcopy(patch)
    out = dict(base) if isinstance(base, Mapping) else {}
    for key, value in patch.items():
        if value is None:
            out.pop(key, None)
        else:
            out[key] = _merge(out.get(key), value)
    return out


def _check_int(where: str, value: Any, lo: float, hi: float, errors: list[str]) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{where} must be an integer")
    elif not lo <= value <= hi:
        errors.append(f"{where} must be in [{lo}, {hi}]")


def _check_quota(where: str, quota: Any, errors: list[str], *, partial: bool) -> None:
    if not isinstance(quota, Mapping):
        errors.append(f"{where} must be an object")
        return
    for key in quota:
        if key not in _QUOTA_RULES:
            errors.append(f"{where}.{key} is not a recognised quota key")
    for key, (_, lo, hi) in _QUOTA_RULES.items():
        if key in quota:
            _check_int(f"{where}.{key}", quota[key], lo, hi, errors)
        elif not partial:
            errors.append(f"{where}.{key} is required")


def validate(doc: Any) -> list[str]:
    """Return a sorted list of problems; empty means valid.  Never raises."""
    errors: list[str] = []
    if not isinstance(doc, Mapping):
        return ["configuration must be a JSON object"]
    for path, reason in find_secrets(doc):
        errors.append(f"{path}: inline secret material ({reason}); use a secretref:// reference")
    for key in doc:
        if key not in _TOP_KEYS:
            errors.append(f"{key}: unknown key (memory overcommit and unlisted policy are not configurable)")
    if doc.get("schema") != CONFIG_SCHEMA:
        errors.append(f"schema must be {CONFIG_SCHEMA!r}")
    version = doc.get("config_version")
    if not isinstance(version, str) or not 1 <= len(version) <= 64:
        errors.append("config_version must be a 1..64 character string")
    for key, lo, hi_open in (("headroom", 0.0, 1.0),):
        value = doc.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            errors.append(f"{key} must be a finite number")
        elif not lo <= value < hi_open:
            errors.append(f"{key} must be in [0, 1)")
    ratio = doc.get("cpu_overcommit")
    if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or not math.isfinite(ratio):
        errors.append("cpu_overcommit must be a finite number")
    elif not 1.0 <= ratio <= MAX_CPU_OVERCOMMIT:
        errors.append(f"cpu_overcommit must be in [1, {MAX_CPU_OVERCOMMIT}]")
    limits = doc.get("limits")
    if not isinstance(limits, Mapping):
        errors.append("limits must be an object")
    else:
        for key in limits:
            if key not in _LIMIT_RULES:
                errors.append(f"limits.{key}: unknown key")
        for key, (_, lo, hi) in _LIMIT_RULES.items():
            if key not in limits:
                errors.append(f"limits.{key} is required")
            else:
                _check_int(f"limits.{key}", limits[key], lo, hi, errors)
    tenants = doc.get("tenants")
    if not isinstance(tenants, Mapping):
        errors.append("tenants must be an object")
    else:
        for key in tenants:
            if key not in ("default_quota", "overrides"):
                errors.append(f"tenants.{key}: unknown key")
        _check_quota("tenants.default_quota", tenants.get("default_quota"), errors, partial=False)
        overrides = tenants.get("overrides", {})
        if not isinstance(overrides, Mapping):
            errors.append("tenants.overrides must be an object")
        else:
            for tenant, quota in overrides.items():
                if not isinstance(tenant, str) or not tenant or len(tenant) > 128:
                    errors.append("tenants.overrides keys must be 1..128 character tenant ids")
                _check_quota(f"tenants.overrides.{tenant}", quota, errors, partial=True)
    prov = doc.get("provenance")
    if not isinstance(prov, Mapping):
        errors.append("provenance must be an object")
    else:
        for key in prov:
            if key not in _PROV_KEYS:
                errors.append(f"provenance.{key}: unknown key")
        for key in ("author", "change_ref", "created"):
            if not isinstance(prov.get(key), str) or not prov.get(key):
                errors.append(f"provenance.{key} is required")
    if not errors:
        try:
            canonical(doc)
        except (TypeError, ValueError) as exc:
            errors.append(f"not canonical JSON: {exc}")
    return sorted(set(errors))


@dataclass(frozen=True)
class PackingConfig:
    """Immutable, validated configuration snapshot."""

    document: Mapping[str, Any]
    digest: str

    @classmethod
    def from_document(cls, doc: Mapping[str, Any]) -> "PackingConfig":
        problems = validate(doc)
        if problems:
            secret = any("inline secret" in p for p in problems)
            raise PackError("SECRET_IN_CONFIG" if secret else "CONFIG_INVALID",
                            "; ".join(problems[:5]), details={"problems": problems[:50]})
        frozen = json.loads(canonical(doc))
        return cls(_freeze(frozen), digest(frozen))

    @property
    def version(self) -> str:
        return self.document["config_version"]

    @property
    def headroom(self) -> float:
        return float(self.document["headroom"])

    @property
    def cpu_overcommit(self) -> float:
        return float(self.document["cpu_overcommit"])

    def limit(self, key: str) -> int:
        return int(self.document["limits"][key])

    def quota(self, tenant: str) -> dict[str, int]:
        tenants = self.document["tenants"]
        merged = dict(tenants["default_quota"])
        merged.update(tenants.get("overrides", {}).get(tenant, {}))
        return merged

    def identity(self) -> dict[str, str]:
        return {"config_version": self.version, "config_digest": self.digest}


def plain(doc: Mapping[str, Any]) -> dict:
    """Mutable deep copy of a (possibly frozen) configuration document."""
    return json.loads(canonical(doc))


def defaults() -> PackingConfig:
    return PackingConfig.from_document(plain(DEFAULTS))


def compose(base: Mapping[str, Any], *overlays: tuple[str, Mapping[str, Any]]) -> PackingConfig:
    """Apply named overlays (``("environment:prod", {...})``, ``("site:edge-7", {...})``)."""
    doc: Any = plain(base)
    layers = [f"base:{base.get('config_version', '?')}"]
    for name, patch in overlays:
        if not isinstance(patch, Mapping):
            raise PackError("CONFIG_INVALID", f"overlay {name!r} must be an object")
        if "schema" in patch or "provenance" in patch:
            raise PackError("CONFIG_INVALID", f"overlay {name!r} may not change schema or provenance")
        doc = _merge(doc, patch)
        layers.append(name)
    doc.setdefault("provenance", {})
    doc["provenance"] = dict(doc["provenance"], layers=layers)
    return PackingConfig.from_document(doc)


def diff(old: Mapping[str, Any] | None, new: Mapping[str, Any]) -> list[dict]:
    """Leaf-level differences ``[{path, old, new}]`` between two configuration documents (MC-10 F)."""
    out: list[dict] = []

    def walk(a: Any, b: Any, path: str) -> None:
        if isinstance(a, Mapping) and isinstance(b, Mapping):
            for k in sorted(set(a) | set(b)):
                walk(a.get(k, _MISSING), b.get(k, _MISSING), f"{path}.{k}" if path else str(k))
        elif a != b:
            out.append({"path": path, "old": None if a is _MISSING else _plain_value(a),
                        "new": None if b is _MISSING else _plain_value(b)})
    walk(old or {}, new, "")
    return out


_MISSING = object()


def _plain_value(v: Any) -> Any:
    return json.loads(json.dumps(v, default=_plain)) if isinstance(v, (Mapping, tuple, list)) else v


# --------------------------------------------------------------------- store
class ConfigStore:
    """Crash-safe, audited, epoch-fenced configuration store (file based)."""

    def __init__(self, root: str | os.PathLike, *, audit=None, clock: Callable[[], float] = time.time):
        self.root = Path(root)
        self.snapshots = self.root / "snapshots"
        self.snapshots.mkdir(parents=True, exist_ok=True)
        self.journal = self.root / "journal.jsonl"
        self.pointer = self.root / "ACTIVE"
        self._audit = audit
        self._clock = clock
        self._lock = threading.Lock()
        self.recovered_from: str | None = None

    # -- low level
    def _write_atomic(self, path: Path, data: bytes) -> None:
        tmp = path.with_name(path.name + f".tmp{os.getpid()}")
        with tmp.open("wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)

    def _load_snapshot(self, dig: str) -> PackingConfig | None:
        path = self.snapshots / f"{dig}.json"
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            cfg = PackingConfig.from_document(doc)
        except (OSError, ValueError, PackError):
            return None
        return cfg if cfg.digest == dig else None

    def _journal(self) -> list[dict]:
        if not self.journal.exists():
            return []
        out = []
        for line in self.journal.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue  # torn final line after a crash: ignored, never trusted
        return out

    def _pointer(self) -> dict | None:
        try:
            return json.loads(self.pointer.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    # -- public
    def active(self) -> PackingConfig | None:
        """Return the verified active configuration, recovering if needed."""
        ptr = self._pointer()
        if ptr:
            cfg = self._load_snapshot(ptr.get("digest", ""))
            if cfg is not None:
                return cfg
        for entry in reversed(self._journal()):
            cfg = self._load_snapshot(entry.get("digest", ""))
            if cfg is not None:
                self.recovered_from = entry.get("digest")
                return cfg
        return None

    def epoch(self) -> int:
        ptr = self._pointer() or {}
        return int(ptr.get("epoch", 0))

    def history(self) -> list[dict]:
        return self._journal()

    def _interprocess_lock(self, timeout_s: float = 2.0, stale_s: float = 30.0):
        """O_EXCL lock file so two *processes* cannot interleave an activation."""
        import contextlib

        lock = self.root / "LOCK"

        @contextlib.contextmanager
        def held():
            deadline = time.monotonic() + timeout_s
            while True:
                try:
                    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    os.write(fd, str(os.getpid()).encode())
                    os.close(fd)
                    break
                except FileExistsError:
                    try:
                        if time.time() - lock.stat().st_mtime > stale_s:
                            lock.unlink()  # holder crashed; lock is advisory and bounded
                            continue
                    except FileNotFoundError:
                        continue
                    if time.monotonic() > deadline:
                        raise PackError("CONFIG_CONFLICT", "another activation holds the store lock") from None
                    time.sleep(0.01)
            try:
                yield
            finally:
                try:
                    lock.unlink()
                except FileNotFoundError:
                    pass
        return held()

    def activate(self, cfg: PackingConfig, *, actor: str, epoch: int, expected_digest: str | None = None,
                 reason: str = "activate") -> dict:
        with self._lock, self._interprocess_lock():
            current_ptr = self._pointer() or {}
            current_epoch = int(current_ptr.get("epoch", 0))
            if epoch < current_epoch:
                raise PackError("STALE_EPOCH", f"epoch {epoch} < owner epoch {current_epoch}")
            current = current_ptr.get("digest")
            previous_cfg = self._load_snapshot(current) if current else None
            changes = diff(previous_cfg.document if previous_cfg else None, cfg.document)
            if expected_digest is not None and expected_digest != current:
                raise PackError("CONFIG_CONFLICT", "active configuration changed since it was read",
                                details={"expected": expected_digest, "actual": current})
            if self._audit is not None:
                from .audit import AuditUnavailable
                try:
                    self._audit.append("config." + reason, actor=actor, outcome="attempt",
                                       resource=cfg.digest, fail_closed=True,
                                       config_version=cfg.version, previous=current, epoch=epoch,
                                       changes=changes[:50], change_count=len(changes))
                except AuditUnavailable as exc:
                    raise PackError("AUDIT_UNAVAILABLE", "configuration change refused: audit sink unavailable") from exc
            self._write_atomic(self.snapshots / f"{cfg.digest}.json", canonical(cfg.document))
            entry = {"ts": round(float(self._clock()), 6), "digest": cfg.digest, "version": cfg.version,
                     "previous": current, "actor": actor, "epoch": epoch, "reason": reason,
                     "changed_paths": [c["path"] for c in changes][:50]}
            with self.journal.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            self._write_atomic(self.pointer, json.dumps({"digest": cfg.digest, "epoch": epoch}).encode())
            if self._audit is not None:
                self._audit.append("config." + reason, actor=actor, outcome="committed", resource=cfg.digest,
                                   config_version=cfg.version, previous=current, epoch=epoch)
            return entry

    def rollback(self, *, actor: str, epoch: int) -> dict:
        """Re-activate the configuration that preceded the current one."""
        ptr = self._pointer() or {}
        current = ptr.get("digest")
        for entry in reversed(self._journal()):
            if entry.get("digest") == current and entry.get("previous"):
                target = self._load_snapshot(entry["previous"])
                if target is None:
                    break
                return self.activate(target, actor=actor, epoch=epoch, expected_digest=current, reason="rollback")
        raise PackError("CONFIG_INVALID", "no intact previous configuration to roll back to")

    def export(self) -> dict:
        """Backup bundle (MC-37): every snapshot plus journal and pointer."""
        return {
            "schema": "PK_PACK_CONFIG_BACKUP/1",
            "pointer": self._pointer(),
            "journal": self._journal(),
            "snapshots": {p.stem: json.loads(p.read_text(encoding="utf-8"))
                          for p in sorted(self.snapshots.glob("*.json"))},
        }

    @classmethod
    def restore(cls, root: str | os.PathLike, bundle: Mapping[str, Any], **kw) -> "ConfigStore":
        """Rebuild a store from :meth:`export`; every snapshot digest is re-verified."""
        if bundle.get("schema") != "PK_PACK_CONFIG_BACKUP/1":
            raise PackError("CONFIG_INVALID", "not a PK_PACK_CONFIG_BACKUP/1 bundle")
        store = cls(root, **kw)
        for dig, doc in bundle["snapshots"].items():
            cfg = PackingConfig.from_document(doc)
            if cfg.digest != dig:
                raise PackError("CONFIG_INVALID", f"backup snapshot {dig[:12]} digest mismatch")
            store._write_atomic(store.snapshots / f"{dig}.json", canonical(cfg.document))
        store._write_atomic(store.journal, "".join(json.dumps(e, sort_keys=True) + "\n"
                                                   for e in bundle["journal"]).encode())
        if bundle.get("pointer"):
            store._write_atomic(store.pointer, json.dumps(bundle["pointer"]).encode())
        return store
