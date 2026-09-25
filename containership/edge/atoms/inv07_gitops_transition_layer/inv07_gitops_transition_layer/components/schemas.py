"""Versioned interface schemas (component 13) and a stdlib validator.

The wire contracts named by the INV-07 architecture contract are defined
here once, written to ``schemas/*.schema.json`` (JSON Schema 2020-12) by
``python -m ...components.schemas --write``, and checked by
``tests/test_contracts.py`` (files must equal the generated text).

Compatibility rules (docs/API_REFERENCE.md):
* ``/N`` is the major version -- a field may be *added* as optional within a
  major; removing, renaming, retyping or making a field required needs ``/N+1``;
* readers must ignore unknown fields only where ``additionalProperties`` is
  not ``false`` (envelopes are closed; ``details`` maps are open);
* the controller emits exactly one major per interface and accepts N and N-1
  on input once an N+1 exists (none does yet).

``validate`` implements the subset of JSON Schema these files use (type,
required, properties, additionalProperties, enum, const, pattern, minimum,
maximum, minLength, maxLength, items, minItems, maxItems, $ref to $defs).
"""
from __future__ import annotations

import json
import os
import re
import sys

from .fsutil import load_json, read_bytes, read_text  # noqa: F401
from .errors import REGISTRY, Malformed

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "schemas")
D = "https://json-schema.org/draft/2020-12/schema"
OID = {"type": "string", "pattern": "^[0-9a-f]{40}([0-9a-f]{24})?$"}
REF = {"type": "string", "pattern": "^refs/(heads|tags)/[A-Za-z0-9._/-]{1,200}$", "maxLength": 210}
SHA = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
RID = {"type": "string", "maxLength": 600}
TS = {"type": "number", "minimum": 0}
ID = {"type": "string", "maxLength": 128}


def _obj(props: dict, required: list, closed: bool = True, **extra) -> dict:
    d = {"type": "object", "properties": props, "required": required, **extra}
    if closed:
        d["additionalProperties"] = False
    return d


SCHEMAS = {
    "PK_GITOPS_VERIFY_1": _obj({
        "schema": {"const": "PK_GITOPS_VERIFY/1"}, "ref": REF, "oid": OID, "tree": OID,
        "result": {"enum": ["verified", "refused"]},
        "signer": _obj({"key_id": ID, "algorithm": {"enum": ["ed25519", "openpgp"]}, "identity": ID}, ["key_id", "algorithm", "identity"]),
        "provenance": {"type": ["object", "null"]}, "trust_digest": SHA, "error": {"type": ["object", "null"]},
        "at": TS, "cid": {"type": ["string", "null"], "maxLength": 64}},
        ["schema", "ref", "oid", "result", "trust_digest", "at"]),
    "PK_GITOPS_SYNC_1": _obj({
        "schema": {"const": "PK_GITOPS_SYNC/1"}, "decision_id": ID, "ref": REF, "oid": OID,
        "previous": {"type": ["string", "null"], "pattern": "^[0-9a-f]{40}([0-9a-f]{24})?$"},
        "mode": {"enum": ["initial", "fast_forward", "signed_revert", "rollback_exception", "unchanged"]},
        "outcome": {"enum": ["applied", "no_change", "refused", "failed", "frozen", "read_only", "duplicate"]},
        "actions": {"type": "array", "maxItems": 100000,
                    "items": _obj({"op": {"enum": ["create", "update", "delete"]}, "rid": RID}, ["op", "rid"])},
        "drift": {"type": "array", "items": RID, "maxItems": 100000}, "epoch": {"type": "integer", "minimum": 0},
        "policy_digest": {"type": "string", "maxLength": 64}, "trust_digest": SHA,
        "error": {"type": ["object", "null"]}, "at": TS, "trace_id": {"type": ["string", "null"], "maxLength": 32}},
        ["schema", "decision_id", "ref", "outcome", "at"]),
    "PK_GITOPS_DRIFT_1": _obj({
        "schema": {"const": "PK_GITOPS_DRIFT/1"}, "ref": REF, "detected_against": OID, "reconciled_to": OID,
        "resources": {"type": "array", "minItems": 1, "maxItems": 100000,
                      "items": _obj({"rid": RID, "change": {"enum": ["modified", "deleted", "added"]}}, ["rid", "change"])},
        "action": {"enum": ["reverted", "reported_only"]}, "at": TS, "decision_id": ID},
        ["schema", "ref", "detected_against", "resources", "action", "at"]),
    "PK_GITOPS_STATUS_1": _obj({
        "schema": {"const": "PK_GITOPS_STATUS/1"}, "tenant": ID, "site": ID, "leader": {"type": "boolean"},
        "epoch": {"type": ["integer", "null"]}, "refs": {"type": "object"}, "frozen": {"type": "array"},
        "last_sync": {"type": ["number", "null"]}, "health": {"enum": ["healthy", "degraded", "blocked"]},
        "reasons": {"type": "array", "items": {"type": "string", "maxLength": 256}},
        "pending_intents": {"type": "integer", "minimum": 0}, "version": {"type": "string"}},
        ["schema", "tenant", "site", "leader", "health", "version"]),
    "PK_GITOPS_ERROR_1": _obj({
        "schema": {"const": "PK_GITOPS_ERROR/1"}, "code": {"enum": sorted(REGISTRY)},
        "category": {"type": "string", "maxLength": 32}, "retry": {"enum": ["terminal", "retryable", "operator"]},
        "severity": {"enum": ["info", "warning", "error", "critical"]}, "message": {"type": "string", "maxLength": 4096},
        "details": {"type": "object"}, "correlation_id": {"type": ["string", "null"], "maxLength": 64},
        "cause": {"type": ["string", "null"], "maxLength": 128}},
        ["schema", "code", "category", "retry", "severity", "message"]),
    "PK_GITOPS_EVENT_1": _obj({
        "schema": {"const": "PK_GITOPS_EVENT/1"}, "ts": TS, "code": {"type": "string", "maxLength": 64},
        "severity": {"enum": ["debug", "info", "warning", "error", "critical"]},
        "message": {"type": "string", "maxLength": 4096}, "tenant": ID, "site": ID,
        "cid": {"type": ["string", "null"]}, "trace_id": {"type": ["string", "null"]},
        "span_id": {"type": ["string", "null"]}, "fields": {"type": "object"}},
        ["schema", "ts", "code", "severity", "message", "tenant", "site"]),
    "PK_GITOPS_EXPLAIN_1": _obj({
        "schema": {"const": "PK_GITOPS_EXPLAIN/1"}, "decision_id": ID, "ref": REF, "oid": {"type": ["string", "null"]},
        "signer": {"type": ["object", "null"]}, "provenance": {"type": ["object", "null"]},
        "policy": {"type": ["object", "null"]}, "actions": {"type": "array"}, "drift": {"type": "array"},
        "overrides": {"type": "array"}, "audit_seq": {"type": "array", "items": {"type": "integer"}},
        "trace_id": {"type": ["string", "null"]}, "outcome": {"type": "string"}, "error": {"type": ["object", "null"]},
        "at": TS, "target": {"type": "string"}, "tenant": ID, "site": ID},
        ["schema", "decision_id", "ref", "outcome", "at"]),
}


