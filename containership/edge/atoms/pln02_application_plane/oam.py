"""MC-09 - OAM Application (``core.oam.dev/v1beta1``) adapter - documented subset.

Supported (and *only* supported) shape::

    apiVersion: core.oam.dev/v1beta1
    kind: Application
    metadata: {name: <dns-label>}
    spec:
      components:
        - name: api
          type: <any component type string; carried as metadata, not interpreted>
          properties: {...}                       # opaque, not interpreted
          traits:
            - type: pk.capabilities   properties: {requires: {state: true}}
            - type: pk.interfaces     properties: {exports: {...}, imports: {"store": "1.2"}}
            - type: pk.bindings       properties: {imports: {"store": "<producer component>"}}
      policies:
        - name: residency
          type: pk.constraints        properties: {residency: ["eu"], ...}

Everything else - other trait types, other policy types, ``workflow``, other
apiVersions - is refused with ``OAM_INVALID`` rather than silently ignored,
because OAM trait/policy semantics would otherwise be assumed but unenforced.
The output is a ``PK_APPLICATION/1`` document plus an application constraints
document for ``policy.merge``.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from .errors import PlaneError
from .resolver import APPLICATION_SCHEMA

OAM_API_VERSION = "core.oam.dev/v1beta1"
SUPPORTED_TRAITS = {"pk.capabilities", "pk.interfaces", "pk.bindings"}
SUPPORTED_POLICIES = {"pk.constraints"}
_DNS = re.compile(r"^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?$")


def _bad(field: str, reason: str) -> PlaneError:
    return PlaneError(f"OAM {field}: {reason}", code="OAM_INVALID", details={"field": field, "reason": reason})


def _map(v: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(v, Mapping):
        raise _bad(field, "must be an object")
    return v


def translate(doc: Mapping[str, Any]) -> tuple[dict, dict]:
    """Return (PK_APPLICATION/1 document, application constraints document)."""
    doc = _map(doc, "$")
    if {str(k) for k in doc} - {"apiVersion", "kind", "metadata", "spec"}:
        raise _bad("$", "unsupported top-level field")
    if doc.get("apiVersion") != OAM_API_VERSION:
        raise _bad("apiVersion", f"only {OAM_API_VERSION} is supported")
    if doc.get("kind") != "Application":
        raise _bad("kind", "only Application is supported")
    meta = _map(doc.get("metadata"), "metadata")
    if not isinstance(meta.get("name"), str) or not _DNS.fullmatch(meta["name"]):
        raise _bad("metadata.name", "must be a DNS label")
    spec = _map(doc.get("spec"), "spec")
    if {str(k) for k in spec} - {"components", "policies"}:
        raise _bad("spec", "unsupported field (workflow is not supported)")
    comps = spec.get("components")
    if not isinstance(comps, list) or not comps:
        raise _bad("spec.components", "must be a non-empty list")

    components, edges = [], []
    for i, c in enumerate(comps):
        c = _map(c, f"spec.components[{i}]")
        if {str(k) for k in c} - {"name", "type", "properties", "traits"}:
            raise _bad(f"spec.components[{i}]", "unsupported field")
        name = c.get("name")
        if not isinstance(name, str) or not _DNS.fullmatch(name):
            raise _bad(f"spec.components[{i}].name", "must be a DNS label")
        if not isinstance(c.get("type"), str):
            raise _bad(f"spec.components[{i}].type", "required string")
        out = {"name": name, "requires": {}, "exports": {}, "imports": {}}
        seen: set[str] = set()
        traits = c.get("traits", [])
        if not isinstance(traits, list):
            raise _bad(f"spec.components[{i}].traits", "must be a list")
        for j, t in enumerate(traits):
            t = _map(t, f"spec.components[{i}].traits[{j}]")
            tt = t.get("type")
            if not isinstance(tt, str) or tt not in SUPPORTED_TRAITS:
                raise _bad(f"spec.components[{i}].traits[{j}].type", f"unsupported trait {str(tt)[:64]!r}")
            if tt in seen:
                raise _bad(f"spec.components[{i}].traits[{j}]", "duplicate trait")
            seen.add(tt)
            props = _map(t.get("properties", {}), f"spec.components[{i}].traits[{j}].properties")
            if tt == "pk.capabilities":
                if {str(k) for k in props} - {"requires"}:
                    raise _bad(f"spec.components[{i}].traits[{j}]", "unsupported property")
                out["requires"] = dict(_map(props.get("requires", {}), "requires"))
            elif tt == "pk.interfaces":
                if {str(k) for k in props} - {"exports", "imports"}:
                    raise _bad(f"spec.components[{i}].traits[{j}]", "unsupported property")
                out["exports"] = dict(_map(props.get("exports", {}), "exports"))
                out["imports"] = dict(_map(props.get("imports", {}), "imports"))
            else:  # pk.bindings
                if {str(k) for k in props} - {"imports"}:
                    raise _bad(f"spec.components[{i}].traits[{j}]", "unsupported property")
                for iface, producer in _map(props.get("imports", {}), "imports").items():
                    if not isinstance(iface, str) or not isinstance(producer, str):
                        raise _bad(f"spec.components[{i}].traits[{j}]", "binding must map interface to producer name")
                    edges.append([producer, name, iface])
        components.append(out)

    constraints: dict[str, Any] = {}
    policies = spec.get("policies", [])
    if not isinstance(policies, list):
        raise _bad("spec.policies", "must be a list")
    for k, p in enumerate(policies):
        p = _map(p, f"spec.policies[{k}]")
        if not isinstance(p.get("type"), str) or p["type"] not in SUPPORTED_POLICIES:
            raise _bad(f"spec.policies[{k}].type", "unsupported policy type")
        for key, val in _map(p.get("properties", {}), f"spec.policies[{k}].properties").items():
            if key in constraints and constraints[key] != val:
                raise _bad(f"spec.policies[{k}]", f"conflicting value for {key}")
            constraints[key] = val
    return {"schema": APPLICATION_SCHEMA, "components": components, "edges": edges}, constraints
