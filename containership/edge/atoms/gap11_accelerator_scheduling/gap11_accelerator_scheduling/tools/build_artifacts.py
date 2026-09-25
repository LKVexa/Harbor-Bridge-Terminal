"""Render generated documents and schema files from tools/registry.py and gap11_control.wire.

Outputs (all deterministic — no timestamps, host names or interpreter versions):
  docs/DESIGN_RECORDS.md, docs/REQUIREMENTS.json, docs/DATA_INVENTORY.md,
  docs/OPERATING_MODES.md, docs/ROLLOUT.md, gap11_control/schemas/*.schema.json,
  release/SBOM.cdx.json
"""
from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))

from registry import COMPONENTS  # noqa: E402
from gap11_control.wire import SCHEMAS  # noqa: E402

ITEMS = json.loads((ROOT / "docs" / "CHECKLIST_ITEMS.json").read_text())
TITLE = {c["id"]: c for c in ITEMS["components"]}


def design_records() -> str:
    out = ["# GAP-11 component design records (GAP11-*.11)\n",
           "Generated from `tools/registry.py`. Owner fields read UNASSIGNED because no owner has been named (GAP11-P2-46).\n"]
    for c in COMPONENTS:
        t = TITLE[c["id"]]
        out.append(f"\n## {c['id']} — {t['title']}  <a id=\"{c['id']}\"></a>\n")
        out.append(f"- **Disposition:** {c['disposition']}  \n- **Required capability (checklist):** {t['capability']}  \n"
                   f"- **Source controls:** {t['source_controls']}  \n- **Purpose / scope:** {c['purpose']}  \n"
                   f"- **Non-goals:** {c['non_goals']}  \n- **Trust boundary:** {c['trust_boundary']}  \n"
                   f"- **Dependencies:** {', '.join(c['dependencies']) or 'none'}  \n- **Inputs:** {', '.join(c['inputs']) or 'n/a'}  \n"
                   f"- **Outputs:** {', '.join(c['outputs']) or 'n/a'}  \n- **Implementation:** {', '.join('`'+m+'`' for m in c['modules']) or 'none'}  \n"
                   f"- **Tests:** {', '.join('`'+x+'`' for x in c['tests']) or 'none'}  \n- **Owner:** {c['owner']}  \n"
                   f"- **Lifecycle template:** {c['template']}  \n")
        if c["blockers"]:
            out.append("- **Blockers:** " + "; ".join(c["blockers"]) + "\n")
    return "".join(out)


def requirements() -> dict:
    reqs = []
    for c in COMPONENTS:
        t = TITLE[c["id"]]
        reqs.append({"id": f"{c['id']}-R00", "level": "MUST", "text": f"GAP-11 MUST provide: {t['capability']}", "component": c["id"],
                     "verified_by": c["tests"]})
        for i, inv in enumerate(c["invariants"], 1):
            reqs.append({"id": f"{c['id']}-R{i:02d}", "level": "MUST", "text": inv, "component": c["id"], "verified_by": c["tests"]})
        for j, code in enumerate(c["telemetry"], 1):
            reqs.append({"id": f"{c['id']}-S{j:02d}", "level": "SHOULD", "text": f"emit stable reason/event `{code}` on the relevant path",
                         "component": c["id"], "verified_by": c["tests"]})
        if c["blockers"]:
            reqs.append({"id": f"{c['id']}-M01", "level": "MAY", "text": "operate under a time-bounded APPROVED exception while blockers remain: " +
                         "; ".join(b.split(":")[0] for b in c["blockers"]), "component": c["id"], "verified_by": ["docs/EXCEPTIONS.json"]})
    return {"schema": "GAP11_REQUIREMENTS/1", "requirements": reqs}


def data_inventory() -> str:
    out = ["# GAP-11 data inventory (GAP11-*.15)\n\n| Component | Datum | Authoritative source | Confidentiality / integrity | Retention | Versioning |\n|---|---|---|---|---|---|\n"]
    for c in COMPONENTS:
        if not c["data"]:
            out.append(f"| {c['id']} | *(no persistent datum; stateless or document)* | — | — | — | — |\n")
        for d in c["data"]:
            out.append(f"| {c['id']} | `{d[0]}` | {d[1]} | {d[2]} | {d[3]} | {d[4]} |\n")
    return "".join(out)


def modes() -> str:
    out = ["# GAP-11 operating modes (GAP11-*.16)\n\n| Component | startup | steady | degraded | recovery | maintenance | shutdown |\n|---|---|---|---|---|---|---|\n"]
    for c in COMPONENTS:
        m = c["modes"]
        out.append(f"| {c['id']} | " + " | ".join(m[k] for k in ("startup", "steady", "degraded", "recovery", "maintenance", "shutdown")) + " |\n")
    return "".join(out)


def rollout() -> str:
    out = ["# GAP-11 rollout / rollback / mixed-version behaviour (GAP11-*.19)\n\n",
           "Global: feature gates live in `config.feature_gates` (default off for gang allocation and preemption); WAL v1 and `ctl/leader` are shared by all 4.x controllers; see docs/COMPATIBILITY.md and RUNBOOK-02/03.\n\n",
           "| Component | Rollout / compatibility note |\n|---|---|\n"]
    for c in COMPONENTS:
        out.append(f"| {c['id']} | {c['rollout']} |\n")
    return "".join(out)


def sbom() -> dict:
    comps = []
    for p in sorted((ROOT / "gap11_control").rglob("*.py")) + [ROOT / "allocator.py"]:
        tree = ast.parse(p.read_text())
        for n in ast.walk(tree):
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                mod = (n.module or "") if isinstance(n, ast.ImportFrom) else n.names[0].name
                root = mod.split(".")[0]
                if isinstance(n, ast.ImportFrom) and n.level:
                    continue
                if root and root not in sys.stdlib_module_names and root not in ("gap11_control", "support") and not root.startswith("test_"):
                    comps.append(root)
    files = [{"name": str(p.relative_to(ROOT)), "hashes": [{"alg": "SHA-256", "content": hashlib.sha256(p.read_bytes()).hexdigest()}]}
             for p in sorted((ROOT / "gap11_control").rglob("*.py")) + [ROOT / "allocator.py"]]
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "library", "name": "gap11-accelerator-scheduling", "version": "4.3.0"}},
            "components": [{"type": "library", "name": c} for c in sorted(set(comps))],
            "properties": [{"name": "third_party_runtime_dependencies", "value": str(len(set(comps)))},
                           {"name": "vendored_code", "value": "none"}, {"name": "native_components", "value": "none"}],
            "files": files}


def main() -> None:
    docs = ROOT / "docs"
    (docs / "DESIGN_RECORDS.md").write_text(design_records())
    (docs / "REQUIREMENTS.json").write_text(json.dumps(requirements(), indent=1) + "\n")
    (docs / "DATA_INVENTORY.md").write_text(data_inventory())
    (docs / "OPERATING_MODES.md").write_text(modes())
    (docs / "ROLLOUT.md").write_text(rollout())
    sd = ROOT / "gap11_control" / "schemas"
    sd.mkdir(exist_ok=True)
    for name, s in SCHEMAS.items():
        fn = name.replace("/", "_v") + ".schema.json"
        (sd / fn).write_text(json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": name, **s}, indent=1, sort_keys=True) + "\n")
    (ROOT / "release").mkdir(exist_ok=True)
    (ROOT / "release" / "SBOM.cdx.json").write_text(json.dumps(sbom(), indent=1) + "\n")
    print("artifacts built")


if __name__ == "__main__":
    main()
