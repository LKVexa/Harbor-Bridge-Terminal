"""INV-25 typed device specifications and ownership registries (MC-003).

Only the five devices of ``MINIMAL_DEVICE_MODEL`` have spec classes; there is
no generic/pass-through spec, so the model cannot be widened by data.
"""
from __future__ import annotations

import os
import pathlib
import re
import stat
import threading
from dataclasses import dataclass
from typing import ClassVar, Final

from ..errors import Inv24Error
from ..runtime import MINIMAL_DEVICE_MODEL

ATTACH_ORDER: Final[tuple[str, ...]] = ("virtio-block", "virtio-net", "virtio-vsock", "serial", "rtc")
_ID = re.compile(r"[a-z][a-z0-9_-]{0,31}")
_TAP = re.compile(r"[a-zA-Z0-9_-]{1,15}")  # IFNAMSIZ-1
_MAC = re.compile(r"([0-9a-f]{2}:){5}[0-9a-f]{2}")
MAX_BLOCK_BYTES: Final[int] = 1 << 40
MAX_DRIVES: Final[int] = 4
MAX_NICS: Final[int] = 4
CID_MIN, CID_MAX = 3, (1 << 32) - 2  # 0-2 reserved by vsock


def _dev_id(v: object) -> str:
    if not isinstance(v, str) or not _ID.fullmatch(v):
        raise Inv24Error("CONFIG_REJECTED", f"device id {v!r} must match {_ID.pattern}")
    return v


@dataclass(frozen=True, slots=True)
class BlockSpec:
    kind: ClassVar[str] = "virtio-block"
    device_id: str
    path: str
    is_root: bool = False
    read_only: bool = True

    def validate(self, *, tenant_root: str | None = None) -> None:
        _dev_id(self.device_id)
        p = pathlib.Path(self.path)
        if not p.is_absolute() or ".." in p.parts:
            raise Inv24Error("CONFIG_REJECTED", f"{self.device_id}: block path must be absolute without '..'")
        if tenant_root is not None:
            root = pathlib.Path(tenant_root).resolve()
            if root not in p.resolve().parents and p.resolve() != root:
                raise Inv24Error("TENANT_MISMATCH", f"{self.device_id}: path outside tenant root")
        try:
            st = os.lstat(p)
        except OSError:
            raise Inv24Error("DEPENDENCY_UNAVAILABLE", f"{self.device_id}: backing file missing") from None
        if stat.S_ISLNK(st.st_mode):
            raise Inv24Error("CONFIG_REJECTED", f"{self.device_id}: symlinked backing file refused")
        if not stat.S_ISREG(st.st_mode):
            raise Inv24Error("CONFIG_REJECTED", f"{self.device_id}: backing file must be regular")
        if st.st_size == 0 or st.st_size > MAX_BLOCK_BYTES or st.st_size % 512:
            raise Inv24Error("CONFIG_REJECTED", f"{self.device_id}: size must be 512-aligned and <= 1 TiB")

    def api(self) -> dict[str, object]:
        return {"drive_id": self.device_id, "path_on_host": self.path,
                "is_root_device": self.is_root, "is_read_only": self.read_only}


@dataclass(frozen=True, slots=True)
class NetSpec:
    kind: ClassVar[str] = "virtio-net"
    device_id: str
    tap: str
    mac: str

    def validate(self, **_: object) -> None:
        _dev_id(self.device_id)
        if not _TAP.fullmatch(self.tap):
            raise Inv24Error("CONFIG_REJECTED", f"{self.device_id}: invalid TAP name")
        if not _MAC.fullmatch(self.mac) or int(self.mac[:2], 16) & 1:
            raise Inv24Error("CONFIG_REJECTED", f"{self.device_id}: MAC must be lowercase unicast")

    def api(self) -> dict[str, object]:
        return {"iface_id": self.device_id, "host_dev_name": self.tap, "guest_mac": self.mac}


@dataclass(frozen=True, slots=True)
class VsockSpec:
    kind: ClassVar[str] = "virtio-vsock"
    device_id: str
    guest_cid: int
    uds_path: str

    def validate(self, **_: object) -> None:
        _dev_id(self.device_id)
        if isinstance(self.guest_cid, bool) or not isinstance(self.guest_cid, int) or not CID_MIN <= self.guest_cid <= CID_MAX:
            raise Inv24Error("CONFIG_REJECTED", "guest CID out of range")
        if not os.path.isabs(self.uds_path) or len(self.uds_path.encode()) > 100:
            raise Inv24Error("CONFIG_REJECTED", "vsock UDS path must be absolute and <= 100 bytes")

    def api(self) -> dict[str, object]:
        return {"vsock_id": self.device_id, "guest_cid": self.guest_cid, "uds_path": self.uds_path}


@dataclass(frozen=True, slots=True)
class SerialSpec:
    """Serial console: implicit Firecracker capability, enabled via kernel ``console=ttyS0``."""
    kind: ClassVar[str] = "serial"
    device_id: str = "serial0"

    def validate(self, **_: object) -> None:
        _dev_id(self.device_id)

    def api(self) -> dict[str, object]:
        return {}


