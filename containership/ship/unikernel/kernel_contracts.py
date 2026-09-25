"""Stable local kernel descriptors and ABI validation for UC-2.7.0."""
from __future__ import annotations
from typing import Any
from . import Refusal

ABI = "UC/PIXEL_KERNEL_ABI/1"
OPS = ("set", "add", "xor")
MAX_TILE_BYTES = 464
MAX_U64 = (1 << 64) - 1


def descriptor() -> dict[str, Any]:
    return {
        "schema": "UC/KERNEL_CAPABILITIES/1",
        "abi": ABI,
        "integer_width_bits": 64,
        "endianness": "explicit-by-TIFF",
        "operations": list(OPS),
        "tile_payload_max_bytes": MAX_TILE_BYTES,
        "transactional_multi_tile": False,
        "simd_qualified": False,
        "gpu_qualified": False,
        "deterministic_integer_semantics": True,
    }


def validate_request(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"abi", "op", "x", "y", "value"}:
        raise Refusal("pixel kernel request fields invalid")
    if value["abi"] != ABI or value["op"] not in OPS:
        raise Refusal("pixel kernel ABI or operation unsupported")
    for k in ("x", "y", "value"):
        v = value[k]
        if isinstance(v, bool) or not isinstance(v, int) or v < 0 or v > MAX_U64:
            raise Refusal("pixel kernel integer field out of bounds", {"field": k})
    return dict(value)
