"""Explicit lifecycle state machines (MC-24, MC-62).

Each machine is a closed transition table; the store calls ``check`` inside
its transaction so illegal jumps are rejected at the authoritative boundary.
"""
from __future__ import annotations

from types import MappingProxyType

from .errors import Inv22Error


def _m(d):
    return MappingProxyType({k: frozenset(v) for k, v in d.items()})


MACHINES = MappingProxyType({
    "matrix": _m({
        "draft": {"validated", "rejected"},
        "validated": {"approved", "rejected"},
        "approved": {"active", "rejected"},
        "active": {"deprecated", "quarantined"},
        "deprecated": {"retired"},
        "quarantined": {"validated", "retired"},
        "rejected": set(), "retired": set(),
    }),
    "cert": _m({
        "pending": {"valid", "rejected"},
        "valid": {"suspended", "revoked", "expired", "superseded"},
        "suspended": {"valid", "revoked", "expired"},
        "revoked": set(), "expired": set(), "superseded": set(), "rejected": set(),
    }),
    "config": _m({
        "received": {"parsed", "rejected"},
        "parsed": {"validated", "rejected"},
        "validated": {"authorized", "rejected"},
        "authorized": {"prepared", "rejected"},
        "prepared": {"active", "rolled_back"},
        "active": {"superseded"},
        "superseded": {"active"},          # rollback re-activates a prior revision
        "rejected": set(), "rolled_back": set(),
    }),
    "deprecation": _m({
        "supported": {"deprecated"},
        "deprecated": {"end_of_support", "supported"},
        "end_of_support": {"removed"},
        "removed": set(),
    }),
})

ADMITTING_CERT_STATES = frozenset({"valid"})


def check(machine: str, current: str, target: str) -> None:
    table = MACHINES.get(machine)
    if table is None or current not in table:
        raise Inv22Error("INV22.STATE.ILLEGAL_TRANSITION", "unknown machine/state", {"machine": machine, "state": current})
    if target not in table[current]:
        raise Inv22Error("INV22.STATE.ILLEGAL_TRANSITION", "transition not permitted",
                         {"machine": machine, "from": current, "to": target})


def allowed(machine: str, current: str) -> list[str]:
    return sorted(MACHINES[machine].get(current, ()))
