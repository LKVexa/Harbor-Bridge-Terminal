"""GAP02-MC-27 — Compatibility negotiation.

Schema ids are ``NAME/MAJOR``. A consumer supporting majors S and a producer
offering majors P negotiate max(S ∩ P). Unknown fields: ignored-and-reported
for same-major minor additions; any unknown field under a *critical* list
(``critical`` key) is rejected. Migration functions upgrade older payloads.
"""
from __future__ import annotations

from typing import Callable

from .errors import Code, Gap02Error

MATRIX = {
    "PK_NODE_CAPABILITIES": {"produce": [1], "consume": [1]},
    "PK_SIGNED_CAPABILITIES": {"produce": [1], "consume": [1]},
    "PK_HARDWARE_INVENTORY": {"produce": [1], "consume": [1]},
    "PK_PROBE_SCHEDULE": {"produce": [1], "consume": [1]},
    "PK_ACCELERATOR_DEVICE": {"produce": [1], "consume": [1]},
    "GAP02_PROBE_CONFIG": {"produce": [1], "consume": [1]},
}
KNOWN_FIELDS = {"PK_NODE_CAPABILITIES/1": {"schema", "node", "present", "absent", "unprobed",
                                           "published_at", "age", "critical"}}
MIGRATIONS: dict[tuple[str, int], Callable[[dict], dict]] = {}


def parse(schema_id: str) -> tuple[str, int]:
    try:
        name, major = schema_id.rsplit("/", 1)
        return name, int(major)
    except (ValueError, AttributeError) as e:
        raise Gap02Error(Code.SCHEMA_INCOMPATIBLE, f"bad schema id {schema_id!r}") from e


def negotiate(name: str, peer_majors: list[int]) -> int:
    ours = set(MATRIX.get(name, {}).get("consume", []))
    common = ours & set(peer_majors)
    if not common:
        raise Gap02Error(Code.SCHEMA_INCOMPATIBLE, f"{name}: ours {sorted(ours)} peer {sorted(peer_majors)}")
    return max(common)


def accept(payload: dict) -> tuple[dict, list[str]]:
    name, major = parse(payload.get("schema", ""))
    while major not in MATRIX.get(name, {}).get("consume", []):
        mig = MIGRATIONS.get((name, major))
        if mig is None:
            raise Gap02Error(Code.SCHEMA_INCOMPATIBLE, f"{name}/{major} unsupported and no migration")
        payload = mig(payload)
        name, major = parse(payload["schema"])
    known = KNOWN_FIELDS.get(f"{name}/{major}")
    unknown = sorted(set(payload) - known) if known else []
    for f in payload.get("critical", []):
        if known is not None and f not in known:
            raise Gap02Error(Code.SCHEMA_INCOMPATIBLE, f"unknown critical field {f!r}")
    clean = {k: v for k, v in payload.items() if not known or k in known}
    return clean, unknown
