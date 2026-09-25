"""Operational reference runtime for PLN-03.

This module intentionally has no dependency on ``pk_core`` so the data-plane
semantics can be unit-tested in a standalone component archive.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from threading import RLock
from typing import TypeAlias


MAX_INLINE_BYTES = 1024 * 1024
MAX_KEY_CHARS = 1024
MAX_NAME_CHARS = 256
MAX_TRANSACTION_OPS = 128


class RuntimePlaneError(RuntimeError):
    """Base class for reference-runtime failures with a stable error code."""

    code = "PK_RUNTIME_ERROR"

    def __init__(self, message: str, **details: object) -> None:
        super().__init__(message)
        self.details = dict(details)


class CapabilityDenied(PermissionError, RuntimePlaneError):
    """Raised when a workload calls a capability it is not bound to."""

    code = "PK_CAPABILITY_DENIED"

    def __init__(self, message: str, **details: object) -> None:
        PermissionError.__init__(self, message)
        self.details = dict(details)


class AdapterUnavailable(RuntimePlaneError):
    """Raised when the backing store for a bound capability cannot be reached."""

    code = "PK_ADAPTER_UNAVAILABLE"


class InvalidRuntimeInput(ValueError):
    """Raised when caller input violates the stable runtime contract."""

    code = "PK_INVALID_ARGUMENT"

    def __init__(self, message: str, **details: object) -> None:
        super().__init__(message)
        self.details = dict(details)


class PayloadTooLarge(InvalidRuntimeInput):
    """Raised when a payload exceeds the reference runtime's inline ceiling."""

    code = "PK_PAYLOAD_TOO_LARGE"


class SecretNotFound(KeyError):
    """Raised when a capability-scoped secret reference is absent."""

    code = "PK_SECRET_NOT_FOUND"


class InvocationTargetUnavailable(RuntimePlaneError):
    """Raised when no local invocation target is registered."""

    code = "PK_INVOKE_TARGET_UNAVAILABLE"


TransactionOperation: TypeAlias = tuple[str, str, bytes | None]


def _require_text(name: str, value: str, *, max_chars: int = MAX_NAME_CHARS) -> str:
    if not isinstance(value, str) or not value:
        raise InvalidRuntimeInput(f"{name} must be a non-empty string", field=name)
    if len(value) > max_chars:
        raise InvalidRuntimeInput(f"{name} exceeds {max_chars} characters", field=name, limit=max_chars)
    if "\x00" in value:
        raise InvalidRuntimeInput(f"{name} may not contain NUL", field=name)
    return value


def _require_payload(payload: bytes) -> bytes:
    if not isinstance(payload, bytes):
        raise InvalidRuntimeInput("payload/value must be bytes", field="payload")
    if len(payload) > MAX_INLINE_BYTES:
        raise PayloadTooLarge(
            f"inline payload exceeds {MAX_INLINE_BYTES} bytes",
            limit=MAX_INLINE_BYTES,
            size=len(payload),
        )
    return payload


class Adapter:
    """Thread-safe in-memory reference adapter used for executable verification."""

    def __init__(self, name: str, available: bool = True):
        self.name = _require_text("adapter name", name)
        self.available = bool(available)
        self._store: dict[str, bytes] = {}
        self._seen: set[str] = set()
        self._messages: list[tuple[str, str, bytes]] = []
        self._targets: dict[str, Callable[[bytes], bytes]] = {}
        self._lock = RLock()

    def _require_available(self) -> None:
        if not self.available:
            raise AdapterUnavailable(self.name, adapter=self.name)

    def get(self, key: str) -> bytes | None:
        with self._lock:
            self._require_available()
            return self._store.get(key)

    def set(self, key: str, value: bytes) -> None:
        value = _require_payload(value)
        with self._lock:
            self._require_available()
            self._store[key] = value

    def delete(self, key: str) -> bool:
        with self._lock:
            self._require_available()
            return self._store.pop(key, None) is not None

    def transact(self, operations: Sequence[TransactionOperation]) -> None:
        """Apply validated state mutations atomically to this adapter."""
        if len(operations) > MAX_TRANSACTION_OPS:
            raise InvalidRuntimeInput(
                f"transaction exceeds {MAX_TRANSACTION_OPS} operations",
                field="operations",
                limit=MAX_TRANSACTION_OPS,
            )
        validated: list[TransactionOperation] = []
        for operation in operations:
            if not isinstance(operation, tuple) or len(operation) != 3:
                raise InvalidRuntimeInput("each transaction operation must be a 3-tuple")
            verb, key, value = operation
            if verb not in {"set", "delete"}:
                raise InvalidRuntimeInput("transaction verb must be 'set' or 'delete'", verb=verb)
            if not isinstance(key, str) or not key:
                raise InvalidRuntimeInput("transaction key must be a non-empty string")
            if verb == "set":
                if value is None:
                    raise InvalidRuntimeInput("set transaction requires a bytes value")
                _require_payload(value)
            elif value is not None:
                raise InvalidRuntimeInput("delete transaction value must be None")
            validated.append((verb, key, value))

        with self._lock:
            self._require_available()
            replacement = dict(self._store)
            for verb, key, value in validated:
                if verb == "set":
                    replacement[key] = value  # type: ignore[assignment]
                else:
                    replacement.pop(key, None)
            self._store = replacement

    def accept(self, idempotency_key: str) -> bool:
        """Return True exactly once for a key while the adapter is available."""
        with self._lock:
            self._require_available()
            if idempotency_key in self._seen:
                return False
            self._seen.add(idempotency_key)
            return True

    def publish(self, storage_key: str, channel: str, idempotency_key: str, payload: bytes) -> bool:
        """Atomically deduplicate, persist, and enqueue a message."""
        payload = _require_payload(payload)
        with self._lock:
            self._require_available()
            if idempotency_key in self._seen:
                return False
            self._store[storage_key] = payload
            self._seen.add(idempotency_key)
            self._messages.append((channel, idempotency_key, payload))
            return True

    def messages(self, channel: str) -> tuple[bytes, ...]:
        with self._lock:
            self._require_available()
            return tuple(payload for item_channel, _, payload in self._messages if item_channel == channel)

    def register_target(self, target: str, handler: Callable[[bytes], bytes]) -> None:
        if not callable(handler):
            raise InvalidRuntimeInput("invocation handler must be callable")
        with self._lock:
            self._targets[target] = handler

    def invoke(self, target: str, payload: bytes) -> bytes:
        payload = _require_payload(payload)
        with self._lock:
            self._require_available()
            handler = self._targets.get(target)
        if handler is None:
            raise InvocationTargetUnavailable(target, target=target, adapter=self.name)
        result = handler(payload)
        if not isinstance(result, bytes):
            raise RuntimePlaneError("invocation target returned a non-bytes response", target=target)
        return _require_payload(result)


