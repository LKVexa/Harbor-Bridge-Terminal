"""MC30 - Resource limits.

One immutable, validated limits object is threaded through schemas, admission control,
the replica node and retention so every collection in the production layer has an
explicit bound.  Unsafe values are rejected at construction (fail closed at startup).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, fields

from .errors import ConfigError, LimitExceeded


@dataclass(frozen=True)
class Limits:
    max_key_bytes: int = 512
    max_value_bytes: int = 1 << 20
    max_vector_entries: int = 64
    max_counter: int = (1 << 63) - 1
    max_unresolved_per_key: int = 64
    max_siblings: int = 8
    max_batch_items: int = 1024
    max_batch_bytes: int = 8 << 20
    max_frame_bytes: int = 16 << 20
    max_audit_records: int = 1_000_000
    max_quarantine_total: int = 100_000
    max_keys_per_tenant: int = 1_000_000
    max_writes_per_tenant_window: int = 100_000

    def __post_init__(self) -> None:
        for f in fields(self):
            value = getattr(self, f.name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ConfigError(f"limit {f.name} must be a positive integer, got {value!r}")
        if self.max_siblings > self.max_unresolved_per_key:
            raise ConfigError("max_siblings may not exceed max_unresolved_per_key")
        if self.max_value_bytes + self.max_key_bytes > self.max_frame_bytes:
            raise ConfigError("a maximal write must fit in one frame")

    def as_dict(self) -> dict:
        return asdict(self)

    # -- checks ---------------------------------------------------------------
    def check_key(self, key: str) -> None:
        if len(key.encode("utf-8")) > self.max_key_bytes:
            raise LimitExceeded(f"key exceeds {self.max_key_bytes} bytes", code="CAP_KEY_SIZE")

    def check_value(self, value: str) -> None:
        if len(value.encode("utf-8")) > self.max_value_bytes:
            raise LimitExceeded(f"value exceeds {self.max_value_bytes} bytes", code="CAP_VALUE_SIZE")

    def check_vector(self, vector) -> None:
        entries = list(vector)
        if len(entries) > self.max_vector_entries:
            raise LimitExceeded(
                f"vector has {len(entries)} entries > {self.max_vector_entries}", code="CAP_VECTOR_SIZE"
            )
        for _site, counter in entries:
            if counter > self.max_counter:
                raise LimitExceeded("vector counter exceeds max_counter", code="CAP_COUNTER_RANGE")

    def check_batch(self, items: int, size: int) -> None:
        if items > self.max_batch_items:
            raise LimitExceeded(f"batch of {items} items > {self.max_batch_items}", code="CAP_BATCH_ITEMS")
        if size > self.max_batch_bytes:
            raise LimitExceeded(f"batch of {size} bytes > {self.max_batch_bytes}", code="CAP_BATCH_BYTES")


DEFAULT_LIMITS = Limits()
