"""Canonical JSON, digests, resource limits and version negotiation (MC-06, MC-25, MC-26).

Canonical form: UTF-8, keys sorted, no insignificant whitespace, integers
only (floats/NaN rejected so bytes are identical across implementations),
duplicate keys rejected on parse.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable

from .errors import Inv22Error


@dataclass(frozen=True)
class Limits:
    max_bytes: int = 1_048_576
    max_depth: int = 32
    max_items: int = 10_000
    max_string: int = 65_536


DEFAULT_LIMITS = Limits()


def _check(value: Any, limits: Limits, depth: int = 0) -> int:
    if depth > limits.max_depth:
        raise Inv22Error("INV22.VALIDATION.LIMIT", "nesting too deep", {"max_depth": limits.max_depth})
    if isinstance(value, bool) or value is None:
        return 1
    if isinstance(value, float):
        raise Inv22Error("INV22.VALIDATION.SCHEMA", "floating point values are not canonical")
    if isinstance(value, int):
        if abs(value) > 2**63:
            raise Inv22Error("INV22.VALIDATION.LIMIT", "integer out of range")
        return 1
    if isinstance(value, str):
        if len(value) > limits.max_string:
            raise Inv22Error("INV22.VALIDATION.LIMIT", "string too long", {"max_string": limits.max_string})
        return 1
    if isinstance(value, (list, tuple)):
        n = 1 + sum(_check(v, limits, depth + 1) for v in value)
    elif isinstance(value, dict):
        for k in value:
            if not isinstance(k, str):
                raise Inv22Error("INV22.VALIDATION.SCHEMA", "object keys must be strings")
        n = 1 + sum(_check(v, limits, depth + 1) for v in value.values())
    else:
        raise Inv22Error("INV22.VALIDATION.SCHEMA", "unsupported value type", {"type": type(value).__name__})
    if n > limits.max_items:
        raise Inv22Error("INV22.VALIDATION.LIMIT", "too many items", {"max_items": limits.max_items})
    return n


def dumps(value: Any, limits: Limits = DEFAULT_LIMITS) -> bytes:
    _check(value, limits)
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")
    if len(data) > limits.max_bytes:
        raise Inv22Error("INV22.VALIDATION.LIMIT", "document too large", {"max_bytes": limits.max_bytes})
    return data


def _no_dupes(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise Inv22Error("INV22.VALIDATION.SCHEMA", "duplicate key", {"key": k})
        out[k] = v
    return out


def _no_float(_s):
    raise Inv22Error("INV22.VALIDATION.SCHEMA", "floating point values are not canonical")


def _no_const(_s):
    raise Inv22Error("INV22.VALIDATION.SCHEMA", "non-finite numbers are not permitted")


def loads(data: bytes | str, limits: Limits = DEFAULT_LIMITS) -> Any:
    raw = data.encode("utf-8") if isinstance(data, str) else bytes(data)
    if len(raw) > limits.max_bytes:
        raise Inv22Error("INV22.VALIDATION.LIMIT", "document too large", {"max_bytes": limits.max_bytes})
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_dupes,
                           parse_float=_no_float, parse_constant=_no_const)
    except Inv22Error:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        raise Inv22Error("INV22.VALIDATION.SCHEMA", "malformed JSON") from None
    _check(value, limits)
    return value


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(dumps(value)).hexdigest()


def file_digest(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


# --- contract version negotiation (MC-25) ------------------------------------

SUPPORTED_CONTRACTS = {
    "PK_BRANCH_MATRIX": (1,),
    "PK_BRANCH_SHIM": (1,),
    "PK_BRANCH_CERT": (1,),
    "PK_BRANCH_ERROR": (1,),
    "PK_BRANCH_CONFIG": (1,),
}


def parse_contract_id(contract_id: str) -> tuple[str, int]:
    if not isinstance(contract_id, str) or contract_id.count("/") != 1:
        raise Inv22Error("INV22.VERSION.UNSUPPORTED", "malformed contract identifier")
    name, _, ver = contract_id.partition("/")
    if not ver.isdigit() or ver.startswith("0"):
        raise Inv22Error("INV22.VERSION.UNSUPPORTED", "malformed contract version")
    return name, int(ver)


def require_supported(contract_id: str, expected_name: str) -> int:
    name, ver = parse_contract_id(contract_id)
    if name != expected_name or ver not in SUPPORTED_CONTRACTS.get(name, ()):
        raise Inv22Error("INV22.VERSION.UNSUPPORTED", "unsupported contract version",
                         {"contract": contract_id, "supported": ",".join(f"{expected_name}/{v}" for v in SUPPORTED_CONTRACTS.get(expected_name, ()))})
    return ver


def negotiate(name: str, peer_versions: Iterable[int]) -> str:
    """Pick the highest mutually supported version; never downgrade silently to an unlisted one."""
    ours = set(SUPPORTED_CONTRACTS.get(name, ()))
    peer = {v for v in peer_versions if isinstance(v, int) and not isinstance(v, bool)}
    common = ours & peer
    if not common:
        raise Inv22Error("INV22.VERSION.UNSUPPORTED", "no mutually supported contract version",
                         {"contract": name, "ours": ",".join(map(str, sorted(ours))), "peer": ",".join(map(str, sorted(peer)))})
    return f"{name}/{max(common)}"
