"""MC-001 - Versioned wire schemas for PK_TOPOLOGY/1, PK_LOCALITY_COST/1, PK_FAIR_SHARE/1.

IDL: ``GAP03-IDL/1`` - a deliberately small, explicit JSON-schema subset
(declared here as data, not prose).  Serialization: canonical JSON
(:mod:`.canonical`), media type ``application/vnd.pk.<iface>.v<major>+json``.

Compatibility policy (machine-checked by :func:`compatible`):
* minor bump = additive optional fields only; removal/type change = major bump;
* unknown fields are REJECTED on v1.x (strict) - peers must negotiate a minor
  that knows them; unknown enum values are rejected;
* removed field names go to ``reserved`` and may never be reused.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from . import canonical
from .errors import SchedulerError

IDL = "GAP03-IDL/1"
LABEL_RE = r"^[A-Za-z0-9][A-Za-z0-9._:\-]{0,62}$"


def _f(type_, *, required=True, unit=None, minimum=None, maximum=None, max_len=None, pattern=None,
       enum=None, items=None, max_items=None, default=None, since="1.0", deprecated=False):
    return {k: v for k, v in dict(type=type_, required=required, unit=unit, minimum=minimum, maximum=maximum,
                                   max_len=max_len, pattern=pattern, enum=enum, items=items, max_items=max_items,
                                   default=default, since=since, deprecated=deprecated).items() if v is not None}


LABEL = dict(max_len=63, pattern=LABEL_RE)
NODE_ENTRY = {"node": _f("string", **LABEL), "region": _f("string", **LABEL), "site": _f("string", **LABEL),
              "rack": _f("string", **LABEL)}

SCHEMAS: dict[str, dict] = {
    "PK_TOPOLOGY/1.0": {
        "id": "pk.topology", "major": 1, "minor": 0, "media_type": "application/vnd.pk.topology.v1+json",
        "reserved": [],
        "fields": {
            "schema": _f("string", enum=["PK_TOPOLOGY/1.0", "PK_TOPOLOGY/1.1"]),
            "environment": _f("string", **LABEL),
            "generation": _f("integer", unit="generation", minimum=0, maximum=canonical.MAX_INT),
            "nodes": _f("array", items={"type": "object", "fields": NODE_ENTRY}, max_items=100_000),
        },
    },
    "PK_TOPOLOGY/1.1": {
        "id": "pk.topology", "major": 1, "minor": 1, "media_type": "application/vnd.pk.topology.v1+json",
        "reserved": [],
        "fields": {
            "schema": _f("string", enum=["PK_TOPOLOGY/1.0", "PK_TOPOLOGY/1.1"]),
            "environment": _f("string", **LABEL),
            "generation": _f("integer", unit="generation", minimum=0, maximum=canonical.MAX_INT),
            "nodes": _f("array", items={"type": "object", "fields": NODE_ENTRY}, max_items=100_000),
            "provenance": _f("string", required=False, max_len=128, since="1.1", default=""),
        },
    },
    "PK_LOCALITY_COST/1.0": {
        "id": "pk.locality_cost", "major": 1, "minor": 0, "media_type": "application/vnd.pk.locality_cost.v1+json",
        "reserved": [],
        "fields": {
            "schema": _f("string", enum=["PK_LOCALITY_COST/1.0"]),
            "topology_generation": _f("integer", unit="generation", minimum=0, maximum=canonical.MAX_INT),
            "a": _f("string", **LABEL), "b": _f("string", **LABEL),
            "cost": _f("integer", unit="locality_class_units", minimum=0, maximum=101),
            "level": _f("string", enum=["same_node", "same_rack", "same_site", "same_region", "cross_region"]),
        },
    },
    "PK_FAIR_SHARE/1.0": {
        "id": "pk.fair_share", "major": 1, "minor": 0, "media_type": "application/vnd.pk.fair_share.v1+json",
        "reserved": [],
        "fields": {
            "schema": _f("string", enum=["PK_FAIR_SHARE/1.0"]),
            "ledger_revision": _f("integer", unit="revision", minimum=0, maximum=canonical.MAX_INT),
            "capacity": _f("integer", unit="slots", minimum=0, maximum=10_000_000),
            "tenant": _f("string", **LABEL),
            "requested_slots": _f("integer", unit="slots", minimum=1, maximum=10_000_000),
            "allowed": _f("boolean"),
            "reason": _f("string", enum=["within_reservation", "surplus_available", "reservations_oversubscribed",
                                         "capacity_exhausted", "protected_reservation"]),
            "reserved_slots": _f("integer", unit="slots", minimum=0, maximum=10_000_000),
            "held_slots": _f("integer", unit="slots", minimum=0, maximum=10_000_000),
            "state_token": _f("string", max_len=64, pattern=r"^[0-9a-f]{64}$"),
            "starved_tenants": _f("array", items={"type": "string", **LABEL}, max_items=10_000),
        },
    },
}

SUPPORTED = {"pk.topology": ("1.0", "1.1"), "pk.locality_cost": ("1.0",), "pk.fair_share": ("1.0",)}
DEPRECATION_SCHEDULE = {"PK_TOPOLOGY/1.0": {"deprecated": False, "sunset": None}}


def fingerprint(name: str) -> str:
    return canonical.digest(SCHEMAS[name])


def registry() -> dict:
    """Immutable schema registry: name -> content digest (the release location is this module)."""
    return {name: {"id": s["id"], "version": f'{s["major"]}.{s["minor"]}', "media_type": s["media_type"],
                   "sha256": fingerprint(name)} for name, s in sorted(SCHEMAS.items())}


def negotiate(schema_id: str, offered: list[str]) -> str:
    """Pick the highest mutually supported version; refuse unknown majors before side effects."""
    ours = SUPPORTED.get(schema_id)
    if not ours:
        raise SchedulerError("UNSUPPORTED_VERSION", f"unknown schema {schema_id}")
    common = [v for v in ours if v in set(offered)]
    if not common:
        raise SchedulerError("UNSUPPORTED_VERSION", f"no common version for {schema_id}")
    return max(common, key=lambda v: tuple(int(x) for x in v.split(".")))


def _validate_value(path: str, spec: dict, value):
    t = spec["type"]
    if t == "string":
        if not isinstance(value, str):
            raise SchedulerError("INVALID_ARGUMENT", f"{path}: expected string")
        if "max_len" in spec and len(value) > spec["max_len"]:
            raise SchedulerError("INVALID_ARGUMENT", f"{path}: too long")
        if "pattern" in spec and not re.fullmatch(spec["pattern"], value):
            raise SchedulerError("INVALID_ARGUMENT", f"{path}: does not match pattern")
        if "enum" in spec and value not in spec["enum"]:
            raise SchedulerError("INVALID_ARGUMENT", f"{path}: unknown enum value")
    elif t == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise SchedulerError("INVALID_ARGUMENT", f"{path}: expected integer")
        if value < spec.get("minimum", -canonical.MAX_INT) or value > spec.get("maximum", canonical.MAX_INT):
            raise SchedulerError("INVALID_ARGUMENT", f"{path}: out of bounds")
    elif t == "boolean":
        if not isinstance(value, bool):
            raise SchedulerError("INVALID_ARGUMENT", f"{path}: expected boolean")
    elif t == "array":
        if not isinstance(value, list):
            raise SchedulerError("INVALID_ARGUMENT", f"{path}: expected array")
        if len(value) > spec.get("max_items", canonical.MAX_ITEMS):
            raise SchedulerError("PAYLOAD_TOO_LARGE", f"{path}: too many items")
        for i, item in enumerate(value):
            _validate_value(f"{path}[{i}]", spec["items"], item)
    elif t == "object":
        _validate_fields(path, spec["fields"], value, reserved=())
    else:  # pragma: no cover - schema authoring error
        raise ValueError(t)


def _validate_fields(path, fields, obj, reserved):
    if not isinstance(obj, dict):
        raise SchedulerError("INVALID_ARGUMENT", f"{path}: expected object")
    unknown = set(obj) - set(fields)
    if unknown:
        raise SchedulerError("INVALID_ARGUMENT", f"{path}: unknown field(s) {sorted(unknown)[:3]}")
    for name in reserved:
        if name in obj:
            raise SchedulerError("INVALID_ARGUMENT", f"{path}: reserved field {name}")
    for name, spec in fields.items():
        if name not in obj:
            if spec.get("required", True):
                raise SchedulerError("INVALID_ARGUMENT", f"{path}.{name}: required")
            continue
        _validate_value(f"{path}.{name}", spec, obj[name])


def validate(name: str, obj: dict) -> dict:
    schema = SCHEMAS.get(name)
    if schema is None:
        raise SchedulerError("UNSUPPORTED_VERSION", f"unknown schema {name}")
    _validate_fields(name, schema["fields"], obj, schema["reserved"])
    if obj.get("schema") != name:
        raise SchedulerError("INVALID_ARGUMENT", "schema field does not match declared schema (schema confusion)")
    if name.startswith("PK_TOPOLOGY"):
        seen = set()
        for n in obj["nodes"]:
            if n["node"] in seen:
                raise SchedulerError("INVALID_ARGUMENT", "duplicate node id")
            seen.add(n["node"])
    return obj


def parse(name: str, data: bytes) -> dict:
    """Resource-bounded parse + schema validation.  Raises SchedulerError only."""
    try:
        obj = canonical.loads(data)
    except canonical.CanonicalError as exc:
        code = "PAYLOAD_TOO_LARGE" if "too large" in str(exc) or "too many" in str(exc) else "INVALID_ARGUMENT"
        raise SchedulerError(code, str(exc)) from None
    return validate(name, obj)


def encode(name: str, obj: dict) -> bytes:
    validate(name, obj)
    return canonical.dumps(obj)


def migrate(obj: dict, target: str) -> dict:
    """Explicit conversions between supported PK_TOPOLOGY minors (round-trip safe)."""
    src = obj.get("schema")
    if src == target:
        return dict(obj)
    if src == "PK_TOPOLOGY/1.0" and target == "PK_TOPOLOGY/1.1":
        out = dict(obj, schema=target)
        out.setdefault("provenance", "")
        return validate(target, out)
    if src == "PK_TOPOLOGY/1.1" and target == "PK_TOPOLOGY/1.0":
        if obj.get("provenance"):
            raise SchedulerError("UNSUPPORTED_VERSION", "downgrade would drop non-empty provenance")
        out = {k: v for k, v in obj.items() if k != "provenance"}
        out["schema"] = target
        return validate(target, out)
    raise SchedulerError("UNSUPPORTED_VERSION", f"no migration {src} -> {target}")


def compatible(old: str, new: str) -> list[str]:
    """Return compatibility violations between two schema versions (empty = compatible)."""
    a, b = SCHEMAS[old], SCHEMAS[new]
    problems = []
    if a["id"] != b["id"]:
        return ["different schema id"]
    if a["major"] != b["major"]:
        return []  # a major bump may break by definition
    for fname, spec in a["fields"].items():
        if fname not in b["fields"]:
            problems.append(f"removed field {fname} in a minor bump")
        elif b["fields"][fname]["type"] != spec["type"]:
            problems.append(f"type change on {fname}")
        elif set(spec.get("enum", [])) - set(b["fields"][fname].get("enum", spec.get("enum", []))):
            problems.append(f"enum value removed on {fname}")
    for fname, spec in b["fields"].items():
        if fname not in a["fields"] and spec.get("required", True):
            problems.append(f"new required field {fname} in a minor bump")
        if fname in a.get("reserved", []):
            problems.append(f"reserved name reused: {fname}")
    return problems


# ---- conversions from runtime objects -------------------------------------------------
def topology_to_wire(snapshot, environment: str, provenance: str = "") -> dict:
    nodes = [{"node": n, "region": p[0], "site": p[1], "rack": p[2]} for n, p in sorted(snapshot.nodes.items())]
    return validate("PK_TOPOLOGY/1.1", {"schema": "PK_TOPOLOGY/1.1", "environment": environment,
                                        "generation": snapshot.generation, "nodes": nodes, "provenance": provenance})


def cost_to_wire(snapshot, a: str, b: str) -> dict:
    cost = snapshot.cost(a, b)
    level = {0: "same_node", 1: "same_rack", 2: "same_site", 11: "same_region", 101: "cross_region"}[cost]
    return validate("PK_LOCALITY_COST/1.0", {"schema": "PK_LOCALITY_COST/1.0", "topology_generation": snapshot.generation,
                                             "a": a, "b": b, "cost": cost, "level": level})


def verdict_to_wire(verdict, ledger_revision: int, starved: list[str]) -> dict:
    return validate("PK_FAIR_SHARE/1.0", {
        "schema": "PK_FAIR_SHARE/1.0", "ledger_revision": ledger_revision, "capacity": verdict.capacity,
        "tenant": verdict.tenant, "requested_slots": verdict.requested_slots, "allowed": verdict.allowed,
        "reason": verdict.reason, "reserved_slots": verdict.reserved_slots, "held_slots": verdict.held_slots,
        "state_token": verdict.state_token, "starved_tenants": sorted(starved)})


def api_reference() -> dict:
    return {"idl": IDL, "registry": registry(), "supported": SUPPORTED, "deprecations": DEPRECATION_SCHEDULE,
            "schemas": SCHEMAS,
            "compatibility_matrix": {f"{o}->{n}": compatible(o, n) for o in SCHEMAS for n in SCHEMAS
                                     if SCHEMAS[o]["id"] == SCHEMAS[n]["id"] and o != n}}
