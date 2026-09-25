"""Hardened, dependency-free reference model for the INV-71 heavy sandbox.

This module is deliberately *not* a hypervisor.  It models security-sensitive
session semantics so they can be unit-tested without ``pk_core`` or a network:
clean snapshot creation, canonical path validation, bounded overlay storage,
canonical egress allowlisting, lifecycle closure, and a bounded tamper-evident
audit chain.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import ipaddress
import json
import re
import threading
from types import MappingProxyType
from typing import Iterable, Mapping

DEFAULT_DISK_QUOTA = 1 << 20
DEFAULT_FILE_QUOTA = 4096
DEFAULT_LOG_LIMIT = 256
DEFAULT_AUDIT_LIMIT = 1024
MAX_PATH_BYTES = 4096
MAX_SESSION_ID_BYTES = 128

_BASE = {
    "/usr/bin/python3": b"interpreter",
    "/etc/hosts": b"127.0.0.1 localhost",
}
BASE: Mapping[str, bytes] = MappingProxyType(_BASE)


class SandboxError(RuntimeError):
    """Base exception for reference sandbox operation failures."""


class SessionClosed(SandboxError):
    """Raised when an operation is attempted after teardown."""


class EgressDenied(PermissionError, SandboxError):
    """Raised when a destination is outside the explicit egress allowlist."""


class LimitExceeded(SandboxError):
    """Raised when an operation would exceed an enforced reference limit."""


class SessionState(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"


@dataclass(frozen=True)
class AuditEvent:
    sequence: int
    operation: str
    outcome: str
    detail: str
    previous_hash: str
    event_hash: str


def digest(fs: Mapping[str, bytes]) -> str:
    """Return an unambiguous SHA-256 digest for a filesystem mapping.

    Both path and payload are length-prefixed.  The previous implementation
    concatenated ``path + NUL + data`` records without a data delimiter, so two
    different mappings could produce identical serialized input before hashing.
    """
    h = hashlib.sha256()
    for path in sorted(fs):
        data = fs[path]
        if not isinstance(path, str) or not isinstance(data, bytes):
            raise TypeError("filesystem entries must map str paths to bytes")
        path_bytes = path.encode("utf-8", "strict")
        h.update(len(path_bytes).to_bytes(8, "big"))
        h.update(path_bytes)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


BASE_DIGEST = digest(BASE)


_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")


def validate_session_id(sid: str) -> str:
    if not isinstance(sid, str) or not sid:
        raise ValueError("sid must be a non-empty string")
    if len(sid.encode("utf-8", "strict")) > MAX_SESSION_ID_BYTES:
        raise ValueError(f"sid exceeds {MAX_SESSION_ID_BYTES} UTF-8 bytes")
    if not _SESSION_ID_RE.fullmatch(sid):
        raise ValueError("sid contains unsupported characters")
    return sid


def normalize_path(path: str) -> str:
    """Validate a canonical absolute POSIX guest path and return it unchanged."""
    if not isinstance(path, str) or not path:
        raise ValueError("path must be a non-empty string")
    if "\x00" in path:
        raise ValueError("path must not contain NUL")
    if len(path.encode("utf-8", "strict")) > MAX_PATH_BYTES:
        raise ValueError(f"path exceeds {MAX_PATH_BYTES} UTF-8 bytes")
    if not path.startswith("/") or path == "/":
        raise ValueError("path must be an absolute non-root POSIX path")
    if "\\" in path:
        raise ValueError("backslashes are not valid guest path separators")
    parts = path.split("/")[1:]
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("path must be canonical and contain no empty, dot, or dot-dot segments")
    return path


def canonicalize_host(host: str) -> str:
    """Return a canonical DNS name or IP literal, rejecting URLs and host:port input."""
    if not isinstance(host, str) or not host:
        raise ValueError("host must be a non-empty string")
    if host != host.strip() or any(ch.isspace() for ch in host):
        raise ValueError("host must not contain whitespace")
    if any(token in host for token in ("/", "\\", "@", "?", "#")) or "://" in host:
        raise ValueError("host must be a bare DNS name or IP literal, not a URL")

    candidate = host[:-1] if host.endswith(".") else host
    if not candidate:
        raise ValueError("host must not be empty")

    try:
        ip = ipaddress.ip_address(candidate)
    except ValueError:
        ip = None
    if ip is not None:
        # v4.3.0 fix (found by tools/fuzz.py): IPv6 zone IDs ("fe80::1%eth0:") were
        # accepted verbatim, letting arbitrary scope text - including ':' and
        # combining characters - into a "canonical" destination.  A zone ID names a
        # host interface, never a remote destination, so it is always rejected.
        if getattr(ip, "scope_id", None):
            raise ValueError("IPv6 zone IDs are not permitted in egress destinations")
        return ip.compressed.lower()

    if ":" in candidate:
        raise ValueError("ports are not permitted in host values")
    try:
        ascii_host = candidate.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValueError("host is not valid IDNA") from exc
    if len(ascii_host) > 253:
        raise ValueError("host exceeds DNS length limit")
    labels = ascii_host.split(".")
    if any(not label or len(label) > 63 for label in labels):
        raise ValueError("host contains an invalid DNS label length")
    for label in labels:
        if label.startswith("-") or label.endswith("-"):
            raise ValueError("DNS labels must not start or end with '-'")
        if not re.fullmatch(r"[a-z0-9-]+", label):
            raise ValueError("host contains unsupported DNS characters")
    return ascii_host


def _audit_hash(previous_hash: str, sequence: int, operation: str, outcome: str, detail: str) -> str:
    payload = json.dumps(
        {
            "sequence": sequence,
            "operation": operation,
            "outcome": outcome,
            "detail": detail,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    h = hashlib.sha256()
    h.update(bytes.fromhex(previous_hash))
    h.update(len(payload).to_bytes(8, "big"))
    h.update(payload)
    return h.hexdigest()


_ZERO_HASH = "0" * 64


@dataclass
class Session:
    sid: str
    egress_allow: frozenset[str]
    disk_quota: int = DEFAULT_DISK_QUOTA
    file_quota: int = DEFAULT_FILE_QUOTA
    log_limit: int = DEFAULT_LOG_LIMIT
    audit_limit: int = DEFAULT_AUDIT_LIMIT
    fs: dict[str, bytes] = field(default_factory=lambda: dict(BASE))
    connections: list[str] = field(default_factory=list)
    denied: list[str] = field(default_factory=list)
    state: SessionState = SessionState.ACTIVE
    audit: list[AuditEvent] = field(default_factory=list)
    _audit_anchor_hash: str = field(default=_ZERO_HASH, init=False, repr=False)
    _sequence: int = field(default=0, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.sid = validate_session_id(self.sid)
        self.egress_allow = frozenset(canonicalize_host(h) for h in self.egress_allow)
        for name, value in (
            ("disk_quota", self.disk_quota),
            ("file_quota", self.file_quota),
            ("log_limit", self.log_limit),
            ("audit_limit", self.audit_limit),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.fs != dict(BASE):
            raise ValueError("sessions must start from the exact clean base snapshot")
        self._emit("session.create", "allowed", f"base={BASE_DIGEST}")

    @property
    def alive(self) -> bool:
        return self.state is SessionState.ACTIVE

    @property
    def audit_head(self) -> str:
        return self.audit[-1].event_hash if self.audit else self._audit_anchor_hash

    def _ensure_active(self) -> None:
        if not self.alive:
            raise SessionClosed(f"{self.sid}: session is closed")

    def _emit(self, operation: str, outcome: str, detail: str) -> None:
        if len(self.audit) >= self.audit_limit:
            evicted = self.audit.pop(0)
            self._audit_anchor_hash = evicted.event_hash
        self._sequence += 1
        previous = self.audit[-1].event_hash if self.audit else self._audit_anchor_hash
        event_hash = _audit_hash(previous, self._sequence, operation, outcome, detail)
        self.audit.append(AuditEvent(self._sequence, operation, outcome, detail, previous, event_hash))

    def verify_audit_chain(self) -> bool:
        previous = self._audit_anchor_hash
        expected_sequence = self.audit[0].sequence if self.audit else self._sequence + 1
        for event in self.audit:
            if event.sequence != expected_sequence or event.previous_hash != previous:
                return False
            if event.event_hash != _audit_hash(previous, event.sequence, event.operation, event.outcome, event.detail):
                return False
            previous = event.event_hash
            expected_sequence += 1
        return True

    def _overlay_usage(self, fs: Mapping[str, bytes] | None = None) -> tuple[int, int]:
        view = self.fs if fs is None else fs
        changed = [(path, data) for path, data in view.items() if path not in BASE or BASE[path] != data]
        return sum(len(data) for _, data in changed), len(changed)

    def _append_bounded(self, target: list[str], value: str) -> None:
        if len(target) >= self.log_limit:
            del target[0]
        target.append(value)

    def write(self, path: str, data: bytes) -> None:
        with self._lock:
            self._ensure_active()
            path = normalize_path(path)
            if not isinstance(data, bytes):
                raise ValueError("data must be bytes")
            candidate = dict(self.fs)
            candidate[path] = data
            bytes_used, files_used = self._overlay_usage(candidate)
            if bytes_used > self.disk_quota:
                self._emit("fs.write", "denied", f"path={path};reason=disk_quota")
                raise LimitExceeded(f"{self.sid}: disk quota {self.disk_quota} bytes")
            if files_used > self.file_quota:
                self._emit("fs.write", "denied", f"path={path};reason=file_quota")
                raise LimitExceeded(f"{self.sid}: file quota {self.file_quota}")
            self.fs = candidate
            self._emit("fs.write", "allowed", f"path={path};bytes={len(data)}")

    def delete(self, path: str) -> None:
        with self._lock:
            self._ensure_active()
            path = normalize_path(path)
            existed = path in self.fs
            self.fs.pop(path, None)
            self._emit("fs.delete", "allowed", f"path={path};existed={str(existed).lower()}")

    def connect(self, host: str) -> None:
        with self._lock:
            self._ensure_active()
            canonical = canonicalize_host(host)
            if canonical not in self.egress_allow:
                self._append_bounded(self.denied, canonical)
                self._emit("egress.connect", "denied", f"host={canonical};reason=not_allowlisted")
                raise EgressDenied(f"{self.sid}: {canonical} not allowlisted")
            self._append_bounded(self.connections, canonical)
            self._emit("egress.connect", "allowed", f"host={canonical}")

    def teardown(self) -> dict[str, object]:
        with self._lock:
            if not self.alive:
                return {
                    "sid": self.sid,
                    "verified": True,
                    "state": self.state.value,
                    "base_digest": BASE_DIGEST,
                    "audit_head": self.audit_head,
                    "audit_chain_valid": self.verify_audit_chain(),
                }
            self.fs.clear()
            self.connections.clear()
            self.denied.clear()
            self.egress_allow = frozenset()
            self.state = SessionState.CLOSED
            verified = not self.fs and not self.connections and not self.denied and not self.egress_allow
            self._emit("session.teardown", "allowed" if verified else "failed", f"verified={str(verified).lower()}")
            return {
                "sid": self.sid,
                "verified": verified,
                "state": self.state.value,
                "base_digest": BASE_DIGEST,
                "audit_head": self.audit_head,
                "audit_chain_valid": self.verify_audit_chain(),
            }


def new_session(
    sid: str,
    allow: Iterable[str] = (),
    *,
    disk_quota: int = DEFAULT_DISK_QUOTA,
    file_quota: int = DEFAULT_FILE_QUOTA,
    log_limit: int = DEFAULT_LOG_LIMIT,
    audit_limit: int = DEFAULT_AUDIT_LIMIT,
) -> Session:
    """Create a validated session from the immutable clean base snapshot."""
    session = Session(
        sid=sid,
        egress_allow=frozenset(allow),
        disk_quota=disk_quota,
        file_quota=file_quota,
        log_limit=log_limit,
        audit_limit=audit_limit,
    )
    if digest(session.fs) != BASE_DIGEST:
        raise SandboxError("clean snapshot digest mismatch")
    return session
