"""Runtime implementation for INV-42 capability descriptors.

The descriptor carried across a boundary is a bearer capability.  A table id and
integer alone are not authority: every descriptor is authenticated with a
per-table secret and the authentication tag binds the schema, table id, number,
and resource type.  The secret never leaves the table.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from typing import Callable
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

WIRE_SCHEMA = "PK_DESCRIPTOR/2"
CLOSE_SCHEMA = "PK_DESCRIPTOR_CLOSE/2"
STATUS_SCHEMA = "PK_DESCRIPTOR_TABLE_STATUS/1"
FIRST_DESCRIPTOR = 3
TABLE_LIMIT = 1024
SESSION_ALLOCATION_LIMIT = 1_048_576
MAX_RESOURCE_TYPE_BYTES = 128
MAX_OWNER_BYTES = 256
_AUTH_TAG_HEX_LEN = hashlib.sha256().digest_size * 2
_TABLE_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_AUTH_TAG_RE = re.compile(r"^[0-9a-f]{64}$")


class DescriptorError(Exception):
    """Base class for stable machine-readable descriptor failures."""

    code = "descriptor_error"

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": str(self)}


class InvalidDescriptor(DescriptorError, ValueError):
    """Raised for malformed, unauthenticated, or tampered descriptors."""

    code = "invalid_descriptor"


class ForeignDescriptor(DescriptorError, PermissionError):
    """Raised when a descriptor is presented to a table that did not issue it."""

    code = "foreign_descriptor"


class DescriptorClosed(DescriptorError, PermissionError):
    """Raised when an authentic descriptor is used after it was closed."""

    code = "descriptor_closed"


class TypeMismatch(DescriptorError, TypeError):
    """Raised when a descriptor is resolved as the wrong resource type."""

    code = "type_mismatch"


class TableFull(DescriptorError, RuntimeError):
    """Raised when the live-descriptor table limit is reached."""

    code = "table_full"


class SessionExhausted(DescriptorError, RuntimeError):
    """Raised when the non-reusing descriptor-number space is exhausted."""

    code = "session_exhausted"


class ForkedTable(DescriptorError, PermissionError):
    """Raised if a table is used in a process other than the one that created it."""

    code = "forked_table"


class TableDestroyed(DescriptorError, PermissionError):
    """Raised when authority is exercised after explicit table destruction."""

    code = "table_destroyed"


class ComponentDisabled(DescriptorError, PermissionError):
    """Raised while the process-wide emergency disable switch is engaged."""

    code = "component_disabled"


class KeyUnavailable(DescriptorError, RuntimeError):
    """Raised when an injected key provider fails or returns unusable key material."""

    code = "key_unavailable"


# --- emergency disable (MC-036) -------------------------------------------
# Process-wide kill switch.  When engaged, every authority-exercising operation
# (open, import, resolve, close) fails closed with ComponentDisabled.  destroy()
# and status() remain available so operators can revoke and observe.
_DISABLED = threading.Event()
DISABLE_ENV = "INV42_EMERGENCY_DISABLE"


def emergency_disable() -> None:
    """Engage the process-wide emergency disable switch (fail closed)."""
    _DISABLED.set()


def emergency_enable() -> None:
    """Release the emergency disable switch."""
    _DISABLED.clear()


def is_disabled() -> bool:
    return _DISABLED.is_set() or os.environ.get(DISABLE_ENV, "") == "1"


# Observer signature: observer(event: dict) -> None.  Events are built by the
# table and never contain the auth tag, table key, owner-supplied resource, or a
# complete wire payload.  Observer failures are swallowed so telemetry can never
# change a security decision (the decision is taken before the event is emitted).
Observer = Callable[[dict], None]
KeyProvider = Callable[[], bytes]


def _bounded_text(value: Any, *, field_name: str, max_bytes: int) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        raise ValueError(f"{field_name} must not contain control characters")
    if value != value.strip():
        raise ValueError(f"{field_name} must not have leading or trailing whitespace")
    if len(value.encode("utf-8")) > max_bytes:
        raise ValueError(f"{field_name} exceeds {max_bytes} UTF-8 bytes")
    return value


@dataclass(frozen=True, slots=True)
class Descriptor:
    """Authenticated serialized capability issued by exactly one table."""

    number: int
    resource_type: str
    table_id: str
    auth_tag: str = field(repr=False)

    def __post_init__(self) -> None:
        if isinstance(self.number, bool) or not isinstance(self.number, int):
            raise ValueError("descriptor number must be an integer")
        if self.number < FIRST_DESCRIPTOR:
            raise ValueError(f"descriptor number must be >= {FIRST_DESCRIPTOR}")
        _bounded_text(
            self.resource_type,
            field_name="resource_type",
            max_bytes=MAX_RESOURCE_TYPE_BYTES,
        )
        if not isinstance(self.table_id, str) or _TABLE_ID_RE.fullmatch(self.table_id) is None:
            raise ValueError("table_id must be 128-bit lowercase hexadecimal")
        if not isinstance(self.auth_tag, str) or _AUTH_TAG_RE.fullmatch(self.auth_tag) is None:
            raise ValueError("auth_tag must be a SHA-256 hexadecimal tag")

    def to_wire(self) -> dict[str, object]:
        """Return the canonical v2 wire representation."""
        return {
            "schema": WIRE_SCHEMA,
            "number": self.number,
            "type": self.resource_type,
            "table": self.table_id,
            "auth": self.auth_tag,
        }


class DescriptorTable:
    """One workload's descriptor table with authenticated, non-reusing handles.

    The table is deliberately not serializable: its HMAC key is process-local
    authority.  A process fork is detected so a cloned table cannot allocate a
    divergent descriptor stream under the same table identity.
    """

    __slots__ = (
        "owner",
        "table_id",
        "_pid",
        "_key",
        "_next",
        "_entries",
        "_issued",
        "_closed_count",
        "_lock",
        "_counters",
        "_destroyed",
        "_observer",
        "_fingerprint",
    )

    def __init__(
        self,
        owner: str,
        *,
        observer: Observer | None = None,
        key_provider: KeyProvider | None = None,
    ) -> None:
        self.owner = _bounded_text(owner, field_name="owner", max_bytes=MAX_OWNER_BYTES)
        # Table identity is issuer-owned; callers cannot select or reuse it.
        self.table_id = secrets.token_hex(16)
        self._pid = os.getpid()
        if key_provider is None:
            key = secrets.token_bytes(32)
        else:
            # MC-016/MC-018: an external key source is trusted only if it answers
            # with >= 256 bits.  Any failure is fail-closed: no table is created.
            try:
                key = key_provider()
            except Exception as exc:  # noqa: BLE001 - provider is foreign code
                raise KeyUnavailable(f"{self.owner}: key provider failed: {type(exc).__name__}") from None
            if not isinstance(key, (bytes, bytearray)) or len(key) < 32:
                raise KeyUnavailable(f"{self.owner}: key provider returned unusable key material")
        self._key = bytearray(key)
        self._observer = observer
        # Non-secret, non-reversible label for correlating events of one table.
        self._fingerprint = hashlib.sha256(b"inv42-table-fp\x00" + self.table_id.encode()).hexdigest()[:16]
        self._next = FIRST_DESCRIPTOR
        self._entries: dict[int, tuple[str, Any]] = {}
        self._issued = 0
        self._closed_count = 0
        self._lock = threading.RLock()
        self._destroyed = False
        self._counters = {
            "foreign_resolutions": 0,
            "closed_reuse_attempts": 0,
            "type_mismatches": 0,
            "invalid_descriptors": 0,
            "capacity_rejections": 0,
            "fork_rejections": 0,
        }

    def __getstate__(self):  # pragma: no cover - defensive serialization guard
        raise TypeError("DescriptorTable contains process-local authority and cannot be serialized")

    @property
    def entries(self):
        """Read-only snapshot of live entries for diagnostics only."""
        with self._lock:
            self._ensure_active_locked()
            return MappingProxyType(dict(self._entries))

    def _ensure_process_locked(self) -> None:
        if os.getpid() != self._pid:
            self._counters["fork_rejections"] += 1
            raise ForkedTable(
                f"{self.owner}: descriptor table belongs to process {self._pid}, "
                f"not process {os.getpid()}"
            )

    def _ensure_active_locked(self) -> None:
        self._ensure_process_locked()
        if self._destroyed:
            raise TableDestroyed(f"{self.owner}: descriptor table has been destroyed")
        if is_disabled():
            raise ComponentDisabled(f"{self.owner}: INV-42 is emergency-disabled")

    @property
    def fingerprint(self) -> str:
        """Non-secret 64-bit table label safe for logs, metrics and traces."""
        return self._fingerprint

    def _emit(self, op: str, started: float, *, error: BaseException | None = None,
              number: int | None = None, resource_type: str | None = None) -> None:
        observer = self._observer
        if observer is None:
            return
        event = {
            "schema": "PK_DESCRIPTOR_EVENT/1",
            "op": op,
            "table_fp": self._fingerprint,
            "outcome": "ok" if error is None else getattr(error, "code", "internal_error"),
            "number": number,
            "type": resource_type,
            "duration_ns": time.perf_counter_ns() - started,
            "ts": time.time(),
        }
        try:
            observer(event)
        except Exception:  # noqa: BLE001 - telemetry must never alter decisions
            pass

    def _mac_message(self, number: int, resource_type: str) -> bytes:
        # Canonical JSON avoids delimiter ambiguity and makes the authenticated
        # fields explicit for future schema migrations.
        return json.dumps(
            [WIRE_SCHEMA, self.table_id, number, resource_type],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

    def _mint_tag(self, number: int, resource_type: str) -> str:
        return hmac.new(
            bytes(self._key),
            self._mac_message(number, resource_type),
            hashlib.sha256,
        ).hexdigest()

    def _authenticate_locked(self, descriptor: Descriptor) -> None:
        if not isinstance(descriptor, Descriptor):
            self._counters["invalid_descriptors"] += 1
            raise InvalidDescriptor("descriptor object has the wrong type")
        if not hmac.compare_digest(descriptor.table_id, self.table_id):
            self._counters["foreign_resolutions"] += 1
            raise ForeignDescriptor(
                f"{self.owner}: descriptor {descriptor.number} belongs to another table"
            )
        expected = self._mint_tag(descriptor.number, descriptor.resource_type)
        if not hmac.compare_digest(descriptor.auth_tag, expected):
            self._counters["invalid_descriptors"] += 1
            raise InvalidDescriptor(
                f"{self.owner}: descriptor {descriptor.number} failed authentication"
            )

    def open(self, resource_type: str, resource: Any) -> Descriptor:
        started = time.perf_counter_ns()
        try:
            fd = self._open(resource_type, resource)
        except DescriptorError as exc:
            self._emit("open", started, error=exc)
            raise
        except ValueError as exc:
            self._emit("open", started, error=exc)
            raise
        self._emit("open", started, number=fd.number, resource_type=fd.resource_type)
        return fd

    def _open(self, resource_type: str, resource: Any) -> Descriptor:
        resource_type = _bounded_text(
            resource_type,
            field_name="resource_type",
            max_bytes=MAX_RESOURCE_TYPE_BYTES,
        )
        with self._lock:
            self._ensure_active_locked()
            if len(self._entries) >= TABLE_LIMIT:
                self._counters["capacity_rejections"] += 1
                raise TableFull(f"{self.owner}: descriptor table is full ({TABLE_LIMIT})")
            if self._issued >= SESSION_ALLOCATION_LIMIT:
                self._counters["capacity_rejections"] += 1
                raise SessionExhausted(
                    f"{self.owner}: session allocation limit reached "
                    f"({SESSION_ALLOCATION_LIMIT})"
                )
            number = self._next
            # MC-019: build the complete descriptor before committing any state so
            # a failure while minting cannot leave a live entry without a handle.
            descriptor = Descriptor(
                number=number,
                resource_type=resource_type,
                table_id=self.table_id,
                auth_tag=self._mint_tag(number, resource_type),
            )
            self._next += 1
            self._issued += 1
            self._entries[number] = (resource_type, resource)
            return descriptor

    def _resolve_locked(self, descriptor: Descriptor, *, expect: str | None = None):
        self._ensure_active_locked()
        self._authenticate_locked(descriptor)
        entry = self._entries.get(descriptor.number)
        if entry is None:
            # A valid authentication tag can only have been minted by this table,
            # so an absent entry is a previously issued and permanently closed one.
            self._counters["closed_reuse_attempts"] += 1
            raise DescriptorClosed(
                f"{self.owner}: descriptor {descriptor.number} was closed"
            )
        resource_type, resource = entry
        if descriptor.resource_type != resource_type:
            # This should be unreachable without key compromise because the type
            # is authenticated, but retain a fail-closed check against state damage.
            self._counters["type_mismatches"] += 1
            raise TypeMismatch(
                f"descriptor {descriptor.number} carries {descriptor.resource_type!r}, "
                f"table holds {resource_type!r}"
            )
        if expect is not None:
            expect = _bounded_text(
                expect,
                field_name="expect",
                max_bytes=MAX_RESOURCE_TYPE_BYTES,
            )
            if resource_type != expect:
                self._counters["type_mismatches"] += 1
                raise TypeMismatch(
                    f"descriptor {descriptor.number} is {resource_type!r}, "
                    f"resolved as {expect!r}"
                )
        return resource

    def _safe_ident(self, descriptor):
        if isinstance(descriptor, Descriptor):
            return descriptor.number, descriptor.resource_type
        return None, None

    def resolve(self, descriptor: Descriptor, *, expect: str | None = None):
        started = time.perf_counter_ns()
        number, rtype = self._safe_ident(descriptor)
        try:
            with self._lock:
                resource = self._resolve_locked(descriptor, expect=expect)
        except (DescriptorError, ValueError) as exc:
            self._emit("resolve", started, error=exc, number=number, resource_type=rtype)
            raise
        self._emit("resolve", started, number=number, resource_type=rtype)
        return resource

    def close(self, descriptor: Descriptor) -> dict[str, object]:
        started = time.perf_counter_ns()
        number, rtype = self._safe_ident(descriptor)
        try:
            receipt = self._close(descriptor)
        except (DescriptorError, ValueError) as exc:
            self._emit("close", started, error=exc, number=number, resource_type=rtype)
            raise
        self._emit("close", started, number=number, resource_type=rtype)
        return receipt

    def _close(self, descriptor: Descriptor) -> dict[str, object]:
        with self._lock:
            self._resolve_locked(descriptor)
            self._entries.pop(descriptor.number)
            self._closed_count += 1
            return {
                "schema": CLOSE_SCHEMA,
                "table": self.table_id,
                "number": descriptor.number,
                "closed": True,
                "number_reusable": False,
            }

    def from_wire(self, payload: Mapping[str, object]) -> Descriptor:
        started = time.perf_counter_ns()
        try:
            fd = self._from_wire(payload)
        except (DescriptorError, ValueError) as exc:
            self._emit("import", started, error=exc)
            raise
        self._emit("import", started, number=fd.number, resource_type=fd.resource_type)
        return fd

    def _from_wire(self, payload: Mapping[str, object]) -> Descriptor:
        """Strictly parse and authenticate a live v2 descriptor.

        Unknown fields are rejected to prevent extension/smuggling ambiguity.
        Version 1 is intentionally not accepted because it had no authenticity
        tag and allowed descriptor forgery within a known table.
        """
        if type(payload) is not dict:  # noqa: E721 - reject hostile dict subclasses
            with self._lock:
                self._counters["invalid_descriptors"] += 1
            raise InvalidDescriptor("descriptor payload must be a plain dict")
        required = {"schema", "number", "type", "table", "auth"}
        keys = set(payload.keys())
        if keys != required:
            with self._lock:
                self._counters["invalid_descriptors"] += 1
            missing = sorted(required - keys)
            extra = sorted(keys - required)
            raise InvalidDescriptor(
                f"descriptor payload fields invalid; missing={missing}, extra={extra}"
            )
        exact = {"schema": str, "number": int, "type": str, "table": str, "auth": str}
        for name, kind in exact.items():
            if type(payload[name]) is not kind:  # noqa: E721 - no hostile subclasses
                with self._lock:
                    self._counters["invalid_descriptors"] += 1
                raise InvalidDescriptor(f"descriptor field {name!r} must be exactly {kind.__name__}")
        if payload["schema"] != WIRE_SCHEMA:
            with self._lock:
                self._counters["invalid_descriptors"] += 1
            raise InvalidDescriptor(
                f"unsupported descriptor schema {payload['schema'][:32]!r}; "
                f"expected {WIRE_SCHEMA!r}"
            )
        try:
            descriptor = Descriptor(
                number=payload["number"],  # type: ignore[arg-type]
                resource_type=payload["type"],  # type: ignore[arg-type]
                table_id=payload["table"],  # type: ignore[arg-type]
                auth_tag=payload["auth"],  # type: ignore[arg-type]
            )
        except (TypeError, ValueError) as exc:
            with self._lock:
                self._counters["invalid_descriptors"] += 1
            raise InvalidDescriptor(str(exc)) from exc
        with self._lock:
            self._resolve_locked(descriptor)
        return descriptor

    def destroy(self) -> None:
        """Permanently revoke the table and best-effort zeroize its in-memory key."""
        with self._lock:
            self._ensure_process_locked()
            if self._destroyed:
                return
            self._entries.clear()
            for index in range(len(self._key)):
                self._key[index] = 0
            self._destroyed = True
        self._emit("destroy", time.perf_counter_ns())

    def __enter__(self):
        with self._lock:
            self._ensure_active_locked()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.destroy()
        return False

    def status(self) -> dict[str, int | str | bool]:
        """Return bounded, non-secret operational state and security counters."""
        with self._lock:
            self._ensure_process_locked()
            return {
                "schema": STATUS_SCHEMA,
                "version": WIRE_SCHEMA,
                "live": len(self._entries),
                "issued": self._issued,
                "closed": self._closed_count,
                "destroyed": self._destroyed,
                "table_limit": TABLE_LIMIT,
                "session_allocation_limit": SESSION_ALLOCATION_LIMIT,
                **self._counters,
            }