@dataclass(frozen=True, slots=True)
class RtcSpec:
    """RTC: implicit on aarch64 (PL031); on x86_64 guests use kvm-clock. No API call."""
    kind: ClassVar[str] = "rtc"
    device_id: str = "rtc0"

    def validate(self, **_: object) -> None:
        _dev_id(self.device_id)

    def api(self) -> dict[str, object]:
        return {}


SPEC_TYPES: Final[dict[str, type]] = {c.kind: c for c in (BlockSpec, NetSpec, VsockSpec, SerialSpec, RtcSpec)}
if set(SPEC_TYPES) != set(MINIMAL_DEVICE_MODEL):  # pragma: no cover - import-time invariant
    raise ImportError("device spec set diverges from MINIMAL_DEVICE_MODEL")


def order_and_check(specs, *, declared: frozenset[str], tenant_root: str | None = None) -> list:
    """Validate specs against the instance's declared devices; deterministic order."""
    ids = set()
    counts: dict[str, int] = {}
    for s in specs:
        if type(s) not in SPEC_TYPES.values():
            raise Inv24Error("DEVICE_OUTSIDE_MODEL", f"unsupported device spec {type(s).__name__}")
        if s.kind not in declared:
            raise Inv24Error("DEVICE_OUTSIDE_MODEL", f"{s.kind} not declared on this instance")
        if s.device_id in ids:
            raise Inv24Error("CONFIG_REJECTED", f"duplicate device id {s.device_id}")
        ids.add(s.device_id)
        counts[s.kind] = counts.get(s.kind, 0) + 1
        s.validate(tenant_root=tenant_root)
    if counts.get("virtio-block", 0) > MAX_DRIVES or counts.get("virtio-net", 0) > MAX_NICS:
        raise Inv24Error("RESOURCE_EXHAUSTED", "too many drives or NICs")
    if counts.get("virtio-vsock", 0) > 1 or counts.get("serial", 0) > 1 or counts.get("rtc", 0) > 1:
        raise Inv24Error("CONFIG_REJECTED", "at most one vsock/serial/rtc per instance")
    roots = [s for s in specs if isinstance(s, BlockSpec) and s.is_root]
    if len(roots) > 1:
        raise Inv24Error("CONFIG_REJECTED", "at most one root drive")
    return sorted(specs, key=lambda s: (ATTACH_ORDER.index(s.kind), s.device_id))


class OwnershipRegistry:
    """Host-wide exclusive ownership of TAPs, MACs, CIDs and block paths.

    A resource bound to one tenant cannot be bound by another until released,
    and release requires the owning (tenant, instance).  Teardown returns
    every resource so a later tenant never inherits an attachment.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._owner: dict[tuple[str, str], tuple[str, str]] = {}
        self._next_cid = CID_MIN

    def claim(self, kind: str, key: str, tenant: str, instance: str) -> None:
        with self._lock:
            cur = self._owner.get((kind, key))
            if cur is not None and cur != (tenant, instance):
                code = "TENANT_MISMATCH" if cur[0] != tenant else "CONFIG_REJECTED"
                raise Inv24Error(code, f"{kind} {key} already owned")
            self._owner[(kind, key)] = (tenant, instance)

    def allocate_cid(self, tenant: str, instance: str) -> int:
        with self._lock:
            for _ in range(1 << 16):
                cid = self._next_cid
                self._next_cid = CID_MIN if cid >= CID_MAX else cid + 1
                if ("cid", str(cid)) not in self._owner:
                    self._owner[("cid", str(cid))] = (tenant, instance)
                    return cid
        raise Inv24Error("RESOURCE_EXHAUSTED", "no free vsock CID")

    def claim_specs(self, specs, tenant: str, instance: str) -> None:
        claimed = []
        try:
            for s in specs:
                for kind, key in _keys(s):
                    self.claim(kind, key, tenant, instance)
                    claimed.append((kind, key))
        except Inv24Error:
            with self._lock:
                for k in claimed:
                    self._owner.pop(k, None)
            raise

    def release_instance(self, tenant: str, instance: str) -> int:
        with self._lock:
            keys = [k for k, v in self._owner.items() if v == (tenant, instance)]
            for k in keys:
                del self._owner[k]
            return len(keys)

    def owned_by(self, tenant: str) -> list[tuple[str, str]]:
        with self._lock:
            return sorted(k for k, v in self._owner.items() if v[0] == tenant)

    def reconcile(self, live: set[tuple[str, str]]) -> int:
        """Drop ownership for (tenant, instance) pairs no longer live."""
        with self._lock:
            dead = [k for k, v in self._owner.items() if v not in live]
            for k in dead:
                del self._owner[k]
            return len(dead)


def _keys(s) -> list[tuple[str, str]]:
    if isinstance(s, NetSpec):
        return [("tap", s.tap), ("mac", s.mac)]
    if isinstance(s, VsockSpec):
        return [("cid", str(s.guest_cid)), ("uds", s.uds_path)]
    if isinstance(s, BlockSpec):
        # writable drives are exclusive; read-only images may be shared (digest-pinned upstream)
        return [("block", str(pathlib.Path(s.path)))] if not s.read_only else []
    return []
