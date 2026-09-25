"""SBOM verification and policy binding (CycloneDX 1.4-1.6 JSON, SPDX 2.3 JSON).

An SBOM is admissible only as the predicate of a DSSE/in-toto attestation
whose subject is the artifact digest (``dsse.verify_envelope`` enforces the
subject match and signer authorisation for the predicate type).  This module
parses the predicate strictly, extracts package identities (purl preferred),
correlates VEX/vulnerability state and produces the ``sbom`` facts consumed by
``policy.evaluate``.
"""
from __future__ import annotations

from typing import Any, Mapping

from .errors import fail

CYCLONEDX = "https://cyclonedx.org/bom"
SPDX = "https://spdx.dev/Document"
MAX_COMPONENTS = 50_000
_OPEN_STATES = {None, "in_triage", "exploitable", "affected", "under_investigation"}


def normalize_purl(purl: str) -> str:
    """Package identity for policy: type/namespace/name only (drop version, qualifiers, subpath), lowercased."""
    p = purl.split("#", 1)[0].split("?", 1)[0]
    head, _, tail = p.rpartition("/")
    name = tail.split("@", 1)[0]
    return (f"{head}/{name}" if head else name).lower()


def _walk(comps: Any, depth: int = 0) -> list:
    if depth > 16 or not isinstance(comps, list):
        if depth > 16:
            raise fail("SBOM_INVALID", "component nesting too deep")
        return []
    out = []
    for c in comps:
        if isinstance(c, Mapping):
            out.append(c)
            out.extend(_walk(c.get("components", []), depth + 1))
    if len(out) > MAX_COMPONENTS:
        raise fail("SBOM_INVALID", "too many components")
    return out


def _pkg_id(c: Mapping[str, Any]) -> str:
    purl = c.get("purl")
    if isinstance(purl, str) and purl.startswith("pkg:"):
        return normalize_purl(purl)
    name = c.get("name")
    if not isinstance(name, str) or not name:
        raise fail("SBOM_INVALID", "component without name/purl")
    return f"name:{name.lower()}"


def facts_from_predicate(predicate_type: str, bom: Mapping[str, Any]) -> dict[str, Any]:
    if predicate_type == CYCLONEDX:
        if bom.get("bomFormat") != "CycloneDX" or str(bom.get("specVersion")) not in ("1.4", "1.5", "1.6"):
            raise fail("SBOM_INVALID", "unsupported CycloneDX document")
        comps = bom.get("components", [])
        if not isinstance(comps, list) or len(comps) > MAX_COMPONENTS:
            raise fail("SBOM_INVALID", "components list invalid")
        pkgs = sorted({_pkg_id(c) for c in _walk(comps)})
        sev: list[str] = []
        for v in bom.get("vulnerabilities", []) or []:
            state = (v.get("analysis") or {}).get("state")
            if state in _OPEN_STATES:
                ratings = v.get("ratings") or [{}]
                sev.append(max((str(r.get("severity", "critical")).lower() for r in ratings), key=lambda s: ["none", "info", "low", "medium", "high", "critical", "unknown"].index(s) if s in ["none", "info", "low", "medium", "high", "critical", "unknown"] else 6))
        fmt = "cyclonedx"
    elif predicate_type == SPDX:
        if bom.get("spdxVersion") not in ("SPDX-2.3",):
            raise fail("SBOM_INVALID", "unsupported SPDX document")
        packs = bom.get("packages", [])
        if not isinstance(packs, list) or len(packs) > MAX_COMPONENTS:
            raise fail("SBOM_INVALID", "packages list invalid")
        pkgs = []
        for p in packs:
            purls = [r.get("referenceLocator") for r in p.get("externalRefs", []) if r.get("referenceType") == "purl"]
            pkgs.append(_pkg_id({"purl": purls[0]} if purls else {"name": p.get("name")}))
        pkgs = sorted(set(pkgs))
        sev = None  # SPDX 2.3 carries no vulnerability state: unknown, never "clean"
        fmt = "spdx"
    else:
        raise fail("SBOM_INVALID", "unknown SBOM predicate type")
    if sev is not None:
        sev = ["critical" if s == "unknown" else ("none" if s == "info" else s) for s in sev]
    return {"format": fmt, "packages": pkgs, "open_vulnerability_severities": sev, "component_count": len(pkgs)}
