"""Run the vendored pk_core conformance workflow + gate over INV-72 (C090, C100 framework lane).

    python -B -m inv72_accelerated_workload_requirement.tools.pk_gate [--out evidence/PK_GATE_RESULTS.json]

pk_core is the owner's PK framework, vendored unchanged under ``_vendor/pk_core`` (provenance in
``_vendor/PK_CORE_PROVENANCE.json``).  Its verdict measures conformance of the component's *declared
contract and exercised checks* against the 100-item checklist.  It is one input to tools/release_gate.py,
not a substitute for the RTM (which records what is actually implemented) - the two axes are reported
separately and never merged.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "_vendor"


def run() -> dict:
    if str(VENDOR) not in sys.path:
        sys.path.insert(0, str(VENDOR))
    if str(ROOT.parent) not in sys.path:
        sys.path.insert(0, str(ROOT.parent))
    from pk_core.gate import ConformanceGate
    from pk_core.workflow import WorkflowEngine
    from importlib import import_module
    comp = import_module(ROOT.name).COMPONENT()
    result = WorkflowEngine().run(comp)
    gate = ConformanceGate().evaluate([result]).to_dict()
    gate["workflow"] = {"certified": result.certified, "counts": result.counts, "coverage": result.coverage}
    mod = import_module(ROOT.name + ".component")
    gate["exercised_findings"] = len(mod.EXERCISED_BANDS)
    gate["declaration_derived_findings"] = sum(result.counts.values()) - len(mod.EXERCISED_BANDS)
    gate["axis_note"] = ("framework conformance only: pk_core's default band handlers derive findings from the "
                         "contract's declarations (several unconditionally), so 'satisfied' there is not "
                         "implementation evidence; implementation status lives in evidence/RTM.json")
    return gate


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "evidence" / "PK_GATE_RESULTS.json"))
    a = ap.parse_args(argv)
    g = run()
    Path(a.out).write_text(json.dumps(g, indent=1, default=str), encoding="utf-8")
    print("PK_GATE", g["verdict"], json.dumps(g["workflow"]["counts"]))
    return 0 if g["verdict"] == "GO" else 1


if __name__ == "__main__":
    sys.exit(main())
