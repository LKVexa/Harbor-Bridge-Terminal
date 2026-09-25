# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Interface resource limits (GAP-021). Every value is enforced in code, not only documented."""
from __future__ import annotations

from dataclasses import dataclass, asdict

#: Addresses are modelled as unsigned 64-bit, matching CHERI-64 address width.
ADDRESS_BITS = 64
MAX_ADDRESS = (1 << ADDRESS_BITS) - 1


@dataclass(frozen=True)
class Limits:
    max_capabilities_per_tenant: int = 65_536
    max_capabilities_total: int = 1_048_576
    max_derivation_depth: int = 64
    max_access_size: int = 1 << 30
    max_request_bytes: int = 16_384
    max_inflight: int = 256
    max_queue_depth: int = 1_024
    max_tenants: int = 4_096
    max_batch: int = 128
    idempotency_cache_entries: int = 65_536
    nonce_cache_entries: int = 262_144

    def validate(self) -> list[str]:
        return [f"{k} must be a positive integer" for k, v in asdict(self).items()
                if type(v) is not int or v <= 0]

    def to_dict(self) -> dict:
        return {"address_bits": ADDRESS_BITS, **asdict(self)}


DEFAULT_LIMITS = Limits()
