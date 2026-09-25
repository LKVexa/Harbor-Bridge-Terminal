"""MC-04 - Version policy, negotiation, and compatibility matrix.

Schema identifiers take the form ``NAME/MAJOR``. Each public contract has a
supported-major window; a request may offer several majors and the plane picks
the highest mutually supported one. Deprecated majors are still accepted until
their removal date and are reported so callers can migrate.
"""
from __future__ import annotations

from dataclasses import dataclass
import datetime as _dt
import re
from typing import Iterable

from .errors import PlaneError

_SCHEMA_ID = re.compile(r"^([A-Z][A-Z0-9_]{0,63})/([1-9][0-9]{0,3})$")


@dataclass(frozen=True)
class MajorPolicy:
    major: int
    status: str  # "current" | "deprecated"
    removal_date: str | None = None  # ISO date after which the major is refused


POLICY: dict[str, tuple[MajorPolicy, ...]] = {
    "PK_APPLICATION": (MajorPolicy(1, "current"),),
    "PK_PROVIDER_CATALOGUE": (MajorPolicy(1, "current"),),
    "PK_APPLICATION_REVISION": (MajorPolicy(1, "current"),),
    "PK_ERROR": (MajorPolicy(1, "current"),),
    "PK_SIGNED_CATALOGUE": (MajorPolicy(1, "current"),),
    "PK_PLANE_CONFIG": (MajorPolicy(1, "current"),),
}

# Adjacent-layer compatibility matrix (MC-04 / MC-34). "verified" means an
# executable fixture in tests/test_integration_harness.py covers the pairing;
# "declared" means the contract names it but no live peer has been exercised.
COMPATIBILITY_MATRIX = [
    {"peer": "PLN-01 Intent plane", "contract": "PK_APPLICATION/1", "direction": "upstream", "evidence": "verified-mock"},
    {"peer": "INV-65 Capability providers", "contract": "PK_PROVIDER_CATALOGUE/1 + PK_SIGNED_CATALOGUE/1", "direction": "upstream", "evidence": "verified-mock"},
    {"peer": "PLN-03 Distributed runtime plane", "contract": "PK_APPLICATION_REVISION/1", "direction": "downstream", "evidence": "verified-mock"},
    {"peer": "SCH-01 Workload classification", "contract": "PK_APPLICATION_REVISION/1", "direction": "downstream", "evidence": "verified-mock"},
    {"peer": "INV-11 Interface contract language", "contract": "WIT subset (wit.py)", "direction": "peer", "evidence": "verified-mock"},
    {"peer": "GAP-04 Autonomy controller", "contract": "catalogue lease / snapshot", "direction": "peer", "evidence": "verified-mock"},
]


def parse_schema_id(value: object) -> tuple[str, int]:
    if not isinstance(value, str):
        raise PlaneError("schema identifier must be a string", code="UNSUPPORTED_VERSION", details={"schema": None})
    m = _SCHEMA_ID.fullmatch(value)
    if not m:
        raise PlaneError("malformed schema identifier", code="UNSUPPORTED_VERSION", details={"schema": value[:64]})
    return m.group(1), int(m.group(2))


def _supported(name: str, today: _dt.date) -> list[MajorPolicy]:
    out = []
    for p in POLICY.get(name, ()):
        if p.removal_date and today >= _dt.date.fromisoformat(p.removal_date):
            continue
        out.append(p)
    return out


def check(schema_id: object, *, today: _dt.date | None = None) -> dict:
    """Accept or refuse a single schema identifier; returns status info."""
    name, major = parse_schema_id(schema_id)
    today = today or _dt.date.today()
    for p in _supported(name, today):
        if p.major == major:
            return {"schema": f"{name}/{major}", "status": p.status, "removal_date": p.removal_date}
    raise PlaneError(f"{name}/{major} is not supported", code="UNSUPPORTED_VERSION",
                     details={"schema": f"{name}/{major}",
                              "supported": [f"{name}/{p.major}" for p in _supported(name, today)]})


def negotiate(name: str, offered: Iterable[int], *, today: _dt.date | None = None) -> int:
    today = today or _dt.date.today()
    offered_set = {o for o in offered if isinstance(o, int) and not isinstance(o, bool)}
    supported = {p.major for p in _supported(name, today)}
    common = offered_set & supported
    if not common:
        raise PlaneError(f"no mutually supported {name} major", code="UNSUPPORTED_VERSION",
                         details={"schema": name, "supported": [f"{name}/{m}" for m in sorted(supported)]})
    return max(common)
