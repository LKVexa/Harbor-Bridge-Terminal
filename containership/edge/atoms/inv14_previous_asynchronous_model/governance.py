"""Governance data: migration registry, waivers, owners, EOL (components P1-13,
P1-17, P2-34, P2-35; C009, C091, C094, C097, C099).

The data lives in ``governance/*.json``.  This module validates it and enforces
it at runtime: ``ConsumerGate.check`` admits a legacy consumer only if it is in
the migration registry and either (a) inside its migration deadline or (b) holds
a live, approved, unexpired waiver.  After the EOL removal date nothing is
admitted.  ``production_blockers`` lists every governance reason the package must
not be certified -- e.g. owners still UNASSIGNED, EOL policy not approved.  This
archive deliberately ships those as blockers: an accountable owner, an approver
and real consumers can only come from the organisation, never from the build.
"""
from __future__ import annotations

import datetime as _dt
import json
import pathlib
import re

try:
    from .errors import Inv14Error
except ImportError:
    from errors import Inv14Error

GOV_DIR = pathlib.Path(__file__).resolve().parent / "governance"
STAGES = ("LEGACY", "DUAL_STACK", "CANARY", "MIGRATED", "ROLLED_BACK")
_ID = re.compile(r"^[a-z0-9][a-z0-9_./-]{0,127}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class GovernanceError(Inv14Error):
    default_code = "PK_GOVERNANCE_INVALID"


def _date(s, field):
    if not isinstance(s, str) or not _DATE.match(s):
        raise GovernanceError(f"{field} must be YYYY-MM-DD", details={"field": field})
    return _dt.date.fromisoformat(s)


def load(name: str, base: pathlib.Path = GOV_DIR) -> dict:
    return json.loads((base / name).read_text())


def validate_registry(doc: dict) -> dict:
    if doc.get("schema") != "PK_POLL_MIGRATION_REGISTRY/1" or not isinstance(doc.get("consumers"), list):
        raise GovernanceError("bad registry schema")
    seen = set()
    for c in doc["consumers"]:
        for k in ("component_id", "owner", "stage", "registered", "deadline"):
            if k not in c:
                raise GovernanceError("registry entry missing field", details={"field": k})
        if not _ID.match(str(c["component_id"])) or c["component_id"] in seen:
            raise GovernanceError("bad or duplicate component_id", details={"id": c["component_id"]})
        seen.add(c["component_id"])
        if c["stage"] not in STAGES:
            raise GovernanceError("unknown stage", details={"stage": c["stage"]})
        if _date(c["deadline"], "deadline") < _date(c["registered"], "registered"):
            raise GovernanceError("deadline precedes registration")
    return doc


def validate_waivers(doc: dict) -> dict:
    if doc.get("schema") != "PK_POLL_WAIVERS/1" or not isinstance(doc.get("waivers"), list):
        raise GovernanceError("bad waiver schema")
    for w in doc["waivers"]:
        for k in ("waiver_id", "component_id", "owner", "approved_by", "granted", "expires", "retirement_commitment"):
            if not w.get(k):
                raise GovernanceError("waiver missing field", details={"field": k})
        if w["approved_by"] == w["owner"]:
            raise GovernanceError("waiver may not be self-approved", code="PK_GOVERNANCE_SELF_APPROVAL")
        if (_date(w["expires"], "expires") - _date(w["granted"], "granted")).days > 180:
            raise GovernanceError("waiver longer than 180 days", code="PK_GOVERNANCE_WAIVER_TOO_LONG")
    return doc


def validate_owners(doc: dict) -> dict:
    if doc.get("schema") != "PK_POLL_OWNERS/1":
        raise GovernanceError("bad owners schema")
    for k in ("accountable_team", "oncall_route", "escalation", "support_boundary", "review_cadence_days"):
        if k not in doc:
            raise GovernanceError("owners missing field", details={"field": k})
    return doc


def validate_eol(doc: dict) -> dict:
    if doc.get("schema") != "PK_POLL_EOL/1":
        raise GovernanceError("bad eol schema")
    ms = doc.get("milestones")
    if not isinstance(ms, list) or not ms:
        raise GovernanceError("eol milestones required")
    prev = None
    for m in ms:
        d = _date(m.get("date"), "milestone.date")
        if prev and d <= prev:
            raise GovernanceError("eol milestones must be strictly increasing")
        prev = d
    if ms[-1].get("phase") != "REMOVED":
        raise GovernanceError("last eol milestone must be REMOVED")
    return doc


def eol_phase(eol: dict, today: _dt.date) -> str:
    phase = "SUPPORTED"
    for m in validate_eol(eol)["milestones"]:
        if today >= _dt.date.fromisoformat(m["date"]):
            phase = m["phase"]
    return phase


class ConsumerGate:
    def __init__(self, registry: dict, waivers: dict, eol: dict):
        self.registry = {c["component_id"]: c for c in validate_registry(registry)["consumers"]}
        self.waivers = validate_waivers(waivers)["waivers"]
        self.eol = validate_eol(eol)

    def register(self, entry: dict, today: _dt.date) -> None:
        """Add a consumer; refused once the EOL phase closes the registry."""
        if eol_phase(self.eol, today) not in ("SUPPORTED", "DEPRECATED"):
            raise GovernanceError("registry closed to new consumers", code="PK_POLL_REGISTRY_CLOSED")
        merged = {"schema": "PK_POLL_MIGRATION_REGISTRY/1", "consumers": list(self.registry.values()) + [entry]}
        validate_registry(merged)
        self.registry[entry["component_id"]] = entry

    def check(self, component_id: str, today: _dt.date) -> dict:
        phase = eol_phase(self.eol, today)
        if phase == "REMOVED":
            raise GovernanceError("INV-14 has reached end of life", code="PK_POLL_EOL_REMOVED")
        c = self.registry.get(component_id)
        if c is None:
            raise GovernanceError("consumer not in migration registry", code="PK_POLL_UNREGISTERED_CONSUMER")
        if c["stage"] == "MIGRATED":
            raise GovernanceError("consumer already migrated; legacy use refused", code="PK_POLL_MIGRATION_REGRESSION")
        if phase != "WAIVER_ONLY" and today <= _dt.date.fromisoformat(c["deadline"]):
            return {"allowed": True, "basis": "deadline", "eol_phase": phase}
        for w in self.waivers:
            if w["component_id"] == component_id and _dt.date.fromisoformat(w["granted"]) <= today <= _dt.date.fromisoformat(w["expires"]):
                return {"allowed": True, "basis": "waiver:" + w["waiver_id"], "eol_phase": phase}
        raise GovernanceError("migration deadline passed and no live waiver", code="PK_POLL_MIGRATION_OVERDUE")


def production_blockers(base: pathlib.Path = GOV_DIR) -> list:
    out = []
    owners = validate_owners(load("OWNERS.json", base))
    if owners["accountable_team"] in ("", "UNASSIGNED"):
        out.append("GOV-OWNER: accountable_team is UNASSIGNED")
    if owners["oncall_route"] in ("", "UNASSIGNED"):
        out.append("GOV-ONCALL: oncall_route is UNASSIGNED")
    eol = validate_eol(load("EOL_POLICY.json", base))
    if eol.get("status") != "APPROVED":
        out.append("GOV-EOL: EOL policy status is " + str(eol.get("status")))
    reg = validate_registry(load("MIGRATION_REGISTRY.json", base))
    if reg.get("inventory_status") != "COMPLETE":
        out.append("GOV-REGISTRY: consumer inventory status is " + str(reg.get("inventory_status")))
    validate_waivers(load("WAIVERS.json", base))
    return out
