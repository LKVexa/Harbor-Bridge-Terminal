"""Secure configuration subsystem (16), capacity/quota model (58),
signed config verification (19) and secret boundary (17).

Configuration is a typed, range-checked, frozen object.  Every knob declares
type, range, default and whether it may be hot-reloaded.  Loading records
provenance (source path + sha256) and, when a key is configured, requires a
valid HMAC-SHA256 signature over the canonical JSON body.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import pathlib
import stat
from dataclasses import dataclass, field, fields, replace
from typing import Any

from .errors import SupervisorError

# name: (type, min, max, default, hot_reloadable, description)
SCHEMA: dict[str, tuple[type, float, float, Any, bool, str]] = {
    "max_workloads": (int, 1, 100_000, 512, False, "ceiling on resident workloads"),
    "max_health_signals": (int, 1, 1024, 64, False, "ceiling on registered health signals"),
    "max_queue_depth": (int, 1, 100_000, 256, True, "pending request queue ceiling"),
    "max_request_bytes": (int, 256, 1_048_576, 65_536, True, "largest accepted request body"),
    "rate_per_second": (float, 0.1, 100_000, 50.0, True, "token-bucket refill per caller"),
    "rate_burst": (int, 1, 100_000, 100, True, "token-bucket burst per caller"),
    "health_staleness_s": (int, 1, 3600, 30, True, "default per-signal staleness bound"),
    "request_skew_s": (int, 1, 3600, 30, True, "accepted request timestamp skew"),
    "replay_window": (int, 16, 1_000_000, 4096, False, "request-id/nonce dedup window size"),
    "drain_grace_s": (int, 0, 86_400, 30, True, "graceful stop grace per workload"),
    "drain_kill_after_s": (int, 0, 86_400, 60, True, "force-kill after deadline+this"),
    "partition_lease_s": (int, 1, 86_400, 90, True, "control-plane lease before partitioned"),
    "partition_max_autonomy_s": (int, 1, 604_800, 3600, True, "autonomy before emergency"),
    "watchdog_timeout_s": (int, 1, 3600, 15, True, "hung-loop threshold"),
    "audit_retention": (int, 100, 10_000_000, 100_000, False, "audit records retained"),
    "evidence_retention": (int, 10, 1_000_000, 10_000, False, "evidence records retained"),
    "memory_pressure_pct": (int, 50, 99, 90, True, "memory % that triggers pressure mode"),
    "disk_pressure_pct": (int, 50, 99, 92, True, "disk % that triggers pressure mode"),
    "cordon_ack_timeout_s": (int, 1, 3600, 10, True, "wait for placement-stop ack"),
}


@dataclass(frozen=True)
class SupervisorConfig:
    max_workloads: int = 512
    max_health_signals: int = 64
    max_queue_depth: int = 256
    max_request_bytes: int = 65_536
    rate_per_second: float = 50.0
    rate_burst: int = 100
    health_staleness_s: int = 30
    request_skew_s: int = 30
    replay_window: int = 4096
    drain_grace_s: int = 30
    drain_kill_after_s: int = 60
    partition_lease_s: int = 90
    partition_max_autonomy_s: int = 3600
    watchdog_timeout_s: int = 15
    audit_retention: int = 100_000
    evidence_retention: int = 10_000
    memory_pressure_pct: int = 90
    disk_pressure_pct: int = 92
    cordon_ack_timeout_s: int = 10
    provenance: dict = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        for f in fields(self):
            if f.name == "provenance":
                continue
            validate_knob(f.name, getattr(self, f.name))

    def to_dict(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self) if f.name != "provenance"}

    def hot_reload(self, changes: dict[str, Any]) -> SupervisorConfig:
        """Apply only hot-reloadable knobs; others require restart."""
        cold = sorted(k for k in changes if k in SCHEMA and not SCHEMA[k][4])
        unknown = sorted(k for k in changes if k not in SCHEMA)
        if unknown:
            raise SupervisorError("E_CONFIG", f"unknown knobs {unknown}")
        if cold:
            raise SupervisorError("E_CONFIG", f"knobs require restart: {cold}")
        return replace(self, **changes)


def validate_knob(name: str, value: Any) -> None:
    if name not in SCHEMA:
        raise SupervisorError("E_CONFIG", f"unknown knob {name!r}")
    typ, lo, hi, _default, _hot, _desc = SCHEMA[name]
    if isinstance(value, bool) or not isinstance(value, (int, float) if typ is float else typ):
        raise SupervisorError("E_CONFIG", f"{name} must be {typ.__name__}")
    if not (lo <= value <= hi):
        raise SupervisorError("E_CONFIG", f"{name}={value} outside [{lo}, {hi}]")


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sign(body: dict, key: bytes) -> str:
    return hmac.new(key, canonical(body), hashlib.sha256).hexdigest()


def verify_signature(body: dict, signature: str, key: bytes) -> bool:
    return hmac.compare_digest(sign(body, key), signature or "")


def load_config(path: str | os.PathLike, *, key: bytes | None = None,
                require_signature: bool = False) -> SupervisorConfig:
    """Load ``{"config": {...}, "signature": "hex"}`` with validation+provenance."""
    p = pathlib.Path(path)
    raw = p.read_bytes()
    if len(raw) > 1_048_576:
        raise SupervisorError("E_CONFIG", "config file too large")
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SupervisorError("E_CONFIG", f"invalid JSON: {exc.msg}") from None
    if not isinstance(doc, dict) or not isinstance(doc.get("config"), dict):
        raise SupervisorError("E_CONFIG", "config document must contain an object 'config'")
    body = doc["config"]
    if key is not None or require_signature:
        if key is None:
            raise SupervisorError("E_SIGNATURE", "signature required but no key provided")
        if not verify_signature(body, doc.get("signature", ""), key):
            raise SupervisorError("E_SIGNATURE", "config signature mismatch")
    unknown = sorted(set(body) - set(SCHEMA))
    if unknown:
        raise SupervisorError("E_CONFIG", f"unknown knobs {unknown}")
    prov = {"source": str(p), "sha256": hashlib.sha256(raw).hexdigest(),
            "signed": key is not None}
    return SupervisorConfig(**body, provenance=prov)


class SecretBoundary:
    """Secret/credential boundary (17).

    Secrets are read from a file with owner-only permissions or from an
    environment variable, held in a bytearray, never logged (``repr`` is
    redacted) and zeroed on ``close``.
    """

    def __init__(self, value: bytes, source: str) -> None:
        self._buf = bytearray(value)
        self.source = source

    @classmethod
    def from_file(cls, path: str | os.PathLike, *, enforce_mode: bool = True) -> SecretBoundary:
        p = pathlib.Path(path)
        st = p.stat()
        if enforce_mode and os.name == "posix" and st.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
            raise SupervisorError("E_CONFIG", f"secret file {p.name} must be mode 0600 or stricter")
        data = p.read_bytes().strip()
        if len(data) < 16:
            raise SupervisorError("E_CONFIG", "secret shorter than 16 bytes")
        return cls(data, f"file:{p.name}")

    @classmethod
    def from_env(cls, name: str) -> SecretBoundary:
        val = os.environ.get(name, "")
        if len(val) < 16:
            raise SupervisorError("E_CONFIG", f"secret env {name} missing or too short")
        return cls(val.encode(), f"env:{name}")

    def reveal(self) -> bytes:
        if not self._buf:
            raise SupervisorError("E_CONFIG", "secret already closed")
        return bytes(self._buf)

    def close(self) -> None:
        for i in range(len(self._buf)):
            self._buf[i] = 0
        self._buf = bytearray()

    def __repr__(self) -> str:  # never leak
        return f"SecretBoundary(source={self.source!r}, value=<redacted>)"

    __str__ = __repr__
