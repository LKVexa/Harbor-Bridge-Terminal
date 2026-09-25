"""PK_UNIKERNEL_SEAL_MANIFEST/1 strict parser (MC-006; C034, C022).

The manifest is a *claim*.  Admission compares it with binary-derived facts; it is never
evidence on its own.  Parsing is strict: exact field sets, bounded sizes, duplicate JSON keys
rejected, unknown schema versions rejected (``UK_UNSUPPORTED_VERSION``).
Normative JSON Schema: schemas/PK_UNIKERNEL_SEAL_MANIFEST-1.schema.json (kept in sync by a test).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .errors import UkError

SCHEMA = "PK_UNIKERNEL_SEAL_MANIFEST/1"
SUPPORTED = (SCHEMA,)
MAX_BYTES = 64 * 1024
_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,62}$")
_SYSCALL = re.compile(r"^(solo5\.)?[a-z0-9_]{1,40}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_CMDLINE = re.compile(r"^[A-Za-z0-9 =_.,:/+-]{0,512}$")
_MARKER = re.compile(r"^[ -~]{4,64}$")
NETWORK_MODES = ("none", "tap")
DEVICE_KINDS = ("serial", "virtio-net", "virtio-blk", "virtio-rng")


@dataclass(frozen=True)
class Boot:
    memory_mib: int
    vcpus: int
    cmdline: str
    ready_marker: str
    entry_symbol: str | None


@dataclass(frozen=True)
class IsolationRequest:
    network: str
    network_bridge: str | None
    devices: tuple
    storage: tuple          # tuple of (digest, read_only)


@dataclass(frozen=True)
class SealManifest:
    name: str
    digest: str
    toolchain: str
    architecture: str
    syscalls: frozenset
    boot: Boot
    isolation: IsolationRequest


def _bad(msg: str) -> UkError:
    return UkError("UK_MANIFEST_INVALID", msg)


def _exact(obj, keys: set, optional: set, where: str) -> dict:
    if not isinstance(obj, dict):
        raise _bad(f"{where} must be an object")
    extra, missing = set(obj) - keys - optional, keys - set(obj)
    if extra or missing:
        raise _bad(f"{where}: unknown {sorted(extra)} missing {sorted(missing)}")
    return obj


def _int(v, lo: int, hi: int, where: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
        raise _bad(f"{where} must be an integer in {lo}..{hi}")
    return v


def _str(v, rx: re.Pattern, where: str) -> str:
    if not isinstance(v, str) or not rx.match(v):
        raise _bad(f"{where} does not match {rx.pattern}")
    return v


def _no_dupes(pairs):
    seen = {}
    for k, v in pairs:
        if k in seen:
            raise _bad(f"duplicate key {k!r}")
        seen[k] = v
    return seen


def loads(text: str | bytes) -> SealManifest:
    if isinstance(text, bytes):
        if len(text) > MAX_BYTES:
            raise UkError("UK_LIMIT_EXCEEDED", "manifest too large")
        text = text.decode("utf-8")
    if not isinstance(text, str) or len(text) > MAX_BYTES:
        raise UkError("UK_LIMIT_EXCEEDED", "manifest too large or not text")
    try:
        obj = json.loads(text, object_pairs_hook=_no_dupes, parse_constant=lambda c: (_ for _ in ()).throw(_bad(c)))
    except UkError:
        raise
    except ValueError as e:
        raise _bad(f"not JSON: {e}") from None
    return parse(obj)


def parse(obj) -> SealManifest:
    if not isinstance(obj, dict):
        raise _bad("manifest must be an object")
    if obj.get("schema") not in SUPPORTED:
        raise UkError("UK_UNSUPPORTED_VERSION", f"manifest schema {obj.get('schema')!r} not in {SUPPORTED}")
    _exact(obj, {"schema", "image", "toolchain", "architecture", "syscalls", "boot", "isolation"}, set(), "manifest")
    img = _exact(obj["image"], {"name", "digest"}, set(), "image")
    sc = obj["syscalls"]
    if not isinstance(sc, list) or len(sc) > 512:
        raise _bad("syscalls must be a list of at most 512 names")
    names = [_str(x, _SYSCALL, "syscalls[]") for x in sc]
    if len(names) != len(set(names)):
        raise _bad("syscalls contains duplicates")
    b = _exact(obj["boot"], {"memory_mib", "vcpus", "cmdline", "ready_marker"}, {"entry_symbol"}, "boot")
    entry = b.get("entry_symbol")
    if entry is not None:
        _str(entry, re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$"), "boot.entry_symbol")
    iso = _exact(obj["isolation"], {"network", "devices", "storage"}, {"network_bridge"}, "isolation")
    net = iso["network"]
    if net not in NETWORK_MODES:
        raise _bad(f"isolation.network must be one of {NETWORK_MODES}")
    bridge = iso.get("network_bridge")
    if (net == "tap") != (bridge is not None):
        raise _bad("network_bridge is required for tap and forbidden otherwise")
    if bridge is not None:
        _str(bridge, _NAME, "isolation.network_bridge")
    devs = iso["devices"]
    if not isinstance(devs, list) or len(devs) > 8 or any(d not in DEVICE_KINDS for d in devs) or len(set(devs)) != len(devs):
        raise _bad(f"isolation.devices must be distinct members of {DEVICE_KINDS}")
    sto = iso["storage"]
    if not isinstance(sto, list) or len(sto) > 4:
        raise _bad("isolation.storage must be a list of at most 4 volumes")
    vols = []
    for v in sto:
        v = _exact(v, {"digest", "read_only"}, set(), "storage[]")
        if v["read_only"] is not True:
            raise _bad("storage volumes must be read_only: true (writable guest storage is not in scope)")
        vols.append((_str(v["digest"], _DIGEST, "storage[].digest"), True))
    return SealManifest(
        _str(img["name"], _NAME, "image.name"), _str(img["digest"], _DIGEST, "image.digest"),
        _str(obj["toolchain"], _NAME, "toolchain"), _str(obj["architecture"], re.compile(r"^(x86_64|aarch64)$"), "architecture"),
        frozenset(names),
        Boot(_int(b["memory_mib"], 8, 4096, "boot.memory_mib"), _int(b["vcpus"], 1, 8, "boot.vcpus"),
             _str(b["cmdline"], _CMDLINE, "boot.cmdline"), _str(b["ready_marker"], _MARKER, "boot.ready_marker"), entry),
        IsolationRequest(net, bridge, tuple(devs), tuple(vols)))


def to_dict(m: SealManifest) -> dict:
    iso = {"network": m.isolation.network, "devices": list(m.isolation.devices),
           "storage": [{"digest": d, "read_only": r} for d, r in m.isolation.storage]}
    if m.isolation.network_bridge is not None:
        iso["network_bridge"] = m.isolation.network_bridge
    boot = {"memory_mib": m.boot.memory_mib, "vcpus": m.boot.vcpus, "cmdline": m.boot.cmdline,
            "ready_marker": m.boot.ready_marker}
    if m.boot.entry_symbol:
        boot["entry_symbol"] = m.boot.entry_symbol
    return {"schema": SCHEMA, "image": {"name": m.name, "digest": m.digest}, "toolchain": m.toolchain,
            "architecture": m.architecture, "syscalls": sorted(m.syscalls), "boot": boot, "isolation": iso}
