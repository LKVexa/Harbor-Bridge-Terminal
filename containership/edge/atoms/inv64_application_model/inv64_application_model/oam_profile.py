"""OAM baseline profile: app/v1 <-> OAM v0.3.0 ``Application`` (MC-11; C031, C093).

Pinned baseline (``provenance/oam-baseline.json``): oam-dev/spec tag ``v0.3.0``,
commit ``3104d27a0ecb55cac84755950e53371aa3e1d2b2``; compatibility level is
**schema-level for components and traits, conceptual for providers/links**
(OAM has no first-class provider or link object). See OAM_PROFILE.md.

Adopted: Application, components (name, type, properties), traits (type,
properties) attached to a component. Adapted: providers and links travel as
``metadata.annotations`` because OAM has no equivalent. Unsupported (refused on
import with a stable reason): ``scopes``, ``policies``, ``workflow``, component
``dependsOn``/``inputs``/``outputs``, and more than one trait of one type on a
component (OAM v0.3.0 §7 "one configuration per trait type" — app/v1 is stricter
nowhere else, so duplicates are refused on export instead of silently merged).
"""
from __future__ import annotations

import json
from typing import Any

from .errors import Inv64Error
from .manifest import validate_issues

OAM_API_VERSION = "core.oam.dev/v1beta1"
OAM_TAG = "v0.3.0"
OAM_COMMIT = "3104d27a0ecb55cac84755950e53371aa3e1d2b2"
UNSUPPORTED_SPEC_KEYS = ("scopes", "policies", "workflow")
UNSUPPORTED_COMPONENT_KEYS = ("scopes", "dependsOn", "inputs", "outputs", "externalRevision")
ANN_PROVIDERS = "inv64.pk/providers"
ANN_LINKS = "inv64.pk/links"


def to_oam(manifest: dict, *, name: str) -> dict:
    if validate_issues(manifest):
        raise Inv64Error("manifest.invalid", details={"stage": "oam-export"})
    comps = []
    for c in manifest.get("components", []):
        traits = [t for t in manifest.get("traits", []) if t["component"] == c["name"]]
        types = [t["type"] for t in traits]
        if len(types) != len(set(types)):
            raise Inv64Error("manifest.invalid", details={"reason": "oam.duplicate_trait_type", "component": c["name"]})
        comps.append({"name": c["name"], "type": c.get("type", "webservice"),
                      "properties": c.get("properties", {}),
                      **({"traits": [{"type": t["type"], "properties": t.get("properties", {})} for t in traits]}
                         if traits else {})})
    ann = {}
    if manifest.get("providers"):
        ann[ANN_PROVIDERS] = json.dumps(manifest["providers"], sort_keys=True, separators=(",", ":"))
    if manifest.get("links"):
        ann[ANN_LINKS] = json.dumps(manifest["links"], sort_keys=True, separators=(",", ":"))
    return {"apiVersion": OAM_API_VERSION, "kind": "Application",
            "metadata": {"name": name, **({"annotations": ann} if ann else {})},
            "spec": {"components": comps}}


def from_oam(doc: Any) -> dict:
    if not isinstance(doc, dict) or doc.get("apiVersion") != OAM_API_VERSION or doc.get("kind") != "Application":
        raise Inv64Error("schema.unsupported" if isinstance(doc, dict) else "request.invalid",
                         details={"reason": "oam.not_application_v1beta1"})
    spec = doc.get("spec")
    if not isinstance(spec, dict) or not isinstance(spec.get("components"), list):
        raise Inv64Error("request.invalid", details={"reason": "oam.spec.components required"})
    for k in UNSUPPORTED_SPEC_KEYS:
        if k in spec:
            raise Inv64Error("request.invalid", details={"reason": f"oam.unsupported.{k}"})
    components, traits = [], []
    for c in spec["components"]:
        if not isinstance(c, dict) or not isinstance(c.get("name"), str) or not isinstance(c.get("type"), str):
            raise Inv64Error("request.invalid", details={"reason": "oam.component.name/type required"})
        for k in UNSUPPORTED_COMPONENT_KEYS:
            if k in c:
                raise Inv64Error("request.invalid", details={"reason": f"oam.unsupported.component.{k}"})
        if "/" in c["type"]:
            raise Inv64Error("request.invalid", details={"reason": "oam.unsupported.namespaced_type"})
        components.append({"name": c["name"], "type": c["type"], "properties": c.get("properties", {})})
        seen = set()
        for t in c.get("traits", []) or []:
            if not isinstance(t, dict) or not isinstance(t.get("type"), str):
                raise Inv64Error("request.invalid", details={"reason": "oam.trait.type required"})
            if t["type"] in seen:
                raise Inv64Error("request.invalid", details={"reason": "oam.duplicate_trait_type"})
            seen.add(t["type"])
            traits.append({"type": t["type"], "component": c["name"], "properties": t.get("properties", {})})
    ann = (doc.get("metadata") or {}).get("annotations") or {}
    try:
        providers = json.loads(ann[ANN_PROVIDERS]) if ANN_PROVIDERS in ann else []
        links = json.loads(ann[ANN_LINKS]) if ANN_LINKS in ann else []
    except (TypeError, ValueError):
        raise Inv64Error("request.invalid", details={"reason": "oam.annotation.malformed"})
    out = {"schema": "app/v1", "components": components, "providers": providers, "links": links, "traits": traits}
    issues = validate_issues(out)
    if issues:
        raise Inv64Error("manifest.invalid", details={"stage": "oam-import", "codes": sorted({i.code for i in issues})})
    return out
