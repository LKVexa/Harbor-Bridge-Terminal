"""Component 05 - licence inventory, NOTICE rules and CI policy (PK_DYN_LICENSE/1).

Classification of SPDX identifiers:
  ALLOW   permissive licences compatible with redistribution in any project licence
  DENY    strong/network copyleft or source-available licences
  UNKNOWN anything else, including ``LicenseRef-*`` and missing values

CI rule (``ci_gate``): any runtime dependency that is DENY or UNKNOWN fails; an
optional dependency that is DENY fails, UNKNOWN is reported as a blocker (it must
be resolved or waived via component 65).  The project's own licence is
``LicenseRef-UNASSIGNED`` until an owner chooses one -> LICENSE file BLOCKED and
the compatibility review is only partially computable.

NOTICE rules: one section per shipped third-party dependency whose licence
requires attribution (Apache-2.0 NOTICE propagation, BSD/MIT copyright notice);
stdlib-only builds therefore produce a NOTICE containing only the project header.
"""
from __future__ import annotations

import re

ALLOW = {"MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC", "PSF-2.0", "Python-2.0",
         "Zlib", "0BSD", "Unlicense", "CC0-1.0"}
DENY = {"GPL-2.0-only", "GPL-2.0-or-later", "GPL-3.0-only", "GPL-3.0-or-later", "AGPL-3.0-only",
        "AGPL-3.0-or-later", "SSPL-1.0", "BUSL-1.1", "CC-BY-NC-4.0", "Commons-Clause"}
ATTRIBUTION = {"MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC", "Zlib", "PSF-2.0", "Python-2.0"}
PROJECT_LICENSE = "LicenseRef-UNASSIGNED"


def classify(spdx: str | None) -> str:
    if not spdx or not isinstance(spdx, str):
        return "UNKNOWN"
    parts = [p.strip("() ") for p in re.split(r"\s+(?:OR|AND)\s+", spdx.strip())]
    kinds = {("ALLOW" if p in ALLOW else "DENY" if p in DENY else "UNKNOWN") for p in parts}
    if " OR " in spdx and "ALLOW" in kinds:
        return "ALLOW"          # licensee may elect the permissive branch
    if "DENY" in kinds:
        return "DENY"
    if "UNKNOWN" in kinds:
        return "UNKNOWN"
    return "ALLOW"


def inventory(pyproject: dict | None = None) -> list[dict]:
    """Dependency inventory derived from declared metadata.

    Runtime: none (stdlib only; the interpreter's PSF licence covers stdlib).
    Optional: each extra's requirements; their licences are unknown until pinned.
    """
    inv = [{"name": "python-stdlib", "scope": "runtime", "license": "PSF-2.0", "bundled": False}]
    proj = (pyproject or {}).get("project", {})
    for dep in proj.get("dependencies", []):
        inv.append({"name": dep, "scope": "runtime", "license": None, "bundled": True})
    for extra, deps in sorted(proj.get("optional-dependencies", {}).items()):
        for dep in deps:
            inv.append({"name": dep, "scope": f"optional:{extra}", "license": None, "bundled": False})
    for i in inv:
        i["class"] = classify(i["license"])
    return inv


def notice(inv: list[dict], project: str = "inv08-dynamic-infrastructure-model") -> str:
    lines = [f"{project}", f"Project licence: {PROJECT_LICENSE} (owner decision pending)", ""]
    for i in sorted(inv, key=lambda x: x["name"]):
        if i["bundled"] and i["license"] in ATTRIBUTION:
            lines.append(f"This product includes {i['name']} under {i['license']}.")
    return "\n".join(lines).rstrip() + "\n"


def compatibility(project_license: str, inv: list[dict]) -> dict:
    if classify(project_license) == "UNKNOWN":
        return {"state": "BLOCKED", "reason": f"project licence {project_license} not chosen",
                "conflicts": []}
    conflicts = [i["name"] for i in inv if i["bundled"] and i["class"] != "ALLOW"]
    return {"state": "OK" if not conflicts else "CONFLICT", "conflicts": conflicts}


def ci_gate(inv: list[dict]) -> dict:
    failures, blockers = [], []
    for i in inv:
        if i["class"] == "DENY" or (i["scope"] == "runtime" and i["class"] == "UNKNOWN"):
            failures.append(f"{i['name']} ({i['scope']}): {i['class']}")
        elif i["class"] == "UNKNOWN":
            blockers.append(f"{i['name']} ({i['scope']}): licence unknown")
    return {"ok": not failures, "failures": failures, "blockers": blockers}