class DistributedRuntime:
    """Backend-independent API surface bound to a revision's capabilities."""

    def __init__(self, bindings: dict[str, Adapter]):
        if not isinstance(bindings, dict):
            raise InvalidRuntimeInput("bindings must be a dict")
        for binding, adapter in bindings.items():
            _require_text("binding", binding, max_chars=MAX_KEY_CHARS)
            parts = binding.split(":")
            if len(parts) != 2 or not all(parts):
                raise InvalidRuntimeInput(
                    "binding keys must use the exact '<workload>:<capability>' form", binding=binding
                )
            if parts[1] not in {"state", "messaging", "secrets", "invoke"}:
                raise InvalidRuntimeInput("binding names an unsupported capability", binding=binding)
            if not isinstance(adapter, Adapter):
                raise InvalidRuntimeInput("every binding value must be an Adapter", binding=binding)
        self._bindings = dict(bindings)

    def _adapter(self, workload: str, capability: str) -> Adapter:
        workload = _require_text("workload", workload)
        capability = _require_text("capability", capability)
        if ":" in workload:
            raise InvalidRuntimeInput("workload may not contain the binding separator", field="workload")
        adapter = self._bindings.get(f"{workload}:{capability}")
        if adapter is None:
            raise CapabilityDenied(
                f"{workload} is not bound to {capability!r}", workload=workload, capability=capability
            )
        return adapter

    @staticmethod
    def _key(tenant: str, key: str) -> str:
        tenant = _require_text("tenant", tenant)
        key = _require_text("key", key, max_chars=MAX_KEY_CHARS)
        if "/" in tenant:
            raise InvalidRuntimeInput("tenant may not contain a namespace separator", field="tenant")
        return f"{tenant}/{key}"

    @staticmethod
    def _channel(tenant: str, topic: str) -> str:
        tenant = _require_text("tenant", tenant)
        topic = _require_text("topic", topic)
        if "/" in tenant:
            raise InvalidRuntimeInput("tenant may not contain a namespace separator", field="tenant")
        return f"{len(tenant)}:{tenant}|{len(topic)}:{topic}"

    @staticmethod
    def _dedupe(tenant: str, topic: str, idempotency_key: str) -> str:
        channel = DistributedRuntime._channel(tenant, topic)
        idem = _require_text("idempotency_key", idempotency_key)
        return f"{channel}|{len(idem)}:{idem}"

    def state_set(self, workload: str, tenant: str, key: str, value: bytes) -> None:
        self._adapter(workload, "state").set(self._key(tenant, key), _require_payload(value))

    def state_get(self, workload: str, tenant: str, key: str) -> bytes | None:
        return self._adapter(workload, "state").get(self._key(tenant, key))

    def state_delete(self, workload: str, tenant: str, key: str) -> bool:
        return self._adapter(workload, "state").delete(self._key(tenant, key))

    def state_transact(
        self,
        workload: str,
        tenant: str,
        operations: Iterable[TransactionOperation],
    ) -> None:
        normalized: list[TransactionOperation] = []
        for operation in operations:
            if not isinstance(operation, tuple) or len(operation) != 3:
                raise InvalidRuntimeInput("each transaction operation must be a 3-tuple")
            verb, key, value = operation
            normalized.append((verb, self._key(tenant, key), value))
        self._adapter(workload, "state").transact(normalized)

    def publish(
        self,
        workload: str,
        tenant: str,
        topic: str,
        payload: bytes,
        idempotency_key: str,
    ) -> bool:
        adapter = self._adapter(workload, "messaging")
        payload = _require_payload(payload)
        channel = self._channel(tenant, topic)
        dedupe_key = self._dedupe(tenant, topic, idempotency_key)
        storage_key = self._key(tenant, f"messages/{len(topic)}:{topic}/{len(idempotency_key)}:{idempotency_key}")
        return adapter.publish(storage_key, channel, dedupe_key, payload)

    def subscribe(self, workload: str, tenant: str, topic: str) -> tuple[bytes, ...]:
        return self._adapter(workload, "messaging").messages(self._channel(tenant, topic))

    def secret_fetch(self, workload: str, tenant: str, reference: str) -> bytes:
        value = self._adapter(workload, "secrets").get(self._key(tenant, reference))
        if value is None:
            raise SecretNotFound(reference)
        return value

    def invoke(self, workload: str, tenant: str, component: str, payload: bytes) -> bytes:
        tenant = _require_text("tenant", tenant)
        if "/" in tenant:
            raise InvalidRuntimeInput("tenant may not contain a namespace separator", field="tenant")
        target = f"{tenant}:{_require_text('component', component)}"
        return self._adapter(workload, "invoke").invoke(target, payload)