def _type_ok(v, t) -> bool:
    ts = t if isinstance(t, list) else [t]
    for x in ts:
        if x == "object" and isinstance(v, dict): return True
        if x == "array" and isinstance(v, list): return True
        if x == "string" and isinstance(v, str): return True
        if x == "integer" and isinstance(v, int) and not isinstance(v, bool): return True
        if x == "number" and isinstance(v, (int, float)) and not isinstance(v, bool): return True
        if x == "boolean" and isinstance(v, bool): return True
        if x == "null" and v is None: return True
    return False


def validate(doc, schema: dict, path: str = "$") -> list[str]:
    errs = []
    if "const" in schema and doc != schema["const"]:
        return [f"{path}: const mismatch"]
    if "enum" in schema and doc not in schema["enum"]:
        return [f"{path}: not in enum"]
    if "type" in schema and not _type_ok(doc, schema["type"]):
        return [f"{path}: wrong type"]
    if isinstance(doc, str):
        if "pattern" in schema and not re.search(schema["pattern"], doc):
            errs.append(f"{path}: pattern mismatch")
        if "maxLength" in schema and len(doc) > schema["maxLength"]:
            errs.append(f"{path}: too long")
    if isinstance(doc, (int, float)) and not isinstance(doc, bool):
        if "minimum" in schema and doc < schema["minimum"]:
            errs.append(f"{path}: below minimum")
        if "maximum" in schema and doc > schema["maximum"]:
            errs.append(f"{path}: above maximum")
    if isinstance(doc, list):
        if "minItems" in schema and len(doc) < schema["minItems"]:
            errs.append(f"{path}: too few items")
        if "maxItems" in schema and len(doc) > schema["maxItems"]:
            errs.append(f"{path}: too many items")
        if "items" in schema:
            for i, x in enumerate(doc):
                errs += validate(x, schema["items"], f"{path}[{i}]")
    if isinstance(doc, dict):
        for r in schema.get("required", []):
            if r not in doc:
                errs.append(f"{path}: missing {r}")
        props = schema.get("properties", {})
        for k, v in doc.items():
            if k in props:
                errs += validate(v, props[k], f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: unexpected property {k}")
    return errs


def check(name: str, doc) -> None:
    errs = validate(doc, SCHEMAS[name])
    if errs:
        raise Malformed("document does not match schema", schema=name, errors=errs[:5])


def render(name: str) -> str:
    s = {"$schema": D, "$id": f"https://pk.example/schemas/{name}.schema.json", "title": name.replace("_", "/", 3)
         .replace("PK/GITOPS/", "PK_GITOPS_"), **SCHEMAS[name]}
    return json.dumps(s, indent=1, sort_keys=True) + "\n"


def write_all(out: str = OUT) -> list[str]:
    os.makedirs(out, exist_ok=True)
    names = []
    for n in sorted(SCHEMAS):
        with open(os.path.join(out, n + ".schema.json"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(render(n))
        names.append(n)
    return names


if __name__ == "__main__":
    if "--write" in sys.argv:
        print("\n".join(write_all()))
    else:
        bad = [n for n in SCHEMAS if not os.path.exists(os.path.join(OUT, n + ".schema.json"))
               or read_text(os.path.join(OUT, n + ".schema.json")) != render(n)]
        print("stale:", bad) if bad else print("schemas up to date")
        sys.exit(1 if bad else 0)
